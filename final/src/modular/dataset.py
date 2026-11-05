"""Pinned HumanEval specifications and domain metadata."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]
DATA_SHA256 = "b2adeeae8b383b6f0c615746a397f25c8abe44da4afb29cd10e6c4bbf0463fd3"
METADATA_PATH = HERE / "data/contracts.json"

def load_tasks():
    path = HERE / "data" / "humaneval.jsonl"
    if hashlib.sha256(path.read_bytes()).hexdigest() != DATA_SHA256:
        raise ValueError("Bundled HumanEval dataset checksum mismatch")
    tasks = [json.loads(line) for line in path.read_text().splitlines()]
    if len(tasks) != 164 or {t["task_id"] for t in tasks} != {f"HumanEval/{i}" for i in range(164)}:
        raise ValueError("Need exactly the original 164 HumanEval tasks")
    return sorted(tasks, key=lambda t: int(t["task_id"].split("/")[1]))

def load_metadata():
    return json.loads(METADATA_PATH.read_text())
