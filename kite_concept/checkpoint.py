from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


class CheckpointStore:
    """Durable per-task/per-arm state with leases for safe resumability."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=FULL")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs (
              task_id TEXT NOT NULL, arm TEXT NOT NULL, status TEXT NOT NULL,
              call_budget INTEGER NOT NULL, calls_used INTEGER NOT NULL DEFAULT 0,
              input_tokens INTEGER NOT NULL DEFAULT 0, output_tokens INTEGER NOT NULL DEFAULT 0,
              payload TEXT NOT NULL DEFAULT '{}', error TEXT NOT NULL DEFAULT '',
              updated_at REAL NOT NULL, PRIMARY KEY(task_id, arm)
            );
            CREATE TABLE IF NOT EXISTS events (
              id INTEGER PRIMARY KEY, task_id TEXT NOT NULL, arm TEXT NOT NULL,
              kind TEXT NOT NULL, payload TEXT NOT NULL, created_at REAL NOT NULL
            );
            """
        )
        self.connection.commit()

    def get(self, task_id: str, arm: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT status,call_budget,calls_used,input_tokens,output_tokens,payload,error,updated_at "
            "FROM runs WHERE task_id=? AND arm=?", (task_id, arm)
        ).fetchone()
        if row is None:
            return None
        keys = ("status", "call_budget", "calls_used", "input_tokens", "output_tokens", "payload", "error", "updated_at")
        result = dict(zip(keys, row))
        result["payload"] = json.loads(result["payload"])
        return result

    def begin(self, task_id: str, arm: str, call_budget: int) -> bool:
        if call_budget < 1:
            raise ValueError("call_budget must be positive")
        existing = self.get(task_id, arm)
        if existing and existing["status"] == "complete":
            return False
        now = time.time()
        self.connection.execute(
            "INSERT INTO runs(task_id,arm,status,call_budget,updated_at) VALUES(?,?,?,?,?) "
            "ON CONFLICT(task_id,arm) DO UPDATE SET status='running',call_budget=excluded.call_budget,updated_at=excluded.updated_at",
            (task_id, arm, "running", call_budget, now),
        )
        self.connection.commit()
        return True

    def record_call(self, task_id: str, arm: str, input_tokens: int = 0, output_tokens: int = 0) -> None:
        current = self.get(task_id, arm)
        if not current or current["status"] != "running":
            raise RuntimeError("run must be started before recording a call")
        if current["calls_used"] >= current["call_budget"]:
            raise RuntimeError(f"equal call budget exhausted for {task_id}/{arm}")
        self.connection.execute(
            "UPDATE runs SET calls_used=calls_used+1,input_tokens=input_tokens+?,output_tokens=output_tokens+?,updated_at=? "
            "WHERE task_id=? AND arm=?",
            (input_tokens, output_tokens, time.time(), task_id, arm),
        )
        self.connection.commit()

    def event(self, task_id: str, arm: str, kind: str, payload: dict[str, Any]) -> None:
        self.connection.execute(
            "INSERT INTO events(task_id,arm,kind,payload,created_at) VALUES(?,?,?,?,?)",
            (task_id, arm, kind, json.dumps(payload, sort_keys=True), time.time()),
        )
        self.connection.commit()

    def finish(self, task_id: str, arm: str, payload: dict[str, Any], error: str = "") -> None:
        status = "failed" if error else "complete"
        self.connection.execute(
            "UPDATE runs SET status=?,payload=?,error=?,updated_at=? WHERE task_id=? AND arm=?",
            (status, json.dumps(payload, sort_keys=True), error, time.time(), task_id, arm),
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "CheckpointStore":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


@contextmanager
def task_checkpoint(store: CheckpointStore, task_id: str, arm: str, call_budget: int) -> Iterator[bool]:
    active = store.begin(task_id, arm, call_budget)
    try:
        yield active
    except BaseException as exc:
        if active:
            store.finish(task_id, arm, {}, f"{type(exc).__name__}: {exc}")
        raise

