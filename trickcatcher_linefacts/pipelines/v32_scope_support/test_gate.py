"""Authored CPU interface controls, not Qwen/paper evidence."""
import copy
import json

import httpx
import pytest

from . import fixtures, gate, diagnostic_client, controller
from .common import task_for, digest
from .cpu_contracts import authored_contract
from .interfaces import control_contexts, envelope, parse, messages


def case(uid):
    return next(c for c in fixtures.cases() if c['fixture_id'] == uid)


def metadata(uid):
    task = task_for(case(uid))
    return {'decision': 'unknown' if uid == 'f13' else 'proposed', 'spec_quote': task['spec'],
            'input_domain': task['spec'], 'required_relation': '' if uid == 'f13' else 'Authored CPU full relation',
            'uncertainty': 'Suitable is undefined' if uid == 'f13' else ''}


@pytest.mark.parametrize('text,kind,body,framing', [
    (' {"x":1} ', 'json', '{"x":1}', 'bare'),
    ('```json\n{"x":1}\n```', 'json', '{"x":1}', 'single_json_fence'),
    (' ```Python\ndef trigger(arguments):\n return True\n```\n', 'code',
     'def trigger(arguments):\n return True', 'single_python_fence')])
def test_entire_envelope_only(text, kind, body, framing):
    assert envelope(text, kind) == (body, framing)


@pytest.mark.parametrize('text', ['Here is JSON:\n```json\n{}\n```', '```json\n{}\n``` extra',
                                  '```json\n{}\n```\n```json\n{}\n```', '```python\n{}\n```',
                                  '{}\n```json\n{}\n```'])
def test_envelopes_never_extract_or_merge(text):
    with pytest.raises(ValueError):
        envelope(text, 'json')


def test_no_duplicate_keys_or_nonfinite_json_and_no_field_swapping():
    task = task_for(case('f02'))
    for raw in ('{"x":1,"x":2}', '{"x":NaN}'):
        with pytest.raises(ValueError):
            parse('meta', raw, task)
    with pytest.raises(ValueError):
        parse('predicate', 'Prose describing a Python predicate', task)
    m = metadata('f02'); m['input_domain'] = 'Python'
    with pytest.raises(ValueError, match='quote_provenance'):
        parse('meta', json.dumps(m), task)
    m = metadata('f13'); m['uncertainty'] = ''
    with pytest.raises(ValueError, match='uncertainty'):
        parse('meta', json.dumps(m), task_for(case('f13')))


def test_separated_spec_code_contexts_and_code_only_contract():
    task = task_for(case('f02'))
    for stage in ('meta', 'predicate'):
        context = json.loads(messages(stage, task, metadata=metadata('f02'))[1]['content'])['context']
        assert 'code' not in context and 'base_tests' not in context
    context = json.loads(messages('behavior', task)[1]['content'])['context']
    assert set(context) == {'code', 'syntax'} and task['spec'] not in context['code']
    code = authored_contract(case('f02'))['value']['predicate_source']
    parsed, payload, _ = parse('predicate', '```python\n' + code.rstrip() + '\n```', task)
    assert parsed == {'source': payload}


def test_raw_text_control_preserved_despite_parse_and_semantic_failure():
    task = task_for(case('f02')); text = 'uncompilable raw model text\n```python\n???\n```'
    record = {'state': 'failed', 'reason': 'predicate_syntax', 'request_hash': 'frozen_request',
              'response': {'origin': 'qwen_endpoint', 'text': text}}
    rows = [{'arguments': {'xs': [1, 1]}, 'execution': {'status': 'ok', 'output_repr': '[1]'}}]
    contexts = control_contexts(task, rows, {'predicate': record}, {'state': 'unqualified'},
                                {'state': 'failed'}, {'state': 'failed'}, {'state': 'unverified'})
    raw = contexts['text_hyp']['raw_guidance']['predicate']
    assert raw['raw_text'] == text and raw['origin'] == 'qwen_endpoint'
    assert raw['response_hash'] == digest(record['response'])
    assert contexts['verified_hyp']['contract'] is None
    assert contexts['toolinput']['common_inputs_and_native_traces'] == contexts['text_hyp']['common_inputs_and_native_traces'] == contexts['verified_hyp']['common_inputs_and_native_traces']


TRIGGERS = {
    'f02': 'def trigger(arguments):\n return len(arguments["xs"]) > len(set(arguments["xs"]))',
    'f04': 'def trigger(arguments):\n return any(x == arguments["limit"] for x in arguments["xs"])',
    'f06': 'def trigger(arguments):\n return set(arguments["required"]) < set(arguments["container"])',
}


