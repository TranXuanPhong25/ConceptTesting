"""Contract, isolation and scoring tests. Scripted responses are not model evidence."""
import copy
import json
from pathlib import Path

import httpx
import pytest

from . import diagnostic, diagnostic_client, pilot_fixtures
from .diagnostic_core import (SCHEMAS, base_inputs, messages, observation, strict_json,
                              task_for, validate, native_observation)
from .diagnostic_execution import execute, replay_candidates


def case(uid):
    return next(c for c in pilot_fixtures.cases() if c['fixture_id'] == uid)


def value(stage):
    if stage == 'concept':
        return {'relation': 'Preserve each eligible occurrence.', 'domain': 'Lists of integers.', 'uncertainty': ''}
    if stage == 'behavior':
        return {'summary': 'Returns the described expression.', 'source_lines': [3], 'limitations': ''}
    if stage == 'hypothesis':
        return {'verdict': 'mismatch', 'required_relation': 'Required relation',
                'actual_relation': 'Actual relation', 'source_lines': [3],
                'trigger': 'A feasible difference', 'alternative': '', 'reason': 'Suspected mismatch'}
    return {'inputs': [], 'reason': 'No discriminating case established.'}


@pytest.mark.parametrize('text', ['{"x":1,"x":2}', '{"x":NaN}', '```json\n{}\n```', '{} trailing'])
def test_strict_json_rejects_ambiguous_or_repaired_content(text):
    with pytest.raises(ValueError):
        strict_json(text)


def test_spec_code_context_isolation_and_no_evaluator_leakage():
    row = case('f02')
    task = task_for(row)
    spec = json.loads(messages('concept', task)[1]['content'])['context']
    code = json.loads(messages('behavior', task)[1]['content'])['context']
    assert set(spec) == {'signature', 'spec'}
    assert set(code) == {'code', 'syntax'}
    assert task['spec'] not in code['code']
    assert 'set(xs)' in code['code']
    for stage in ('concept', 'behavior', 'hypothesis', 'inputs', 'revision'):
        serialized = json.dumps(messages(stage, task))
        assert 'evaluator' not in serialized and 'fixture_id' not in serialized
        assert row['evaluator']['witness'] not in serialized


def test_hyp_only_removes_only_explicit_concept():
    task = task_for(case('f02'))
    kwargs = {'behavior': value('behavior'), 'hypothesis': value('hypothesis'), 'evidence': {}}
    guided = json.loads(messages('inputs', task, concept=value('concept'), **kwargs)[1]['content'])
    control = json.loads(messages('inputs', task, **kwargs)[1]['content'])
    del guided['context']['model_concept_claim']
    assert guided == control


def test_schema_and_reference_checks_separate_from_semantics():
    task = task_for(case('f02'))
    unsupported_claim = value('hypothesis')
    # Mechanical validity deliberately does NOT imply this free-text claim is true.
    assert validate('hypothesis', json.dumps(unsupported_claim), task) == unsupported_claim
    unsupported_claim['source_lines'] = [999]
    with pytest.raises(ValueError, match='source_line'):
        validate('hypothesis', json.dumps(unsupported_claim), task)
    unsupported_claim['source_lines'] = [3]
    unsupported_claim['trigger'] = ''
    with pytest.raises(ValueError, match='trigger'):
        validate('hypothesis', json.dumps(unsupported_claim), task)
    unsupported_claim['verdict'] = 'unknown'
    unsupported_claim['source_lines'] = []
    validate('hypothesis', json.dumps(unsupported_claim), task)


def test_typed_output_and_public_seed_boundaries():
    assert observation('True') != observation('1')
    assert observation('exception:ValueError') == ('exception', 'ValueError')
    assert base_inputs(case('f06')) == ['([1], [1])']
    assert case('f06')['evaluator']['witness'] not in base_inputs(case('f06'))


def test_actual_native_traced_replay_and_expected_is_not_put(tmp_path):
    task = task_for(case('f02'))
    result = execute(task, '([1, 1],)', tmp_path)
    assert result['native_checked'], result
    assert result['output_repr'] == '[1]'
    assert native_observation(result) == observation('[1]')
    assert execute(task, '([1, 1],)', tmp_path) == result
    proposal = {'inputs': [{'arguments': '([1, 1],)', 'expected': '[1, 1]',
                            'predicted_actual': '[1]', 'purpose': 'trigger'}], 'reason': 'duplicate counts'}
    feedback = replay_candidates(task, proposal, tmp_path)
    assert feedback[0]['prediction_matches_native'] is True
    assert feedback[0]['expected_differs_native'] is True
    assert 'reference' not in json.dumps(feedback)


