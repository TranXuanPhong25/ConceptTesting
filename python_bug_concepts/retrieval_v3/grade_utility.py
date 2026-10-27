"""Grade the matched, model-generated tests using independent native execution."""
from __future__ import annotations

import json
import math
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ..retrieval_v2.grade_witnesses import isolated
from .client import atomic
from .run import OLD, tasks


def equal(left, right, atol=0.0):
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left == right or abs(left - right) <= atol
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(equal(a, b, atol) for a, b in zip(left, right))
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(equal(left[k], right[k], atol) for k in left)
    return left == right


def valid_tests(response):
    rows = (response.get("parsed") or {}).get("tests")
    if response.get("status") != "received" or not isinstance(rows, list) or len(rows) > 3:
        return [], "invalid_tests_array"
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("args"), list) or "expected" not in row:
            return [], "invalid_test_record"
        def finite(value):
            if isinstance(value, float):
                return math.isfinite(value)
            if isinstance(value, list):
                return all(finite(x) for x in value)
            if isinstance(value, dict):
                return all(isinstance(k, str) and finite(x) for k, x in value.items())
            return value is None or isinstance(value, (str, int, bool))
        if not finite(row):
            return [], "non_json_or_nonfinite_data"
    return rows, None


def grade(out: Path):
    references = {r["task_id"]: {k: r[k] for k in ("entry_point", "prompt", "canonical_solution", "contract", "atol")}
                  for r in map(json.loads, (Path.home() / ".cache/evalplus/HumanEvalPlus-v0.1.10.jsonl").read_text().splitlines())}
    source = {t["task_id"]: t for t in tasks()}
    jobs = []
    for p in sorted((out / "utility").glob("*.json")):
        record = json.loads(p.read_text())
        rows, error = valid_tests(record["response"])
        for i, row in enumerate(rows):
            jobs.append({"task_id": record["task_id"], "arm": record["arm"], "sample": i, **row})
        atomic(out / "utility_validation" / p.name, {"task_id": record["task_id"], "arm": record["arm"], "tests": len(rows), "schema_error": error})

    def one(job):
        task_id = job["task_id"]
        ref = references[task_id]
        base = {"entry": ref["entry_point"], "args": job["args"]}
        code = ref["prompt"] + ref["canonical_solution"]
        validity = isolated({**base, "mode": "validity", "source": code, "contract": ref["contract"]})
        if validity.get("status") != "ok" or validity.get("value") is not True:
            return {**job, "validity": validity, "input_valid": False, "confirmed_bug": False, "false_alarm": False}
        expected = isolated({**base, "mode": "value", "source": code})
        actual = isolated({**base, "mode": "value", "source": source[task_id]["code"]})
        oracle_correct = expected.get("status") == "ok" and equal(job["expected"], expected.get("value"), ref.get("atol", 0.0))
        actual_differs = expected.get("status") == "ok" and (actual.get("status") == "error" or actual.get("status") == "ok" and not equal(actual["value"], expected["value"], ref.get("atol", 0.0)))
        assertion_fails = actual.get("status") == "error" or actual.get("status") == "ok" and not equal(actual["value"], job["expected"], ref.get("atol", 0.0))
        return {**job, "validity": validity, "reference": expected, "put": actual, "input_valid": True,
                "oracle_correct": oracle_correct, "actual_bug_input": actual_differs,
                "confirmed_bug": oracle_correct and actual_differs,
                "false_alarm": expected.get("status") == "ok" and not oracle_correct and assertion_fails,
                "worker_unresolved": expected.get("status") != "ok" or actual.get("status") not in {"ok", "error"}}

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(one, jobs))
    atomic(out / "utility_grading.json", {"reference_fields_used": ["entry_point", "prompt", "canonical_solution", "contract", "atol"],
                                           "hidden_tests_used": False, "results": results})
    return results


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    print(len(grade(args.out)), "native test results")
