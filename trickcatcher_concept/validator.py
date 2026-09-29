"""AutoCode-style validator selection (AutoCode #125, CodeHacker #124).

Several LLM-written candidate validators are scored on labelled inputs: known
valid inputs (existing tests the PUT passes; they must be accepted), LLM-written
near-valid illegal inputs and boundary-valid inputs, and mechanical negatives
(truncated or empty copies of valid inputs -- the failure mode of the earlier
pilot, where ``N=200000`` was followed by only 696 numbers). The candidate with
the most correct labels among those that accept every known-valid input wins.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from trickcatcher_concept import sandbox
from trickcatcher_concept.sandbox import PYTHON, _wrap

VALID, INVALID, ERROR = "valid", "invalid", "error"


def parse_validators(response: str) -> list[str]:
    parts = re.split(r"^#+\s*VALIDATOR\s*\d+\s*$", response, flags=re.M | re.I)
    codes = []
    for part in parts[1:] if len(parts) > 1 else parts:
        match = re.search(r"```(?:python|py)?[^\n]*\n(.*?)```", part, flags=re.S)
        code = (match.group(1) if match else part).strip()
        if code and ("sys.stdin" in code or "input(" in code):
            codes.append(code + "\n")
    return codes[:3]


def parse_cases(response: str) -> list[tuple[str, bool]]:
    """Return (input, is_valid) pairs from the CASES_PROMPT layout."""
    text = re.sub(r"^```[^\n]*$", "", response, flags=re.M)
    pieces = re.split(r"^(INVALID|VALID)\s*\d+[^\n]*:[ \t]*$", text, flags=re.M)
    cases = []
    for i in range(1, len(pieces) - 1, 2):
        body = pieces[i + 1].strip("\n")
        if body.strip():
            cases.append((body.strip() + "\n", pieces[i] == "VALID"))
    return cases


def mechanical_negatives(valid_inputs: list[str], limit: int = 6) -> list[str]:
    """Truncations of known-valid inputs; each must be rejected by a strict validator."""
    negatives = [""]
    for text in valid_inputs[:limit]:
        tokens = text.split()
        if len(tokens) >= 2:
            lines = text.rstrip("\n").split("\n")
            # drop the final token (count/format mismatch)
            last = lines[-1].rsplit(None, 1)[0] if len(lines[-1].split()) > 1 else None
            truncated = "\n".join(lines[:-1] + ([last] if last else [])) + "\n"
            negatives.append(truncated)
            # the pilot's failure mode: header kept, most of the body dropped
            if len(lines) >= 2:
                negatives.append(lines[0] + "\n")
    seen, unique = set(), []
    for item in negatives:
        if item not in seen and item not in valid_inputs:
            unique.append(item)
            seen.add(item)
    return unique


def run_validator(path: Path, stdin_text: str, timeout: float = 20.0) -> str:
    try:
        with sandbox.process_slot():
            proc = subprocess.run(_wrap([PYTHON, str(path)], 4096), input=stdin_text.encode(), capture_output=True,
                                  timeout=timeout, start_new_session=True)
    except subprocess.TimeoutExpired:
        return ERROR
    if proc.returncode == 0:
        return VALID
    if proc.returncode == 1:
        return INVALID
    return ERROR  # crash: treated as rejection when filtering, as error when scoring


@dataclass
class Selection:
    index: int | None
    code: str | None
    scores: list[dict] = field(default_factory=list)
    reason: str = ""


def select_validator(candidates: list[str], positives: list[str], labelled: list[tuple[str, bool]],
                     negatives: list[str], workdir: Path) -> Selection:
    workdir.mkdir(parents=True, exist_ok=True)
    scores = []
    for index, code in enumerate(candidates):
        path = workdir / f"candidate_{index}.py"
        path.write_text(code)
        pos_ok = sum(run_validator(path, text) == VALID for text in positives)
        lab_ok = sum(run_validator(path, text) == (VALID if ok else INVALID) for text, ok in labelled)
        neg_ok = sum(run_validator(path, text) == INVALID for text in negatives)
        scores.append({"index": index, "positives_accepted": pos_ok, "positives": len(positives),
                       "labelled_correct": lab_ok, "labelled": len(labelled),
                       "negatives_rejected": neg_ok, "negatives": len(negatives),
                       "sha256": hashlib.sha256(code.encode()).hexdigest()})
    eligible = [s for s in scores if s["positives_accepted"] == s["positives"]]
    if not eligible:
        return Selection(None, None, scores, "no candidate accepts every known-valid input")
    best = max(eligible, key=lambda s: (s["labelled_correct"] + s["negatives_rejected"], -s["index"]))
    return Selection(best["index"], candidates[best["index"]], scores, "selected")