def test_invalid_domain_and_candidate_slots_remain_visible(tmp_path):
    task = task_for(case('f02'))
    proposal = {'inputs': [
        {'arguments': '__import__("os")', 'expected': '0', 'predicted_actual': '0', 'purpose': 'trigger'},
        {'arguments': '([True],)', 'expected': '[]', 'predicted_actual': '[]', 'purpose': 'contrast'},
        {'arguments': '([1, 1],)', 'expected': '[1, 1]', 'predicted_actual': '[1]', 'purpose': 'trigger'}],
        'reason': 'CPU fixture'}
    rows = replay_candidates(task, proposal, tmp_path)
    assert len(rows) == 3
    assert rows[0]['state'] == 'invalid_literal'
    assert rows[1]['state'] == 'unknown' and rows[1]['execution']['status'] == 'filtered'
    assert rows[2]['state'] == 'observed'


def test_masked_unused_and_unreachable_effects_are_correct(tmp_path):
    from .fixture_oracles import expected
    for uid in ('f14', 'f15'):
        row = case(uid)
        result = execute(task_for(row), '([1, 1],)', tmp_path)
        assert result['native_checked']
        assert native_observation(result) == expected(row, '([1, 1],)')


def test_exception_and_observed_prediction_counterevidence(tmp_path):
    row = case('f08')
    task = task_for(row)
    proposal = {'inputs': [{'arguments': '([],)', 'expected': 'None',
                            'predicted_actual': 'None', 'purpose': 'trigger'}], 'reason': 'empty'}
    feedback = replay_candidates(task, proposal, tmp_path)
    assert feedback[0]['execution']['native_checked']
    assert feedback[0]['execution']['exception_type'] == 'ValueError'
    assert feedback[0]['prediction_matches_native'] is False


class ScriptedClient:
    """CPU-only positive control, explicitly NOT a model or paper simulation."""
    def __init__(self):
        self.requests = []

    def complete(self, request):
        self.requests.append(request)
        stage = request['stage']
        artifact = value(stage)
        if stage == 'hypothesis':
            if request['slot'].startswith('f02'):
                artifact['source_lines'] = [3]
            else:
                artifact.update(verdict='unknown' if request['slot'].startswith('f13') else 'consistent',
                                source_lines=[], trigger='')
        if stage == 'inputs' and request['slot'].startswith('f02'):
            artifact['inputs'] = [{'arguments': '([1, 1],)', 'expected': '[1, 1]',
                                   'predicted_actual': '[1]', 'purpose': 'trigger'}]
        return {'text': json.dumps(artifact), 'finish_reason': 'stop', 'origin': 'authored_CPU_test_only'}


def test_end_to_end_controls_frozen_scoring_and_resume(tmp_path, monkeypatch):
    selected = [case(uid) for uid in ('f02', 'f13', 'f14')]
    monkeypatch.setattr(diagnostic.pilot_fixtures, 'cases', lambda: selected)
    monkeypatch.setitem(diagnostic.D, 'cases', 3)
    client = ScriptedClient()
    diagnostic.run(client, tmp_path)
    initial = len(client.requests)
    diagnostic.run(client, tmp_path)
    assert len(client.requests) == initial
    result = diagnostic.report(tmp_path)
    for summary in result['totals'].values():
        assert summary['fixtures'] == 3
        assert summary['detected_bug_cases'] == 1
        assert summary['correct_assertion_cases'] == 1
        assert summary['false_alarm_cases'] == 0
    state = json.loads((tmp_path / 'cases/f02.json').read_text())
    assert state['arms']['hyp_only']['hypothesis'] == state['arms']['concept_chain']['hypothesis']
    assert not result['advance_to_benchmark']
    path = tmp_path / 'cases/f02.json'
    path.write_text('{}')
    with pytest.raises(ValueError, match='generation_drift'):
        diagnostic.report(tmp_path)


