"""Mechanical and executable negative controls; authored output is not Qwen evidence."""
import copy
import json

import pytest

from . import experiment, fixtures
from .binding import bind, observation
from .common import D, task_for
from .contracts import messages, parse
from .cpu_contracts import authored_contract
from .evidence import contract_results, hypothesis_evidence, qualify, replay, replay_inputs, shared_selection
from .predicates import evaluate, validate_code


def case(uid):
    return next(c for c in fixtures.cases() if c['fixture_id'] == uid)


@pytest.mark.parametrize('uid', ['f01', 'f03', 'f05'])
def test_pure_contracts_calibrate_across_full_frozen_bank(uid, tmp_path):
    c = case(uid); artifact = authored_contract(c)
    assert qualify(c, artifact, fixtures.semantic_bank(c), tmp_path)['state'] == 'calibrated'


@pytest.mark.parametrize('source', [
    'import os\ndef obligation(arguments, observation):\n return True',
    'def obligation(arguments, observation):\n return observation.__class__',
    'def obligation(arguments, observation):\n arguments["xs"] = []\n return True',
    'def obligation(arguments, observation):\n return eval("True")',
    'def obligation(arguments, observation):\n while True: pass\n return True',
    'def obligation(arguments, observation):\n return obligation(arguments, observation)',
    'def obligation(arguments, observation):\n return [x for x in arguments["xs"] for y in arguments["xs"]]'
])
def test_nonpure_or_unbounded_sources_rejected(source):
    with pytest.raises(ValueError):
        validate_code(source, 'obligation')


@pytest.mark.parametrize('constant', ['True', 'False'])
def test_vacuous_predicates_fail_semantic_calibration(constant, tmp_path):
    c = case('f02'); artifact = authored_contract(c)
    artifact['value']['predicate_source'] = 'def obligation(arguments, observation):\n return ' + constant
    assert qualify(c, artifact, fixtures.semantic_bank(c), tmp_path)['state'] == 'unqualified'


def test_python_bool_integer_equality_does_not_pass_semantic_bank(tmp_path):
    c = case('f05'); artifact = authored_contract(c)
    artifact['value']['predicate_source'] = ('def obligation(arguments, observation):\n'
        ' if observation["status"] != "ok": return False\n'
        ' return observation["value"] == all(x in arguments["container"] for x in arguments["required"])')
    assert qualify(c, artifact, fixtures.semantic_bank(c), tmp_path)['state'] == 'unqualified'


@pytest.mark.parametrize('uid,expression', [
    ('f01', 'type(value) is list and value == sorted(arguments["xs"])'),
    ('f03', 'type(value) is not bool and value == sum(1 for x in arguments["xs"] if x >= arguments["limit"])')])
def test_recursive_wrong_type_and_float_equality_are_rejected(uid, expression, tmp_path):
    c = case(uid); artifact = authored_contract(c)
    artifact['value']['predicate_source'] = ('def obligation(arguments, observation):\n'
        ' if observation["status"] != "ok": return False\n'
        ' value = observation["value"]\n return ' + expression)
    assert qualify(c, artifact, fixtures.semantic_bank(c), tmp_path)['state'] == 'unqualified'


def test_ambiguous_raw_predicate_is_unqualified_without_being_rewritten(tmp_path):
    c = case('f13'); artifact = authored_contract(case('f01')); original = copy.deepcopy(artifact)
    q = qualify(c, artifact, [], tmp_path)
    assert q['state'] == 'unknown_spec' and q['model_abstained'] is False
    assert artifact == original


def test_named_json_binding_types_unknown_missing_and_nested_limits():
    task = task_for(case('f02'))
    assert bind(task, {'xs': [2, 2]}) == ({'xs': [2, 2]}, '([2, 2],)')
    for arguments in ({}, {'xs': [], 'extra': 1}, [2, 2]):
        with pytest.raises(ValueError):
            bind(task, arguments)
    with pytest.raises(ValueError):
        bind(task, {'xs': [2 ** 129]})


