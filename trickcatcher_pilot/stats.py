"""Paired task-level results for the three TrickCatcher prompt arms."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def _load(path: str) -> dict[int, dict[str, Any]]:
    rows = {}
    with Path(path).open() as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                rows[row["task_num"]] = row
    return rows


def _mcnemar(a_only: int, b_only: int) -> float:
    n = a_only + b_only
    if not n:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, k) for k in range(min(a_only, b_only) + 1)) / 2**n)


def summarize(baseline_path: str, generic_path: str, concept_path: str) -> dict[str, Any]:
    rows = {name: _load(path) for name, path in (
        ("baseline", baseline_path), ("generic", generic_path), ("concept", concept_path)
    )}
    tasks = sorted(set.intersection(*(set(group) for group in rows.values())))
    arms = {}
    for name, group in rows.items():
        selected = [group[task] for task in tasks]
        arms[name] = {
            "exposed_tasks": sum(row["task_exposed"] for row in selected),
            "exposing_inputs": sum(row["exposing"] for row in selected),
            "valid_inputs": sum(row["valid"] for row in selected),
            "generated_inputs": sum(row["generated"] for row in selected),
            "task_ids": [row["task_num"] for row in selected if row["task_exposed"]],
        }
    comparisons = {}
    for a, b in (("baseline", "generic"), ("baseline", "concept"), ("generic", "concept")):
        a_only = sum(rows[a][task]["task_exposed"] and not rows[b][task]["task_exposed"] for task in tasks)
        b_only = sum(rows[b][task]["task_exposed"] and not rows[a][task]["task_exposed"] for task in tasks)
        comparisons[f"{a}_vs_{b}"] = {"a_only": a_only, "b_only": b_only, "mcnemar_exact_two_sided": _mcnemar(a_only, b_only)}
    return {"paired_tasks": len(tasks), "task_ids": tasks, "arms": arms, "comparisons": comparisons}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--generic", required=True)
    parser.add_argument("--concept", required=True)
    args = parser.parse_args()
    print(json.dumps(summarize(args.baseline, args.generic, args.concept), indent=2))


if __name__ == "__main__":
    main()
