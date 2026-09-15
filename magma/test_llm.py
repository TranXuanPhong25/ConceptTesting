#!/usr/bin/env python3
"""Test nhanh ket noi LLM (Groq hoac 9router/Vertex Gemini) TRUOC khi chay full — tranh dot ca run roi loi auth.

Chay TU REPO ROOT:
  # Groq (mac dinh):
  GROQ_API_KEY=gsk_... .venv/bin/python magma/test_llm.py
  # 9router / Vertex Gemini:
  LLM_PROVIDER=router ROUTER_BASE_URL=https://.../v1 ROUTER_API_KEY=... \
    LLM_MODEL=vertex/gemini-3.1-pro-preview python3 magma/test_llm.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import llm_client                                              # noqa: E402

prov = os.environ.get("LLM_PROVIDER", "groq")
print("provider =", prov, "| model =", llm_client.model_id())
if prov == "router":
    print("ROUTER_BASE_URL =", os.environ.get("ROUTER_BASE_URL") or "(THIEU!)")
    print("ROUTER_API_KEY  =", "co" if (os.environ.get("ROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")) else "(THIEU!)")

llm = llm_client.make_llm()
if llm is None:
    raise SystemExit("[X] make_llm() -> None: thieu key/base_url. Kiem env o tren.")

from langchain_core.messages import HumanMessage             # noqa: E402
try:
    r = llm.invoke([HumanMessage(content="Reply with exactly the two characters: OK")])
    print("[OK] ket noi thanh cong. Model tra ve:", repr((r.content or "")[:120]))
except Exception as e:
    print("[X] goi that bai:", type(e).__name__, str(e)[:300])
    sys.exit(1)
