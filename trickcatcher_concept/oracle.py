"""Diversity-driven differential oracle and the paper's recall/precision/F1.

Ports ``Analysis/utils.py`` (``get_trigger_df`` + ``compute_res_df`` with
method_type='tc') from the pinned TrickCatcher artifact:

* Only non-error outputs are compared (the artifact drops TIME_OUT, RUN_ERROR
  and empty outputs before building triggers).
* For a combination of k variants, an input triggers when some variant in the
  combination disagrees with the PUT. The candidate oracles are the disagreeing
  outputs with the largest number of supporting variants in that combination
  (ties keep every tied output, as the artifact does); each (input, oracle) is a
  reported test case.
* Per PUT and combination, the TP fraction among reported test cases is added to
  TP and its complement to FP. TP_rate = TP / C(n, k) where n is the number of
  kept variants with at least one successful output (k is capped at n).
* recall = sum(TP_rate) / #PUTs; precision = mean over PUTs with any report of
  TP / (TP + FP); F1 from these two (Appendix B / RQ1 notebook).
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from typing import Callable, Iterable

OK = "OK"


@dataclass
class TestCase:
    input_id: str
    oracle: str
    supporters: tuple[str, ...]


def eligible_variants(outputs: dict[str, dict[str, list[str]]]) -> list[str]:
    return sorted(name for name, table in outputs.items()
                  if name != "put" and any(status == OK for status, _ in table.values()))


def test_cases_for(outputs: dict[str, dict[str, list[str]]], combo: Iterable[str],
                   allowed: Callable[[str], bool] | None = None) -> list[TestCase]:
    put = outputs["put"]
    cases: list[TestCase] = []
    combo = tuple(combo)
    for input_id, (status, put_out) in put.items():
        if status != OK or (allowed is not None and not allowed(input_id)):
            continue
        votes: dict[str, list[str]] = {}
        for name in combo:
            entry = outputs[name].get(input_id)
            if entry and entry[0] == OK and entry[1] != put_out:
                votes.setdefault(entry[1], []).append(name)
        if not votes:
            continue
        top = max(len(v) for v in votes.values())
        for out, names in sorted(votes.items()):
            if len(names) == top:
                cases.append(TestCase(input_id, out, tuple(names)))
    return cases


@dataclass
class PutScore:
    n_variants: int
    k: int
    total: int
    tp: float
    fp: float
    fp_bad_input: float
    reported: bool

    @property
    def tp_rate(self) -> float:
        return self.tp / self.total if self.total else 0.0

    @property
    def precision(self) -> float | None:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) > 0 else None


def score_put(outputs: dict[str, dict[str, list[str]]], k: int, is_true: Callable[[TestCase], bool],
              input_valid: Callable[[str], bool], allowed: Callable[[str], bool] | None = None,
              max_combos: int = 300) -> PutScore:
    variants = eligible_variants(outputs)
    n = len(variants)
    if n == 0:
        return PutScore(0, 0, 0, 0.0, 0.0, 0.0, False)
    kk = min(k, n)
    total = math.comb(n, kk)
    combos = list(combinations(variants, kk))
    if len(combos) > max_combos:  # never hit for n <= 10, kept as a guard
        combos = combos[:max_combos]
        total = len(combos)
    tp = fp = bad = 0.0
    for combo in combos:
        cases = test_cases_for(outputs, combo, allowed)
        if not cases:
            continue
        good = sum(is_true(c) for c in cases)
        tp += good / len(cases)
        fp += 1 - good / len(cases)
        bad += sum(not input_valid(c.input_id) for c in cases) / len(cases)
    return PutScore(n, kk, total, tp, fp, bad, (tp + fp) > 0)


def aggregate(scores: list[PutScore], n_puts: int) -> dict[str, float]:
    recall = sum(s.tp_rate for s in scores) / n_puts if n_puts else 0.0
    precisions = [s.precision for s in scores if s.precision is not None]
    precision = sum(precisions) / len(precisions) if precisions else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"recall": recall, "precision": precision, "f1": f1, "n_puts": n_puts,
            "n_reported": len(precisions), "tp_sum": sum(s.tp_rate for s in scores)}


def majority(values: Iterable[str]) -> str | None:
    counts = Counter(values)
    return counts.most_common(1)[0][0] if counts else None
