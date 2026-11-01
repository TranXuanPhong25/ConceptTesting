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

from final.pipeline import digest
from .arms import default_arms
from .arms.toolinput import ToolInputArm
from .artifacts import ArtifactStore
from .calls import CachedModelCalls
from .context import PipelineSettings, TaskContext
from .stages.base import PipelineStage
from .stages.frozen_cohort import FrozenCohortStage
from .stages.concept_analysis import ConceptAnalysisStage
from .stages.witness_sampling import WitnessSamplingStage
from .stages.input_generation import InputGenerationStage
from .stages.reference_oracle import ReferenceOracleStage
from .stages.put_evaluation import PutEvaluationStage
from .stages.reporting import ReportingStage


class BenchmarkPipeline:
    def __init__(self, cohort_path: Path, artifacts: ArtifactStore, *, arms=None,
                 settings: PipelineSettings | None = None, calls=None):
        self.artifacts = artifacts
        self.settings = settings or PipelineSettings()
        self.arms = tuple(default_arms() if arms is None else arms)
        self.validate_arm_names()
        self.calls = calls
        if self.artifacts.read_only and calls is not None and not isinstance(calls, CachedModelCalls):
            raise ValueError("Read-only replay only accepts cached model calls")
        if self.artifacts.read_only and calls is None:
            self.calls = CachedModelCalls(artifacts)
        self.cohort_stage = FrozenCohortStage(cohort_path)
        self.reporting_stage = ReportingStage()
        self.generation_stages = [
            self.cohort_stage, ConceptAnalysisStage(self.arms),
            WitnessSamplingStage(ToolInputArm()), InputGenerationStage(self.arms),
        ]
        self.evaluation_stages = [ReferenceOracleStage(), PutEvaluationStage(), self.reporting_stage]
        self.stage_events = []

    def validate_arm_names(self):
        names = set()
        for arm in self.arms:
            if not arm.name or not arm.name.replace("_", "").isalnum() or arm.name in names:
                raise ValueError("Arm names must be unique nonempty identifiers")
            names.add(arm.name)
        if not names:
            raise ValueError("At least one arm is required")

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
            if self.artifacts.read_only and self.artifacts.exists("summary.json"):
                historical_summary = self.artifacts.read("summary.json")
                if historical_summary != summary:
                    raise ValueError("Historical summary mismatch")
            else:
                self.artifacts.write("modular_summary.json", summary)
            if not self.artifacts.read_only:
                self.artifacts.path("REPORT.md").write_text(self.reporting_stage.render(summary))
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
            # Replay accepts exactly the original task set and its registered budgets.
            if self.artifacts.exists("manifest.json"):
                if self.settings != PipelineSettings():
                    raise ValueError("Historical replay requires the original protocol settings")
                historical = self.artifacts.read("manifest.json")
                if historical["tasks"] != task_ids:
                    raise ValueError("Replay requires the original task set in original order")
                if historical["arms"] != [arm.name for arm in self.arms]:
                    raise ValueError("Replay requires the original arms in original order")
                historical_fields = {
                    "inputs_per_arm": self.settings.input_budget,
                    "input_temperature": self.settings.input_temperature,
                    "input_max_tokens": self.settings.input_tokens,
                }
                for field_name, expected_value in historical_fields.items():
                    if historical[field_name] != expected_value:
                        raise ValueError(f"Replay setting mismatch: {field_name}")
                final_directory = Path(__file__).resolve().parents[1]
                for relative_path, expected_hash in historical["sources"].items():
                    source_path = Path(relative_path)
                    if not source_path.is_absolute():
                        source_path = final_directory / source_path
                    if hashlib.sha256(source_path.read_bytes()).hexdigest() != expected_hash:
                        raise ValueError(f"Historical source changed: {relative_path}")
                metadata_path = final_directory / "experiments/concept_reference_v1/data/contracts.json"
                if hashlib.sha256(metadata_path.read_bytes()).hexdigest() != historical["contracts_sha256"]:
                    raise ValueError("Historical contract metadata checksum mismatch")
                import json
                historical_metadata = json.loads(metadata_path.read_text())
                for task_id in task_ids:
                    if metadata[task_id] != historical_metadata[task_id]:
                        raise ValueError(f"Replay metadata changed: {task_id}")
                from final.run import load_tasks
                historical_tasks = {}
                for task in load_tasks():
                    historical_tasks[task["task_id"]] = task
                for task in tasks:
                    if task != historical_tasks[task["task_id"]]:
                        raise ValueError(f"Replay task definition changed: {task['task_id']}")
                if historical["python"] != platform.python_version():
                    raise ValueError("Historical Python version mismatch")
                for package_name, package_version in historical["packages"].items():
                    if importlib.metadata.version(package_name) != package_version:
                        raise ValueError(f"Historical dependency version mismatch: {package_name}")
            elif self.artifacts.exists("modular_manifest.json"):
                historical = self.artifacts.read("modular_manifest.json")
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
        self.artifacts.write("modular_manifest.json", {
            "protocol": "class-based-refactor-v1", "tasks": task_ids,
            "cohort_sha256": self.cohort_stage.cohort["cohort_sha256"],
            "settings": asdict(self.settings), "stages": stages, "arms": arm_classes,
            "sources": self.source_hashes(), "metadata_sha256": digest(selected_metadata),
            "task_data_sha256": digest(tasks),
            "model": self.calls.model_id if self.calls is not None else None,
            "calls_backend": type(self.calls).__module__ + "." + type(self.calls).__qualname__,
            "python": platform.python_version(), "python_executable": str(Path(sys.executable).resolve()),
            "packages": {name: importlib.metadata.version(name) for name in
                         ("python-graphs", "networkx", "coverage", "hypothesis", "numpy", "scipy", "evalplus")},
        })

    def source_hashes(self):
        source_paths = set()
        module_directory = Path(__file__).resolve().parent
        for source_path in module_directory.rglob("*.py"):
            if "tests" not in source_path.parts:
                source_paths.add(source_path)
        final_directory = module_directory.parent
        for file_name in ("core_model.py", "contracts.py", "pipeline.py", "prompts.py", "run.py"):
            source_paths.add(final_directory / file_name)
        for folder_name in ("concept_reference_v1", "concept_reference_v1_recovery"):
            for source_path in (final_directory / "experiments" / folder_name).glob("*.py"):
                source_paths.add(source_path)
        for instance in self.generation_stages + self.evaluation_stages + list(self.arms):
            source_paths.add(Path(inspect.getfile(type(instance))).resolve())
        if self.calls is not None:
            source_paths.add(Path(inspect.getfile(type(self.calls))).resolve())
            if hasattr(self.calls, "model"):
                source_paths.add(Path(inspect.getfile(type(self.calls.model))).resolve())
        result = {}
        for source_path in sorted(source_paths):
            result[str(source_path)] = hashlib.sha256(source_path.read_bytes()).hexdigest()
        return result

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
