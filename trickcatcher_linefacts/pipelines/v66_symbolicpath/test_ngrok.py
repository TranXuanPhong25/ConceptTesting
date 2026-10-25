"""Transport/integration regression tests with authored fixtures, no real model calls."""
import ast
import io
import json
import urllib.error
import urllib.request
import http.client
import importlib

import pytest

from .bindings import resolve
from .construction import construct, replay
from .hypotheses import catalog
from .ngrok_client import EndpointError, NgrokClient, NoRedirect
from .ngrok_run import generate_case, compact_arm, call, write_new
from .public_adapter import adapt, NORMALIZED_COMPARATOR
from .test_pathfault import CONFIG


WRAPPED = '''import copy
class Solution:
    def count(self, xs, k):
        if k > 0 and len(xs) == k + 2:
            return len(set(xs))
        return 0
def count(xs, k):
    """Count all occurrences when k is positive and length is k plus two; otherwise return zero."""
    return Solution().count(*copy.deepcopy((xs, k)))
'''


def test_solution_wrapper_keeps_original_coordinates_and_replay():
    rows, _ = catalog(WRAPPED, 'count')
    h = next(r for r in rows if r['before'] == 'len(set(xs))')
    assert h['span'][0] == 5
    report = construct(WRAPPED, 'count', [([1, 2], 5)], h, CONFIG)
    assert report['inputs'], report
    assert report['inputs'][0]['observations']['put']['site_events']


def test_stateful_constructor_is_not_silently_inlined():
    source = WRAPPED.replace('class Solution:', 'class Solution:\n    def __init__(self):\n        self.counter = 1')
    fn, bound = resolve(ast.parse(source), 'count')
    assert not bound and fn.lineno > 5


def test_normalized_public_comparator_is_checked_not_executed():
    base = NORMALIZED_COMPARATOR + '\ndef check(candidate):\n    assert _heldout_same(candidate([1, 2], 5), 0, 0.0)\n'
    request, skipped = adapt(WRAPPED, 'count', base, 'fixture')
    assert request['public_examples'] == [dict(arguments='([1, 2], 5)', expected='0')]
    assert not skipped
    bad = base.replace('return x == y', 'return True')
    with pytest.raises(ValueError, match='unsupported_public_test_module'):
        adapt(WRAPPED, 'count', bad, 'fixture')


def test_original_only_replay_supports_generator_feedback():
    result = replay('def f(x):\n    return x + 1\n', 'f', (2,), None)
    assert result['put']['output'] == {'type': 'int', 'repr': '3'}
    assert 'alternative' not in result


def test_transport_refuses_paid_provider_fallback_and_redacts_connection_errors():
    with pytest.raises(EndpointError, match='ngrok_provider_required'):
        NgrokClient(base='https://openrouter.ai')
    def fail(*args, **kwargs):
        raise urllib.error.URLError('sensitive-host-placeholder')
    client = NgrokClient(base='https://' + 'fixture.' + 'ngrok-free.app', opener=fail)
    with pytest.raises(EndpointError) as error:
        client.metadata()
    assert str(error.value) == 'endpoint_connection_failed'


def test_transport_discovers_actual_model_and_sends_bounded_json_request(monkeypatch):
    monkeypatch.setenv('QWEN_API_KEY', 'unit-test-token')
    sent = []
    def opener(request, timeout):
        sent.append(request)
        result = {'data': [{'id': 'served-qwen', 'max_model_len': 8192}]} if request.data is None else {
            'model': 'served-qwen', 'choices': [{'message': {'content': '{"tests": []}'}, 'finish_reason': 'stop'}],
            'usage': {'prompt_tokens': 10, 'completion_tokens': 4}}
        return io.BytesIO(json.dumps(result).encode())
    c = NgrokClient(base='https://' + 'fixture.' + 'ngrok-free.app', model='stale-alias', opener=opener)
    assert c.metadata() == dict(provider='ngrok', model='served-qwen', max_model_len=8192)
    completion = c.complete([{'role': 'user', 'content': 'unit fixture'}], 64, 7)
    assert completion['input_tokens'] == 10 and completion['output_tokens'] == 4
    body = json.loads(sent[-1].data)
    assert body['model'] == 'served-qwen' and body['max_tokens'] == 64
    assert 'unit-test-token' not in json.dumps(completion)


def test_generator_resume_does_not_repeat_completed_calls_and_preserves_evidence(tmp_path):
    class FixtureClient:
        # Tests cache/round orchestration only. These are not model-generated research artifacts.
        model = 'unit-fixture'
        calls = 0
        def tokenize(self, messages): return dict(count=100, max_model_len=8192)
        def complete(self, messages, max_tokens, seed):
            self.calls += 1
            data = json.loads(messages[-1]['content'])
            value = {'hypotheses': [], 'summary': 'unit fixture'} if 'eligible_sites' in data else {
                'tests': [{'arguments': '(2,)', 'expected': '3'}], 'reason': 'unit fixture'}
            return dict(content=json.dumps(value), finish_reason='stop', input_tokens=1, output_tokens=1,
                        model=self.model, provider='ngrok')
    client = FixtureClient()
    request = dict(case_id='fixture', source='def f(x):\n    return x + 1\n', entry='f',
                   public_examples=[dict(arguments='(1,)', expected='2')])
    first = generate_case(client, request, tmp_path / 'case', CONFIG)
    assert client.calls == 13
    second = generate_case(client, request, tmp_path / 'case', CONFIG)
    assert client.calls == 13 and first == second
    cpu = json.loads((tmp_path / 'case/cpu_prepared.json').read_text())['result']
    concept, raw = compact_arm(cpu, 'concept'), compact_arm(cpu, 'equal_evidence_raw')
    assert concept['evidence'] == raw['evidence']


