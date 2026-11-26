import json

import httpx
import pytest

from final.src.models import OPENROUTER_DEFAULT_MODEL, create_model
from final.src.models.model import TransportError
from final.src.modular.artifacts import ArtifactStore
from final.src.modular.calls import CachedModelCalls, RecordedModelCalls


def test_flint_keeps_reasoning_through_a_saved_turn(tmp_path, monkeypatch):
    monkeypatch.setenv('OPENROUTER_API_KEY', 'fixture-key')
    monkeypatch.setenv('OPENROUTER_MODEL', 'legacy-model')
    model = create_model(backend='openrouter', context=8192)
    assert model.model_id == OPENROUTER_DEFAULT_MODEL and model.timeout == 300
    reasoning = [{'type': 'reasoning.encrypted', 'data': 'opaque', 'index': 0, 'format': 'fixture'}]
    requests = []

    def respond(request):
        assert request.url == 'https://openrouter.ai/api/v1/chat/completions'
        assert request.headers['Authorization'] == 'Bearer fixture-key'
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={
            'id': 'fixture', 'object': 'chat.completion', 'created': 1, 'model': model.model_id,
            'choices': [{'index': 0, 'finish_reason': 'stop', 'message': {
                'role': 'assistant', 'content': '{"inputs":[]}', 'reasoning_details': reasoning,
            }}],
            'usage': {'prompt_tokens': 11, 'completion_tokens': 8, 'total_tokens': 19, 'cost': 0},
        })

    monkeypatch.setattr(model, '_completion_http_client', lambda _: httpx.Client(transport=httpx.MockTransport(respond)))
    store = ArtifactStore(tmp_path)
    calls = RecordedModelCalls(model, store)
    messages = [{'role': 'user', 'content': 'Generate inputs.'}]
    sampling = {'temperature': .7, 'max_tokens': 1024, 'seed': 5}
    response = calls.complete(0, 'initial', messages, **sampling)
    assert response.reasoning_details == reasoning
    assert response.usage['cost'] == 0
    assert response.usage['tokenizer_prompt_tokens_source'] == 'local_safe_estimate'
    cached = CachedModelCalls(ArtifactStore(tmp_path, read_only=True)).complete(0, 'initial', messages, **sampling)
    assert cached == response

    followup = [*messages, cached.assistant_message(), {'role': 'user', 'content': 'Revise the inputs.'}]
    response_format = {'type': 'json_object'}
    calls.complete(0, 'followup', followup, response_format=response_format, **sampling)
    assert len(requests) == 2
    for request in requests:
        assert request['model'] == OPENROUTER_DEFAULT_MODEL and request['max_tokens'] == 1024
        assert request['reasoning'] == {'enabled': True}
        assert request['provider'] == {'only': ['recursive/bf16'], 'allow_fallbacks': False}
    assert requests[1]['messages'][1]['reasoning_details'] == reasoning
    assert requests[1]['response_format'] == response_format
    assert all('fixture-key' not in path.read_text() for path in tmp_path.rglob('*.json'))


@pytest.mark.parametrize(('status', 'retryable'), [(401, False), (429, True)])
def test_openrouter_http_errors_are_sanitized(monkeypatch, status, retryable):
    monkeypatch.setenv('OPENROUTER_API_KEY', 'fixture-key')
    model = create_model(backend='openrouter')

    def respond(_):
        return httpx.Response(status, json={'error': {'message': 'fixture-key'}})

    monkeypatch.setattr(model, '_completion_http_client', lambda _: httpx.Client(transport=httpx.MockTransport(respond)))
    with pytest.raises(TransportError) as failure:
        model.generate([{'role': 'user', 'content': 'hello'}], temperature=0, max_tokens=256, seed=1)
    assert failure.value.http_status == status and failure.value.retryable == retryable
    assert 'fixture-key' not in str(failure.value)


def test_luna_low_and_top_p_are_sent_in_request(monkeypatch):
    monkeypatch.setenv('OPENROUTER_API_KEY', 'fixture-key')
    monkeypatch.setenv('OPENROUTER_REASONING_EFFORT', 'low')
    monkeypatch.setenv('OPENROUTER_TOP_P', '.95')
    model = create_model(backend='openrouter', model_name='openai/gpt-6-luna')
    requests = []

    def respond(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={
            'id': 'fixture', 'object': 'chat.completion', 'created': 1, 'model': model.model_id,
            'choices': [{'index': 0, 'finish_reason': 'stop', 'message': {
                'role': 'assistant', 'content': 'def f(x): return x',
            }}],
            'usage': {'prompt_tokens': 11, 'completion_tokens': 8, 'total_tokens': 19},
        })

    monkeypatch.setattr(model, '_completion_http_client', lambda _: httpx.Client(transport=httpx.MockTransport(respond)))
    model.generate([{'role': 'user', 'content': 'Implement f.'}], temperature=.8, max_tokens=1024, seed=17)
    assert requests[0]['reasoning'] == {'effort': 'low'}
    assert requests[0]['top_p'] == .95
    assert 'stop' not in requests[0]
