"""Readable entry point. Replay is the safe default and never creates a model."""
import argparse
import json
import os
import time
from pathlib import Path

from final.src.modular.dataset import load_tasks
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
    parser.add_argument("--catalogue-off", action="store_true", help="Instruction-only ablation for catalogue arms")
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
    arms = selected_arms(options.arms) if options.arms else default_arms()
    if options.catalogue_off:
        from .arms.classical import CatalogueSettings
        arms = tuple(type(arm)(CatalogueSettings(catalogue=False)) if getattr(arm, "measures_catalogue", False)
                     else arm for arm in arms)
    input_tokens = options.input_tokens or max(
        4096 if any(getattr(arm, "measures_catalogue", False) for arm in arms) else 2048,
        *(getattr(arm, 'default_input_tokens', 2048) for arm in arms))
    if input_tokens + 128 >= options.context_tokens:
        parser.error("Completion reserve must leave prompt context")
    settings = PipelineSettings(target_programs=options.target_programs, input_budget=options.input_budget,
                                input_tokens=input_tokens, context_tokens=options.context_tokens)
    return settings, arms


def construct_pipeline(parser, options, artifacts, settings, arms):
    read_only = options.mode == "replay"
    calls = None
    if not read_only:
        # New experiments must have their own directory. Never modify a frozen v1 run.
        if artifacts.exists("manifest.json") or (artifacts.exists("status.json") and not artifacts.exists("modular_manifest.json")):
            parser.error("Use a new --artifacts directory for a modular run")
        if any(arm.uses_model for arm in arms):
            from final.src.runtime.model import QwenModel
            calls = RecordedModelCalls(QwenModel(), artifacts)
    cache = False if options.no_execution_cache else InputExecutionCache(
        options.execution_cache, read_only=read_only)
    pipeline = BenchmarkPipeline(options.cohort, artifacts, calls=calls, arms=arms, settings=settings,
                                 execution_cache=cache)
    return pipeline


def prepare_pipeline(parser, options):
    tasks = load_tasks()
    if options.task_ids:
        requested_ids = set(options.task_ids)
        known_ids = {task["task_id"] for task in tasks}
        unsupported_ids = requested_ids - known_ids
        if unsupported_ids:
            parser.error(f"Unsupported task IDs: {', '.join(sorted(unsupported_ids))}")
        tasks = [task for task in tasks if task["task_id"] in requested_ids]
    metadata_path = Path(__file__).resolve().parents[2] / "data/contracts.json"
    metadata = json.loads(metadata_path.read_text())
    return tasks, metadata


def main(arguments=None):
    parser, options = load_options(arguments)
    settings, arms = load_pipeline_settings(parser, options)
    tasks, metadata = prepare_pipeline(parser, options)
    read_only = options.mode == "replay"
    artifacts = ArtifactStore(options.artifacts, read_only=read_only)
    pipeline = construct_pipeline(parser, options, artifacts, settings, arms)
    if read_only:
        summary = pipeline.run(tasks, metadata)
    else:
        status_path = artifacts.path("status.json")
        status = {"state": "running", "pid": os.getpid(), "updated_utc": time.time()}
        save(status_path, status)
        try:
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
