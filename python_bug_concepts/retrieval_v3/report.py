"""Quality, ranking and native utility metrics, with failures kept in denominators."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from .client import atomic
from .run import HERE, OLD, tasks, verify_inputs


def discounted(grades):
    return sum((2 ** grade - 1) / math.log2(i + 2) for i, grade in enumerate(grades[:3]))


def report(out: Path):
    verify_inputs()
    gold = json.loads((OLD / "gold.json").read_text())["tasks"]
    site_gold = json.loads((OLD / "mechanism_sites.json").read_text())["tasks"]
    records = []
    for task in tasks():
        stem = task["task_id"].replace("/", "_")
        path = out / "retrieved" / (stem + ".json")
        result = json.loads(path.read_text()) if path.exists() else {"baseline": [], "selected": [], "schema_error": "missing"}
        path = out / "judged" / (stem + ".json")
        judged = json.loads(path.read_text()) if path.exists() else {"valid_schema": False}
        grades, binding_grades = {}, {}
        if judged["valid_schema"]:
            for row in judged["response"]["parsed"]["cards"]:
                grades[judged["mapping"]["cards"][row["key"]]] = row
            for row in judged["response"]["parsed"]["bindings"]:
                mapping = judged["mapping"]["bindings"][row["key"]]
                binding_grades[(mapping["system"], mapping["rank"])] = row
        all_pool_grades = sorted((g["grade"] for g in grades.values()), reverse=True)
        ideal = discounted(all_pool_grades)
        methods = {}
        for name, selected in (("v2", result["baseline"]), ("v3", result["selected"])):
            rows = []
            for rank, row in enumerate(selected[:3]):
                cid = row["concept_id"]
                hit = cid in gold[task["task_id"]]["concept_ids"]
                lines = {s["line"] for s in site_gold.get(task["task_id"], {}).get(cid, [])}
                card_grade = grades.get(cid)
                binding = binding_grades.get((name, rank))
                rows.append({**row, "rank": rank + 1, "frozen_family_match": hit, "frozen_site_match": hit and row["line"] in lines,
                             "judge_card": card_grade, "judge_binding": binding})
            relevant = [r["rank"] for r in rows if r["frozen_family_match"]]
            judged_relevant = [r["rank"] for r in rows if r["judge_card"] and r["judge_card"]["grade"] >= 2]
            methods[name] = {"selected": rows, "frozen_hit_at_1": bool(relevant) and min(relevant) == 1,
                             "frozen_hit_at_3": bool(relevant), "frozen_reciprocal_rank": 1 / min(relevant) if relevant else 0,
                             "frozen_site_hit_at_3": any(r["frozen_site_match"] for r in rows),
                             "judged_hit_at_3": bool(judged_relevant),
                             "judged_reciprocal_rank": 1 / min(judged_relevant) if judged_relevant else 0,
                             "judged_ndcg_at_3": discounted([r["judge_card"]["grade"] if r["judge_card"] else 0 for r in rows]) / ideal if ideal else 0}
        records.append({"task_id": task["task_id"], "split": task["split"], "frozen_labeled": bool(gold[task["task_id"]]["concept_ids"]),
                        "retrieval_schema_error": result.get("schema_error"), "judge_valid": judged["valid_schema"], "systems": methods})

    summaries = {}
    for name in ("v2", "v3"):
        counts = [r["systems"][name] for r in records]
        rows = [s for c in counts for s in c["selected"]]
        known_grades = [r["judge_card"]["grade"] for r in rows if r["judge_card"]]
        positive = sum(g >= 2 for g in known_grades)
        binding = [r["judge_binding"] for r in rows if r["judge_binding"]]
        summaries[name] = {
            "tasks": 113, "returned_concepts": len(rows), "tasks_with_candidates": sum(bool(c["selected"]) for c in counts),
            "frozen_label_hit_at_1": sum(c["frozen_hit_at_1"] for c in counts),
            "frozen_label_hit_at_3": sum(c["frozen_hit_at_3"] for c in counts),
            "frozen_label_site_hit_at_3": sum(c["frozen_site_hit_at_3"] for c in counts),
            "frozen_label_mrr_at_3": sum(c["frozen_reciprocal_rank"] for c in counts) / 113,
            "frozen_label_precision_returned": sum(r["frozen_family_match"] for r in rows) / len(rows) if rows else 0,
            "frozen_label_precision_fixed3": sum(r["frozen_family_match"] for r in rows) / (113 * 3),
            "judge_graded_concepts": len(known_grades), "judge_grade_ge2_concepts": positive,
            "judge_precision_returned_conservative": positive / len(rows) if rows else 0,
            "judge_precision_graded_only": positive / len(known_grades) if known_grades else 0,
            "judge_precision_fixed3": positive / (113 * 3),
            "judge_mean_grade_0_to_3": sum(known_grades) / len(known_grades) if known_grades else 0,
            "judge_context_only_count": sum(g == 1 for g in known_grades),
            "judge_irrelevant_or_wrong_count": sum(g == 0 for g in known_grades),
            "judge_hit_at_3": sum(c["judged_hit_at_3"] for c in counts),
            "judge_mrr_at_3": sum(c["judged_reciprocal_rank"] for c in counts) / 113,
            "judge_ndcg_at_3_pool_relative": sum(c["judged_ndcg_at_3"] for c in counts) / 113,
            "judge_where_accuracy": sum(b["where"] for b in binding) / len(binding) if binding else 0,
            "judge_how_accuracy": sum(b["how"] for b in binding) / len(binding) if binding else 0,
            "judge_what_accuracy": sum(b["what"] for b in binding) / len(binding) if binding else 0,
            "judge_all_where_how_what_count": sum(all(b[k] for k in ("where", "how", "what")) for b in binding),
        }
        summaries[name]["splits"] = {split: {
            "tasks": sum(r["split"] == split for r in records),
            "frozen_label_hit_at_3": sum(r["systems"][name]["frozen_hit_at_3"] for r in records if r["split"] == split),
            "frozen_label_site_hit_at_3": sum(r["systems"][name]["frozen_site_hit_at_3"] for r in records if r["split"] == split),
            "judge_hit_at_3": sum(r["systems"][name]["judged_hit_at_3"] for r in records if r["split"] == split),
        } for split in ("development", "audit")}

    utility_rows = json.loads((out / "utility_grading.json").read_text())["results"] if (out / "utility_grading.json").exists() else []
    cohort = set(json.loads((HERE / "data/utility_cohort.json").read_text())["tasks"])
    utility = {}
    sets = {}
    for arm in ("plain", "v2", "v3"):
        rows = [r for r in utility_rows if r["arm"] == arm]
        valid = [r for r in rows if r["input_valid"]]
        valid_reference = [r for r in valid if r.get("reference", {}).get("status") == "ok"]
        bug_tasks = {r["task_id"] for r in rows if r["confirmed_bug"]}
        false_tasks = {r["task_id"] for r in rows if r["false_alarm"]}
        sets[arm] = bug_tasks
        utility[arm] = {"tasks": len(cohort), "proposed_tests": len(rows), "valid_tests": len(valid),
                        "oracle_correct_tests": sum(r.get("oracle_correct", False) for r in rows),
                        "oracle_accuracy_given_valid_reference": sum(r.get("oracle_correct", False) for r in rows) / len(valid_reference) if valid_reference else 0,
                        "confirmed_bug_tests": sum(r["confirmed_bug"] for r in rows), "confirmed_bug_tasks": len(bug_tasks),
                        "false_alarm_tests": sum(r["false_alarm"] for r in rows), "false_alarm_tasks": len(false_tasks),
                        "bug_task_ids": sorted(bug_tasks), "false_alarm_task_ids": sorted(false_tasks),
                        "unresolved_workers": sum(r.get("worker_unresolved", False) for r in rows)}
    utility["paired"] = {}
    for other in ("plain", "v2"):
        utility["paired"]["v3_vs_" + other] = {"wins": len(sets["v3"] - sets[other]), "losses": len(sets[other] - sets["v3"]),
                                                 "win_tasks": sorted(sets["v3"] - sets[other]), "loss_tasks": sorted(sets[other] - sets["v3"])}
    usage = {"attempts": 0, "received": 0, "unknown_usage": 0, "input_tokens": 0, "output_tokens": 0, "by_stage": {}}
    ledger = out / "attempts.jsonl"
    if ledger.exists():
        usage["attempts"] = len(ledger.read_text().splitlines())
    for p in (out / "calls").glob("*/response.json"):
        row = json.loads(p.read_text())
        stage = usage["by_stage"].setdefault(row["stage"], {"received": 0, "input_tokens": 0, "output_tokens": 0})
        if row["status"] == "received":
            usage["received"] += 1
            stage["received"] += 1
            for key, field in (("input_tokens", "prompt_tokens"), ("output_tokens", "completion_tokens")):
                value = row.get("usage", {}).get(field) or 0
                usage[key] += value
                stage[key] += value
        elif row.get("unknown_completion_usage"):
            usage["unknown_usage"] += 1
    summary = {"model": "qwen3.5-27b-awq", "quality": summaries,
               "judge_valid_tasks": sum(r["judge_valid"] for r in records),
               "retrieval_schema_failures": sum(bool(r["retrieval_schema_error"]) for r in records),
               "native_utility": utility, "usage": usage,
               "limits": ["Same-model judge is auxiliary, not independent truth.", "Frozen v2 labels are incomplete and corpus design saw HumanEval public source.",
                          "Utility arms match test-generation calls; v3 has extra retrieval inference cost.",
                          "Native failing tests establish utility and oracle correctness, not automatic causal attribution to a concept."]}
    atomic(out / "QUALITY_SUMMARY.json", summary)
    atomic(out / "QUALITY_TASKS.json", records)
    return {"summary_path": str(out / "QUALITY_SUMMARY.json"), "retrieval_v2_site_hit": summaries["v2"]["frozen_label_site_hit_at_3"],
            "retrieval_v3_site_hit": summaries["v3"]["frozen_label_site_hit_at_3"],
            "utility_plain": utility["plain"]["confirmed_bug_tasks"], "utility_v2": utility["v2"]["confirmed_bug_tasks"], "utility_v3": utility["v3"]["confirmed_bug_tasks"]}


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    print(json.dumps(report(p.parse_args().out), indent=2))