def hypothesis(trigger, target=3):
    return {'state': 'valid', 'value': {'obligation_id': 'O1', 'verdict': 'mismatch',
                                       'target_line': target, 'claim': 'Multiplicity loss',
                                       'trigger_source': trigger, 'predicted_effect': 'Lower count',
                                       'alternative': '', 'reason': 'CPU fixture'}}


TRIGGER = 'def trigger(arguments):\n return len(arguments["xs"]) > len(set(arguments["xs"]))'


def test_witness_support_rejects_masked_and_dead_effects_and_bad_trigger(tmp_path):
    for uid in ('f02', 'f14', 'f15'):
        c = case(uid); task = task_for(c)
        pool = [replay(task, {'xs': [2, 2]}, tmp_path / 'native'),
                replay(task, {'xs': [1, 2]}, tmp_path / 'native')]
        contract = authored_contract(c)
        q = qualify(c, contract, fixtures.semantic_bank(c), tmp_path / 'predicates')
        checks = contract_results(contract, q, pool, tmp_path / 'predicates')
        target = 3 if uid != 'f15' else 4
        result = hypothesis_evidence(task, hypothesis(TRIGGER, target), pool, checks, tmp_path / 'predicates')
        assert result['state'] == ('observed_supported' if uid == 'f02' else 'contradicted_trigger')
        if uid == 'f02':
            bad = hypothesis('def trigger(arguments):\n return True')
            assert hypothesis_evidence(task, bad, pool, checks, tmp_path / 'predicates')['state'] == 'contradicted_trigger'
        if uid == 'f15':
            from .evidence import feedback_for
            feedback = feedback_for(pool, checks, result)
            assert feedback[0]['target_reached'] is False and feedback[0]['native_checked'] is True
            assert feedback[0]['is_counterexample'] is True


def test_runtime_error_non_boolean_and_empty_batch_are_unknown(tmp_path):
    rows = [{'arguments': {'xs': []}, 'observation': {'status': 'ok', 'value': []}}]
    for expr in ('1', '1 // 0', 'arguments["missing"]'):
        source = 'def obligation(arguments, observation):\n return ' + expr
        assert evaluate(source, 'obligation', rows, tmp_path)[0]['state'] == 'unknown'
    assert evaluate('def trigger(arguments):\n return True', 'trigger', [], tmp_path) == []


def test_input_domain_filter_not_model_domain(tmp_path):
    task = task_for(case('f02'))
    results = replay_inputs(task, {'inputs': [{'arguments': {'xs': [True]}, 'purpose': 'trigger'},
                                             {'arguments': {'xs': [2, 2]}, 'purpose': 'trigger'}]}, tmp_path)
    assert results[0]['state'] == 'unknown' and results[0]['execution']['status'] == 'filtered'
    assert results[1]['state'] == 'observed'


def test_spec_code_isolation_and_no_calibration_rows_in_model_context():
    c = case('f02'); task = task_for(c)
    a = json.loads(messages('contract', task)[1]['content'])['context']
    b = json.loads(messages('behavior', task)[1]['content'])['context']
    assert set(a) == {'signature', 'spec'} and set(b) == {'code', 'syntax'}
    assert task['spec'] not in b['code']
    assert 'semantic_bank' not in json.dumps(messages('hypothesis', task, qualification_state='calibrated'))


def test_exact_quote_and_locked_obligation_reference():
    c = case('f02'); task = task_for(c); artifact = authored_contract(c)['value']
    artifact['spec_quote'] = task['spec']
    assert parse('contract', json.dumps(artifact), task) == artifact
    artifact['spec_quote'] = 'not in the original spec'
    with pytest.raises(ValueError):
        parse('contract', json.dumps(artifact), task)
    h = hypothesis(TRIGGER)['value']; h['obligation_id'] = 'O2'
    with pytest.raises(ValueError):
        parse('hyp_revision', json.dumps(h), task)


