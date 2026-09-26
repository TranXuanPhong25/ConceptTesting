#!/usr/bin/env python3
"""Per-problem input validators: AutoCode selection + CodeHacker calibration.

Stage 1 (AutoCode, arXiv 2510.12803 section 3.1): the LLM enumerates the
input constraints as atomic rules (Specification Grounding, arXiv
2607.06636: one rule per record) and writes ~40 labelled cases, 10 valid and
30 near-valid illegal inputs.  Three candidate validators are written
independently; the one classifying the most cases correctly is kept.  The
official statement examples are added as valid cases and must be accepted.

Stage 2 (CodeHacker, arXiv 2602.20213 Phase I): the selected validator is
attacked with bypass inputs (invalid but plausible) and rejection inputs
(valid extremes, including generator-built maximum-size inputs).  Where the
validator disagrees with the attack label, an independent patch call first
adjudicates the label against the statement (anti-hallucination step) and
then rewrites the validator.  A patch is kept only if it still accepts every
statement example and does not lose accuracy on the labelled pool.

Output: one JSONL row per problem with the selected code, constraint rules,
selection/calibration scores and LLM usage.  Resume-safe by problem_id.
"""

from __future__ import annotations

import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from testcase_eval.data import load_rows
from testcase_eval.llm import Gemini
from testcase_eval.sandbox import run_python_program
from testcase_eval.store import JsonlWriter, read_jsonl

MAX_CASE_BYTES = 8 * 1024 * 1024

CASES_PROMPT = """You are an expert Codeforces problem setter preparing an input validator.

Problem statement:
{statement}

Step 1. Enumerate every constraint the input must satisfy as a numbered list of ATOMIC rules
(format/line structure, token counts, each numeric range, string alphabet and length, structural
guarantees such as "the graph is a tree", "all a_i are distinct", "p is a permutation", "the sum of n
over all test cases does not exceed ...", "the answer is guaranteed to exist"). One rule per item.

Step 2. Write 40 small test inputs for the validator: 10 VALID inputs (including smallest cases and
tricky-but-legal cases) and 30 NEAR-VALID INVALID inputs, each violating exactly one rule (off-by-one
ranges, wrong counts, t/n mismatch, duplicate where distinct is required, disconnected graph, wrong
alphabet, sum constraint exceeded, missing line, ...).  Keep every input under 2000 characters; for rules
that need a huge input to violate (e.g. a sum of n limit), write a short Python 3 program that prints
the input instead (field "generator").

Return ONLY a JSON object inside a ```json fence:
{{"rules": ["R1: ...", "R2: ..."],
  "cases": [{{"input": "...", "valid": true, "rule": "", "why": "..."}},
            {{"generator": "print(...)", "valid": false, "rule": "R7", "why": "..."}}]}}
"""

VALIDATOR_PROMPT = """You are an expert Codeforces problem setter.  Write an input validator for this problem.

Problem statement:
{statement}

Constraint rules to enforce:
{rules}

Requirements:
- A single Python 3 program that reads ALL of stdin (sys.stdin.read()) and exits with status 0 if and
  only if the input satisfies EVERY rule, otherwise prints the violated rule to stderr and exits with
  status 1 (sys.exit(1)).
- Tokenise on whitespace; do not reject extra spaces or a missing final newline, but do reject missing or
  extra tokens.  Check every numeric range, count, alphabet, and structural guarantee (tree/connected,
  distinctness, permutation, sortedness, sums over test cases, ...) that the statement states.
- Integers must be written as plain decimal integers (reject "1.0", "1e5").
- Must run in under 5 seconds on maximum-size inputs (use iterative algorithms, no recursion).
- Do not solve the problem; only check the input.

Return only the program inside a ```python fence."""

ATTACK_PROMPT = """You are attacking an input validator for a Codeforces problem (CodeHacker-style calibration).

Problem statement:
{statement}

Constraint rules:
{rules}

Current validator:
```python
{code}
```

Produce 12 attack inputs:
- 6 BYPASS attacks: INVALID inputs (violating exactly one statement rule) that this validator is most
  likely to wrongly ACCEPT because a check is missing or off by one.
- 6 REJECTION attacks: VALID inputs at the extremes (maximum sizes, maximum/minimum values, all-equal,
  degenerate structures, maximum number of test cases with the sum limit exactly reached) that this
  validator might wrongly REJECT or time out on.  Build large ones with a short Python 3 generator.
Label each with the ground truth according to the STATEMENT, not according to the validator.

Return ONLY a JSON object inside a ```json fence:
{{"cases": [{{"input": "...", "valid": false, "rule": "R3", "why": "..."}},
            {{"generator": "import random\\n...", "valid": true, "rule": "", "why": "..."}}]}}
"""

