#!/usr/bin/env python3
"""Huong PATCH-DERIVED CONCEPT — rut guidance tu DIFF vuln<->fixed (patch), theo DIG (arXiv 2606.13037).

Kich ban 'one-day' (patch DA BIET): bench_patch = blind base + goi y tu patch = dieu kien AN TOAN ma ban
va ap dat (chinh la dieu can VI PHAM de kich hoat loi tren ban chua va). So voi concept tree-sitter.

So 3 dieu kien: bench_blind | bench_concept (tree-sitter) | bench_patch (diff-derived).
Chay TU REPO ROOT:  GROQ_API_KEY=... SAMPLES=3 .venv/bin/python patch_concept/run.py
                    GOLD=bench/items/gold_juliet.jsonl PATCH_CACHE=patch_concept/juliet.jsonl ... (Juliet)
"""
import os, sys, re, json

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); BENCH = os.path.join(ROOT, "bench")
sys.path.insert(0, BENCH); sys.path.insert(0, os.path.join(ROOT, "pipeline_v3"))
import common                                                       # noqa: E402
import lab                                                          # noqa: E402
from prompts import build_bench_blind, build_bench_concept, _harness_note  # noqa: E402


def _added(vuln, fixed):
    v = set(l.strip() for l in vuln.split("\n") if l.strip())
    return [l.strip() for l in fixed.split("\n") if l.strip() and l.strip() not in v]


def diff_guidance(item):
    """Suy goi y tu patch: cac dong THEM cua ban va + dieu kien an toan (if) can VI PHAM de trigger."""
    added = _added(item["func_vuln"], item["func_fixed"])
    conds = []
    for a in added:
        m = re.search(r"if\s*\((.+?)\)\s*(?:\{|return|$)", a)
        if m:
            conds.append(m.group(1).strip())
    spec = "Ban va (patch) THEM cac dong:\n" + "\n".join("  + " + a for a in added[:6])
    if conds:
        spec += ("\n-> Dieu kien AN TOAN ban va ap dat: %s. De KICH HOAT loi tren ban CHUA va, truyen input "
                 "sao cho dieu kien do XAY RA (vi pham gia dinh an toan)." % " ; ".join("`%s`" % c for c in conds))
    else:
        spec += ("\n-> Ban va doi thu tu / gan NULL sau free de tranh loi; kich hoat bang cach di DUNG duong dan "
                 "ma ban va da chan (vd dung con tro SAU khi free).")
    return spec


def build_patch(item):
    d = {"func": item["func_vuln"], "lines_concept": item.get("lines_concept") or {}, "family_pred": item.get("family_pred")}
    msgs = common.build_blind_adv(d)                              # base blind (few-shot+CoT, KHONG concept)
    fn = common.focal(item["func_vuln"]) or item["focal"]
    msgs[-1]["content"] += "\n\nGOI Y TU BAN VA (patch-derived):\n" + diff_guidance(item) + _harness_note(item, fn)
    return msgs


CONDS = {"bench_blind": build_bench_blind, "bench_concept": build_bench_concept, "bench_patch": build_patch}
GOLD = os.environ.get("GOLD", os.path.join(BENCH, "items", "gold_juliet.jsonl"))
CACHE = os.environ.get("PATCH_CACHE", os.path.join(HERE, "juliet.jsonl"))


def main():
    items = [json.loads(l) for l in open(GOLD) if l.strip()]
    pos = [it for it in items if it["expect"] != "safe"]
    cache = lab.generate(pos, CONDS, CACHE) if os.environ.get("GROQ_API_KEY") else lab.load_cache(CACHE)
    lab.report(pos, CONDS, cache,
               mcnemar_pairs=[("bench_patch", "bench_concept"), ("bench_patch", "bench_blind")])
    print("\nDoc: patch-derived dung THEM thong tin (patch) so voi concept tree-sitter -> kich ban one-day.")


if __name__ == "__main__":
    main()
