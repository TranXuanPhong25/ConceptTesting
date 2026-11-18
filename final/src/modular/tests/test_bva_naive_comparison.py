"""Comparison identifies PUTs by task and validates verdict/input provenance."""
import pytest

from final.src.audits.compare_bva_naive import collect, partition
from final.src.audits.continue_bva_evaluation import save, digest


def test_put_ids_are_task_local_and_partitions_are_disjoint():
    bva = {('HumanEval/0', '1'), ('HumanEval/1', '1')}
    naive = {('HumanEval/1', '1'), ('HumanEval/2', '1')}
    result = partition(bva, naive, bva | naive)
    assert result['shared'] == 1
    assert result['bva_only'] == result['naive_only'] == 1
    assert result['net_bva_minus_naive'] == 0
    assert result['bva_only_puts'] == [{'task_id': 'HumanEval/0', 'put_id': '1'}]


@pytest.fixture
def verdicts(tmp_path):
    task = 'HumanEval/0'
    inputs = {'task_id': task, 'arms': {'boundary': {'inputs': [
        {'args': '(0,)', 'kwargs': '{}'}, {'args': '(1,)', 'kwargs': '{}'}]}}}
    save(tmp_path/'modular_manifest.json', {'tasks': [task]})
    save(tmp_path/'generation_frozen.json', {'inputs': {task: digest(inputs)}})
    save(tmp_path/'tasks/0/inputs.json', inputs)
    save(tmp_path/'tasks/0/oracle_valid.json', {'tests': [
        {'args': '(0,)', 'kwargs': '{}', 'expected': '0', 'input_key': 'zero'},
        {'args': '(1,)', 'kwargs': '{}', 'expected': '1', 'input_key': 'one'}]})
    save(tmp_path/'tasks/0/result.json', {'task_id': task, 'arms': {'boundary': {'valid_inputs': 2, 'detected_put_ids': ['0']}},
        'arm_indices': {'boundary': [0, 1]}, 'outcomes': {'0': {'failing': [1], 'unstable': []}, '1': {'failing': [], 'unstable': []}}})
    for repeat in range(2):
        save(tmp_path/f'tasks/0/evaluation/0_{repeat}.json', {'tests': [{'status': 'pass', 'actual': '0'}, {'status': 'fail', 'actual': '0'}]})
    save(tmp_path/'modular_summary.json', {'arms': {'boundary': {'detected': 1}}})
    return tmp_path


def test_collect_requires_two_observations_and_keeps_witness_identity(verdicts):
    result = collect(verdicts, 'boundary')
    assert result['detected'] == {('HumanEval/0', '0')}
    assert result['value'] == result['non_timeout'] == result['detected']
    assert result['witnesses'][('HumanEval/0', '0')]['input']['input_key'] == 'one'


def test_saved_outcome_analysis_ignores_modified_generation_inputs(verdicts):
    save(verdicts/'tasks/0/inputs.json', {'changed': True})
    result=collect(verdicts, 'boundary')
    assert result['detected']=={('HumanEval/0','0')}
