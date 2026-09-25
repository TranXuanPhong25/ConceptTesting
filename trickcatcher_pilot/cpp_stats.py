"""Task-level exact paired comparison for the C++ direct-input pilot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from trickcatcher_pilot.paired import _mcnemar


def compare(a: Path, b: Path) -> dict:
    rows_a = {row["problem_id"]: row for line in a.read_text().splitlines() if line.strip() for row in [json.loads(line)]}
    rows_b = {row["problem_id"]: row for line in b.read_text().splitlines() if line.strip() for row in [json.loads(line)]}
    ids = sorted(rows_a.keys() & rows_b.keys())
    ids = [pid for pid in ids if rows_a[pid]["evaluable"] and rows_b[pid]["evaluable"]]
    a_only = [pid for pid in ids if rows_a[pid]["task_exposed"] and not rows_b[pid]["task_exposed"]]
    b_only = [pid for pid in ids if rows_b[pid]["task_exposed"] and not rows_a[pid]["task_exposed"]]
    return {"paired_tasks": len(ids), "a_exposed": sum(rows_a[pid]["task_exposed"] for pid in ids),
            "b_exposed": sum(rows_b[pid]["task_exposed"] for pid in ids),
            "a_only": a_only, "b_only": b_only,
            "exact_mcnemar_p": _mcnemar(len(a_only), len(b_only))}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--a", required=True)
    parser.add_argument("--b", required=True)
    args = parser.parse_args()
    print(json.dumps(compare(Path(args.a), Path(args.b)), indent=2))


if __name__ == "__main__":
    main()
