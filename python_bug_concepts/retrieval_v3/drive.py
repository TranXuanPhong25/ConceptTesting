"""Own the full lifecycle, sparse keepalive, native grading and terminal status."""
import argparse
import json
import os
import threading
import time
from pathlib import Path

from .client import Client, atomic
from .run import execute
from .grade_utility import grade


def main(out):
    atomic(out / "OWNER.json", {"pid": os.getpid(), "started": time.time(), "model": "qwen3.5-27b-awq"})
    finished = threading.Event()
    def keepalive():
        for index in range(3):
            if finished.wait(1200):
                return
            try:
                client = Client(out)
                client.preflight()
                response = client.complete([{"role": "user", "content": "ping"}], stage="keepalive", max_tokens=1, seed=315000 + index)
                atomic(out / f"keepalive_{index}.json", {"status": response["status"], "request_sha256": response["request_sha256"]})
            except Exception as exc:
                atomic(out / f"keepalive_{index}.json", {"error_type": type(exc).__name__})
    thread = threading.Thread(target=keepalive, daemon=True)
    thread.start()
    try:
        for stage in ("retrieve", "judge", "utility"):
            execute(stage, out)
        grade(out)
        from .report import report
        summary = report(out)
        atomic(out / "TERMINAL.json", {"status": "complete", "finished": time.time(), "summary": summary})
    except BaseException as exc:
        atomic(out / "TERMINAL.json", {"status": "stopped", "finished": time.time(), "error_type": type(exc).__name__})
        raise
    finally:
        finished.set()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    main(args.out)
