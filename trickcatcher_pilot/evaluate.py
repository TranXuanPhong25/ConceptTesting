"""Score literal inputs against EvalPlus contracts, canonical code, and PUTs.

The generator never receives the canonical code or contracts. Each execution
runs in a child process with a timeout; model output is parsed as literals.
"""

from __future__ import annotations

import argparse
import ast
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any


_CHILD = r'''
import contextlib, io, json, sys
payload = json.load(sys.stdin)
try:
    namespace = {"__name__": "__test__"}
    with contextlib.redirect_stdout(io.StringIO()):
        exec("from typing import *", namespace)
        if payload["contract"]:
            exec(payload["contract"], namespace)
            namespace["__contract"](*payload["args"])
        exec(payload["code"], namespace)
        result = namespace[payload["entry_point"]](*payload["args"])
    print(json.dumps({"status": "pass", "value": result}, allow_nan=True))
except AssertionError as exc:
    print(json.dumps({"status": "invalid", "error": str(exc)[:200]}))
except BaseException as exc:
    print(json.dumps({"status": "error", "error": type(exc).__name__ + ": " + str(exc)[:200]}))
'''


def _contract_source(task: dict[str, Any]) -> str:
    if not task.get("contract"):
        return ""
    functions = [node for node in ast.parse(task["prompt"]).body if isinstance(node, ast.FunctionDef)]
    entry = next(node for node in functions if node.name == task["entry_point"])
    return f"def __contract({ast.unparse(entry.args)}):\n{task['contract']}\n    return True\n"


def _execute(code: str, entry_point: str, args: list[Any], contract: str, timeout: float) -> dict[str, Any]:
    payload = {"code": code, "entry_point": entry_point, "args": args, "contract": contract}
    try:
        process = subprocess.run(
            [sys.executable, "-I", "-c", _CHILD], input=json.dumps(payload),
            text=True, capture_output=True, timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired:
        return {"status": "timeout"}
    try:
        return json.loads(process.stdout)
    except ValueError:
        return {"status": "runner_error", "error": process.stderr[-300:]}


def _same(a: Any, b: Any, atol: float) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool):
        if math.isnan(float(a)) or math.isnan(float(b)):
            return math.isnan(float(a)) and math.isnan(float(b))
        return math.isclose(a, b, rel_tol=0, abs_tol=atol)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_same(x, y, atol) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_same(a[k], b[k], atol) for k in a)
    return a == b


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    from evalplus.data import get_human_eval_plus

    reference = get_human_eval_plus()
    source_root = Path(args.artifact) / "Datasets" / "EvalPlus" / "PUTs"
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    summary: dict[str, Any] = {"tasks": 0, "generated_inputs": 0, "valid_inputs": 0, "exposing_inputs": 0, "exposed_tasks": 0}
    with Path(args.pred).open() as predictions, output.open("w") as destination:
        for line in predictions:
            if not line.strip():
                continue
            pred = json.loads(line)
            task_num = pred["task_num"]
            task = reference[f"HumanEval/{task_num}"]
            source = (source_root / f"HumanEval_{task_num}" / "put0.py").read_text()
            canonical = task["prompt"] + task["canonical_solution"]
            contract = _contract_source(task)
            results = []
            for params in pred.get("inputs", []):
                ref = _execute(canonical, task["entry_point"], params, contract, args.timeout)
                if ref["status"] != "pass":
                    results.append({"input": params, "reference": ref, "valid": False, "exposed": False})
                    continue
                buggy = _execute(source, task["entry_point"], params, "", args.timeout)
                exposed = buggy["status"] != "pass" or not _same(ref["value"], buggy["value"], task["atol"])
                results.append({"input": params, "reference": ref, "buggy": buggy, "valid": True, "exposed": exposed})
            result = {
                "task_num": task_num, "arm": pred["arm"], "results": results,
                "generated": len(results), "valid": sum(item["valid"] for item in results),
                "exposing": sum(item["exposed"] for item in results),
                "task_exposed": any(item["exposed"] for item in results),
                "generation_error": pred.get("error", ""),
            }
            destination.write(json.dumps(result, ensure_ascii=False, allow_nan=True) + "\n")
            destination.flush()
            summary["tasks"] += 1
            summary["generated_inputs"] += result["generated"]
            summary["valid_inputs"] += result["valid"]
            summary["exposing_inputs"] += result["exposing"]
            summary["exposed_tasks"] += result["task_exposed"]
            print(f"task={task_num} arm={pred['arm']} valid={result['valid']} exposed={result['exposing']}", flush=True)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pred", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--artifact", default="/tmp/TrickCatcher-upstream")
    parser.add_argument("--timeout", type=float, default=2)
    print(json.dumps(evaluate(parser.parse_args())))


if __name__ == "__main__":
    main()
