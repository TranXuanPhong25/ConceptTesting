"""Gemini (Vertex AI) client with a resume cache and a token/cost ledger.

Reuses the repository's provider factory (``magma.llm_client.make_llm``,
LLM_PROVIDER=vertex). Every call is cached by (model, temperature, thinking
budget, messages, sample key), so interrupted runs resume without re-billing
and re-runs are reproducible. Usage is appended to a ledger JSONL.

Pricing (USD per 1M tokens) for gemini-3-flash-preview on Vertex AI:
input 0.50, output 3.00 (thinking tokens are billed as output). Override
with CH_PRICE_IN / CH_PRICE_OUT.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

PRICE_IN = float(os.environ.get("CH_PRICE_IN", "0.50"))
PRICE_OUT = float(os.environ.get("CH_PRICE_OUT", "3.00"))


def cost_usd(input_tokens: int, output_tokens: int, reasoning_tokens: int = 0) -> float:
    return (input_tokens * PRICE_IN + (output_tokens + reasoning_tokens) * PRICE_OUT) / 1e6


@dataclass
class LLMResponse:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    latency_s: float = 0.0
    cached: bool = False
    error: str = ""

    @property
    def cost(self) -> float:
        return cost_usd(self.input_tokens, self.output_tokens, self.reasoning_tokens)


def response_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and isinstance(block.get("text"), str) and block.get("type", "text") == "text":
            parts.append(block["text"])
    return "".join(parts)


class LLM:
    """Thread-safe cached chat client. ``messages`` are (role, text) with role in system|user|assistant."""

    def __init__(
        self,
        cache_path: Path,
        ledger_path: Path,
        temperature: float = 0.7,
        thinking_budget: int | None = None,
        max_output_tokens: int | None = None,
        timeout: float = 600.0,
        max_concurrency: int = 8,
        backend: Any = None,
    ):
        self.cache_path = Path(cache_path)
        self.ledger_path = Path(ledger_path)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.temperature = temperature
        self.thinking_budget = thinking_budget
        self.max_output_tokens = max_output_tokens
        self.timeout = timeout
        self.backend = backend  # test hook: callable(messages)->LLMResponse
        self._local = threading.local()
        self._lock = threading.Lock()
        self._sem = threading.Semaphore(max_concurrency)
        self._cache: dict[str, dict[str, Any]] = {}
        if self.cache_path.exists():
            with self.cache_path.open() as handle:
                for line in handle:
                    if line.strip():
                        try:
                            row = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        self._cache[row["key"]] = row

    @property
    def model(self) -> str:
        return os.environ.get("LLM_MODEL", "gemini-3-flash-preview")

    def _client(self):
        client = getattr(self._local, "client", None)
        if client is None:
            if self.thinking_budget is not None:
                os.environ["LLM_THINKING_BUDGET"] = str(self.thinking_budget)
            else:
                os.environ.pop("LLM_THINKING_BUDGET", None)
            from magma.llm_client import make_llm

            client = make_llm(
                temperature=self.temperature,
                timeout=self.timeout,
                max_retries=0,
                max_tokens=self.max_output_tokens,
            )
            if client is None:
                raise RuntimeError("LLM not configured (source scripts/vertex_env.sh)")
            self._local.client = client
        return client

    def key(self, messages: Sequence[tuple[str, str]], sample_key: str) -> str:
        blob = json.dumps(
            [self.model, self.temperature, self.thinking_budget, list(messages), sample_key], ensure_ascii=False
        )
        return hashlib.sha256(blob.encode()).hexdigest()

    def chat(self, messages: Sequence[tuple[str, str]], tag: str, sample_key: str = "", meta: dict | None = None) -> LLMResponse:
        key = self.key(messages, sample_key)
        with self._lock:
            hit = self._cache.get(key)
        if hit is not None:
            response = LLMResponse(hit["text"], hit["input_tokens"], hit["output_tokens"], hit["reasoning_tokens"],
                                   hit.get("latency_s", 0.0), cached=True)
            self._ledger(tag, response, meta)
            return response
        response = self._call(messages)
        if not response.error:
            row = {"key": key, "tag": tag, "text": response.text, "input_tokens": response.input_tokens,
                   "output_tokens": response.output_tokens, "reasoning_tokens": response.reasoning_tokens,
                   "latency_s": response.latency_s, "model": self.model}
            with self._lock:
                self._cache[key] = row
                with self.cache_path.open("a") as handle:
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        self._ledger(tag, response, meta)
        return response

    def _call(self, messages: Sequence[tuple[str, str]]) -> LLMResponse:
        if self.backend is not None:
            return self.backend(messages)
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        converted = []
        for role, text in messages:
            if role == "system":
                converted.append(SystemMessage(content=text))
            elif role == "assistant":
                converted.append(AIMessage(content=text))
            else:
                converted.append(HumanMessage(content=text))
        last_error = ""
        for attempt in range(7):
            with self._sem:
                start = time.monotonic()
                try:
                    result = self._client().invoke(converted)
                except Exception as exc:  # noqa: BLE001 - quota / transport errors are retried
                    last_error = f"{type(exc).__name__}: {str(exc)[:300]}"
                    result = None
                latency = time.monotonic() - start
            if result is not None:
                usage = getattr(result, "usage_metadata", None) or {}
                details = usage.get("output_token_details") or {}
                reasoning = int(details.get("reasoning", 0) or 0)
                text = response_text(getattr(result, "content", ""))
                # langchain's output_tokens excludes thoughts for Gemini; keep them separate
                return LLMResponse(text, int(usage.get("input_tokens", 0) or 0), int(usage.get("output_tokens", 0) or 0),
                                   reasoning, round(latency, 2))
            wait = min(90, 5 * 2**attempt)
            time.sleep(wait)
        return LLMResponse("", error=last_error)

    def _ledger(self, tag: str, response: LLMResponse, meta: dict | None) -> None:
        row = {"t": round(time.time(), 1), "tag": tag, "cached": response.cached, "in": response.input_tokens,
               "out": response.output_tokens, "think": response.reasoning_tokens, "latency_s": response.latency_s,
               "cost": round(response.cost, 6), "error": response.error, **(meta or {})}
        with self._lock:
            with self.ledger_path.open("a") as handle:
                handle.write(json.dumps(row) + "\n")


# ------------------------------------------------------------------ parsing


def extract_code(text: str, lang: str = "cpp") -> str | None:
    """Last fenced code block (C++ preferred)."""
    blocks = re.findall(r"```([a-zA-Z0-9+#]*)\s*\n(.*?)```", text, re.S)
    if not blocks:
        return text if "#include" in text and "main" in text else None
    wanted = [body for tag, body in blocks if tag.lower() in ({"cpp", "c++", "cc", "cxx"} if lang == "cpp" else {lang})]
    chosen = wanted or [body for _, body in blocks]
    # prefer the block that has a main()
    with_main = [body for body in chosen if "main" in body] if lang == "cpp" else chosen
    return (with_main or chosen)[-1].strip()


def extract_json(text: str) -> Any:
    """Parse the first JSON object/array in the text (fenced or bare)."""
    fenced = re.findall(r"```(?:json)?\s*\n(.*?)```", text, re.S)
    candidates = fenced + [text]
    for candidate in candidates:
        candidate = candidate.strip()
        for opener, closer in (("{", "}"), ("[", "]")):
            start = candidate.find(opener)
            if start < 0:
                continue
            depth = 0
            in_str = False
            escape = False
            for index in range(start, len(candidate)):
                ch = candidate[index]
                if in_str:
                    if escape:
                        escape = False
                    elif ch == "\\":
                        escape = True
                    elif ch == '"':
                        in_str = False
                    continue
                if ch == '"':
                    in_str = True
                elif ch == opener:
                    depth += 1
                elif ch == closer:
                    depth -= 1
                    if depth == 0:
                        blob = candidate[start : index + 1]
                        try:
                            return json.loads(blob)
                        except json.JSONDecodeError:
                            try:
                                return json.loads(re.sub(r"//[^\n]*", "", blob))
                            except json.JSONDecodeError:
                                break
    return None
