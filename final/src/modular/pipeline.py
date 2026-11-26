"""Orchestrate generation-before-oracle evaluation on a frozen PUT cohort."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from contextlib import contextmanager
from dataclasses import asdict
import fcntl
import importlib.metadata
import os
from pathlib import Path
import platform
import sys
import threading
import time

from .black_box import StructuredCatalogueArm, measure_task_catalogues
from .artifacts import ArtifactStore
from .catalogue_reporting import CatalogueReporter
from .cohort import load_cohort
from .context import PipelineSettings, TaskContext
from . import default_arms
from .generators import InputGenerator, MethodInputGenerator
from .input_contract import validate_generated_inputs
from .put_evaluation import evaluate_puts
from .reference_oracle import run_reference_oracle
from .references import HumanEvalPlusReferencePrograms
from .reporting import Reporter
from .spec_obligation import RepairedControlFlowObligationArm
from .pynguin.adapter import PynguinInputGenerator
from .tool_sampling.generator import ToolInputGenerator
from .tool_sampling.reporting import ToolReporter


def generate_task_inputs(context: TaskContext, input_generator: InputGenerator) -> dict:
    """Load saved inputs or generate, validate, and persist inputs.json for one task."""
    path = context.task_directory + "/inputs.json"
    use_saved_inputs = context.artifacts.read_only or context.artifacts.exists(path)
    if use_saved_inputs:
        result = context.artifacts.read(path)
    else:
        result = input_generator.generate(context)

    validate_generated_inputs(result, task_id=context.task['task_id'])

    if not use_saved_inputs:
        context.artifacts.write(path, result)
        # Keep the JSON representation consumed by reference execution.
        result = context.artifacts.read(path)
    context.inputs = result
    return result


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
        tool_config: dict | None = None,
        pynguin_settings=None,
        reference_programs=None,
        dataset=None,
        native_lock: Path | None = None,
        on_step=None,
        generation_workers: int = 1,
    ):
        self.artifacts = artifacts
        self.settings = settings or PipelineSettings()
        if sum(option is not None for option in (arms, input_generator, tool_config, pynguin_settings)) > 1:
            raise ValueError('Choose one input source')
        if tool_config is not None:
            input_generator = ToolInputGenerator(
                tool_config.get('budgets'),
                preparations=tool_config.get('preparations'),
                semantic_controls=tool_config.get('semantic_controls'),
            )
        elif pynguin_settings is not None:
            input_generator = PynguinInputGenerator(pynguin_settings)
        elif input_generator is None:
            input_generator = MethodInputGenerator(default_arms() if arms is None else arms)
        self.input_generator = input_generator
        # Input methods exposed for configuration and reporting.
        self.arms = tuple(input_generator.methods)
        self.catalogue_arms = tuple(arm.name for arm in self.arms if isinstance(arm, StructuredCatalogueArm))
        self.tool_sampling = input_generator if isinstance(input_generator, ToolInputGenerator) else None
        self.pynguin = input_generator if isinstance(input_generator, PynguinInputGenerator) else None
        self.calls = None if artifacts.read_only else calls
        self.cohort_path = Path(cohort_path).resolve()
        self.cohort = load_cohort(self.cohort_path)
        self.cohort_tasks = {row["task_id"]: row for row in self.cohort["tasks"]}
        self.dataset = dataset
        if reference_programs is not None:
            self.reference_programs = reference_programs
        elif dataset is not None:
            self.reference_programs = dataset.load_reference_programs()
        else:
            self.reference_programs = HumanEvalPlusReferencePrograms()
        if self.tool_sampling is not None:
            self.reporter = ToolReporter()
        elif self.catalogue_arms or self.pynguin is not None:
            self.reporter = CatalogueReporter()
        else:
            self.reporter = Reporter()
        self.native_lock = native_lock
        self.on_step = on_step
        self.generation_workers = max(1, int(generation_workers))
        self._event_lock = threading.Lock()
        self.stage_events = []
        self.completed_tasks = Counter()

    def _needs_input_context(self) -> bool:
        if isinstance(self.input_generator, MethodInputGenerator):
            return self.input_generator.prepare_packet
        if self.tool_sampling is not None or self.pynguin is not None:
            return True
        # Compatibility for saved-input audit scripts with packet receipts.
        return type(self.input_generator).prepare_context is not InputGenerator.prepare_context

    def _record_event(self, context: TaskContext, name: str, state: str, **details) -> None:
        event = {"task_id": context.task["task_id"], "stage": name, "state": state, **details}
        with self._event_lock:
            self.stage_events.append(event)
            if self.native_lock is not None and state == 'complete' and name in ('input_generation', 'put_evaluation'):
                self.completed_tasks[name] += 1
                self.artifacts.write_metadata('progress.json', {
                    **event,
                    'generated_tasks': self.completed_tasks['input_generation'],
                    'evaluated_tasks': self.completed_tasks['put_evaluation'],
                    'total_tasks': self.total_tasks,
                    'updated_utc': time.time(),
                })
            if self.on_step is not None:
                self.on_step(context, name, state)

    def _run_step(self, context: TaskContext, name: str, action):
        self._record_event(context, name, "started")
        try:
            result = action()
        except BaseException as error:
            self._record_event(context, name, "failed", error_type=type(error).__name__)
            raise
        self._record_event(context, name, "complete")
        return result

    def run(self, tasks: list[dict] | None = None, metadata: dict | None = None) -> dict:
        if tasks is None:
            if self.dataset is None:
                raise ValueError("Tasks must be supplied when no dataset loader is configured")
            tasks = self.dataset.load_tasks()
        if metadata is None:
            if self.dataset is None:
                raise ValueError("Metadata must be supplied when no dataset loader is configured")
            metadata = self.dataset.load_metadata()
        if self.artifacts.read_only:
            # Rebuild the summary from saved results for the requested task IDs.
            return self.reporter.summarize_saved(self.artifacts, [task["task_id"] for task in tasks])

        needs_input_context = self._needs_input_context()
        with self.run_lock(), self.native_execution_lock('generation' if self.pynguin is not None else None):
            self.total_tasks = len(tasks)
            self.completed_tasks.clear()
            self.write_manifest(tasks)
            contexts = []
            for task in tasks:
                context = TaskContext(task, metadata[task["task_id"]], self.artifacts, self.settings, self.calls)
                context.cohort_task = self.cohort_tasks[task["task_id"]]
                contexts.append(context)

            def _generate_one(ctx):
                if needs_input_context:
                    self._run_step(ctx, "input_context", lambda c=ctx: self.input_generator.prepare_context(c))
                self._run_step(ctx, "input_generation", lambda c=ctx: generate_task_inputs(c, self.input_generator))

            self.set_run_phase('generation')
            if self.generation_workers > 1 and len(contexts) > 1:
                with ThreadPoolExecutor(max_workers=self.generation_workers) as pool:
                    futures = [pool.submit(_generate_one, ctx) for ctx in contexts]
                    for future in futures:
                        future.result()
            else:
                for ctx in contexts:
                    _generate_one(ctx)
            # Finish generation for every task before any oracle or PUT receives the inputs.
            if self.tool_sampling is not None:
                self.tool_sampling.validate_generation(contexts)
            if self.pynguin is not None:
                self.pynguin.validate_generation(contexts)
            with self.native_execution_lock('evaluation' if self.pynguin is None else None):
                self.set_run_phase('evaluation')
                for context in contexts:
                    self.evaluate_task(context)
            summary = self.reporter.build_summary(contexts, self.cohort)
            self.input_generator.extend_summary(contexts, summary, self.reporter)
            self.artifacts.write_metadata("modular_summary.json", summary)
            report_text = self.reporter.render(summary)
            for arm in self.arms:
                if isinstance(arm, RepairedControlFlowObligationArm):
                    report_text += arm.render_summary(summary)
            self.artifacts.path("REPORT.md").write_text(report_text)
            return summary

    def evaluate_task(self, context):
        self._run_step(
            context,
            'reference_oracle',
            lambda: run_reference_oracle(
                context,
                reference_programs=self.reference_programs,
            ),
        )
        if self.catalogue_arms:
            self._run_step(
                context,
                'catalogue_measurement',
                lambda: measure_task_catalogues(context, self.catalogue_arms),
            )
        self._run_step(
            context,
            'put_evaluation',
            lambda: evaluate_puts(context),
        )
        if self.tool_sampling is not None:
            self._run_step(
                context,
                'tool_selection_audit',
                lambda: self.tool_sampling.post_evaluation(
                    context,
                    self.reference_programs,
                ),
            )

    @contextmanager
    def native_execution_lock(self, phase):
        if phase is None or self.native_lock is None:
            yield
            return
        self.set_run_phase(phase, state='waiting_native_lock')
        with self.native_lock.open('a+') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield

    def set_run_phase(self, phase, *, state='running'):
        if self.native_lock is not None:
            self.artifacts.write_metadata('status.json', {
                'state': state,
                'phase': phase,
                'pid': os.getpid(),
                'updated_utc': time.time(),
            })

    def write_manifest(self, tasks):
        task_ids = [task["task_id"] for task in tasks]
        if self.artifacts.exists("manifest.json"):
            raise ValueError("Legacy experiment directory is unsupported; use a new modular run directory")
        if self.artifacts.read_only:
            return
        stages = []
        if self._needs_input_context():
            stages.append({
                "name": "input_context",
                "configuration": {"methods": [arm.name for arm in self.arms]},
            })
        stages.append({"name": "input_generation"})
        reference_config = {"reference_programs": self.reference_programs.configuration()}
        stages.append({"name": "reference_oracle", "configuration": reference_config})
        if self.catalogue_arms:
            stages.append({"name": "catalogue_measurement", "configuration": {"arms": list(self.catalogue_arms)}})
        put_config = {"scorer": self.settings.scorer}
        if self.settings.scorer == "confirm_first_failures":
            put_config["unstable_scope"] = "retested-inputs"
        stages.append({"name": "put_evaluation", "configuration": put_config})
        if self.tool_sampling is not None:
            stages.append({"name": "tool_selection_audit"})
        stages.append({
            "name": "reporting",
            "class": type(self.reporter).__module__ + "." + type(self.reporter).__qualname__,
            "configuration": {},
        })

        arm_classes = [
            {
                "class": type(arm).__module__ + "." + type(arm).__qualname__,
                "name": arm.name,
                "configuration": arm.configuration(),
            }
            for arm in self.arms
        ]
        package_names = [
            "coverage", "numpy", "scipy", "evalplus", "langchain-openai",
            "langchain-core", "openai", "httpx",
        ]
        if self.catalogue_arms:
            package_names.append("pydantic")
        package_names.extend(self.input_generator.runtime_dependencies())
        model = getattr(self.calls, "model", None)
        package_names.extend(getattr(model, "runtime_dependencies", lambda: ())())
        self.artifacts.write_metadata("modular_manifest.json", {
            "tasks": task_ids,
            "settings": asdict(self.settings),
            "stages": stages,
            "arms": arm_classes,
            "input_generator": self.generator_configuration(),
            "model": self.calls.model_id if self.calls is not None else None,
            "calls_backend": type(self.calls).__module__ + "." + type(self.calls).__qualname__,
            "python": platform.python_version(),
            "python_executable": str(Path(sys.executable).resolve()),
            "packages": {name: importlib.metadata.version(name) for name in package_names},
        })

    def generator_configuration(self):
        return {
            "class": type(self.input_generator).__module__ + "." + type(self.input_generator).__qualname__,
            "configuration": self.input_generator.configuration(),
        }

    @contextmanager
    def run_lock(self):
        if self.artifacts.read_only:
            raise ValueError("Run lock requires a writable artifact store")
        self.artifacts.directory.mkdir(parents=True, exist_ok=True)
        with self.artifacts.path(".run.lock").open("a+") as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield
