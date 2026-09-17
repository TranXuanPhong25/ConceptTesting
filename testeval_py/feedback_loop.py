#!/usr/bin/env python3
"""Feedback-driven targeted test generation for Python/TestEval."""

from __future__ import annotations

import argparse
import json
import os
import signal
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

from concept_annotator_py import annotate_record
from testeval_py.llm_runner import (
    BASELINE_PROMPT_VERSION,
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    _default_llm_factory,
    _response_text,
    build_baseline_line_prompt,
    build_line_prompt,
    clean_model_output,
    result_record,
    _validate_generated_test,
)


FEEDBACK_PROMPT_VERSION = "feedback-v1"


def evaluate_target(record: dict[str, Any], testcase: str, target_line: int, timeout: int = 5) -> dict[str, Any]:
    """Execute one generated test and report target reachability separately from assertions."""
    try:
        compile(testcase, "<generated-test>", "exec")
    except SyntaxError as exc:
        return {"status": "syntax_error", "covered": False, "error": exc.msg}
    namespace: dict[str, Any] = {}
    seen: set[int] = set()
    try:
        with _time_limit(timeout):
            source = record.get("code") or record.get("python_solution", "")
            exec(compile(source, "under_test.py", "exec"), namespace)
            exec(compile(testcase, "generated_test.py", "exec"), namespace)
            name = f"test_{record['func_name']}"
            if name not in namespace or f"solution.{record['func_name']}" not in testcase:
                return {"status": "missing_focal_call", "covered": False, "error": "test function or focal call missing"}

            def trace(frame, event, _arg):
                if frame.f_code.co_filename == "under_test.py" and event == "line":
                    seen.add(frame.f_lineno)
                return trace

            previous = __import__("sys").gettrace()
            __import__("sys").settrace(trace)
            try:
                namespace[name]()
            finally:
                __import__("sys").settrace(previous)
    except AssertionError:
        return {"status": "assertion_failed", "covered": target_line in seen, "error": "assertion failed"}
    except Exception as exc:
        return {"status": "runtime_error", "covered": target_line in seen, "error": type(exc).__name__}
    return {"status": "covered" if target_line in seen else "not_covered", "covered": target_line in seen, "error": ""}


def feedback_message(result: dict[str, Any], target_line: int) -> str:
    if result["status"] == "covered":
        return f"Target line {target_line} was covered and the test executed successfully. Keep this input structure."
    if result["status"] == "assertion_failed":
        return (
            f"The test reached target line {target_line}, but an assertion failed. "
            "Keep the path-reaching input and repair the expected result."
        )
    if result["status"] == "not_covered":
        return (
            f"The test executed but did not reach target line {target_line}. "
            "Change the concrete input to satisfy the required control-flow relation."
        )
    return (
        f"The generated test did not execute correctly ({result['status']}: {result.get('error', '')}). "
        "Return one standalone zero-argument test function with a valid focal call."
    )


def run(args: argparse.Namespace, llm_factory: Callable[[float, float, int], Any] | None = None) -> int:
    if args.mode != "line":
        raise SystemExit("feedback loop currently supports --mode line")
    prompt_mode = getattr(args, "prompt_mode", "symbolic")
    if prompt_mode not in {"symbolic", "baseline"}:
        raise SystemExit("--prompt-mode must be symbolic or baseline")
    prompt_version = PROMPT_VERSION if prompt_mode == "symbolic" else BASELINE_PROMPT_VERSION
    path_by_task = _load_paths(args.paths)
    llm = None if args.dry_run else (llm_factory or _default_llm_factory)(args.temperature, args.request_timeout, args.max_output_tokens)
    if not args.dry_run and llm is None:
        raise SystemExit("LLM is not configured")

    output = Path(args.out)
    cache_path = Path(args.cache) if args.cache else Path(str(output) + ".cache.jsonl")
    cached = _load_cache(cache_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with Path(args.input).open() as source, output.open("w") as destination:
        for raw_line in source:
            if not raw_line.strip():
                continue
            if args.limit and count >= args.limit:
                break
            record = json.loads(raw_line)
            annotated = annotate_record(record, path_by_task.get(record.get("task_num")))
            annotation = annotated["concept_annotation_py"]
            tests: dict[int, str] = {}
            for target in annotation["line_targets"][: args.max_targets or None]:
                prompt = (
                    build_line_prompt(record, annotation, target)
                    if prompt_mode == "symbolic"
                    else build_baseline_line_prompt(record, target)
                )
                messages = [{"role": "user", "content": prompt}]
                best = ""
                target_line = target["line"]
                for round_index in range(args.rounds + 1):
                    key = f"{FEEDBACK_PROMPT_VERSION}:{prompt_version}:line:{record['task_num']}:{target_line}:r{round_index}"
                    if key in cached:
                        generated = cached[key]
                    elif args.dry_run:
                        generated = "# DRY RUN\n" + prompt
                    else:
                        generated = _chat_messages(llm, messages)
                        cached[key] = generated
                        _append_jsonl(cache_path, {"key": key, "test": generated})
                    best = generated
                    if args.dry_run:
                        break
                    result = evaluate_target(record, generated, target_line, args.test_timeout)
                    if result["status"] == "covered":
                        break
                    messages.extend(
                        [
                            {"role": "assistant", "content": generated},
                            {"role": "user", "content": feedback_message(result, target_line) + " Return only the corrected test function."},
                        ]
                    )
                tests[target_line] = best
            destination.write(json.dumps(result_record(record, args.mode, tests, FEEDBACK_PROMPT_VERSION), ensure_ascii=False) + "\n")
            destination.flush()
            count += 1
            print(f"task={record['task_num']} mode=feedback-line targets={len(tests)}", flush=True)
    print(f"generated {count} feedback-loop task(s) -> {output}")
    return count


def _chat_messages(llm: Any, messages: list[dict[str, str]]) -> str:
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

    response = llm.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT)
        ]
        + [
            AIMessage(content=item["content"]) if item["role"] == "assistant" else HumanMessage(content=item["content"])
            for item in messages
        ]
    )
    text = _response_text(getattr(response, "content", response))
    if not text.strip():
        raise ValueError("LLM returned empty or non-text content")
    generated = clean_model_output(text)
    _validate_generated_test(generated)
    return generated


def _load_cache(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open() as handle:
        return {row["key"]: row["test"] for row in (json.loads(line) for line in handle if line.strip()) if row.get("key") and row.get("test")}


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


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


def _load_paths(path: str | None) -> dict[int, dict[str, Any]]:
    if not path:
        return {}
    with Path(path).open() as handle:
        return {row["task_num"]: row for row in (json.loads(line) for line in handle if line.strip())}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in", dest="input", required=True)
    parser.add_argument("--paths")
    parser.add_argument("--out", required=True)
    parser.add_argument("--cache")
    parser.add_argument("--mode", choices=("line",), default="line")
    parser.add_argument("--prompt-mode", choices=("symbolic", "baseline"), default="symbolic")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--max-targets", type=int, default=0)
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--test-timeout", type=int, default=5)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--request-timeout", type=float, default=60.0)
    parser.add_argument("--max-output-tokens", type=int, default=4096)
    parser.add_argument("--dry-run", action="store_true")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
