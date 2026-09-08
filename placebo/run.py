#!/usr/bin/env python3
"""Huong PLACEBO — chung minh NOI DUNG concept moi la thu giup (khong phai prompt dai).

concept_shuffle = concept nhung XAO tag rui ro giua cac dong + DAO family (concept-shaped, SAI noi dung).
Neu loi the concept la THAT -> DISCRIM cua concept_shuffle phai TUT ve ~ blind.
Kiem dinh McNemar: concept vs concept_shuffle (va concept vs blind) tren ket qua discriminate per-item.

So 3 dieu kien: bench_blind | bench_concept | concept_shuffle.
Chay TU REPO ROOT:  GROQ_API_KEY=... SAMPLES=3 .venv/bin/python placebo/run.py
                    GOLD=bench/items/gold_juliet.jsonl PLACEBO_CACHE=placebo/juliet.jsonl ... (Juliet)
"""
import os, sys, json, hashlib, random

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); BENCH = os.path.join(ROOT, "bench")
sys.path.insert(0, BENCH); sys.path.insert(0, os.path.join(ROOT, "pipeline_v3"))
import common                                                       # noqa: E402
import lab                                                          # noqa: E402
from prompts import build_bench_blind, build_bench_concept, _harness_note  # noqa: E402

FAMS = ["oob_write", "oob_read", "oob", "uaf", "double_free", "null_deref"]


def build_shuffle(item):
    """Placebo: xao vector concept giua cac dong + gan family SAI (deterministic theo id)."""
    rnd = random.Random(int(hashlib.sha1(("shuf::" + item["id"]).encode()).hexdigest(), 16) % (2 ** 32))
    lc = item.get("lines_concept") or {}
    keys = list(lc.keys()); vals = [list(v) for v in lc.values()]
    rnd.shuffle(vals)
    d = {"func": item["func_vuln"], "lines_concept": dict(zip(keys, vals))}
    real = item.get("family_pred"); wrong = [f for f in FAMS if f != real] or FAMS
    d["family_pred"] = rnd.choice(wrong)
    msgs = common.build_concept(d)
    fn = common.focal(item["func_vuln"]) or item["focal"]
    msgs[-1]["content"] += _harness_note(item, fn)
    return msgs


CONDS = {"bench_blind": build_bench_blind, "bench_concept": build_bench_concept, "concept_shuffle": build_shuffle}
GOLD = os.environ.get("GOLD", os.path.join(BENCH, "items", "gold.jsonl"))
CACHE = os.environ.get("PLACEBO_CACHE", os.path.join(HERE, "placebo_cache.jsonl"))


def main():
    items = [json.loads(l) for l in open(GOLD) if l.strip()]
    pos = [it for it in items if it["expect"] != "safe"]
    cache = lab.generate(pos, CONDS, CACHE) if os.environ.get("GROQ_API_KEY") else lab.load_cache(CACHE)
    lab.report(pos, CONDS, cache,
               mcnemar_pairs=[("bench_concept", "concept_shuffle"), ("bench_concept", "bench_blind")])
    print("\nDoc: concept > concept_shuffle (McNemar co y nghia) => loi the den tu NOI DUNG concept, khong phai prompt dai.")


if __name__ == "__main__":
    main()
