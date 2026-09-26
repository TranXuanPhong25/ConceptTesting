"""Resume-safe Gemini calls through the repo's shared Vertex client.

Every call is cached as one JSON file (prompt, response, token usage), so a
killed run resumes without repeating paid calls and costs can be audited.
The client itself is ``magma.llm_client.make_llm`` (native Vertex AI).
"""

from __future__ import annotations

import concurrent.futures as cf
import json
import os
import random
import re
import shlex
import threading
import time
from pathlib import Path
from typing import Any

from trickcatcher_concept.provenance import sha256_text

TRANSIENT = ("429", "500", "503", "504", "ResourceExhausted", "DeadlineExceeded", "Unavailable",
             "UNAVAILABLE", "timed out", "Timeout", "RemoteDisconnected", "Connection", "empty response",
             "watchdog")

# The underlying ChatVertexAI client is given `timeout=180`, but a handful of calls have been
# observed to block far longer than that (grpc/thinking-mode edge cases). A generous outer
# watchdog on a dedicated pool guarantees `call()` always returns so one stuck request cannot
# starve `max_concurrency` forever; the orphaned thread is left to finish or die with the process.
WATCHDOG_TIMEOUT_S = 240
_watchdog_pool = cf.ThreadPoolExecutor(max_workers=256, thread_name_prefix="tcc-llm-watchdog")


def load_env_file(path: str | os.PathLike) -> list[str]:
    """Parse ``export KEY=value`` lines without a shell; returns the key names only."""
    keys = []
    for line in Path(path).read_text().splitlines():
        match = re.match(r"\s*export\s+([A-Za-z_][A-Za-z0-9_]*)=(.*)$", line)
        if match:
            value = shlex.split(match.group(2), comments=True)
            os.environ.setdefault(match.group(1), value[0] if value else "")
            keys.append(match.group(1))
    return keys


def response_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(item if isinstance(item, str) else item.get("text", "")
                       for item in content if isinstance(item, (str, dict)))
    return ""


