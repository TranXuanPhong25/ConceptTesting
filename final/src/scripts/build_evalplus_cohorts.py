"""Build frozen EvalPlus Mini and Full base-screened cohorts from an existing HumanEval cohort.

Zero LLM calls: re-screens already-generated base-passing PUTs against EvalPlus
`base_input + plus_input` inside the existing bwrap sandbox and records exact
`base_input_keys`, pass/fail status, and C1/C2 coverage for each cohort.
"""
from __future__ import annotations

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
import copy
import hashlib
import inspect
import json
from pathlib import Path
import pickle
import sys
import time

sys.set_int_max_str_digits(0)

from evalplus.data import get_human_eval_plus, get_human_eval_plus_hash
from evalplus.evaluate import get_groundtruth

from final.src.runtime.artifacts import save
from final.src.runtime.execution import ExecutionError, execute

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOURCE = ROOT / "final/out/cohorts/qwen35_27b_humaneval164/cohort.json"


def _frozen(value):
    if isinstance(value, dict):
        return ("dict", tuple(sorted(((_frozen(k), _frozen(v)) for k, v in value.items()), key=repr)))
    if isinstance(value, (list, tuple)):
        return (type(value).__name__, tuple(_frozen(v) for v in value))
    if isinstance(value, (set, frozenset)):
        return (type(value).__name__, tuple(sorted((_frozen(v) for v in value), key=repr)))
    return (type(value).__name__, repr(value))


def _signature_for(prompt: str, entry: str):
    ns: dict = {}
    exec(compile(prompt, "<specification>", "exec"), ns)
    return inspect.signature(ns[entry])


def _input_keys_for_task(prompt: str, entry: str, all_inputs: list) -> list[str]:
    sig = _signature_for(prompt, entry)
    seen = set()
    keys = []
    for raw_args in all_inputs:
        bound = sig.bind(*raw_args)
        bound.apply_defaults()
        key = repr(_frozen(dict(bound.arguments)))
        if key not in seen:
            seen.add(key)
            keys.append(key)
    return keys


def _make_evalplus_check_source(entry: str, all_inputs: list, all_expected: list, atol: float) -> str:
    """Generate a self-contained check(candidate) script for runtime/worker.py base()."""
    payload = base64.b64encode(pickle.dumps(list(zip(all_inputs, all_expected)))).decode("ascii")
    lines = [
        "import base64, copy, math, pickle, sys",
        "sys.set_int_max_str_digits(0)",
        "import numpy as np",
        f"_CASES = pickle.loads(base64.b64decode({payload!r}))",
        f"_ATOL = {float(atol)!r}",
        f"_ENTRY = {entry!r}",
    ]
    if entry == "find_zero":
        lines.append("from evalplus.eval._special_oracle import _poly")
    lines.extend([
        "def _matches(args, actual, expected):",
        "    if _ENTRY == 'find_zero':",
        "        return abs(_poly(args[0], actual)) <= _ATOL",
        "    if actual == expected:",
        "        return True",
        "    atol = _ATOL",
        "    float_expected = isinstance(expected, float) or (isinstance(expected, (list, tuple)) and bool(expected) and all(isinstance(x, float) for x in expected))",
        "    if atol == 0 and float_expected:",
        "        atol = 1e-6",
        "    if atol and type(actual) == type(expected):",
        "        if isinstance(expected, (list, tuple)) and len(actual) != len(expected):",
        "            return False",
        "        return bool(np.allclose(actual, expected, rtol=1e-7, atol=atol))",
        "    return False",
        "def check(candidate):",
        "    for args, expected in _CASES:",
        "        actual = candidate(*copy.deepcopy(args))",
        "        assert _matches(args, actual, expected)",
    ])
    return "\n".join(lines) + "\n"


def _screen_program(prompt: str, entry: str, check_source: str, code: str, timeout: float):
    job = {
        "mode": "base",
        "context": prompt,
        "source": code,
        "entry": entry,
        "base": check_source,
        "timeout": timeout,
        "seed": 20261030,
        "trace": True,
    }
    try:
        outcome = execute(job)
    except ExecutionError as exc:
        outcome = {"status": "error", "exception": type(exc).__name__}
    return outcome


def build_cohort(source_path: Path, output_path: Path, *, mini: bool, workers: int = 8):
    t0 = time.time()
    source = json.loads(source_path.read_text())
    problems = get_human_eval_plus(mini=mini)
    gt = get_groundtruth(problems, get_human_eval_plus_hash(mini=mini), [])
    label = "evalplus_mini_v0.1.10" if mini else "evalplus_full_v0.1.10"
    timeout = 45.0

    new_tasks = []
    jobs = []
    for task_idx, row in enumerate(source["tasks"]):
        tid = row["task_id"]
        prob = problems[tid]
        entry = prob["entry_point"]
        all_inputs = list(prob["base_input"]) + list(prob["plus_input"])
        all_expected = list(gt[tid]["base"]) + list(gt[tid]["plus"])
        base_keys = sorted(set(row.get("base_input_keys", [])) | set(_input_keys_for_task(prob["prompt"], entry, all_inputs)))
        check_src = _make_evalplus_check_source(entry, all_inputs, all_expected, prob.get("atol", 0.0))

        new_row = copy.deepcopy(row)
        new_row["base_input_keys"] = base_keys
        new_tasks.append(new_row)

        for prog_idx, prog in enumerate(new_row["programs"]):
            if prog["base"]["status"] == "pass":
                jobs.append((task_idx, prog_idx, prob["prompt"], entry, check_src, prog["code"]))

    print(f"[{label}] Screening {len(jobs)} base-passing PUTs across {len(new_tasks)} tasks with {workers} workers...")
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_map = {
            pool.submit(_screen_program, prompt, entry, check_src, code, timeout): (task_idx, prog_idx)
            for (task_idx, prog_idx, prompt, entry, check_src, code) in jobs
        }
        for future in as_completed(future_map):
            task_idx, prog_idx = future_map[future]
            outcome = future.result()
            # Drop bulky full input_keys list per program (task-level base_input_keys already holds the full set).
            outcome.pop("input_keys", None)
            new_tasks[task_idx]["programs"][prog_idx]["base"] = outcome
            done += 1
            if done % 200 == 0 or done == len(jobs):
                print(f"[{label}] {done}/{len(jobs)} PUTs screened ({time.time() - t0:.1f}s)")

    total_pass = 0
    eligible_tasks = 0
    for row in new_tasks:
        passing = sum(1 for p in row["programs"] if p["base"]["status"] == "pass")
        row["base_pass"] = passing
        if passing:
            eligible_tasks += 1
            total_pass += passing

    cohort_sha = hashlib.sha256(json.dumps(new_tasks, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    result = {
        **source,
        "base_suite": label,
        "source_cohort": str(source_path.relative_to(ROOT)),
        "tasks": new_tasks,
        "cohort_sha256": cohort_sha,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save(output_path, result)
    print(f"[{label}] Saved {output_path}: {eligible_tasks}/164 eligible tasks, {total_pass} eligible base-passing PUTs ({time.time() - t0:.1f}s)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--variants", nargs="+", choices=("mini", "full"), default=["mini", "full"])
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    for variant in args.variants:
        out = ROOT / f"final/out/cohorts/qwen35_27b_humaneval_plus_{variant}/cohort.json"
        build_cohort(args.source, out, mini=(variant == "mini"), workers=args.workers)


if __name__ == "__main__":
    main()
