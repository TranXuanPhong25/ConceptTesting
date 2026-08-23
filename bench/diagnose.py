#!/usr/bin/env python3
"""Soi tung item: blind vs concept -> compiles/fires tren vuln|fixed + DISCRIM.
Chi ro concept THANG/THUA o dau va vi sao (miss-on-vuln = sensitivity, fire-on-fixed = specificity).
Chay:  .venv/bin/python bench/diagnose.py            (bang)
       .venv/bin/python bench/diagnose.py oob_write_03  (in ca test blind+concept cua 1 id)
"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "pipeline_v3"))
import common
from run_diff import run_diff, extract_code

GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
GOLD = os.environ.get("GOLD", os.path.join(ROOT, "bench", "items", "gold.jsonl"))
CACHE = os.environ.get("BENCH_CACHE", os.path.join(ROOT, "bench", "bench_cache.jsonl"))
CONDS = ["bench_blind", "bench_concept"]
cache = {}
for l in open(CACHE):
    try:
        o = json.loads(l); cache[o["key"]] = o["target"]
    except Exception:
        pass
def key(it, c): return common.cache_key(GROQ_MODEL, c, it["id"] + "::" + it["func_vuln"])
items = [json.loads(l) for l in open(GOLD)]

if len(sys.argv) > 1:
    it = next(d for d in items if d["id"] == sys.argv[1])
    for c in CONDS:
        print("=" * 70, "\n", c, "| family_pred:", it.get("family_pred"), "\n", "=" * 70)
        print(extract_code(cache.get(key(it, c), "")) or "[MISSING]")
    sys.exit()

print("%-14s %-11s %-11s  %-13s %-13s  concept?" % ("id", "gold", "pred", "blind(v/f)", "concept(v/f)"))
def vf(r): return "c%df%d|c%df%d" % (r["compiles_vuln"], r["fires_vuln"], r["compiles_fixed"], r["fires_fixed"])
def disc(r): return r["compiles_vuln"] and r["compiles_fixed"] and r["fires_vuln"] and not r["fires_fixed"]
for it in items:
    if it["expect"] == "safe":
        continue
    rb = run_diff(cache.get(key(it, "bench_blind"), ""), it)
    rc = run_diff(cache.get(key(it, "bench_concept"), ""), it)
    db, dc = disc(rb), disc(rc)
    tag = "=" if db == dc else ("CONCEPT+" if dc else "CONCEPT-")
    print("%-14s %-11s %-11s  %-13s %-13s  %s" % (
        it["id"], it["family"], str(it.get("family_pred")), vf(rb), vf(rc), tag))
