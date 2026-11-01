"""Readable entry point. Replay is the safe default and never creates a model."""
import argparse
import json
from pathlib import Path

from final.run import load_tasks
from .artifacts import ArtifactStore
from .calls import RecoveryModelCalls
from .pipeline import BenchmarkPipeline
from .arms import default_arms, selected_arms


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("replay", "run"), default="replay")
    parser.add_argument("--cohort", type=Path, default=Path("final/out/cohorts/qwen35_27b_humaneval164/cohort.json"))
    parser.add_argument("--artifacts", type=Path, default=Path("final/out/concept_reference_v1_recovery"))
    parser.add_argument("--arms", nargs="+", choices=[arm.name for arm in default_arms()],
                        help="Choose run types; replay of the original run requires all six")
    options = parser.parse_args(arguments)
    read_only = options.mode == "replay"
    artifacts = ArtifactStore(options.artifacts, read_only=read_only)
    arms = selected_arms(options.arms) if options.arms else default_arms()
    calls = None
    if not read_only:
        # New experiments must have their own directory. Never modify a frozen v1 run.
        if artifacts.exists("manifest.json") or artifacts.exists("status.json"):
            parser.error("Use a new --artifacts directory for a modular run")
        if any(arm.uses_model for arm in arms):
            from final.experiments.concept_reference_v1_recovery.model import QwenModel
            calls = RecoveryModelCalls(QwenModel(), artifacts)
    metadata_path = Path(__file__).resolve().parents[1] / "experiments/concept_reference_v1/data/contracts.json"
    metadata = json.loads(metadata_path.read_text())
    pipeline = BenchmarkPipeline(options.cohort, artifacts, calls=calls, arms=arms)
    summary = pipeline.run(load_tasks(), metadata)
    print(json.dumps({"mode": options.mode, "scored_tasks": summary["scored_tasks"],
                      "arms": summary["arms"], "stage_events": len(pipeline.stage_events)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