def test_discovery_pool_determinism_and_no_gold_selection():
    for uid in ('f02', 'f04', 'f06', 'f13'):
        c = case(uid)
        a, b = fixtures.discovery_pool(c), fixtures.discovery_pool(c)
        assert a == b and len(a['pool']) == 24
        c['evaluator']['witness'] = 'FORBIDDEN'
        assert fixtures.discovery_pool(c) == a


def test_common_selection_includes_supported_witness_for_every_arm():
    pool = [{'arguments': {'xs': [i]}} for i in range(10)]
    checks = [{'state': 'evaluated', 'value': i != 9} for i in range(10)]
    support = {'state': 'observed_supported', 'witness_indices': [9]}
    selected = shared_selection(pool, checks, support)
    assert selected['indices'][0] == 9 and len(selected['indices']) == 6


class ScriptedClient:
    """Authored CPU response fixture; never called Qwen or counted as semantic evidence."""
    def __init__(self):
        self.calls = []

    def complete(self, request):
        self.calls.append(request)
        uid, arm, stage = request['slot'].split('__')
        ctx = json.loads(request['messages'][1]['content'])['context']
        if stage == 'contract':
            artifact = authored_contract(case(uid))['value']
            artifact['spec_quote'] = ctx['spec'] if artifact['decision'] == 'proposed' else ''
        elif stage == 'behavior':
            artifact = {'summary': 'Authored CPU interface fixture', 'source_lines': [3], 'limitations': ''}
        elif stage in ('hypothesis', 'hyp_revision'):
            artifact = hypothesis(TRIGGER)['value']
            if uid != 'f02':
                artifact.update(verdict='unknown' if uid == 'f13' else 'consistent',
                                target_line=None, trigger_source='', claim='')
        else:
            artifact = {'inputs': [{'arguments': {'xs': [42, 42]}, 'purpose': 'trigger'}] if uid == 'f02' else [],
                        'reason': 'Authored CPU input fixture'}
        return {'text': json.dumps(artifact), 'origin': 'authored_CPU_test_only', 'finish_reason': 'stop'}


def test_full_mechanism_controls_freezes_resume_and_whole_pool_accounting(tmp_path, monkeypatch):
    selected = [case(uid) for uid in ('f02', 'f14', 'f13')]
    monkeypatch.setattr(experiment.fixtures, 'cases', lambda: copy.deepcopy(selected))
    client = ScriptedClient()
    experiment.run(client, tmp_path)
    assert len(client.calls) == 30
    experiment.run(client, tmp_path)
    assert len(client.calls) == 30
    result = experiment.report(tmp_path)
    assert result['cases'] == 3 and result['model_expected_outputs_generated'] is False
    assert result['totals']['witness_only']['detected_cases'] == 1
    row = next(x for x in result['rows'] if x['case'] == 'f02')
    assert row['initial_support'] == row['final_support'] == 'observed_supported'
    for a in experiment.ARMS:
        assert row['arms'][a]['unique_bug_inputs'] == 1
        assert row['arms'][a]['novel_bug_inputs_outside_full_pool'] == 1
        assert not row['arms'][a]['new_detected_case_beyond_witness_only']
    assert row['arms']['verified_hyp']['selected_bug_inputs'] == 1
    assert row['arms']['verified_hyp']['novel_generated_inputs_outside_full_pool'] == 1
    assert row['arms']['verified_hyp']['duplicate_observed_slots'] == 1
    assert result['stage_counts']['hyp_revision']['valid'] == 3
    assert result['preparation_counts']['qualification_calibrated'] == 2
    assert result['final_support_states']['observed_supported'] == 1
    contexts = [json.loads(r['messages'][1]['content'])['context'] for r in client.calls
                if r['slot'].startswith('f02') and r['stage'] == 'inputs']
    assert len(contexts) == 3
    assert contexts[0]['common_inputs_and_native_traces'] == contexts[1]['common_inputs_and_native_traces'] == contexts[2]['common_inputs_and_native_traces']
    assert all('semantic_bank' not in json.dumps(r['messages']) for r in client.calls)
    revision_context = next(json.loads(r['messages'][1]['content'])['context'] for r in client.calls
                            if r['slot'] == 'f02__shared__hyp_revision')
    assert revision_context['initial_support_state'] == 'observed_supported'
    assert 'target_reached' in revision_context['fixed_pool_feedback'][0]
    path = tmp_path / 'preparation/f02.json'
    path.write_text('{}')
    with pytest.raises(ValueError, match='frozen_data_drift'):
        experiment.report(tmp_path)


