#!/usr/bin/env python3
"""Sinh INPUT-generator qua Groq (teacher) cho Magma. blind vs concept. Resumable (append-jsonl cache).

Chay TU REPO ROOT:  GROQ_API_KEY=gsk_... SAMPLES=3 .venv/bin/python magma/gen.py
Env: GROQ_MODEL (mac dinh openai/gpt-oss-120b) | GROQ_RPM=30 | CONDS | GOLD | MAGMA_GEN_CACHE
Key doc tu env (KHONG hardcode).
"""
import os, sys, json, time, glob

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from prompts import BUILD, prompt_key                            # noqa: E402

GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_RPM   = int(os.environ.get("GROQ_RPM", "30"))
SAMPLES    = int(os.environ.get("SAMPLES", "1"))
CONDS      = os.environ.get("CONDS", "magma_blind,magma_concept").split(",")
GOLD       = os.environ.get("GOLD")   # neu set: 1 file; khong thi gop tat ca items/*.jsonl (da-target)
CACHE      = os.environ.get("MAGMA_GEN_CACHE", os.path.join(HERE, "gen_cache.jsonl"))
KEY        = os.environ.get("GROQ_API_KEY")
if not KEY:
    raise SystemExit("Thieu GROQ_API_KEY.")

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
llm = ChatGroq(model=GROQ_MODEL, temperature=0.6, groq_api_key=KEY)
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


_files = [GOLD] if GOLD else sorted(glob.glob(os.path.join(HERE, "items", "*.jsonl")))
items = [json.loads(l) for f in _files for l in open(f) if l.strip()]
print("items:", len(items), "| files:", len(_files), "| model:", GROQ_MODEL, "| conds:", CONDS, "| SAMPLES:", SAMPLES)
new = 0
for it in items:
    for cond in CONDS:
        for s in range(SAMPLES):
            k = prompt_key(GROQ_MODEL, cond, it) + "#%d" % s
            if k in _cache:
                continue
            o = call(BUILD[cond](it))
            if o and len(o) > 30:
                _cache[k] = o
                open(CACHE, "a").write(json.dumps({"key": k, "target": o}) + "\n"); new += 1
print("\nXONG. cache:", len(_cache), "moi:", new, "| ->", CACHE)
print("-> .venv/bin/python magma/score.py")
