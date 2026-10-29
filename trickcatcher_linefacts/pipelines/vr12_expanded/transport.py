"""Single-attempt ngrok transport with a shared registered completion ledger."""
import fcntl
import hashlib
import json
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from .paths import CONFIG
from .llm_client import NoRedirect, atomic_json

MAX_ATTEMPTS = 3503


class Client:
    def __init__(self, root):
        raw = os.environ.get('CT_RETRIEVAL_BASE_URL', '').rstrip('/')
        url = urllib.parse.urlsplit(raw)
        if url.scheme != 'https' or not re.fullmatch(r'[a-z0-9.-]+\.(?:ngrok-free\.dev|ngrok-free\.app|ngrok\.app|ngrok\.io)', url.hostname or ''):
            raise ValueError('authorized HTTPS endpoint required')
        if url.path != '/v1' or url.query or url.fragment or url.username or url.password:
            raise ValueError('endpoint must end in /v1 without credentials or query')
        self._base, self.root, self.model = raw, Path(root), CONFIG['model']
        self.root.mkdir(parents=True, exist_ok=True)
        self._open = urllib.request.build_opener(NoRedirect()).open
        self.stop = threading.Event()

    def http(self, path, payload=None, root=False):
        request = urllib.request.Request((self._base[:-3] if root else self._base) + path,
            data=None if payload is None else json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json', 'ngrok-skip-browser-warning': '1'})
        try:
            with self._open(request, timeout=240 if payload is not None else 25) as response:
                raw = response.read(8_000_001)
            if len(raw) > 8_000_000:
                raise RuntimeError('response_size_limit')
            return json.loads(raw)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f'http_status_{exc.code}') from None
        except Exception as exc:
            raise RuntimeError('transport_' + type(exc).__name__) from None

    def preflight(self):
        models = self.http('/models')
        item = next((m for m in models.get('data', []) if m.get('id') == self.model), None)
        if item is None or item.get('max_model_len', 8192) != 8192:
            raise ValueError('registered_model_or_context_absent')
        atomic_json(self.root / 'endpoint_metadata.json', {'model': self.model, 'context_limit': 8192})

    def reserve(self, key):
        with (self.root / 'attempts.jsonl').open('a+') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            stream.seek(0)
            rows = [json.loads(line) for line in stream if line.strip()]
            if len(rows) >= MAX_ATTEMPTS:
                raise RuntimeError('registered_completion_cap')
            if any(r['key'] == key for r in rows):
                raise RuntimeError('attempted_request_must_not_retry')
            stream.write(json.dumps({'key': key, 'time': time.time()}) + '\n')
            stream.flush()

    def chat(self, messages, seed, *, temperature=0.7, top_p=0.95, max_tokens=1024):
        if self.stop.is_set():
            raise RuntimeError('transport_stopped')
        body = dict(model=self.model, messages=messages, seed=seed, temperature=temperature,
                    top_p=top_p, max_tokens=max_tokens, stream=False, chat_template_kwargs={'enable_thinking': False})
        key = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        folder = self.root / 'calls' / key
        folder.mkdir(parents=True, exist_ok=True)
        with (folder / '.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            saved = folder / 'response.json'
            if saved.exists():
                response = json.loads(saved.read_text())
                if response.get('status') != 'received':
                    self.stop.set()
                    raise RuntimeError('previous_request_failed')
                return response
            attempted = False
            start = time.monotonic()
            try:
                tokens = self.http('/tokenize', dict(model=self.model, messages=messages,
                    add_generation_prompt=True, chat_template_kwargs={'enable_thinking': False}), root=True)
                if not isinstance(tokens.get('count'), int) or tokens['count'] + max_tokens > 8192:
                    raise RuntimeError('context_preflight_failed')
                atomic_json(folder / 'request.json', dict(body=body, prompt_tokens=tokens['count']))
                self.reserve(key)
                attempted = True
                raw = self.http('/chat/completions', body)
                atomic_json(folder / 'raw.json', raw)
                if raw.get('model') != self.model:
                    raise RuntimeError('served_model_changed')
                choice, usage = raw['choices'][0], raw.get('usage') or {}
                value = choice['message'].get('content') or ''
                if not isinstance(value, str):
                    raise ValueError('invalid_content')
                response = dict(key=key, status='received', text=value, model=self.model,
                    n_in=usage.get('prompt_tokens', 0), n_out=usage.get('completion_tokens', 0),
                    usage=usage, finish_reason=choice.get('finish_reason'), seconds=time.monotonic()-start,
                    params={k:body[k] for k in ('model','seed','temperature','top_p','max_tokens')}, transport_attempts=1)
                atomic_json(saved, response)
                return response
            except Exception as exc:
                self.stop.set()
                error = str(exc) if re.fullmatch(r'[A-Za-z_0-9]+', str(exc)) else type(exc).__name__
                atomic_json(saved, dict(status='failed', error=error, attempted=attempted,
                    unknown_completion_usage=attempted and not error.startswith('http_status_4'), seconds=time.monotonic()-start))
                raise RuntimeError(error) from None
