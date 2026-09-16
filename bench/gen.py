#!/usr/bin/env python3
"""Sinh test cho benchmark qua LLM teacher (Groq | 9router | Vertex native). blind vs concept. Resumable.

Chay (Groq, mac dinh):
  GROQ_API_KEY=gsk_... .venv/bin/python bench/gen.py
Chay voi Gemini qua 9router (them 2026-09-16, dong bo voi feedback/loop.py):
  LLM_PROVIDER=router ROUTER_BASE_URL=https://.../v1 ROUTER_API_KEY=... LLM_MODEL=vertex/gemini-3-flash-preview \\
      CONDS=bench_blind_en,bench_concept_en .venv/bin/python bench/gen.py
Env: GROQ_RPM=30 | SAMPLES=1 | CONDS=bench_blind,bench_concept[,bench_concept2,bench_blind_en,bench_concept_en]
     | GOLD | BENCH_CACHE | LLM_PROVIDER=groq|router|vertex (xem magma/llm_client.py)
Cache key = prompt_key(model, cond, item) — da gom NOI DUNG prompt (khong chi ten model) nen doi
provider/model/prompt TU DONG khong dam cache cu (xem bench/prompts.py::prompt_key).
"""
import os, sys, json, time, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "pipeline_v3"))
import common                        # noqa: E402
from prompts import BUILD, prompt_key  # noqa: E402
_llc = importlib.util.spec_from_file_location("magma_llm_client", os.path.join(ROOT, "magma", "llm_client.py"))
llm_client = importlib.util.module_from_spec(_llc); _llc.loader.exec_module(llm_client)

MODEL      = llm_client.model_id()
GROQ_RPM   = int(os.environ.get("GROQ_RPM", "30"))
SAMPLES    = int(os.environ.get("SAMPLES", "1"))    # K mau/item (temperature -> khac nhau) -> giam nhieu
CONDS      = os.environ.get("CONDS", "bench_blind,bench_concept").split(",")
GOLD       = os.environ.get("GOLD", os.path.join(ROOT, "bench", "items", "gold_juliet.jsonl"))
CACHE      = os.environ.get("BENCH_CACHE", os.path.join(ROOT, "bench", "juliet_cache.jsonl"))


def _key(item, cond):
    return prompt_key(MODEL, cond, item)


_cache = {}
if os.path.exists(CACHE):
    for l in open(CACHE):
        try:
            o = json.loads(l); _cache[o["key"]] = o["target"]
        except Exception:
            pass
print("cache co san:", len(_cache))

from langchain_core.messages import SystemMessage, HumanMessage  # noqa: E402
llm = llm_client.make_llm(temperature=0.3)   # None neu thieu key -> chi doc duoc tu cache co san
mi = 60.0 / max(1, GROQ_RPM); last = [0.0]


def call(msgs):
    if llm is None:
        raise SystemExit("Cache mieng va KHONG co LLM (thieu key/base_url cho LLM_PROVIDER=%s)."
                          % os.environ.get("LLM_PROVIDER", "groq"))
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
print("items:", len(items), "| model:", MODEL, "| conds:", CONDS, "| SAMPLES:", SAMPLES)
new = 0
for i, it in enumerate(items):
    for cond in CONDS:
        for s in range(SAMPLES):
            k = _key(it, cond) + "#%d" % s
            if k in _cache:
                continue
            o = call(BUILD[cond](it))       # temperature 0.3 -> moi mau khac nhau
            if o and len(o) > 40:
                _cache[k] = o
                open(CACHE, "a").write(json.dumps({"key": k, "target": o}) + "\n"); new += 1
    if (i + 1) % 5 == 0:
        print("  %d/%d (moi %d, cache %d)" % (i + 1, len(items), new, len(_cache)))
print("\nXONG. cache:", len(_cache), "| file:", CACHE)
print("-> Chay:  .venv/bin/python bench/score.py")
