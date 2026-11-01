"""Import existing inputs/responses byte for byte while keeping the original run intact."""
from __future__ import annotations

import fcntl
import hashlib
import json
import shutil
from pathlib import Path

from final.pipeline import save
from final.experiments.concept_reference_v1.cohort import load_cohort


def prepare_resume(source_directory: Path, destination_directory: Path, cohort_path: Path):
    destination_directory.mkdir(parents=True, exist_ok=True)
    with (source_directory / ".run.lock").open("a+") as source_lock:
        fcntl.flock(source_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with (destination_directory / ".run.lock").open("a+") as destination_lock:
            fcntl.flock(destination_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if (destination_directory / "tasks").exists():
                raise RuntimeError("Destination already contains task artifacts; refusing to overwrite")
            cohort = load_cohort(cohort_path)
            original_manifest = json.loads((source_directory / "manifest.json").read_text())
            for relative_path, expected_hash in original_manifest["sources"].items():
                source_path = Path("final") / relative_path
                if hashlib.sha256(source_path.read_bytes()).hexdigest() != expected_hash:
                    raise RuntimeError("Original frozen source hash mismatch")
            copied_files = {}
            for directory_name in ("tasks", "keepalive"):
                source_path = source_directory / directory_name
                if not source_path.exists():
                    continue
                shutil.copytree(source_path, destination_directory / directory_name)
                for artifact_path in source_path.rglob("*"):
                    if not artifact_path.is_file():
                        continue
                    relative_path = artifact_path.relative_to(source_directory)
                    expected_hash = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
                    imported_path = destination_directory / relative_path
                    if hashlib.sha256(imported_path.read_bytes()).hexdigest() != expected_hash:
                        raise RuntimeError("Imported checkpoint hash mismatch")
                    copied_files[str(relative_path)] = expected_hash
            save(destination_directory / "import_manifest.json", {
                "source_run": str(source_directory),
                "cohort_path": str(cohort_path),
                "cohort_sha256": cohort["cohort_sha256"],
                "original_manifest": original_manifest,
                "copied_file_hashes": copied_files,
            })
            return {
                "imported_files": len(copied_files),
                "input_task_files": len(list((destination_directory / "tasks").glob("*/inputs.json"))),
                "received_responses": len(list((destination_directory / "tasks").glob("*/calls/*/response.json"))),
                "cohort_sha256": cohort["cohort_sha256"],
            }


if __name__ == "__main__":
    print(prepare_resume(
        Path("final/out/concept_reference_v1"),
        Path("final/out/concept_reference_v1_recovery"),
        Path("final/out/cohorts/qwen35_27b_humaneval164/cohort.json"),
    ))
