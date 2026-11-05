"""Readable entry point. Replay is the safe default and never creates a model."""
import argparse
import json
import os
import time
from pathlib import Path

from final.run import load_tasks
from .artifacts import ArtifactStore
from .calls import RecoveryModelCalls
from .pipeline import BenchmarkPipeline
from .context import PipelineSettings
from .execution_cache import InputExecutionCache
from .arms import available_arms, LEGACY_METHOD_NAMES, default_arms, selected_arms
from final.pipeline import save
from final.experiments.concept_reference_v1_recovery.keepalive import KeepAlive


def positive_integer(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("Expected a positive integer")
    return number


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("replay", "run"), default="replay")
    parser.add_argument("--cohort", type=Path, default=Path("final/out/cohorts/qwen35_27b_humaneval164/cohort.json"))
    parser.add_argument("--artifacts", type=Path, default=Path("final/out/modular_pipeline"))
    parser.add_argument("--legacy-generation", action="store_true",
                        help="Explicit compatibility mode for archived concept/witness arms")
    parser.add_argument("--arms", nargs="+", choices=[arm.name for arm in available_arms()] + list(LEGACY_METHOD_NAMES),
                        help="Input methods: plain (default), boundary; archived methods require --legacy-generation")
    parser.add_argument("--task-ids", nargs="+", help="Explicit subset, e.g. HumanEval/0 HumanEval/18")
    parser.add_argument("--target-programs", type=positive_integer, default=10,
                        help="Expected frozen programs per task; use 1 for representative smoke cohorts")
    parser.add_argument("--input-budget", type=positive_integer, default=20,
                        help="Total input budget per arm per task, including the boundary arm")
    parser.add_argument("--execution-cache", type=Path, default=Path("final/out/execution_cache"),
                        help="Shared per-input reference/PUT execution cache")
    parser.add_argument("--no-execution-cache", action="store_true", help="Use the original batch execution without shared input caching")
    parser.add_argument("--v11-concept-cache", type=Path,
                        help="Read-only source of matching V11 concept bundles; default: existing runtimefix run")
    parser.add_argument("--v11-cache-only", action="store_true",
                        help="Fail on missing V11 concept caches instead of mining new concepts")
    parser.add_argument("--v11-resource-exclusions", type=Path,
                        help="Explicit source-bound resource exclusions from preparation, prompts and evaluation")
    options = parser.parse_args(arguments)
    modern_names = {arm.name for arm in available_arms()}
    if not options.legacy_generation and set(options.arms or ()) - modern_names:
        parser.error("Archived concept/witness methods require explicit --legacy-generation")
    read_only = options.mode == "replay"
    artifacts = ArtifactStore(options.artifacts, read_only=read_only)
    arms = (selected_arms(options.arms, v11_cache_directory=options.v11_concept_cache,
                          v11_cache_only=options.v11_cache_only,
                          v11_resource_exclusions=options.v11_resource_exclusions)
            if options.arms else default_arms())
    tasks = load_tasks()
    if options.task_ids:
        requested_ids = set(options.task_ids)
        known_ids = {task["task_id"] for task in tasks}
        if requested_ids - known_ids or len(requested_ids) != len(options.task_ids):
            parser.error("--task-ids must contain unique known task IDs")
        tasks = [task for task in tasks if task["task_id"] in requested_ids]
    settings = PipelineSettings(target_programs=options.target_programs, input_budget=options.input_budget)
    calls = None
    if not read_only:
        # New experiments must have their own directory. Never modify a frozen v1 run.
        if artifacts.exists("manifest.json") or (artifacts.exists("status.json") and not artifacts.exists("modular_manifest.json")):
            parser.error("Use a new --artifacts directory for a modular run")
        if any(arm.uses_model for arm in arms):
            from final.experiments.concept_reference_v1_recovery.model import QwenModel
            calls = RecoveryModelCalls(QwenModel(), artifacts)
    metadata_path = Path(__file__).resolve().parents[1] / "experiments/concept_reference_v1/data/contracts.json"
    metadata = json.loads(metadata_path.read_text())
    cache = False if options.no_execution_cache or options.legacy_generation else InputExecutionCache(
        options.execution_cache, read_only=read_only)
    pipeline = BenchmarkPipeline(options.cohort, artifacts, calls=calls, arms=arms, settings=settings,
                                 execution_cache=cache)
    if read_only:
        summary = pipeline.run(tasks, metadata)
    else:
        save(artifacts.path("status.json"), {"state": "running", "pid": os.getpid(), "updated_utc": time.time()})
        try:
            with KeepAlive(artifacts.directory):
                summary = pipeline.run(tasks, metadata)
        except BaseException as error:
            details = error.details() if hasattr(error, "details") else None
            save(artifacts.path("status.json"), {"state": "interrupted", "pid": os.getpid(),
                 "error_type": type(error).__name__, "error": details, "updated_utc": time.time()})
            raise
        save(artifacts.path("status.json"), {"state": "complete", "pid": os.getpid(),
             "updated_utc": time.time(), "scored_tasks": summary["scored_tasks"]})
    print(json.dumps({"mode": options.mode, "scored_tasks": summary["scored_tasks"],
                      "arms": summary["arms"], "stage_events": len(pipeline.stage_events)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
