"""Continue a stopped full BVA run using its frozen runtime and received checkpoints."""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import importlib.metadata
import json
import os
import platform
from pathlib import Path
import shutil
import subprocess
import sys

from final.src.runtime.artifacts import digest, save
from .run_prompt_style import configure_endpoint, read


ROOT = Path(__file__).resolve().parents[3]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(source, directory):
    if directory.exists():
        raise ValueError("Use a new output directory")
    with (source / ".worker.lock").open("r") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if read(source / "status.json")["state"] != "interrupted":
            raise ValueError("Continuation requires an interrupted, stopped source run")
        original_hashes = {str(path): sha256(path) for path in source.rglob("*") if path.is_file()}
        plan = read(source / "launch_plan.json")
        snapshot = read(source / "source_snapshot.json")
        if snapshot["sources"].get(str(source / "launch_plan.json")) != sha256(source / "launch_plan.json"):
            raise ValueError("Original request plan changed")
        manifest_path = source / "modular_manifest.json"
        if manifest_path.exists():
            manifest = read(manifest_path)
            if manifest["python"] != platform.python_version():
                raise ValueError("Frozen Python version differs")
            for package, version in manifest["packages"].items():
                if importlib.metadata.version(package) != version:
                    raise ValueError("Frozen dependency changed: " + package)
        archive_root = source / "source_archive"
        for name, checksum in snapshot["archive"].items():
            if sha256(Path(name)) != checksum:
                raise ValueError("Original runtime archive changed: " + name)
        calls = list(source.glob("tasks/*/calls/*/attempt.json"))
        received = []
        for attempt_path in calls:
            if "_unknown_attempt_" in attempt_path.parent.name:
                continue
            task_number = attempt_path.parents[2].name
            call_name = attempt_path.parent.name
            key = f"{task_number}/{call_name}"
            attempt = read(attempt_path)
            request = read(attempt_path.parent / "request.json")
            expected = plan["requests"].get(key)
            if (expected is None or digest(request) != expected["request_sha256"]
                    or attempt.get("request_id") != digest(request) or attempt.get("state") != "received"
                    or not (attempt_path.parent / "response.json").is_file()):
                raise ValueError("Unresolved or mismatched checkpoint; refusing automatic regeneration: " + key)
            received.append(key)
        directory.mkdir(parents=True)
        runtime = directory / "runtime"
        sources, backup_hashes = {}, {}
        for name, checksum in snapshot["archive"].items():
            archived = Path(name)
            relative = archived.relative_to(archive_root)
            destination = runtime / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(archived, destination)
            destination.chmod(0o444)
            sources[str(destination)] = checksum
            backup_hashes[str(archived)] = checksum
        # Initial launch archived executing modules but not these inert namespace markers.
        bootstrap = []
        for relative in ("final/__init__.py", "final/src/__init__.py", "final/src/audits/__init__.py"):
            path = runtime / relative
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('"""Frozen BVA runtime package namespace."""\n')
                path.chmod(0o444)
                sources[str(path)] = sha256(path)
                bootstrap.append(str(path))
        imports, historical_usage = [], {key: 0 for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
        for path in source.glob("tasks/*/calls/*/*.json"):
            destination = directory / path.relative_to(source)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)
            checksum = sha256(path)
            sources[str(destination)] = checksum
            imports.append({"source": str(path), "destination": str(destination), "sha256": checksum})
            if path.name == "response.json":
                for key in historical_usage:
                    historical_usage[key] += read(path).get("usage", {}).get(key, 0)
        completed_tasks = []
        for input_path in sorted(source.glob("tasks/*/inputs.json")):
            batch = read(input_path)
            number = input_path.parent.name
            if batch["task_id"] != f"HumanEval/{number}":
                raise ValueError("Imported input task mismatch")
            for program in batch.get("arms", {}).get("boundary", {}).get("programs", []):
                if program["logical_calls"]["generation"]:
                    key = f"{number}/bva_{program['program_id']}_soft_inputs"
                    if key not in received:
                        raise ValueError("Completed task has a missing received call: " + key)
            for filename in ("inputs.json", "packet.json", "boundary_plan.json", "boundary_arm.json"):
                path = input_path.parent / filename
                if not path.exists():
                    continue
                destination = directory / path.relative_to(source)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, destination)
                checksum = sha256(path)
                sources[str(destination)] = checksum
                imports.append({"source": str(path), "destination": str(destination), "sha256": checksum})
            completed_tasks.append(batch["task_id"])
        observer_records = [{"source": str(path), "sha256": sha256(path),
                             "state": read(path).get("state"),
                             "known_total_tokens": read(path).get("usage", {}).get("total_tokens", 0)}
                            for path in sorted((source / "keepalive").glob("*.json"))]
        new_plan = {**plan, "cohort": str(runtime / Path(plan["cohort"]).relative_to(ROOT)),
            "continuation_source": str(source), "runtime_policy": "original-source-archive-isolated-from-live-worktree",
            "imported_received_calls": len(received), "remaining_new_logical_call_cap": plan["logical_call_cap"] - len(received),
            "imported_completed_tasks": completed_tasks, "imported_historical_usage": historical_usage,
            "historical_observer_usage": {"records": observer_records,
                "known_total_tokens": sum(row["known_total_tokens"] for row in observer_records),
                "scope": "parent-run keepalive, separate from continuation keepalive"}}
        save(directory / "launch_plan.json", new_plan)
        save(directory / "continuation_receipts.json", {"source": str(source), "imports": imports,
             "runtime_archive_hashes": snapshot["archive"], "namespace_bootstrap_files": bootstrap,
             "received_calls": received, "policy": "no response repair; no changed request or scoring; historical unknown attempts copied"})
        for path in (directory / "launch_plan.json", directory / "continuation_receipts.json"):
            sources[str(path)] = sha256(path)
        save(directory / "source_snapshot.json", {"sources": sources, "archive": backup_hashes})
        if original_hashes != {str(path): sha256(path) for path in source.rglob("*") if path.is_file()}:
            raise ValueError("Original stopped run changed during continuation preparation")
        save(directory / "status.json", {"state": "prepared", "imported_received_calls": len(received),
             "remaining_new_logical_call_cap": new_plan["remaining_new_logical_call_cap"]})
        return new_plan


