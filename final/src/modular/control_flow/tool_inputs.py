"""Strictly oracle-free loader for saved 4-tool pytest inputs (excluding Klara)."""
from __future__ import annotations

from collections import Counter
import json
import os
from pathlib import Path

from ..call_builder import CallBuilder, input_identity
from final.src.runtime.execution import ExecutionError, execute

FOUR_TOOLS = ("crosshair", "pynguin", "utbot", "ghostwriter")
DEFAULT_MAX_PRIOR_INPUTS = 128
DEFAULT_MAX_PROMPT_PRIOR_INPUTS = 12
MAX_PROMPT_CALL_CHARS = 300
VALIDATE_CHUNK_SIZE = 64

TOOL_RUN_SUBDIRS = {
    "HumanEval": "final/out/put_pytest_tools_20261122",
    "MBPP": "final/out/mbppplus_put_pytest_tools_20261122",
}


def default_tool_runs_dir(task_id: str, *, workspace: str | Path | None = None) -> Path:
    """Resolve the default 4-tool saved artifact root for HumanEval or MBPP+."""
    prefix = task_id.split("/", 1)[0]
    relative = TOOL_RUN_SUBDIRS.get(prefix, TOOL_RUN_SUBDIRS["HumanEval"])
    roots: list[Path] = []
    if workspace is not None:
        roots.append(Path(workspace))
    env_workspace = os.environ.get("CONCEPTTESTER_WORKSPACE")
    if env_workspace:
        roots.append(Path(env_workspace))
    here = Path(__file__).resolve()
    roots.extend(here.parents)
    cwd = Path.cwd().resolve()
    roots.append(cwd)
    roots.extend(cwd.parents)

    seen: set[Path] = set()
    for root in roots:
        if root in seen:
            continue
        seen.add(root)
        candidate = root / relative
        if candidate.is_dir():
            return candidate
    fallback_root = here.parents[4] if len(here.parents) > 4 else cwd
    return fallback_root / relative


def is_sandbox_infrastructure_error(error: BaseException) -> bool:
    """Distinguish host/bwrap infrastructure failures from per-input crashes."""
    text = str(error)
    return (
        "bubblewrap is required" in text
        or "bwrap:" in text
        or "Creating new namespace failed" in text
    )


def _validate_domain_chunk(task: dict, contract: str, chunk: list[dict], *, timeout: float, seed: int) -> list[dict]:
    """Run oracle-free domain contract validation with binary-split fallback."""
    if not chunk:
        return []
    job = {
        "mode": "validate",
        "context": task["prompt"],
        "contract": contract,
        "entry": task["entry_point"],
        "tests": [{"args": row["args"], "kwargs": row["kwargs"]} for row in chunk],
        "timeout": timeout,
        "seed": seed,
    }
    try:
        outcome = execute(job)
        tests = outcome.get("tests")
        if not isinstance(tests, list) or len(tests) != len(chunk):
            raise ExecutionError("Invalid validate outcome")
        return tests
    except ExecutionError as error:
        if is_sandbox_infrastructure_error(error):
            raise
        if len(chunk) > 1:
            mid = len(chunk) // 2
            return (
                _validate_domain_chunk(task, contract, chunk[:mid], timeout=timeout, seed=seed)
                + _validate_domain_chunk(task, contract, chunk[mid:], timeout=timeout, seed=seed)
            )
        return [{"status": "timeout"}]


def _validate_domain_candidates(
    task: dict,
    contract: str,
    candidates: list[dict],
    *,
    timeout: float,
    seed: int,
    chunk_size: int = VALIDATE_CHUNK_SIZE,
) -> list[dict]:
    outcomes: list[dict] = []
    for offset in range(0, len(candidates), chunk_size):
        chunk = candidates[offset : offset + chunk_size]
        outcomes.extend(_validate_domain_chunk(task, contract, chunk, timeout=timeout, seed=seed))
    return outcomes


def _put_sort_key(path: Path) -> tuple[int, int | str]:
    return (0, int(path.name)) if path.name.isdigit() else (1, path.name)


