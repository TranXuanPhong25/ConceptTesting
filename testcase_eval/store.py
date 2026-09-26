"""Content-addressed test storage and a resumable execution cache (SQLite)."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import zlib
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent / "data"
INLINE_LIMIT = 64 * 1024


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "surrogatepass")).hexdigest()


def store_test(text: str, tests_dir: Path | None = None) -> dict[str, Any]:
    """Keep small inputs inline; spill large generator outputs to data/tests/<sha>.txt."""
    digest = sha(text)
    if len(text) <= INLINE_LIMIT:
        return {"test": text, "test_sha": digest}
    directory = tests_dir or DATA_DIR / "tests"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{digest}.txt"
    if not path.exists():
        path.write_text(text)
    return {"test": None, "test_path": str(path.relative_to(DATA_DIR.parent.parent)) if path.is_relative_to(DATA_DIR.parent.parent) else str(path), "test_sha": digest, "test_bytes": len(text)}


def resolve_test(row: dict[str, Any]) -> str:
    if row.get("test") is not None:
        return str(row["test"])
    path = row.get("test_path")
    if not path:
        return ""
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = DATA_DIR.parent.parent / candidate
    return candidate.read_text() if candidate.exists() else ""


class ExecCache:
    """(key, input_sha) -> execution result; thread-safe, survives restarts."""

    def __init__(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), check_same_thread=False, timeout=60)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS runs (kind TEXT, key TEXT, input_sha TEXT, payload BLOB, "
            "PRIMARY KEY (kind, key, input_sha))"
        )
        self.conn.commit()
        self.lock = threading.Lock()

    def get(self, kind: str, key: str, input_sha: str) -> dict[str, Any] | None:
        with self.lock:
            row = self.conn.execute(
                "SELECT payload FROM runs WHERE kind=? AND key=? AND input_sha=?", (kind, key, input_sha)
            ).fetchone()
        return json.loads(zlib.decompress(row[0])) if row else None

    def put(self, kind: str, key: str, input_sha: str, value: dict[str, Any]) -> None:
        blob = zlib.compress(json.dumps(value, ensure_ascii=False).encode(), 6)
        with self.lock:
            self.conn.execute("INSERT OR REPLACE INTO runs VALUES (?,?,?,?)", (kind, key, input_sha, blob))
            self.conn.commit()


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    rows = []
    with p.open() as handle:
        for line in handle:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # tolerate a torn final line after a crash
    return rows


class JsonlWriter:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("a")
        self.lock = threading.Lock()

    def write(self, row: dict[str, Any]) -> None:
        with self.lock:
            self.handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            self.handle.flush()

    def close(self) -> None:
        self.handle.close()