class Scripted:
    """Own-pipeline CPU response fixtures only, no model or paper simulation."""
    def __init__(self, bad_predicate=False, bad_trigger=False):
        self.calls = []; self.bad_predicate = bad_predicate; self.bad_trigger = bad_trigger

    def complete(self, request):
        self.calls.append(request); uid, stage = request['slot'].split('__')
        framing = 'json'
        if stage == 'meta':
            value = metadata(uid)
        elif stage == 'predicate':
            text = authored_contract(case(uid))['value']['predicate_source']; framing = 'python'
            if self.bad_predicate and uid == 'f02': text = 'not Python function syntax!'
        elif stage == 'behavior':
            value = {'summary': 'CPU fixture', 'source_lines': [3], 'limitations': ''}
        elif stage == 'hypothesis':
            mismatch = uid in TRIGGERS
            value = {'verdict': 'mismatch' if mismatch else 'unknown' if uid == 'f13' else 'consistent',
                     'target_line': 3 if mismatch else None,
                     'trigger_condition': 'Authored discriminating condition' if mismatch else '',
                     'explanation': 'CPU-only interface fixture'}
        elif stage == 'trigger':
            text = TRIGGERS[uid]; framing = 'python'
            if self.bad_trigger and uid == 'f04': text = 'def trigger(arguments):\n return True'
        else:
            arguments = {'f02': {'xs': [42, 42]}, 'f04': {'xs': [42], 'limit': 42},
                         'f06': {'container': [42, 43], 'required': [42]}, 'f14': {'xs': [42, 42, 41]}}
            value = {'inputs': [{'arguments': arguments[uid], 'purpose': 'contrast' if uid == 'f14' else 'trigger'}]
                     if uid != 'f13' else [], 'reason': 'Unknown suitability' if uid == 'f13' else 'CPU discriminator/contrast'}
        if framing == 'json': text = json.dumps(value)
        return {'text': '```' + framing + '\n' + text.rstrip() + '\n```',
                'origin': 'authored_CPU_test_only', 'finish_reason': 'stop'}


def test_full_feasibility_source_freeze_and_novel_accounting(tmp_path, monkeypatch):
    client = Scripted(); gate.run(client, tmp_path, backend={'mode': 'plain'})
    assert len(client.calls) == 27
    result = gate.report(tmp_path)
    assert result['gates'] == {'A': True, 'B': True, 'C': True}
    assert sum(r['novel_bug_inputs'] for r in result['rows']) == 3
    assert sum(r['new_detected_case'] for r in result['rows']) == 0
    assert next(r for r in result['rows'] if r['case'] == 'f13')['code_state'] == 'not_applicable_unknown'
    gate.run(client, tmp_path, backend={'mode': 'plain'}); assert len(client.calls) == 27
    monkeypatch.setattr(gate, 'ROOT', tmp_path)
    monkeypatch.setattr(gate, 'verify_preflight', lambda: None)
    original_freeze, original_report = gate.freeze, gate.report
    monkeypatch.setattr(gate, 'freeze', lambda root=tmp_path: original_freeze(root))
    monkeypatch.setattr(gate, 'report', lambda root=tmp_path: original_report(root))
    def forbidden_client(*args, **kwargs):
        raise AssertionError('Completed resume must not make network metadata calls')
    monkeypatch.setattr(controller, 'Client', forbidden_client)
    monkeypatch.setattr(gate, 'Client', forbidden_client)
    assert controller.main() == 0
    assert json.loads((tmp_path / 'status.json').read_text())['completed_resume_without_network']
    monkeypatch.setattr(gate.sys, 'argv', ['gate', 'online', '--online'])
    gate.main()
    (tmp_path / 'artifacts/f02__meta.json').write_text('{}')
    with pytest.raises(ValueError, match='frozen_data_drift'):
        gate.report(tmp_path)


def test_failed_contract_gate_stops_all_dependent_model_calls_and_keeps_raw(tmp_path):
    client = Scripted(bad_predicate=True); gate.run(client, tmp_path, backend={'mode': 'plain'})
    assert len(client.calls) == 9 and not any(q['stage'] == 'behavior' for q in client.calls)
    result = gate.report(tmp_path)
    assert result['gates'] == {'A': False, 'B': None, 'C': None}
    assert len(result['rows']) == 5 and all(x['phaseB'] == 'blocked' for x in result['rows'])
    context = json.loads((tmp_path / 'contexts/f02__phaseA.json').read_text())
    assert 'not Python' in context['text_hyp']['raw_guidance']['predicate']['raw_text']
    assert context['verified_hyp']['contract'] is None
    assert context['toolinput']['common_inputs_and_native_traces']
    failed = json.loads((tmp_path / 'artifacts/f02__predicate.json').read_text())
    assert failed['envelope'] == 'single_python_fence' and 'not Python' in failed['decoded_payload']


