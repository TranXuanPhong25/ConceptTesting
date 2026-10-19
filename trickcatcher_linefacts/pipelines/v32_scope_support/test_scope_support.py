"""Authored mechanism regressions, never recovered historical model output."""
import copy
import json

import pytest

from . import evidence, gate
from .predicates import validate_code, evaluate
from .test_gate import Scripted, TRIGGERS


@pytest.mark.parametrize('body', [
    'return all(x > 0 for x in arguments["a"]) and all(x < 5 for x in arguments["b"])',
    'return all(all(x > 0 for x in row) for row in arguments["a"])',
    'return all(all(x > 0 for x in x) for x in arguments["a"])',
    'xs = arguments["a"]\n return all(x > 0 for x in xs) and len([x for x in xs if x > 1]) > 0',
])
def test_valid_lexical_comprehensions(body):
    source = 'def trigger(arguments):\n ' + body
    assert validate_code(source, 'trigger') == source


@pytest.mark.parametrize('body,reason', [
    ('v = all(x for x in arguments["a"])\n return x', 'unknown_name'),
    ('x = x + 1\n return x > 0', 'unknown_name'),
    ('if arguments["a"]:\n  x = 1\n return x == 1', 'unknown_name'),
    ('return all(x for x in x)', 'unknown_name'),
    ('return all(arguments for arguments in [1])', 'binding_mutation'),
    ('return all(len for len in [1])', 'binding_mutation'),
    ('x = 1\n x = 2\n return True', 'binding_mutation'),
    ('return all(x for x in [1] for y in [2])', 'nested_iteration'),
    ('return arguments.get("a")', 'AST_policy'),
    ('return trigger(arguments)', 'call_policy'),
    ('arguments["a"] = 1\n return True', 'mutation'),
    ('return all(_x for _x in [1])', 'binding_mutation'),
])
def test_unsafe_or_unbound_code_rejected(body, reason):
    with pytest.raises(ValueError, match=reason):
        validate_code('def trigger(arguments):\n ' + body, 'trigger')


def test_comprehension_runs_in_guarded_worker_and_does_not_leak(tmp_path):
    source = ('def trigger(arguments):\n'
              ' return all(x > 0 for x in arguments["a"]) and all(x < 5 for x in arguments["b"])')
    assert evaluate(source, 'trigger', [{'arguments': {'a': [1, 2], 'b': [3]}},
                                      {'arguments': {'a': [0], 'b': [3]}}], tmp_path) == [
        {'state': 'evaluated', 'value': True}, {'state': 'evaluated', 'value': False}]


def row(n, triggered=False, reached=True):
    return {'arguments': {'n': n, 'triggered': triggered}, 'input_id': str(n),
            'execution': {'native_checked': True, 'status': 'ok', 'output_repr': 'False',
                          'events': [{'event': 'line', 'line': 3, 'function': 'f'}] if reached else [],
                          'omitted_events': 0}}


H = {'state': 'valid', 'value': {'verdict': 'mismatch', 'target_line': 3, 'trigger_source': 'authored'}}
T = {'state': 'evaluated', 'value': True}
F = {'state': 'evaluated', 'value': False}
U = {'state': 'unknown', 'reason': 'authored_failure'}


@pytest.fixture
def trigger_evaluator(monkeypatch):
    def own_rows(source, kind, rows, root):
        return [{'state': 'evaluated', 'value': r['arguments']['triggered']} for r in rows]
    monkeypatch.setattr(evidence, 'evaluate', own_rows)


def test_new_witness_promotes_cumulative_candidate(trigger_evaluator, tmp_path):
    pool = [row(1)]
    initial = evidence.hypothesis_evidence({'entry': 'f'}, H, pool, [T], tmp_path)
    assert gate.provisional(initial)
    ctx = gate.candidate_context({'hypothesis': None}, {'support': initial, 'hypothesis': H})
    assert ctx['hypothesis'] is None and ctx['unverified_candidate'] == H['value']
    new = dict(row(2, True), state='observed', slot=0)
    update = evidence.cumulative_support({'entry': 'f'}, H, pool, [T], [new], [F], tmp_path)
    assert update['support']['state'] == 'observed_supported'
    assert update['accepted_slots'] == update['novel_accepted_slots'] == [0]
    assert update['proposal_ledger'][0]['cumulative_index'] == 1


