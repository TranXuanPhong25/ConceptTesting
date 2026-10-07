#!/usr/bin/env python3
"""Build the PLACEBO training file: same functions/targets, concept labels deranged ACROSS functions
of the SAME line count (pre-registered scheme, see README.md).

  python make_placebo.py <train_concept.jsonl> <train_concept_placebo.jsonl>   # writes + prints checks
  python make_placebo.py --selftest                                            # tiny synthetic check

Scheme (seed 20261007):
  * stratum = raw line count n = len(func.split("\n")) (== len(lines_concept) for all 23,184 rows).
  * stratum size >= 2: uniform random derangement; function i gets the whole n x 8 `lines_concept`
    matrix of another function j != i with the same n.
  * singleton strata: donor = uniform random function with strictly more lines; take its first n lines.
    The single longest function (no longer donor exists) gets a within-function line permutation.
  * `concepts` (function-level) recomputed as OR over the new line labels (true data satisfies this).
"""
import sys, json, hashlib
from collections import defaultdict
import numpy as np

SEED = 20261007


def derangement(n, rng):
    while True:                                   # rejection: P(accept) -> 1/e, cheap for our sizes
        p = rng.permutation(n)
        if not (p == np.arange(n)).any():
            return p


def make(rows, seed=SEED):
    """-> (new_lines_concept list, donor index list; -1 = within-function permutation)."""
    rng = np.random.default_rng(seed)
    n = [len(r["func"].split("\n")) for r in rows]
    assert all(len(r["lines_concept"]) == k for r, k in zip(rows, n)), "line count != len(lines_concept)"
    strata = defaultdict(list)
    for i, k in enumerate(n):
        strata[k].append(i)
    donor = [None] * len(rows)
    for k in sorted(strata):
        ids = strata[k]
        if len(ids) >= 2:
            for a, b in zip(ids, derangement(len(ids), rng)):
                donor[a] = ids[b]
    order = sorted(range(len(rows)), key=lambda i: n[i])
    for k in sorted(strata):
        ids = strata[k]
        if len(ids) == 1:
            longer = [j for j in order if n[j] > k]
            donor[ids[0]] = int(rng.choice(longer)) if longer else -1
    new = []
    for i, r in enumerate(rows):
        k = n[i]
        if donor[i] == -1:
            perm = rng.permutation(k)
            new.append({str(t): rows[i]["lines_concept"][str(int(perm[t]))] for t in range(k)})
        else:
            src = rows[donor[i]]["lines_concept"]
            new.append({str(t): src[str(t)] for t in range(k)})
    return new, donor


def checks(rows, new, donor):
    n = len(rows)
    C = len(rows[0]["lines_concept"]["0"])
    same = sum(rows[i]["lines_concept"] == new[i] for i in range(n))
    T = np.array([v for r in rows for v in r["lines_concept"].values()])
    P = np.array([v for d in new for v in d.values()])
    y = np.array([r["target"] for r in rows])
    Ft = np.array([[int(any(v[j] for v in r["lines_concept"].values())) for j in range(C)] for r in rows])
    Fp = np.array([[int(any(v[j] for v in d.values())) for j in range(C)] for d in new])
    print("functions=%d  self-donor=%d  within-perm=%d  singleton-donor=%d" % (
        n, sum(d == i for i, d in enumerate(donor)), sum(d == -1 for d in donor),
        sum(d not in (None, -1) and len(rows[d]["func"].split("\n")) != len(rows[i]["func"].split("\n"))
            for i, d in enumerate(donor))))
    print("placebo matrix identical to true matrix by chance: %d (%.2f%%)" % (same, 100 * same / n))
    print("line-level positive rate  true   :", T.mean(0).round(4))
    print("line-level positive rate  placebo:", P.mean(0).round(4))
    print("P(c|vul)-P(c|ben) true   :", (Ft[y == 1].mean(0) - Ft[y == 0].mean(0)).round(3))
    print("P(c|vul)-P(c|ben) placebo:", (Fp[y == 1].mean(0) - Fp[y == 0].mean(0)).round(3))


def selftest():
    rng = np.random.default_rng(0)
    rows = []
    for i, k in enumerate([3, 3, 3, 5, 5, 7, 9]):        # 7 and 9 are singletons
        rows.append({"idx": i, "target": i % 2, "func": "\n".join("x" for _ in range(k)),
                     "lines_concept": {str(t): rng.integers(0, 2, 8).tolist() for t in range(k)}})
    new, donor = make(rows, seed=1)
    for i, d in enumerate(donor):
        assert d != i
        assert len(new[i]) == len(rows[i]["lines_concept"])
        if d not in (-1, None):
            assert len(rows[d]["lines_concept"]) >= len(new[i])
    assert donor[5] == 6 and donor[6] == -1                # 7-line singleton -> 9-line donor; longest -> self-perm
    for k in (3, 5):                                       # multiset preserved inside each stratum
        ids = [i for i, r in enumerate(rows) if len(r["lines_concept"]) == k]
        a = sorted(json.dumps(rows[i]["lines_concept"], sort_keys=True) for i in ids)
        b = sorted(json.dumps(new[i], sort_keys=True) for i in ids)
        assert a == b
    print("selftest ok")


def main():
    if sys.argv[1:] == ["--selftest"]:
        return selftest()
    src, dst = sys.argv[1:3]
    rows = [json.loads(l) for l in open(src)]
    new, donor = make(rows)
    with open(dst, "w") as f:
        for r, lc in zip(rows, new):
            r = dict(r, lines_concept=lc,
                     concepts=[int(any(v[j] for v in lc.values())) for j in range(len(lc["0"]))])
            f.write(json.dumps(r) + "\n")
    checks(rows, new, donor)
    print("sha256(%s) = %s" % (dst, hashlib.sha256(open(dst, "rb").read()).hexdigest()))


if __name__ == "__main__":
    main()