PATCH_PROMPT = """The input validator below disagrees with the intended label on some cases.

Problem statement:
{statement}

Constraint rules:
{rules}

Validator:
```python
{code}
```

Disagreements (label = intended ground truth, observed = validator verdict):
{disagreements}

First, for each disagreement, decide from the STATEMENT whether the intended label is actually correct
(labels were written by another model and can be wrong).  Then write a corrected validator that agrees
with the statement on every case.  Keep all requirements: read all stdin, exit 0 iff valid, exit 1 with
a message otherwise, whitespace-tolerant tokenisation, under 5 seconds on maximum inputs.

Return a JSON object in a ```json fence: {{"wrong_labels": [<indices of disagreements whose label is wrong>]}}
followed by the full corrected program in a ```python fence."""


def extract_block(text: str | None, lang: str) -> str | None:
    if not text:
        return None
    blocks = re.findall(r"```" + lang + r"[^\n]*\n(.*?)```", text, re.S)
    return blocks[-1] if blocks else None


def parse_json_block(text: str | None) -> Any:
    raw = extract_block(text, "json")
    if raw is None and text:
        start, end = text.find("{"), text.rfind("}")
        raw = text[start : end + 1] if start >= 0 else None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def materialise(case: dict[str, Any]) -> str | None:
    if isinstance(case.get("input"), str):
        return case["input"]
    if isinstance(case.get("generator"), str):
        run = run_python_program(case["generator"], "", timeout=15.0, output_limit=MAX_CASE_BYTES)
        if run["result"] == "success_run" and run["output"].strip():
            return run["output"]
    return None


def classify(code: str, text: str) -> bool | None:
    """True=accepted, False=rejected, None=validator crashed/timed out."""
    run = run_python_program(code, text, timeout=20.0)
    if run["result"] == "success_run":
        return True
    if run["result"] == "runtime_error" and run.get("returncode") == 1:
        return False
    return None


def score(code: str, cases: list[dict[str, Any]]) -> dict[str, Any]:
    correct, errors, samples_ok = 0, 0, True
    wrong: list[int] = []
    for i, case in enumerate(cases):
        verdict = classify(code, case["text"])
        if verdict is None:
            errors += 1
            ok = False
        else:
            ok = verdict == case["valid"]
        correct += ok
        if not ok:
            wrong.append(i)
            if case.get("sample"):
                samples_ok = False
    return {"correct": correct, "total": len(cases), "errors": errors, "samples_ok": samples_ok, "wrong": wrong}


def build_cases(raw_cases: list[Any], origin: str) -> list[dict[str, Any]]:
    cases = []
    for case in raw_cases or []:
        if not isinstance(case, dict) or not isinstance(case.get("valid"), bool):
            continue
        text = materialise(case)
        if text is None:
            continue
        cases.append({"text": text, "valid": case["valid"], "rule": case.get("rule", ""), "why": str(case.get("why", ""))[:200], "origin": origin})
    return cases


