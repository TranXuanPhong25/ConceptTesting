"""Wait for the requested time and reviewed code, then resume automatically."""
from __future__ import annotations

import hashlib
import fcntl
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from final.pipeline import save
from .model import QwenModel, TransportError


def main():
    schedule_directory = Path("final/out/concept_reference_v1_recovery_schedule")
    schedule_directory.mkdir(parents=True, exist_ok=True)
    with (schedule_directory / ".schedule.lock").open("a+") as scheduler_lock:
        try:
            fcntl.flock(scheduler_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 2
        return run_schedule(schedule_directory)


def run_schedule(schedule_directory):
    recovery_directory = Path("final/out/concept_reference_v1_recovery")
    deadline_record = json.loads(Path("/tmp/concepttester-final-retry-deadline.json").read_text())
    retry_deadline = datetime.fromisoformat(deadline_record["not_before_utc"])
    readiness_path = schedule_directory / "ready_to_launch.json"
    save(schedule_directory / "status.json", {
        "state": "waiting_retry_deadline",
        "not_before_utc": retry_deadline.isoformat(),
        "pid": os.getpid(),
    })
    while datetime.now(timezone.utc) < retry_deadline:
        remaining_seconds = (retry_deadline - datetime.now(timezone.utc)).total_seconds()
        time.sleep(min(30, max(0, remaining_seconds)))
    while True:
        if not readiness_path.exists():
            save(schedule_directory / "status.json", {"state": "waiting_review_clearance", "pid": os.getpid()})
            time.sleep(10)
            continue
        clearance = json.loads(readiness_path.read_text())
        for source_path, expected_hash in clearance["source_hashes"].items():
            actual_hash = hashlib.sha256(Path(source_path).read_bytes()).hexdigest()
            if actual_hash != expected_hash:
                save(schedule_directory / "status.json", {"state": "source_changed_after_review", "pid": os.getpid()})
                return 2
        try:
            model = QwenModel()
            endpoint_details = model.check_endpoint()
        except TransportError as error:
            save(schedule_directory / "status.json", {
                "state": "waiting_for_endpoint",
                "error": error.details(),
                "pid": os.getpid(),
            })
            if error.error_type in ("ModelChanged", "ExpectedModelMissing", "ContextTooSmall"):
                return 2
            time.sleep(60)
            continue
        save(schedule_directory / "status.json", {
            "state": "launching",
            "endpoint": endpoint_details,
            "pid": os.getpid(),
        })
        recovery_directory.mkdir(parents=True, exist_ok=True)
        with (recovery_directory / "run.log").open("ab") as log_file:
            controller = subprocess.Popen(
                ["final/.venv/bin/python", "-m", "final.experiments.concept_reference_v1_recovery.run", "--workers", "2"],
                stdout=log_file, stderr=log_file, stdin=subprocess.DEVNULL, start_new_session=True,
            )
        (recovery_directory / "controller.pid").write_text(str(controller.pid) + "\n")
        save(schedule_directory / "status.json", {
            "state": "running", "controller_pid": controller.pid, "pid": os.getpid(),
        })
        exit_code = controller.wait()
        if exit_code == 0:
            save(schedule_directory / "status.json", {
                "state": "complete", "controller_pid": controller.pid, "pid": os.getpid(),
            })
            return 0
        controller_status_path = recovery_directory / "status.json"
        controller_status = json.loads(controller_status_path.read_text()) if controller_status_path.exists() else {}
        error_details = controller_status.get("error") or {}
        if error_details.get("operation") in ("models", "tokenize") and error_details.get("retryable"):
            save(schedule_directory / "status.json", {
                "state": "waiting_after_read_only_failure", "error": error_details, "pid": os.getpid(),
            })
            time.sleep(60)
            continue
        save(schedule_directory / "status.json", {
            "state": "interrupted", "controller_status": controller_status, "pid": os.getpid(),
        })
        return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
