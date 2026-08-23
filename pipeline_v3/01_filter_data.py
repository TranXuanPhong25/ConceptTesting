#!/usr/bin/env python3
"""01 - Loc VD dataset.

Giu `func`, `target`, `cwe` (chuan hoa) + `project`, `commit_id`, `idx`, `split`
(3 truong sau CAN de split chong leakage theo project, du user chi yeu cau 3 truong dau).
Giu CA target 0 va 1 (co doi chung am). Lam viec CPU, khong nhan.

Chay:
    python pipeline_v3/01_filter_data.py --n 500 --balance
Ra: data/work/filtered.jsonl
"""
import os, sys, json, random, argparse, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common import norm_cwe

SRC = {"train": "data/VD/train_concept.jsonl",
       "valid": "data/VD/valid_concept.jsonl",
       "test":  "data/VD/teest_concept.jsonl"}   # ten file thuc la 'teest'
OUT = "data/work/filtered.jsonl"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=0, help="tong so mau giu (0 = tat ca)")
    ap.add_argument("--balance", action="store_true", help="can bang so luong target 0/1")
    ap.add_argument("--min_lines", type=int, default=6)
    ap.add_argument("--max_lines", type=int, default=28)
    ap.add_argument("--splits", default="train,valid,test", help="split lay tu VD")
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()

    want = set(a.splits.split(","))
    rows = []
    for split, path in SRC.items():
        if split not in want:
            continue
        if not os.path.exists(path):
            print("[warn] thieu", path); continue
        for line in open(path):
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            if "func" not in d or "target" not in d:
                continue
            nl = len(d["func"].splitlines())
            if not (a.min_lines <= nl <= a.max_lines):
                continue
            rows.append({
                "func": d["func"], "target": int(d["target"]), "cwe": norm_cwe(d.get("cwe")),
                "project": d.get("project", "?"), "commit_id": d.get("commit_id"),
                "idx": d.get("idx"), "split": split,
            })

    rng = random.Random(a.seed); rng.shuffle(rows)
    if a.balance:
        pos = [r for r in rows if r["target"] == 1]
        neg = [r for r in rows if r["target"] == 0]
        k = min(len(pos), len(neg))
        if a.n:
            k = min(k, a.n // 2)
        rows = pos[:k] + neg[:k]; rng.shuffle(rows)
    elif a.n:
        rows = rows[:a.n]

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print("Ghi %d -> %s" % (len(rows), OUT),
          "| target:", dict(collections.Counter(r["target"] for r in rows)),
          "| split:", dict(collections.Counter(r["split"] for r in rows)))


if __name__ == "__main__":
    main()