def synthesize(problem: dict[str, Any], helper: Gemini, candidates: int = 3, rounds: int = 2) -> dict[str, Any]:
    statement = problem["prompt"]
    log: dict[str, Any] = {"problem_id": problem["problem_id"], "calls": []}

    def call(stage: str, prompt: str) -> str | None:
        result = helper.complete(prompt)
        log["calls"].append({"stage": stage, **result.usage(), "ok": result.text is not None})
        return result.text

    spec = parse_json_block(call("cases", CASES_PROMPT.format(statement=statement))) or {}
    rules = [str(r) for r in spec.get("rules", []) if str(r).strip()]
    rules_text = "\n".join(rules) or "(derive them from the statement)"
    cases = [{"text": ex[0], "valid": True, "rule": "", "why": "statement example", "origin": "sample", "sample": True}
             for ex in problem.get("examples") or [] if ex and ex[0].strip()]
    cases += build_cases(spec.get("cases", []), "autocode")

    with ThreadPoolExecutor(candidates) as pool:
        codes = list(pool.map(lambda i: extract_block(call(f"candidate{i}", VALIDATOR_PROMPT.format(statement=statement, rules=rules_text)), "python"),
                              range(candidates)))
    scored = []
    for i, code in enumerate(codes):
        if code:
            scored.append((score(code, cases), i, code))
    if not scored:
        return {**log, "rules": rules, "code": None, "status": "no_candidate"}
    scored.sort(key=lambda t: (t[0]["samples_ok"], t[0]["correct"], -len(t[2])), reverse=True)
    best_score, best_index, best_code = scored[0]
    log["selection"] = [{"candidate": i, "correct": s["correct"], "total": s["total"], "samples_ok": s["samples_ok"]} for s, i, _ in scored]

    calibration = []
    for round_index in range(rounds):
        attack = parse_json_block(call(f"attack{round_index}", ATTACK_PROMPT.format(statement=statement, rules=rules_text, code=best_code))) or {}
        new_cases = build_cases(attack.get("cases", []), f"attack{round_index}")
        cases += new_cases
        current = score(best_code, cases)
        attack_wrong = [i for i in current["wrong"] if cases[i]["origin"] == f"attack{round_index}"]
        entry = {"round": round_index, "attacks": len(new_cases), "misclassified": len(attack_wrong),
                 "bypass": sum(1 for i in attack_wrong if not cases[i]["valid"]),
                 "rejection": sum(1 for i in attack_wrong if cases[i]["valid"])}
        if not current["wrong"]:
            calibration.append({**entry, "patched": False})
            break
        shown = current["wrong"][:12]
        disagreements = "\n".join(
            f"[{k}] label={'VALID' if cases[i]['valid'] else 'INVALID'} observed={'accepted' if cases[i]['valid'] is False else 'rejected/crashed'} "
            f"rule={cases[i]['rule']} why={cases[i]['why']}\ninput (first 600 chars):\n{cases[i]['text'][:600]}"
            for k, i in enumerate(shown)
        )
        response = call(f"patch{round_index}", PATCH_PROMPT.format(statement=statement, rules=rules_text, code=best_code, disagreements=disagreements))
        verdict = parse_json_block(response) or {}
        wrong_labels = {int(k) for k in verdict.get("wrong_labels", []) if str(k).lstrip("-").isdigit()} if isinstance(verdict, dict) else set()
        for k in wrong_labels:
            if 0 <= k < len(shown) and not cases[shown[k]].get("sample"):
                cases[shown[k]]["valid"] = not cases[shown[k]]["valid"]
                cases[shown[k]]["relabelled"] = True
        patched = extract_block(response, "python")
        before = score(best_code, cases)
        kept = False
        if patched:
            after = score(patched, cases)
            if after["samples_ok"] and after["correct"] >= before["correct"]:
                best_code, kept = patched, True
                before = after
        calibration.append({**entry, "relabelled": len(wrong_labels), "patched": kept, "accuracy_after": before["correct"] / max(1, before["total"])})
    final = score(best_code, cases)
    return {
        **log,
        "rules": rules,
        "code": best_code,
        "status": "ok" if final["samples_ok"] else "rejects_sample",
        "selected_candidate": best_index,
        "calibration": calibration,
        "final_accuracy": final["correct"] / max(1, final["total"]),
        "final_cases": final["total"],
        "samples_ok": final["samples_ok"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--problems", default="", help="comma-separated problem ids or @file with one id per line")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    problems = load_rows("problem")
    if args.problems:
        wanted = open(args.problems[1:]).read().split() if args.problems.startswith("@") else args.problems.split(",")
        order = {p: i for i, p in enumerate(wanted)}
        problems = sorted((p for p in problems if p["problem_id"] in order), key=lambda p: order[p["problem_id"]])
    done = {r["problem_id"] for r in read_jsonl(args.out)}
    todo = [p for p in problems if p["problem_id"] not in done]
    if args.limit:
        todo = todo[: args.limit]
    helper = Gemini(temperature=1.0, max_output_tokens=16384, timeout=240)
    writer = JsonlWriter(args.out)

    def work(problem: dict[str, Any]) -> None:
        try:
            row = synthesize(problem, helper)
        except Exception as exc:  # noqa: BLE001 - keep the batch alive, record the failure
            row = {"problem_id": problem["problem_id"], "code": None, "status": f"exception: {exc!r}"[:300]}
        writer.write(row)
        print(f"{problem['problem_id']} status={row.get('status')} acc={row.get('final_accuracy')}", flush=True)

    with ThreadPoolExecutor(args.workers) as pool:
        list(pool.map(work, todo))
    writer.close()
    print(json.dumps(helper.meter.summary()))


if __name__ == "__main__":
    main()
