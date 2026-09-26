#!/usr/bin/env python3
"""Task 2 (Fault Exposure) input generation: paper baselines and concept conditions.

Conditions (all on the same targets, one final input per target):

  do            official Task2-DO prompt, one call (paper's direct-output baseline)
  cot           official Task2 prompt ("Think step by step"), one call (paper's CoT)
  cot_val       `cot` answer reused as attempt 1, then up to 2 validator-feedback
                repairs.  Control: isolates the validator loop from the concept.
  concept_nohyp generation prompt of `concept` without the fault hypothesis
                (generator allowed, same repair loop).  Ablation for concept content.
  concept       fault-hypothesis analyst -> hypothesis-conditioned input or
                generator program -> up to 2 validator-feedback repairs.

Generation settings follow the official `generate.py`: temperature 1.0,
max_tokens 2048 for the paper prompts.  Extraction follows the official
`extract.py`: regex first, then an LLM fallback with the official extraction
prompt (Gemini instead of gpt-4.1-mini).

Resume-safe: one JSONL row per (condition, submission_id), appended as soon as
it is finished.
"""

from __future__ import annotations

import argparse
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from testcase_eval.data import load_rows
from testcase_eval.llm import Gemini
from testcase_eval.sandbox import run_python_program
from testcase_eval.store import JsonlWriter, read_jsonl, resolve_test, sha, store_test
from testcase_eval.validator import extract_block, parse_json_block

CONDITIONS = ("do", "cot", "cot_val", "concept_nohyp", "concept")
MAX_REPAIRS = 2
GENERATOR_OUTPUT_LIMIT = 16 * 1024 * 1024

# --- official extraction (extract.py @ 45275c6) --------------------------------
EXTRACT_PROMPT = """You are given an LLM-generated response to a test-input-generation task.

**Your job:**
Extract the *complete, valid, and effective* test input from the response, even if the response does not strictly follow the expected ` ```plaintext ... ``` ` format.
The test input is usually the actual data or values to be given to the algorithm, not code or explanations.
Sometimes the LLM response may have formatting errors, be missing code blocks, or present the test input in plain text.
Please do your best to identify and extract the correct test input, ignoring code generation code, explanations, or markdown formatting.

**Common formats to look for:**
1. Content within ` ```plaintext ... ``` ` or ` ``` ... ``` ` code blocks
2. Content following **Test Input:** heading until the next heading (like **Explanation:** or **Output:**)
3. Plain text that represents test data/input values

**Requirements:**
- If you cannot find any valid test input in the response, return "None" as the test value.
- The extracted test input should be as complete, valid, and precise as possible, even if the response is imperfectly formatted.
- If there are multiple possible candidates, choose the one that most likely represents the actual input expected by the algorithm problem.
- For **Test Input:** format, extract everything from after the heading until the next markdown heading or explanation section.
- Remove any trailing explanations or comments, keep only the raw input data.

**LLM Response:**
{response}
"""
EXTRACT_SUFFIX = '\n\nReturn only a JSON object {"test": "<extracted input or None>"} in a ```json fence.'


def extract_test_regex(response: str) -> str | None:
    """Verbatim port of official extract.extract_test_regex."""
    answer_match = re.search(r"<answer>\s*(.*?)\s*</answer>", response, re.DOTALL)
    if answer_match:
        answer_content = answer_match.group(1).strip()
        match1 = re.search(r"```plaintext\s*(.*?)```", answer_content, re.DOTALL)
        if match1:
            return match1.group(1).strip()
        match2 = re.search(r"```\s*(.*?)```", answer_content, re.DOTALL)
        if match2:
            return match2.group(1).strip()
    match1 = re.search(r"```plaintext\s*(.*?)```", response, re.DOTALL)
    if match1:
        return match1.group(1).strip()
    match2 = re.search(r"```\s*(.*?)```", response, re.DOTALL)
    if match2:
        return match2.group(1).strip()
    return None


