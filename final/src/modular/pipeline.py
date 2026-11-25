"""Orchestrate generation-before-oracle evaluation on a frozen PUT cohort."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import asdict
import fcntl
import importlib.metadata
import json
from pathlib import Path
import platform
import sys
import threading

from .artifacts import ArtifactStore
from .calls import CachedModelCalls
from .cohort import load_cohort
from .context import PipelineSettings, TaskContext
from .execution_cache import InputExecutionCache
from .generators import InputGenerator, MethodInputGenerator, default_input_generator, generator_for_arms
from .input_contract import validate_generated_inputs
from .put_evaluation import evaluate_puts
from .reference_oracle import run_reference_oracle
from .references import HumanEvalPlusReferencePrograms
from .reporting import Reporter


def generate_task_inputs(context: TaskContext, input_generator: InputGenerator) -> dict:
    """Load saved inputs or generate, validate, and persist inputs.json for one task."""
    path = context.task_directory + "/inputs.json"
    use_saved_inputs = context.artifacts.read_only or context.artifacts.exists(path)
    if use_saved_inputs:
        result = context.artifacts.read(path)
    else:
        result = input_generator.generate(context)

    validate_generated_inputs(result, task_id=context.task["task_id"], input_budget=context.settings.input_budget)

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
        execution_cache=None,
        reference_programs=None,
        dataset=None,
        on_before_evaluation=None,
        on_step=None,
        generation_workers: int = 1,
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
        self.calls = CachedModelCalls(artifacts) if artifacts.read_only else calls
        self.cohort_path = Path(cohort_path).resolve()
        self.cohort = load_cohort(self.cohort_path)
        self.cohort_tasks = {row["task_id"]: row for row in self.cohort["tasks"]}
        if execution_cache is None and input_generator.cache_input_execution:
            execution_cache = InputExecutionCache(
                artifacts.directory.parent / "execution_cache",
                read_only=artifacts.read_only,
            )
        self.execution_cache = None if execution_cache is False else execution_cache
        self.dataset = dataset
        if reference_programs is not None:
            self.reference_programs = reference_programs
        elif dataset is not None:
            self.reference_programs = dataset.load_reference_programs()
        else:
            self.reference_programs = HumanEvalPlusReferencePrograms()
        self.reporter = input_generator.reporter() or Reporter()
        self.on_before_evaluation = on_before_evaluation
        self.on_step = on_step
        self.generation_workers = max(1, int(generation_workers))
        self._event_lock = threading.Lock()
        self.stage_events = []

    def _needs_input_context(self) -> bool:
        return (
            type(self.input_generator).prepare_context is not InputGenerator.prepare_context
            and getattr(self.input_generator, "prepare_packet", True)
        )

    def _post_reference_step(self) -> str | None:
        has_catalogue_arms = any(getattr(arm, "measures_catalogue", False) for arm in self.arms)
        if isinstance(self.input_generator, MethodInputGenerator):
            return "catalogue_measurement" if has_catalogue_arms else None
        if type(self.input_generator).post_reference is not InputGenerator.post_reference:
            return "catalogue_measurement" if has_catalogue_arms else "post_reference"
        return None

    def _post_evaluation_step(self) -> str | None:
        if type(self.input_generator).post_evaluation is not InputGenerator.post_evaluation:
            if type(self.input_generator).__name__ == "ToolInputGenerator":
                return "tool_selection_audit"
            return "post_evaluation"
        return None

    def _generate_task(self, context: TaskContext) -> dict:
        return generate_task_inputs(context, self.input_generator)

    def _record_event(self, context: TaskContext, name: str, state: str, **details) -> None:
        event = {"task_id": context.task["task_id"], "stage": name, "state": state, **details}
        with self._event_lock:
            self.stage_events.append(event)
            if not self.artifacts.read_only:
                with self.artifacts.path("stage_events.jsonl").open("a") as event_file:
                    event_file.write(json.dumps(event) + "\n")
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
        post_ref_name = self._post_reference_step()
        post_eval_name = self._post_evaluation_step()
        with self.run_lock():
            self.write_manifest(tasks, metadata)
            contexts = []
            for task in tasks:
                context = TaskContext(task, metadata[task["task_id"]], self.artifacts, self.settings, self.calls)
                context.cohort_task = self.cohort_tasks[task["task_id"]]
                contexts.append(context)

            def _generate_one(ctx):
                if needs_input_context:
                    self._run_step(ctx, "input_context", lambda c=ctx: self.input_generator.prepare_context(c))
                self._run_step(ctx, "input_generation", lambda c=ctx: self._generate_task(c))

            if self.generation_workers > 1 and len(contexts) > 1:
                with ThreadPoolExecutor(max_workers=self.generation_workers) as pool:
                    futures = [pool.submit(_generate_one, ctx) for ctx in contexts]
                    for future in futures:
                        future.result()
            else:
                for ctx in contexts:
                    _generate_one(ctx)
            # Finish generation for every task before any oracle or PUT receives the inputs.
            self.input_generator.validate_generation(contexts)
            if self.on_before_evaluation is not None:
                self.on_before_evaluation()
            for context in contexts:
                self._run_step(
                    context,
                    "reference_oracle",
                    lambda ctx=context: run_reference_oracle(
                        ctx,
                        execution_cache=self.execution_cache,
                        reference_programs=self.reference_programs,
                    ),
                )
                if post_ref_name is not None:
                    self._run_step(
                        context,
                        post_ref_name,
                        lambda ctx=context: self.input_generator.post_reference(ctx),
                    )
                self._run_step(
                    context,
                    "put_evaluation",
                    lambda ctx=context: evaluate_puts(ctx, execution_cache=self.execution_cache),
                )
                if post_eval_name is not None:
                    self._run_step(
                        context,
                        post_eval_name,
                        lambda ctx=context: self.input_generator.post_evaluation(
                            ctx, self.execution_cache, self.reference_programs
                        ),
                    )
            summary = self.reporter.build_summary(contexts, self.cohort)
            self.input_generator.extend_summary(contexts, summary, self.reporter)
            self.artifacts.write_metadata("modular_summary.json", summary)
            report_text = self.reporter.render(summary)
            self.artifacts.path("REPORT.md").write_text(report_text)
            return summary

    def write_manifest(self, tasks, metadata=None):
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
        stages.append({
            "name": "input_generation",
            "configuration": self.generator_configuration(),
        })
        reference_config = {"reference_programs": self.reference_programs.configuration()}
        if self.execution_cache is not None:
            reference_config["execution_cache"] = self.execution_cache.configuration()
        stages.append({"name": "reference_oracle", "configuration": reference_config})
        post_ref_name = self._post_reference_step()
        if post_ref_name is not None:
            post_ref_config = (
                {"arms": [arm.name for arm in self.arms if getattr(arm, "measures_catalogue", False)]}
                if post_ref_name == "catalogue_measurement"
                else {}
            )
            stages.append({"name": post_ref_name, "configuration": post_ref_config})
        put_config = {"scorer": self.settings.scorer}
        if self.settings.scorer == "confirm_first_failures":
            put_config["unstable_scope"] = "retested-inputs"
        if self.execution_cache is not None:
            put_config["execution_cache"] = self.execution_cache.configuration()
        stages.append({"name": "put_evaluation", "configuration": put_config})
        post_eval_name = self._post_evaluation_step()
        if post_eval_name is not None:
            post_eval_config = (
                {
                    "audit_cap": self.input_generator.config["audit_cap"],
                    "random_seeds": self.input_generator.config["random_seeds"],
                    "reference": self.reference_programs.configuration(),
                }
                if post_eval_name == "tool_selection_audit"
                else {}
            )
            stages.append({"name": post_eval_name, "configuration": post_eval_config})
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
        if any(getattr(arm, "measures_catalogue", False) for arm in self.arms):
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
