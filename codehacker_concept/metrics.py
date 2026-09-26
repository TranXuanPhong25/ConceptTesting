"""Metrics from CodeHacker Appendix E plus paired statistics.

HSR  = |{s in S_target : some generated x hacks s}| / |S_target|
TPR  = fraction of originally-correct submissions accepted by the new suite
TNR  = fraction of originally-incorrect submissions rejected by the new suite
VPR  = fraction of test inputs accepted by the refined validator
"""

from __future__ import annotations

import math
import random
from typing import Iterable, Sequence


def rate(hits: Iterable[bool]) -> float:
    values = list(hits)
    return sum(values) / len(values) if values else float("nan")


def hsr(successes: Sequence[bool]) -> float:
    return rate(successes)


def tpr(correct_accepted: Sequence[bool]) -> float:
    return rate(correct_accepted)


def tnr(incorrect_rejected: Sequence[bool]) -> float:
    return rate(incorrect_rejected)


def vpr(valid_flags: Sequence[bool]) -> float:
    return rate(valid_flags)


def mcnemar_exact(a_only: int, b_only: int) -> float:
    """Two-sided exact McNemar p-value on discordant pairs."""
    n = a_only + b_only
    if n == 0:
        return 1.0
    k = min(a_only, b_only)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2**n)


def paired_compare(a: Sequence[bool], b: Sequence[bool], n_boot: int = 10000, seed: int = 0) -> dict:
    if len(a) != len(b):
        raise ValueError("paired sequences must have equal length")
    n = len(a)
    a_only = sum(1 for x, y in zip(a, b) if x and not y)
    b_only = sum(1 for x, y in zip(a, b) if y and not x)
    diffs = [int(y) - int(x) for x, y in zip(a, b)]
    rng = random.Random(seed)
    boots = []
    for _ in range(n_boot if n else 0):
        sample = [diffs[rng.randrange(n)] for _ in range(n)]
        boots.append(sum(sample) / n)
    boots.sort()
    ci = (boots[int(0.025 * len(boots))], boots[int(0.975 * len(boots)) - 1]) if boots else (float("nan"), float("nan"))
    return {
        "n": n,
        "rate_a": rate(a),
        "rate_b": rate(b),
        "diff_b_minus_a": (sum(diffs) / n) if n else float("nan"),
        "ci95": ci,
        "a_only": a_only,
        "b_only": b_only,
        "mcnemar_p": mcnemar_exact(a_only, b_only),
    }


def wilson_ci(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (centre - half, centre + half)