# --- concept prompts ---------------------------------------------------------------
ANALYST_PROMPT = """You are a competitive-programming hacker.  Find how this specific wrong submission diverges
from a correct solution.

{problem_and_code}

Input constraints (every hack input must satisfy all of them):
{rules}

Analyse the buggy code against the statement.  Report up to 3 fault hypotheses, most likely first.  Each
hypothesis must be specific to THIS code (quote the exact expression or line), and must name the input
relation that triggers it.  Consider wrong logic/greedy, off-by-one and boundary handling, overflow,
uninitialised or stale state across test cases, wrong special cases (n=1, all equal, ...), precision, and
complexity (TLE/MLE on maximum inputs) or runtime errors (out-of-bounds, recursion depth, division by zero).

Return ONLY a JSON object in a ```json fence:
{{"hypotheses": [{{
  "suspicious_code": "exact quoted expression/line from the buggy code",
  "mechanism": "what the code does wrong",
  "violated_invariant": "the property a correct solution maintains that this code breaks",
  "trigger_condition": "precise relation over input values that makes the bug fire",
  "expected_correct_behavior": "what a correct solution outputs/does on such an input",
  "buggy_behavior": "what this code outputs/does instead (wrong value, crash, timeout)",
  "failure_mode": "WA | TLE | RE | MLE",
  "needs_large_input": false,
  "minimal_trigger": "smallest concrete input sketch, or how to build the large one"
}}]}}"""

GEN_INSTRUCTIONS = """**Instructions:**
- Construct ONE test input that satisfies every input constraint listed above{trigger_clause}.
- If exposing the bug needs a large input (time/memory limit, overflow on big values, deep recursion),
  write a deterministic Python 3 program that prints the complete input to stdout (no stdin, runs in
  under 5 seconds, output under 16 MB) inside a single ```python fence.
- Otherwise output the raw test input directly inside a single ```plaintext fence (keep it small).
- Output exactly one fenced block as your final answer.

Think step by step."""

REPAIR_PROMPT = """{original}

Your previous answer:
{previous}

Problem with that answer: {feedback}

Fix the test input so that it satisfies every input constraint{keep}.  Return the corrected answer in the
same format (one ```plaintext block with the raw input, or one ```python generator block)."""


def render_rules(rules: list[str]) -> str:
    return "\n".join(f"- {r}" for r in rules) if rules else "- (see the statement)"


def render_hypothesis(h: dict[str, Any]) -> str:
    fields = [
        ("Suspicious code", "suspicious_code"),
        ("Mechanism", "mechanism"),
        ("Violated invariant", "violated_invariant"),
        ("Trigger condition", "trigger_condition"),
        ("Expected correct behaviour", "expected_correct_behavior"),
        ("Buggy behaviour", "buggy_behavior"),
        ("Failure mode", "failure_mode"),
        ("Needs large input", "needs_large_input"),
        ("Minimal trigger", "minimal_trigger"),
    ]
    lines = ["**Fault hypothesis for this buggy code (from a prior analysis):**"]
    for label, key in fields:
        if h.get(key) not in (None, ""):
            lines.append(f"- {label}: {h[key]}")
    return "\n".join(lines)


def split_official_prompt(content: str) -> str:
    """Official prompt minus its instruction/format tail: task header + problem + buggy code."""
    cut = content.find("**Instructions:**")
    return content[:cut].rstrip() if cut >= 0 else content


