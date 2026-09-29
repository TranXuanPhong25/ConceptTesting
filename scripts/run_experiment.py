#!/usr/bin/env python3
"""Run the real 4-arm experiment (Direct LLM, MutGen, KITE, Concept extension) over a task
manifest, checkpointed to SQLite for safe resume. See kite_concept/runner.py for the glue and
research/kite-concept-extension-2026-09-26.md for the documented method and deviations.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kite_concept.arms import ArmWorkflows
from kite_concept.checkpoint import CheckpointStore
from kite_concept.knowledge import concept_from_mechanism, retrieve
from kite_concept.llm import configured_llm
from kite_concept.protocol import EqualBudgetProtocol, ProtocolConfig
from kite_concept.runner import build_context, final_detection, install_and_run, load_mechanisms, make_generate, run_pit
from kite_concept.structure import extract_unit_structures

ARMS = ("direct", "mutgen", "kite", "concept")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--checkpoint", default="/tmp/kite-concept-cache/run-state.sqlite")
    parser.add_argument("--outcomes", required=True)
    parser.add_argument("--mechanisms", default="/tmp/kite-concept-cache/kb_mechanisms.jsonl")
    parser.add_argument("--budget", type=int, default=3)
    parser.add_argument("--reruns", type=int, default=2)
    parser.add_argument("--arms", default=",".join(ARMS))
    parser.add_argument("--limit-tasks", type=int, default=0)
    parser.add_argument("--java-home", default=str(Path.home() / ".local/kite/jdk-11.0.32.1+1"))
    args = parser.parse_args()

    rows = json.loads(Path(args.manifest).read_text())["tasks"]
    if args.limit_tasks:
        rows = rows[: args.limit_tasks]
    mechanisms = load_mechanisms(Path(args.mechanisms)) if Path(args.mechanisms).exists() else []
    print(f"tasks={len(rows)} mechanisms={len(mechanisms)}", flush=True)

    llm = configured_llm(temperature=0.1, timeout=180, max_tokens=8192)
    generate = make_generate(llm)
    store = CheckpointStore(args.checkpoint)
    protocol = EqualBudgetProtocol(store, ProtocolConfig(call_budget=args.budget, reruns=args.reruns))
    arms_to_run = args.arms.split(",")

    outcomes_path = Path(args.outcomes)
    outcomes_path.parent.mkdir(parents=True, exist_ok=True)
    existing_outcomes: set[tuple[str, str]] = set()
    if outcomes_path.exists():
        for line in outcomes_path.read_text().splitlines():
            if line.strip():
                row = json.loads(line)
                existing_outcomes.add((row["task_id"], row["arm"]))

    with outcomes_path.open("a", encoding="utf-8") as out_handle:
        for row in rows:
            ctx = build_context(row, Path(args.java_home))
            task = ctx.task
            print(f"=== {task.id} ===", flush=True)

            def correct_check(suite: str) -> tuple[bool, str]:
                return install_and_run(ctx.fixed_checkout, ctx.package, suite)

            profile = task.source
            structures = extract_unit_structures(task.source)
            retrieved = retrieve(mechanisms, profile, structures, limit=max(args.budget, 1)) if mechanisms else []

            for arm in arms_to_run:
                existing = store.get(task.id, arm)
                if existing and existing["status"] == "complete":
                    print(f"{task.id}/{arm} already complete, skipping generation", flush=True)
                else:
                    if existing and existing["status"] == "failed":
                        print(f"{task.id}/{arm} retrying after previous failure: {existing['error'][:150]}", flush=True)
                    try:
                        if arm == "direct":
                            def worker(t, budget, charge):
                                wf = ArmWorkflows(generate, correct_check, lambda s, i: (False, ""), charge)
                                return wf.direct(t, json.dumps(t.context))
                        elif arm == "mutgen":
                            def worker(t, budget, charge):
                                wf = ArmWorkflows(generate, correct_check, lambda s, i: (False, ""), charge)
                                def mutation_rounds(suite):
                                    try:
                                        return run_pit(ctx.fixed_checkout, t.focal_class)
                                    except Exception as exc:
                                        store.event(t.id, arm, "pit_error", {"error": str(exc)[:500]})
                                        return []
                                return wf.mutgen(t, "Summary: " + t.focal_method, mutation_rounds, budget)
                        elif arm == "kite":
                            def target_check(suite, injection):
                                return install_and_run(ctx.buggy_checkout, ctx.package, suite)
                            def worker(t, budget, charge):
                                wf = ArmWorkflows(generate, correct_check, target_check, charge)
                                targets = [(m, {"before": "", "after": "", "trigger_recipe": m.how})
                                           for m, _score in retrieved]
                                return wf.kite(t, targets, budget)
                        else:  # concept
                            def worker(t, budget, charge):
                                wf = ArmWorkflows(generate, correct_check, lambda s, i: (False, ""), charge)
                                concepts = [concept_from_mechanism(m, m.how, m.expected_failure_signal)
                                            for m, _score in retrieved]
                                return wf.concept(t, concepts, budget)
                        result = protocol.run_task(task, arm, worker)
                    except Exception as exc:  # keep going with the next arm/task
                        store.finish(task.id, arm, {}, f"{type(exc).__name__}: {exc}"[:500])
                        print(f"{task.id}/{arm} FAILED: {exc}", flush=True)
                        continue

                if (task.id, arm) in existing_outcomes:
                    continue
                current = store.get(task.id, arm)
                suite = (current or {}).get("payload", {}).get("suite", "") if current else ""
                detection = final_detection(ctx, suite, reruns=args.reruns)
                outcome = {"task_id": task.id, "project": task.project, "arm": arm,
                           "detected": bool(detection["detected"]), "reason": detection.get("reason", ""),
                           "stable": detection.get("stable", False), "ts": time.time()}
                out_handle.write(json.dumps(outcome, sort_keys=True) + "\n")
                out_handle.flush()
                existing_outcomes.add((task.id, arm))
                print(f"{task.id}/{arm} detected={outcome['detected']} ({outcome['reason']})", flush=True)


if __name__ == "__main__":
    main()
