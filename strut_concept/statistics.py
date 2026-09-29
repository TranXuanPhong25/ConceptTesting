"""Paired summaries without optional scientific dependencies."""

from __future__ import annotations

import math
import random
from collections.abc import Callable
from typing import Any


def metric(row: dict[str, Any], kind: str) -> float:
    ev = row["evaluation"]
    if kind == "pass":
        return float(ev["status"] == "passed")
    numerator = ev[f"{kind}_covered"]
    denominator = ev[f"{kind}_total"]
    return numerator / denominator if denominator else 0.0


def paired_bootstrap(differences: list[float], seed: int = 20250926, draws: int = 10000) -> tuple[float, float]:
    if not differences:
        return 0.0, 0.0
    rng = random.Random(seed)
    n = len(differences)
    samples = sorted(sum(differences[rng.randrange(n)] for _ in range(n)) / n for _ in range(draws))
    return samples[int(draws * 0.025)], samples[int(draws * 0.975)]


def exact_sign_p(differences: list[float]) -> float:
    nonzero = [d for d in differences if d != 0]
    n = len(nonzero)
    if not n:
        return 1.0
    k = min(sum(d > 0 for d in nonzero), sum(d < 0 for d in nonzero))
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2**n)
    return min(1.0, 2 * tail)


def compare(rows: list[dict[str, Any]], left: str, right: str, kind: str) -> dict[str, Any]:
    by_key = {(row["subject"], row["arm"]): row for row in rows}
    names = sorted({row["subject"] for row in rows if (row["subject"], left) in by_key and (row["subject"], right) in by_key})
    diffs = [metric(by_key[(name, left)], kind) - metric(by_key[(name, right)], kind) for name in names]
    low, high = paired_bootstrap(diffs)
    return {
        "metric": kind,
        "left": left,
        "right": right,
        "n": len(diffs),
        "mean_difference": sum(diffs) / len(diffs) if diffs else 0.0,
        "bootstrap_95_ci": [low, high],
        "sign_test_p": exact_sign_p(diffs),
        "wins": sum(d > 0 for d in diffs),
        "ties": sum(d == 0 for d in diffs),
        "losses": sum(d < 0 for d in diffs),
    }


def aggregate(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = {}
    for arm in sorted({row["arm"] for row in rows}):
        selected = [row for row in rows if row["arm"] == arm]
        result[arm] = {kind: sum(metric(row, kind) for row in selected) / len(selected) for kind in ("pass", "line", "branch")}
        result[arm]["functions"] = float(len(selected))
        result[arm]["input_tokens"] = float(sum(row.get("usage", {}).get("input_tokens", 0) for row in selected))
        result[arm]["output_tokens"] = float(sum(row.get("usage", {}).get("output_tokens", 0) for row in selected))
    return result
