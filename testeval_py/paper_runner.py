"""Run the official TestEval targeted-line protocols with an optional concept block.

The upstream prompt, line numbering, response formatting, and evaluator are
loaded from a pinned TestEval checkout. The only prompt change in the concept
arm is an appended reachability block.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from concept_annotator_py import annotate_record
from magma.llm_client import make_llm, model_id
from testeval_py.llm_runner import _response_text, _retry_delay_seconds

DEFAULT_COT_FACT_KINDS = {
    "branch_true",
    "branch_false",
    "avoid_early_exit",
    "state_after_update",
    "state_before_use",
    "loop_two_plus_iteration",
    "recursive_argument_swap",
}


def _upstream_modules(root: Path) -> tuple[Any, Any]:
    if not (root / "data_utils.py").is_file() or not (root / "format.py").is_file():
        raise SystemExit(f"TestEval upstream source missing in {root}")
    sys.path.insert(0, str(root))
    import data_utils  # type: ignore[import-not-found]

    spec = importlib.util.spec_from_file_location("testeval_upstream_format", root / "format.py")
    assert spec and spec.loader
    formatter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(formatter)
    return data_utils, formatter


def build_paper_prompt(
    record: dict[str, Any],
    line: int,
    system_template: str,
    line_template: str,
    add_lineno: Any,
    concept_block: str | None = None,
) -> str:
    """Match upstream Gemini's one-string prompt construction exactly."""
    code = record["python_solution"]
    target_text = f"{line}: {code.split(chr(10))[line - 1]}"
    prompt = system_template.format(lang="python") + line_template.format(
        lang="python",
        program=add_lineno(code),
        description=record["description"],
        func_name=record["func_name"],
        lineno=target_text,
    )
    if concept_block is not None:
        prompt += "\n\n" + concept_block
    return prompt


def _concept_block(target: dict[str, Any], fact_kinds: set[str] | None) -> str | None:
    facts = target.get("symbolic", {}).get("reachability_facts", [])
    selected = [fact for fact in facts if fact_kinds is None or fact["kind"] in fact_kinds]
    if not selected:
        return None
    return "Reachability facts for this target:\n" + "\n".join(
        f"- {fact['kind']}: {fact['detail']}" for fact in selected
    )


def _witness_block(witness: dict[str, Any] | None) -> str | None:
    if not witness:
        return None
    locals_text = ", ".join(
        f"{name}={value!r}" for name, value in witness.get("locals_at_target", {}).items()
    )
    lines = [
        "Verified execution witness:",
        f"- {witness['call']} reached line {witness['target_line']} and returned normally.",
        "- Recent executed source lines: " + " -> ".join(map(str, witness.get("recent_lines", []))),
    ]
    if locals_text:
        lines.append("- State immediately before target line: " + locals_text)
    lines.append("- LeetCode input constraints were not independently verified by this search.")
    return "\n".join(lines)


def _condition_hypotheses_block(facts: str | None, witness: str | None) -> str | None:
    parts: list[str] = []
    if facts:
        parts.append(facts.replace("Reachability facts for this target:", "Static facts from program analysis:"))
    if witness:
        parts.append(witness)
    if not parts:
        return None
    parts.append(
        "Use these facts to derive the necessary conditions for reaching the target. "
        "Correct them if they conflict with the source."
    )
    return "\n\n".join(parts)


def _test_witness_block(witness: str | None) -> str | None:
    if not witness:
        return None
    return (
        "Generated conditions above are the primary constraints.\n\n"
        + witness
        + "\n\nGenerate the test that satisfies both the generated conditions and the verified witness."
    )


def _response_text_if_complete(response: Any) -> str:
    metadata = getattr(response, "response_metadata", {}) or {}
    finish = metadata.get("finish_reason")
    if finish is not None and str(finish).upper() not in {"1", "STOP", "FINISH_REASON_STOP"}:
        return ""
    return _response_text(getattr(response, "content", response))


