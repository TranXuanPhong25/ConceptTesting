#!/usr/bin/env python3
"""Cham diem Magma: render input tu output model -> oracle vi-phan (vuln/fixed) -> triggered/discrim.

Metric (K mau, ty le dat):
  TRIGGERED = canary dung bug muc tieu HOAC abort tren build VULN (ground-truth)
  DISCRIM   = TRIGGERED tren vuln & SACH tren fixed
So blind vs concept + McNemar (tai dung bench/lab.mcnemar).

Chay TU REPO ROOT (sau magma/gen.py):  .venv/bin/python magma/score.py
"""
import os, sys, json, collections, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "bench"))
import lab                                                      # noqa: E402  (bench/lab -> cache sys.modules['prompts']=bench)
from oracle import run_input, discrim, render_input             # noqa: E402  (magma, ten rieng)

# magma/prompts va bench/prompts TRUNG ten -> nap magma/prompts theo DUONG DAN (tranh bench/prompts da cache).
_ps = importlib.util.spec_from_file_location("magma_prompts", os.path.join(HERE, "prompts.py"))
_pm = importlib.util.module_from_spec(_ps); _ps.loader.exec_module(_pm)
prompt_key = _pm.prompt_key

import glob                                                       # noqa: E402
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
CACHE = os.environ.get("MAGMA_GEN_CACHE", os.path.join(HERE, "gen_cache.jsonl"))
SAMPLES = int(os.environ.get("SAMPLES", "1"))
CONDS = os.environ.get("CONDS", "magma_blind,magma_concept").split(",")


def load_items():
    """GOLD (1 file) neu set, khong thi gop tat ca magma/items/*.jsonl (da-target)."""
    g = os.environ.get("GOLD")
    files = [g] if g else sorted(glob.glob(os.path.join(HERE, "items", "*.jsonl")))
    return [json.loads(l) for f in files for l in open(f) if l.strip()]


def load_cache():
    c = {}
    if os.path.exists(CACHE):
        for l in open(CACHE):
            try:
                o = json.loads(l); c[o["key"]] = o["target"]
            except Exception:
                pass
    return c


def _samples(item, cond, cache):
    base = prompt_key(GROQ_MODEL, cond, item)
    return [cache[base + "#%d" % s] for s in range(SAMPLES) if base + "#%d" % s in cache]


def main():
    cache = load_cache()
    if not cache:
        raise SystemExit("Cache rong (%s). Chay magma/gen.py truoc." % CACHE)
    items = load_items()
    agg = {c: {"n": 0, "has": 0, "render": 0.0, "trig": 0.0, "disc": 0.0} for c in CONDS}
    # per-item discriminate (max qua K mau) cho McNemar — DICT keyed by bug_id (lab.mcnemar yeu cau)
    binv = {c: {} for c in CONDS}

    for it in items:
        per = {}
        for c in CONDS:
            a = agg[c]; a["n"] += 1
            smp = _samples(it, c, cache)
            if not smp:
                per[c] = 0; continue
            a["has"] += 1
            rendered = 0; trig = 0.0; disc = 0.0; any_disc = 0
            for raw in smp:
                data = render_input(raw)
                if not data:
                    continue
                rendered += 1
                res = run_input(data, it)
                t = res["triggered"]                         # canary dung bug muc tieu (ground-truth)
                d = discrim(res)
                trig += t; disc += d; any_disc = max(any_disc, d)
            k = len(smp)
            a["render"] += rendered / k; a["trig"] += trig / k; a["disc"] += disc / k
            per[c] = any_disc
        for c in CONDS:
            binv[c][it["bug_id"]] = per.get(c, 0)
        print("  %-14s " % it["bug_id"] + " ".join("%s=%d" % (c.replace("magma_", ""), per.get(c, 0)) for c in CONDS))

    print("\nmodel:", GROQ_MODEL, "| items:", len(items), "| SAMPLES:", SAMPLES, "\n")
    print("%-14s %8s %10s %11s %9s" % ("cond", "have", "render%", "TRIGGER%", "DISCRIM%"))
    for c in CONDS:
        a = agg[c]; n = a["n"] or 1
        print("%-14s %6d/%-2d %9.0f%% %10.0f%% %8.0f%%"
              % (c, a["has"], a["n"], 100 * a["render"] / n, 100 * a["trig"] / n, 100 * a["disc"] / n))

    if len(CONDS) >= 2:
        # mcnemar(concept, blind): b = concept-only thang, c = blind-only thang
        b, c_, p = lab.mcnemar(binv[CONDS[1]], binv[CONDS[0]])
        print("\nMcNemar %s vs %s: concept-only=%d blind-only=%d p=%.4f"
              % (CONDS[1], CONDS[0], b, c_, p))
    print("\nDISCRIM = input NO dung bug tren VULN & SACH tren FIXED (oracle vi-phan Magma).")


if __name__ == "__main__":
    main()