@pytest.mark.parametrize('old_check,old_trigger,expected', [
    (T, True, 'contradicted_trigger'), (U, False, 'unverified'),
    ({'state': 'evaluated', 'value': 1}, False, 'unverified'),
])
def test_new_witness_cannot_erase_old_bad_evidence(trigger_evaluator, tmp_path, old_check, old_trigger, expected):
    update = evidence.cumulative_support({'entry': 'f'}, H, [row(1, old_trigger)], [old_check],
                                        [dict(row(2, True), state='observed', slot=0)], [F], tmp_path)
    assert update['support']['state'] == expected and update['accepted_slots'] == []


@pytest.mark.parametrize('state', ['invalid', 'unknown'])
def test_failed_proposals_are_not_filtered_out(trigger_evaluator, tmp_path, state):
    proposals = [dict(row(2, True), state='observed', slot=0), {'slot': 1, 'state': state}]
    update = evidence.cumulative_support({'entry': 'f'}, H, [row(1)], [T], proposals, [F], tmp_path)
    assert update['support']['state'] == 'unverified' and update['accepted_slots'] == []
    assert update['failed_proposal_slots'] == [1] and len(update['proposal_ledger']) == 2


def test_shared_duplicate_is_not_novel(trigger_evaluator, tmp_path):
    original = row(1, True)
    update = evidence.cumulative_support({'entry': 'f'}, H, [original], [F],
                                        [dict(original, state='observed', slot=0)], [F], tmp_path)
    assert update['accepted_slots'] == [0] and update['novel_accepted_slots'] == []


@pytest.mark.parametrize('checks', [[], [F, F]])
def test_missing_or_excess_evaluator_coverage_blocks_support(trigger_evaluator, tmp_path, checks):
    support = evidence.hypothesis_evidence({'entry': 'f'}, H, [row(1, True)], checks, tmp_path)
    assert support['state'] == 'unverified' and not support['complete_coverage']


def test_missing_trigger_and_truncated_trace_are_unknown(monkeypatch, tmp_path):
    monkeypatch.setattr(evidence, 'evaluate', lambda *args: [])
    support = evidence.hypothesis_evidence({'entry': 'f'}, H, [row(1, True)], [F], tmp_path)
    assert support['unknown_indices'] == [0] and not gate.provisional(support)
    monkeypatch.setattr(evidence, 'evaluate', lambda *args: [T])
    native = row(1, True, False); native['execution']['omitted_events'] = 1
    support = evidence.hypothesis_evidence({'entry': 'f'}, H, [native], [F], tmp_path)
    assert support['state'] == 'unverified' and support['unknown_indices'] == [0]
    native['execution']['omitted_events'] = 0
    assert evidence.hypothesis_evidence({'entry': 'f'}, H, [native], [F], tmp_path)['state'] == 'contradicted_trigger'


def test_end_to_end_provisional_promotion_and_resume(tmp_path, monkeypatch):
    # Fresh CPU-authored exact condition outside the full original shared pool.
    monkeypatch.setitem(TRIGGERS, 'f06',
        'def trigger(arguments):\n return arguments["container"] == [42, 43] and arguments["required"] == [42]')
    client = Scripted(); gate.run(client, tmp_path, backend={'mode': 'plain'})
    result = gate.report(tmp_path)
    assert result['gates'] == {'A': True, 'B': True, 'C': True}
    r = next(x for x in result['rows'] if x['case'] == 'f06')
    assert r['initial_support'] == 'unverified' and r['final_support'] == 'observed_supported'
    assert r['provisional_admission'] and r['novel_accepted_witness_inputs'] == 1
    request = next(q for q in client.calls if q['slot'] == 'f06__inputs')
    ctx = json.loads(request['messages'][1]['content'])['context']
    assert ctx['hypothesis'] is None and ctx['candidate_status'] == 'unverified_candidate'
    gate.run(client, tmp_path, backend={'mode': 'plain'})
    assert len(client.calls) == 27


def test_correct_case_good_contrast_cannot_hide_invalid_proposal(tmp_path):
    class InvalidContrast(Scripted):
        def complete(self, request):
            response = super().complete(request)
            if request['slot'] == 'f14__inputs':
                payload = {'inputs': [{'arguments': {'xs': [42]}, 'purpose': 'contrast'},
                                      {'arguments': {'xs': [1.5]}, 'purpose': 'contrast'}], 'reason': 'CPU domain test'}
                response['text'] = json.dumps(payload)
            return response
    gate.run(InvalidContrast(), tmp_path, backend={'mode': 'plain'})
    result = gate.report(tmp_path)
    assert result['gates']['C'] is False
    r = next(x for x in result['rows'] if x['case'] == 'f14')
    assert r['phaseC'] == 'failed'
