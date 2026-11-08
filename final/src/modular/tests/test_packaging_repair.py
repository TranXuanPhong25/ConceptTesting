import json
import pytest

from final.src.audits.repair_cached_plain import static_evidence, repair_record, repaired_batch
from final.src.modular.call_builder import CallBuilder


def setup_signature(signature, contract=''):
    task = {'prompt': signature + '\n    pass\n', 'entry_point': 'f'}
    builder = CallBuilder.for_source(task['prompt'], 'f')
    evidence = static_evidence(task, contract, next(iter(builder.signature.parameters)))
    return builder, evidence


@pytest.mark.parametrize('raw,expected', [("('你好')", "('你好',)"), ("''", "('',)")])
def test_string_rewrap_preserves_exact_value(raw, expected):
    builder, proof = setup_signature('def f(text: str):')
    output, reason = repair_record({'args': raw, 'kwargs': '{}'}, builder, proof)
    assert output['args'] == expected and reason == 'rewrap_single_argument'


@pytest.mark.parametrize('raw', ['[0, 0]', '[0]', '[]'])
def test_bare_list_requires_static_incompatibility_of_original_binding(raw):
    builder, proof = setup_signature('def f(values):', 'assert type(values) == list')
    output, _ = repair_record({'args': raw, 'kwargs': '{}'}, builder, proof)
    assert output['args'] == '(' + raw + ',)'


def test_viable_nested_list_and_multi_argument_calls_are_preserved():
    builder, proof = setup_signature('def f(values: list):')
    assert repair_record({'args': '[[0]]', 'kwargs': '{}'}, builder, proof)[0] is None
    builder = CallBuilder.for_source('def f(x, y): pass', 'f')
    assert repair_record({'args': '(1, 2)', 'kwargs': '{}'}, builder, [('int','exact','fixture')])[0] is None


@pytest.mark.parametrize('contract', [
    'assert values and all(isinstance(v, int) for v in values)',
    'if values:\n    assert all(isinstance(v, int) for v in values)',
    'assert all(v for group in [] for v in values)',
    'values = []\nassert type(values) == list',
])
def test_conditional_or_rebound_contracts_do_not_authorize_repairs(contract):
    _, proof = setup_signature('def f(values):', contract)
    assert proof == []


def test_unconditional_iteration_proves_noniterable_singleton_binding_invalid():
    builder, proof = setup_signature('def f(values):', 'assert all([isinstance(v, int) for v in values])')
    assert repair_record({'args': '[0]', 'kwargs': '{}'}, builder, proof)[0]['args'] == '([0],)'
    assert repair_record({'args': '[[]]', 'kwargs': '{}'}, builder, proof)[0] is None


@pytest.mark.parametrize('signature', ['def f(*, value: str):', 'def f(value: str=""):', 'def f(value):'])
def test_ambiguous_default_keyword_or_untyped_signatures_stay_unrepaired(signature):
    builder, proof = setup_signature(signature)
    assert repair_record({'args': "'x'", 'kwargs': '{}'}, builder, proof)[0] is None


def test_nonempty_kwargs_and_expressions_are_not_repaired():
    builder, proof = setup_signature('def f(value: str):')
    for row in [{'args': "'x'", 'kwargs': "{'value':'y'}"}, {'args': "'x' * 3", 'kwargs': '{}'}]:
        assert repair_record(row, builder, proof)[0] is None


def test_one_record_per_raw_slot_retains_original_viable_records():
    builder, proof = setup_signature('def f(value: list):')
    original = {'args': '([1],)', 'kwargs': '{}', 'concept_id': None}
    invalid = {'args': '[2]', 'kwargs': '{}', 'concept_id': None}
    arm = {'inputs': [original, invalid], 'rejected': []}
    response = {'finish_reason': 'stop', 'text': json.dumps({'inputs': [original, invalid]})}
    output, changes, _ = repaired_batch(arm, response, builder, proof)
    assert len(output['inputs']) == 2 and output['inputs'][0] == original
    assert changes[0]['raw_index'] == 1 and changes[0]['original_admitted_record'] == invalid
    assert output['inputs'][1]['args'] == '([2],)'
    assert arm['inputs'][1] == invalid


def test_truncated_and_malformed_responses_are_not_reparsed():
    builder, proof = setup_signature('def f(value: str):')
    arm = {'inputs': [], 'rejected': []}
    for response in [{'finish_reason': 'length', 'text': '{}'}, {'finish_reason': 'stop', 'text': '```'}]:
        assert repaired_batch(arm, response, builder, proof)[0] == arm
