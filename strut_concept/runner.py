"""Resume-safe experiment orchestration."""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from .benchmark import SUBJECTS, TUNING_COUNT, Subject, default_picolibc_root, prepare_source
from .evaluator import evaluate
from .extractor import build_context, build_seed
from .prompts import SYSTEM, prompt_for
from .translator import clean_c_output, parse_cases, translate_cases


ARMS = ("direct", "strut", "extended")
PROMPT_VERSION = "strut-concept-v1"


def _append(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _load(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return rows
    for raw in path.read_text().splitlines():
        try:
            row = json.loads(raw)
            rows[row["key"]] = row
        except (json.JSONDecodeError, KeyError):
            continue
    return rows


def _response_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(block if isinstance(block, str) else block.get("text", "") for block in content if isinstance(block, (str, dict)))
    return str(content)


def _usage(response: Any) -> dict[str, int]:
    usage = getattr(response, "usage_metadata", None) or getattr(response, "response_metadata", {}).get("usage_metadata", {}) or {}
    return {
        "input_tokens": int(usage.get("input_tokens", usage.get("prompt_token_count", 0)) or 0),
        "output_tokens": int(usage.get("output_tokens", usage.get("candidates_token_count", 0)) or 0),
        "total_tokens": int(usage.get("total_tokens", usage.get("total_token_count", 0)) or 0),
    }


def _invoke(llm: Any, prompt: str, retries: int = 4) -> tuple[str, dict[str, int]]:
    from langchain_core.messages import HumanMessage, SystemMessage

    error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            response = llm.invoke([SystemMessage(content=SYSTEM), HumanMessage(content=prompt)])
            return _response_text(response.content), _usage(response)
        except Exception as exc:
            error = exc
            if attempt < retries:
                time.sleep(min(60, 4 * 2**attempt))
    raise RuntimeError(f"LLM invocation failed after {retries + 1} attempts: {error}") from error


def run(
    output_dir: Path,
    phase: str,
    picolibc_root: Path | None = None,
    llm: Any | None = None,
    arms: tuple[str, ...] = ARMS,
) -> list[dict[str, Any]]:
    if phase not in {"tune", "full"}:
        raise ValueError("phase must be tune or full")
    if llm is None:
        from magma.llm_client import make_llm
        llm = make_llm(temperature=0.0, timeout=360, max_retries=0, max_tokens=2400)
    if llm is None:
        raise RuntimeError("Vertex LLM is not configured")
    root = picolibc_root or default_picolibc_root()
    count = TUNING_COUNT if phase == "tune" else len(SUBJECTS)
    journal = output_dir / "results.jsonl"
    cached = _load(journal)
    for subject in SUBJECTS[:count]:
        prepared = output_dir / "prepared" / f"{subject.name}.c"
        source = prepare_source(subject, root, prepared)
        context = build_context(source, subject)
        for arm in arms:
            key_material = f"{PROMPT_VERSION}:{subject.name}:{arm}"
            key = hashlib.sha256(key_material.encode()).hexdigest()[:24]
            if key in cached and cached[key].get("evaluation", {}).get("status") != "generation_error":
                continue
            seed = build_seed(context, extended=arm == "extended")
            prompt = prompt_for(arm, context, seed)
            started = time.time()
            try:
                raw, usage = _invoke(llm, prompt)
                harness = clean_c_output(raw) if arm == "direct" else translate_cases(subject, parse_cases(raw))
                evaluation = evaluate(subject, source, harness, output_dir / "build" / subject.name / arm)
                error = ""
            except Exception as exc:
                raw, usage, harness = "", {}, ""
                evaluation = None
                error = f"{type(exc).__name__}: {exc}"
            artifact = output_dir / "generated" / subject.name
            artifact.mkdir(parents=True, exist_ok=True)
            (artifact / f"{arm}.txt").write_text(raw)
            if harness:
                (artifact / f"{arm}.c").write_text(harness)
            row = {
                "key": key, "prompt_version": PROMPT_VERSION, "phase_first_seen": phase,
                "subject": subject.name, "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
                "arm": arm, "usage": usage,
                "elapsed_seconds": time.time() - started,
                "evaluation": evaluation.to_dict() if evaluation else {"status": "generation_error", "compile_returncode": -1, "run_returncode": None, "line_covered": 0, "line_total": 0, "branch_covered": 0, "branch_total": 0, "error": error},
            }
            _append(journal, row)
            cached[key] = row
            print(f"{phase} {subject.name} {arm}: {row['evaluation']['status']}", flush=True)
    return list(_load(journal).values())
