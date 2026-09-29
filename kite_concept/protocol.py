from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .checkpoint import CheckpointStore, task_checkpoint
from .models import TaskRecord

ARMS = ("direct", "mutgen", "kite", "concept")


@dataclass(frozen=True)
class ProtocolConfig:
    call_budget: int = 5
    temperature: float = 0.1
    reruns: int = 2
    seed: int = 260711573


class EqualBudgetProtocol:
    """Arm-neutral orchestration; arm implementations share the same hard call cap."""

    def __init__(self, store: CheckpointStore, config: ProtocolConfig):
        self.store = store
        self.config = config

    def run_task(self, task: TaskRecord, arm: str, worker: Callable[[TaskRecord, int, Callable[..., None]], dict]) -> dict:
        if arm not in ARMS:
            raise ValueError(f"unknown arm {arm}")
        with task_checkpoint(self.store, task.id, arm, self.config.call_budget) as active:
            if not active:
                return self.store.get(task.id, arm)["payload"]  # type: ignore[index]

            def charge(input_tokens: int = 0, output_tokens: int = 0) -> None:
                self.store.record_call(task.id, arm, input_tokens, output_tokens)

            result = worker(task, self.config.call_budget, charge)
            result.setdefault("task_id", task.id)
            result.setdefault("project", task.project)
            result.setdefault("arm", arm)
            self.store.finish(task.id, arm, result)
            return result


def export_results(store_path: Path, output: Path) -> int:
    import sqlite3
    connection = sqlite3.connect(store_path)
    rows = connection.execute("SELECT task_id,arm,status,calls_used,input_tokens,output_tokens,payload,error FROM runs ORDER BY task_id,arm")
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output.open("w", encoding="utf-8") as handle:
        for task_id, arm, status, calls, input_tokens, output_tokens, payload, error in rows:
            handle.write(json.dumps({"task_id": task_id, "arm": arm, "status": status, "calls": calls,
                                     "input_tokens": input_tokens, "output_tokens": output_tokens,
                                     "result": json.loads(payload), "error": error}, sort_keys=True) + "\n")
            count += 1
    connection.close()
    return count

