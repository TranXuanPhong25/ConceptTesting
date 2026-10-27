"""Render the completed quality study, including concrete wrong-concept cases."""
from __future__ import annotations

import json
from pathlib import Path

from .client import atomic
from .run import HERE


def render(out: Path):
    summary = json.loads((out / "QUALITY_SUMMARY.json").read_text())
    tasks = json.loads((out / "QUALITY_TASKS.json").read_text())
    q = summary["quality"]
    rows = ["# Concept retrieval quality — Qwen3.5-27B-AWQ", "",
            "This study evaluates every returned concept, its concrete where/how/what, and native test utility. Old coverage alone does not establish quality.", "",
            "## Card selection quality on 113 PUTs", "",
            "| Metric | Structural v2 | Qwen v3 |", "| --- | ---: | ---: |"]
    metrics = [
        ("Returned concepts", "returned_concepts", False),
        ("Concepts matching frozen bug-family labels / returned (incomplete labels)", "frozen_label_precision_returned", True),
        ("Frozen-label correct family hit@3", "frozen_label_hit_at_3", False),
        ("Frozen-label family + first faulty site hit@3", "frozen_label_site_hit_at_3", False),
        ("Blinded judge: actual-bug grade >=2 / all returned (missing grades count 0)", "judge_precision_returned_conservative", True),
        ("Blinded judge: actual-bug grade >=2 / fixed 3 slots per task", "judge_precision_fixed3", True),
        ("Blinded judge: mean relevance grade (0–3)", "judge_mean_grade_0_to_3", False),
        ("Blinded judge: irrelevant/wrong cards", "judge_irrelevant_or_wrong_count", False),
        ("Blinded judge: context-only cards without actual-bug link", "judge_context_only_count", False),
        ("Blinded judge: hit@3", "judge_hit_at_3", False),
        ("Blinded judge: MRR@3", "judge_mrr_at_3", False),
        ("Blinded judge: nDCG@3 relative to pooled returned candidates", "judge_ndcg_at_3_pool_relative", False),
    ]
    for label, key, percent in metrics:
        values = [f"{q[name][key]:.1%}" if percent else str(round(q[name][key], 4)) for name in ("v2", "v3")]
        rows.append(f"| {label} | {values[0]} | {values[1]} |")
    rows += ["", f"Judge schema valid on {summary['judge_valid_tasks']}/113 tasks. V3 retrieval schema failures: {summary['retrieval_schema_failures']}. Invalid/missing task responses remain in task denominators.", "",
             "## Concrete where / how / what", "", "| Blinded binding judgment | v2 | v3 |", "| --- | ---: | ---: |"]
    for label, key in (("Where: cited site is actually faulty", "judge_where_accuracy"), ("How: causal mechanism is correct", "judge_how_accuracy"), ("What: consequence/input class distinguishes correct behavior", "judge_what_accuracy")):
        rows.append(f"| {label} | {q['v2'][key]:.1%} | {q['v3'][key]:.1%} |")
    rows.append(f"| All three fields correct (count) | {q['v2']['judge_all_where_how_what_count']} | {q['v3']['judge_all_where_how_what_count']} |")
    utility = summary["native_utility"]
    rows += ["", "## Native test utility on the fixed 40-task cohort", "",
             "All three arms use one matched Qwen test-generation call, at most three tests, the same per-task seed and 800-token completion cap. Utility prompts receive card definitions only, not v3's extra instantiated explanations. References and official contracts are used only afterwards by the native grader.", "",
             "| Native outcome | No concept | v2 concepts | v3 concepts |", "| --- | ---: | ---: | ---: |"]
    for label, key in (("Proposed tests", "proposed_tests"), ("Official-contract-valid tests", "valid_tests"), ("Reference-correct expected outputs", "oracle_correct_tests"), ("Confirmed bug tasks / 40", "confirmed_bug_tasks"), ("False-alarm tests (wrong oracle with failing assertion)", "false_alarm_tests"), ("Tasks with false alarms", "false_alarm_tasks"), ("Unresolved workers", "unresolved_workers")):
        rows.append("| " + label + " | " + " | ".join(str(utility[arm][key]) for arm in ("plain", "v2", "v3")) + " |")
    for name, stats in utility["paired"].items():
        rows.append(f"\n{name}: {stats['wins']} paired wins / {stats['losses']} losses on confirmed bug tasks.")
    rows += ["", "A failing test counts as a confirmed bug only when its input passes the official contract, the proposed expected result agrees with the reference, and the PUT differs or raises. Wrong expected outputs are reported as false alarms. This distinguishes useful guidance from plausible wording.", "",
             "## Wrong or weak concept examples", "",
             "These are concrete saved failures; the grader reasons are model judgments, not silently adopted ground truth.", ""]
    examples = []
    for task in tasks:
        for name in ("v2", "v3"):
            for row in task["systems"][name]["selected"]:
                grade = row.get("judge_card")
                if grade and grade["grade"] <= 1:
                    examples.append({"task_id": task["task_id"], "system": name, "concept_id": row["concept_id"], "line": row["line"], "grade": grade["grade"], "reason": grade.get("reason", ""), "how": row["how"]})
    atomic(out / "WRONG_OR_WEAK_EXAMPLES.json", examples)
    shown = []
    for method in ("v2", "v3"):
        subset = [r for r in examples if r["system"] == method]
        subset.sort(key=lambda r: (r["grade"], int(r["task_id"].split("/")[1]), r["concept_id"]))
        shown += subset[:5]
    for row in shown:
        rows += [f"- {row['task_id']} / {row['system']} / `{row['concept_id']}` / line {row['line']} / grade {row['grade']}: {row['reason']}"]
    rows += ["", "## Limits and inference accounting", ""]
    rows += ["- " + limit for limit in summary["limits"]]
    rows += ["- Method names and ranks were hidden from the judge; style of instantiated explanations can still reveal their origin. Shared cards were deduplicated and received one common grade.",
             "- Graded nDCG is relative to the union of the two methods' returned cards, not an exhaustively judged 162-card relevance set.",
             "- The old 91-task mechanism label set is incomplete; unmatched cards on unlabeled tasks require independent review rather than automatically being known wrong.", "",
             "Main-run inference accounting:", "", "```json", json.dumps(summary["usage"], indent=2), "```", "",
             "The separate engineering-review and four-canary artifacts are preserved outside the main-run folder. Their usage is additional and is not hidden in task-only metrics.", "",
             "## Artifacts", "",
             "- `QUALITY_SUMMARY.json`: aggregate selection, binding, utility and usage metrics.",
             "- `QUALITY_TASKS.json`: all 113 tasks, ranks, frozen-label matches and blind grades.",
             "- `utility_grading.json`: executable test inputs, proposed oracle, reference and PUT results.",
             "- `judge_jobs/`, `judged/`: exact anonymous mappings and grading responses.",
             "- `retrieval_jobs/`, `retrieved/`, `calls/`: frozen public-only requests and raw cached model responses.", ""]
    (HERE / "RESULTS.md").write_text("\n".join(rows))
    return summary


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    render(p.parse_args().out)
