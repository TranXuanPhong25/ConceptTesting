#!/usr/bin/env python3
"""Sinh test cho benchmark qua Groq (teacher). blind vs concept. Resumable.

Chay:  GROQ_API_KEY=gsk_... .venv/bin/python bench/gen.py
Env:   GROQ_MODEL (mac dinh openai/gpt-oss-120b, free) | GROQ_RPM=30 |
       CONDS=bench_blind,bench_concept | BENCH_CACHE (duong dan cache)
Key doc tu env (KHONG hardcode). Cache key = cache_key(model, cond, id::func_vuln).
"""
import os, sys, json, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "pipeline_v3"))
import common          # noqa: E402
from prompts import BUILD  # noqa: E402

GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_RPM   = int(os.environ.get("GROQ_RPM", "30"))
CONDS      = os.environ.get("CONDS", "bench_blind,bench_concept").split(",")
GOLD       = os.environ.get("GOLD", os.path.join(ROOT, "bench", "items", "gold.jsonl"))
CACHE      = os.environ.get("BENCH_CACHE", os.path.join(ROOT, "bench", "bench_cache.jsonl"))
KEY        = os.environ.get("GROQ_API_KEY")
if not KEY:
    raise SystemExit("Thieu GROQ_API_KEY. Chay: GROQ_API_KEY=gsk_... .venv/bin/python bench/gen.py")


def _key(item, cond):
    return common.cache_key(GROQ_MODEL, cond, item["id"] + "::" + item["func_vuln"])


_cache = {}
if os.path.exists(CACHE):
    for l in open(CACHE):
        try:
            o = json.loads(l); _cache[o["key"]] = o["target"]
        except Exception:
            pass
print("cache co san:", len(_cache))

from langchain_groq import ChatGroq                              # noqa: E402
from langchain_core.messages import SystemMessage, HumanMessage  # noqa: E402
llm = ChatGroq(model=GROQ_MODEL, temperature=0.3, groq_api_key=KEY)
mi = 60.0 / max(1, GROQ_RPM); last = [0.0]


def call(msgs):
    for a in range(6):
        dt = time.monotonic() - last[0]
        if dt < mi:
            time.sleep(mi - dt)
        last[0] = time.monotonic()
        try:
            return llm.invoke([SystemMessage(content=msgs[0]["content"]),
                               HumanMessage(content=msgs[1]["content"])]).content
        except Exception as e:
            w = min(60, 4 * 2 ** a); print("[warn] retry %ds: %s" % (w, str(e)[:90])); time.sleep(w)
    return None


items = [json.loads(l) for l in open(GOLD) if l.strip()]
print("items:", len(items), "| model:", GROQ_MODEL, "| conds:", CONDS)
new = 0
for i, it in enumerate(items):
    for cond in CONDS:
        k = _key(it, cond)
        if k in _cache:
            continue
        o = call(BUILD[cond](it))
        if o and len(o) > 40:
            _cache[k] = o
            open(CACHE, "a").write(json.dumps({"key": k, "target": o}) + "\n"); new += 1
    if (i + 1) % 5 == 0:
        print("  %d/%d (moi %d, cache %d)" % (i + 1, len(items), new, len(_cache)))
print("\nXONG. cache:", len(_cache), "| file:", CACHE)
print("-> Chay:  .venv/bin/python bench/score.py")
