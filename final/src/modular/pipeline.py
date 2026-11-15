"""Orchestrate replaceable stages and enforce the generation-before-oracle barrier."""
from __future__ import annotations

import fcntl
import hashlib
import inspect
import importlib.metadata
import platform
import sys
import json
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path

from final.src.runtime.artifacts import digest
from .generators import InputGenerator, default_input_generator, generator_for_arms
from .artifacts import ArtifactStore
from .calls import CachedModelCalls
from .execution_cache import InputExecutionCache
from .references import HumanEvalPlusReferencePrograms
from .context import PipelineSettings, TaskContext
from .stages.base import PipelineStage
from .stages.frozen_cohort import FrozenCohortStage
from .stages.input_generation import InputGenerationStage
from .stages.reference_oracle import ReferenceOracleStage
from .stages.put_evaluation import PutEvaluationStage
from .stages.reporting import ReportingStage


class BenchmarkPipeline:
    def __init__(self, cohort_path: Path, artifacts: ArtifactStore, *, arms=None,
                 settings: PipelineSettings | None = None, calls=None,
                 input_generator: InputGenerator | None = None, execution_cache=None, reference_programs=None):
        self.artifacts = artifacts
        self.settings = settings or PipelineSettings()
        if input_generator is not None and arms is not None:
            raise ValueError("Inject input_generator or supply arms, not both")
        if input_generator is None:
            input_generator = default_input_generator() if arms is None else generator_for_arms(arms)
        self.input_generator = input_generator
        # Input methods exposed for configuration and reporting.
        self.arms = tuple(getattr(input_generator, "methods", ()))
        self.calls = calls
        if self.artifacts.read_only and calls is not None and not isinstance(calls, CachedModelCalls):
            raise ValueError("Read-only replay only accepts cached model calls")
        if self.artifacts.read_only and calls is None:
            self.calls = CachedModelCalls(artifacts)
        self.cohort_stage = FrozenCohortStage(cohort_path)
        self.reporting_stage = input_generator.reporting_stage() or ReportingStage()
        self.generation_stages = [
            self.cohort_stage, *input_generator.preparation_stages(), InputGenerationStage(input_generator),
        ]
        if execution_cache is None and input_generator.cache_input_execution:
            execution_cache = InputExecutionCache(artifacts.directory.parent / "execution_cache",
                                                  read_only=artifacts.read_only)
        self.execution_cache = None if execution_cache is False else execution_cache
        if reference_programs is None:
            reference_programs = HumanEvalPlusReferencePrograms()
        self.reference_programs = reference_programs
        self.evaluation_stages = [ReferenceOracleStage(self.execution_cache, reference_programs),
                                  *input_generator.post_reference_stages(),
                                  PutEvaluationStage(self.execution_cache), self.reporting_stage]
        self.stage_events = []

    def insert_stage(self, stage: PipelineStage, *, after: str):
        """Add a stage without changing orchestration code or a central switch."""
        for stages in (self.generation_stages, self.evaluation_stages):
            for stage_index, current_stage in enumerate(stages):
                if current_stage.name == after:
                    stages.insert(stage_index + 1, stage)
                    try:
                        self.validate_stage_order()
                    except Exception:
                        stages.remove(stage)
                        raise
                    return self
        raise ValueError(f"Unknown predecessor stage: {after}")

    def validate_stage_order(self):
        completed_names = set()
        for stage in self.generation_stages + self.evaluation_stages:
            if stage.name in completed_names:
                raise ValueError(f"Duplicate stage: {stage.name}")
            for dependency in stage.requires:
                if dependency not in completed_names:
                    raise ValueError(f"Stage {stage.name} requires earlier stage {dependency}")
            completed_names.add(stage.name)

    def run(self, tasks: list[dict], metadata: dict) -> dict:
        self.validate_stage_order()
        task_ids = []
        for task in tasks:
            task_ids.append(task["task_id"])
        if len(task_ids) != len(set(task_ids)) or not task_ids:
            raise ValueError("Task IDs must be nonempty and unique")
        for task_id in task_ids:
            if task_id not in self.cohort_stage.task_records:
                raise ValueError(f"Task missing from frozen cohort: {task_id}")
        with self.run_lock():
            self.verify_or_write_manifest(tasks, metadata)
            contexts = []
            for task in tasks:
                context = TaskContext(task, metadata[task["task_id"]], self.artifacts, self.settings, self.calls)
                contexts.append(context)
                self.execute_stages(self.generation_stages, context)
            self.freeze_inputs(contexts)
            for context in contexts:
                context.inputs_frozen = True
                self.execute_stages(self.evaluation_stages, context)
            summary = self.reporting_stage.build_summary(contexts, self.cohort_stage.cohort)
            self.input_generator.extend_summary(contexts, summary, self.reporting_stage)
            if self.artifacts.read_only and self.artifacts.exists("summary.json"):
                historical_summary = self.artifacts.read("summary.json")
                if historical_summary != summary:
                    raise ValueError("Historical summary mismatch")
            else:
                self.artifacts.write("modular_summary.json", summary)
            if not self.artifacts.read_only:
                report_text = self.reporting_stage.render(summary)
                report_text += self.input_generator.render_summary(summary)
                self.artifacts.path("REPORT.md").write_text(report_text)
            return summary

    def execute_stages(self, stages, context):
        for stage in stages:
            for dependency in stage.requires:
                if dependency not in context.completed_stages:
                    raise RuntimeError(f"Missing stage dependency: {dependency}")
            self.record_stage_event(context, stage, "started")
            try:
                stage.run(context)
            except BaseException as error:
                self.record_stage_event(context, stage, "failed", error_type=type(error).__name__)
                raise
            context.completed_stages.add(stage.name)
            self.record_stage_event(context, stage, "complete")

    def record_stage_event(self, context, stage, state, **details):
        event = {"task_id": context.task["task_id"], "stage": stage.name, "state": state, **details}
        self.stage_events.append(event)
        if not self.artifacts.read_only:
            with self.artifacts.path("stage_events.jsonl").open("a") as event_file:
                event_file.write(json.dumps(event) + "\n")

    def freeze_inputs(self, contexts):
        input_hashes = {}
        for context in contexts:
            if "input_generation" not in context.completed_stages:
                raise RuntimeError("Cannot freeze inputs before generation completes")
            input_hashes[context.task["task_id"]] = digest(context.inputs)
        freeze = {
            "cohort_sha256": self.cohort_stage.cohort["cohort_sha256"],
            "inputs": input_hashes, "inputs_sha256": digest(input_hashes),
        }
        self.artifacts.write("generation_frozen.json", freeze)

    def verify_or_write_manifest(self, tasks, metadata):
        task_ids = []
        for task in tasks:
            task_ids.append(task["task_id"])
        if self.artifacts.read_only:
            if self.artifacts.exists("manifest.json"):
                raise ValueError("Archived experiment replay is not supported by this pipeline")
            if not self.artifacts.exists("modular_manifest.json"):
                raise FileNotFoundError("Read-only replay requires modular_manifest.json")
            if self.artifacts.exists("modular_manifest.json"):
                historical = self.artifacts.read("modular_manifest.json")
                if historical.get("protocol") != "input-generation-benchmark-v2":
                    raise ValueError("Modular replay protocol mismatch; use a new run directory")
                if historical["task_data_sha256"] != digest(tasks) or historical["settings"] != asdict(self.settings):
                    raise ValueError("Modular replay task/settings mismatch")
                selected_metadata = {task_id: metadata[task_id] for task_id in task_ids}
                if historical["metadata_sha256"] != digest(selected_metadata):
                    raise ValueError("Modular replay metadata mismatch")
                current_arms = []
                for arm in self.arms:
                    current_arms.append({"class": type(arm).__module__ + "." + type(arm).__qualname__,
                                         "name": arm.name, "configuration": arm.configuration()})
                if historical["arms"] != current_arms:
                    raise ValueError("Modular replay arms mismatch")
                if historical.get("input_generator") != self.generator_configuration():
                    raise ValueError("Modular replay input generator mismatch")
                current_stages = []
                for stage in self.generation_stages + self.evaluation_stages:
                    current_stages.append({"name": stage.name, "class": type(stage).__module__ + "." + type(stage).__qualname__,
                                           "configuration": stage.configuration()})
                if historical["stages"] != current_stages:
                    raise ValueError("Modular replay stages mismatch")
                for file_name, expected_hash in historical["sources"].items():
                    if hashlib.sha256(Path(file_name).read_bytes()).hexdigest() != expected_hash:
                        raise ValueError(f"Modular source changed: {file_name}")
                if historical["python"] != platform.python_version():
                    raise ValueError("Modular replay Python mismatch")
                for package_name, expected_version in historical["packages"].items():
                    if importlib.metadata.version(package_name) != expected_version:
                        raise ValueError(f"Modular dependency changed: {package_name}")
            return
        if self.artifacts.exists("manifest.json"):
            raise ValueError("Frozen historical run is read-only; use a new modular run directory")
        stages = []
        for stage in self.generation_stages + self.evaluation_stages:
            stages.append({"name": stage.name, "class": type(stage).__module__ + "." + type(stage).__qualname__,
                           "configuration": stage.configuration()})
        arm_classes = []
        for arm in self.arms:
            arm_classes.append({"class": type(arm).__module__ + "." + type(arm).__qualname__,
                                "name": arm.name, "configuration": arm.configuration()})
        selected_metadata = {}
        for task_id in task_ids:
            selected_metadata[task_id] = metadata[task_id]
        package_names = ["coverage", "numpy", "scipy", "evalplus", "langchain-openai",
                         "langchain-core", "openai", "httpx"]
        if any(getattr(arm, "measures_catalogue", False) for arm in self.arms):
            package_names.append("pydantic")
        package_names.extend(self.input_generator.runtime_dependencies())
        self.artifacts.write("modular_manifest.json", {
            "protocol": "input-generation-benchmark-v2", "tasks": task_ids,
            "cohort_sha256": self.cohort_stage.cohort["cohort_sha256"],
            "settings": asdict(self.settings), "stages": stages, "arms": arm_classes,
            "input_generator": self.generator_configuration(),
            "sources": self.source_hashes(), "metadata_sha256": digest(selected_metadata),
            "task_data_sha256": digest(tasks),
            "model": self.calls.model_id if self.calls is not None else None,
            "calls_backend": type(self.calls).__module__ + "." + type(self.calls).__qualname__,
            "python": platform.python_version(), "python_executable": str(Path(sys.executable).resolve()),
            "packages": {name: importlib.metadata.version(name) for name in package_names},
        })

    def source_hashes(self):
        source_paths = set()
        module_directory = Path(__file__).resolve().parent
        for source_path in module_directory.rglob("*.py"):
            if "tests" not in source_path.parts:
                source_paths.add(source_path)
        final_directory = module_directory.parent
        source_paths.update((final_directory / "models").glob("*.py"))
        source_paths.update((final_directory / "runtime").glob("*.py"))
        source_paths.add(final_directory.parent / "data/humaneval.jsonl")
        source_paths.add(final_directory.parent / "data/contracts.json")
        for stage in self.generation_stages + self.evaluation_stages:
            source_paths.update(stage.source_dependencies())
        source_paths.update(self.input_generator.source_dependencies())
        dependencies = list(self.input_generator.dependency_objects())
        for instance in self.generation_stages + self.evaluation_stages + [self.input_generator] + dependencies:
            source_paths.add(Path(inspect.getfile(type(instance))).resolve())
        if self.calls is not None:
            source_paths.add(Path(inspect.getfile(type(self.calls))).resolve())
            if hasattr(self.calls, "model"):
                source_paths.add(Path(inspect.getfile(type(self.calls.model))).resolve())
        result = {}
        for source_path in sorted(source_paths):
            result[str(source_path)] = hashlib.sha256(source_path.read_bytes()).hexdigest()
        return result

    def generator_configuration(self):
        return {"class": type(self.input_generator).__module__ + "." + type(self.input_generator).__qualname__,
                "configuration": self.input_generator.configuration()}

    @contextmanager
    def run_lock(self):
        if self.artifacts.read_only:
            lock_path = self.artifacts.path(".run.lock")
            if not lock_path.exists():
                raise FileNotFoundError("Read-only replay requires the run lock file")
            lock_file = lock_path.open("r")
            lock_mode = fcntl.LOCK_SH
        else:
            self.artifacts.directory.mkdir(parents=True, exist_ok=True)
            lock_file = self.artifacts.path(".run.lock").open("a+")
            lock_mode = fcntl.LOCK_EX
        with lock_file:
            fcntl.flock(lock_file, lock_mode | fcntl.LOCK_NB)
            yield
