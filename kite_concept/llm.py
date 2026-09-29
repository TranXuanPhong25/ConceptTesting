from __future__ import annotations

import os
from typing import Any

from magma.llm_client import make_llm, model_id


def configured_llm(temperature: float = 0.1, timeout: float = 360, max_tokens: int = 8192) -> Any:
    """Reuse the repository client. The caller must source vertex_env.sh first."""
    if os.environ.get("LLM_PROVIDER") != "vertex":
        raise RuntimeError("LLM_PROVIDER must be vertex; source scripts/vertex_env.sh before calling")
    requested = model_id().lower()
    if "gemini-3" not in requested or "flash" not in requested or "preview" not in requested:
        raise RuntimeError(f"expected Gemini 3 Flash preview, configured model is {model_id()!r}")
    llm = make_llm(temperature=temperature, timeout=timeout, max_retries=0, max_tokens=max_tokens)
    if llm is None:
        raise RuntimeError("Vertex AI client is not configured")
    return llm


def response_text(response: Any) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            part if isinstance(part, str) else part.get("text", "")
            for part in content if isinstance(part, (str, dict))
        )
    return ""