class LLM:
    """Thread-safe cached caller. ``factory`` is injectable for tests.

    ``min_interval`` paces the *start* of every call attempt (a token-bucket-style
    reservation, not just a cap on concurrent in-flight calls): the observed
    failure mode against this Vertex project was sustained ResourceExhausted
    (429) errors even at low concurrency, i.e. a requests-per-minute quota
    rather than a concurrency quota, which only pacing -- not a smaller
    semaphore -- fixes.
    """

    def __init__(self, cache_root: Path, max_concurrency: int = 8, factory=None, model: str | None = None,
                min_interval: float = 0.0):
        self.cache_root = Path(cache_root)
        self.semaphore = threading.Semaphore(max_concurrency)
        self._clients: dict[tuple, Any] = {}
        self._lock = threading.Lock()
        self._retry_log_lock = threading.Lock()
        self._rate_lock = threading.Lock()
        self._next_dispatch = 0.0
        self.min_interval = min_interval
        self._factory = factory
        self.model = model or os.environ.get("LLM_MODEL", "")

    def _throttle(self) -> None:
        if self.min_interval <= 0:
            return
        with self._rate_lock:
            now = time.monotonic()
            reserved = max(now, self._next_dispatch)
            self._next_dispatch = reserved + self.min_interval
        wait = reserved - now
        if wait > 0:
            time.sleep(wait)

    def _client(self, temperature: float, max_tokens: int):
        key = (temperature, max_tokens, self.model)
        with self._lock:
            if key not in self._clients:
                if self._factory is not None:
                    self._clients[key] = self._factory(temperature, max_tokens)
                else:
                    from magma.llm_client import make_llm
                    if self.model:
                        os.environ["LLM_MODEL"] = self.model
                    client = make_llm(temperature=temperature, timeout=180, max_retries=0, max_tokens=max_tokens)
                    if client is None:
                        raise RuntimeError("Vertex/Gemini provider is not configured")
                    self._clients[key] = client
            return self._clients[key]

    def model_name(self) -> str:
        return self.model

    def call(self, name: str, prompt: str, *, temperature: float, max_tokens: int, retries: int = 6) -> dict:
        """Return the cached record for ``name`` or perform the call. Raises after retries."""
        path = self.cache_root / f"{name}.json"
        prompt_sha = sha256_text(prompt)
        if path.is_file():
            record = json.loads(path.read_text())
            if record.get("prompt_sha256") == prompt_sha and record.get("response"):
                record["cached"] = True
                return record
        from langchain_core.messages import HumanMessage

        client = self._client(temperature, max_tokens)
        last_error = ""
        for attempt in range(retries + 1):
            self._throttle()
            started = time.time()
            try:
                with self.semaphore:
                    future = _watchdog_pool.submit(client.invoke, [HumanMessage(content=prompt)])
                    try:
                        response = future.result(timeout=WATCHDOG_TIMEOUT_S)
                    except cf.TimeoutError as exc:
                        raise TimeoutError(f"watchdog: no response within {WATCHDOG_TIMEOUT_S}s") from exc
                text = response_text(getattr(response, "content", response)).strip()
                if not text:
                    raise ValueError("empty response")
                usage = dict(getattr(response, "usage_metadata", None) or {})
                record = {
                    "name": name, "model": self.model_name(), "temperature": temperature,
                    "max_tokens": max_tokens, "thinking_budget": os.environ.get("LLM_THINKING_BUDGET"),
                    "prompt_sha256": prompt_sha, "prompt": prompt, "response": text,
                    "input_tokens": usage.get("input_tokens", 0), "output_tokens": usage.get("output_tokens", 0),
                    "attempts": attempt + 1, "latency_s": round(time.time() - started, 2),
                    "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                }
                path.parent.mkdir(parents=True, exist_ok=True)
                tmp = path.with_suffix(".tmp")
                tmp.write_text(json.dumps(record, ensure_ascii=False))
                os.replace(tmp, path)
                record["cached"] = False
                return record
            except Exception as exc:  # noqa: BLE001 - provider errors are heterogeneous
                last_error = f"{type(exc).__name__}: {exc}"[:500]
                self._log_retry(name, attempt, last_error)
                if attempt >= retries or not any(token in last_error for token in TRANSIENT):
                    break
                time.sleep(min(120, 10 * 2**attempt) * (0.5 + random.random()))
        raise RuntimeError(f"LLM call {name} failed: {last_error}")

    def _log_retry(self, name: str, attempt: int, error: str) -> None:
        """Append-only diagnostic log of every failed attempt (not the successful cache), so
        retry causes (rate limits vs. other transient errors) can be audited after a run."""
        line = json.dumps({"name": name, "attempt": attempt, "error": error,
                           "at": time.strftime("%Y-%m-%dT%H:%M:%S")}) + "\n"
        with self._retry_log_lock:
            self.cache_root.mkdir(parents=True, exist_ok=True)
            with (self.cache_root / "_retries.jsonl").open("a") as handle:
                handle.write(line)


def extract_code(response: str, lang: str) -> str:
    """Take the longest fenced block if present, otherwise the whole reply."""
    blocks = re.findall(r"```[ \t]*([A-Za-z0-9_+#-]*)[^\n]*\n(.*?)```", response, flags=re.S)
    if blocks:
        preferred = [b for tag, b in blocks if tag.lower() in ({"cpp", "c++", "cc"} if lang == "cpp" else {"python", "py", "python3"})]
        pool = preferred or [b for _, b in blocks]
        return max(pool, key=len).strip() + "\n"
    text = response.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[^\n]*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
    return text.strip() + "\n"


def extract_json(response: str) -> Any:
    text = response.strip()
    fenced = re.findall(r"```(?:json)?\s*\n(.*?)```", text, flags=re.S)
    candidates = fenced + [text]
    match = re.search(r"\{.*\}", text, flags=re.S)
    if match:
        candidates.append(match.group(0))
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except ValueError:
            continue
    raise ValueError("no JSON object in response")
