"""Serial ngrok-only chat transport. Never stores or reports endpoint/key values."""
import json
import os
import re
import http.client
import urllib.error
import urllib.parse
import urllib.request


class EndpointError(RuntimeError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        return None  # Never forward endpoint credentials, including to another ngrok host.


class NgrokClient:
    def __init__(self, base=None, model=None, timeout=360, opener=None):
        base = (base or os.environ.get('QWEN_BASE_URL', '')).rstrip('/')
        parsed = urllib.parse.urlsplit(base)
        host = parsed.hostname or ''
        if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise EndpointError('ngrok_https_endpoint_required')
        if not re.fullmatch(r'[a-z0-9.-]+\.(?:ngrok-free\.app|ngrok-free\.dev|ngrok\.app|ngrok\.io)', host):
            raise EndpointError('ngrok_provider_required_no_external_fallback')
        if parsed.path not in ('', '/v1'): raise EndpointError('endpoint_path_must_be_root_or_v1')
        self._base = base if parsed.path == '/v1' else base + '/v1'
        self._key = os.environ.get('QWEN_API_KEY', '')
        self.model = model or os.environ.get('QWEN_MODEL')
        self.timeout = timeout
        self._open = opener or urllib.request.build_opener(NoRedirect()).open

    def _request(self, path, payload=None, api=True):
        headers = {'Content-Type': 'application/json', 'ngrok-skip-browser-warning': '1'}
        if self._key: headers['Authorization'] = 'Bearer ' + self._key
        data = None if payload is None else json.dumps(payload).encode()
        req = urllib.request.Request((self._base if api else self._base[:-3]) + path, data=data, headers=headers)
        try:
            with self._open(req, timeout=15 if payload is None else self.timeout) as response:
                body = response.read(4_000_001)
            if len(body) > 4_000_000: raise EndpointError('response_size_limit')
            return json.loads(body)
        except urllib.error.HTTPError as exc:
            raise EndpointError(f'http_status:{exc.code}') from None
        except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException):
            raise EndpointError('endpoint_connection_failed') from None
        except (ValueError, UnicodeError):
            raise EndpointError('endpoint_invalid_json') from None

    def metadata(self):
        result = self._request('/models')
        models = result.get('data', [])
        if not models: raise EndpointError('no_served_models')
        ids = [r.get('id') for r in models]
        if self.model not in ids:
            if len(ids) != 1: raise EndpointError('set_QWEN_MODEL_to_a_served_model')
            self.model = ids[0]
        item = next(r for r in models if r.get('id') == self.model)
        return dict(provider='ngrok', model=self.model, max_model_len=item.get('max_model_len'))

    def complete(self, messages, max_tokens, seed):
        if not self.model: self.metadata()
        result = self._request('/chat/completions', dict(model=self.model, messages=messages,
            max_tokens=max_tokens, temperature=.2, top_p=.95, seed=seed,
            response_format={'type': 'json_object'}, stream=False))
        choices = result.get('choices', [])
        if not choices: raise EndpointError('no_completion_choices')
        row = choices[0]
        usage = result.get('usage') or {}
        return dict(content=row.get('message', {}).get('content') or '', finish_reason=row.get('finish_reason'),
                    input_tokens=usage.get('prompt_tokens'), output_tokens=usage.get('completion_tokens'),
                    model=result.get('model', self.model), provider='ngrok')

    def tokenize(self, messages):
        # This vLLM deployment exposes the prompt form of /tokenize; its chat
        # form returns HTTP 500 even though /v1/chat/completions is healthy.
        # Qwen2.5's default template is ChatML, so serialize the same messages
        # before asking the server tokenizer for the exact token count.
        chunks = []
        for message in messages:
            role = message.get('role')
            content = message.get('content', '')
            chunks.append(f'<|im_start|>{role}\n{content}<|im_end|>\n')
        prompt = ''.join(chunks) + '<|im_start|>assistant\n'
        result = self._request('/tokenize', dict(model=self.model, prompt=prompt, add_special_tokens=True), api=False)
        count, limit = result.get('count'), result.get('max_model_len')
        if type(count) is not int or type(limit) is not int or count < 0 or limit < 1:
            raise EndpointError('tokenizer_missing_count_or_context_limit')
        return dict(count=count, max_model_len=limit)


def json_object(content):
    text = content.strip()
    if text.startswith('```json') and text.endswith('```'): text = text[7:-3].strip()
    elif text.startswith('```') and text.endswith('```'): text = text[3:-3].strip()
    data = json.loads(text)
    if not isinstance(data, dict): raise ValueError('expected_json_object')
    return data
