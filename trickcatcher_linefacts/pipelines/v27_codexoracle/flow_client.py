"""Explicit online transport (port of v23 diagnostic_client). Raw responses/cumulative attempts survive resume."""
import hashlib
import json
import os
import threading
import os
from pathlib import Path
import time
from urllib.parse import urlsplit

import httpx
from jinja2.sandbox import SandboxedEnvironment

from .paths import CONFIG
from .flow_common import digest, immutable, strict_json

D = CONFIG['flowrun']

HERE = Path(__file__).resolve().parent


class SlotFailure(RuntimeError):
    """Terminal failure for one logical slot; no more retries on resume."""


class ProtocolFailure(RuntimeError):
    """Model/token accounting cannot be trusted; stop the entire run."""


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f'{path.name}.{os.getpid()}.{threading.get_ident()}.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    temp.replace(path)


class Client:
    """No paid fallback. Construction requires the caller's explicit --online opt-in."""
    def __init__(self, root):
        raw = os.environ.get('QWEN_BASE_URL', '').rstrip('/')
        parsed = urlsplit(raw)
        host = parsed.hostname or ''
        local = host in ('localhost', '127.0.0.1', '::1')
        tunnel = any(host.endswith('.' + x) for x in
                     ('ngrok-free.dev', 'ngrok.dev', 'ngrok-free.app', 'ngrok.app', 'ngrok.io'))
        if (not raw or parsed.scheme not in ('http', 'https') or not (local or tunnel)
                or (not local and parsed.scheme != 'https') or parsed.username
                or parsed.password or parsed.query or parsed.fragment):
            raise ValueError('invalid_or_missing_QWEN_BASE_URL')
        self.base = raw if raw.endswith('/v1') else raw + '/v1'
        self.root_url = self.base[:-3]
        self.key = os.environ.get('QWEN_API_KEY', '')
        headers = {'ngrok-skip-browser-warning': '1'}
        if self.key:
            headers['Authorization'] = 'Bearer ' + self.key
        self.http = httpx.Client(headers=headers, timeout=D['timeout_seconds'],
                                 trust_env=False, follow_redirects=False)
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        template = (HERE / 'chat_template.jinja').read_text()
        manifest = json.loads((HERE / 'tokenizer_manifest.json').read_text())
        if hashlib.sha256(template.encode()).hexdigest() != manifest['template_sha256']:
            raise ValueError('tokenizer_template_drift')
        self.template = SandboxedEnvironment().from_string(template)
        self.context = manifest['context_window']
        try:
            models = self.call('/models', timeout=15)
            model = next(x for x in models.get('data', []) if x.get('id') == CONFIG['flowrun']['model'])
            if model.get('max_model_len') != self.context:
                raise ValueError('context_mismatch')
        except (StopIteration, KeyError, TypeError, httpx.HTTPError, ValueError):
            self.http.close()
            raise RuntimeError('pinned_Qwen_model_or_context_unavailable') from None
        immutable(self.root / 'server.json', {'id': model['id'], 'max_model_len': self.context})

    def close(self):
        self.http.close()

    def call(self, path, payload=None, timeout=None):
        url = (self.root_url if path == '/tokenize' else self.base) + path
        with self.http.stream('GET' if payload is None else 'POST', url,
                              json=payload, timeout=timeout or D['timeout_seconds']) as response:
            response.raise_for_status()
            body = bytearray()
            for chunk in response.iter_bytes():
                body.extend(chunk)
                if len(body) > 16 * 1024 * 1024:
                    raise ValueError('response_body_limit')
        return strict_json(body.decode(), max_bytes=16 * 1024 * 1024)

    def redact(self, text):
        for secret in (self.base, self.root_url, self.key):
            if secret:
                text = text.replace(secret, '<redacted>')
        return text

    def token_count(self, messages):
        rendered = self.template.render(messages=messages, add_generation_prompt=True, tools=None)
        path = self.root / 'tokens' / (digest(rendered) + '.json')
        quarantine = path.with_suffix('.quarantine.json')
        if quarantine.exists():
            raise ProtocolFailure('quarantined_tokenizer_prompt')
        if path.exists():
            return json.loads(path.read_text())['count']
        ledger_path = path.with_suffix('.attempts.json')
        attempts = json.loads(ledger_path.read_text()) if ledger_path.exists() else []
        while len(attempts) < 3:
            attempts.append({'state': 'reserved'})
            write_json(ledger_path, attempts)
            try:
                result = self.call('/tokenize', {'model': CONFIG['flowrun']['model'], 'prompt': rendered,
                                                'add_special_tokens': False}, timeout=20)
                if (type(result) is not dict or type(result.get('count')) is not int
                        or result['count'] < 0
                        or result.get('max_model_len') != self.context):
                    raise ProtocolFailure('tokenizer_metadata_mismatch')
                immutable(path, {'count': result['count'], 'rendered_sha256': digest(rendered)})
                attempts[-1]['state'] = 'received'
                write_json(ledger_path, attempts)
                return result['count']
            except (ValueError, UnicodeError, ProtocolFailure) as exc:
                immutable(quarantine, {'reason': 'tokenizer_protocol_mismatch', 'error_type': type(exc).__name__})
                attempts[-1]['state'] = 'quarantined'
                write_json(ledger_path, attempts)
                raise ProtocolFailure('tokenizer_protocol_mismatch') from None
            except httpx.HTTPError as exc:
                attempts[-1].update(state='transport_error', error=type(exc).__name__)
                write_json(ledger_path, attempts)
                if len(attempts) < 3:
                    time.sleep((2, 8)[len(attempts) - 1])
        raise SlotFailure('tokenizer_attempt_budget_exhausted')

    def complete(self, request):
        path = self.root / 'calls' / request['slot']
        immutable(path / 'request.json', request)
        if (path / 'quarantine.json').exists():
            raise ProtocolFailure('quarantined_completion_slot')
        if (path / 'response.json').exists():
            return json.loads((path / 'response.json').read_text())
        count = self.token_count(request['messages'])
        limit = D['max_tokens'][request['stage']]
        if count + limit > self.context:
            raise SlotFailure('context_budget_exceeded')
        payload = {'model': CONFIG['flowrun']['model'], 'messages': request['messages'],
                   'temperature': 0, 'top_p': 1, 'seed': request['seed'], 'max_tokens': limit}
        immutable(path / 'wire_request.json', {'payload': payload, 'input_tokens': count})
        ledger = path / 'attempts.json'
        attempts = json.loads(ledger.read_text()) if ledger.exists() else []
        while len(attempts) < D['max_attempts_per_call']:
            attempts.append({'state': 'reserved_usage_unknown'})
            write_json(ledger, attempts)  # reserve before sending; interruption still consumes an attempt
            try:
                raw = self.call('/chat/completions', payload)
            except httpx.HTTPError as exc:
                code = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None
                attempts[-1].update(state='transport_error_usage_unknown',
                                    error=type(exc).__name__, http_status=code)
                write_json(ledger, attempts)
                if code is not None and code not in (408, 429, 500, 502, 503, 504):
                    raise SlotFailure('non_retryable_completion_HTTP_' + str(code)) from None
                if len(attempts) < D['max_attempts_per_call']:
                    time.sleep((2, 8)[len(attempts) - 1])
                continue
            except (ValueError, UnicodeError):
                immutable(path / 'quarantine.json', {'reason': 'unparseable_completion_body'})
                attempts[-1]['state'] = 'quarantined'
                write_json(ledger, attempts)
                raise ProtocolFailure('unparseable_completion_body') from None
            try:
                choice = raw['choices'][0]
                text = choice['message']['content']
                usage = raw['usage']
                if (type(text) is not str or type(usage['prompt_tokens']) is not int
                        or type(usage['completion_tokens']) is not int
                        or usage['prompt_tokens'] != count
                        or not 0 <= usage['completion_tokens'] <= limit):
                    raise ValueError('usage_or_content_mismatch')
                result = {'text': self.redact(text), 'origin': 'qwen_endpoint',
                          'finish_reason': choice.get('finish_reason'),
                          'input_tokens': usage['prompt_tokens'],
                          'output_tokens': usage['completion_tokens']}
            except (KeyError, IndexError, TypeError, ValueError):
                # Retain malformed raw body without endpoint/secrets, quarantine this slot permanently.
                immutable(path / 'quarantine.json', {'raw': self.redact(json.dumps(raw)),
                                                      'reason': 'completion_protocol_mismatch'})
                attempts[-1]['state'] = 'quarantined'
                write_json(ledger, attempts)
                raise ProtocolFailure('completion_protocol_mismatch') from None
            immutable(path / 'response.json', result)
            attempts[-1].update(state='received', input_tokens=result['input_tokens'],
                                output_tokens=result['output_tokens'])
            write_json(ledger, attempts)
            return result
        raise SlotFailure('completion_attempt_budget_exhausted')
