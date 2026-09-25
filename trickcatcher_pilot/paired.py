"""Paired bug-exposure analysis across one or more EvalPlus task slices."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def _load(paths: list[str]) -> dict[int, dict[str, Any]]:
    rows = {}
    for path in paths:
        with Path(path).open() as handle:
            for line in handle:
                if line.strip():
                    row = json.loads(line)
                    if row["task_num"] in rows:
                        raise ValueError(f"duplicate task {row['task_num']} across input files")
                    rows[row["task_num"]] = row
    return rows


def _mcnemar(a_only: int, b_only: int) -> float:
    n = a_only + b_only
    if not n:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, k) for k in range(min(a_only, b_only) + 1)) / 2**n)


def compare(a_paths: list[str], b_paths: list[str], both_valid_only: bool = False) -> dict[str, Any]:
    a, b = _load(a_paths), _load(b_paths)
    tasks = sorted(a.keys() & b.keys())
    if both_valid_only:
        tasks = [task for task in tasks if a[task]["valid"] and b[task]["valid"]]
    a_only = [task for task in tasks if a[task]["task_exposed"] and not b[task]["task_exposed"]]
    b_only = [task for task in tasks if b[task]["task_exposed"] and not a[task]["task_exposed"]]
    return {
        "paired_tasks": len(tasks),
        "both_valid_only": both_valid_only,
        "a_exposed_tasks": sum(a[task]["task_exposed"] for task in tasks),
        "b_exposed_tasks": sum(b[task]["task_exposed"] for task in tasks),
        "a_exposing_inputs": sum(a[task]["exposing"] for task in tasks),
        "b_exposing_inputs": sum(b[task]["exposing"] for task in tasks),
        "a_valid_inputs": sum(a[task]["valid"] for task in tasks),
        "b_valid_inputs": sum(b[task]["valid"] for task in tasks),
        "a_only": a_only,
        "b_only": b_only,
        "mcnemar_exact_two_sided": _mcnemar(len(a_only), len(b_only)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--a", action="append", required=True, help="One or more JSONL files for arm A")
    parser.add_argument("--b", action="append", required=True, help="One or more JSONL files for arm B")
    parser.add_argument("--both-valid-only", action="store_true")
    args = parser.parse_args()
    print(json.dumps(compare(args.a, args.b, args.both_valid_only), indent=2))


if __name__ == "__main__":
    main()