class Pipeline:
    def __init__(self, gen: Gemini, helper: Gemini, validators: dict[str, dict[str, Any]], cot_rows: dict[int, dict[str, Any]]):
        self.gen = gen
        self.helper = helper
        self.validators = validators
        self.cot_rows = cot_rows

    # -- helpers --------------------------------------------------------------
    def call(self, llm: Gemini, trace: list, stage: str, prompt: str) -> str | None:
        result = llm.complete(prompt)
        trace.append({"stage": stage, **result.usage(), "finish": result.finish_reason, "response": result.text})
        return result.text

    def extract(self, trace: list, response: str | None) -> str | None:
        if not response:
            return None
        test = extract_test_regex(response)
        if test:
            return test
        answer = parse_json_block(self.call(self.helper, trace, "extract_fallback", EXTRACT_PROMPT.format(response=response) + EXTRACT_SUFFIX))
        test = answer.get("test") if isinstance(answer, dict) else None
        return None if not test or str(test).strip() == "None" else str(test)

    def materialise(self, trace: list, response: str | None) -> tuple[str | None, str]:
        """Return (input, kind) from a concept-style answer: python generator or plaintext."""
        if not response:
            return None, "no_response"
        program = extract_block(response, "python")
        plain = extract_block(response, "plaintext")
        if program and not plain:
            run = run_python_program(program, "", timeout=15.0, output_limit=GENERATOR_OUTPUT_LIMIT)
            trace.append({"stage": "run_generator", "result": run["result"], "bytes": len(run.get("output") or ""), "error": (run.get("error") or "")[-300:]})
            if run["result"] == "success_run" and run["output"].strip():
                return run["output"], "generator"
            return None, f"generator_{run['result']}"
        test = self.extract(trace, response)
        return test, "plaintext" if test else "no_input"

    def check(self, problem_id: str, test: str | None) -> tuple[str, str]:
        if not test or not test.strip():
            return "no_input", "no test input could be extracted from the answer"
        validator = self.validators.get(problem_id)
        if not validator:
            return "missing", ""
        run = run_python_program(validator["code"], test, timeout=20.0)
        if run["result"] == "success_run":
            return "accepted", ""
        if run["result"] == "runtime_error" and run.get("returncode") == 1:
            return "rejected", (run.get("error") or "").strip()[-400:] or "validator rejected the input"
        return f"error_{run['result']}", ""

    def repair_loop(self, trace: list, problem_id: str, original: str, response: str | None, test: str | None,
                    concept_style: bool, keep: str, kind: str = "plaintext") -> tuple[str | None, str, str]:
        verdict, message = self.check(problem_id, test)
        trace.append({"stage": "validate", "verdict": verdict, "message": message[:300]})
        for attempt in range(MAX_REPAIRS):
            if verdict not in {"rejected", "no_input"}:
                break
            feedback = f"the input validator rejected it: {message}" if verdict == "rejected" else message
            last_run = next((t for t in reversed(trace) if t.get("stage") == "run_generator"), None)
            if verdict == "no_input" and concept_style and last_run and last_run["result"] != "success_run":
                feedback = f"your generator program failed ({last_run['result']}): {last_run['error']}"
            previous = (response or "")[-6000:]
            prompt = REPAIR_PROMPT.format(original=original, previous=previous, feedback=feedback, keep=keep)
            response = self.call(self.gen, trace, f"repair{attempt}", prompt)
            if concept_style:
                test, kind = self.materialise(trace, response)
            else:
                test = self.extract(trace, response)
            verdict, message = self.check(problem_id, test)
            trace.append({"stage": "validate", "verdict": verdict, "message": message[:300]})
        return test, verdict, kind

    # -- conditions -----------------------------------------------------------
    def run(self, condition: str, record: dict[str, Any], do_record: dict[str, Any] | None) -> dict[str, Any]:
        info = record["extra_info"]
        problem_id, submission_id = info["problem_id"], int(info["submission_id"])
        trace: list[dict[str, Any]] = []
        final_verdict = None
        hypotheses = None
        kind = "plaintext"
        if condition == "do":
            response = self.call(self.gen, trace, "generate", do_record["prompt"][0]["content"])
            test = self.extract(trace, response)
        elif condition == "cot":
            response = self.call(self.gen, trace, "generate", record["prompt"][0]["content"])
            test = self.extract(trace, response)
        elif condition == "cot_val":
            prior = self.cot_rows.get(submission_id)
            original = record["prompt"][0]["content"]
            if prior is None:
                response = self.call(self.gen, trace, "generate", original)
                test = self.extract(trace, response)
            else:
                response = next((t["response"] for t in prior.get("trace", []) if t.get("stage") == "generate"), None)
                test = resolve_test(prior) or None
                trace.append({"stage": "reuse_cot", "input_tokens": 0, "output_tokens": 0})
            test, final_verdict, kind = self.repair_loop(trace, problem_id, original, response, test, False, "")
        else:
            validator = self.validators.get(problem_id) or {}
            rules = render_rules(validator.get("rules") or [])
            base = split_official_prompt(record["prompt"][0]["content"])
            constraint_block = "**Input constraints (all must hold):**\n" + rules
            if condition == "concept":
                analysis = parse_json_block(self.call(self.gen, trace, "analyst", ANALYST_PROMPT.format(problem_and_code=base, rules=rules)))
                hypotheses = [h for h in (analysis or {}).get("hypotheses", []) if isinstance(h, dict)] if isinstance(analysis, dict) else []
                top = hypotheses[0] if hypotheses else None
                hyp_block = render_hypothesis(top) + "\n\n" if top else ""
                trigger = " AND makes the trigger condition of the fault hypothesis hold, so the buggy code diverges from the expected correct behaviour" if top else ", and maximises the failure probability of the buggy code"
                keep = " while still making the trigger condition hold" if top else ""
            else:
                hyp_block = ""
                trigger = ", and maximises the failure probability of the buggy code"
                keep = ""
            original = f"{base}\n\n{constraint_block}\n\n{hyp_block}{GEN_INSTRUCTIONS.format(trigger_clause=trigger)}"
            response = self.call(self.gen, trace, "generate", original)
            test, kind = self.materialise(trace, response)
            test, final_verdict, kind = self.repair_loop(trace, problem_id, original, response, test, True, keep, kind)
        usage = {
            "calls": sum(1 for t in trace if "input_tokens" in t and t.get("stage") != "reuse_cot"),
            "input_tokens": sum(t.get("input_tokens", 0) for t in trace),
            "output_tokens": sum(t.get("output_tokens", 0) for t in trace),
        }
        row = {
            "problem_id": problem_id,
            "submission_id": submission_id,
            "condition": condition,
            "model": Gemini.model_name(),
            **store_test(test or ""),
            "input_kind": kind,
            "gen_validator_verdict": final_verdict,
            "hypotheses": hypotheses,
            "usage": usage,
            "trace": trace,
            "extra_info": {**info, "model_name": Gemini.model_name(), "response_id": 0},
        }
        return row


