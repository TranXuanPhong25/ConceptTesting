"""Authored contract checks; no model endpoint or benchmark outcomes."""
import json
import copy

from final.src.core_model import ModelResponse
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


def test_full_coverage_still_generates_semantic_witness_and_replays(tmp_path):
    from final.src.modular.arms.spec_obligation import SpecObligationArm
    calls = Calls()
    ctx = context(tmp_path, calls)
    result = SpecObligationArm().run(ctx)
    assert len(calls.requests) == 2
    assert result['obligations'][0]['base_membership']['status'] == 'miss'
    assert result['obligations'][0]['new_membership']['status'] == 'hit'
    assert result['obligations'][0]['source_sha256']
    assert result['obligations'][0]['line'] == 2
    assert any(row['reason'] == 'duplicate_base' for row in result['rejected'])
    assert all(row['args'] != '([2, 3],)' for row in result['inputs'])
    assert any(row['status'] == 'complete' and row['draws'] > 0 for row in result['sampling'])
    assert result['functional_bug_detection'] == 'pending_shared_reference_evaluation'
    for messages in calls.requests:
        payload = json.loads(messages[-1]['content'])
        assert list(payload)[-1] == 'base_inputs_do_not_repeat'
        assert '4: ' not in payload['programs'][0]['numbered_source']
        assert '2:     unique = set(xs)' in payload['programs'][0]['numbered_source']
    ctx.calls = None
    ctx.artifacts = ArtifactStore(tmp_path, read_only=True)
    assert SpecObligationArm().run(ctx) == result


def test_bad_metadata_and_hypothesis_do_not_discard_direct_inputs(tmp_path):
    from final.src.modular.arms.spec_obligation import SpecObligationArm
    bad = obligation()
    bad['strategies'] = {'xs': {'kind': 'executable', 'code': 'bad'}}
    first = {'obligations': [bad], 'inputs': [{'arguments': {'xs': [6, 6]}}]}
    result = SpecObligationArm().run(context(tmp_path, Calls(first=first)))
    assert result['inputs']
    assert result['sampling'][0]['status'] == 'unsupported'
    bad['line'] = 900
    result = SpecObligationArm().run(context(tmp_path / 'bad_site', Calls(first=first)))
    assert not result['obligations'] and result['inputs']
    assert result['errors']


def test_missing_base_inventory_is_unknown(tmp_path):
    from final.src.modular.arms.spec_obligation import SpecObligationArm
    ctx = context(tmp_path, Calls())
    ctx.cohort_task['programs'][0]['base'].pop('calls')
    result = SpecObligationArm().run(ctx)
    assert result['obligations'][0]['base_membership']['status'] == 'unknown'


def test_hybrid_keeps_coverage_targets_alongside_semantic_obligations(tmp_path):
    from final.src.modular.arms.spec_obligation import ControlFlowObligationArm
    ctx = context(tmp_path, Calls())
    ctx.cohort_task['programs'][0]['code'] = 'def f(xs):\n    if not xs:\n        return 0\n    unique = set(xs)\n    return sum(unique)\n'
    ctx.cohort_task['programs'][0]['base']['coverage'] = {
        'lines': [2, 4, 5], 'arcs': [[-1, 2], [2, 4], [4, 5], [5, -1]]}
    ctx.calls.first['obligations'][0]['line'] = 4
    ctx.calls.second['inputs'].append({'arguments': {'xs': []}})
    result = ControlFlowObligationArm().run(ctx)
    assert result['selected_targets'] and result['obligations']
    assert result['target_coverage']['covered'] > 0
    assert all(t['source_sha256'] and t['line'] for t in result['selected_targets'])
    assert len(ctx.calls.requests) == 2


def test_strategy_aliases_are_normalized_without_executing_code():
    from final.src.modular.spec_obligation.schema import normalize_strategies
    assert normalize_strategies({'x': {'kind': 'integers', 'min_value': 1, 'max_value': 5}}) == {
        'x': {'kind': 'int', 'min': 1, 'max': 5}}


def test_integer_cohort_program_ids_bind_without_string_conversion(tmp_path):
    from final.src.modular.arms.spec_obligation import SpecObligationArm
    calls = Calls()
    calls.first['obligations'][0]['program_id'] = 0
    ctx = context(tmp_path, calls)
    ctx.cohort_task['programs'][0]['id'] = 0
    ctx.packet['visible_put_ids'] = [0]
    result = SpecObligationArm().run(ctx)
    assert result['obligations'][0]['program_id'] == 0
    assert result['obligations'][0]['new_membership']['status'] == 'hit'


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


def test_prefect_and_cli_register_both_arms_with_correct_call_cap():
    from final.src.modular.arms import selected_arms
    from final.src.orchestration.config import normalize, preview
    names = ['spec_obligation', 'control_flow_obligation']
    assert [a.name for a in selected_arms(names)] == names
    config = normalize({'arms': names, 'task_numbers': [0]})
    result = preview(config)
    assert result['logical_calls_by_arm'] == dict.fromkeys(names, 2)


def test_validated_v2_is_retired_and_cannot_be_selected():
    import pytest
    from final.src.modular.arms import selected_arms
    from final.src.orchestration.config import normalize
    with pytest.raises(ValueError, match='Unknown'):
        selected_arms(['control_flow_obligation_validated'])
    with pytest.raises(ValueError, match='Unknown'):
        normalize({'arms': ['control_flow_obligation_validated']})


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


