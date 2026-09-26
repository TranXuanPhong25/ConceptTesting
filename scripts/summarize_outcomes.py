#!/usr/bin/env python3
"""Summarize real outcomes_*.jsonl rows into per-arm/per-project RBDR and paired stats.

Usage: summarize_outcomes.py OUTCOMES.jsonl POPULATION_SIZE [--left kite --right direct]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kite_concept.metrics import paired_comparison, project_rbdr, rbdr


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("outcomes")
    parser.add_argument("--left", default="kite")
    parser.add_argument("--right", default="direct")
    args = parser.parse_args()

    rows = [json.loads(l) for l in Path(args.outcomes).read_text().splitlines() if l.strip()]
    arms = sorted({r["arm"] for r in rows})
    print(f"total real (task,arm) rows: {len(rows)}")
    print(f"distinct tasks covered: {len({r['task_id'] for r in rows})}")
    for arm in arms:
        arm_rows = [r for r in rows if r["arm"] == arm]
        n_detected = sum(1 for r in arm_rows if r["detected"])
        print(f"  {arm}: {n_detected}/{len(arm_rows)} detected (of rows completed for this arm)")
        by_project = project_rbdr(arm_rows)
        print(f"    by project (over completed rows only): {by_project}")

    left = {r["task_id"]: r["detected"] for r in rows if r["arm"] == args.left}
    right = {r["task_id"]: r["detected"] for r in rows if r["arm"] == args.right}
    matched = sorted(set(left) & set(right))
    print(f"matched tasks for {args.left} vs {args.right}: {len(matched)}")
    if len(matched) >= 1:
        comparison = paired_comparison({k: left[k] for k in matched}, {k: right[k] for k in matched})
        print(json.dumps(comparison, indent=2, sort_keys=True))
    else:
        print("no matched tasks yet; paired comparison not computable")


if __name__ == "__main__":
    main()
