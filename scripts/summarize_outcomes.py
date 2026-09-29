#!/usr/bin/env python3
"""Summarize real outcomes_*.jsonl rows into per-arm/per-project RBDR and paired stats.

Per "Validity and statistics" in research/kite-concept-extension-2026-09-26.md, RBDR uses every
task in the *declared population* as denominator, including generation failures -- not just the
rows that happen to be present in the outcomes file yet. Pass --manifest so partial runs report
population-correct RBDR instead of silently using len(rows-so-far) as the denominator.

Usage:
  summarize_outcomes.py OUTCOMES.jsonl [--manifest MANIFEST.json] [--left kite --right direct]

Always reports, in addition to any --left/--right pair: concept vs kite and concept vs mutgen
(matched on task_id, exact McNemar + seeded paired bootstrap CI), since those are the two
comparisons this experiment is designed around.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kite_concept.metrics import paired_comparison, project_rbdr, rbdr


def _report_pair(rows: list[dict], left_arm: str, right_arm: str) -> None:
    left = {r["task_id"]: r["detected"] for r in rows if r["arm"] == left_arm}
    right = {r["task_id"]: r["detected"] for r in rows if r["arm"] == right_arm}
    matched = sorted(set(left) & set(right))
    print(f"matched tasks for {left_arm} vs {right_arm}: {len(matched)}")
    if len(matched) >= 1:
        comparison = paired_comparison({k: left[k] for k in matched}, {k: right[k] for k in matched})
        print(json.dumps(comparison, indent=2, sort_keys=True))
    else:
        print("no matched tasks yet; paired comparison not computable")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("outcomes")
    parser.add_argument("--manifest", default="", help="task manifest JSON; sets the RBDR "
                         "denominator to the declared population (overall and per-project) "
                         "instead of just the rows present so far.")
    parser.add_argument("--left", default="kite")
    parser.add_argument("--right", default="direct")
    args = parser.parse_args()

    rows = [json.loads(l) for l in Path(args.outcomes).read_text().splitlines() if l.strip()]
    arms = sorted({r["arm"] for r in rows})

    population: int | None = None
    project_population: dict[str, int] | None = None
    if args.manifest:
        manifest_tasks = json.loads(Path(args.manifest).read_text())["tasks"]
        population = len(manifest_tasks)
        project_population = dict(Counter(t["project"] for t in manifest_tasks))

    print(f"total real (task,arm) rows: {len(rows)}")
    print(f"distinct tasks covered: {len({r['task_id'] for r in rows})}")
    if population is not None:
        print(f"declared population (from manifest): {population} tasks; per project: {project_population}")
    for arm in arms:
        arm_rows = [r for r in rows if r["arm"] == arm]
        n_detected = sum(1 for r in arm_rows if r["detected"])
        denom = population if population is not None else len(arm_rows)
        print(f"  {arm}: {n_detected}/{len(arm_rows)} rows resolved so far "
              f"-> RBDR {n_detected}/{denom} = {rbdr(arm_rows, denom):.4f} "
              f"(denominator: {'declared population' if population is not None else 'rows resolved so far'})")
        by_project = project_rbdr(arm_rows, project_population)
        print(f"    per-project RBDR: {by_project}")

    print()
    _report_pair(rows, args.left, args.right)
    print()
    if {args.left, args.right} != {"concept", "kite"}:
        _report_pair(rows, "concept", "kite")
        print()
    if {args.left, args.right} != {"concept", "mutgen"}:
        _report_pair(rows, "concept", "mutgen")


if __name__ == "__main__":
    main()
