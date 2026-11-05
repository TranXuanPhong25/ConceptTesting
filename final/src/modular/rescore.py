"""Rescore saved input batches with corrected HumanEval+ references; no model backend."""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from final.src.runtime.artifacts import digest, save
from final.src.modular.dataset import load_tasks
from .arms import selected_arms
from .artifacts import ArtifactStore
from .context import PipelineSettings
from .execution_cache import InputExecutionCache
from .generators.frozen import FrozenInputsGenerator
from .pipeline import BenchmarkPipeline
from .references import HumanEvalPlusReferencePrograms


def build_rescore_pipeline(source_directory, cohort_path, output_directory, *, cache_directory):
    source = ArtifactStore(source_directory, read_only=True)
    manifest = source.read("modular_manifest.json")
    method_names = [record["name"] for record in manifest["arms"]]
    if set(method_names) - {"plain", "boundary"}:
        raise ValueError("This rescorer supports modern plain/boundary input batches")
    generator = FrozenInputsGenerator(source_directory, methods=selected_arms(method_names))
    tasks_by_id = {task["task_id"]: task for task in load_tasks()}
    tasks = [tasks_by_id[task_id] for task_id in manifest["tasks"]]
    metadata_path = Path(__file__).resolve().parents[2] / "data/contracts.json"
    all_metadata = json.loads(metadata_path.read_text())
    metadata = {task["task_id"]: all_metadata[task["task_id"]] for task in tasks}
    if digest(tasks) != manifest["task_data_sha256"] or digest(metadata) != manifest["metadata_sha256"]:
        raise ValueError("Rescore task/spec/domain metadata differs from original generation")
    reference = HumanEvalPlusReferencePrograms()
    for task in tasks:
        reference.for_task(task, metadata[task["task_id"]])
    artifacts = ArtifactStore(output_directory)
    if artifacts.directory == source.directory:
        raise ValueError("Rescore requires a separate output directory")
    pipeline = BenchmarkPipeline(cohort_path, artifacts, input_generator=generator,
        settings=PipelineSettings(**manifest["settings"]), calls=None,
        execution_cache=InputExecutionCache(cache_directory), reference_programs=reference)
    if pipeline.cohort_stage.cohort["cohort_sha256"] != manifest["cohort_sha256"]:
        raise ValueError("Rescore must use the original frozen cohort")
    return pipeline, tasks, metadata


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run", type=Path, required=True)
    parser.add_argument("--cohort", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--execution-cache", type=Path, default=Path("final/out/execution_cache"))
    options = parser.parse_args(arguments)
    pipeline, tasks, metadata = build_rescore_pipeline(options.source_run, options.cohort, options.artifacts,
                                                      cache_directory=options.execution_cache)
    status = pipeline.artifacts.path("status.json")
    save(status, {"state": "running", "pid": os.getpid(), "updated_utc": time.time(),
                  "phase": "rescore-only", "new_model_calls": 0})
    try:
        summary = pipeline.run(tasks, metadata)
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
