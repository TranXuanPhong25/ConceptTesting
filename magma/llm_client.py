#!/usr/bin/env python3
"""Chon LLM provider qua env — de chay CUNG thi nghiem voi teacher khac (Groq gpt-oss vs Gemini 3.1 Pro
qua 9router/Vertex AI) MA KHONG nhan ban code. Cache tu tach theo model (prompt_key da hash model).

  LLM_PROVIDER=groq   (mac dinh) -> ChatGroq, GROQ_MODEL, GROQ_API_KEY
  LLM_PROVIDER=router            -> ChatOpenAI OpenAI-compatible (9router route toi Vertex Gemini)
       ROUTER_BASE_URL = endpoint 9router (vd https://.../v1)
       ROUTER_API_KEY  = key 9router  (hoac OPENAI_API_KEY)
       LLM_MODEL       = id model tren 9router (vd vertex/gemini-3.1-pro-preview)

Dung `model_id()` de lay ten model dua vao prompt_key => cache Gemini KHONG lan cache Groq.
Neu 9router KHONG phai OpenAI-compatible thi bao — se doi sang client native.
"""
import os


def model_id():
    """Ten model hien tai (theo provider) — dung cho prompt_key de tach cache."""
    if os.environ.get("LLM_PROVIDER", "groq") == "router":
        return os.environ.get("LLM_MODEL", "vertex/gemini-3.1-pro-preview")
    return os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")


def make_llm(temperature=0.6):
    """Tra ve LLM co .invoke(messages).content, hoac None neu thieu key (chay bang cache)."""
    provider = os.environ.get("LLM_PROVIDER", "groq")
    if provider == "router":
        key = os.environ.get("ROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
        base = os.environ.get("ROUTER_BASE_URL")
        if not (key and base):
            return None                                       # thieu cau hinh -> chay bang cache
        from langchain_openai import ChatOpenAI                # lazy: chi can khi that su dung router
        return ChatOpenAI(model=model_id(), temperature=temperature, api_key=key, base_url=base)
    from langchain_groq import ChatGroq
    key = os.environ.get("GROQ_API_KEY")
    return ChatGroq(model=model_id(), temperature=temperature, groq_api_key=key) if key else None