def _round_robin_select(entries: list[dict], limit: int) -> list[dict]:
    """Select up to `limit` unique inputs balanced across the 4 pytest tools."""
    if limit <= 0 or not entries:
        return []
    queues: dict[str, list[dict]] = {}
    for tool in FOUR_TOOLS:
        primary = [row for row in entries if row["first_tool"] == tool]
        secondary = [row for row in entries if row["first_tool"] != tool and tool in row["tools"]]
        queues[tool] = primary + secondary

    selected: list[dict] = []
    chosen_keys: set[str] = set()
    cursors = {tool: 0 for tool in FOUR_TOOLS}
    while len(selected) < limit:
        progressed = False
        for tool in FOUR_TOOLS:
            queue = queues[tool]
            cursor = cursors[tool]
            while cursor < len(queue) and queue[cursor]["key"] in chosen_keys:
                cursor += 1
            cursors[tool] = cursor
            if cursor < len(queue):
                entry = queue[cursor]
                cursors[tool] = cursor + 1
                chosen_keys.add(entry["key"])
                selected.append(entry)
                progressed = True
                if len(selected) >= limit:
                    break
        if not progressed:
            break
    return selected


def load_four_tool_prior_inputs(
    task: dict,
    metadata: dict | None,
    programs: list[dict],
    *,
    tool_runs_dir: str | Path | None = None,
    max_prior_inputs: int = DEFAULT_MAX_PRIOR_INPUTS,
    validate_timeout: float = 2.0,
    seed: int = 271828,
    validator=None,
) -> dict:
    """Load unique, signature/domain-valid 4-tool inputs without ever reading oracle_replay.json."""
    runs_dir = Path(tool_runs_dir) if tool_runs_dir else default_tool_runs_dir(task["task_id"])
    if not runs_dir.is_dir():
        raise FileNotFoundError(f"4-tool runs directory not found: {runs_dir}")

    task_number = int(task["task_id"].split("/")[1])
    task_dir = runs_dir / "tasks" / str(task_number)
    builder = CallBuilder.for_source(task["prompt"], task["entry_point"])

    base_keys: set[str] = set()
    for program in programs:
        for call in program.get("base", {}).get("calls", []):
            try:
                base_keys.add(repr(input_identity(builder.signature, call)))
            except (ValueError, TypeError, SyntaxError, KeyError):
                pass

    if not task_dir.is_dir():
        return {
            "inputs": [],
            "stats": {
                "tool_runs_dir": str(runs_dir),
                "task_dir_present": False,
                "tools": list(FOUR_TOOLS),
                "receipts_read": 0,
                "raw_calls": 0,
                "invalid_signature": 0,
                "base_duplicates_skipped": 0,
                "unique_candidates": 0,
                "domain_checked": False,
                "domain_rejected": 0,
                "unique_valid": 0,
                "selected": 0,
                "selected_by_tool": {},
            },
        }

    receipts_read = 0
    raw_calls = 0
    invalid_signature = 0
    base_duplicates_skipped = 0
    unique: dict[str, dict] = {}

    # Read ONLY pre-oracle per-tool receipt.json files; never read oracle_replay.json.
    for put_dir in sorted((p for p in task_dir.iterdir() if p.is_dir()), key=_put_sort_key):
        for tool in FOUR_TOOLS:
            receipt_path = put_dir / tool / "receipt.json"
            if not receipt_path.is_file():
                continue
            receipt = json.loads(receipt_path.read_text())
            if receipt.get("base", "pass") != "pass":
                continue
            receipts_read += 1
            for call_row in receipt.get("calls", []):
                raw_calls += 1
                if not isinstance(call_row, dict):
                    invalid_signature += 1
                    continue
                args_literal = call_row.get("args")
                kwargs_literal = call_row.get("kwargs")
                if not isinstance(args_literal, str) or not isinstance(kwargs_literal, str):
                    invalid_signature += 1
                    continue
                record = {"args": args_literal, "kwargs": kwargs_literal}
                try:
                    builder.validate_call(record)
                    key = repr(input_identity(builder.signature, record))
                except (ValueError, TypeError, SyntaxError, KeyError, RecursionError):
                    invalid_signature += 1
                    continue
                if key in base_keys:
                    base_duplicates_skipped += 1
                    continue
                if key in unique:
                    if tool not in unique[key]["tools"]:
                        unique[key]["tools"].append(tool)
                    if put_dir.name not in unique[key]["put_ids"]:
                        unique[key]["put_ids"].append(put_dir.name)
                else:
                    unique[key] = {
                        "key": key,
                        "args": args_literal,
                        "kwargs": kwargs_literal,
                        "first_tool": tool,
                        "tools": [tool],
                        "put_ids": [put_dir.name],
                    }

    candidates = list(unique.values())
    contract = (metadata or {}).get("contract", "")
    domain_checked = bool(contract and contract.strip() and candidates)
    domain_rejected = 0
    if domain_checked:
        validate_fn = validator or _validate_domain_candidates
        outcomes = validate_fn(task, contract, candidates, timeout=validate_timeout, seed=seed)
        valid_entries: list[dict] = []
        for entry, outcome in zip(candidates, outcomes, strict=True):
            if outcome.get("status") == "valid":
                valid_entries.append(entry)
            else:
                domain_rejected += 1
    else:
        valid_entries = candidates

    selected = _round_robin_select(valid_entries, max_prior_inputs)
    formatted = [
        {
            "input_id": f"tool4_{index}",
            "source_stage": f"tool4:{entry['first_tool']}",
            "tools": list(entry["tools"]),
            "args": entry["args"],
            "kwargs": entry["kwargs"],
        }
        for index, entry in enumerate(selected)
    ]
    selected_by_tool = dict(Counter(row["source_stage"].split(":", 1)[-1] for row in formatted))
    return {
        "inputs": formatted,
        "stats": {
            "tool_runs_dir": str(runs_dir),
            "task_dir_present": True,
            "tools": list(FOUR_TOOLS),
            "receipts_read": receipts_read,
            "raw_calls": raw_calls,
            "invalid_signature": invalid_signature,
            "base_duplicates_skipped": base_duplicates_skipped,
            "unique_candidates": len(candidates),
            "domain_checked": domain_checked,
            "domain_rejected": domain_rejected,
            "unique_valid": len(valid_entries),
            "selected": len(formatted),
            "selected_by_tool": selected_by_tool,
        },
    }