def test_bad_trigger_stops_before_generation(tmp_path):
    client = Scripted(bad_trigger=True); gate.run(client, tmp_path, backend={'mode': 'plain'})
    assert not any(q['stage'] == 'inputs' for q in client.calls)
    result = gate.report(tmp_path)
    assert result['gates'] == {'A': True, 'B': False, 'C': None}
    assert next(r for r in result['rows'] if r['case'] == 'f04')['phaseB'] == 'contradicted_trigger'


def test_capability_echo_is_raw_bare_json_and_has_one_slot(tmp_path):
    content = {'schema': {'properties': {'guided_json': {}}}}
    document = {'paths': {'/v1/chat/completions': {'post': {'requestBody': {'content': {'application/json': content}}}}}}
    class Backend:
        def __init__(self): self.calls = []
        def call(self, *args, **kwargs): return document
        def complete(self, request):
            self.calls.append(request)
            return {'text': '```json\n{"schema_gate":true}\n```', 'finish_reason': 'stop'}
    client = Backend(); result = gate.choose_backend(client, tmp_path)
    assert result['advertised'] and result['mode'] == 'plain'
    gate.choose_backend(client, tmp_path); assert len(client.calls) == 1
    assert client.calls[0]['guided_schema'] == gate.ECHO_SCHEMA
    (tmp_path / 'capability_response.json').write_text('{}')
    with pytest.raises(ValueError, match='capability_evidence_drift'):
        gate.choose_backend(client, tmp_path)


@pytest.mark.parametrize('phase', ['phaseA', 'phaseB'])
def test_resume_rebuilds_missing_context_without_new_requests(tmp_path, monkeypatch, phase):
    original = gate.immutable
    def interrupted(path, data):
        if str(path).endswith('f02__' + phase + '.json'):
            raise RuntimeError('authored interruption after durable case before context')
        return original(path, data)
    client = Scripted()
    monkeypatch.setattr(gate, 'immutable', interrupted)
    with pytest.raises(RuntimeError, match='authored interruption'):
        gate.run(client, tmp_path, backend={'mode': 'plain'})
    monkeypatch.setattr(gate, 'immutable', original)
    gate.run(client, tmp_path, backend={'mode': 'plain'})
    assert len(client.calls) == 27
    assert gate.report(tmp_path)['gates'] == {'A': True, 'B': True, 'C': True}
    for uid in fixtures.IDS:
        assert (tmp_path / 'contexts' / (uid + '__' + phase + '.json')).exists()


def test_correct_case_needs_resolved_checks_and_native_evidence():
    row = {'case': 'f14', 'records': {'behavior': {'state': 'valid'},
           'hypothesis': {'state': 'valid', 'parsed': {'verdict': 'consistent'}}},
           'checks': [{'state': 'unknown'}], 'pool': [{'execution': {'native_checked': False}}]}
    assert not gate.b_ok(row)
    row['checks'] = [{'state': 'evaluated', 'value': True}]
    assert not gate.b_ok(row)


def test_client_transmits_schema_without_changing_prompt_usage(tmp_path, monkeypatch):
    monkeypatch.setenv('QWEN_BASE_URL', 'http://127.0.0.1:9876'); seen = []
    def handler(req):
        if req.url.path.endswith('/models'):
            return httpx.Response(200, json={'data': [{'id': 'qwen2.5-coder-7b-instruct', 'max_model_len': 16384}]})
        if req.url.path.endswith('/tokenize'):
            return httpx.Response(200, json={'count': 50, 'max_model_len': 16384})
        seen.append(json.loads(req.content))
        return httpx.Response(200, json={'choices': [{'message': {'content': '{"schema_gate":true}'}, 'finish_reason': 'stop'}],
                                       'usage': {'prompt_tokens': 50, 'completion_tokens': 6}})
    original = httpx.Client
    monkeypatch.setattr(diagnostic_client.httpx, 'Client', lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    client = diagnostic_client.Client(tmp_path)
    request = {'slot': 'capability__echo', 'stage': 'echo', 'seed': 1,
               'messages': [{'role': 'user', 'content': 'NOT_JSON'}], 'guided_schema': gate.ECHO_SCHEMA}
    assert client.complete(request)['input_tokens'] == 50
    assert seen[0]['guided_json'] == gate.ECHO_SCHEMA
    client.close()
