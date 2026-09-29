"""Command-line entry point."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .benchmark import SUBJECTS, TUNING_COUNT, default_picolibc_root
from .runner import run
from .statistics import aggregate, compare


def _rows(path: Path, limit: int) -> list[dict]:
    names = {s.name for s in SUBJECTS[:limit]}
    latest: dict[str, dict] = {}
    for raw in path.read_text().splitlines():
        row = json.loads(raw)
        if row["subject"] in names:
            latest[row["key"]] = row
    return list(latest.values())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("tune", "full"):
        command = sub.add_parser(name)
        command.add_argument("--output-dir", type=Path, required=True)
        command.add_argument("--picolibc-root", type=Path, default=default_picolibc_root())
    report = sub.add_parser("report")
    report.add_argument("--output-dir", type=Path, required=True)
    report.add_argument("--phase", choices=("tune", "full"), default="full")
    args = parser.parse_args()
    if args.command in {"tune", "full"}:
        run(args.output_dir, args.command, args.picolibc_root)
        return
    limit = TUNING_COUNT if args.phase == "tune" else len(SUBJECTS)
    latest = _rows(args.output_dir / "results.jsonl", limit)
    rows = [row for row in latest if row.get("evaluation", {}).get("status") != "generation_error"]
    completed = {arm: sum(row["arm"] == arm for row in rows) for arm in ("direct", "strut", "extended")}
    payload = {
        "completion": {"expected_per_arm": limit, "completed_per_arm": completed, "complete": all(n == limit for n in completed.values())},
        "aggregate": aggregate(rows), "paired": []
    }
    for left, right in (("strut", "direct"), ("extended", "strut")):
        for kind in ("pass", "line", "branch"):
            payload["paired"].append(compare(rows, left, right, kind))
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