def test_attempts_are_persisted_before_dispatch_and_capped(tmp_path):
    folder = tmp_path / 'slot'
    class Broken:
        model = 'unit-fixture'
        calls = 0
        def tokenize(self, messages): return dict(count=100, max_model_len=8192)
        def complete(self, *args, **kwargs):
            self.calls += 1
            assert (folder / 'request.json').exists()
            assert (folder / f'attempt_{self.calls:02d}.json').exists()
            raise EndpointError('endpoint_connection_failed')
    c = Broken()
    for _ in range(4):
        with pytest.raises(EndpointError): call(c, folder, [], 'probe', 1, 32)
    assert c.calls == 2


def test_atomic_publication_does_not_leave_a_partial_destination(tmp_path, monkeypatch):
    runner = importlib.import_module(__package__ + '.ngrok_run')
    original = runner.json.dump
    def interrupt(value, stream, **kwargs):
        stream.write('{"partial":')
        raise RuntimeError('authored interruption')
    monkeypatch.setattr(runner.json, 'dump', interrupt)
    with pytest.raises(RuntimeError): write_new(tmp_path / 'record.json', {'valid': True})
    assert not (tmp_path / 'record.json').exists() and not list(tmp_path.glob('.pending-*'))
    monkeypatch.setattr(runner.json, 'dump', original)
    write_new(tmp_path / 'record.json', {'valid': True})
    with pytest.raises(FileExistsError): write_new(tmp_path / 'record.json', {'valid': False})
    assert json.loads((tmp_path / 'record.json').read_text()) == {'valid': True}


def test_inputs_only_has_exactly_the_displayed_witnesses():
    rows = [dict(rank=i, hypothesis={}, base_status='unknown', construction_status='ok', limitations=[],
                 inputs=[dict(arguments=repr((i, j)), predicted_put={}, predicted_alternative={}, put_path=[],
                              alternative_path=[], verification='unit', domain={}) for j in range(3)]) for i in range(5)]
    prepared = {'prompts': {'concept': {'evidence': rows}, 'inputs_only': {'inputs': ['all hidden inputs']}}}
    shown = compact_arm(prepared, 'concept')['evidence']
    assert compact_arm(prepared, 'inputs_only')['inputs'] == [x['arguments'] for h in shown for x in h['inputs']]
    assert len(compact_arm(prepared, 'inputs_only')['inputs']) == 6


def test_redirects_never_forward_credentials():
    request = urllib.request.Request('https://' + 'fixture.' + 'ngrok-free.app/v1/models', headers={'Authorization': 'unit'})
    assert NoRedirect().redirect_request(request, None, 302, 'moved', {}, 'https://openrouter.ai') is None


def test_incomplete_http_response_is_sanitized():
    def broken(*args, **kwargs): raise http.client.IncompleteRead(b'private-placeholder', 100)
    client = NgrokClient(base='https://' + 'fixture.' + 'ngrok-free.app', opener=broken)
    with pytest.raises(EndpointError, match='^endpoint_connection_failed$'): client.metadata()


def test_received_response_survives_interrupted_final_publication(tmp_path, monkeypatch):
    runner = importlib.import_module(__package__ + '.ngrok_run')
    class Fixture:
        model = 'unit'
        calls = 0
        def tokenize(self, messages): return dict(count=100, max_model_len=8192)
        def complete(self, *args, **kwargs):
            self.calls += 1
            return dict(content='{"tests": []}', finish_reason='stop', input_tokens=1, output_tokens=1, model=self.model, provider='ngrok')
    c = Fixture(); original = runner.write_new
    def interrupted(path, value):
        if path.name == 'response.json': raise RuntimeError('authored interruption')
        return original(path, value)
    monkeypatch.setattr(runner, 'write_new', interrupted)
    with pytest.raises(RuntimeError): call(c, tmp_path, [], 'probe', 1, 32)
    monkeypatch.setattr(runner, 'write_new', original)
    assert call(c, tmp_path, [], 'probe', 1, 32)['value'] == {'tests': []}
    assert c.calls == 1


def test_context_overflow_never_dispatches_a_chat_request(tmp_path):
    class TooLong:
        model = 'unit'
        def tokenize(self, messages): return dict(count=8100, max_model_len=8192)
        def complete(self, *args, **kwargs): raise AssertionError('must not dispatch')
    record = call(TooLong(), tmp_path, [], 'probe', 1, 1536)
    assert record['error'] == 'context_budget_exceeded' and not list(tmp_path.glob('attempt_??.json'))


def test_tokenization_uses_root_endpoint_and_preserves_exact_context_count():
    seen = []
    def opener(request, timeout):
        seen.append(request)
        return io.BytesIO(b'{"count": 123, "max_model_len": 8192}')
    client = NgrokClient(base='https://' + 'fixture.' + 'ngrok-free.app/v1', model='unit', opener=opener)
    assert client.tokenize([{'role': 'user', 'content': 'unit'}]) == dict(count=123, max_model_len=8192)
    assert urllib.request.urlparse(seen[0].full_url).path == '/tokenize'
    body = json.loads(seen[0].data)
    assert 'messages' not in body and '<|im_start|>user' in body['prompt'] and '<|im_start|>assistant' in body['prompt']
