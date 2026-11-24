"""CPU coverage audit must use owner traces and retain missing observations as unknown."""
from copy import deepcopy

from final.src.audits.recheck_saved_coverage import measure
from final.src.modular.tests.test_spec_obligation import SPEC, obligation


def test_owner_trace_repairs_missing_membership_without_claiming_other_owner_hit():
    row = {**obligation(), 'id': 'O1', 'predicate_status': 'supported', 'new_membership': {'status': 'unknown'}}
    generation = {'inputs': [{'args': '([4,4],)', 'kwargs': '{}'}],
        'selected_targets': [{'id': 't', 'program_id': 'p1', 'criterion': 'C1', 'line': 2}],
        'obligations': [row], 'rounds': [{'supplied_target_ids': ['t']}]}
    task = {'task_id': 'HumanEval/0', 'prompt': SPEC, 'entry_point': 'f'}
    traces = {('p0', 0): {'domain': 'valid', 'status': 'executed', 'coverage': {'lines': [2], 'arcs': []}}}
    original = deepcopy(generation)
    result = measure(task, generation, traces)
    assert result['obligations'][0]['new_membership']['status'] == 'hit'
    assert result['obligations'][0]['old_membership']['status'] == 'unknown'
    assert result['target_coverage'] == {'covered': 0, 'total': 1}
    assert result['target_measurements'][0]['status'] == 'unknown'
    assert result['target_measurements'][0]['prompt_rounds'] == [0]
    assert generation == original


def test_empty_predicate_is_not_replaced_with_true():
    row = {**obligation(), 'id': 'O1', 'predicate': '', 'predicate_status': 'unsupported',
           'predicate_error': 'invalid_predicate_size', 'new_membership': {'status': 'unknown'}}
    result = measure({'task_id': 'HumanEval/0', 'prompt': SPEC, 'entry_point': 'f'},
        {'inputs': [{'args': '([4,4],)', 'kwargs': '{}'}], 'obligations': [row]},
        {('p0', 0): {'domain': 'valid', 'status': 'executed', 'coverage': {'lines': [2], 'arcs': []}}})
    assert result['obligations'][0]['new_membership']['status'] == 'unknown'
