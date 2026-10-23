"""Single-attempt exact-model HTTP transport. No endpoint in persisted artifacts."""
import json
import hashlib
import os
import re
from pathlib import Path
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit

import httpx
from jinja2.sandbox import SandboxedEnvironment

from .flow_common import immutable, strict_json, digest, write_json

MODEL = 'qwen2.5-coder-32b-instruct'
HERE = Path(__file__).resolve().parent


class TransportStop(RuntimeError):
    pass


class InputOverCap(Exception):
    """Local tokenizer check failed; no completion attempt was reserved or sent."""
    def __init__(self, count, cap=6144):
        super().__init__(f'input_over_cap:{count}>{cap}')
        self.count, self.cap = count, cap


class Client:
    def __init__(self, root, base=None, transport=None, before_request=None, preflight_id='launch0'):
        self.root = Path(root)
        self.before_request = before_request or (lambda: None)
        self.base = (base or os.environ.get('QWEN_BASE_URL', '')).rstrip('/')
        if not self.base:
            raise TransportStop('missing_endpoint_environment')
        if not self.base.endswith('/v1'):
            self.base += '/v1'
        self.http = httpx.Client(transport=transport, timeout=3600, trust_env=False, follow_redirects=False,
                                 headers={'ngrok-skip-browser-warning': '1'})
        self.template = SandboxedEnvironment().from_string((HERE / 'chat_template.jinja').read_text())
        try:
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,32}', preflight_id):
                raise TransportStop('preflight_id')
            preflight = self.root/'preflights'/preflight_id
            if (preflight/'result.json').exists():
                if strict_json((preflight/'result.json').read_text()) != {'model': MODEL, 'context': 8192}:
                    raise TransportStop('preflight_cache_drift')
            else:
                if (preflight/'attempt.json').exists():
                    raise TransportStop('models_attempt_already_consumed_no_retry')
                self.before_request()
                immutable(preflight/'attempt.json', {'state': 'reserved', 'model': MODEL})
                data = self.request('GET', '/models', guarded=True)
                if type(data) is not dict or type(data.get('data')) is not list or any(type(x) is not dict for x in data['data']):
                    raise TransportStop('models_protocol')
                match = next((x for x in data['data'] if x.get('id') == MODEL), None)
                if match is None or match.get('max_model_len') != 8192:
                    raise TransportStop('requested_model_or_context_unavailable')
                immutable(preflight/'result.json', {'model': MODEL, 'context': 8192})
            immutable(self.root / 'server.json', {'model': MODEL, 'context': 8192})
        except BaseException:
            self.http.close()
            raise

    def request(self, method, path, payload=None, raw_folder=None, guarded=False):
        if not guarded:
            self.before_request()
        url = self.base[:-3] + path if path == '/tokenize' else self.base + path
        metadata = {'method': method, 'path': path, 'state': 'started',
                    'started_utc': datetime.now(timezone.utc).isoformat(), 'payload_sha256': digest(payload)}
        metadata_folder = None
        if path != '/chat/completions':
            existing = sorted((self.root/'metadata_calls').glob('*/attempt.json'))
            if any(strict_json(p.read_text()).get('state') == 'started' for p in existing):
                raise TransportStop('metadata_attempt_already_consumed_no_retry')
            metadata_folder = self.root/'metadata_calls'/f'{len(existing):04d}'
            immutable(metadata_folder/'attempt.json', metadata)
            raw_folder = metadata_folder
        started = time.monotonic()
        try:
            with self.http.stream(method, url, json=payload) as response:
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > 2 * 1024 * 1024:
                        raise TransportStop('response_size')
                status = response.status_code
            metadata['http_status'] = status
            response_text = body.decode('utf-8', errors='replace')
            if raw_folder is not None:
                # Preserve every rejected response with a raw hash and secret-safe text.
                text = response_text.replace(self.base, '<endpoint>').replace(self.base[:-3], '<endpoint>')
                host = urlsplit(self.base).hostname
                if host: text = text.replace(host, '<host>')
                text = re.sub(r'https?://[^\s"<>]+', '<url>', text)
                immutable(raw_folder / 'raw_response.json', {'http_status': status,
                          'raw_body_sha256': hashlib.sha256(body).hexdigest(), 'body_redacted': text})
            if status != 200:
                raise TransportStop('HTTP_status_' + str(status))
            result = strict_json(response_text, max_bytes=2 * 1024 * 1024)
            metadata['state'] = 'received'
            metadata['raw_body_sha256'] = hashlib.sha256(body).hexdigest()
            return result
        except (httpx.HTTPError, ValueError, UnicodeError):
            metadata.update(state='failed', reason='transport_or_JSON_failure')
            raise TransportStop('transport_or_JSON_failure') from None
        except TransportStop as exc:
            metadata.update(state='failed', reason=str(exc))
            raise
        finally:
            if path != '/chat/completions':
                metadata['seconds'] = time.monotonic()-started
                write_json(metadata_folder/'attempt.json', metadata)
                self.root.mkdir(parents=True, exist_ok=True)
                with (self.root / 'metadata.jsonl').open('a') as stream:
                    stream.write(json.dumps(metadata) + '\n')

    def token_count(self, messages):
        rendered = self.template.render(messages=messages, add_generation_prompt=True, tools=None)
        folder = self.root / 'tokens' / digest(rendered)
        if (folder / 'result.json').exists():
            return json.loads((folder / 'result.json').read_text())['count']
        if (folder / 'attempt.json').exists():
            raise TransportStop('tokenizer_attempt_already_consumed')
        self.before_request()
        immutable(folder / 'attempt.json', {'state': 'reserved'})
        data = self.request('POST', '/tokenize', {'model': MODEL, 'prompt': rendered, 'add_special_tokens': False}, guarded=True)
        if type(data) is not dict or type(data.get('count')) is not int or data['count'] < 0 or data.get('max_model_len') != 8192:
            raise TransportStop('tokenizer_protocol')
        immutable(folder / 'result.json', {'count': data['count'], 'rendered_hash': digest(rendered)})
        return data['count']

    def complete(self, slot, messages):
        folder = self.root / 'calls' / slot
        immutable(folder / 'request.json', {'model': MODEL, 'messages': messages})
        if (folder / 'response.json').exists():
            result = json.loads((folder / 'response.json').read_text())
            attempt = json.loads((folder / 'attempt.json').read_text())
            if attempt.get('state') != 'received':
                attempt.update(state='received', usage_known=True, input_tokens=result['usage']['prompt_tokens'],
                               output_tokens=result['usage']['completion_tokens'], recovered_saved_response=True)
                write_json(folder / 'attempt.json', attempt)
            return result
        if (folder / 'attempt.json').exists():
            raise TransportStop('completion_attempt_already_consumed_no_retry')
        if len(list((self.root / 'calls').glob('*/attempt.json'))) >= 24:
            raise TransportStop('task_call_cap')
        count = self.token_count(messages)
        if count > 6144:
            raise InputOverCap(count)
        payload = {'model': MODEL, 'messages': messages, 'max_tokens': 1536, 'temperature': 0,
                   'top_p': 1, 'seed': 20261023}
        self.before_request()
        immutable(folder / 'wire_request.json', {'payload': payload, 'input_tokens': count})
        attempt = {'state': 'reserved', 'usage_known': False, 'input_tokens': None, 'output_tokens': None}
        write_json(folder / 'attempt.json', attempt)
        start = time.monotonic()
        try:
            data = self.request('POST', '/chat/completions', payload, raw_folder=folder, guarded=True)
            if type(data) is not dict or type(data.get('usage')) is not dict:
                raise TransportStop('completion_shape')
            usage = data.get('usage', {})
            known = all(type(usage.get(k)) is int and usage[k] >= 0 for k in ('prompt_tokens', 'completion_tokens'))
            attempt.update(usage_known=known, input_tokens=usage.get('prompt_tokens') if known else None,
                           output_tokens=usage.get('completion_tokens') if known else None)
            if not known or usage['prompt_tokens'] != count or usage['completion_tokens'] > 1536:
                raise TransportStop('completion_usage_binding')
            choice = data['choices'][0]
            if choice['message'].get('tool_calls') or type(choice['message'].get('content')) is not str:
                raise TransportStop('unexpected_model_protocol')
            if self.base in choice['message']['content'] or urlsplit(self.base).hostname in choice['message']['content']:
                raise TransportStop('endpoint_in_model_text_quarantined')
            result = {'text': choice['message']['content'], 'finish_reason': choice['finish_reason'],
                      'usage': usage, 'model': data.get('model'), 'origin': 'user_authorized_Qwen32B_endpoint'}
            if data.get('model') != MODEL:
                raise TransportStop('completion_model_identity')
            immutable(folder / 'response.json', result)
            attempt['state'] = 'received'
            return result
        except (KeyError, TypeError, IndexError):
            attempt['state'] = 'protocol_failed'
            raise TransportStop('completion_shape') from None
        except TransportStop as exc:
            attempt.update(state='failed', reason=str(exc))
            raise
        finally:
            attempt['seconds'] = time.monotonic() - start
            write_json(folder / 'attempt.json', attempt)

    def close(self):
        self.http.close()
