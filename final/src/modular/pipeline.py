"""Orchestrate replaceable stages and enforce the generation-before-oracle barrier."""
from __future__ import annotations

import fcntl
import importlib.metadata
import platform
import sys
import json
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path

from .generators import InputGenerator, default_input_generator, generator_for_arms
from .artifacts import ArtifactStore
from .calls import CachedModelCalls
from .execution_cache import InputExecutionCache
from .references import HumanEvalPlusReferencePrograms
from .context import PipelineSettings, TaskContext
from .stages.frozen_cohort import FrozenCohortStage
from .stages.input_generation import InputGenerationStage
from .stages.reference_oracle import ReferenceOracleStage
from .stages.put_evaluation import PutEvaluationStage
from .stages.reporting import ReportingStage


class BenchmarkPipeline:

    def __init__(
        self,
        cohort_path: Path,
        artifacts: ArtifactStore,
        *,
        arms=None,
        settings: PipelineSettings | None = None,
        calls=None,
        input_generator: InputGenerator | None = None,
        execution_cache=None,
        reference_programs=None,
    ):
        self.artifacts = artifacts
        self.settings = settings or PipelineSettings()
        if input_generator is not None and arms is not None:
            raise ValueError("Inject input_generator or supply arms, not both")
        if input_generator is None:
            input_generator = (
                default_input_generator() if arms is None else generator_for_arms(arms)
            )
        self.input_generator = input_generator
        # Input methods exposed for configuration and reporting.
        self.arms = tuple(getattr(input_generator, "methods", ()))
        self.calls = calls
        if (
            self.artifacts.read_only
            and calls is not None
            and not isinstance(calls, CachedModelCalls)
        ):
            raise ValueError("Read-only replay only accepts cached model calls")
        if self.artifacts.read_only and calls is None:
            self.calls = CachedModelCalls(artifacts)
        self.cohort_stage = FrozenCohortStage(cohort_path)
        self.reporting_stage = input_generator.reporting_stage() or ReportingStage()
        self.generation_stages = [
            self.cohort_stage,
            *input_generator.preparation_stages(),
            InputGenerationStage(input_generator),
        ]
        if execution_cache is None and input_generator.cache_input_execution:
            execution_cache = InputExecutionCache(
                artifacts.directory.parent / "execution_cache",
                read_only=artifacts.read_only,
            )
        self.execution_cache = None if execution_cache is False else execution_cache
        if reference_programs is None:
            reference_programs = HumanEvalPlusReferencePrograms()
        self.reference_programs = reference_programs
        self.evaluation_stages = [
            ReferenceOracleStage(self.execution_cache, reference_programs),
            *input_generator.post_reference_stages(),
            PutEvaluationStage(self.execution_cache),
            *input_generator.post_evaluation_stages(
                self.execution_cache, reference_programs
            ),
            self.reporting_stage,
        ]
        self.stage_events = []

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
        if self.artifacts.read_only:
            return self.reporting_stage.summarize_saved(self.artifacts, [task["task_id"] for task in tasks])
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
            self.write_manifest(tasks, metadata)
            contexts = []
            for task in tasks:
                context = TaskContext(task, metadata[task["task_id"]], self.artifacts, self.settings, self.calls)
                contexts.append(context)
                self.execute_stages(self.generation_stages, context)
            self.input_generator.validate_generation(contexts)
            for context in contexts:
                self.execute_stages(self.evaluation_stages, context)
            summary = self.reporting_stage.build_summary(contexts, self.cohort_stage.cohort)
            self.input_generator.extend_summary(contexts, summary, self.reporting_stage)
            self.artifacts.write_metadata("modular_summary.json", summary)
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

    def write_manifest(self, tasks, metadata):
        task_ids = []
        for task in tasks:
            task_ids.append(task["task_id"])
        if self.artifacts.exists("manifest.json"):
            raise ValueError("Legacy experiment directory is unsupported; use a new modular run directory")
        if self.artifacts.read_only:
            return
        stages = []
        for stage in self.generation_stages + self.evaluation_stages:
            stages.append({"name": stage.name, "class": type(stage).__module__ + "." + type(stage).__qualname__,
                           "configuration": stage.configuration()})
        arm_classes = []
        for arm in self.arms:
            arm_classes.append({"class": type(arm).__module__ + "." + type(arm).__qualname__,
                                "name": arm.name, "configuration": arm.configuration()})
        package_names = ["coverage", "numpy", "scipy", "evalplus", "langchain-openai",
                         "langchain-core", "openai", "httpx"]
        if any(getattr(arm, "measures_catalogue", False) for arm in self.arms):
            package_names.append("pydantic")
        package_names.extend(self.input_generator.runtime_dependencies())
        model = getattr(self.calls, "model", None)
        package_names.extend(getattr(model, "runtime_dependencies", lambda: ())())
        self.artifacts.write_metadata("modular_manifest.json", {
            "tasks": task_ids,
            "settings": asdict(self.settings), "stages": stages, "arms": arm_classes,
            "input_generator": self.generator_configuration(),
            "model": self.calls.model_id if self.calls is not None else None,
            "calls_backend": type(self.calls).__module__ + "." + type(self.calls).__qualname__,
            "python": platform.python_version(), "python_executable": str(Path(sys.executable).resolve()),
            "packages": {name: importlib.metadata.version(name) for name in package_names},
        })

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
