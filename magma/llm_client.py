#!/usr/bin/env python3
"""Chon LLM provider qua env — de chay CUNG thi nghiem voi teacher khac (Groq gpt-oss vs Gemini 3.1 Pro
qua 9router/Vertex AI) MA KHONG nhan ban code. Cache tu tach theo model (prompt_key da hash model).

  LLM_PROVIDER=groq   (mac dinh) -> ChatGroq, GROQ_MODEL, GROQ_API_KEY
  LLM_PROVIDER=vertex            -> ChatVertexAI NATIVE (goi thang Google Vertex AI, khong qua router)
       VERTEX_PROJECT  = GCP project id            (bat buoc)
       VERTEX_LOCATION = region, mac dinh us-central1 (vd global neu model chi o global)
       LLM_MODEL       = ten model Vertex, mac dinh gemini-3.1-pro-preview
       AUTH: `gcloud auth application-default login`  HOAC  GOOGLE_APPLICATION_CREDENTIALS=/path/sa.json
  LLM_PROVIDER=router            -> ChatOpenAI OpenAI-compatible (vd 9router)
       ROUTER_BASE_URL + ROUTER_API_KEY + LLM_MODEL

Dung `model_id()` de lay ten model dua vao prompt_key => cache Gemini KHONG lan cache Groq.
"""
import os


def model_id():
    """Ten model hien tai (theo provider) — dung cho prompt_key de tach cache."""
    p = os.environ.get("LLM_PROVIDER", "groq")
    if p == "vertex":
        return os.environ.get("LLM_MODEL", os.environ.get("VERTEX_MODEL", "gemini-3.1-pro-preview"))
    if p == "router":
        return os.environ.get("LLM_MODEL", "vertex/gemini-3.1-pro-preview")
    return os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")


def make_llm(temperature=0.6):
    """Tra ve LLM co .invoke(messages).content, hoac None neu thieu cau hinh (chay bang cache)."""
    provider = os.environ.get("LLM_PROVIDER", "groq")
    if provider == "vertex":
        proj = os.environ.get("VERTEX_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT")
        loc = os.environ.get("VERTEX_LOCATION", "us-central1")
        if not proj:
            return None                                       # thieu project -> chay bang cache
        from langchain_google_vertexai import ChatVertexAI     # lazy: pip install langchain-google-vertexai
        # auth qua ADC (gcloud auth application-default login) hoac GOOGLE_APPLICATION_CREDENTIALS
        return ChatVertexAI(model=model_id(), temperature=temperature, project=proj, location=loc)
    if provider == "router":
        key = os.environ.get("ROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
        base = os.environ.get("ROUTER_BASE_URL")
        if not (key and base):
            return None
        from langchain_openai import ChatOpenAI                # lazy: chi can khi that su dung router
        return ChatOpenAI(model=model_id(), temperature=temperature, api_key=key, base_url=base)
    from langchain_groq import ChatGroq
    key = os.environ.get("GROQ_API_KEY")
    return ChatGroq(model=model_id(), temperature=temperature, groq_api_key=key) if key else None
