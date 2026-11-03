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
from .arms import available_arms, default_arms, selected_arms
from final.pipeline import save
from final.experiments.concept_reference_v1_recovery.keepalive import KeepAlive


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("replay", "run"), default="replay")
    parser.add_argument("--cohort", type=Path, default=Path("final/out/cohorts/qwen35_27b_humaneval164/cohort.json"))
    parser.add_argument("--artifacts", type=Path, default=Path("final/out/concept_reference_v1_recovery"))
    parser.add_argument("--arms", nargs="+", choices=[arm.name for arm in available_arms()],
                        help="Choose run types; replay of the original run requires all six")
    parser.add_argument("--v11-concept-cache", type=Path,
                        help="Read-only source of matching V11 concept bundles; default: existing runtimefix run")
    parser.add_argument("--v11-cache-only", action="store_true",
                        help="Fail on missing V11 concept caches instead of mining new concepts")
    options = parser.parse_args(arguments)
    read_only = options.mode == "replay"
    artifacts = ArtifactStore(options.artifacts, read_only=read_only)
    arms = (selected_arms(options.arms, v11_cache_directory=options.v11_concept_cache,
                          v11_cache_only=options.v11_cache_only)
            if options.arms else default_arms())
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
    pipeline = BenchmarkPipeline(options.cohort, artifacts, calls=calls, arms=arms)
    if read_only:
        summary = pipeline.run(load_tasks(), metadata)
    else:
        save(artifacts.path("status.json"), {"state": "running", "pid": os.getpid(), "updated_utc": time.time()})
        try:
            with KeepAlive(artifacts.directory):
                summary = pipeline.run(load_tasks(), metadata)
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
