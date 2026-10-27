"""Validate and compare manually proposed witnesses, outside retrieval."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVAL = HERE / "evaluation"
REFERENCE = Path.home() / ".cache/evalplus/HumanEvalPlus-v0.1.10.jsonl"


def isolated(job: dict) -> dict:
    try:
        result = subprocess.run(
            [sys.executable, "-I", str(HERE / "grader_worker.py")],
            input=json.dumps(job), capture_output=True, text=True, timeout=2.5,
            cwd="/tmp", env={"PATH": os.defpath, "LANG": "C.UTF-8", "PYTHONIOENCODING": "utf-8"},
        )
        if result.returncode:
            return {"status": "worker_failure", "returncode": result.returncode}
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        return {"status": "timeout"}


def grade() -> dict:
    # Deliberately project away hidden test cases and other reference fields.
    refs = {r["task_id"]: {k: r[k] for k in ("entry_point", "prompt", "canonical_solution", "contract")}
            for r in map(json.loads, REFERENCE.read_text().splitlines())}
    tasks = {r["task_id"]: r for r in json.loads((EVAL / "inputs.json").read_text())}
    proposed = json.loads((EVAL / "fault_cases.json").read_text())

    def one(row):
        tid = row["task_id"]
        ref = refs[tid]
        code = ref["prompt"] + ref["canonical_solution"]
        base = {"entry": ref["entry_point"], "args": row["args"]}
        validity = isolated({**base, "mode": "validity", "source": code, "contract": ref["contract"]})
        oracle = isolated({**base, "mode": "value", "source": code})
        actual = isolated({**base, "mode": "value", "source": tasks[tid]["code"]})
        value_equal = oracle.get("status") == actual.get("status") == "ok" and oracle["value"] == actual["value"]
        admissible = validity.get("status") == "ok" and validity.get("value") is True
        mismatch = oracle.get("status") == "ok" and (
            (actual.get("status") == "ok" and not value_equal) or actual.get("status") == "error")
        confirmed = admissible and mismatch and bool(row["concept_ids"])
        return {**row, "validity": validity, "reference": oracle, "put": actual,
                "value_equal": value_equal, "confirmed_for_strict_labels": confirmed}

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(one, proposed))
    report = {"reference_path": str(REFERENCE), "reference_sha256": hashlib.sha256(REFERENCE.read_bytes()).hexdigest(),
              "reference_fields_read": ["entry_point", "prompt", "canonical_solution", "contract"],
              "hidden_test_cases_read": False, "target_execution": "bounded isolated grading workers only",
              "results": results}
    (EVAL / "witness_grading.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    labels = {r["task_id"]: {"concept_ids": [], "witness_ids": [], "rationale": "No confirmed matching mechanism witness in this run."} for r in tasks.values()}
    for i, row in enumerate(results):
        if row["confirmed_for_strict_labels"]:
            item = labels[row["task_id"]]
            item["concept_ids"] = sorted(set(item["concept_ids"]) | set(row["concept_ids"]))
            item["witness_ids"].append(i)
            item["rationale"] = row["rationale"]
    gold = {"label_kind": "single_author_actual_bug_mechanism_with_contract_valid_value_mismatch_or_exception_witness",
            "inputs_sha256": hashlib.sha256((EVAL / "inputs.json").read_bytes()).hexdigest(),
            "witness_report_sha256": hashlib.sha256((EVAL / "witness_grading.json").read_bytes()).hexdigest(),
            "labeled_tasks": sum(bool(x["concept_ids"]) for x in labels.values()), "tasks": labels,
            "limitations": ["Mechanism labels are manually judged by one author; native replay confirms failure and validity, not causal attribution by itself.",
                            "Unlabeled tasks remain misses; no type-only value-equal or timeout case is counted."]}
    (EVAL / "gold.json").write_text(json.dumps(gold, indent=2, ensure_ascii=False) + "\n")
    return gold


if __name__ == "__main__":
    result = grade()
    print(json.dumps({"confirmed_labeled_tasks": result["labeled_tasks"], "cohort": len(result["tasks"])}, indent=2))
