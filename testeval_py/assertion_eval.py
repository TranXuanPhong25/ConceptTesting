#!/usr/bin/env python3
"""Measure TestEval syntax, execution, and assertion correctness."""

from __future__ import annotations

import argparse
import ast
import json
import signal
from pathlib import Path
from typing import Any


def evaluate_predictions(path: str, timeout: int = 5) -> dict[str, Any]:
    with Path(path).open() as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    total = syntax = executable = assertions = 0
    failures: list[dict[str, Any]] = []
    for row in rows:
        for target_line, testcase in row.get("tests", {}).items():
            total += 1
            outcome = _evaluate_one(row, testcase, timeout)
            syntax += outcome["syntax"]
            executable += outcome["executable"]
            assertions += outcome["assertion"]
            if not outcome["assertion"]:
                failures.append({"task_num": row["task_num"], "target_line": int(target_line), "reason": outcome["reason"]})
    result = {
        "tasks": len(rows),
        "tests": total,
        "syntax_correct": syntax,
        "executable_correct": executable,
        "assertion_correct": assertions,
        "syntax_rate": syntax / max(1, total),
        "executable_rate": executable / max(1, total),
        "assertion_rate": assertions / max(1, total),
        "assertion_failures": failures,
    }
    return result


def _evaluate_one(row: dict[str, Any], testcase: str, timeout: int) -> dict[str, Any]:
    try:
        test_tree = ast.parse(testcase)
    except SyntaxError as exc:
        return {"syntax": 0, "executable": 0, "assertion": 0, "reason": f"syntax: {exc.msg}"}
    test_functions = [node for node in test_tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    has_assert = any(isinstance(node, ast.Assert) for node in ast.walk(test_tree))
    namespace: dict[str, Any] = {}
    try:
        with _time_limit(timeout):
            exec(compile(row["code"], "under_test.py", "exec"), namespace)
            exec(compile(testcase, "generated_test.py", "exec"), namespace)
            name = f"test_{row['func_name']}"
            if name not in namespace or not test_functions or f"solution.{row['func_name']}" not in testcase:
                return {"syntax": 1, "executable": 0, "assertion": 0, "reason": "missing test function or focal call"}
            namespace[name]()
    except AssertionError:
        return {"syntax": 1, "executable": 1, "assertion": 0, "reason": "assertion failed"}
    except Exception as exc:
        return {"syntax": 1, "executable": 0, "assertion": 0, "reason": f"runtime: {type(exc).__name__}"}
    return {"syntax": 1, "executable": 1, "assertion": int(has_assert), "reason": "no assertion" if not has_assert else ""}


class _time_limit:
    def __init__(self, seconds: int):
        self.seconds = seconds

    def __enter__(self):
        self.previous = signal.getitimer(signal.ITIMER_REAL)
        signal.signal(signal.SIGALRM, self._raise)
        signal.setitimer(signal.ITIMER_REAL, self.seconds)

    def __exit__(self, exc_type, exc_value, traceback):
        signal.setitimer(signal.ITIMER_REAL, *self.previous)

    @staticmethod
    def _raise(*_args):
        raise TimeoutError


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pred", required=True, help="TestEval prediction JSONL")
    parser.add_argument("--timeout", type=int, default=5)
    args = parser.parse_args()
    print(json.dumps(evaluate_predictions(args.pred, args.timeout), indent=2))


if __name__ == "__main__":
    main()