def test_client_quarantine_and_cumulative_attempts(tmp_path, monkeypatch):
    monkeypatch.setenv('QWEN_BASE_URL', 'http://127.0.0.1:9876')
    def handler(request):
        if request.url.path.endswith('/models'):
            return httpx.Response(200, json={'data': [{'id': 'qwen2.5-coder-7b-instruct', 'max_model_len': 16384}]})
        if request.url.path.endswith('/tokenize'):
            return httpx.Response(200, json={'count': 50, 'max_model_len': 16384})
        return httpx.Response(200, json={'choices': [{'message': {'content': '{}'}, 'finish_reason': 'stop'}],
                                       'usage': {'prompt_tokens': 49, 'completion_tokens': 3}})
    original = httpx.Client
    monkeypatch.setattr(diagnostic_client.httpx, 'Client',
                        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    client = diagnostic_client.Client(tmp_path)
    request = {'slot': 'f02__shared__concept', 'stage': 'concept', 'seed': 1,
               'task_hash': 'example', 'messages': messages('concept', task_for(case('f02')))}
    with pytest.raises(RuntimeError, match='protocol_mismatch'):
        client.complete(request)
    with pytest.raises(RuntimeError, match='quarantined'):
        client.complete(request)
    attempts = json.loads((tmp_path / 'calls' / request['slot'] / 'attempts.json').read_text())
    assert len(attempts) == 1 and attempts[0]['state'] == 'quarantined'
    client.close()


def test_cli_requires_explicit_online_flag(monkeypatch):
    monkeypatch.setattr('sys.argv', ['diagnostic', 'online'])
    with pytest.raises(SystemExit, match='requires_explicit'):
        diagnostic.main()


def test_terminal_transport_failure_is_persisted_and_control_continues(tmp_path, monkeypatch):
    selected = [case('f02')]
    monkeypatch.setattr(diagnostic.pilot_fixtures, 'cases', lambda: selected)
    monkeypatch.setitem(diagnostic.D, 'cases', 1)
    class FailedConcept(ScriptedClient):
        def complete(self, request):
            if request['stage'] == 'concept':
                raise diagnostic_client.SlotFailure('completion_attempt_budget_exhausted')
            return super().complete(request)
    diagnostic.run(FailedConcept(), tmp_path)
    result = diagnostic.report(tmp_path)
    assert result['stage_counts']['concept'] == {'valid': 0, 'failed': 1}
    assert result['totals']['direct_chain']['correct_assertion_cases'] == 1
    assert result['totals']['concept_chain']['blocked_cases'] == 1
    assert result['totals']['hyp_only']['blocked_cases'] == 1


def test_invalid_input_stage_is_not_reported_as_valid_abstention(tmp_path, monkeypatch):
    selected = [case('f02')]
    monkeypatch.setattr(diagnostic.pilot_fixtures, 'cases', lambda: selected)
    monkeypatch.setitem(diagnostic.D, 'cases', 1)
    class InvalidInputs(ScriptedClient):
        def complete(self, request):
            if request['slot'] == 'f02__concept_chain__inputs':
                return {'text': '```json\n{}\n```', 'finish_reason': 'stop', 'origin': 'authored_CPU_test_only'}
            return super().complete(request)
    diagnostic.run(InvalidInputs(), tmp_path)
    result = diagnostic.report(tmp_path)
    guided = next(r for r in result['rows'] if r['arm'] == 'concept_chain')
    assert guided['failed_input_stages'] == 1
    assert guided['valid_abstention_stages'] == 0
    assert guided['stage_states'] == {'inputs': 'failed', 'revision': 'blocked_upstream'}


def test_preflight_cannot_survive_source_drift(tmp_path, monkeypatch):
    monkeypatch.setattr(diagnostic, 'source_snapshot', lambda: {'worker.py': 'old'})
    from .diagnostic_core import immutable, digest
    immutable(tmp_path / 'preflight.json', {'passed': True, 'source': {'worker.py': 'old'},
                                           'fixtures_hash': digest(pilot_fixtures.cases())})
    assert diagnostic.verify_preflight(tmp_path)['passed']
    monkeypatch.setattr(diagnostic, 'source_snapshot', lambda: {'worker.py': 'new'})
    with pytest.raises(ValueError, match='source_drift'):
        diagnostic.verify_preflight(tmp_path)


def test_incomplete_report_has_full_denominator_without_efficacy_scoring(tmp_path):
    result = diagnostic.report(tmp_path)
    assert result['state'] == 'incomplete'
    assert len(result['rows']) == 16
    assert 'totals' not in result
    assert not result['advance_to_benchmark']


def test_inherited_client_cannot_bypass_diagnostic(tmp_path):
    from .llm_client import Client
    with pytest.raises(RuntimeError, match='inherited_online_client_disabled'):
        Client(tmp_path, offline=False)


def test_large_tokenizer_response_and_cumulative_timeout_attempts(tmp_path, monkeypatch):
    monkeypatch.setenv('QWEN_BASE_URL', 'http://127.0.0.1:9876')
    counts = {'completion': 0}
    def handler(request):
        if request.url.path.endswith('/models'):
            return httpx.Response(200, json={'data': [{'id': 'qwen2.5-coder-7b-instruct', 'max_model_len': 16384}]})
        if request.url.path.endswith('/tokenize'):
            return httpx.Response(200, json={'count': 14000, 'max_model_len': 16384,
                                            'tokens': [60000] * 14000})
        counts['completion'] += 1
        return httpx.Response(503)
    original = httpx.Client
    monkeypatch.setattr(diagnostic_client.httpx, 'Client',
                        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    monkeypatch.setattr(diagnostic_client.time, 'sleep', lambda _: None)
    client = diagnostic_client.Client(tmp_path)
    request = {'slot': 'f02__shared__concept', 'stage': 'concept', 'seed': 1,
               'task_hash': 'example', 'messages': messages('concept', task_for(case('f02')))}
    path = tmp_path / 'calls' / request['slot'] / 'attempts.json'
    diagnostic_client.write_json(path, [{'state': 'reserved_usage_unknown'}, {'state': 'transport_error_usage_unknown'}])
    with pytest.raises(diagnostic_client.SlotFailure, match='attempt_budget_exhausted'):
        client.complete(request)
    assert counts['completion'] == 1
    assert len(json.loads(path.read_text())) == 3
    with pytest.raises(diagnostic_client.SlotFailure, match='attempt_budget_exhausted'):
        client.complete(request)
    assert counts['completion'] == 1
    client.close()


@pytest.mark.parametrize('metadata', [[], None, {'count': -1, 'max_model_len': 16384},
                                     {'count': 50, 'max_model_len': 8192}])
def test_tokenizer_bad_metadata_stays_quarantined_on_resume(tmp_path, monkeypatch, metadata):
    monkeypatch.setenv('QWEN_BASE_URL', 'http://127.0.0.1:9876')
    counter = {'tokens': 0}
    def handler(request):
        if request.url.path.endswith('/models'):
            return httpx.Response(200, json={'data': [{'id': 'qwen2.5-coder-7b-instruct', 'max_model_len': 16384}]})
        counter['tokens'] += 1
        return httpx.Response(200, content=json.dumps(metadata), headers={'content-type': 'application/json'})
    original = httpx.Client
    monkeypatch.setattr(diagnostic_client.httpx, 'Client',
                        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    client = diagnostic_client.Client(tmp_path)
    packet = messages('concept', task_for(case('f02')))
    for _ in range(4):
        with pytest.raises(diagnostic_client.ProtocolFailure, match='tokenizer'):
            client.token_count(packet)
    assert counter['tokens'] == 1
    client.close()


def test_overlong_prompt_is_slot_failure_not_global_protocol_quarantine(tmp_path, monkeypatch):
    monkeypatch.setenv('QWEN_BASE_URL', 'http://127.0.0.1:9876')
    def handler(request):
        if request.url.path.endswith('/models'):
            return httpx.Response(200, json={'data': [{'id': 'qwen2.5-coder-7b-instruct', 'max_model_len': 16384}]})
        return httpx.Response(200, json={'count': 17000, 'max_model_len': 16384})
    original = httpx.Client
    monkeypatch.setattr(diagnostic_client.httpx, 'Client',
                        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    client = diagnostic_client.Client(tmp_path)
    request = {'slot': 'f02__shared__concept', 'stage': 'concept', 'seed': 1,
               'task_hash': 'example', 'messages': messages('concept', task_for(case('f02')))}
    with pytest.raises(diagnostic_client.SlotFailure, match='context_budget_exceeded'):
        client.complete(request)
    assert not list((tmp_path / 'tokens').glob('*.quarantine.json'))
    client.close()
