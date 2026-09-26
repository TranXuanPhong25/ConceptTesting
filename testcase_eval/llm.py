"""Thread-safe Gemini/Vertex access for TestCase-Eval runs.

Reuses the repo's provider switch (`magma.llm_client.make_llm`) and response
normaliser (`testeval_py.llm_runner._response_text`).  Adds three things the
extension needs: loading the untracked Vertex env file without a shell
`source`, token accounting for cost reports, and bounded concurrency with
retry/backoff so long jobs survive quota errors.
"""

from __future__ import annotations

import os
import random
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# gRPC (Vertex transport) logs a line on every fork(); sandbox runs fork constantly.
os.environ.setdefault("GRPC_VERBOSITY", "ERROR")
os.environ.setdefault("GRPC_ENABLE_FORK_SUPPORT", "false")

DEFAULT_ENV_FILE = "/home/phong/dev/ConceptTester/scripts/vertex_env.sh"

# Vertex AI list price for gemini-3-flash-preview (USD per 1M tokens, text,
# standard tier) at the time of the run.  Thinking tokens bill as output.
PRICE_INPUT_PER_M = 0.50
PRICE_OUTPUT_PER_M = 3.00

_ASSIGN = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$")

# Process-wide call pacing: minimum seconds between call *starts*, shared by
# every Gemini instance in this interpreter (a generation script typically
# builds two: a `gen` LLM and a `helper` LLM, both hitting the same Vertex
# quota).  Set TESTCASE_EVAL_MIN_INTERVAL to throttle proactively instead of
# relying only on reactive 429 backoff; several agents in this repo share one
# Vertex project's quota, so keep this conservative under concurrent runs.
_PACE_LOCK = threading.Lock()
_LAST_CALL_AT = [0.0]


def _pace() -> None:
    interval = float(os.environ.get("TESTCASE_EVAL_MIN_INTERVAL", "0") or 0)
    if interval <= 0:
        return
    with _PACE_LOCK:
        wait = _LAST_CALL_AT[0] + interval - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _LAST_CALL_AT[0] = time.monotonic()


def load_env_file(path: str | None = None, override: bool = False) -> list[str]:
    """Parse `export KEY=VALUE` lines into os.environ. Returns the key names only."""
    env_path = Path(path or os.environ.get("TESTCASE_EVAL_ENV_FILE", DEFAULT_ENV_FILE))
    if not env_path.exists():
        return []
    keys: list[str] = []
    for line in env_path.read_text().splitlines():
        match = _ASSIGN.match(line)
        if not match:
            continue
        key, value = match.group(1), match.group(2).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if override or key not in os.environ:
            os.environ[key] = value
        keys.append(key)
    return keys


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    return input_tokens / 1e6 * PRICE_INPUT_PER_M + output_tokens / 1e6 * PRICE_OUTPUT_PER_M


@dataclass
class CallResult:
    text: str | None
    input_tokens: int = 0
    output_tokens: int = 0
    latency_s: float = 0.0
    error: str | None = None
    finish_reason: str | None = None

    def usage(self) -> dict[str, Any]:
        return {"input_tokens": self.input_tokens, "output_tokens": self.output_tokens, "latency_s": round(self.latency_s, 2)}


@dataclass
class UsageMeter:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    failures: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock)

    def add(self, result: CallResult) -> None:
        with self.lock:
            self.calls += 1
            self.input_tokens += result.input_tokens
            self.output_tokens += result.output_tokens
            if result.text is None:
                self.failures += 1

    def summary(self) -> dict[str, Any]:
        return {
            "calls": self.calls,
            "failures": self.failures,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "usd": round(estimate_cost(self.input_tokens, self.output_tokens), 4),
        }


class Gemini:
    """Minimal wrapper: `complete(prompt, system=None)` -> CallResult."""

    def __init__(
        self,
        temperature: float = 1.0,
        max_output_tokens: int = 2048,
        timeout: float = 120.0,
        max_attempts: int = 12,
        env_file: str | None = None,
        llm: Any = None,
    ) -> None:
        if llm is None:
            load_env_file(env_file)
            from magma.llm_client import make_llm

            llm = make_llm(temperature=temperature, timeout=timeout, max_retries=0, max_tokens=max_output_tokens)
            if llm is None:
                raise SystemExit("LLM is not configured (Vertex env missing)")
        self.llm = llm
        self.max_attempts = max_attempts
        self.meter = UsageMeter()

    @staticmethod
    def model_name() -> str:
        from magma.llm_client import model_id

        return model_id()

    def complete(self, prompt: str, system: str | None = None) -> CallResult:
        from langchain_core.messages import HumanMessage, SystemMessage

        from testeval_py.llm_runner import _response_text

        messages: list[Any] = []
        if system:
            messages.append(SystemMessage(content=system))
        messages.append(HumanMessage(content=prompt))
        last_error = None
        for attempt in range(self.max_attempts):
            _pace()
            start = time.monotonic()
            try:
                response = self.llm.invoke(messages)
            except Exception as exc:  # noqa: BLE001 - retry transport/quota errors
                last_error = str(exc)[:300]
                time.sleep(min(120, 4 * 2**attempt) * random.uniform(0.5, 1.5))
                continue
            usage = getattr(response, "usage_metadata", None) or {}
            meta = getattr(response, "response_metadata", None) or {}
            result = CallResult(
                text=_response_text(getattr(response, "content", response)),
                input_tokens=int(usage.get("input_tokens", 0) or 0),
                output_tokens=int(usage.get("output_tokens", 0) or 0),
                latency_s=time.monotonic() - start,
                finish_reason=str(meta.get("finish_reason")) if meta.get("finish_reason") is not None else None,
            )
            self.meter.add(result)
            return result
        failed = CallResult(text=None, error=last_error)
        self.meter.add(failed)
        return failed
