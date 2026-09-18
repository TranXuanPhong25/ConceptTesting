#!/usr/bin/env python3
"""Paired baseline-vs-concept comparison for TestCase-Eval oracle output.

Exact-binomial (sign test) McNemar, ported from bench/lab.py:mcnemar so all
three benchmarks in this repo (Juliet, Magma, TestCase-Eval) report
significance the same way.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def mcnemar(bin_a: dict[Any, int], bin_b: dict[Any, int]) -> tuple[int, int, float]:
    """Exact (sign/binomial) McNemar over unmatched (discordant) pairs. Returns (b, c, p_two_sided)."""
    ids = set(bin_a) & set(bin_b)
    b = sum(1 for i in ids if bin_a[i] == 1 and bin_b[i] == 0)  # a beats b
    c = sum(1 for i in ids if bin_a[i] == 0 and bin_b[i] == 1)  # b beats a
    n = b + c
    if n == 0:
        return b, c, 1.0
    k = min(b, c)
    p = 2 * sum(math.comb(n, i) for i in range(k + 1)) * (0.5**n)
    return b, c, min(1.0, p)


def load_exposed(path: str) -> dict[int, int]:
    with Path(path).open() as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    return {int(row["submission_id"]): int(bool(row["exposed"])) for row in rows}


def compare(baseline_path: str, concept_path: str) -> dict[str, Any]:
    baseline = load_exposed(baseline_path)
    concept = load_exposed(concept_path)
    paired = sorted(set(baseline) & set(concept))
    b_rate = sum(baseline[i] for i in paired) / max(1, len(paired))
    c_rate = sum(concept[i] for i in paired) / max(1, len(paired))
    b, c, p = mcnemar(concept, baseline)
    return {
        "n_paired": len(paired),
        "baseline_fault_exposure": b_rate,
        "concept_fault_exposure": c_rate,
        "concept_only_exposed": b,
        "baseline_only_exposed": c,
        "mcnemar_p": p,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, help="oracle output for condition=baseline")
    parser.add_argument("--concept", required=True, help="oracle output for condition=concept")
    args = parser.parse_args()
    summary = compare(args.baseline, args.concept)
    sig = "***" if summary["mcnemar_p"] < 0.01 else ("*" if summary["mcnemar_p"] < 0.05 else "ns")
    print(json.dumps(summary, indent=2))
    print(
        f"\nMcNemar concept vs baseline: concept-only={summary['concept_only_exposed']} "
        f"baseline-only={summary['baseline_only_exposed']} p={summary['mcnemar_p']:.4f} ({sig})"
    )


if __name__ == "__main__":
    main()
