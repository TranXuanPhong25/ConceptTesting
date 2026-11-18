"""Readable entry point. Replay is the safe default and never creates a model."""
import argparse
import json
import os
import time
from contextlib import nullcontext, contextmanager
from pathlib import Path

from final.src.benchmarks.datasets import DatasetLoader
from .artifacts import ArtifactStore
from .calls import RecordedModelCalls
from .pipeline import BenchmarkPipeline
from .context import PipelineSettings
from .execution_cache import InputExecutionCache
from .arms import available_arms, default_arms, selected_arms
from final.src.runtime.artifacts import save


def positive_integer(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("Expected a positive integer")
    return number


@contextmanager
def pynguin_native_lock():
    import fcntl
    path = Path(__file__).resolve().parents[2] / 'out/.boundary_native.lock'
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def load_options(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("replay", "run"), default="replay")
    parser.add_argument("--cohort", type=Path, default=Path("final/out/cohorts/qwen35_27b_humaneval164/cohort.json"))
    parser.add_argument("--artifacts", type=Path, default=Path("final/out/modular_pipeline"))
    parser.add_argument("--arms", nargs="+", choices=[arm.name for arm in available_arms()],
                        help="Input methods: plain (default), boundary (soft BVA), or catalogue testing arms")
    parser.add_argument("--input-tokens", type=positive_integer,
                        help="Completion tokens/call; default 4096 with catalogue arms, otherwise 2048")
    parser.add_argument("--context-tokens", type=positive_integer, default=8192)
    parser.add_argument("--model-backend", choices=("qwen", "vertex"),
                        help="Live transport; defaults to FINAL_MODEL_BACKEND or existing Qwen backend")
    parser.add_argument("--model-name", help="Model ID for the selected live backend")
    parser.add_argument("--catalogue-off", action="store_true", help="Instruction-only ablation for catalogue arms")
    parser.add_argument("--tool-config", type=Path,
                        help="Opt-in tool pipeline JSON: {budgets: {...}, preparations: optional task map}")
    parser.add_argument("--pynguin-config", type=Path, help="Opt-in PynguinSettings JSON; upstream input baseline")
    parser.add_argument("--task-ids", nargs="+", help="Explicit subset, e.g. HumanEval/0 HumanEval/18")
    parser.add_argument("--target-programs", type=positive_integer, default=10,
                        help="Expected frozen programs per task; use 1 for representative smoke cohorts")
    parser.add_argument("--input-budget", type=positive_integer, default=20,
                        help="Total input budget per arm per task, including the boundary arm")
    parser.add_argument("--execution-cache", type=Path, default=Path("final/out/execution_cache"),
                        help="Shared per-input reference/PUT execution cache")
    parser.add_argument("--no-execution-cache", action="store_true", help="Use the original batch execution without shared input caching")
    options = parser.parse_args(arguments)
    return parser, options


def load_pipeline_settings(parser, options):
    if options.pynguin_config and (options.tool_config or options.arms or options.catalogue_off):
        parser.error('--pynguin-config cannot be combined with other generator options')
    tool_generator = None
    if options.pynguin_config:
        from .pynguin.config import PynguinSettings
        pynguin_settings = PynguinSettings(**json.loads(options.pynguin_config.read_text()))
        if options.input_budget > 20:
            parser.error('Pynguin requires --input-budget <=20')
        from .pynguin.adapter import PynguinInputGenerator
        tool_generator = PynguinInputGenerator(pynguin_settings)
    if options.tool_config:
        if options.arms or options.catalogue_off:
            parser.error("--tool-config cannot be combined with --arms or --catalogue-off")
        from .generators.tools import ToolInputGenerator
        document = json.loads(options.tool_config.read_text())
        if not isinstance(document, dict) or set(document) - {"budgets", "preparations", "semantic_controls"}:
            parser.error("Tool config accepts budgets, optional preparations and semantic_controls only")
        tool_generator = ToolInputGenerator(document.get("budgets"), preparations=document.get("preparations"),
                                           semantic_controls=document.get("semantic_controls"))
    arms = selected_arms(options.arms) if options.arms else default_arms()
    if options.catalogue_off:
        from .arms.classical import CatalogueSettings
        arms = tuple(type(arm)(CatalogueSettings(catalogue=False)) if getattr(arm, "measures_catalogue", False)
                     else arm for arm in arms)
    input_tokens = options.input_tokens or max(
        4096 if tool_generator or any(getattr(arm, "measures_catalogue", False) for arm in arms) else 2048,
        *(getattr(arm, 'default_input_tokens', 2048) for arm in arms))
    if input_tokens + 128 >= options.context_tokens:
        parser.error("Completion reserve must leave prompt context")
    settings = PipelineSettings(target_programs=options.target_programs, input_budget=options.input_budget,
                                input_tokens=input_tokens, context_tokens=options.context_tokens)
    if options.pynguin_config:
        pynguin_settings.validate_environment()
    return settings, arms, tool_generator


def construct_pipeline(parser, options, artifacts, settings, arms, tool_generator):
    calls = None
    model = None
    # New experiments must have their own directory. Never modify a frozen v1 run.
    if artifacts.exists("manifest.json") or (artifacts.exists("status.json") and not artifacts.exists("modular_manifest.json")):
        parser.error("Use a new --artifacts directory for a modular run")
    if tool_generator is None:
        requires_model = any(arm.uses_model for arm in arms)
    elif hasattr(tool_generator, "requires_model"):
        requires_model = tool_generator.requires_model
    else:
        requires_model = getattr(tool_generator, "preparations", None) is None
    if requires_model:
        from final.src.models import create_model
        model = create_model(backend=options.model_backend, model_name=options.model_name,
                             context=options.context_tokens)
        calls = RecordedModelCalls(model, artifacts)
    cache = False if options.no_execution_cache else InputExecutionCache(options.execution_cache)
    pipeline = BenchmarkPipeline(
        options.cohort,
        artifacts,
        calls=calls,
        arms=None if tool_generator else arms,
        input_generator=tool_generator,
        settings=settings,
        execution_cache=cache,
    )
    return pipeline, model


def prepare_pipeline(parser, options):
    dataset = DatasetLoader('HE-py')
    tasks = dataset.load_tasks()
    if options.task_ids:
        requested_ids = set(options.task_ids)
        known_ids = {task["task_id"] for task in tasks}
        unsupported_ids = requested_ids - known_ids
        if unsupported_ids:
            parser.error(f"Unsupported task IDs: {', '.join(sorted(unsupported_ids))}")
        tasks = [task for task in tasks if task["task_id"] in requested_ids]
    metadata = dataset.load_metadata()
    return tasks, metadata


def main(arguments=None):
    parser, options = load_options(arguments)
    if options.mode == "replay":
        from .stages.reporting import ReportingStage
        summary = ReportingStage.summarize_saved(ArtifactStore(options.artifacts, read_only=True), options.task_ids)
        results = json.dumps(
            {
                "mode": "replay",
                "scored_tasks": summary["scored_tasks"],
                "arms": summary["arms"],
                "stage_events": 0,
            },
            indent=2,
        )
        print(results)
        return 0
    settings, arms, tool_generator = load_pipeline_settings(parser, options)
    tasks, metadata = prepare_pipeline(parser, options)
    artifacts = ArtifactStore(options.artifacts)
    pipeline, model = construct_pipeline(parser, options, artifacts, settings, arms, tool_generator)
    status_path = artifacts.path("status.json")
    status = {"state": "running", "pid": os.getpid(), "updated_utc": time.time()}
    save(status_path, status)
    try:
        native_lock = nullcontext()
        if options.pynguin_config:
            native_lock = pynguin_native_lock()
        with native_lock:
            summary = pipeline.run(tasks, metadata)
    except BaseException as error:
        details = error.details() if hasattr(error, "details") else None
        status.update(
            state="interrupted",
            error_type=type(error).__name__,
            error=details,
            updated_utc=time.time(),
        )
        save(status_path, status)
        raise
    status.update(
        state="complete",
        updated_utc=time.time(),
        scored_tasks=summary["scored_tasks"],
    )
    save(status_path, status)
    result = {
        "mode": options.mode,
        "scored_tasks": summary["scored_tasks"],
        "arms": summary["arms"],
        "stage_events": len(pipeline.stage_events),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