def _invoke(
    llm: Any,
    prompt: str,
    retries: int,
    retry_sleep: float,
    retry_max_wait: float,
    system_prompt: str | None = None,
) -> str:
    from langchain_core.messages import HumanMessage, SystemMessage

    for attempt in range(retries + 1):
        try:
            messages = ([SystemMessage(content=system_prompt)] if system_prompt is not None else [])
            messages.append(HumanMessage(content=prompt))
            response = llm.invoke(messages)
            return _response_text_if_complete(response)
        except Exception as exc:
            if attempt == retries:
                raise RuntimeError(f"Vertex call failed after {retries + 1} attempts: {exc}") from exc
            delay = _retry_delay_seconds(exc, attempt, retry_sleep, retry_max_wait)
            print(f"[retry] waiting {delay:.1f}s after {type(exc).__name__}: {str(exc)[:120]}", flush=True)
            time.sleep(delay)
    raise AssertionError("unreachable")


def _load_cache(path: Path) -> dict[str, str]:
    cache: dict[str, str] = {}
    if path.exists():
        for line in path.read_text().splitlines():
            try:
                row = json.loads(line)
                cache[row["key"]] = row["raw"]
            except (ValueError, KeyError, TypeError):
                continue
    return cache


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _append_cache(path: Path, key: str, raw: str) -> None:
    _append_jsonl(path, {"key": key, "raw": raw})