def test_terminal_slot_failure_remains_in_full_case_denominator(tmp_path, monkeypatch):
    selected = [case('f02')]
    monkeypatch.setattr(experiment.fixtures, 'cases', lambda: copy.deepcopy(selected))
    class Failed(ScriptedClient):
        def complete(self, request):
            if request['stage'] == 'contract':
                raise experiment.SlotFailure('transport_budget_exhausted')
            return super().complete(request)
    experiment.run(Failed(), tmp_path)
    result = experiment.report(tmp_path)
    assert result['cases'] == 1
    assert result['rows'][0]['qualification']['state'] == 'unqualified'
    assert result['rows'][0]['arms']['verified_hyp']['selected_bug_inputs'] == 0
    assert result['rows'][0]['arms']['toolinput']['unique_bug_inputs'] == 1


def test_reserved_unknown_worker_is_never_reexecuted(tmp_path, monkeypatch):
    from . import isolated
    from .common import immutable, digest
    from .paths import CONFIG
    script = experiment.HERE / 'predicate_worker.py'
    job = {'rows': [{'arguments': {'xs': []}}]}
    immutable(tmp_path / 'job.json', job)
    identity = digest({'job': job, 'script': str(script), 'interpreter': CONFIG['V4_PYTHON']})
    immutable(tmp_path / 'attempt.json', {'identity': identity, 'state': 'reserved', 'launched': None})
    monkeypatch.setattr(isolated.subprocess, 'Popen', lambda *a, **k: (_ for _ in ()).throw(AssertionError('must not rerun')))
    result = isolated.run_once(script, job, tmp_path)
    assert result['rows'][0]['state'] == 'unknown'
    assert isolated.run_once(script, job, tmp_path) == result
    assert json.loads((tmp_path / 'attempt.json').read_text())['resume_cached_unknown'] is True


def test_partial_worker_output_recovery_is_unknown_and_orphan_cannot_overwrite_it(tmp_path, monkeypatch):
    from . import isolated
    from .common import immutable, digest
    from .paths import CONFIG
    script = experiment.HERE / 'predicate_worker.py'; job = {'rows': [{'arguments': {'xs': []}}]}
    immutable(tmp_path / 'job.json', job)
    identity = digest({'job': job, 'script': str(script), 'interpreter': CONFIG['V4_PYTHON']})
    immutable(tmp_path / 'attempt.json', {'identity': identity, 'state': 'launched', 'launched': True})
    (tmp_path / 'result.json').write_text('{')
    monkeypatch.setattr(isolated.subprocess, 'Popen', lambda *a, **k: (_ for _ in ()).throw(AssertionError('must not rerun')))
    first = isolated.run_once(script, job, tmp_path)
    assert first['status'] == 'unresolved'
    (tmp_path / 'worker-output.part').write_text('{"rows":[{"state":"evaluated","value":true}]}')
    assert isolated.run_once(script, job, tmp_path) == first


def test_unknown_reservation_stays_unknown_launch_when_canonical_unknown_is_recovered(tmp_path):
    from . import isolated
    from .common import immutable, digest
    from .paths import CONFIG
    script = experiment.HERE / 'predicate_worker.py'; job = {'rows': []}
    immutable(tmp_path / 'job.json', job)
    identity = digest({'job': job, 'script': str(script), 'interpreter': CONFIG['V4_PYTHON']})
    immutable(tmp_path / 'attempt.json', {'identity': identity, 'state': 'reserved', 'launched': None})
    immutable(tmp_path / 'result.json', {'status': 'unresolved', 'rows': []})
    isolated.run_once(script, job, tmp_path)
    assert json.loads((tmp_path / 'attempt.json').read_text())['launched'] is None
