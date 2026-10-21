"""Authored CPU controls of our diagnostic, no model/paper simulation."""
import copy
import json
from pathlib import Path

import httpx
import pytest

from . import d1, flow_tools, fixture_oracles
from .d1_client import Client, TransportStop
from .flow_common import immutable, digest


def test_catalog_projection_and_authored_private_truths():
    data = d1.read(d1.HERE / 'd1_packets.json')
    projection = set(data['shared_policy']['public_catalog_projection'])
    assert not projection & set(data['shared_policy']['excluded_catalog_fields'])
    assert len(data['episodes']) == 8
    private = d1.read(d1.HERE / 'd1_evaluator_private.json')
    cases = {x['fixture_id']: x for x in d1.pilot_fixtures.cases()}
    for p in private['episodes']:
        if p['hidden_witness']:
            expected = fixture_oracles.expected(cases[p['fixture']], p['hidden_witness'])
            assert expected == ('ok', d1.typed_value(d1.parse_literal(p['hidden_required_output'], output=True)))
    assert len(private['planned_denominators']['no_supplied_revealing_row_bug_episodes']) == 4


@pytest.mark.parametrize('text', ['{"claims":[],"claims":[]}', '{"claims":[],"note":NaN}', 'prefix {"claims":[]}', '```python\n{}\n```'])
def test_no_response_recovery(text):
    with pytest.raises(ValueError): d1.decode(text, 'stop')


def test_entire_json_fence_and_claim_uniqueness():
    assert d1.decode('```json\n{"claims":[]}\n```', 'stop') == {'claims': []}
    claim = {'id': 'h', 'kind': 'mismatch', 'statement': 'candidate', 'stance': 'candidate', 'evidence': []}
    with pytest.raises(ValueError, match='claim_ids'):
        d1.decode(json.dumps({'claims': [claim, claim]}), 'stop')


def test_single_attempt_transport_usage_and_no_retry(tmp_path):
    calls = []
    def handler(request):
        calls.append(request.url.path)
        if request.url.path == '/v1/models':
            return httpx.Response(200, json={'data': [{'id': 'qwen2.5-coder-32b-instruct', 'max_model_len': 8192}]})
        if request.url.path == '/tokenize':
            return httpx.Response(200, json={'count': 40, 'max_model_len': 8192})
        return httpx.Response(503, text='not persisted')
    client = Client(tmp_path, base='http://localhost/v1', transport=httpx.MockTransport(handler))
    with pytest.raises(TransportStop, match='HTTP_status_503'):
        client.complete('a', [{'role': 'user', 'content': 'hello'}])
    with pytest.raises(TransportStop, match='already_consumed'):
        client.complete('a', [{'role': 'user', 'content': 'hello'}])
    assert calls.count('/v1/chat/completions') == 1
    assert d1.read(tmp_path / 'calls/a/attempt.json')['usage_known'] is False
    assert all('localhost' not in p.read_text() for p in tmp_path.rglob('*.json'))


def test_usage_mismatch_stays_known_but_stops(tmp_path):
    def handler(request):
        if request.url.path.endswith('/models'):
            return httpx.Response(200, json={'data': [{'id': 'qwen2.5-coder-32b-instruct', 'max_model_len': 8192}]})
        if request.url.path == '/tokenize':
            return httpx.Response(200, json={'count': 40, 'max_model_len': 8192})
        return httpx.Response(200, json={'usage': {'prompt_tokens': 41, 'completion_tokens': 2},
            'model': 'qwen2.5-coder-32b-instruct', 'choices': [{'message': {'content': '{"claims":[]}'}, 'finish_reason': 'stop'}]})
    client = Client(tmp_path, base='http://localhost', transport=httpx.MockTransport(handler))
    with pytest.raises(TransportStop, match='usage_binding'):client.complete('a', [{'role': 'user', 'content': 'hi'}])
    assert d1.read(tmp_path / 'calls/a/attempt.json')['usage_known'] is True
    assert '{"claims":[]}' in d1.read(tmp_path / 'calls/a/raw_response.json')['body_redacted'] or 'claims' in d1.read(tmp_path / 'calls/a/raw_response.json')['body_redacted']


def test_cached_response_recovers_usage_without_new_request(tmp_path):
    count = []
    def handler(request):
        if request.url.path.endswith('/models'):
            return httpx.Response(200, json={'data': [{'id': 'qwen2.5-coder-32b-instruct', 'max_model_len': 8192}]})
        if request.url.path == '/tokenize':return httpx.Response(200, json={'count': 40, 'max_model_len': 8192})
        count.append(1)
        return httpx.Response(200, json={'usage': {'prompt_tokens': 40, 'completion_tokens': 2},
            'model': 'qwen2.5-coder-32b-instruct', 'choices': [{'message': {'content': '{"claims":[]}'}, 'finish_reason': 'stop'}]})
    c = Client(tmp_path, base='http://localhost', transport=httpx.MockTransport(handler))
    c.complete('a', [{'role': 'user', 'content': 'hi'}])
    path = tmp_path / 'calls/a/attempt.json'; data = d1.read(path);data.update(state='reserved', usage_known=False);path.write_text(json.dumps(data))
    c.complete('a', [{'role': 'user', 'content': 'hi'}])
    assert len(count) == 1 and d1.read(path)['usage_known']