def run(args: argparse.Namespace, llm: Any | None = None) -> dict[str, int]:
    upstream = Path(args.upstream).resolve()
    data_utils, formatter = _upstream_modules(upstream)
    protocol = getattr(args, "protocol", "basic")
    if protocol not in {"basic", "two-step"}:
        raise SystemExit("--protocol must be basic or two-step")
    dataset_name = "leetcode-py-all.jsonl" if protocol == "two-step" else "leetcode-py.jsonl"
    dataset = upstream / "data" / dataset_name
    if not dataset.is_file():
        raise SystemExit(f"Official dataset missing: {dataset}")
    if protocol == "two-step":
        system = (upstream / "prompt" / "system_exec.txt").read_text()
        condition_template = (upstream / "prompt" / "line_oneshot_gencond.txt").read_text()
        test_template = (upstream / "prompt" / "line_oneshot_gentest.txt").read_text()
    else:
        system = (upstream / "prompt" / "system.txt").read_text()
        template = (upstream / "prompt" / "template_line.txt").read_text()
    records = data_utils.read_jsonl(dataset)
    task_num = getattr(args, "task_num", None)
    records = (
        [record for record in records if record["task_num"] == task_num]
        if task_num is not None else records[: args.limit or None]
    )
    if task_num is not None and not records:
        raise SystemExit(f"Task {task_num} not found in {dataset}")
    target_line = getattr(args, "target_line", None)
    if target_line is not None and not any(target_line in record["target_lines"] for record in records):
        raise SystemExit(f"Target line {target_line} not found in selected task(s)")
    if args.arm in {"concept", "concept-witness"}:
        from testeval_py.llm_runner import _parse_fact_kinds

        kinds = _parse_fact_kinds(args.concept_facts)
        if kinds is None and protocol == "two-step":
            kinds = DEFAULT_COT_FACT_KINDS
    else:
        if args.concept_facts:
            raise SystemExit("--concept-facts applies only to --arm concept")
        kinds = None
    if args.arm == "concept-witness" and protocol != "two-step":
        raise SystemExit("--arm concept-witness requires --protocol two-step")
    if llm is None and not args.dry_run:
        if os.environ.get("LLM_PROVIDER") != "vertex":
            raise SystemExit("Set LLM_PROVIDER=vertex for the native Vertex arm")
        llm = make_llm(
            temperature=0,
            timeout=args.request_timeout,
            max_retries=0,
            max_tokens=args.max_output_tokens or (1024 if protocol == "two-step" else 256),
        )
        if llm is None:
            raise SystemExit("Native Vertex is not configured")
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    cache_path = Path(args.cache) if args.cache else Path(str(output) + ".cache.jsonl")
    primary_cache = _load_cache(cache_path)
    cache = {}
    for reused_path in getattr(args, "reuse_cache", []) or []:
        cache.update(_load_cache(Path(reused_path)))
    cache.update(primary_cache)

    def persist_reused(key: str) -> str:
        raw = cache[key]
        if key not in primary_cache:
            primary_cache[key] = raw
            _append_cache(cache_path, key, raw)
        return raw

    witness_cache_path = Path(str(output) + ".witnesses.jsonl")
    witness_cache = {}
    if args.arm == "concept-witness" and witness_cache_path.exists():
        for entry in witness_cache_path.read_text().splitlines():
            try:
                row = json.loads(entry)
                witness_cache[row["key"]] = row["result"]
            except (ValueError, KeyError, TypeError):
                continue
    raw_rows = []
    formatted_rows = []
    errors = 0
    fallback_total = 0
    for record in records:
        raw_tests = {}
        formatted_tests = {}
        conditions = {}
        fallback_targets = []
        annotation = annotate_record(record)["concept_annotation_py"] if args.arm != "baseline" else None
        selected_targets = [
            (index, line)
            for index, line in enumerate(record["target_lines"][: args.max_targets or None])
            if target_line is None or line == target_line
        ]
        witness_result = None
        if args.arm == "concept-witness":
            from testeval_py.verified_witness import WITNESS_VERSION, find_verified_witnesses

            selected = {**record, "target_lines": [line for _, line in selected_targets]}
            witness_key = hashlib.sha256(
                json.dumps(
                    [WITNESS_VERSION, args.witness_seconds, args.witness_max_candidates,
                     selected["func_name"], selected["python_solution"], selected.get("description", ""),
                     selected["target_lines"]],
                    ensure_ascii=False,
                ).encode()
            ).hexdigest()
            if witness_key in witness_cache:
                witness_result = witness_cache[witness_key]
            else:
                witness_result = find_verified_witnesses(
                    selected, seconds=args.witness_seconds, max_candidates=args.witness_max_candidates
                )
                witness_cache[witness_key] = witness_result
                _append_jsonl(witness_cache_path, {"key": witness_key, "result": witness_result})
            verified = {int(line): value for line, value in witness_result.get("witnesses", {}).items()}
        for index, line in selected_targets:
            block = None
            if annotation is not None:
                block = _concept_block(annotation["line_targets"][index], kinds)
            if protocol == "two-step":
                numbered = data_utils.add_lineno_comment(record["python_solution"])
                condition_prompt = condition_template.format(program=numbered, targetline=line)
                witness_text = _witness_block(verified.get(line)) if witness_result is not None else None
                condition_hypotheses = _condition_hypotheses_block(block, witness_text)
                if condition_hypotheses:
                    condition_prompt += "\n\n" + condition_hypotheses
                condition_key = hashlib.sha256(
                    (model_id() + "\0two-step:conditions\0" + system + "\0" + condition_prompt).encode()
                ).hexdigest()
                condition_failed = False
                try:
                    if args.dry_run:
                        condition = condition_prompt
                    elif condition_key in cache:
                        condition = persist_reused(condition_key)
                    else:
                        condition = _invoke(
                            llm, condition_prompt, args.retries, args.retry_sleep, args.retry_max_wait, system
                        )
                        cache[condition_key] = condition
                        primary_cache[condition_key] = condition
                        _append_cache(cache_path, condition_key, condition)
                except Exception as exc:
                    errors += 1
                    condition_failed = True
                    condition = ""
                    print(f"[error] conditions task={record['task_num']} line={line}: {exc}", flush=True)
                conditions[line] = condition
                test_prompt = test_template.format(
                    func_name=record["func_name"], program=numbered, conditions=condition
                )
                test_witness = _test_witness_block(witness_text)
                if test_witness:
                    test_prompt += "\n\n" + test_witness
                prompt = test_prompt
                key = hashlib.sha256(
                    (model_id() + "\0two-step:test\0" + system + "\0" + prompt).encode()
                ).hexdigest()
                system_prompt = system
            else:
                prompt = build_paper_prompt(record, line, system, template, data_utils.add_lineno, block)
                key = hashlib.sha256((model_id() + "\0" + prompt).encode()).hexdigest()
                system_prompt = None
            if protocol == "two-step" and condition_failed:
                raw = ""
            elif args.dry_run:
                raw = prompt
            elif key in cache:
                raw = persist_reused(key)
            else:
                try:
                    raw = _invoke(llm, prompt, args.retries, args.retry_sleep, args.retry_max_wait, system_prompt)
                    cache[key] = raw
                    primary_cache[key] = raw
                    _append_cache(cache_path, key, raw)
                except Exception as exc:
                    errors += 1
                    raw = ""
                    print(f"[error] test task={record['task_num']} line={line}: {exc}", flush=True)
            raw_tests[line] = raw
            formatted_tests[line] = (
                formatter.reformat_case_byrules(
                    formatter.remove_extra(raw, record["func_name"]),
                    f"test_{record['func_name']}",
                ) if not args.dry_run else raw
            )
            if (
                witness_result is not None
                and not args.dry_run
                and getattr(args, "witness_fallback", True)
                and line in verified
            ):
                from testeval_py.feedback_loop import evaluate_target

                current = evaluate_target(record, formatted_tests[line], line)
                if not current["covered"] or current["status"] == "runtime_error":
                    fallback = (
                        f"def test_{record['func_name']}():\n"
                        f"    solution = Solution()\n"
                        f"    {verified[line]['call']}"
                    )
                    fallback = formatter.reformat_case_byrules(
                        formatter.remove_extra(fallback, record["func_name"]),
                        f"test_{record['func_name']}",
                    )
                    checked = evaluate_target(record, fallback, line)
                    if checked["status"] == "covered":
                        formatted_tests[line] = fallback
                        fallback_targets.append(line)
                        fallback_total += 1
        base = {
            "task_num": record["task_num"],
            "task_title": record["task_title"],
            "func_name": record["func_name"],
            "difficulty": record["difficulty"],
            "code": record["python_solution"],
        }
        extras = {"conditions": conditions} if protocol == "two-step" else {}
        if witness_result is not None:
            extras["witness_search"] = witness_result
            extras["witness_fallback_targets"] = fallback_targets
        raw_rows.append({**base, "tests": raw_tests, **extras})
        formatted_rows.append({**base, "tests": formatted_tests, **extras})
        print(f"task={record['task_num']} targets={len(raw_tests)} arm={args.arm} protocol={protocol}", flush=True)
    raw_path = Path(str(output) + ".raw.jsonl")
    data_utils.write_jsonl(raw_rows, raw_path)
    data_utils.write_jsonl(formatted_rows, output)
    total = sum(len(row["tests"]) for row in formatted_rows)
    print(
        f"wrote {len(records)} tasks, {total} targets, {errors} provider errors, "
        f"{fallback_total} verified-witness fallbacks -> {output}"
    )
    return {"tasks": len(records), "targets": total, "provider_errors": errors, "fallbacks": fallback_total}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", required=True, help="Pinned official TestEval checkout")
    parser.add_argument("--out", required=True, help="Formatted predictions for upstream eval_linecov.py")
    parser.add_argument("--cache")
    parser.add_argument("--reuse-cache", nargs="*", help="Read existing compatible prompt-hash caches")
    parser.add_argument("--arm", choices=("baseline", "concept", "concept-witness"), required=True)
    parser.add_argument("--protocol", choices=("basic", "two-step"), default="basic")
    parser.add_argument("--concept-facts", help="Optional comma-separated whitelist for concept arm")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--task-num", type=int, help="Run one official task by task_num")
    parser.add_argument("--target-line", type=int, help="Run one target line within the selected task")
    parser.add_argument("--max-targets", type=int, default=0, help="Targets per task; 0 means all")
    parser.add_argument("--witness-seconds", type=float, default=2.0, help="Local search time budget per program")
    parser.add_argument("--witness-max-candidates", type=int, default=800)
    parser.add_argument("--no-witness-fallback", action="store_false", dest="witness_fallback",
                        help="Prompt-only ablation: do not replace missed targets with a verified call")
    parser.add_argument("--max-output-tokens", type=int, help="Default: 256 basic, 1024 two-step")
    parser.add_argument("--request-timeout", type=float, default=360)
    parser.add_argument("--retries", type=int, default=5)
    parser.add_argument("--retry-sleep", type=float, default=30)
    parser.add_argument("--retry-max-wait", type=float, default=180)
    parser.add_argument("--dry-run", action="store_true")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
