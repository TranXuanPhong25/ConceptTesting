"""Cached OpenAI-compatible client for a user-provided Qwen ngrok server."""
from __future__ import annotations

# Direct-script workers run with -I: establish this copy's package explicitly.
import sys as _package_sys
from pathlib import Path as _PackagePath
if not __package__:
    _package_here = _PackagePath(__file__).resolve().parent
    _package_sys.path.insert(0, str(_package_here.parents[2]))
    __package__ = "trickcatcher_linefacts.pipelines." + _package_here.name
from .paths import REPO as _REPO, DATA_OUT, CONFIG, dataset_paths

import fcntl
import hashlib
import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def atomic_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + f".{os.getpid()}.{threading.get_ident()}.tmp")
    temp.write_text(json.dumps(obj, ensure_ascii=False, allow_nan=False, indent=1) + "\n")
    temp.replace(path)


class Client:
    def __new__(cls, cache_dir, *, offline=True, model=None, **kwargs):
        if offline:
            from .offline_client import OfflineClient
            return OfflineClient(cache_dir, model=model, **kwargs)
        return super().__new__(cls)

    def __init__(self, cache_dir, *, workers=16, timeout=600, retries=8, backoff=2.0, offline=True, model=None):
        base = os.environ.get("QWEN_BASE_URL", "").rstrip("/")
        parsed = urllib.parse.urlsplit(base)
        host = parsed.hostname or ""
        local = host in ("localhost", "127.0.0.1", "::1")
        tunnel = any(host.endswith("." + suffix) for suffix in ("ngrok-free.app", "ngrok.app", "ngrok.io", "ngrok-free.dev", "ngrok.dev"))
        if not base or parsed.scheme not in ("http", "https") or not (local or tunnel):
            raise ValueError("Set QWEN_BASE_URL to the local fake server or the user's Qwen ngrok server")
        if parsed.username or parsed.password or parsed.query or parsed.fragment or (not local and parsed.scheme != "https"):
            raise ValueError("QWEN_BASE_URL must have no credentials/query/fragment and tunnels require HTTPS")
        self._url = base + ("" if parsed.path.rstrip("/").endswith("/v1") else "/v1") + "/chat/completions"
        self._token = os.environ.get("QWEN_API_KEY", "")
        self.model = model or CONFIG["model"]
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.workers, self.timeout, self.retries, self.backoff = workers, timeout, retries, backoff
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        self._log_lock = threading.Lock()
        self._slots = threading.BoundedSemaphore(workers)

    def _log(self, record):
        with self._log_lock, (self.cache_dir / "calls.jsonl").open("a") as stream:
            stream.write(json.dumps(record) + "\n")

    def chat(self, messages, seed, *, temperature=0.7, top_p=0.95, max_tokens=1024):
        with self._slots:
            return self._chat(messages, seed, temperature, top_p, max_tokens)

    def _chat(self, messages, seed, temperature, top_p, max_tokens):
        params = dict(model=self.model, temperature=temperature, top_p=top_p, max_tokens=max_tokens, seed=seed)
        payload = dict(params, messages=messages)
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
        key = hashlib.sha256(encoded).hexdigest()
        cache = self.cache_dir / f"{key}.json"
        with (self.cache_dir / f"{key}.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if cache.exists():
                record = json.loads(cache.read_text())
                self._log(dict(key=key, cache_hit=True, seed=seed))
                return dict(record, cache_hit=True)
            headers = {"Content-Type": "application/json", "ngrok-skip-browser-warning": "1"}
            if self._token:
                headers["Authorization"] = "Bearer " + self._token
            for attempt in range(self.retries + 1):
                start = time.perf_counter()
                try:
                    request = urllib.request.Request(self._url, encoded, headers)
                    with self._opener.open(request, timeout=self.timeout) as response:
                        raw = json.loads(response.read(16 * 1024 * 1024))
                    text = raw["choices"][0]["message"]["content"]
                    if not isinstance(text, str):
                        raise ValueError("invalid message content")
                    # The endpoint/token are never persisted even if a server echoes them.
                    for secret in (os.environ.get("QWEN_BASE_URL", ""), self._token):
                        if secret:
                            text = text.replace(secret, "[redacted]")
                    usage = raw.get("usage") or {}
                    n_in, n_out = int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0))
                    seconds = time.perf_counter() - start
                    record = dict(key=key, params=params, text=text, n_in=n_in, n_out=n_out,
                                  seconds=seconds, output_tokens_per_second=n_out / max(seconds, 1e-9),
                                  total_tokens_per_second=(n_in + n_out) / max(seconds, 1e-9),
                                  transport_attempts=attempt + 1)
                    atomic_json(cache, record)
                    self._log(dict(record, text=None, cache_hit=False, attempt=attempt))
                    return dict(record, cache_hit=False)
                except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError, IndexError, TypeError) as exc:
                    # Exception strings/HTTP bodies can contain endpoint URLs or credentials.
                    status = exc.code if isinstance(exc, urllib.error.HTTPError) else None
                    self._log(dict(key=key, seed=seed, attempt=attempt, cache_hit=False,
                                   seconds=time.perf_counter() - start, error=type(exc).__name__, status=status))
                    if attempt == self.retries or (status is not None and status not in (408, 429) and status < 500):
                        raise RuntimeError(f"Qwen request failed ({type(exc).__name__}, HTTP {status})") from None
                    time.sleep(min(30, self.backoff * 2 ** attempt))

    def chat_many(self, jobs):
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            return list(pool.map(lambda job: self.chat(*job), jobs))
