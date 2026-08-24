#!/usr/bin/env python3
"""Cham diem EXECUTED vi-phan: concept vs blind tren gold set.

Voi moi item x cond: run_diff(test) link test voi CA func_vuln lan func_fixed.
  TP           = compile vuln & no tren vuln            (bat bug that)
  FP           = compile fixed & no tren fixed          (bao dong gia)
  DISCRIM      = compile ca 2 & no vuln & KHONG no fixed (dinh vi DUNG bug)
  neg control  = sach ca 2 ban (do specificity)

Chay:  .venv/bin/python bench/score.py     (sau khi bench/gen.py da sinh cache)
Env:   GROQ_MODEL (khop luc gen) | BENCH_CACHE
"""
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "pipeline_v3"))
from run_diff import run_diff, CXX  # noqa: E402
from prompts import prompt_key      # noqa: E402

GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
GOLD  = os.environ.get("GOLD", os.path.join(ROOT, "bench", "items", "gold.jsonl"))
CACHE = os.environ.get("BENCH_CACHE", os.path.join(ROOT, "bench", "bench_cache.jsonl"))
SAMPLES = int(os.environ.get("SAMPLES", "1"))
CONDS = ["bench_blind", "bench_concept"]


def _key(item, cond):
    return prompt_key(GROQ_MODEL, cond, item)


def _samples(item, cond, cache):
    base = _key(item, cond)
    return [cache[base + "#%d" % s] for s in range(SAMPLES) if base + "#%d" % s in cache]


def load_cache():
    c = {}
    if os.path.exists(CACHE):
        for l in open(CACHE):
            try:
                o = json.loads(l); c[o["key"]] = o["target"]
            except Exception:
                pass
    return c


def main():
    if not CXX:
        raise SystemExit("Khong co compiler.")
    cache = load_cache()
    if not cache:
        raise SystemExit("Cache rong (%s). Chay bench/gen.py truoc." % CACHE)
    items = [json.loads(l) for l in open(GOLD) if l.strip()]
    pos = [it for it in items if it["expect"] != "safe"]
    neg = [it for it in items if it["expect"] == "safe"]

    agg = {c: {"n": 0, "has": 0, "cv": 0, "tp": 0, "fp": 0, "disc": 0} for c in CONDS}
    fam = {c: collections.defaultdict(lambda: [0, 0]) for c in CONDS}  # family -> [disc, n]
    negagg = {c: {"n": 0, "clean": 0, "has": 0} for c in CONDS}

    for it in pos:
        for c in CONDS:
            a = agg[c]; a["n"] += 1
            smp = _samples(it, c, cache)         # K mau; metric = ty le mau dat -> giam nhieu
            if not smp:
                continue
            a["has"] += 1
            rs = [run_diff(raw, it) for raw in smp]; k = len(rs)
            cv = sum(r["compiles_vuln"] for r in rs) / k
            tp = sum(1 for r in rs if r["compiles_vuln"] and r["fires_vuln"]) / k
            fp = sum(1 for r in rs if r["compiles_fixed"] and r["fires_fixed"]) / k
            disc = sum(1 for r in rs if r["compiles_vuln"] and r["compiles_fixed"]
                       and r["fires_vuln"] and not r["fires_fixed"]) / k
            a["cv"] += cv; a["tp"] += tp; a["fp"] += fp; a["disc"] += disc
            fam[c][it["family"]][0] += disc; fam[c][it["family"]][1] += 1

    for it in neg:
        for c in CONDS:
            na = negagg[c]; na["n"] += 1
            smp = _samples(it, c, cache)
            if not smp:
                continue
            na["has"] += 1
            rs = [run_diff(raw, it) for raw in smp]
            na["clean"] += sum(1 for r in rs if not r["fires_vuln"] and not r["fires_fixed"]) / len(rs)

    print("model:", GROQ_MODEL, "| pos:", len(pos), "| neg:", len(neg), "| cache:", len(cache), "\n")
    print("%-14s %8s %10s %9s %11s %9s"
          % ("cond", "have", "compile_v", "FIRES_v", "clean_fix", "DISCRIM"))
    for c in CONDS:
        a = agg[c]; n = a["n"] or 1
        print("%-14s %6d/%-2d %9.0f%% %8.0f%% %10.0f%% %8.0f%%"
              % (c, a["has"], a["n"], 100 * a["cv"] / n, 100 * a["tp"] / n,
                 100 * (a["n"] - a["fp"]) / n, 100 * a["disc"] / n))

    print("\n=== DISCRIM theo ho (disc/n, trung binh qua %d mau) — concept vs blind ===" % SAMPLES)
    print("  %-13s %10s %10s" % ("family", "blind", "concept"))
    for f in sorted({x for c in CONDS for x in fam[c]}):
        b = fam["bench_blind"][f]; co = fam["bench_concept"][f]
        print("  %-13s %7.1f/%-2d %7.1f/%-2d" % (f, b[0], b[1], co[0], co[1]))

    print("\n=== negative controls (sach ca 2 = tot) ===")
    for c in CONDS:
        na = negagg[c]
        print("  %-14s clean %.1f/%d" % (c, na["clean"], na["n"]))

    print("\nDISCRIM = compile ca 2 & no tren vuln & KHONG no tren fixed (test dinh vi DUNG bug).")
    print("So sanh chinh: bench_concept vs bench_blind o cot DISCRIM + per-family.")


if __name__ == "__main__":
    main()
