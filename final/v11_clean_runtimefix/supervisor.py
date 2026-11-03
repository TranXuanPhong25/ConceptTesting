"""Durable delayed launch, one-minute health checks and bounded transport recovery."""

import fcntl
import hashlib
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from final.pipeline import save
from final.experiments.concept_reference_v1_recovery.model import (
    QwenModel,
    TransportError,
)

SCHEDULE = Path("final/out/v11_clean_runtimefix_schedule")
OUTPUT = Path("final/out/v11_clean_runtimefix")


def main():
    SCHEDULE.mkdir(parents=True, exist_ok=True)
    with (SCHEDULE / ".supervisor.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return supervise()


def supervise():
    existing_status_path = SCHEDULE / "status.json"
    if existing_status_path.exists():
        existing_state = json.loads(existing_status_path.read_text()).get("state")
        if existing_state in (
            "complete",
            "user_stopped",
            "source_drift",
            "needs_code_review",
        ):
            return 0
    deadline = datetime.fromisoformat(
        json.loads((SCHEDULE / "schedule.json").read_text())["not_before_utc"]
    )
    while datetime.now(timezone.utc) < deadline:
        save(
            SCHEDULE / "status.json",
            dict(
                state="waiting_deadline",
                not_before_utc=deadline.isoformat(),
                pid=os.getpid(),
            ),
        )
        time.sleep(
            min(30, max(0, (deadline - datetime.now(timezone.utc)).total_seconds()))
        )
    while not (SCHEDULE / "ready.json").exists():
        save(
            SCHEDULE / "status.json",
            dict(state="waiting_review_and_tests", pid=os.getpid()),
        )
        time.sleep(15)
    restarts = 0
    while True:
        if (SCHEDULE / "STOP").exists():
            save(SCHEDULE / "status.json", dict(state="user_stopped", pid=os.getpid()))
            return 0
        readiness = json.loads((SCHEDULE / "ready.json").read_text())
        for filename, expected in readiness["source_hashes"].items():
            if hashlib.sha256(Path(filename).read_bytes()).hexdigest() != expected:
                save(
                    SCHEDULE / "status.json",
                    dict(state="source_drift", pid=os.getpid(), path=filename),
                )
                return 2
        try:
            endpoint = QwenModel().check_endpoint()
        except TransportError as error:
            save(
                SCHEDULE / "status.json",
                dict(state="waiting_endpoint", pid=os.getpid(), error=error.details()),
            )
            if error.error_type in (
                "ModelChanged",
                "ExpectedModelMissing",
                "ContextTooSmall",
            ):
                return 2
            time.sleep(60)
            continue
        OUTPUT.mkdir(parents=True, exist_ok=True)
        with (OUTPUT / "run.log").open("ab") as log:
            process = subprocess.Popen(
                ["final/.venv/bin/python", "-m", "final.v11_clean_runtimefix.run"],
                stdout=log,
                stderr=log,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
        save(
            SCHEDULE / "status.json",
            dict(
                state="running",
                pid=os.getpid(),
                controller_pid=process.pid,
                endpoint=endpoint,
                restarts=restarts,
            ),
        )
        heartbeat_number = 0
        while process.poll() is None:
            if (SCHEDULE / "STOP").exists():
                process.terminate()
                process.wait(timeout=20)
                save(
                    SCHEDULE / "status.json",
                    dict(state="user_stopped", pid=os.getpid()),
                )
                return 0
            controller_status = (
                json.loads((OUTPUT / "status.json").read_text())
                if (OUTPUT / "status.json").exists()
                else {}
            )
            active_cases = []
            for progress_path in (OUTPUT / "cases").glob("*/progress.json"):
                progress = json.loads(progress_path.read_text())
                if progress.get("state") == "running":
                    worker_progress_path = (
                        progress_path.parent / "fact_worker/worker_progress.json"
                    )
                    if worker_progress_path.exists():
                        progress["worker_cpu_progress"] = json.loads(
                            worker_progress_path.read_text()
                        )
                    active_cases.append(
                        dict(case_id=progress_path.parent.name, **progress)
                    )
            save(
                SCHEDULE / "heartbeat.json",
                dict(
                    controller_pid=process.pid,
                    time_utc=datetime.now(timezone.utc).isoformat(),
                    controller_status=controller_status,
                    active_cases=active_cases,
                ),
            )
            heartbeat_number += 1
            # A separately recorded20minute keepalive runs in the controller,
            # including while both workers are busy with CPU-only fact analysis.
            time.sleep(30)
        status = (
            json.loads((OUTPUT / "status.json").read_text())
            if (OUTPUT / "status.json").exists()
            else {}
        )
        if process.returncode == 0:
            save(
                SCHEDULE / "status.json",
                dict(state="complete", pid=os.getpid(), summary=status.get("summary")),
            )
            return 0
        error = status.get("error") or {}
        if process.returncode < 0 and restarts < 3:
            restarts += 1
            time.sleep(60)
            continue
        if status.get("error_type") == "TransportError" and (
            error.get("retryable") or error.get("http_status") == 404
        ):
            restarts += 1
            time.sleep(60)
            continue
        save(
            SCHEDULE / "status.json",
            dict(state="needs_code_review", pid=os.getpid(), controller_status=status),
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
