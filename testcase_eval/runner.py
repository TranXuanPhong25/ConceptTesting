#!/usr/bin/env python3
"""Generate TestCase-Eval Task 2 inputs with baseline or static concepts."""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from magma.llm_client import make_llm, model_id
from testcase_eval.concepts import render_fault_concepts, static_fault_concepts
from testcase_eval.data import is_python3_language
from testeval_py.llm_runner import _response_text


SYSTEM_PROMPT = (
    "You generate one complete valid stdin input for an algorithm problem. "
    "Return only the raw input inside a plaintext code fence, with no program code."
)


def extract_test_input(response: str) -> str | None:
    answer = re.search(r"<answer>\s*(.*?)\s*</answer>", response, re.S | re.I)
    candidate = answer.group(1) if answer else response
    fenced = re.search(r"```(?:plaintext)?\s*(.*?)```", candidate, re.S | re.I)
    if fenced:
        value = fenced.group(1).strip()
        return value or None
    heading = re.search(r"(?:\*\*)?Test Input:(?:\*\*)?\s*(.*?)(?:\n\s*(?:\*\*)?(?:Explanation|Output):|\Z)", candidate, re.S | re.I)
    if heading:
        value = heading.group(1).strip()
        return value or None
    return None


def build_prompt(record: dict[str, Any], submission: dict[str, Any], condition: str) -> str:
    content = record["prompt"][0]["content"]
    if condition == "concept":
        concepts = static_fault_concepts(submission["source"], submission["language"])
        content += "\n\n" + render_fault_concepts(concepts)
    return content


def run(args: argparse.Namespace) -> int:
    with Path(args.submissions).open() as handle:
        submissions = [json.loads(line) for line in handle if line.strip()]
    by_id = {int(row["id"]): row for row in submissions}
    completed: set[tuple[str, int]] = set()
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        with output.open() as handle:
            for line in handle:
                if line.strip():
                    row = json.loads(line)
                    completed.add((row["condition"], int(row["submission_id"])))

    llm = make_llm(temperature=args.temperature, timeout=args.request_timeout, max_retries=0, max_tokens=args.max_output_tokens)
    if llm is None:
        raise SystemExit("LLM is not configured")
    min_interval = 60.0 / max(1, args.rpm)
    last_call = [0.0]

    def call(prompt: str) -> str | None:
        for attempt in range(6):
            dt = time.monotonic() - last_call[0]
            if dt < min_interval:
                time.sleep(min_interval - dt)
            last_call[0] = time.monotonic()
            try:
                response = llm.invoke([SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=prompt)])
                return _response_text(getattr(response, "content", response))
            except Exception as exc:  # noqa: BLE001 - retry any transport/quota error, mirrors magma/gen.py
                wait = min(60, 4 * 2**attempt)
                print(f"[warn] retry {wait}s: {str(exc)[:120]}", flush=True)
                time.sleep(wait)
        return None

    generated = 0
    total_for_condition = sum(1 for cond, _ in completed if cond == args.condition)
    seen_problems: set[str] = set()
    with Path(args.input).open() as source, output.open("a") as destination:
        for line in source:
            if not line.strip():
                continue
            record = json.loads(line)
            info = record["extra_info"]
            submission_id = int(info["submission_id"])
            submission = by_id.get(submission_id)
            if submission is None:
                continue
            if args.python_only and not is_python3_language(str(submission["language"])):
                continue
            if args.one_per_problem:
                problem_id = info["problem_id"]
                if problem_id in seen_problems:
                    continue
                seen_problems.add(problem_id)
            key = (args.condition, submission_id)
            if key in completed:
                continue
            if args.limit and total_for_condition >= args.limit:
                break
            prompt = build_prompt(record, submission, args.condition)
            raw = call(prompt)
            if raw is None:
                print(f"[skip] {info['problem_id']} submission={submission_id}: exhausted retries", flush=True)
                continue
            test = extract_test_input(raw)
            row = {
                "problem_id": info["problem_id"],
                "submission_id": submission_id,
                "task_type": info["task_type"],
                "condition": args.condition,
                "model": model_id(),
                "language": submission["language"],
                "test": test or "",
                "response": raw,
                "extra_info": {**info, "model_name": model_id(), "response_id": 0},
            }
            destination.write(json.dumps(row, ensure_ascii=False) + "\n")
            destination.flush()
            os.fsync(destination.fileno())
            completed.add(key)
            generated += 1
            total_for_condition += 1
            print(f"{args.condition} {info['problem_id']} submission={submission_id} valid={bool(test)}", flush=True)
    print(f"generated {generated} TestCase-Eval Task 2 input(s) -> {output}")
    return generated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in", dest="input", required=True, help="Official Task 2 JSONL")
    parser.add_argument("--submissions", required=True, help="Official submission_lite JSONL")
    parser.add_argument("--out", required=True)
    parser.add_argument("--condition", choices=("baseline", "concept"), default="baseline")
    parser.add_argument("--python-only", action="store_true")
    parser.add_argument("--one-per-problem", action="store_true", help="Keep only the first target submission per problem_id")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--rpm", type=int, default=20, help="Max requests per minute (throttle + backoff on errors)")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--request-timeout", type=float, default=60.0)
    parser.add_argument("--max-output-tokens", type=int, default=2048)
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
