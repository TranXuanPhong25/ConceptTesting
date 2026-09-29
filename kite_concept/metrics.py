from __future__ import annotations

import math
import random
from collections import Counter
from typing import Iterable, Mapping


def rbdr(rows: Iterable[Mapping], denominator: int | None = None) -> float:
    values = [bool(row.get("detected", False)) for row in rows]
    total = denominator if denominator is not None else len(values)
    if total < len(values) or total <= 0:
        raise ValueError("denominator must be positive and no smaller than observed rows")
    return sum(values) / total


def project_rbdr(rows: Iterable[Mapping], expected: Mapping[str, int] | None = None) -> dict[str, float]:
    grouped: dict[str, list[Mapping]] = {}
    for row in rows:
        grouped.setdefault(str(row["project"]), []).append(row)
    return {name: rbdr(values, (expected or {}).get(name)) for name, values in sorted(grouped.items())}


def _exact_mcnemar(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(0, min(b, c) + 1)) / (2**n)
    return min(1.0, 2 * tail)


def paired_comparison(
    left: Mapping[str, bool], right: Mapping[str, bool], bootstrap_samples: int = 10000, seed: int = 260711573
) -> dict[str, float | int]:
    task_ids = sorted(set(left) & set(right))
    if not task_ids:
        raise ValueError("arms have no matched tasks")
    pairs = [(int(bool(left[k])), int(bool(right[k]))) for k in task_ids]
    discordant = Counter(pairs)
    observed = sum(a - b for a, b in pairs) / len(pairs)
    rng = random.Random(seed)
    deltas = []
    for _ in range(bootstrap_samples):
        sample = [pairs[rng.randrange(len(pairs))] for _ in pairs]
        deltas.append(sum(a - b for a, b in sample) / len(sample))
    deltas.sort()
    low = deltas[int(0.025 * (len(deltas) - 1))] if deltas else observed
    high = deltas[int(0.975 * (len(deltas) - 1))] if deltas else observed
    return {
        "n": len(pairs), "left_only": discordant[(1, 0)], "right_only": discordant[(0, 1)],
        "delta": observed, "bootstrap_ci_low": low, "bootstrap_ci_high": high,
        "mcnemar_exact_p": _exact_mcnemar(discordant[(1, 0)], discordant[(0, 1)]),
    }

