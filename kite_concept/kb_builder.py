"""Best-effort mechanism knowledge-base construction from cached historical-bug sources.

The paper reviews 1,325 mechanisms across Defects4J/Bears/Bugs.jar/GitBug-Java/GHRB manually. That
manual review cannot be reproduced. This module instead builds a smaller, real, LLM-reviewed
mechanism set from the one cached source that ships full unified diffs inline (Bears,
``~/.local/kite/kbsrc/bears/bears-bugs.json``, 251 bugs), so no additional repository cloning is
required. Records whose repository matches any of the five held-out benchmark projects
(Cli/Compress/Csv/JacksonDatabind/Jsoup) are rejected before any mechanism is derived from them,
independent of the later ``knowledge.build_knowledge_base`` de-leakage check, which also runs on
this module's output.

This is a documented scope-reduction: GHRB and GitBug-Java are cached here only as commit/PR
metadata (no inline diff text), so extracting their mechanisms would require cloning and building
each of their ~90 upstream repositories; Bugs.jar has no cached source at all. Both are left for a
follow-up run.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

from .extraction import mechanism_extraction_prompt, parse_mechanism
from .structure import extract_unit_structures

BENCHMARK_MARKERS = (
    "commons-cli", "apache/commons-cli",
    "commons-compress", "apache/commons-compress",
    "commons-csv", "apache/commons-csv",
    "jackson-databind", "fasterxml/jackson-databind", "fasterxml-jackson-databind",
    "jsoup/jsoup", "jhy/jsoup",
)


def is_benchmark_repo(name: str) -> bool:
    lowered = name.lower()
    return any(marker in lowered for marker in BENCHMARK_MARKERS)


_FILE_RE = re.compile(r"^diff --git a/(.*) b/(.*)$")


def diff_file_pairs(bug_id: str, repo_name: str, diff_text: str) -> list[dict[str, str]]:
    """Reconstruct one (fixed, buggy) local-code pair per touched ``.java`` file in one diff.

    Hunks are concatenated per file (coarser than method-level localization, but sufficient input
    for mechanism abstraction, which only needs locally-aligned correct/buggy code).
    """
    pairs: list[dict[str, str]] = []
    current_file: str | None = None
    fixed_lines: list[str] = []
    buggy_lines: list[str] = []

    def flush() -> None:
        if current_file and current_file.endswith(".java"):
            fixed = "\n".join(fixed_lines).strip()
            buggy = "\n".join(buggy_lines).strip()
            if fixed and buggy and fixed != buggy:
                pairs.append({"bug_id": bug_id, "repo": repo_name, "file": current_file, "fixed": fixed, "buggy": buggy})

    for line in diff_text.splitlines():
        match = _FILE_RE.match(line)
        if match:
            flush()
            current_file = match.group(2)
            fixed_lines, buggy_lines = [], []
            continue
        if line.startswith("@@"):
            continue
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line[:1] == "+":
            fixed_lines.append(line[1:])
        elif line[:1] == "-":
            buggy_lines.append(line[1:])
        elif line[:1] == " ":
            fixed_lines.append(line[1:])
            buggy_lines.append(line[1:])
    flush()
    return pairs


def bears_candidates(bears_json_path: Path) -> Iterable[dict[str, str]]:
    data = json.loads(bears_json_path.read_text(encoding="utf-8"))
    for bug in data:
        repo = bug.get("repository") or {}
        repo_name = str(repo.get("name") or repo.get("url") or "")
        if is_benchmark_repo(repo_name):
            continue
        bug_id = str(bug.get("bugId") or bug.get("bugName") or "bears-?")
        diff_text = bug.get("diff") or ""
        if not isinstance(diff_text, str) or not diff_text.strip():
            continue
        for pair in diff_file_pairs(bug_id, repo_name, diff_text):
            if len(pair["fixed"]) < 2000 and len(pair["buggy"]) < 2000:  # keep prompts small
                yield pair


def extract_mechanism(
    llm: Any, response_text_fn, candidate: dict[str, str], mechanism_id: str, max_retries: int = 5
) -> dict[str, Any] | None:
    import time as _time
    import random as _random

    prompt = mechanism_extraction_prompt(candidate["fixed"], candidate["buggy"], f"file: {candidate['file']}")
    response = None
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            response = llm.invoke(prompt)
            break
        except Exception as exc:  # network/model error; retry transient quota errors
            last_exc = exc
            transient = "ResourceExhausted" in type(exc).__name__ or "429" in str(exc) or "Resource exhausted" in str(exc)
            if not transient or attempt == max_retries - 1:
                return {"error": f"llm_error:{type(exc).__name__}:{exc}"[:300]}
            _time.sleep((2 ** attempt) + _random.uniform(0, 1))
    if response is None:
        return {"error": f"llm_error:{type(last_exc).__name__ if last_exc else 'unknown'}:{last_exc}"[:300]}
    text = response_text_fn(response)
    usage = getattr(response, "usage_metadata", None) or {}
    try:
        record = parse_mechanism(
            text,
            mechanism_id=mechanism_id,
            evidence_ids=(candidate["bug_id"],),
            structures=tuple(extract_unit_structures(candidate["fixed"])),
            source_project=candidate["repo"],
        )
    except ValueError as exc:
        return {"error": f"parse_error:{exc}"[:300], "usage": usage}
    row = record.to_dict()
    row["structures"] = [
        {"anchors": list(s.anchors), "relations": list(s.relations), "coarse_key": list(s.coarse_key), "fingerprint": s.fingerprint}
        for s in record.structures
    ]
    row["usage"] = usage
    return row
