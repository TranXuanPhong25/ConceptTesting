"""Context-aware adapter for the user-selected vLLM model; no URL in artifacts."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from final.core_model import CoreModel, ModelResponse, ModelError


class QwenModel(CoreModel):
    def __init__(self, *, context=8192, timeout=300):
        self.url = os.environ['FINAL_BASE_URL'].rstrip('/')
        self.name = os.environ['FINAL_MODEL']
        self.context, self.timeout = context, timeout

    @property
    def model_id(self):
        return self.name

    def post(self, path, body, *, root=False):
        headers = {'Content-Type': 'application/json', 'ngrok-skip-browser-warning': '1'}
        if os.environ.get('FINAL_API_KEY'):
            headers['Authorization'] = 'Bearer ' + os.environ['FINAL_API_KEY']
        base = self.url[:-3] if root and self.url.endswith('/v1') else self.url
        req = urllib.request.Request(base + path, data=json.dumps(body).encode(), headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read(16 * 1024 * 1024 + 1)
            if len(raw) > 16 * 1024 * 1024:
                raise ModelError('API response too large')
            return json.loads(raw)
        except urllib.error.HTTPError as exc:
            raise ModelError(f'HTTP {exc.code}; endpoint/body suppressed') from None
        except (OSError, ValueError) as exc:
            raise ModelError(type(exc).__name__) from None

    def tokens(self, messages):
        body = self.post('/tokenize', dict(model=self.name, messages=messages,
                    add_generation_prompt=True, chat_template_kwargs={'enable_thinking': False}),root=True)
        count = body.get('count', len(body.get('tokens', [])))
        if not isinstance(count, int) or count <= 0:
            raise ModelError('Tokenizer returned no valid count')
        return count

    def generate(self, messages, *, temperature, max_tokens, seed):
        prompt_tokens = self.tokens(messages)
        budget = min(max_tokens, self.context - prompt_tokens - 64)
        if budget < min(256,max_tokens):
            raise ModelError('Prompt exceeds safe context budget; no completion sent')
        data = self.post('/chat/completions', dict(model=self.name, messages=messages,
                    temperature=temperature, max_tokens=budget, seed=seed, stream=False,
                    chat_template_kwargs={'enable_thinking': False}))
        try:
            choice = data['choices'][0]
            content = choice['message']['content']
            if not isinstance(content, str) or not content.strip():
                raise ValueError()
            usage = dict(data.get('usage', {}), tokenizer_prompt_tokens=prompt_tokens,
                         requested_output_budget=budget)
            return ModelResponse(content, usage, choice.get('finish_reason'))
        except (KeyError, IndexError, TypeError, ValueError):
            raise ModelError('Completion returned no usable text') from None