def compact_prompt_prior_inputs(
    prior_inputs: list[dict],
    *,
    limit: int = DEFAULT_MAX_PROMPT_PRIOR_INPUTS,
    max_call_chars: int = MAX_PROMPT_CALL_CHARS,
) -> tuple[list[dict], dict]:
    """Select compact round-robin examples for the LLM prompt while keeping full counts in summary."""
    by_stage = dict(Counter(row.get("source_stage", "unknown") for row in prior_inputs))
    if not prior_inputs or limit <= 0:
        return [], {
            "total_prior_inputs": len(prior_inputs),
            "shown_examples": 0,
            "omitted_from_prompt": len(prior_inputs),
            "by_source_stage": by_stage,
        }

    grouped: dict[str, list[dict]] = {}
    for row in prior_inputs:
        call_len = len(str(row.get("args", ""))) + len(str(row.get("kwargs", "")))
        if call_len > max_call_chars:
            continue
        stage = row.get("source_stage", "unknown")
        grouped.setdefault(stage, []).append(row)

    compact: list[dict] = []
    stages = list(grouped.keys())
    cursors = {stage: 0 for stage in stages}
    while len(compact) < limit and stages:
        progressed = False
        for stage in stages:
            cursor = cursors[stage]
            if cursor < len(grouped[stage]):
                row = grouped[stage][cursor]
                cursors[stage] = cursor + 1
                item = {
                    "input_id": row.get("input_id"),
                    "source_stage": stage,
                    "args": row.get("args"),
                    "kwargs": row.get("kwargs"),
                }
                if isinstance(row.get("tools"), list) and len(row["tools"]) > 1:
                    item["tools"] = row["tools"]
                compact.append(item)
                progressed = True
                if len(compact) >= limit:
                    break
        if not progressed:
            break

    summary = {
        "total_prior_inputs": len(prior_inputs),
        "shown_examples": len(compact),
        "omitted_from_prompt": len(prior_inputs) - len(compact),
        "by_source_stage": by_stage,
    }
    return compact, summary
