"""Streaming vLLM transport with explicit, sanitized failure information."""
from __future__ import annotations

import json
import http.client
import os
import shlex
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from final.core_model import CoreModel, ModelError, ModelResponse


class TransportError(ModelError):
    def __init__(self, operation: str, error_type: str, *, http_status=None,
                 retryable=False, completion_started=False, partial_text=""):
        self.operation = operation
        self.error_type = error_type
        self.http_status = http_status
        self.retryable = retryable
        self.completion_started = completion_started
        self.partial_text = partial_text
        super().__init__(f"{operation}: {error_type}" + (f" (HTTP {http_status})" if http_status else ""))

    def details(self) -> dict:
        return {
            "operation": self.operation,
            "error_type": self.error_type,
            "http_status": self.http_status,
            "retryable": self.retryable,
            "completion_started": self.completion_started,
            "partial_text_characters": len(self.partial_text),
        }


@dataclass(frozen=True)
class PreparedGeneration:
    messages: list[dict[str, str]]
    prompt_tokens: int
    output_tokens: int


class QwenModel(CoreModel):
    """Same sampling parameters as v1; streaming avoids silent full-response waits."""

    def __init__(self, *, context=8192, timeout=180, expected_model=None):
        self.context = context
        self.timeout = timeout
        self.endpoint_file = Path(os.environ.get("FINAL_ENDPOINT_ENV_FILE", "/tmp/concepttester-final-qwen.env"))
        self.expected_model = expected_model or "qwen3.5-27b-awq"
        self.refresh_configuration()

    def refresh_configuration(self):
        configuration = dict(os.environ)
        if self.endpoint_file.exists():
            for line in self.endpoint_file.read_text().splitlines():
                fields = shlex.split(line, comments=True)
                if fields and fields[0] == "export":
                    fields = fields[1:]
                if len(fields) == 1 and "=" in fields[0]:
                    name, value = fields[0].split("=", 1)
                    if name in ("FINAL_BASE_URL", "FINAL_MODEL", "FINAL_API_KEY"):
                        configuration[name] = value
        self.base_url = configuration.get("FINAL_BASE_URL", "").rstrip("/")
        self.api_key = configuration.get("FINAL_API_KEY", "")
        self.name = configuration.get("FINAL_MODEL", self.expected_model)
        if self.name != self.expected_model:
            raise TransportError("configuration", "ModelChanged")
        if not self.base_url.startswith(("https://", "http://")):
            raise TransportError("configuration", "MissingEndpoint")

    @property
    def model_id(self):
        return self.expected_model

    def request(self, operation: str, body=None, *, timeout=None):
        self.refresh_configuration()
        if operation == "tokenize":
            endpoint_root = self.base_url[:-3] if self.base_url.endswith("/v1") else self.base_url
            endpoint = endpoint_root + "/tokenize"
        else:
            endpoint = self.base_url + ("/models" if operation == "models" else "/chat/completions")
        headers = {"Content-Type": "application/json", "ngrok-skip-browser-warning": "1"}
        if self.api_key:
            headers["Authorization"] = "Bearer " + self.api_key
        request_data = json.dumps(body).encode() if body is not None else None
        http_request = urllib.request.Request(endpoint, data=request_data, headers=headers)
        try:
            return urllib.request.urlopen(http_request, timeout=timeout or self.timeout)
        except urllib.error.HTTPError as error:
            raise TransportError(operation, "HTTPError", http_status=error.code,
                retryable=error.code in (408, 429, 500, 502, 503, 504) or
                    (error.code == 404 and operation in ("models", "tokenize")),
                completion_started=operation == "completion") from None
        except (OSError, ValueError, http.client.HTTPException) as error:
            raise TransportError(operation, type(error).__name__, retryable=True,
                completion_started=operation == "completion") from None

    def check_endpoint(self):
        try:
            with self.request("models", timeout=25) as response:
                payload = json.load(response)
        except (OSError, ValueError, http.client.HTTPException) as error:
            raise TransportError("models", type(error).__name__, retryable=True) from None
        if not isinstance(payload, dict):
            raise TransportError("models", "InvalidPayload", retryable=True)
        matching_models = []
        for served_model in payload.get("data", []):
            if isinstance(served_model, dict) and served_model.get("id") == self.expected_model:
                matching_models.append(served_model)
        if not matching_models:
            raise TransportError("models", "ExpectedModelMissing")
        advertised_context = matching_models[0].get("max_model_len", self.context)
        if advertised_context < self.context:
            raise TransportError("models", "ContextTooSmall")
        return {"model": self.expected_model, "context": advertised_context}

    def tokens(self, messages):
        request_body = {
            "model": self.expected_model,
            "messages": messages,
            "add_generation_prompt": True,
            "chat_template_kwargs": {"enable_thinking": False},
        }
        for attempt_number in range(3):
            try:
                with self.request("tokenize", request_body, timeout=60) as response:
                    payload = json.load(response)
                if not isinstance(payload, dict):
                    raise TransportError("tokenize", "InvalidPayload", retryable=True)
                token_count = payload.get("count")
                if token_count is None:
                    token_count = len(payload.get("tokens", []))
                if type(token_count) is not int or token_count <= 0:
                    raise TransportError("tokenize", "InvalidTokenCount")
                return token_count
            except (OSError, ValueError, http.client.HTTPException) as error:
                transport_error = TransportError("tokenize", type(error).__name__, retryable=True)
                if attempt_number == 2:
                    raise transport_error from None
                time.sleep((5, 20)[attempt_number])
            except TransportError as error:
                if not error.retryable or attempt_number == 2:
                    raise
                time.sleep((5, 20)[attempt_number])

    def prepare_generation(self, messages, max_tokens):
        prompt_tokens = self.tokens(messages)
        output_tokens = min(max_tokens, self.context - prompt_tokens - 64)
        if output_tokens < min(256, max_tokens):
            raise TransportError("tokenize", "PromptExceedsContext")
        return PreparedGeneration(messages, prompt_tokens, output_tokens)

    def generate_prepared(self, prepared, *, temperature, seed):
        request_body = {
            "model": self.expected_model,
            "messages": prepared.messages,
            "temperature": temperature,
            "max_tokens": prepared.output_tokens,
            "seed": seed,
            "stream": True,
            "stream_options": {"include_usage": True},
            "chat_template_kwargs": {"enable_thinking": False},
        }
        text_fragments = []
        usage = {}
        finish_reason = None
        response_bytes = 0
        generation_started_at = time.monotonic()
        usage_footer_complete = False
        try:
            with self.request("completion", request_body) as response:
                for response_line in response:
                    if time.monotonic() - generation_started_at > 1800:
                        raise TransportError("completion", "GenerationDeadline", completion_started=True)
                    response_bytes += len(response_line)
                    if response_bytes > 16 * 1024 * 1024:
                        raise TransportError("completion", "ResponseTooLarge", completion_started=True)
                    response_line = response_line.strip()
                    if not response_line.startswith(b"data:"):
                        continue
                    event_data = response_line[5:].strip()
                    if event_data == b"[DONE]":
                        break
                    event = json.loads(event_data)
                    if not isinstance(event, dict) or not isinstance(event.get("choices", []), list):
                        raise TransportError("completion", "InvalidStreamEvent", retryable=True, completion_started=True)
                    if event.get("usage"):
                        usage = event["usage"]
                        usage_footer_complete = True
                    for choice in event.get("choices", []):
                        if not isinstance(choice, dict):
                            raise TransportError("completion", "InvalidStreamChoice", retryable=True, completion_started=True)
                        if choice.get("index", 0) != 0:
                            continue
                        delta = choice.get("delta") or {}
                        if not isinstance(delta, dict):
                            raise TransportError("completion", "InvalidStreamDelta", retryable=True, completion_started=True)
                        content = delta.get("content")
                        if content is not None and not isinstance(content, str):
                            raise TransportError("completion", "InvalidStreamContent", retryable=True, completion_started=True)
                        if content:
                            text_fragments.append(content)
                        if choice.get("finish_reason") is not None:
                            finish_reason = choice["finish_reason"]
        except (OSError, ValueError, http.client.HTTPException) as error:
            if finish_reason is None:
                raise TransportError("completion", type(error).__name__, retryable=True,
                    completion_started=True, partial_text="".join(text_fragments)) from None
        except TransportError as error:
            if finish_reason is None:
                error.partial_text = "".join(text_fragments)
                raise
        complete_text = "".join(text_fragments)
        if finish_reason is None or not complete_text.strip():
            raise TransportError("completion", "IncompleteStream", retryable=True,
                completion_started=True, partial_text=complete_text)
        usage = dict(usage, tokenizer_prompt_tokens=prepared.prompt_tokens,
                     requested_output_budget=prepared.output_tokens,
                     usage_footer_complete=usage_footer_complete)
        return ModelResponse(complete_text, usage, finish_reason)

    def generate(self, messages, *, temperature, max_tokens, seed):
        prepared = self.prepare_generation(messages, max_tokens)
        return self.generate_prepared(prepared, temperature=temperature, seed=seed)
