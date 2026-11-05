"""Replace the backend by implementing CoreModel.generate; pipeline code stays unchanged."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModelResponse:
    text: str
    usage: dict[str, Any] = field(default_factory=dict)
    finish_reason: str | None = None


class ModelError(RuntimeError):
    """Sanitized transport error; never includes credentials or endpoint URLs."""


class CoreModel(ABC):
    @property
    @abstractmethod
    def model_id(self) -> str:
        """Stable identifier recorded in run manifests."""

    @abstractmethod
    def generate(self, messages: list[dict[str, str]], *, temperature: float,
                 max_tokens: int, seed: int) -> ModelResponse:
        """One model invocation, without automatic retries."""


class OpenAICompatibleModel(CoreModel):
    """Chat-completions transport for vLLM, routers, and compatible providers.

    URL and key are read only from environment. Custom providers can subclass
    CoreModel instead of changing any generation/evaluation code.
    """

    def __init__(self, model: str, *, base_url_env: str = "FINAL_BASE_URL",
                 api_key_env: str = "FINAL_API_KEY", timeout: float = 240,
                 extra_body: dict | None = None):
        self._model = model
        self.base_url = os.environ.get(base_url_env, "").rstrip("/")
        if not self.base_url.startswith(("http://", "https://")):
            raise ValueError(f"Set {base_url_env} to the API base URL (including /v1 if required)")
        self.key = os.environ.get(api_key_env, "")
        self.timeout = timeout
        self.extra_body = extra_body or {}
        reserved = {"model", "messages", "stream", "temperature", "max_tokens", "seed"}
        if reserved & self.extra_body.keys():
            raise ValueError("extra_body cannot override standard request fields")

    @property
    def model_id(self) -> str:
        return self._model

    def generate(self, messages, *, temperature, max_tokens, seed):
        body = dict(model=self.model_id, messages=messages, temperature=temperature,
                    max_tokens=max_tokens, seed=seed, stream=False, **self.extra_body)
        headers = {"Content-Type": "application/json"}
        if self.key:
            headers["Authorization"] = "Bearer " + self.key
        req = urllib.request.Request(self.base_url + "/chat/completions",
                                     data=json.dumps(body).encode(), headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read(16 * 1024 * 1024 + 1)
            if len(raw) > 16 * 1024 * 1024:
                raise ModelError("API response exceeds 16 MiB")
            data = json.loads(raw)
            choice = data["choices"][0]
            content = choice["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ModelError("API returned no text content")
            return ModelResponse(content, data.get("usage", {}), choice.get("finish_reason"))
        except urllib.error.HTTPError as exc:
            raise ModelError(f"HTTP {exc.code}; no automatic retry (usage may be unknown)") from None
        except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
            raise ModelError(f"API request failed: {type(exc).__name__}; usage may be unknown") from None