def launch(directory):
    runtime = directory / "runtime"
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(runtime)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    probe = subprocess.run([sys.executable, "-P", "-B", "-c",
        "import json;from final.src.modular.stages import put_evaluation;from final.src.runtime import execution;"
        "print(json.dumps([put_evaluation.__file__,str(execution.HERE/'worker.py')]))"], cwd=ROOT, env=environment,
        capture_output=True, text=True, check=True)
    module_paths = json.loads(probe.stdout)
    if not all(Path(name).is_relative_to(runtime) for name in module_paths):
        raise ValueError("Frozen runtime imported live worktree modules")
    save(directory / "runtime_import_probe.json", {"module_paths": module_paths, "live_worktree_excluded": True})
    with (directory / "launch_reserved.json").open("x") as marker:
        json.dump({"automatic_restart": False}, marker)
    with (directory / "runner.log").open("xb") as log:
        process = subprocess.Popen([sys.executable, "-P", "-B", "-u", "-m", "final.src.audits.run_bva_full",
            "--worker", "--artifacts", str(directory)], cwd=ROOT, env=environment,
            stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    (directory / "runner.pid").write_text(str(process.pid) + "\n")
    return process.pid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path)
    parser.add_argument("--prepare-only", action="store_true")
    options = parser.parse_args()
    if not options.prepare_only:
        configure_endpoint()
    directory = (options.artifacts or Path("final/out/boundary_soft_humaneval164_resume_" + dt.datetime.now().strftime("%Y%m%d_%H%M%S"))).resolve()
    plan = prepare(options.source_run.resolve(), directory)
    record = {"artifacts": str(directory), "reused_received_calls": plan["imported_received_calls"],
              "reused_task_batches": len(plan["imported_completed_tasks"]),
              "remaining_new_logical_calls": plan["remaining_new_logical_call_cap"]}
    if not options.prepare_only:
        record["pid"] = launch(directory)
    print(json.dumps(record), flush=True)


if __name__ == "__main__":
    main()
