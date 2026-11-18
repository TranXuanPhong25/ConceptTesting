"""Rescore saved input batches with corrected HumanEval+ references; no model backend."""
from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

from final.src.runtime.artifacts import save
from final.src.benchmarks.datasets import load_tasks
from .artifacts import ArtifactStore
from .context import PipelineSettings
from .execution_cache import InputExecutionCache
from .generators.frozen import FrozenInputsGenerator
from .pipeline import BenchmarkPipeline
from .references import HumanEvalPlusReferencePrograms


@dataclass
class SavedInputMethod:
    name: str
    options: dict

    def configuration(self):
        return self.options

    def extend_summary(self, contexts, summary, reporting):
        pass


def methods_for_rescore(records):
    return tuple(SavedInputMethod(record["name"], record.get("configuration", {})) for record in records)


def build_rescore_pipeline(source_directory, cohort_path, output_directory, *, cache_directory, read_only=False):
    source = ArtifactStore(source_directory, read_only=True)
    manifest = source.read("modular_manifest.json")
    generator = FrozenInputsGenerator(source_directory, methods=methods_for_rescore(manifest["arms"]))
    tasks_by_id = {task["task_id"]: task for task in load_tasks()}
    tasks = [tasks_by_id[task_id] for task_id in manifest["tasks"]]
    metadata_path = Path(__file__).resolve().parents[2] / "data/contracts.json"
    all_metadata = json.loads(metadata_path.read_text())
    metadata = {task["task_id"]: all_metadata[task["task_id"]] for task in tasks}
    reference = HumanEvalPlusReferencePrograms()
    for task in tasks:
        reference.for_task(task, metadata[task["task_id"]])
    artifacts = ArtifactStore(output_directory,read_only=read_only)
    if artifacts.directory == source.directory or artifacts.directory.is_relative_to(source.directory):
        raise ValueError("Rescore requires a separate output directory")
    if not read_only and artifacts.directory.exists():
        raise ValueError("Rescore requires a new output directory; the execution cache can be shared")
    pipeline = BenchmarkPipeline(cohort_path, artifacts, input_generator=generator,
        settings=PipelineSettings(**manifest["settings"]), calls=None,
        execution_cache=InputExecutionCache(cache_directory,read_only=read_only), reference_programs=reference)
    return pipeline, tasks, metadata


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run", type=Path, required=True)
    parser.add_argument("--cohort", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--execution-cache", type=Path, default=Path("final/out/execution_cache"))
    parser.add_argument('--replay',action='store_true',help='Summarize saved evaluation results without executing programs')
    options = parser.parse_args(arguments)
    if options.replay:
        from .stages.reporting import ReportingStage
        summary = ReportingStage.summarize_saved(ArtifactStore(options.artifacts, read_only=True))
        print(json.dumps({"arms": summary["arms"], "new_model_calls": 0, "new_native_calls": 0}))
        return 0
    pipeline, tasks, metadata = build_rescore_pipeline(options.source_run, options.cohort, options.artifacts,
                                                      cache_directory=options.execution_cache)
    status = pipeline.artifacts.path("status.json")
    save(status, {"state": "running", "pid": os.getpid(), "updated_utc": time.time(),
                  "phase": "rescore-only", "new_model_calls": 0})
    try:
        summary = pipeline.run(tasks, metadata)
        from final.src.audits.detection_kinds import classify_arm,kind_counts,strongest_kind
        union={};kinds={}
        for arm in summary['arms']:
            detected=classify_arm(pipeline.artifacts.directory,arm);kinds[arm]=kind_counts(detected)
            for key,row in detected.items():
                if key not in union or strongest_kind({union[key]['kind'],row['kind']})==row['kind']:
                    union[key]=row
        save(pipeline.artifacts.path('rescore_metrics.json'),{'arms':summary['arms'],
            'detection_kinds':kinds,'union':kind_counts(union),'new_model_calls':0})
    except BaseException as error:
        save(status, {"state": "interrupted", "pid": os.getpid(), "updated_utc": time.time(),
                      "error_type": type(error).__name__, "new_model_calls": 0})
        raise
    save(status, {"state": "complete", "pid": os.getpid(), "updated_utc": time.time(),
                  "scored_tasks": summary["scored_tasks"], "new_model_calls": 0})
    print(json.dumps({"scored_tasks": summary["scored_tasks"], "arms": summary["arms"],
                      "new_model_calls": 0, "cache": summary.get("input_execution_cache")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
