"""Bounded, content-addressed ngrok transport; endpoint values never persisted."""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

MODEL = "qwen3.5-27b-awq"
MAX_ATTEMPTS = 356


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def atomic(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    temp.replace(path)


def digest(data) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def json_object(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    result = json.loads(text)
    if not isinstance(result, dict):
        raise ValueError("expected_json_object")
    return result


class Client:
    def __init__(self, out: Path, timeout=150):
        self.out = Path(out)
        self.timeout = timeout
        raw = os.environ.get("CT_RETRIEVAL_BASE_URL", "").rstrip("/")
        parsed = urllib.parse.urlsplit(raw)
        if parsed.scheme != "https" or not re.fullmatch(r"[a-z0-9.-]+\.(?:ngrok-free\.app|ngrok-free\.dev|ngrok\.app|ngrok\.io)", parsed.hostname or ""):
            raise ValueError("Authorized ngrok HTTPS endpoint required in CT_RETRIEVAL_BASE_URL")
        if parsed.path != "/v1" or parsed.query or parsed.fragment or parsed.username or parsed.password:
            raise ValueError("Endpoint must have the /v1 path without credentials/query")
        self._base = raw
        self._open = urllib.request.build_opener(NoRedirect()).open
        self.out.mkdir(parents=True, exist_ok=True)

    def http(self, path, payload=None, *, root=False):
        data = None if payload is None else json.dumps(payload).encode()
        req = urllib.request.Request((self._base[:-3] if root else self._base) + path, data=data,
                                     headers={"Content-Type": "application/json", "ngrok-skip-browser-warning": "1"})
        try:
            with self._open(req, timeout=self.timeout if data else 25) as response:
                content = response.read(4_000_001)
            if len(content) > 4_000_000:
                raise RuntimeError("response_size_limit")
            return json.loads(content)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"http_status_{exc.code}") from None
        except Exception as exc:
            raise RuntimeError("transport_" + type(exc).__name__) from None

    def preflight(self):
        result = self.http("/models")
        model = next((m for m in result.get("data", []) if m.get("id") == MODEL), None)
        if not model:
            raise ValueError("Authorized served model is absent; no substitution")
        metadata = {"model": MODEL, "context_limit": model.get("max_model_len", 8192)}
        atomic(self.out / "endpoint_metadata.json", metadata)
        return metadata

    def tokens(self, messages):
        payload = {"model": MODEL, "messages": messages, "add_generation_prompt": True,
                   "chat_template_kwargs": {"enable_thinking": False}}
        value = self.http("/tokenize", payload, root=True)
        if not isinstance(value.get("count"), int):
            raise ValueError("tokenizer_count_missing")
        return {"prompt_tokens": value["count"], "context_limit": value.get("max_model_len", 8192)}

    def reserve(self, identity):
        path = self.out / "attempts.jsonl"
        with path.open("a+") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            stream.seek(0)
            rows = [json.loads(x) for x in stream if x.strip()]
            if len(rows) >= MAX_ATTEMPTS:
                raise ValueError("registered_attempt_budget_exhausted")
            if any(r["request_sha256"] == identity["request_sha256"] for r in rows):
                raise ValueError("previous_attempt_without_terminal_response_no_retry")
            stream.write(json.dumps({**identity, "time": time.time()}) + "\n")
            stream.flush()
            fcntl.flock(stream, fcntl.LOCK_UN)

    def complete(self, messages, *, stage: str, max_tokens: int, seed: int):
        request = {"model": MODEL, "messages": messages, "temperature": 0.1, "top_p": 0.95,
                   "max_tokens": max_tokens, "seed": seed, "stream": False,
                   "chat_template_kwargs": {"enable_thinking": False}, "response_format": {"type": "json_object"}}
        key = digest({"stage": stage, "request": request})
        folder = self.out / "calls" / key
        response_path = folder / "response.json"
        if response_path.exists():
            return json.loads(response_path.read_text())
        token_info = self.tokens(messages)
        if token_info["prompt_tokens"] + max_tokens > token_info["context_limit"]:
            # No model inference has happened; do not silently truncate a task.
            raise ValueError("context_preflight_failed")
        atomic(folder / "request.json", {"stage": stage, "body": request, "tokens": token_info})
        self.reserve({"stage": stage, "request_sha256": key, "prompt_tokens": token_info["prompt_tokens"], "max_tokens": max_tokens})
        start = time.monotonic()
        try:
            raw = self.http("/chat/completions", request)
            atomic(folder / "raw.json", raw)
            choice = raw["choices"][0]
            message = choice["message"]
            value = {"request_sha256": key, "stage": stage, "status": "received", "model": raw.get("model"),
                     "content": message.get("content") or "", "reasoning_content": message.get("reasoning_content") or "",
                     "finish_reason": choice.get("finish_reason"), "usage": raw.get("usage", {}),
                     "elapsed_seconds": time.monotonic() - start}
            try:
                value["parsed"] = json_object(value["content"])
            except (ValueError, TypeError):
                value["parse_error"] = True
        except Exception as exc:
            # Never serialize an exception string that may contain an endpoint.
            safe = str(exc) if re.fullmatch(r"(?:http_status_\d+|transport_\w+)", str(exc)) else type(exc).__name__
            value = {"request_sha256": key, "stage": stage, "status": "failed", "error": safe,
                     "unknown_completion_usage": not safe.startswith("http_status_4"), "elapsed_seconds": time.monotonic() - start}
        atomic(response_path, value)
        return value
