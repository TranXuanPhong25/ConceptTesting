#!/usr/bin/env python3
"""Task 1 (Fault Coverage): generation and scoring on a problem subset.

Official setting (generate.py/stat_task1.py @ 45275c6): 20 samples of the
Task1 prompt per problem at temperature 1.0; every test runs on every
submission of the problem in `submission_all`; Cov@k = share of wrong
submissions exposed by at least one of the first k tests.

Conditions:
  cot      the official Task1 (CoT) prompt, 20 independent samples
  concept  one "fault catalogue" call enumerates 20 distinct, atomic failure
           hypotheses for plausible wrong solutions (Specification Grounding:
           one rule -> one test), then sample i targets hypothesis i with the
           validator constraint block and the same validator repair loop as
           Task 2.  Generator programs are allowed for large inputs.

Strict Cov@k counts a test only if the validator accepts it and all accepted
submissions succeed and agree on it.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from testcase_eval.data import load_rows
from testcase_eval.evaluate import Evaluator
from testcase_eval.generate import GEN_INSTRUCTIONS, Pipeline, render_rules, split_official_prompt
from testcase_eval.llm import Gemini
from testcase_eval.metrics import official_consensus, official_exposed, strict_consensus
from testcase_eval.store import JsonlWriter, read_jsonl, resolve_test, sha, store_test
from testcase_eval.validator import parse_json_block

SAMPLES = 20

CATALOGUE_PROMPT = """You are preparing hack tests for a Codeforces problem.  Many contestants submitted WRONG
solutions to it.  Enumerate {k} DISTINCT, atomic hypotheses about how plausible wrong solutions fail
(wrong greedy/idea, off-by-one or boundary, overflow, special cases such as n=1 or all-equal values,
stale state across test cases, precision, worst-case complexity -> TLE/MLE, recursion depth, ...).
Each hypothesis must name the input property that exposes it.  Cover different mechanisms.

{problem}

Input constraints:
{rules}

