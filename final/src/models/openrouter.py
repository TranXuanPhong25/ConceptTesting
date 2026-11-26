"""OpenRouter JSON completions with the shared context and HTTP limits."""
from __future__ import annotations

import os
import time

import httpx
import openai

from . import OPENROUTER_DEFAULT_MODEL
from .core_model import ModelResponse
from .model import QwenModel, TransportError


class OpenRouterModel(QwenModel):
    backend_name = 'openrouter'
    _model_context_field = 'context_length'
    _request_headers = {}

    def __init__(self, model=None, *, context=8192, timeout=300):
        super().__init__(context=context, timeout=timeout, expected_model=model or OPENROUTER_DEFAULT_MODEL)
        self.last_tokenizer_source = 'local_safe_estimate'

    def refresh_configuration(self):
        self.base_url = 'https://openrouter.ai/api/v1'
        self.api_key = os.environ.get('OPENROUTER_API_KEY', '').strip()
        if not self.api_key:
            raise TransportError('configuration', 'MissingOpenRouterAPIKey')

    def tokens(self, messages):
        return self._estimate_tokens(messages)

    def generate_prepared(self, prepared, *, temperature, seed, response_format=None):
        self.refresh_configuration()
        options = {} if response_format is None else {'response_format': response_format}
        if os.environ.get('OPENROUTER_TOP_P'):
            top_p = float(os.environ['OPENROUTER_TOP_P'])
            if not 0 < top_p <= 1:
                raise TransportError('configuration', 'InvalidTopP')
            options['top_p'] = top_p
        if self.model_id == OPENROUTER_DEFAULT_MODEL:
            options['extra_body'] = {
                'reasoning': {'enabled': True},
                'provider': {'only': ['recursive/bf16'], 'allow_fallbacks': False},
            }
        elif os.environ.get('OPENROUTER_REASONING_EFFORT'):
            options['extra_body'] = {
                'reasoning': {'effort': os.environ['OPENROUTER_REASONING_EFFORT']},
            }
        try:
            with self._completion_http_client(time.monotonic()) as http_client:
                client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url,
                                       http_client=http_client, timeout=self.timeout, max_retries=0)
                response = client.chat.completions.create(
                    model=self.model_id, messages=prepared.messages, temperature=temperature,
                    max_tokens=prepared.output_tokens, seed=seed, stream=False, **options,
                )
            choice = next((item for item in response.choices if item.index == 0), None)
            if choice is None or not choice.finish_reason or choice.finish_reason == 'error':
                raise TransportError('completion', 'IncompleteResponse', retryable=True, completion_started=True)
            message = choice.message
            reasoning_details = (message.model_extra or {}).get('reasoning_details')
            if reasoning_details is not None and (
                not isinstance(reasoning_details, list) or any(not isinstance(item, dict) for item in reasoning_details)
            ):
                raise TransportError('completion', 'InvalidReasoningDetails', retryable=True, completion_started=True)
            text = '' if message.content is None else message.content
            if not isinstance(text, str) or not (text.strip() or reasoning_details):
                raise TransportError('completion', 'MissingContent', retryable=True, completion_started=True)
            usage = response.usage.model_dump(exclude_none=True) if response.usage is not None else {}
        except (openai.APIError, httpx.HTTPError, OSError, ValueError, TypeError, AttributeError) as error:
            status = getattr(error, 'status_code', None)
            raise TransportError('completion', 'HTTPError' if status else type(error).__name__,
                http_status=status, retryable=status in (408, 429, 500, 502, 503, 504) if status else True,
                completion_started=True) from None

        usage.update(tokenizer_prompt_tokens=prepared.prompt_tokens,
                     tokenizer_prompt_tokens_source=prepared.prompt_token_source,
                     requested_output_budget=prepared.output_tokens,
                     usage_footer_complete=response.usage is not None)
        return ModelResponse(text, usage, choice.finish_reason, reasoning_details)
