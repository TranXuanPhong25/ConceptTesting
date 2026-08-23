#!/usr/bin/env python3
"""Build items/gold.jsonl tu authored.py: TU-KIEM oracle vi-phan + dien concept.

  1) Voi moi case chay run_diff(ref_test) — chung minh oracle DUNG truoc khi co LLM:
       expect=fires_on_vuln -> compile ca 2 & fires_vuln & KHONG fires_fixed
       expect=safe          -> compile ca 2 & KHONG fires_vuln & KHONG fires_fixed
  2) Dien concepts/lines_concept = annotator tree-sitter (tai dung 02_extract_concept)
     tren func_vuln; family_pred = predict_family (heuristic, khong leak nhan CWE).

Chay TU REPO ROOT:  .venv/bin/python bench/build_items.py
"""
import os, sys, json, collections, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)                                # run_diff, authored
sys.path.insert(0, os.path.join(ROOT, "pipeline_v3"))  # common

from run_diff import run_diff, CXX          # noqa: E402
from authored import ITEMS                  # noqa: E402
import common                               # noqa: E402


def load_annotator():
    p = os.path.join(ROOT, "pipeline_v3", "02_extract_concept.py")
    spec = importlib.util.spec_from_file_location("extract_concept", p)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod.load_annotator()


def check(item):
    r = run_diff(item["ref_test"], item)
    if item["expect"] == "safe":
        ok = (r["compiles_vuln"] and r["compiles_fixed"]
              and not r["fires_vuln"] and not r["fires_fixed"])
    else:
        ok = (r["compiles_vuln"] and r["compiles_fixed"]
              and r["fires_vuln"] and not r["fires_fixed"])
    return ok, r


def build(src_items, out_name):
    """Self-check + annotate -> ghi bench/items/<out_name>. Tra (good, bad). Dung chung
    cho seed (authored) va Juliet (juliet_extract)."""
    if not CXX:
        raise SystemExit("Khong co compiler (cc/gcc/clang).")
    os.chdir(ROOT)                          # annotator dung duong dan tuong doi ConceptCoder/...
    annotate = load_annotator()
    out_path = os.path.join(ROOT, "bench", "items", out_name)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    good, bad = [], []
    for it in src_items:
        ok, r = check(it)
        print("  [%s] %-30s %s" % ("OK " if ok else "FAIL", it["id"], "" if ok else r))
        if not ok:
            bad.append(it["id"]); continue
        try:
            concepts, lc = annotate(it["func_vuln"])
        except Exception as e:
            concepts, lc = [0] * len(common.PROPS), {}
            print("     [warn] annotate loi: %s" % str(e)[:80])
        d = dict(it)
        d["concepts"], d["lines_concept"] = concepts, lc
        d["family_pred"] = common.predict_family({"func": it["func_vuln"], "lines_concept": lc})
        good.append(d)

    with open(out_path, "w") as f:
        for d in good:
            f.write(json.dumps(d) + "\n")
    print("\n%s: %d/%d OK -> %s" % (out_name, len(good), len(src_items), out_path))
    if bad:
        print("FAIL (sua truoc khi dung): %s" % ", ".join(bad))
    return good, bad


def main():
    good, _ = build(ITEMS, "gold.jsonl")
    print("family_pred:", dict(collections.Counter(d["family_pred"] for d in good)))
    print("\n%-14s %-12s %s" % ("id", "gold", "pred (concept signal)"))
    for d in good:
        flag = "" if (d["expect"] == "safe" or d["family_pred"]) else "  <- None (concept yeu)"
        print("  %-14s %-12s %s%s" % (d["id"], d["family"], d["family_pred"], flag))


if __name__ == "__main__":
    main()
