"""Authored contract checks; no model endpoint or benchmark outcomes."""
import json
import copy

from final.src.models.core_model import ModelResponse
from final.src.modular.artifacts import ArtifactStore
from final.src.modular.context import PipelineSettings, TaskContext

SPEC = 'def f(xs):\n    """Return the total of every occurrence in xs."""\n'
SOURCE = 'def f(xs):\n    unique = set(xs)\n    return sum(unique)\n'


def context(tmp_path, calls):
    base = {'args': '([2, 3],)', 'kwargs': '{}'}
    program = {'id': 'p0', 'code': SOURCE, 'base': {'status': 'pass', 'calls': [base],
        'coverage': {'lines': [2, 3], 'arcs': [[-1, 2], [2, 3], [3, -1]]}}}
    return TaskContext({'task_id': 'HumanEval/0', 'entry_point': 'f', 'prompt': SPEC, 'test': ''},
        {'contract': '    assert isinstance(xs, list)\n    assert all(type(x) is int for x in xs)\n'},
        ArtifactStore(tmp_path), PipelineSettings(input_budget=4, input_tokens=2048), calls,
        cohort_task={'generated': 1, 'programs': [program]}, packet={'visible_put_ids': ['p0'], 'common': ''})


def obligation():
    return {'program_id': 'p0', 'line': 2, 'requirement': 'every occurrence',
        'pattern': 'dedup loses contributions', 'scenario': 'equal positive values must both contribute',
        'predicate': 'len(xs) > distinct_count(xs) and sum(xs) > 0',
        'instruction': 'Repeat a nonzero positive value.',
        'counterexample': 'Dedup is correct when the spec asks for distinct values.',
        'strategies': {'xs': {'kind': 'sampled', 'values': [[4, 4], [5, 5]]}}}


class Calls:
    def __init__(self, first=None, second=None):
        self.first = first if first is not None else {'obligations': [obligation()]}
        self.second = second if second is not None else {'inputs': [
            {'arguments': {'xs': [2, 3]}}, {'arguments': {'xs': [4, 4]}}]}
        self.requests = []

    def token_count(self, messages):
        return 100

    def complete(self, number, name, messages, **kwargs):
        self.requests.append(messages)
        raw = self.first if len(self.requests) == 1 else self.second
        return ModelResponse(raw if isinstance(raw, str) else json.dumps(raw), finish_reason='stop')


def test_truncated_response_salvages_only_complete_input_records():
    from final.src.modular.spec_obligation.schema import read_response
    raw, repairs = read_response('{"inputs":[{"arguments":{"xs":[4,4]}},{"arguments":{"xs":[5,')
    assert raw['inputs'] == [{'arguments': {'xs': [4, 4]}}]
    assert 'complete_input_records_salvaged' in repairs










def test_strategy_aliases_are_normalized_without_executing_code():
    from final.src.modular.spec_obligation.schema import normalize_strategies
    assert normalize_strategies({'x': {'kind': 'integers', 'min_value': 1, 'max_value': 5}}) == {
        'x': {'kind': 'int', 'min': 1, 'max': 5}}




def test_duplicate_entry_is_omitted_without_aborting_other_programs(tmp_path):
    from final.src.modular.spec_obligation.evidence import Evidence
    from final.src.modular.spec_obligation.prompts import messages
    ctx = context(tmp_path, Calls())
    other = copy.deepcopy(ctx.cohort_task['programs'][0])
    other['id'] = 'p1'
    ctx.cohort_task['programs'].append(other)
    ctx.packet['visible_put_ids'].append('p1')
    ctx.cohort_task['programs'][0]['code'] = (
        'def f(xs):\n    return sum(xs)\n\n'
        'def f(xs):\n    return 0\n')
    evidence = Evidence(ctx, 'spec_obligation')
    assert 'p0' not in evidence.analyses
    assert set(evidence.by_id) == {'p1'}
    request = messages(ctx, evidence, hybrid=False, phase='propose')
    assert [p['program_id'] for p in json.loads(request[-1]['content'])['programs']] == ['p1']
    assert any('expected_one_top_level_function' in str(row) for row in evidence.errors)


def test_obligation_strategy_list_is_bound_to_signature_parameters(tmp_path):
    from final.src.modular.spec_obligation.evidence import Evidence
    from final.src.modular.spec_obligation.schema import parse_obligations
    ctx = context(tmp_path, Calls())
    evidence = Evidence(ctx, 'spec_obligation')
    row = obligation()
    row['strategies'] = [row['strategies']['xs']]
    accepted, errors = parse_obligations({'obligations': [row]}, evidence)
    assert accepted and not errors
    assert accepted[0]['strategies'] == {'xs': {'kind': 'sampled', 'values': [[4, 4], [5, 5]]}}


def test_requirement_paraphrase_keeps_grounding_as_hypothesis(tmp_path):
    from final.src.modular.spec_obligation.evidence import Evidence
    from final.src.modular.spec_obligation.schema import parse_obligations
    ctx = context(tmp_path, Calls())
    evidence = Evidence(ctx, 'spec_obligation')
    row = obligation()
    row['requirement'] = 'All occurrences contribute to the total.'
    accepted, errors = parse_obligations({'obligations': [row]}, evidence)
    assert accepted and not errors
    assert accepted[0]['requirement_grounding'] == 'overlap_hypothesis'




