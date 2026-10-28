"""V85 chat transport with recorded output allocation inside the 8192 context."""
import fcntl
import hashlib
import json
import re
import time
from ..v85_retrievalhybrid.transport import Client as ParentClient
from ..v85_retrievalhybrid.llm_client import atomic_json


def request_key(body):
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class Client(ParentClient):
    def chat(self, messages, seed, *, temperature=0.7, top_p=0.95, max_tokens=1024):
        if self.stop.is_set():
            raise RuntimeError('transport_stopped')
        body = dict(model=self.model, messages=messages, seed=seed, temperature=temperature,
                    top_p=top_p, max_tokens=max_tokens, stream=False,
                    chat_template_kwargs={'enable_thinking': False})
        requested_key = request_key(body)
        attempted = False
        start = time.monotonic()
        folder = self.root / 'preflight' / requested_key
        try:
            tokens = self.http('/tokenize', dict(model=self.model, messages=messages,
                add_generation_prompt=True, chat_template_kwargs={'enable_thinking': False}), root=True)
            count = tokens.get('count')
            if type(count) is not int or count < 0 or count >= 8192:
                raise RuntimeError('context_preflight_failed')
            body['max_tokens'] = min(max_tokens, 8192-count)
            allocation = dict(requested_key=requested_key, prompt_tokens=count,
                requested_max_tokens=max_tokens, effective_max_tokens=body['max_tokens'], context_limit=8192)
            atomic_json(self.root/'context'/f'{requested_key}.json', allocation)
            key = request_key(body)
            folder = self.root / 'calls' / key
            folder.mkdir(parents=True, exist_ok=True)
            with (folder / '.lock').open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                saved = folder / 'response.json'
                if saved.exists():
                    response = json.loads(saved.read_text())
                    if response.get('status') != 'received':
                        raise RuntimeError('previous_request_failed')
                    return response
                atomic_json(folder/'request.json', dict(body=body, prompt_tokens=count, allocation=allocation))
                self.reserve(key)
                attempted = True
                raw = self.http('/chat/completions', body)
                atomic_json(folder/'raw.json', raw)
                if raw.get('model') != self.model:
                    raise RuntimeError('served_model_changed')
                choice, usage = raw['choices'][0], raw.get('usage') or {}
                value = choice['message'].get('content') or ''
                if not isinstance(value, str):
                    raise ValueError('invalid_content')
                response = dict(key=key, status='received', text=value, model=self.model,
                    n_in=usage.get('prompt_tokens', 0), n_out=usage.get('completion_tokens', 0),
                    usage=usage, finish_reason=choice.get('finish_reason'), seconds=time.monotonic()-start,
                    params={k:body[k] for k in ('model','seed','temperature','top_p','max_tokens')},
                    allocation=allocation, transport_attempts=1)
                atomic_json(saved, response)
                return response
        except Exception as exc:
            self.stop.set()
            error = str(exc) if re.fullmatch(r'[A-Za-z_0-9]+', str(exc)) else type(exc).__name__
            # Preserve any existing response when duplicate/replay validation fails.
            failed = folder/'response.json'
            if failed.exists():
                failed = folder/'replay_error.json'
            atomic_json(failed, dict(status='failed', error=error, attempted=attempted,
                unknown_completion_usage=attempted and not error.startswith('http_status_4'),
                seconds=time.monotonic()-start))
            raise RuntimeError(error) from None
