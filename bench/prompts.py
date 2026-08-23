#!/usr/bin/env python3
"""Prompt cho benchmark: blind vs concept.

Tai dung NGUON prompt pipeline_v3/common.py (build_blind_adv / build_concept) — byte-identical
voi pipeline that — roi them rang buoc HARNESS: chi GOI focal, dung khai bao co san (prelude),
KHONG dinh nghia lai -> test link duoc voi CA func_vuln lan func_fixed.

Concept dung `family_pred` (heuristic tu concept, khong dung nhan CWE) va concept_lines: khong leak.
Generator CHI thay func_vuln + prelude (khai bao), KHONG BAO GIO thay func_fixed.
"""
import os, sys, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "pipeline_v3"))
import common  # noqa: E402


def _harness_note(item, fn):
    pre = (item.get("driver_prelude") or "").strip()
    blk = ("Khai bao DA CO SAN (struct/typedef/helper — dung tham chieu, KHONG dinh nghia lai):\n"
           "```c\n%s\n```\n" % pre) if pre else ""
    return ("\n\n%sQUAN TRONG (harness): KHONG dinh nghia lai ham `%s` hay cac struct/helper tren "
            "(se duoc cung cap khi bien dich). Chi viet `int main()` GOI `%s(...)` voi input DOC HAI "
            "de kich hoat loi bo nho duoi AddressSanitizer/UBSan. Chi #include header chuan. "
            "Tra DUY NHAT mot khoi ```c ... ```." % (blk, fn, fn))


def _d(item):
    return {"func": item["func_vuln"],
            "lines_concept": item.get("lines_concept") or {},
            "family_pred": item.get("family_pred")}


def build_bench_blind(item):
    d = _d(item); msgs = common.build_blind_adv(d)
    fn = common.focal(item["func_vuln"]) or item["focal"]
    msgs[-1]["content"] += _harness_note(item, fn)
    return msgs


def build_bench_concept(item):
    d = _d(item); msgs = common.build_concept(d)
    fn = common.focal(item["func_vuln"]) or item["focal"]
    msgs[-1]["content"] += _harness_note(item, fn)
    return msgs


BUILD = {"bench_blind": build_bench_blind, "bench_concept": build_bench_concept}


def prompt_key(model, cond, item):
    """Cache key = hash CUA PROMPT that -> doi prompt (vd family_pred thay) TU dong invalidate."""
    m = BUILD[cond](item)
    blob = "::".join([model, cond, item["id"], m[0]["content"], m[1]["content"]])
    return hashlib.sha1(blob.encode()).hexdigest()
