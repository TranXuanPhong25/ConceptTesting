#!/usr/bin/env python3
"""Generate TestEval Python targeted tests with an OpenAI-compatible LLM."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Callable

from concept_annotator_py import annotate_record, render_prompt_block


SYSTEM_PROMPT = (
    "You write standalone Python test functions for the given LeetCode-style Solution class. "
    "Return exactly one executable zero-argument function and no explanation. "
    "The function is not a unittest.TestCase method: never add a self parameter and use plain assert, never self.assert*. "
    "Use one minimal concrete input unless the target requires otherwise, keep the function under 40 lines, "
    "and do not use markdown fences."
)

PROMPT_VERSION = "symbolic-v1"


def build_line_prompt(record: dict[str, Any], annotation: dict[str, Any], target: dict[str, Any]) -> str:
    source = _numbered_source(record["python_solution"])
    concepts = render_prompt_block({**annotation, "line_targets": [target], "branch_targets": [], "path_targets": []})
    return (
        "Write one Python unittest method for the function `{func}`.\n\n"
        "Problem description:\n{description}\n\n"
        "Program under test (line-numbered):\n```python\n{source}\n```\n\n"
        "The test must execute target line {line}.\n"
        "Target code: `{code}`\n"
        "Target concepts: {target_concepts}\n\n"
        "Static TestEval context:\n{concepts}\n\n"
        "Start exactly with `def test_{func}():`, create `solution = Solution()`, "
        "and call the method with concrete inputs. Do not return explanations, markdown, "
        "or assertions about implementation details."
    ).format(
        func=record["func_name"],
        description=record.get("description", ""),
        source=source,
        line=target["line"],
        code=target.get("code", ""),
        target_concepts=", ".join(target.get("concepts", [])) or "none",
        concepts=concepts,
    )


def build_branch_prompt(record: dict[str, Any], annotation: dict[str, Any], target: dict[str, Any]) -> str:
    source = _numbered_source(record["python_solution"])
    concepts = render_prompt_block({**annotation, "line_targets": [], "branch_targets": [target], "path_targets": []})
    return (
        "Write one Python unittest method for the function `{func}`.\n\n"
        "Problem description:\n{description}\n\n"
        "Program under test (line-numbered):\n```python\n{source}\n```\n\n"
        "The test must execute the target branch from line {start} to line {end}.\n"
        "Branch condition: `{condition}`. The branch must execute, not merely be present in the input.\n"
        "Static TestEval context:\n{concepts}\n\n"
        "Start exactly with `def test_{func}():`, create `solution = Solution()`, "
        "and call the method with concrete inputs. Do not return explanations, markdown, "
        "or assertions about implementation details."
    ).format(
        func=record["func_name"],
        description=record.get("description", ""),
        source=source,
        start=target["start"],
        end=target["end"],
        condition=target.get("condition") or "fallthrough",
        concepts=concepts,
    )


def clean_model_output(raw: str) -> str:
    """Extract one test method while tolerating common markdown wrappers."""
    text = raw.strip()
    match = re.search(r"```(?:python)?\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
    if match:
        text = match.group(1).strip()
    start = text.find("def test_")
    if start >= 0:
        text = text[start:]
    return text.strip()


def result_record(record: dict[str, Any], mode: str, tests: dict[int, str] | list[dict[str, Any]]) -> dict[str, Any]:
    if mode == "line":
        tests = {str(line): test for line, test in tests.items()}
    return {
        "task_num": record["task_num"],
        "task_title": record.get("task_title"),
        "func_name": record["func_name"],
        "difficulty": record.get("difficulty"),
        "code": record["python_solution"],
        "tests": tests,
        "generation_mode": mode,
        "prompt_version": PROMPT_VERSION,
    }


def _numbered_source(source: str) -> str:
    return "\n".join(f"{i}: {line}" for i, line in enumerate(source.splitlines(), 1))


def _load_paths(path: str | None) -> dict[int, dict[str, Any]]:
    if not path:
        return {}
    with Path(path).open() as handle:
        return {row["task_num"]: row for row in (json.loads(line) for line in handle if line.strip())}


def _chat(llm: Any, prompt: str) -> str:
    from langchain_core.messages import HumanMessage, SystemMessage

    response = llm.invoke([SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=prompt)])
    content = getattr(response, "content", response)
    text = _response_text(content)
    if not text.strip():
        raise ValueError("LLM returned empty or non-text content")
    generated = clean_model_output(text)
    _validate_generated_test(generated)
    return generated


def _response_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and isinstance(block.get("text"), str):
            parts.append(block["text"])
    return "\n".join(parts)


def _validate_generated_test(source: str) -> None:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise ValueError(f"LLM returned invalid Python: {exc.msg}") from exc
    functions = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if len(functions) != 1 or not functions[0].name.startswith("test_"):
        raise ValueError("LLM must return exactly one top-level test function")
    args = functions[0].args
    if args.args or args.posonlyargs or args.kwonlyargs or args.vararg or args.kwarg:
        raise ValueError("LLM test function must have zero parameters")
    if any(
        isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "self"
        for node in ast.walk(functions[0])
    ):
        raise ValueError("LLM test function must not use self.assert methods")


def _generate_with_retry(llm: Any, prompt: str, retries: int, sleep_seconds: float) -> str:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return _chat(llm, prompt)
        except Exception as exc:  # network/provider errors are retriable
            last_error = exc
            if attempt < retries:
                time.sleep(sleep_seconds * (2**attempt))
    raise RuntimeError(f"LLM call failed after {retries + 1} attempt(s): {last_error}") from last_error


def _target_key(mode: str, task_num: int, target: dict[str, Any], index: int) -> str:
    if mode == "line":
        return f"{PROMPT_VERSION}:line:{task_num}:{target['line']}"
    return f"{PROMPT_VERSION}:branch:{task_num}:{index}:{target['start']}:{target['end']}"


def _load_cache(path: Path) -> dict[str, str]:
    cached: dict[str, str] = {}
    if not path.exists():
        return cached
    with path.open() as handle:
        for line in handle:
            try:
                row = json.loads(line)
                if row.get("key") and row.get("test"):
                    cached[row["key"]] = row["test"]
            except (json.JSONDecodeError, TypeError):
                continue
    return cached


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _seed_cache_from_output(path: Path, mode: str, cached: dict[str, str], cache_path: Path) -> None:
    if not path.exists():
        return
    with path.open() as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            task_num = row.get("task_num")
            if row.get("prompt_version") != PROMPT_VERSION:
                continue
            if mode == "line":
                entries = [
                    (f"{PROMPT_VERSION}:line:{task_num}:{target_line}", test)
                    for target_line, test in row.get("tests", {}).items()
                ]
            else:
                entries = [
                    (f"{PROMPT_VERSION}:branch:{task_num}:{index}:{test.get('start')}:{test.get('end')}", test.get("test"))
                    for index, test in enumerate(row.get("tests", []))
                ]
            for key, test in entries:
                if test and key not in cached:
                    cached[key] = test
                    _append_jsonl(cache_path, {"key": key, "test": test})


def run(args: argparse.Namespace, llm_factory: Callable[[float, float, int], Any] | None = None) -> int:
    if args.mode not in {"line", "branch"}:
        raise SystemExit("--mode must be line or branch")
    path_by_task = _load_paths(args.paths)
    llm = (
        None
        if args.dry_run
        else (llm_factory or _default_llm_factory)(args.temperature, args.request_timeout, args.max_output_tokens)
    )
    if not args.dry_run and llm is None:
        raise SystemExit("LLM is not configured. Source scripts/router_env.sh and set LLM_PROVIDER=router.")

    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    cache_path = Path(args.cache) if args.cache else Path(str(output) + ".cache.jsonl")
    errors_path = Path(str(output) + ".errors.jsonl")
    cached = _load_cache(cache_path)
    _seed_cache_from_output(output, args.mode, cached, cache_path)
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
            tests: dict[int, str] | list[dict[str, Any]]
            if args.mode == "line":
                tests = {}
                targets = annotation["line_targets"][: args.max_targets or None]
                for index, target in enumerate(targets):
                    prompt = build_line_prompt(record, annotation, target)
                    key = _target_key(args.mode, record["task_num"], target, index)
                    try:
                        if args.dry_run:
                            generated = "# DRY RUN\n" + prompt
                        elif key in cached:
                            generated = cached[key]
                        else:
                            generated = _generate_with_retry(llm, prompt, args.retries, args.retry_sleep)
                            cached[key] = generated
                            _append_jsonl(cache_path, {"key": key, "test": generated})
                        tests[target["line"]] = generated
                    except Exception as exc:
                        _append_jsonl(errors_path, {"key": key, "error": f"{type(exc).__name__}: {exc}"})
                        if args.fail_fast:
                            raise
                        tests[target["line"]] = ""
                        print(f"[error] {key}: {type(exc).__name__}: {exc}", flush=True)
            else:
                tests = []
                targets = annotation["branch_targets"][: args.max_targets or None]
                for index, target in enumerate(targets):
                    prompt = build_branch_prompt(record, annotation, target)
                    key = _target_key(args.mode, record["task_num"], target, index)
                    try:
                        if args.dry_run:
                            generated = "# DRY RUN\n" + prompt
                        elif key in cached:
                            generated = cached[key]
                        else:
                            generated = _generate_with_retry(llm, prompt, args.retries, args.retry_sleep)
                            cached[key] = generated
                            _append_jsonl(cache_path, {"key": key, "test": generated})
                    except Exception as exc:
                        _append_jsonl(errors_path, {"key": key, "error": f"{type(exc).__name__}: {exc}"})
                        if args.fail_fast:
                            raise
                        generated = ""
                        print(f"[error] {key}: {type(exc).__name__}: {exc}", flush=True)
                    tests.append({"start": target["start"], "end": target["end"], "test": generated})
            destination.write(json.dumps(result_record(record, args.mode, tests), ensure_ascii=False) + "\n")
            destination.flush()
            os.fsync(destination.fileno())
            count += 1
            print(f"task={record['task_num']} mode={args.mode} targets={len(targets)}", flush=True)
    print(f"generated {count} TestEval task(s) -> {output}")
    return count


def _default_llm_factory(temperature: float, request_timeout: float, max_output_tokens: int):
    from magma.llm_client import make_llm

    return make_llm(
        temperature=temperature,
        timeout=request_timeout,
        max_retries=0,
        max_tokens=max_output_tokens,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in", dest="input", required=True, help="Raw or annotated TestEval leetcode-py JSONL")
    parser.add_argument("--paths", help="TestEval tgt_paths.jsonl")
    parser.add_argument("--out", required=True, help="TestEval-compatible prediction JSONL")
    parser.add_argument("--cache", help="Successful target cache; defaults to <out>.cache.jsonl")
    parser.add_argument("--mode", choices=("line", "branch"), default="line")
    parser.add_argument("--limit", type=int, default=0, help="Maximum tasks; 0 means all")
    parser.add_argument("--max-targets", type=int, default=0, help="Maximum targets per task; 0 means all")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--request-timeout", type=float, default=60.0, help="Timeout per provider request in seconds")
    parser.add_argument("--max-output-tokens", type=int, default=4096, help="Maximum tokens in one generated test")
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--retry-sleep", type=float, default=2.0)
    parser.add_argument("--dry-run", action="store_true", help="Write prompts without calling the LLM")
    parser.add_argument("--fail-fast", action="store_true", help="Stop after a target exhausts all retries")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
