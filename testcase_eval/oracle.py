#!/usr/bin/env python3
"""Python-subset Fault Exposure oracle compatible with TestCase-Eval Task 2."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from testcase_eval.data import is_python3_language


def outputs_equal(left: str, right: str, tolerance: float = 1e-12) -> bool:
    left_lines = [line.strip() for line in left.strip().splitlines()]
    right_lines = [line.strip() for line in right.strip().splitlines()]
    if left_lines == right_lines:
        return True
    left_tokens, right_tokens = left.strip().split(), right.strip().split()
    if len(left_tokens) != len(right_tokens):
        return False
    booleans = {"yes", "no", "true", "false"}
    for a, b in zip(left_tokens, right_tokens):
        try:
            if not math.isclose(float(a), float(b), rel_tol=0.0, abs_tol=tolerance):
                return False
        except ValueError:
            aa = a.lower() if a.lower() in booleans else a
            bb = b.lower() if b.lower() in booleans else b
            if aa != bb:
                return False
    return True


def execute_python(source: str, input_data: str, timeout: int = 5) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "solution.py"
        path.write_text(source)
        try:
            result = subprocess.run(
                [sys.executable, "-I", "-u", str(path)],
                input=input_data if input_data.endswith("\n") else input_data + "\n",
                text=True,
                capture_output=True,
                timeout=timeout,
                cwd=td,
            )
        except subprocess.TimeoutExpired:
            return {"status": "time_limit_exceeded", "output": "", "error": "timeout"}
    if result.returncode != 0:
        return {"status": "runtime_error", "output": result.stdout, "error": result.stderr[-500:]}
    return {"status": "success_run", "output": result.stdout, "error": result.stderr[-500:]}


def consensus_output(outputs: list[str]) -> str | None:
    if not outputs:
        return None
    if len(outputs) == 1:
        return outputs[0]
    for i, left in enumerate(outputs):
        if any(outputs_equal(left, right) for right in outputs[i + 1 :]):
            return left
    return None


def evaluate_fault_exposure_record(
    prediction: dict[str, Any], submissions: list[dict[str, Any]], timeout: int = 5, max_right: int = 5
) -> dict[str, Any]:
    problem_id = prediction["problem_id"]
    submission_id = int(prediction["submission_id"])
    compatible = [
        row
        for row in submissions
        if row["problem_id"] == problem_id and is_python3_language(str(row.get("language", "")))
    ]
    right = [row for row in compatible if row["type"] == "right_submission"][:max_right]
    wrong = next((row for row in compatible if int(row["id"]) == submission_id and row["type"] == "wrong_submission"), None)
    right_runs = [execute_python(row["source"], prediction.get("test", ""), timeout) for row in right]
    expected = consensus_output([run["output"] for run in right_runs if run["status"] == "success_run"])
    if expected is None or wrong is None:
        return {
            "problem_id": problem_id,
            "submission_id": submission_id,
            "valid_input": False,
            "exposed": False,
            "reason": "missing correct consensus or Python target submission",
        }
    wrong_run = execute_python(wrong["source"], prediction.get("test", ""), timeout)
    exposed = wrong_run["status"] in {"runtime_error", "time_limit_exceeded", "memory_limit_exceeded"}
    if wrong_run["status"] == "success_run":
        exposed = not outputs_equal(wrong_run["output"], expected)
    return {
        "problem_id": problem_id,
        "submission_id": submission_id,
        "valid_input": True,
        "expected_output": expected,
        "wrong_status": wrong_run["status"],
        "wrong_output": wrong_run.get("output", ""),
        "exposed": exposed,
        "reason": "output mismatch or failure" if exposed else "wrong implementation matched correct consensus",
    }


def evaluate_file(predictions_path: str, submissions_path: str, output_path: str, timeout: int = 5) -> dict[str, Any]:
    with Path(predictions_path).open() as handle:
        predictions = [json.loads(line) for line in handle if line.strip()]
    with Path(submissions_path).open() as handle:
        submissions = [json.loads(line) for line in handle if line.strip()]
    results = [evaluate_fault_exposure_record(row, submissions, timeout) for row in predictions]
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as handle:
        for row in results:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    valid = sum(row["valid_input"] for row in results)
    exposed = sum(row["exposed"] for row in results)
    summary = {
        "records": len(results),
        "valid_inputs": valid,
        "exposed": exposed,
        "fault_exposure": exposed / max(1, len(results)),
        "fault_exposure_given_valid": exposed / max(1, valid),
        "scope": "TestCase-Eval Task 2 Python/PyPy subset",
    }
    print(json.dumps(summary, indent=2))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pred", required=True)
    parser.add_argument("--submissions", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--timeout", type=int, default=5)
    args = parser.parse_args()
    evaluate_file(args.pred, args.submissions, args.out, args.timeout)


if __name__ == "__main__":
    main()
