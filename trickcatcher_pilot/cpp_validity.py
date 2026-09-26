"""Exact input-shape and numeric-constraint checks for exposed pilot problems.

These checks were added after the raw run exposed a malformed p02616 input.
Only problems listed here are covered; other tasks are not declared valid.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from trickcatcher_pilot.paired import _mcnemar


def _integers(stdin: str) -> list[int] | None:
    try:
        return [int(token) for token in stdin.split()]
    except ValueError:
        return None


def valid_input(problem_id: str, stdin: str) -> bool | None:
    tokens = stdin.split()
    if problem_id == "p02775":
        return len(tokens) == 1 and tokens[0].isdigit() and int(tokens[0]) >= 1 and len(tokens[0]) <= 1_000_001
    if problem_id == "p02777":
        if len(tokens) != 5:
            return False
        s, t, a_raw, b_raw, u = tokens
        try:
            a, b = int(a_raw), int(b_raw)
        except ValueError:
            return False
        return (1 <= len(s) <= 10 and 1 <= len(t) <= 10 and s.islower() and t.islower()
                and s.isalpha() and t.isalpha() and s != t and u in {s, t} and 1 <= a <= 10 and 1 <= b <= 10)
    values = _integers(stdin)
    if values is None:
        return False
    if problem_id == "p02550":
        return len(values) == 3 and 1 <= values[0] <= 10**10 and 0 <= values[1] < values[2] <= 10**5
    if problem_id == "p02574":
        if not values:
            return False
        n = values[0]
        return 2 <= n <= 10**6 and len(values) == 1 + n and all(1 <= x <= 10**6 for x in values[1:])
    if problem_id == "p02575":
        if len(values) < 2:
            return False
        h, w = values[:2]
        return (1 <= h <= 200_000 and 1 <= w <= 200_000 and len(values) == 2 + 2 * h
                and all(1 <= values[i] <= values[i + 1] <= w for i in range(2, len(values), 2)))
    if problem_id == "p02580":
        if len(values) < 3:
            return False
        h, w, m = values[:3]
        coords = list(zip(values[3::2], values[4::2]))
        return (1 <= h <= 300_000 and 1 <= w <= 300_000 and 1 <= m <= min(h * w, 300_000)
                and len(values) == 3 + 2 * m and len(set(coords)) == m
                and all(1 <= y <= h and 1 <= x <= w for y, x in coords))
    if problem_id == "p02598":
        if len(values) < 2:
            return False
        n, k = values[:2]
        return 1 <= n <= 200_000 and 0 <= k <= 10**9 and len(values) == 2 + n and all(1 <= x <= 10**9 for x in values[2:])
    if problem_id == "p02599":
        if len(values) < 2:
            return False
        n, q = values[:2]
        if not (1 <= n <= 500_000 and 1 <= q <= 500_000 and len(values) == 2 + n + 2 * q):
            return False
        colors = values[2:2 + n]
        queries = values[2 + n:]
        return all(1 <= c <= n for c in colors) and all(1 <= queries[i] <= queries[i + 1] <= n for i in range(0, len(queries), 2))
    if problem_id == "p02616":
        if len(values) < 2:
            return False
        n, k = values[:2]
        return 1 <= k <= n <= 200_000 and len(values) == 2 + n and all(abs(x) <= 10**9 for x in values[2:])
    if problem_id == "p02641":
        if len(values) < 2:
            return False
        x, n = values[:2]
        excluded = values[2:]
        return (1 <= x <= 100 and 0 <= n <= 100 and len(excluded) == n
                and len(set(excluded)) == n and all(1 <= p <= 100 for p in excluded))
    if problem_id == "p02709":
        if not values:
            return False
        n = values[0]
        return 2 <= n <= 2000 and len(values) == 1 + n and all(1 <= x <= 10**9 for x in values[1:])
    if problem_id == "p02716":
        if not values:
            return False
        n = values[0]
        return 2 <= n <= 200_000 and len(values) == 1 + n and all(abs(x) <= 10**9 for x in values[1:])
    if problem_id == "p02726":
        return len(values) == 3 and 3 <= values[0] <= 2000 and 1 <= values[1] <= values[0] \
            and 1 <= values[2] <= values[0] and values[1] + 1 < values[2]
    if problem_id == "p02732":
        if not values:
            return False
        n = values[0]
        return 3 <= n <= 200_000 and len(values) == 1 + n and all(1 <= x <= n for x in values[1:])
    if problem_id == "p02733":
        if len(tokens) < 3:
            return False
        try:
            h, w, k = map(int, tokens[:3])
        except ValueError:
            return False
        rows = tokens[3:]
        return (1 <= h <= 10 and 1 <= w <= 1000 and 1 <= k <= h * w and len(rows) == h
                and all(len(row) == w and set(row) <= {"0", "1"} for row in rows))
    if problem_id == "p02767":
        if not values:
            return False
        n = values[0]
        return 1 <= n <= 100 and len(values) == 1 + n and all(1 <= x <= 100 for x in values[1:])
    if problem_id == "p02787":
        if len(values) < 2:
            return False
        h, n = values[:2]
        return (1 <= h <= 10_000 and 1 <= n <= 1000 and len(values) == 2 + 2 * n
                and all(1 <= value <= 10_000 for value in values[2:]))
    return None


def compare_validated(a: Path, b: Path) -> dict:
    rows_a = {r["problem_id"]: r for r in map(json.loads, a.read_text().splitlines())}
    rows_b = {r["problem_id"]: r for r in map(json.loads, b.read_text().splitlines())}
    tasks = sorted(rows_a.keys() & rows_b.keys())
    details = []
    for pid in tasks:
        counts = []
        for row in (rows_a[pid], rows_b[pid]):
            hits = [x for x in row["results"] if x["exposed"]]
            valid = [x for x in hits if valid_input(pid, x["input"]) is True]
            invalid = [x for x in hits if valid_input(pid, x["input"]) is False]
            unknown = [x for x in hits if valid_input(pid, x["input"]) is None]
            counts.append({"valid": len(valid), "invalid": len(invalid), "unknown": len(unknown)})
        details.append({"problem_id": pid, "baseline": counts[0], "concept": counts[1]})
    evaluated = [d for d in details if d["baseline"]["valid"] or d["concept"]["valid"]]
    a_only = [d["problem_id"] for d in evaluated if d["baseline"]["valid"] and not d["concept"]["valid"]]
    b_only = [d["problem_id"] for d in evaluated if d["concept"]["valid"] and not d["baseline"]["valid"]]
    return {"paired_tasks": len(tasks), "baseline_valid_exposure": sum(bool(d["baseline"]["valid"]) for d in details),
            "concept_valid_exposure": sum(bool(d["concept"]["valid"]) for d in details),
            "baseline_only": a_only, "concept_only": b_only, "exact_mcnemar_p": _mcnemar(len(a_only), len(b_only)),
            "details": [d for d in details if any(sum(c.values()) for c in (d["baseline"], d["concept"]))]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--concept", required=True)
    args = parser.parse_args()
    print(json.dumps(compare_validated(Path(args.baseline), Path(args.concept)), indent=2))


if __name__ == "__main__":
    main()
