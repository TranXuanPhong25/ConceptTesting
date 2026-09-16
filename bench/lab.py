#!/usr/bin/env python3
"""Harness thi nghiem DUNG CHUNG: sinh test qua LLM (Groq | 9router | Vertex native) + cham diem vi-phan + McNemar.

Dung cho cac huong (placebo, patch_concept, ...): moi huong chi dinh nghia them DIEU KIEN
(name -> builder(item)->messages) roi goi generate() + report(). Tai dung bench/run_diff (oracle).

Env: GROQ_RPM=30 | SAMPLES=1 | LLM_PROVIDER=groq|router|vertex (xem magma/llm_client.py, them 2026-09-16
     de chay Juliet qua Gemini dong bo voi feedback/loop.py). Cache key da gom MODEL nen doi provider/model
     KHONG dam cache cu.
"""
import os, sys, json, time, math, hashlib, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "pipeline_v3"))
import common                       # noqa: E402,F401
from run_diff import run_diff       # noqa: E402
_llc = importlib.util.spec_from_file_location("magma_llm_client", os.path.join(ROOT, "magma", "llm_client.py"))
llm_client = importlib.util.module_from_spec(_llc); _llc.loader.exec_module(llm_client)

MODEL      = llm_client.model_id()
GROQ_RPM   = int(os.environ.get("GROQ_RPM", "30"))
SAMPLES    = int(os.environ.get("SAMPLES", "1"))


def _key(cond, item, builder, s):
    m = builder(item)
    blob = "::".join([MODEL, cond, item["id"], str(s), m[0]["content"], m[1]["content"]])
    return hashlib.sha1(blob.encode()).hexdigest()


def load_cache(path):
    c = {}
    if os.path.exists(path):
        for l in open(path):
            try:
                o = json.loads(l); c[o["key"]] = o["target"]
            except Exception:
                pass
    return c


def generate(items, conds, cache_path):
    """conds: dict name->builder. Sinh K=SAMPLES mau/item/cond qua LLM (llm_client). Resumable."""
    cache = load_cache(cache_path)
    from langchain_core.messages import SystemMessage, HumanMessage
    llm = llm_client.make_llm(temperature=0.3)
    if llm is None:
        raise SystemExit("Thieu key/base_url cho LLM_PROVIDER=%s." % os.environ.get("LLM_PROVIDER", "groq"))
    mi = 60.0 / max(1, GROQ_RPM); last = [0.0]

    def call(m):
        for a in range(6):
            dt = time.monotonic() - last[0]
            if dt < mi:
                time.sleep(mi - dt)
            last[0] = time.monotonic()
            try:
                return llm.invoke([SystemMessage(content=m[0]["content"]), HumanMessage(content=m[1]["content"])]).content
            except Exception as e:
                w = min(60, 4 * 2 ** a); print("[warn] retry %ds: %s" % (w, str(e)[:80])); time.sleep(w)
        return None

    new = 0
    for i, it in enumerate(items):
        for cond, builder in conds.items():
            for s in range(SAMPLES):
                k = _key(cond, it, builder, s)
                if k in cache:
                    continue
                o = call(builder(it))
                if o and len(o) > 40:
                    cache[k] = o
                    open(cache_path, "a").write(json.dumps({"key": k, "target": o}) + "\n"); new += 1
        if (i + 1) % 5 == 0:
            print("  %d/%d (moi %d, cache %d)" % (i + 1, len(items), new, len(cache)))
    print("gen xong: cache %d (moi %d)" % (len(cache), new))
    return cache


def _disc(out, item):
    r = run_diff(out, item)
    return 1 if (r["compiles_vuln"] and r["compiles_fixed"] and r["fires_vuln"] and not r["fires_fixed"]) else 0


def evaluate(items, conds, cache):
    """Tra {cond: {"sum":float, "n":int, "bin":{id:0/1}}}. bin = da so mau discriminate (cho McNemar)."""
    out = {c: {"sum": 0.0, "n": 0, "bin": {}} for c in conds}
    for it in items:
        for cond, builder in conds.items():
            outs = [cache[_key(cond, it, builder, s)] for s in range(SAMPLES) if _key(cond, it, builder, s) in cache]
            if not outs:
                continue
            ds = [_disc(o, it) for o in outs]
            frac = sum(ds) / len(ds)
            a = out[cond]; a["sum"] += frac; a["n"] += 1; a["bin"][it["id"]] = 1 if frac >= 0.5 else 0
    return out


def mcnemar(bin_a, bin_b):
    """Exact (sign/binomial) McNemar tren cap khong-hop (discordant). Tra (b, c, p_two_sided)."""
    ids = set(bin_a) & set(bin_b)
    b = sum(1 for i in ids if bin_a[i] == 1 and bin_b[i] == 0)   # a hon b
    c = sum(1 for i in ids if bin_a[i] == 0 and bin_b[i] == 1)   # b hon a
    n = b + c
    if n == 0:
        return b, c, 1.0
    k = min(b, c)
    p = 2 * sum(math.comb(n, i) for i in range(k + 1)) * (0.5 ** n)
    return b, c, min(1.0, p)


def report(items, conds, cache, mcnemar_pairs=()):
    ev = evaluate(items, conds, cache)
    print("\nmodel: %s | items: %d | SAMPLES: %d\n" % (MODEL, len(items), SAMPLES))
    print("  %-22s %8s   %s" % ("cond", "DISCRIM", "(disc/n)"))
    for c in conds:
        a = ev[c]; n = a["n"] or 1
        print("  %-22s %6.0f%%   (%.1f/%d)" % (c, 100 * a["sum"] / n, a["sum"], a["n"]))
    for x, y in mcnemar_pairs:
        b, cc, p = mcnemar(ev[x]["bin"], ev[y]["bin"])
        sig = "***" if p < 0.01 else ("*" if p < 0.05 else "ns")
        print("\nMcNemar %s vs %s: %s hon=%d, %s hon=%d, p=%.4f (%s)" % (x, y, x, b, y, cc, p, sig))
    return ev
