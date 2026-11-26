"""Vertex transport contracts; no credentials or remote API calls."""
from types import SimpleNamespace

import pytest

from final.src.models.model import PreparedGeneration, TransportError


@pytest.fixture
def vertex(monkeypatch):
    from final.src.models.vertex import VertexAIModel
    calls = []
    class Chat:
        def __init__(self, **kwargs):
            calls.append(('init', kwargs))
        def get_num_tokens_from_messages(self, messages):
            calls.append(('tokens', messages))
            return 10
        def get_num_tokens(self, text):
            calls.append(('system_tokens', text))
            return 4
        def invoke(self, messages, **kwargs):
            calls.append(('invoke', messages, kwargs))
            return self.reply
    Chat.reply = SimpleNamespace(content='{"inputs":[]}', usage_metadata={
        'input_tokens': 14, 'output_tokens': 5, 'total_tokens': 19,
        'output_token_details': {'reasoning': 2}}, response_metadata={'finish_reason': 'STOP'})
    monkeypatch.setattr(VertexAIModel, '_chat_class', staticmethod(lambda: Chat))
    model = VertexAIModel('fixture-gemini', project='fixture-project', location='global')
    return model, calls, Chat


def test_vertex_uses_native_langchain_and_preserves_checkpoint_response(vertex):
    model, calls, _ = vertex
    messages = [{'role': 'system', 'content': 'Return JSON.'}, {'role': 'user', 'content': 'hello'}]
    result = model.generate(messages, temperature=.7, max_tokens=512, seed=17)
    assert model.model_id == 'vertex/fixture-gemini'
    assert result.text == '{"inputs":[]}' and result.finish_reason == 'stop'
    assert result.usage['prompt_tokens'] == 14 and result.usage['completion_tokens'] == 5
    assert result.usage['total_tokens'] == 19
    assert result.usage['output_token_details']['reasoning'] == 2
    assert result.usage['usage_footer_complete'] is True
    assert result.usage['tokenizer_prompt_tokens'] >= 14
    init = calls[0][1]
    assert init['model'] == 'fixture-gemini' and init['project'] == 'fixture-project'
    assert init['location'] == 'global' and init['max_retries'] == 0
    invocation = next(c for c in calls if c[0] == 'invoke')
    assert invocation[2]['max_output_tokens'] == 512 and invocation[2]['seed'] == 17
    assert invocation[2]['temperature'] == .7
    assert not any(k in init for k in ['base_url', 'api_key'])


def test_vertex_counts_system_context_and_enforces_context(vertex):
    model, _, _ = vertex
    model.context = 100
    with pytest.raises(TransportError, match='PromptExceedsContext'):
        model.prepare_generation([{'role': 'system', 'content': 'context'}], 256)


def test_vertex_native_schema_and_text_blocks(vertex):
    model, calls, chat = vertex
    chat.reply = SimpleNamespace(content=[{'type': 'reasoning', 'text': 'private thought'},
        {'type': 'text', 'text': 'json'}], usage_metadata=None,
        response_metadata={'finish_reason': 'MAX_TOKENS'})
    schema = {'type': 'object', 'properties': {'x': {'type': 'integer'}}}
    result = model.generate_prepared(PreparedGeneration([], 10, 100), temperature=0, seed=1,
        response_format={'type': 'json_schema', 'json_schema': {'name': 'fixture', 'schema': schema}})
    invocation = next(c for c in calls if c[0] == 'invoke')
    assert invocation[2]['response_mime_type'] == 'application/json'
    native_schema = invocation[2]['response_schema']
    assert native_schema['properties']['x']['type_'] == 'INTEGER'
    assert result.text == 'json' and result.finish_reason == 'length'
    assert result.usage['usage_footer_complete'] is False
    assert 'total_tokens' not in result.usage


