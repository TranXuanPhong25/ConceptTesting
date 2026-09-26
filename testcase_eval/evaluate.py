#!/usr/bin/env python3
"""Execute generated Task 2 inputs on all languages and score Fault Exposure.

Mirrors the official pipeline (`sandbox.py` Task 2 branch + `stat_task2.py`):
every accepted submission of the problem in `submission_lite` (any language)
plus the one target wrong submission run on the generated input; expected
output = official consensus; exposed = target crashes/TLE/MLE or disagrees.

Adds, per record, the strict validity gate (validator acceptance + all
accepted submissions succeed and agree) and a low-load re-run of every
time_limit_exceeded result so TLE verdicts are not artefacts of parallel load.

Resume-safe: executions are cached in SQLite and the output JSONL is appended
per record; re-running skips records already scored.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from testcase_eval.data import load_rows
from testcase_eval.metrics import official_consensus, official_exposed, strict_consensus
from testcase_eval.sandbox import Executor, language_family, run_python_program
from testcase_eval.store import DATA_DIR, ExecCache, JsonlWriter, read_jsonl, resolve_test, sha

TIME_LIMIT = 3.0
MEMORY_LIMIT = 512


class Evaluator:
    def __init__(self, cache_path: str | Path | None = None, validators_path: str | Path | None = None, submissions: list[dict] | None = None) -> None:
        self.cache = ExecCache(cache_path or DATA_DIR / "exec_cache.sqlite")
        self.executor = Executor()
        rows = submissions if submissions is not None else load_rows("submission_lite")
        self.by_id = {int(r["id"]): r for r in rows}
        self.right: dict[str, list[dict]] = defaultdict(list)
        for r in rows:
            if r["type"] == "right_submission":
                self.right[r["problem_id"]].append(r)
        self.validators: dict[str, str] = {}
        if validators_path:
            for row in read_jsonl(validators_path):
                if row.get("code"):
                    self.validators[row["problem_id"]] = row["code"]

    # -- execution -------------------------------------------------------
    def run(self, submission: dict, test: str, test_sha: str, recheck: bool = False) -> dict[str, Any]:
        key = f"sub:{submission['id']}"
        cached = self.cache.get("exec", key, test_sha)
        if cached is not None and not (recheck and cached.get("result") == "time_limit_exceeded" and not cached.get("rechecked")):
            return cached
        if language_family(submission["language"]) is None:
            result = {"result": "unsupported", "output": "", "error": submission["language"], "time": 0.0}
        else:
            result = self.executor.execute(submission["language"], submission["source"], test, TIME_LIMIT, MEMORY_LIMIT)
        result = {k: result.get(k) for k in ("result", "output", "error", "time")}
        result["output"] = (result["output"] or "")[: 8 * 1024 * 1024]
        if recheck:
            result["rechecked"] = True
        self.cache.put("exec", key, test_sha, result)
        return result

    def validate(self, problem_id: str, test: str, test_sha: str) -> str:
        code = self.validators.get(problem_id)
        if code is None:
            return "missing"
        key = f"val:{problem_id}:{sha(code)[:16]}"
        cached = self.cache.get("validator", key, test_sha)
        if cached is not None:
            return cached["verdict"]
        return validator_verdict(code, test, self.cache, key, test_sha)

    # -- scoring ---------------------------------------------------------
    def score(self, prediction: dict[str, Any], recheck: bool = False) -> dict[str, Any]:
        problem_id = prediction["problem_id"]
        submission_id = int(prediction["submission_id"])
        target = self.by_id.get(submission_id)
        test = resolve_test(prediction)
        base = {
            "problem_id": problem_id,
            "submission_id": submission_id,
            "condition": prediction.get("condition"),
            "language": target["language"] if target else None,
            "family": language_family(target["language"]) if target else None,
            "target_verdict": target["verdict"] if target else None,
            "test_sha": sha(test) if test else None,
            "test_bytes": len(test),
        }
        if not test.strip() or test.strip() == "ERROR" or target is None:
            return {**base, "input_present": False, "validator": "no_input", "official_consensus": False,
                    "exposed_official": False, "strict_valid": False, "exposed_strict": False, "invalid_reason": "no_input"}
        test_sha = base["test_sha"]
        right_runs = []
        for sub in self.right[problem_id]:
            run = self.run(sub, test, test_sha, recheck)
            right_runs.append({"id": int(sub["id"]), "language": sub["language"], "result": run["result"],
                               "output": run["output"], "time": run.get("time")})
        expected = official_consensus([r["output"] for r in right_runs if r["result"] == "success_run"])
        target_run = self.run(target, test, test_sha, recheck)
        exposed = official_exposed(expected, target_run["result"], target_run["output"])
        strict_expected, strict_reason = strict_consensus(right_runs)
        verdict = self.validate(problem_id, test, test_sha)
        validator_ok = verdict == "accepted"
        strict_valid = validator_ok and strict_expected is not None
        invalid_reason = None
        if not validator_ok:
            invalid_reason = f"validator_{verdict}"
        elif strict_expected is None:
            invalid_reason = strict_reason
        exposed_strict = strict_valid and official_exposed(strict_expected, target_run["result"], target_run["output"])
        return {
            **base,
            "input_present": True,
            "validator": verdict,
            "official_consensus": expected != "",
            "right_results": [{"id": r["id"], "result": r["result"], "time": r["time"]} for r in right_runs],
            "target_result": target_run["result"],
            "target_time": target_run.get("time"),
            "exposed_official": exposed,
            "strict_valid": strict_valid,
            "exposed_strict": exposed_strict,
            "invalid_reason": invalid_reason,
            "expected_head": (strict_expected or expected or "")[:200],
            "target_head": (target_run["output"] or "")[:200],
        }


def validator_verdict(code: str, test: str, cache: ExecCache | None = None, key: str | None = None, test_sha: str | None = None) -> str:
    run = run_python_program(code, test, timeout=20.0)
    if run["result"] == "success_run":
        verdict = "accepted"
    elif run["result"] == "runtime_error" and run.get("returncode") in (1, 2, 3):
        verdict = "rejected"
    else:
        verdict = f"error_{run['result']}"
    if cache is not None and key and test_sha:
        cache.put("validator", key, test_sha, {"verdict": verdict, "stderr": (run.get("error") or "")[-300:]})
    return verdict


def evaluate_file(pred_path: str, out_path: str, validators: str | None, workers: int = 12, recheck_workers: int = 2, limit: int = 0) -> dict[str, Any]:
    evaluator = Evaluator(validators_path=validators)
    predictions = read_jsonl(pred_path)
    if limit:
        predictions = predictions[:limit]
    done = {(r.get("condition"), int(r["submission_id"])) for r in read_jsonl(out_path)}
    todo = [p for p in predictions if (p.get("condition"), int(p["submission_id"])) not in done]
    print(f"{len(predictions)} predictions, {len(todo)} to score", flush=True)

    writer = JsonlWriter(out_path)
    chunk = 240
    for start in range(0, len(todo), chunk):
        batch = todo[start : start + chunk]
        # Pass 1: parallel execution fills the cache.
        with ThreadPoolExecutor(workers) as pool:
            first = list(pool.map(lambda p: evaluator.score(p), batch))
        # Pass 2: re-run every TLE (accepted or target) at low concurrency, then re-score.
        needs = [i for i, r in enumerate(first) if r.get("target_result") == "time_limit_exceeded"
                 or any(x["result"] == "time_limit_exceeded" for x in r.get("right_results", []))]
        with ThreadPoolExecutor(recheck_workers) as pool:
            for i, row in zip(needs, pool.map(lambda i: evaluator.score(batch[i], recheck=True), needs)):
                first[i] = row
        for row in first:
            writer.write(row)
        print(f"scored {start + len(batch)}/{len(todo)} (rechecked {len(needs)} TLE record(s) in chunk)", flush=True)
    writer.close()
    return summarize(read_jsonl(out_path))


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    groups: dict[str, list] = defaultdict(list)
    for r in rows:
        groups["all"].append(r)
        groups[r.get("family") or "unsupported"].append(r)
    for name, items in groups.items():
        n = len(items)
        out[name] = {
            "n": n,
            "fault_exposure_official": sum(r["exposed_official"] for r in items) / max(1, n),
            "fault_exposure_strict": sum(r["exposed_strict"] for r in items) / max(1, n),
            "input_present": sum(r["input_present"] for r in items) / max(1, n),
            "validator_accept": sum(r["validator"] == "accepted" for r in items) / max(1, n),
            "official_consensus": sum(r["official_consensus"] for r in items) / max(1, n),
            "strict_valid": sum(r["strict_valid"] for r in items) / max(1, n),
        }
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pred", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--validators", default=None)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--recheck-workers", type=int, default=2)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    print(json.dumps(evaluate_file(args.pred, args.out, args.validators, args.workers, args.recheck_workers, args.limit), indent=2))


if __name__ == "__main__":
    main()
