"""Native Vertex AI through LangChain, compatible with recorded model calls."""
from __future__ import annotations

import os

from langchain_core.messages import convert_to_messages
from langsmith import tracing_context

from final.src.models.core_model import CoreModel, ModelResponse
from .model import PreparedGeneration, TransportError


def transport_error(operation, error, *, completion_started=False):
    code = getattr(error, 'code', None)
    if callable(code):
        code = code()
    try:
        status = int(code) if code is not None else None
    except (TypeError, ValueError):
        status = None
    return TransportError(operation, type(error).__name__, http_status=status,
        retryable=status in (408, 429, 500, 502, 503, 504) or isinstance(error, (TimeoutError, ConnectionError, OSError)),
        completion_started=completion_started)


class VertexAIModel(CoreModel):
    backend_name = 'vertex'

    def __init__(self, model=None, *, project=None, location=None, context=8192, timeout=180):
        self.name = model or os.environ.get('VERTEX_MODEL') or os.environ.get('LLM_MODEL')
        self.project = project or os.environ.get('VERTEX_PROJECT') or os.environ.get('GOOGLE_CLOUD_PROJECT')
        self.location = location or os.environ.get('VERTEX_LOCATION') or os.environ.get('GOOGLE_CLOUD_LOCATION', 'global')
        if not self.name:
            raise TransportError('configuration', 'MissingModel')
        if not self.project:
            raise TransportError('configuration', 'MissingProject')
        self.context, self.timeout = context, timeout
        self._client = None

    @property
    def model_id(self):
        return 'vertex/' + self.name

    def runtime_dependencies(self):
        return ('langchain-google-vertexai', 'google-cloud-aiplatform', 'google-auth')

    @staticmethod
    def _chat_class():
        try:
            from langchain_google_vertexai import ChatVertexAI
        except ImportError:
            raise TransportError('configuration', 'MissingVertexDependency') from None
        return ChatVertexAI

    def _chat(self):
        if self._client is None:
            options = dict(model=self.name, project=self.project, location=self.location,
                           timeout=self.timeout, max_retries=0)
            thinking = os.environ.get('LLM_THINKING_BUDGET')
            if thinking is not None:
                options['thinking_budget'] = int(thinking)
            self._client = self._chat_class()(**options)
        return self._client

    def tokens(self, messages):
        try:
            with tracing_context(enabled=False):
                chat = self._chat()
                count = chat.get_num_tokens_from_messages(convert_to_messages(messages))
                # ChatVertexAI 3.2.5 counts contents but omits the separate system instruction.
                system = '\n\n'.join(m['content'] for m in messages if m['role'] == 'system')
                if system:
                    count += chat.get_num_tokens(system)
                if type(count) is not int or count <= 0:
                    raise TransportError('tokenize', 'InvalidTokenCount')
                return count + 32  # Reserve framing between contents and the system instruction.
        except TransportError:
            raise
        except Exception as error:
            raise transport_error('tokenize', error) from None

    def check_endpoint(self):
        self.tokens([{'role': 'user', 'content': 'ping'}])
        return dict(model=self.model_id, context=self.context, backend='vertex', check='count_tokens')

    def prepare_generation(self, messages, max_tokens):
        count = self.tokens(messages)
        budget = min(max_tokens, self.context - count - 64)
        if budget < min(256, max_tokens):
            raise TransportError('tokenize', 'PromptExceedsContext')
        return PreparedGeneration(messages, count, budget)

    def generate_prepared(self, prepared, *, temperature, seed, response_format=None):
        options = dict(temperature=temperature, seed=seed, max_output_tokens=prepared.output_tokens)
        if response_format is not None:
            kind = response_format.get('type')
            if kind == 'json_schema' and isinstance(response_format.get('json_schema', {}).get('schema'), dict):
                # Vertex's protobuf Schema rejects Pydantic JSON Schema keys such as
                # $defs/$ref. Use the installed LangChain converter, which resolves
                # references and preserves supported constraints before serialization.
                try:
                    from langchain_google_vertexai.functions_utils import _dict_to_gapic_schema
                    native = _dict_to_gapic_schema(
                        response_format['json_schema']['schema'], pydantic_version='v2')
                    # LangChain expects a dict; protobuf field names must be snake_case
                    # throughout unions too, where its own dict converter does not recurse.
                    native_schema = type(native).to_dict(native, use_integers_for_enums=False,
                        preserving_proto_field_name=True, always_print_fields_with_no_presence=False)
                except (ImportError, KeyError, TypeError, ValueError) as error:
                    raise TransportError('configuration', 'InvalidVertexResponseSchema') from error
                options.update(response_mime_type='application/json', response_schema=native_schema)
            elif kind == 'json_object':
                options['response_mime_type'] = 'application/json'
            else:
                raise TransportError('configuration', 'UnsupportedResponseFormat')
        started = False
        try:
            with tracing_context(enabled=False):
                chat = self._chat()
                started = True
                result = chat.invoke(prepared.messages, **options)
        except TransportError:
            raise
        except Exception as error:
            raise transport_error('completion', error, completion_started=started) from None
        content = result.content
        if isinstance(content, list):
            content = ''.join(p['text'] for p in content if isinstance(p, dict)
                              and p.get('type') == 'text' and isinstance(p.get('text'), str) and not p.get('thought'))
        raw_finish = (result.response_metadata or {}).get('finish_reason')
        finish = getattr(raw_finish, 'name', str(raw_finish)).upper() if raw_finish is not None else None
        if finish is None or not isinstance(content, str) or not content.strip():
            raise TransportError('completion', 'IncompleteResponse' if finish is None else 'EmptyResponse',
                                 retryable=finish is None, completion_started=True)
        if finish not in ('STOP', 'MAX_TOKENS'):
            raise TransportError('completion', 'UnexpectedFinishReason', completion_started=True)
        usage = dict(result.usage_metadata or {})
        for native, common in [('input_tokens', 'prompt_tokens'), ('output_tokens', 'completion_tokens')]:
            if type(usage.get(native)) is int:
                usage[common] = usage[native]
        usage.update(tokenizer_prompt_tokens=prepared.prompt_tokens, requested_output_budget=prepared.output_tokens,
            prompt_count_method='vertex_count_tokens_plus_system_and_framing',
            usage_footer_complete=all(type(usage.get(k)) is int for k in ('prompt_tokens', 'completion_tokens', 'total_tokens')))
        return ModelResponse(content, usage, 'stop' if finish == 'STOP' else 'length')

    def generate(self, messages, *, temperature, max_tokens, seed):
        return self.generate_prepared(self.prepare_generation(messages, max_tokens), temperature=temperature, seed=seed)
