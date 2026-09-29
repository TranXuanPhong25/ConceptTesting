from __future__ import annotations

import hashlib
import json
import random
import re
from pathlib import Path
from typing import Iterable

PROJECT_COUNTS = {"Cli": 24, "Compress": 32, "Csv": 11, "JacksonDatabind": 51, "Jsoup": 54}
TOTAL_TASKS = sum(PROJECT_COUNTS.values())


def validate_manifest(rows: Iterable[dict]) -> list[dict]:
    rows = list(rows)
    ids = [(row.get("project"), row.get("bug_id"), row.get("focal_class"), row.get("focal_method")) for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("task manifest contains duplicate method tasks")
    counts = {project: sum(row.get("project") == project for row in rows) for project in PROJECT_COUNTS}
    if len(rows) != TOTAL_TASKS or counts != PROJECT_COUNTS:
        raise ValueError(f"expected exact KITE split {PROJECT_COUNTS}, got {counts} ({len(rows)} total)")
    return rows


def seeded_tuning_subset(rows: Iterable[dict], size: int = 40, seed: int = 260711573) -> list[dict]:
    rows = list(rows)
    if not 30 <= size <= 50:
        raise ValueError("tuning subset must contain 30-50 tasks")
    by_project = {p: [r for r in rows if r["project"] == p] for p in PROJECT_COUNTS}
    if any(not values for values in by_project.values()):
        raise ValueError("tuning population must span all five projects")
    rng = random.Random(seed)
    chosen: list[dict] = []
    remaining = size
    projects = list(PROJECT_COUNTS)
    for index, project in enumerate(projects):
        available = by_project[project]
        quota = round(size * PROJECT_COUNTS[project] / TOTAL_TASKS)
        quota = max(1, min(quota, len(available), remaining - (len(projects) - index - 1)))
        chosen.extend(rng.sample(available, quota))
        remaining -= quota
    pool = [r for r in rows if r not in chosen]
    chosen.extend(rng.sample(pool, remaining))
    return sorted(chosen, key=lambda r: (r["project"], int(r["bug_id"]), r["focal_method"]))


def write_manifest(path: Path, rows: Iterable[dict], provenance: dict) -> None:
    tasks = list(rows)
    payload = {"schema_version": 1, "provenance": provenance, "tasks": tasks}
    canonical = json.dumps(tasks, sort_keys=True, separators=(",", ":"))
    payload["task_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def changed_methods_from_diff(diff: str) -> list[dict[str, str]]:
    """Conservative reconstruction helper: accept patches localized to one Java method."""
    files = re.findall(r"^\+\+\+ b/(.*?\.java)$", diff, re.MULTILINE)
    hunks = re.findall(r"^@@[^@]*@@\s*(.*)$", diff, re.MULTILINE)
    signatures = []
    method = re.compile(r"(?:public|protected|private|static|final|synchronized|native|abstract|\s)+[\w<>\[\], ?]+\s+(\w+)\s*\(")
    for heading in hunks:
        match = method.search(heading)
        if match:
            signatures.append(match.group(1))
    if len(set(files)) == 1 and len(set(signatures)) == 1:
        return [{"file": files[0], "method": signatures[0]}]
    return []