def test_data_measurements_and_malformed_sibling_are_preserved(tmp_path):
    case = d1.pilot_fixtures.cases()[1]
    session = d1.Session(d1.task(case), tmp_path, arm='CPU')
    session.begin_round()
    malformed = {'tool': 'inspect_data', 'names': []}
    nested = malformed
    for _ in range(30):nested['extra'] = {}; nested = nested['extra']
    assert session.act(malformed)['status'] == 'refused'
    feedback = d1.compact(session.view(session.act({'tool': 'inspect_data', 'names': ['xs']})))
    assert feedback['status'] == 'ok' and feedback['names'][0]['name'] == 'xs'
    assert feedback['reaching_definitions'] == 'unknown'


class Scripted:
    def __init__(self):self.calls = []
    def complete(self, slot, messages):
        self.calls.append((slot, messages))
        arm = slot.split('__')[1]; turn = int(slot.split('__')[2])
        value = {'claims': []}
        query = {'action': {'tool': 'replay_input', 'input': '([2, 2],)'}, 'claim': None,
                 'prediction': 'CPU control', 'why': 'test ledger binding'}
        if turn < 3 and not (arm == 'concept_committed' and turn == 2):value['queries'] = [query]
        if arm == 'concept_committed' and turn == 1:value['later_queries'] = [query]
        if turn == 3:value['final_inputs'] = []
        return {'text': json.dumps(value), 'finish_reason': 'stop', 'origin': 'authored_CPU_only'}


def test_end_to_end_freeze_controls_commitment_and_resume(tmp_path):
    d1.prepare(tmp_path)
    for ep in ('E1', 'E2', 'E3', 'E4', 'E5', 'E6', 'E7', 'E8'):
        row = d1.read(tmp_path / 'prepared' / (ep + '.json'))
        c = d1.messages(row, 'concept_adaptive', 1, [])
        g = d1.messages(row, 'generic_adaptive', 1, [])
        cc = json.loads(c[1]['content'])['context']; gg = json.loads(g[1]['content'])['context']
        assert cc['initial_hypothesis'] == gg['initial_hypothesis']
        assert cc['initial_observations'] == gg['initial_observations']
        assert cc['injected_observation'] is None and 'concept' not in gg
        assert not {'minimal_contrast', 'tool_gap_example', 'implementation'} & cc['concept'].keys()
        assert 'source_fixture' not in cc and 'hidden_required_output' not in c[1]['content']
        assert set(cc['tool_protocol']['schemas']) == {'inspect_flow', 'inspect_data', 'replay_input'}
    private = d1.read(d1.HERE / 'd1_evaluator_private.json')
    for p in private['episodes']:
        row = d1.read(tmp_path / 'prepared' / (p['id'] + '.json'))
        native = row['injection']
        assert native['native_checked']
        assert d1.typed_value(d1.parse_literal(native['output'], output=True)) == d1.typed_value(d1.parse_literal(p['injection_expected_native'], output=True))
    client = Scripted(); d1.run(client, tmp_path, check_quota=False)
    assert len(client.calls) == 72
    d1.verify(tmp_path)
    d1.run(client, tmp_path, check_quota=False); assert len(client.calls) == 72
    for episode in ('E1', 'E7'):
        first = d1.read(tmp_path / 'events' / (episode + '__concept_committed__1.json'))
        second = d1.read(tmp_path / 'events' / (episode + '__concept_committed__2.json'))
        assert first['reply']['later_queries']
        assert second['feedback'][0]['input'] == '([2, 2],)'
    p = next((tmp_path / 'artifacts').glob('*.json'));p.write_text('{}')
    with pytest.raises(AssertionError, match='generation_drift'):d1.verify(tmp_path)


def test_worker_unknown_attempt_never_relaunches(tmp_path, monkeypatch):
    from . import isolated
    job = {'rows': []}
    folder = tmp_path / 'job';folder.mkdir()
    identity = digest({'job': job, 'script': '/nonexistent', 'interpreter': isolated.CONFIG['V4_PYTHON']})
    immutable(folder / 'attempt.json', {'identity': identity, 'launched': None, 'state': 'reserved'})
    monkeypatch.setattr(isolated.subprocess, 'Popen', lambda *a, **k: (_ for _ in ()).throw(AssertionError('must not launch')))
    assert isolated.run_once(Path('/nonexistent'), job, folder)['status'] == 'unresolved'