def test_validated_v2_is_retired_and_cannot_be_selected():
    import pytest
    from final.src.modular.arms import selected_arms
    from final.src.orchestration.config import normalize
    with pytest.raises(ValueError, match='Unknown'):
        selected_arms(['control_flow_obligation_validated'])
    with pytest.raises(ValueError, match='Unknown'):
        normalize({'arms': ['control_flow_obligation_validated']})


def test_explicit_resume_reuses_exact_prompt_before_retokenizing(tmp_path):
    from final.src.modular.spec_obligation.evidence import Evidence
    from final.src.modular.spec_obligation.prompts import messages
    from final.src.runtime.artifacts import digest, save
    ctx = context(tmp_path, Calls())
    evidence = Evidence(ctx, 'spec_obligation')
    original = messages(ctx, evidence, hybrid=False, phase='propose', input_budget=4)
    record = {'messages': original, 'temperature': ctx.settings.input_temperature,
              'max_tokens': ctx.settings.input_tokens, 'seed': ctx.settings.input_seed}
    call = ctx.artifacts.path('tasks/0/calls/spec_obligation_propose')
    save(call / 'request.json', record)
    save(call.with_name(call.name + '.frozen_request_replay.json'),
         {'request_id': digest(record), 'authorization': 'Authored continuation'})
    class NoTokenizer:
        def token_count(self, request):
            raise AssertionError('Frozen prompt must not be rebuilt from a new token count')
    ctx.calls = NoTokenizer()
    assert messages(ctx, evidence, hybrid=False, phase='propose', input_budget=4) == original


def test_saved_prompt_replay_rejects_changed_source_or_settings(tmp_path):
    import pytest
    from final.src.modular.spec_obligation.evidence import Evidence
    from final.src.modular.spec_obligation.prompts import messages
    from final.src.runtime.artifacts import digest, save
    ctx = context(tmp_path, Calls());evidence = Evidence(ctx, 'spec_obligation')
    original = messages(ctx, evidence, hybrid=False, phase='propose', input_budget=4)
    call = ctx.artifacts.path('tasks/0/calls/spec_obligation_propose')
    record = {'messages': original, 'temperature': .7, 'max_tokens': ctx.settings.input_tokens,
              'seed': ctx.settings.input_seed + 1}
    save(call / 'request.json', record)
    directive = call.with_name(call.name + '.frozen_request_replay.json')
    save(directive, {'request_id': digest(record), 'authorization': 'fixture'})
    with pytest.raises(ValueError, match='settings_mismatch'):
        messages(ctx, evidence, hybrid=False, phase='propose', input_budget=4)
    record['seed'] -= 1;save(call / 'request.json', record)
    save(directive, {'request_id': digest(record), 'authorization': 'fixture'})
    evidence.by_id['p0']['code'] = evidence.by_id['p0']['code'].replace('set(xs)', 'list(xs)')
    with pytest.raises(ValueError, match='source_mismatch'):
        messages(ctx, evidence, hybrid=False, phase='propose', input_budget=4)


def test_partial_trace_can_witness_site_but_cannot_prove_site_missed(tmp_path):
    from final.src.modular.spec_obligation.evidence import Evidence
    evidence = Evidence(context(tmp_path, Calls()), 'spec_obligation')
    row = {**obligation(), 'predicate_status': 'supported'}
    call = evidence.canonical_call({'arguments': {'xs': [4, 4]}})
    partial = {'domain': 'valid', 'status': 'timeout', 'coverage': {'lines': [1], 'arcs': []}}
    assert evidence.scenario(row, call, partial)[0] is None
    partial['coverage']['lines'].append(2)
    assert evidence.scenario(row, call, partial)[0] is True


def test_repeated_membership_reuses_predicate_receipt(tmp_path):
    from final.src.modular.spec_obligation.evidence import Evidence
    evidence = Evidence(context(tmp_path, Calls()), 'spec_obligation')
    row = {**obligation(), 'predicate_status': 'supported'}
    call = evidence.canonical_call({'arguments': {'xs': [4, 4]}})
    observed = {'domain': 'valid', 'status': 'executed', 'coverage': {'lines': [2], 'arcs': []}}
    assert evidence.scenario(row, call, observed)[0] is True
    evidence.predicate_checks = 512
    assert evidence.scenario(row, call, observed)[0] is True










def test_usage_accounting_separates_hybrid_from_control_flow(tmp_path):
    from final.src.modular.catalogue_reporting import usage_by_arm
    for name in ('spec_obligation_propose', 'spec_obligation_construct', 'control_flow_round_0',
                 'control_flow_obligation_propose'):
        path = tmp_path / 'tasks/0/calls' / name
        path.mkdir(parents=True)
        (path / 'attempt.json').write_text('{}')
        (path / 'response.json').write_text(json.dumps({'usage': {
            'prompt_tokens': 10, 'completion_tokens': 5, 'total_tokens': 15}}))
    result = usage_by_arm(tmp_path, ['spec_obligation', 'control_flow', 'control_flow_obligation'])
    assert result['spec_obligation']['received'] == 2
    assert result['spec_obligation']['known_usage']['total_tokens'] == 30
    assert result['control_flow']['received'] == 1
    assert result['control_flow_obligation']['received'] == 1