def test_summary_handles_shared_prompt_overflow_without_inventing_coverage(tmp_path):
    from final.src.modular.arms.spec_obligation import SpecObligationArm
    ctx = context(tmp_path, Calls())
    ctx.inputs = {'arms': {'spec_obligation': {'inputs': [], 'rejected': [], 'status': 'prompt_too_large'}}}
    summary = {}
    SpecObligationArm().extend_summary([ctx], summary, None)
    assert summary['spec_obligation']['coverage_pending_tasks'] == 1


def test_base_dedup_checks_invisible_program_inventory(tmp_path):
    from final.src.modular.arms.spec_obligation import SpecObligationArm
    ctx = context(tmp_path, Calls())
    other = copy.deepcopy(ctx.cohort_task['programs'][0])
    other['id'] = 'not_visible'
    other['base']['calls'] = [{'args': '([4, 4],)', 'kwargs': '{}'}]
    ctx.cohort_task['programs'].append(other)
    result = SpecObligationArm().run(ctx)
    assert all(row['args'] != '([4, 4],)' for row in result['inputs'])


def test_unsupported_predicate_and_wrong_spec_quote_preserve_direct_inputs(tmp_path):
    from final.src.modular.arms.spec_obligation import SpecObligationArm
    row = obligation()
    row['predicate'] = 'local_unique_count > 0'
    first = {'obligations': [row], 'inputs': [{'arguments': {'xs': [8, 8]}}]}
    result = SpecObligationArm().run(context(tmp_path, Calls(first=first)))
    assert result['obligations'][0]['base_membership']['status'] == 'unknown'
    assert result['obligations'][0]['new_membership']['status'] == 'unknown'
    assert result['inputs']
    row['requirement'] = 'never mentioned in spec'
    result = SpecObligationArm().run(context(tmp_path / 'wrong_quote', Calls(first=first)))
    assert not result['obligations'] and result['inputs']


def test_truncated_response_records_are_usable_in_generation(tmp_path):
    from final.src.modular.arms.spec_obligation import SpecObligationArm
    calls = Calls(second='{"inputs":[{"arguments":{"xs":[9,9]}},{"arguments":')
    result = SpecObligationArm().run(context(tmp_path, calls))
    assert any(row['args'] == '([9, 9],)' for row in result['inputs'])
    assert result['rounds'][1]['response_repairs'] == ['complete_input_records_salvaged']


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


def test_two_arms_share_freeze_oracle_and_read_only_pipeline_replay(tmp_path, monkeypatch):
    from final.src.modular.arms.spec_obligation import SpecObligationArm, ControlFlowObligationArm
    from final.src.modular.dataset import DATA_SHA256
    from final.src.modular.pipeline import BenchmarkPipeline
    from final.src.modular.references import TaskReferencePrograms
    from final.src.modular.tests.helpers import FixtureCalls
    from final.src.runtime.artifacts import digest, save
    from final.src.runtime.execution import execute

    ctx = context(tmp_path / 'unused', None)
    task = {**ctx.task, 'canonical_solution': '    return sum(xs)\n'}
    row = {**ctx.cohort_task, 'task_id': task['task_id'], 'base_pass': 1, 'base_input_keys': []}
    cohort = tmp_path / 'cohort.json'
    save(cohort, {'tasks': [row], 'cohort_sha256': digest([row]), 'dataset_sha256': DATA_SHA256})
    directory = tmp_path / 'run'

    class Model:
        model_id = 'authored-offline-obligation-fixture'
        def tokens(self, messages): return 100
        def generate(self, messages, **kwargs):
            phase = json.loads(messages[-1]['content'])['phase']
            raw = Calls().first if phase == 'propose' else Calls().second
            return ModelResponse(json.dumps(raw), {'prompt_tokens': 10, 'completion_tokens': 5, 'total_tokens': 15}, 'stop')

    def oracle(job):
        assert (directory / 'generation_frozen.json').is_file()
        frozen = json.loads((directory / 'tasks/0/inputs.json').read_text())
        assert set(frozen['arms']) == {'spec_obligation', 'control_flow_obligation'}
        return execute(job)

    monkeypatch.setattr('final.src.modular.stages.reference_oracle.execute', oracle)
    pipeline = BenchmarkPipeline(cohort, ArtifactStore(directory),
        arms=(SpecObligationArm(), ControlFlowObligationArm()),
        settings=PipelineSettings(target_programs=1, input_budget=4),
        calls=FixtureCalls(Model(), directory), execution_cache=False, reference_programs=TaskReferencePrograms())
    metadata = {task['task_id']: {**ctx.metadata, 'atol': 0}}
    result = pipeline.run([task], metadata)
    assert result['arms']['spec_obligation']['detected'] == 1
    assert result['arms']['control_flow_obligation']['detected'] == 1
    assert result['spec_obligation']['call_usage']['received'] == 2
    replay = BenchmarkPipeline(cohort, ArtifactStore(directory, read_only=True),
        arms=(SpecObligationArm(), ControlFlowObligationArm()), settings=pipeline.settings,
        execution_cache=False, reference_programs=TaskReferencePrograms())
    assert replay.run([task], metadata) == result
