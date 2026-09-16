#!/usr/bin/env python3
"""Huong PATCH-DERIVED CONCEPT — rut guidance tu DIFF vuln<->fixed (patch), theo DIG (arXiv 2606.13037).

Kich ban 'one-day' (patch DA BIET): bench_patch = blind base + goi y tu patch = dieu kien AN TOAN ma ban
va ap dat (chinh la dieu can VI PHAM de kich hoat loi tren ban chua va). So voi concept tree-sitter.

So 3 dieu kien: bench_blind | bench_concept (tree-sitter) | bench_patch (diff-derived).
Chay TU REPO ROOT (Groq, mac dinh):
  GROQ_API_KEY=... SAMPLES=3 .venv/bin/python patch_concept/run.py
  GOLD=bench/items/gold_juliet.jsonl PATCH_CACHE=patch_concept/juliet.jsonl ... (Juliet)
Chay voi Gemini qua 9router (them 2026-09-16, qua bench/lab.py::generate -> llm_client):
  LLM_PROVIDER=router ROUTER_BASE_URL=https://.../v1 ROUTER_API_KEY=... LLM_MODEL=vertex/gemini-3-flash-preview \\
      GOLD=bench/items/gold_juliet.jsonl PATCH_CACHE=patch_concept/juliet_en_gemini.jsonl \\
      .venv/bin/python patch_concept/run.py
"""
import os, sys, re, json

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); BENCH = os.path.join(ROOT, "bench")
sys.path.insert(0, BENCH); sys.path.insert(0, os.path.join(ROOT, "pipeline_v3"))
import common                                                       # noqa: E402
import lab                                                          # noqa: E402
from prompts import (build_bench_blind, build_bench_concept, _harness_note,      # noqa: E402
                      build_bench_blind_en, build_bench_concept_en, _harness_note_en)


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


# EN (2026-09-16): ban tieng Anh — dung khi chay voi Gemini, tranh confound ngon ngu (dong bo voi
# bench/prompts.py::build_bench_blind_en / feedback/loop.py). diff_guidance con lai VIETNAMESE (chi la
# text mo ta LOGIC RUT TU DIFF, khong phai prompt gui LLM truc tiep o day) -> dich rieng ham nay cho ban _en.
def diff_guidance_en(item):
    added = _added(item["func_vuln"], item["func_fixed"])
    conds = []
    for a in added:
        m = re.search(r"if\s*\((.+?)\)\s*(?:\{|return|$)", a)
        if m:
            conds.append(m.group(1).strip())
    spec = "The patch (fix) ADDS these lines:\n" + "\n".join("  + " + a for a in added[:6])
    if conds:
        spec += ("\n-> SAFETY condition imposed by the patch: %s. To TRIGGER the bug on the UNPATCHED build, "
                 "supply input such that this condition WOULD occur (violate the safety assumption)."
                 % " ; ".join("`%s`" % c for c in conds))
    else:
        spec += ("\n-> The patch reorders operations / sets a pointer to NULL after free to avoid the bug; "
                 "trigger it by going down the path the patch BLOCKS (e.g. use the pointer AFTER free).")
    return spec


def build_patch_en(item):
    d = {"func": item["func_vuln"], "lines_concept": item.get("lines_concept") or {}, "family_pred": item.get("family_pred")}
    msgs = build_bench_blind_en(item)                             # da bao gom _harness_note_en
    # build_bench_blind_en da chen _harness_note_en o cuoi -> chen GUIDANCE truoc phan harness note bang
    # cach dung LAI logic build_blind_adv-EN thay vi ghep chuoi mu (tranh harness note bi ket giua).
    fn = common.focal(d["func"]) or item["focal"]
    guidance = "\n\nGUIDANCE FROM THE PATCH (patch-derived):\n" + diff_guidance_en(item)
    base = msgs[-1]["content"]
    hn = _harness_note_en(item, fn)
    assert base.endswith(hn), "build_bench_blind_en format da doi, can cap nhat build_patch_en"
    msgs[-1]["content"] = base[: -len(hn)] + guidance + hn
    return msgs


CONDS = {"bench_blind": build_bench_blind, "bench_concept": build_bench_concept, "bench_patch": build_patch}
CONDS_EN = {"bench_blind_en": build_bench_blind_en, "bench_concept_en": build_bench_concept_en,
            "bench_patch_en": build_patch_en}
GOLD = os.environ.get("GOLD", os.path.join(BENCH, "items", "gold_juliet.jsonl"))
CACHE = os.environ.get("PATCH_CACHE", os.path.join(HERE, "juliet.jsonl"))
PATCH_LANG = os.environ.get("PATCH_LANG", "vi")   # vi (cu) | en (dung khi LLM_PROVIDER=router/vertex Gemini)


def main():
    conds = CONDS_EN if PATCH_LANG == "en" else CONDS
    suffix = "_en" if PATCH_LANG == "en" else ""
    items = [json.loads(l) for l in open(GOLD) if l.strip()]
    pos = [it for it in items if it["expect"] != "safe"]
    # generate() tu doc cache truoc, chi thuc su can key/base_url khi co CACHE MISS (xem bench/lab.py) ->
    # KHONG con gate cung theo GROQ_API_KEY (sai voi LLM_PROVIDER=router/vertex).
    cache = lab.generate(pos, conds, CACHE)
    lab.report(pos, conds, cache,
               mcnemar_pairs=[("bench_patch" + suffix, "bench_concept" + suffix),
                              ("bench_patch" + suffix, "bench_blind" + suffix)])
    print("\nDoc: patch-derived dung THEM thong tin (patch) so voi concept tree-sitter -> kich ban one-day.")


if __name__ == "__main__":
    main()