def test_vertex_resolves_pydantic_defs_before_native_schema(monkeypatch):
    from final.src.models.vertex import VertexAIModel
    from types import SimpleNamespace
    calls=[]
    class Chat:
        def __init__(self, **kwargs): pass
        def invoke(self, messages, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(content='{}', usage_metadata={}, response_metadata={'finish_reason':'STOP'})
    monkeypatch.setattr(VertexAIModel, '_chat_class', staticmethod(lambda: Chat))
    schema={'$defs':{'Arguments':{'type':'object','properties':{'x':{'type':'integer'}},'required':['x']}},
            'type':'object','properties':{'arguments':{'$ref':'#/$defs/Arguments'}},'required':['arguments']}
    VertexAIModel('fixture',project='fixture').generate_prepared(
        PreparedGeneration([],1,64),temperature=0,seed=1,
        response_format={'type':'json_schema','json_schema':{'name':'fixture','schema':schema}})
    native=calls[0]['response_schema']
    assert native['properties']['arguments']['properties']['x']['type_'] == 'INTEGER'


@pytest.mark.parametrize('finish,content', [(None, 'text'), ('STOP', ''), ('SAFETY', '')])
def test_vertex_does_not_accept_incomplete_or_empty_response(vertex, finish, content):
    model, _, chat = vertex
    chat.reply = SimpleNamespace(content=content, usage_metadata=None, response_metadata={'finish_reason': finish})
    with pytest.raises(TransportError) as failure:
        model.generate_prepared(PreparedGeneration([], 1, 100), temperature=0, seed=1)
    assert failure.value.completion_started


def test_vertex_errors_are_sanitized_and_retry_policy_is_explicit(vertex):
    model, _, chat = vertex
    class Busy(Exception):
        code = 429
    def failed(*args, **kwargs):
        raise Busy('private URL credentials')
    chat.invoke = failed
    with pytest.raises(TransportError) as failure:
        model.generate_prepared(PreparedGeneration([], 1, 100), temperature=0, seed=1)
    assert failure.value.http_status == 429 and failure.value.retryable
    assert 'private' not in str(failure.value)


@pytest.mark.parametrize('backend', ['qwen', 'vertex'])
def test_factory_uses_fixed_five_minute_timeout(monkeypatch, backend):
    import final.src.models.model as transport
    import final.src.models.vertex as native
    import final.src.models as models
    monkeypatch.setattr(transport, 'QwenModel', lambda **kw: kw)
    monkeypatch.setattr(native, 'VertexAIModel', lambda **kw: kw)
    selected = models.create_model(backend=backend, model_name='fixture', context=4096)
    assert selected['timeout'] == 300
    assert selected['context'] == 4096
    assert selected['expected_model' if backend == 'qwen' else 'model'] == 'fixture'
    with pytest.raises(TypeError, match='timeout'):
        models.create_model(backend=backend, timeout=60)


def test_vertex_configuration_is_lazy_and_requires_model_project(monkeypatch):
    from final.src.models.vertex import VertexAIModel
    for name in ['VERTEX_MODEL', 'LLM_MODEL', 'VERTEX_PROJECT', 'GOOGLE_CLOUD_PROJECT']:
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(TransportError, match='MissingModel'):
        VertexAIModel()
    with pytest.raises(TransportError, match='MissingProject'):
        VertexAIModel('fixture')
    monkeypatch.setenv('LLM_MODEL', 'fixture')
    monkeypatch.setenv('VERTEX_PROJECT', 'fixture-project')
    model = VertexAIModel()
    assert model.model_id == 'vertex/fixture'


def test_vertex_installed_sdk_builds_native_requests_without_network(monkeypatch):
    """Exercise LangChain and Google proto conversion, not only a chat-shaped stub."""
    from google.auth.credentials import AnonymousCredentials
    from google.cloud.aiplatform_v1beta1.types import GenerateContentResponse
    from langchain_google_vertexai import ChatVertexAI
    from final.src.models.vertex import VertexAIModel
    requests = []
    response = GenerateContentResponse(candidates=[{
        'content': {'role': 'model', 'parts': [{'text': '{"inputs":[]}'}]}, 'finish_reason': 'STOP'}],
        usage_metadata={'prompt_token_count': 14, 'candidates_token_count': 5, 'total_token_count': 19})
    class Prediction:
        def count_tokens(self, request):
            requests.append(('count', request))
            return SimpleNamespace(total_tokens=10)
        def generate_content(self, **kwargs):
            requests.append(('generate', kwargs))
            return response
    monkeypatch.setattr(ChatVertexAI, 'prediction_client', property(lambda self: Prediction()))
    chat = ChatVertexAI(model='gemini-fixture', project='fixture-project', location='global',
                        credentials=AnonymousCredentials(), max_retries=0)
    model = VertexAIModel('gemini-fixture', project='fixture-project')
    model._client = chat
    result = model.generate([{'role': 'system', 'content': 'Return JSON'}, {'role': 'user', 'content': 'hi'}],
                            temperature=.7, max_tokens=256, seed=12)
    assert result.text == '{"inputs":[]}' and result.usage['total_tokens'] == 19
    call = next(row[1] for row in requests if row[0] == 'generate')
    config = call['request'].generation_config
    assert config.max_output_tokens == 256 and config.seed == 12
    assert call['request'].system_instruction.parts[0].text == 'Return JSON'


@pytest.mark.parametrize('backend', ['vertex', 'qwen', 'openrouter'])
def test_cli_selects_backend_without_keepalive(tmp_path, monkeypatch, backend):
    import final.src.modular.run as cli
    import final.src.models as models
    model = SimpleNamespace(model_id=f'{backend}/fixture', backend_name=backend)
    selected = []
    def factory(**kwargs):
        selected.append(kwargs)
        return model
    class Pipeline:
        stage_events = []
        def __init__(self, *args, **kwargs):
            assert kwargs['calls'].model is model
        def run(self, *args):
            return {'scored_tasks': 1, 'arms': {}}
    monkeypatch.setattr(models, 'create_model', factory)
    monkeypatch.setattr(cli, 'BenchmarkPipeline', Pipeline)
    assert cli.main(['--mode', 'run', '--model-backend', backend, '--model-name', 'fixture',
                     '--artifacts', str(tmp_path)]) == 0
    assert selected == [{'backend': backend, 'model_name': 'fixture', 'context': 16384}]