Return ONLY a JSON object in a ```json fence:
{{"hypotheses": [{{"mechanism": "...", "trigger_condition": "...", "expected_correct_behavior": "...",
  "failure_mode": "WA | TLE | RE | MLE", "needs_large_input": false}}]}}"""


def run_generation(args: argparse.Namespace) -> None:
    problems = open(args.problems).read().split()
    task1 = {r["extra_info"]["problem_id"]: r for r in load_rows("task1")}
    validators = {r["problem_id"]: r for r in read_jsonl(args.validators) if r.get("code") and r.get("status") == "ok"}
    done = {(r["problem_id"], int(r["response_id"])) for r in read_jsonl(args.out)}
    gen = Gemini(temperature=1.0, max_output_tokens=2048 if args.condition == "cot" else 8192, timeout=180)
    helper = Gemini(temperature=1.0, max_output_tokens=4096, timeout=120)
    pipeline = Pipeline(gen, helper, validators, {})
    writer = JsonlWriter(args.out)
    catalogues: dict[str, list] = {}
    cat_path = args.out.replace(".jsonl", "_catalogue.jsonl")
    for row in read_jsonl(cat_path):
        catalogues[row["problem_id"]] = row["hypotheses"]
    cat_writer = JsonlWriter(cat_path)

    def catalogue(pid: str) -> list:
        if pid in catalogues:
            return catalogues[pid]
        trace: list = []
        rules = render_rules((validators.get(pid) or {}).get("rules") or [])
        text = pipeline.call(gen, trace, "catalogue", CATALOGUE_PROMPT.format(k=SAMPLES, problem=split_official_prompt(task1[pid]["prompt"][0]["content"]), rules=rules))
        parsed = parse_json_block(text)
        hyps = [h for h in (parsed or {}).get("hypotheses", []) if isinstance(h, dict)] if isinstance(parsed, dict) else []
        catalogues[pid] = hyps
        cat_writer.write({"problem_id": pid, "hypotheses": hyps, "usage": {k: sum(t.get(k, 0) for t in trace) for k in ("input_tokens", "output_tokens")}})
        return hyps

    def one(item: tuple[str, int]) -> None:
        pid, rid = item
        record = task1[pid]
        trace: list = []
        verdict, kind, hyp = None, "plaintext", None
        if args.condition == "cot":
            response = pipeline.call(gen, trace, "generate", record["prompt"][0]["content"])
            test = pipeline.extract(trace, response)
        else:
            hyps = catalogue(pid)
            hyp = hyps[rid % len(hyps)] if hyps else None
            rules = render_rules((validators.get(pid) or {}).get("rules") or [])
            block = ""
            if hyp:
                block = "**Target failure hypothesis for plausible wrong solutions:**\n" + "\n".join(f"- {k}: {v}" for k, v in hyp.items()) + "\n\n"
            trigger = " AND makes the trigger condition of the target hypothesis hold" if hyp else ", and maximises the failure probability of wrong solutions"
            original = f"{split_official_prompt(record['prompt'][0]['content'])}\n\n**Input constraints (all must hold):**\n{rules}\n\n{block}{GEN_INSTRUCTIONS.format(trigger_clause=trigger)}"
            response = pipeline.call(gen, trace, "generate", original)
            test, kind = pipeline.materialise(trace, response)
            test, verdict, kind = pipeline.repair_loop(trace, pid, original, response, test, True, " while still targeting the hypothesis" if hyp else "", kind)
        if all(t.get("response") is None for t in trace if t.get("stage") == "generate"):
            return
        writer.write({"problem_id": pid, "response_id": rid, "condition": args.condition, **store_test(test or ""),
                      "input_kind": kind, "gen_validator_verdict": verdict, "hypothesis": hyp,
                      "usage": {"calls": sum(1 for t in trace if "input_tokens" in t),
                                "input_tokens": sum(t.get("input_tokens", 0) for t in trace),
                                "output_tokens": sum(t.get("output_tokens", 0) for t in trace)},
                      "trace": trace})

    items = [(p, i) for p in problems for i in range(SAMPLES) if (p, i) not in done]
    if args.condition == "concept":
        with ThreadPoolExecutor(args.workers) as pool:
            list(pool.map(catalogue, problems))
    print(f"{args.condition}: {len(items)} generation(s) to run", flush=True)
    with ThreadPoolExecutor(args.workers) as pool:
        list(pool.map(one, items))
    writer.close()
    cat_writer.close()
    print(json.dumps({"gen": gen.meter.summary(), "helper": helper.meter.summary()}))


def run_scoring(args: argparse.Namespace) -> None:
    problems = open(args.problems).read().split()
    subs = [r for r in load_rows("submission_all") if r["problem_id"] in set(problems)]
    evaluator = Evaluator(validators_path=args.validators, submissions=subs)
    wrong: dict[str, list] = defaultdict(list)
    for r in subs:
        if r["type"] == "wrong_submission":
            wrong[r["problem_id"]].append(r)
    preds = [p for p in read_jsonl(args.pred) if p["problem_id"] in set(problems)]
    done = {(r["problem_id"], int(r["response_id"])) for r in read_jsonl(args.out)}
    todo = [p for p in preds if (p["problem_id"], int(p["response_id"])) not in done]
    writer = JsonlWriter(args.out)

    def score(pred: dict[str, Any]) -> dict[str, Any]:
        pid = pred["problem_id"]
        test = resolve_test(pred)
        base = {"problem_id": pid, "response_id": int(pred["response_id"]), "condition": pred.get("condition")}
        if not test.strip():
            return {**base, "valid_official": False, "strict_valid": False, "exposed_official": [], "exposed_strict": [], "validator": "no_input"}
        tsha = sha(test)
        right = [evaluator.run(s, test, tsha) for s in evaluator.right[pid]]
        expected = official_consensus([r["output"] for r in right if r["result"] == "success_run"])
        strict_expected, _ = strict_consensus(right)
        verdict = evaluator.validate(pid, test, tsha)
        strict_ok = verdict == "accepted" and strict_expected is not None
        exposed, exposed_strict = [], []
        for w in wrong[pid]:
            run = evaluator.run(w, test, tsha)
            if official_exposed(expected, run["result"], run["output"]):
                exposed.append(int(w["id"]))
            if strict_ok and official_exposed(strict_expected, run["result"], run["output"]):
                exposed_strict.append(int(w["id"]))
        return {**base, "validator": verdict, "valid_official": expected != "", "strict_valid": strict_ok,
                "exposed_official": exposed, "exposed_strict": exposed_strict}

    # parallelise across tests; each test runs its ~240 submissions sequentially
    with ThreadPoolExecutor(args.workers) as pool:
        for n, row in enumerate(pool.map(score, todo), 1):
            writer.write(row)
            if n % 20 == 0:
                print(f"scored {n}/{len(todo)}", flush=True)
    writer.close()
    print(json.dumps(coverage(read_jsonl(args.out), wrong), indent=2))


def coverage(rows: list[dict[str, Any]], wrong: dict[str, list]) -> dict[str, Any]:
    total = sum(len(wrong[p]) for p in {r["problem_id"] for r in rows})
    out: dict[str, Any] = {"wrong_submissions": total}
    for key in ("exposed_official", "exposed_strict"):
        for k in (1, 5, 10, 20):
            hit = {(r["problem_id"], i) for r in rows if r["response_id"] < k for i in r[key]}
            out[f"{key}_cov@{k}"] = len(hit) / max(1, total)
    out["strict_valid_rate"] = sum(r["strict_valid"] for r in rows) / max(1, len(rows))
    out["validator_accept_rate"] = sum(r["validator"] == "accepted" for r in rows) / max(1, len(rows))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate")
    g.add_argument("--condition", choices=("cot", "concept"), required=True)
    g.add_argument("--problems", required=True)
    g.add_argument("--out", required=True)
    g.add_argument("--validators", default="testcase_eval/results/validators.jsonl")
    g.add_argument("--workers", type=int, default=6)
    s = sub.add_parser("score")
    s.add_argument("--pred", required=True)
    s.add_argument("--problems", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--validators", default="testcase_eval/results/validators.jsonl")
    s.add_argument("--workers", type=int, default=12)
    args = parser.parse_args()
    run_generation(args) if args.cmd == "generate" else run_scoring(args)


if __name__ == "__main__":
    main()