def select_subset(task2: list[dict], submissions: dict[int, dict], per_family: int, seed: int) -> list[int]:
    """Seeded, language-stratified subset: at most one target per problem."""
    import random

    from testcase_eval.sandbox import language_family

    rng = random.Random(seed)
    records = list(task2)
    rng.shuffle(records)
    picked: list[int] = []
    used_problems: set[str] = set()
    counts: dict[str, int] = {"cpp": 0, "java": 0, "python": 0}
    for record in records:
        info = record["extra_info"]
        family = language_family(submissions[int(info["submission_id"])]["language"])
        if family is None or counts[family] >= per_family or info["problem_id"] in used_problems:
            continue
        picked.append(int(info["submission_id"]))
        used_problems.add(info["problem_id"])
        counts[family] += 1
        if all(v >= per_family for v in counts.values()):
            break
    return picked


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--condition", choices=CONDITIONS, required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--targets", default="", help="file with one submission_id per line (default: all 10,000)")
    parser.add_argument("--validators", default="testcase_eval/results/validators.jsonl")
    parser.add_argument("--cot", default="", help="cot predictions to reuse as attempt 1 for cot_val")
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    task2 = load_rows("task2")
    task2_do = {int(r["extra_info"]["submission_id"]): r for r in load_rows("task2_do")}
    if args.targets:
        wanted = [int(x) for x in Path(args.targets).read_text().split()]
        index = {int(r["extra_info"]["submission_id"]): r for r in task2}
        task2 = [index[i] for i in wanted if i in index]
    validators = {r["problem_id"]: r for r in read_jsonl(args.validators) if r.get("code")} if args.validators else {}
    cot_rows = {int(r["submission_id"]): r for r in read_jsonl(args.cot)} if args.cot else {}
    done = {int(r["submission_id"]) for r in read_jsonl(args.out) if r.get("condition") == args.condition}
    todo = [r for r in task2 if int(r["extra_info"]["submission_id"]) not in done]
    if args.limit:
        todo = todo[: args.limit]
    print(f"{args.condition}: {len(todo)} target(s) to generate ({len(done)} done)", flush=True)

    gen = Gemini(temperature=1.0, max_output_tokens=2048 if args.condition in {"do", "cot", "cot_val"} else 8192, timeout=180)
    helper = Gemini(temperature=1.0, max_output_tokens=4096, timeout=120)
    pipeline = Pipeline(gen, helper, validators, cot_rows)
    writer = JsonlWriter(args.out)
    counter = [0]
    lock = threading.Lock()

    def work(record: dict[str, Any]) -> None:
        sid = int(record["extra_info"]["submission_id"])
        try:
            row = pipeline.run(args.condition, record, task2_do.get(sid))
        except Exception as exc:  # noqa: BLE001 - record and continue; rerun resumes it
            print(f"[error] {sid}: {exc!r}"[:300], flush=True)
            return
        if all(t.get("response") is None for t in row["trace"] if t.get("stage") in {"generate", "analyst"}) and args.condition != "cot_val":
            print(f"[skip] {sid}: LLM call failed; will retry on resume", flush=True)
            return
        writer.write(row)
        with lock:
            counter[0] += 1
            if counter[0] % 25 == 0:
                print(f"{args.condition}: {counter[0]}/{len(todo)} usage={gen.meter.summary()} helper={helper.meter.summary()}", flush=True)

    with ThreadPoolExecutor(args.workers) as pool:
        list(pool.map(work, todo))
    writer.close()
    print(json.dumps({"gen": gen.meter.summary(), "helper": helper.meter.summary()}))


if __name__ == "__main__":
    main()
