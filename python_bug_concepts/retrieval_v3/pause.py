"""Pause new completions at the existing ledger lock, preserving in-flight work.

This does not change frozen inference code/messages. Current responses can finish
and be cached. New completions cannot reserve an attempt until this barrier ends.
"""
import argparse
import datetime
import fcntl
import json
import os
import signal
import threading
import time
from pathlib import Path

from .client import Client, atomic


def pause(out: Path, seconds: float):
    wake = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: wake.set())
    signal.signal(signal.SIGINT, lambda *_: wake.set())
    with (out / "attempts.jsonl").open("a+") as ledger:
        fcntl.flock(ledger, fcntl.LOCK_EX)
        started = time.time()
        resume = started + seconds
        state = {"status": "paused_new_completions", "barrier_pid": os.getpid(), "started": started,
                 "resume_at": resume, "resume_utc": datetime.datetime.fromtimestamp(resume, datetime.timezone.utc).isoformat(),
                 "reason": "Explicit user request: wait approximately two hours for quota reset, then continue",
                 "inflight_policy": "already reserved requests finish and cache; new reservations block"}
        atomic(out / "PAUSE.json", state)
        early = wake.wait(seconds)
        if not early:
            try:
                Client(out).preflight()
            except Exception as exc:
                atomic(out / "PAUSE.json", {**state, "status": "resume_blocked_endpoint", "error_type": type(exc).__name__, "updated": time.time()})
                wake.wait()
        atomic(out / "PAUSE.json", {**state, "status": "resumed", "resumed_at": time.time(), "early_resume_signal": early})
        fcntl.flock(ledger, fcntl.LOCK_UN)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seconds", type=float, default=7200)
    args = parser.parse_args()
    pause(args.out, args.seconds)
