"""Fixed candidate pools isolate observation caps from generation and final input selection."""
from copy import deepcopy

from final.src.audits.compare_native_budgets import compare_task, saved_pool
from final.src.audits.recheck_saved_coverage import SavedScenarios


def fixture():
    task = {'task_id': 'HumanEval/0', 'entry_point': 'f',
            'prompt': 'def f(x: int):\n    """Return x above threshold2, otherwise0."""\n'}
    calls = [{'args': f'({x},)', 'kwargs': '{}'} for x in (0, 1, 3)]
    program = {'id': 'p0', 'code': 'def f(x):\n    if x > 2:\n        return x\n    return 0\n',
               'base': {'calls': []}}
    target = {'id': 't', 'program_id': 'p0', 'criterion': 'C1', 'line': 3}
    obligation = {'id': 'O1', 'program_id': 'p0', 'line': 3, 'predicate': 'x > 2',
                  'predicate_status': 'supported', 'new_membership': {'status': 'unknown'}}
    generation = {'inputs': calls[:2], 'candidate_count': 3, 'selected_targets': [target],
        'analysis': [{'program_id': 'p0'}],
        'concepts': [], 'obligations': [obligation], 'candidate_ledger': [
            {'candidate_id': str(i), 'canonical_args': call, 'domain': 'true', 'errors': [],
             'sources': [{'tool': 'llm', 'round': 0, 'index': i}]} for i, call in enumerate(calls)]}
    return task, {'programs': [program]}, generation


def test_larger_cap_adds_witness_on_identical_order_without_changing_saved_inputs():
    task, cohort, generation = fixture()
    old = deepcopy(generation);executed = []

    def trace(owner, job):
        executed.append(job['tests'][0])
        x = int(job['tests'][0]['args'].strip('(),'))
        return {'domain': 'valid', 'status': 'executed',
                'coverage': {'lines': [2, 3] if x > 2 else [2, 4], 'arcs': []}}, .1

    result = compare_task(task, {}, cohort, generation, {'visible_put_ids': ['p0']}, trace, (2, 4))
    low, high = result['caps']['2'], result['caps']['4']
    assert low['target_coverage']['covered'] == 0 and high['target_coverage']['covered'] == 1
    assert low['obligations'][0]['new_membership']['status'] == 'unknown'
    assert high['obligations'][0]['new_membership']['status'] == 'hit'
    assert low['input_put_order'] == high['input_put_order'][:2]
    assert len(executed) == 3 and high['observations'] == 3
    assert generation == old


def test_pool_dedup_and_full_base_exclusion_use_call_identity():
    task, cohort, generation = fixture()
    cohort['programs'][0]['base']['calls'] = [generation['candidate_ledger'][0]['canonical_args']]
    generation['candidate_ledger'].append(deepcopy(generation['candidate_ledger'][1]))
    generation['candidate_count'] = 2
    candidates, priority = saved_pool(generation, cohort, SavedScenarios(task))
    assert len(candidates) == len(priority) == 2
    assert {row['call']['args'] for row in candidates.values()} == {'(1,)', '(3,)'}


def test_labelled_llm_seeds_stay_in_direct_queue_and_rounds_are_interleaved():
    task, cohort, generation = fixture()
    generation['concepts'] = [{'id': 'c0', 'round': 0}, {'id': 'c1', 'round': 1}]
    generation['candidate_ledger'][0]['sources'][0]['concept_id'] = 'c0'
    generation['candidate_ledger'][1]['sources'][0]['concept_id'] = 'c0'
    generation['candidate_ledger'][2]['sources'][0].update(round=1, concept_id='c1')
    extra = deepcopy(generation['candidate_ledger'][0])
    extra.update(candidate_id='sample', canonical_args={'args': '(7,)', 'kwargs': '{}'},
                 sources=[{'tool': 'hypothesis', 'round': 0, 'concept_id': 'c0', 'draw_index': 0}])
    generation['candidate_ledger'].append(extra);generation['candidate_count'] = 4
    candidates, order = saved_pool(generation, cohort, SavedScenarios(task))
    assert [candidates[key]['call']['args'] for key in order] == ['(0,)', '(3,)', '(7,)', '(1,)']


def test_fallback_never_executes_visible_program_rejected_by_analysis():
    task, cohort, generation = fixture()
    generation['selected_targets'] = [];generation['obligations'] = []
    extra = deepcopy(cohort['programs'][0]);extra['id'] = 'rejected'
    cohort['programs'].append(extra)
    owners = []

    def trace(owner, job):
        owners.append(owner)
        return {'domain': 'valid', 'status': 'executed', 'coverage': {'lines': [], 'arcs': []}}, .1

    compare_task(task, {}, cohort, generation, {'visible_put_ids': ['rejected', 'p0']}, trace, (2, 4))
    assert set(owners) == {'p0'}
