"""Official TestCase-Eval metric logic plus the stricter validity-gated variant.

`validate_outputs`, `official_consensus`, and `official_exposed` port
`stat_task1.py` / `stat_task2.py` (FlowRays/TestCase-Eval @ 45275c6).  The
official checker compares numbers with gmpy2 mpfr at 129 bits and an
absolute tolerance of 1e-12; Decimal with 60 significant digits gives the
same answers for every token that parses in both.

The strict metric (this extension) additionally requires that
  (a) the LLM-written, calibrated validator accepts the input, and
  (b) every accepted submission of the problem ran successfully and all of
      them produced equivalent output (not merely one agreeing pair).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, localcontext
from typing import Any, Iterable

FAILURE_VERDICTS = {"runtime_error", "time_limit_exceeded", "memory_limit_exceeded"}
_TOKEN_SET = {"yes", "no", "true", "false"}
_PRECISION = Decimal("1e-12")


def _number(token: str) -> Decimal | None:
    if "_" in token:  # mpfr rejects digit separators; Decimal would accept them
        return None
    try:
        return Decimal(token)
    except (InvalidOperation, ValueError):
        return None


def validate_outputs(output1: str, output2: str) -> bool:
    lines1, lines2 = output1.strip().split("\n"), output2.strip().split("\n")
    if len(lines1) == len(lines2) and all(a.strip() == b.strip() for a, b in zip(lines1, lines2)):
        return True
    tokens1, tokens2 = output1.strip().split(), output2.strip().split()
    if len(tokens1) != len(tokens2):
        return False
    with localcontext() as ctx:
        ctx.prec = 60
        for tok1, tok2 in zip(tokens1, tokens2):
            num1, num2 = _number(tok1), _number(tok2)
            if num1 is not None and num2 is not None:
                if num1.is_nan() or num2.is_nan():
                    continue  # mpfr: abs(nan - x) > eps is False
                if num1.is_infinite() or num2.is_infinite():
                    if num1 != num2:
                        return False
                    continue
                if abs(num1 - num2) > _PRECISION:
                    return False
                continue
            # official code: mpfr raises ValueError when *either* token is non-numeric
            a = tok1.lower() if tok1.lower() in _TOKEN_SET else tok1
            b = tok2.lower() if tok2.lower() in _TOKEN_SET else tok2
            if a != b:
                return False
    return True


def official_consensus(outputs: list[str]) -> str:
    """Return the official expected output ('' when no consensus)."""
    if len(outputs) == 1:
        return outputs[0]
    for i in range(len(outputs)):
        for j in range(i + 1, len(outputs)):
            if validate_outputs(outputs[i], outputs[j]):
                return outputs[i]
    return ""


def official_exposed(expected: str, verdict: str, output: str) -> bool:
    """stat_task2.exposure for one (target, expected) pair."""
    if expected == "":
        return False
    if verdict == "success_run":
        return not validate_outputs(output, expected)
    return verdict in FAILURE_VERDICTS


def strict_consensus(right_runs: Iterable[dict[str, Any]], minimum: int = 2) -> tuple[str | None, str]:
    """All accepted submissions must succeed and agree. Returns (expected, reason)."""
    runs = list(right_runs)
    supported = [r for r in runs if r.get("result") not in {"unsupported", "compilation_error"}]
    if len(supported) < minimum:
        return None, "too_few_accepted_runs"
    if any(r.get("result") != "success_run" for r in supported):
        return None, "accepted_submission_failed"
    first = supported[0]["output"]
    if not all(validate_outputs(first, r["output"]) for r in supported[1:]):
        return None, "accepted_submissions_disagree"
    return first, "ok"
