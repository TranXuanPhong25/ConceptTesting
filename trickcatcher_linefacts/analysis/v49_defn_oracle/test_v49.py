"""Reference-free checks for Amendment 1, including the real isolated worker."""
import ast
import itertools
import json

import pytest

from trickcatcher_linefacts.analysis.v49_defn_oracle import oracle as O


def ok(value):
    return ['ok', repr(value)]


@pytest.mark.parametrize('programs,expected', [
    ([ok(1)], None),
    ([ok(1), ok(1)], ok(1)),
    ([ok(1), ok(1), ok(0), ok(0)], None),  # exactly V/2 is insufficient
    ([ok(1), ok(1), ok(0)], ok(1)),
    ([ok(1), ok(1), ['timeout']], ok(1)),
    ([ok(1), ok(1), ['timeout'], ['timeout']], None),
    ([ok(1), ok(1), ['exception', 'ValueError'], ['skipped']], None),
    ([ok(1), ok(1), ok(1), ['timeout'], ['exception', 'MemoryError']], ok(1)),
    ([ok(1), ok(2), ok(2), ok(0), ok(0)], None),
])
def test_primary_quorum(programs, expected):
    assert O.votes(ok(0), programs)['primary'] == expected


def test_finishing_only_and_native_rules():
    result = O.votes(ok(0), [ok(1), ok(1), ['timeout'], ['exception', 'ValueError'], ['skipped']])
    assert result['primary'] is None
    assert result['finishing'] == result['tc_full'] == ok(1)
    assert result['consensus'] is None
    assert O.votes(ok(0), [ok(1), ok(1), ok(0), ok(0)])['finishing'] is None
    assert O.votes(ok(0), [ok(2), ok(1)])['tc_full'] == ok(2)  # v46 tie order
    assert O.votes(ok(0), [ok(1)] * 3)['consensus'] == ok(1)
    assert O.votes(ok(0), [ok(1)] * 2)['consensus'] is None


def test_unparseable_normal_output_is_a_finishing_disagreement():
    result = O.votes(ok(0), [ok(1), ok(1), ['ok', 'truncated('], ['ok', 'truncated(']])
    assert result['primary'] is result['finishing'] is None


@pytest.mark.parametrize('put', [['timeout'], ['exception', 'ValueError'], ['skipped'], ['ok', 'bad(']])
def test_put_failure_never_emits(put):
    assert all(v is None for v in O.votes(put, [ok(1)] * 5).values())


@pytest.mark.parametrize('put,expected', [(1, True), (1, 1.0), (0, None), (0, [1, (None, b'x')])])
def test_votes_keep_typed_equality_across_json(put, expected):
    result = json.loads(json.dumps(O.votes(ok(put), [ok(expected)] * 3)))
    assert O.E.same(O.E.iorel.value(result['primary']), O.E.iorel.value(ok(expected)))
    assert O.votes(ok(expected), [ok(expected)] * 3)['primary'] is None


@pytest.mark.parametrize('out,reasons', [
    ([ok(0), ok(1)], []),
    ([['timeout'], ok(1)], ['timeout']),
    ([ok(0), ['exception', 'MemoryError']], ['MemoryError']),
    ([ok(0), ['exception', 'RecursionError']], ['RecursionError']),
    ([['exception', 'ValueError'], ok(1)], ['exception']),
    ([['exception', 'load:SyntaxError'], ok(1)], ['load']),
    ([['skipped'], ok(1)], ['skipped-crash']),
    ([ok(0), ok(2)], ['mismatch']),
    ([ok(False), ok(1)], ['mismatch']),
    ([['timeout'], ['exception', 'MemoryError']], ['timeout', 'MemoryError']),
])
def test_strict_public_validity(out, reasons):
    assert O.rejection([ok(0), ok(1)], out) == reasons


def test_validity_does_not_ignore_put_timeout_or_exception():
    assert O.rejection([['timeout'], ok(1)], [ok(0), ok(1)]) == ['mismatch']
    assert O.rejection([['exception', 'ValueError']], [['exception', 'ValueError']])
    assert O.rejection([], []) == ['load']
    assert O.rejection([ok(1)], []) == ['load']


@pytest.mark.parametrize('out,expected', [
    ([['timeout'], ok(1)], True),
    ([['exception', 'load:MemoryError'], ok(1)], True),
    ([['exception', 'RecursionError'], ['timeout']], True),
    ([['exception', 'load:SyntaxError'], ok(1)], False),
    ([['timeout'], ok(99)], False),
    ([ok(0), ok(1)], False),
])
def test_resource_only_rejections_include_load_memory_errors(out, expected):
    assert O.resource_only(O.rejection([ok(0), ok(1)], out), out) is expected


def toy_record(n=10):
    # Slots 7/8/9 were generated but invalid: sampling valid programs only is wrong.
    values = [ok(1), ok(1), ok(1), ok(0), ['timeout'], ok(2), ok(2)]
    rows = {'(0,)': dict(put=ok(0), programs={'tc': {str(i): o for i, o in enumerate(values)}}),
            '(1,)': dict(put=ok(0), programs={'tc': {str(i): ok(0) for i in range(len(values))}})}
    record = dict(families={'tc': dict(valid_programs=list(range(len(values))), planned=n)}, inputs=rows)
    truth = {lit: dict(valid=True, ref=O.E.iorel.value(ok(1)), exposing=True) for lit in rows}
    return record, truth


def test_k5_exact_mean_matches_independent_brute_force():
    record, truth = toy_record()
    meta, actual = O.subset_mean(record, record['inputs'], truth)
    assert meta['subsets'] == 252
    expected = []
    for chosen in itertools.combinations(range(10), 5):
        selected = [record['inputs']['(0,)']['programs']['tc'][str(i)] for i in chosen if i < 7]
        agreeing = sum(v == ok(1) for v in selected)
        wrong = sum(v == ok(2) for v in selected)
        confirmed = int(agreeing >= 2 and 2 * agreeing > len(selected))
        fa = int(wrong >= 2 and 2 * wrong > len(selected))
        expected.append(dict(tests=confirmed + fa, eligible_inputs=2 * int(len(selected) >= 2),
                             confirmed_tasks=confirmed, correct_assertions=confirmed, fa_tests=fa))
    for mode in ('capped', 'uncapped'):
        for key in expected[0]:
            assert actual['primary'][mode][key] == pytest.approx(sum(m[key] for m in expected) / 252)
        assert actual['primary'][mode]['precision'] == pytest.approx(sum(m['correct_assertions'] for m in expected) / sum(m['tests'] for m in expected))


def test_subset_control_preserves_invalid_slots_and_empty_tc_tasks():
    record, truth = toy_record()
    record['families']['tc']['valid_programs'] = []
    for row in record['inputs'].values():
        row['programs']['tc'] = {}
    meta, result = O.subset_mean(record, record['inputs'], truth)
    assert meta['subsets'] == 252
    assert result['primary']['capped']['tests'] == result['primary']['capped']['eligible_inputs'] == 0


def test_paired_k5_eligibility_is_conditioned_on_each_subset():
    record, truth = toy_record()
    record['families']['defn'] = dict(valid_programs=[0, 1])
    for row in record['inputs'].values():
        row['programs']['defn'] = {'0': ok(1), '1': ok(1)}
    result = O.paired_k5(record, record['inputs'], truth, 'defn')
    # With seven valid tc slots, every size-five subset has at least two valid programs.
    assert result['inputs'] == pytest.approx(2)
    assert result['families']['defn']['primary']['capped']['confirmed_tasks'] == 1
    record['families']['tc']['valid_programs'] = [0, 1]
    for row in record['inputs'].values():
        row['programs']['tc'] = {k: v for k, v in row['programs']['tc'].items() if k in ('0', '1')}
    result = O.paired_k5(record, record['inputs'], truth, 'defn')
    chance = sum(0 in s and 1 in s for s in itertools.combinations(range(10), 5)) / 252
    assert result['inputs'] == pytest.approx(2 * chance)
    assert result['families']['defn']['primary']['capped']['confirmed_tasks'] == pytest.approx(chance)


def decision_row(cid, pid, a=1, b=0, fa_a=0, fa_b=0):
    return dict(case_id=str(cid), problem_id=pid, input_sets={'decisive': {
        'defn': dict(primary=dict(capped=dict(confirmed_tasks=a, fa_tests=fa_a))),
        'brute': dict(primary=dict(capped=dict(confirmed_tasks=b, fa_tests=fa_b)))}})


def test_problem_span_not_task_count_and_losses_reduce_margin():
    rows = [decision_row(i, 'duplicate') for i in range(3)]
    assert O.comparison(rows, 'defn', 'brute')['verdict'] == 'NO-GO'
    rows = [decision_row(i, str(i)) for i in range(3)]
    assert O.comparison(rows, 'defn', 'brute')['verdict'] == 'GO'
    rows.append(decision_row(4, 'fourth', a=0, b=1))
    assert O.comparison(rows, 'defn', 'brute')['verdict'] == 'NO-GO'
    rows[0]['input_sets']['decisive']['defn']['primary']['capped']['fa_tests'] = 1
    assert not O.comparison(rows[:3], 'defn', 'brute')['checks']['fa_no_worse']


def test_problem_id_uses_spec_only():
    def case(body):
        return dict(source='def f(x):\n    "same task"\n    ' + body, entry='f', base='', valid_code=None)
    assert O.problem_id(case('return x')) == O.problem_id(case('return x + 1'))
    assert O.problem_id(case('return x')) != O.problem_id(dict(case('return x'), source='def f(x):\n    "other task"\n    return x'))


def test_code_block_extracts_defn_sample_and_preserves_concept_comments():
    # Same response form as the saved v49/defn/3/0 record; standalone public-only fixture.
    text = ('Explanation outside the fenced block.\n```python\n'
            'def f(nums):\n    # ENUMERATE: all splits\n    # CHECK: nondecreasing segment sums\n'
            '    # AGGREGATE: maximum segment count\n    return len(nums)\n```\nTrailing text.')
    source = O.code_block(text)
    assert source.startswith('def f(') and '```' not in source and 'Trailing' not in source
    assert all(m in source for m in O.MARKERS)
    ast.parse(source)
    case = dict(source='def f(nums): return len(nums)', entry='f')
    assert all(O.audit(case, source)['concept_comments'].values())
    assert not any(O.audit(case, 'def f(nums):\n    s = "# ENUMERATE:"\n    return 0')['concept_comments'].values())


def test_ast_proxy_reports_literal_wrapper_and_implementation():
    case = dict(source='class Solution:\n    def f(self, x): return x\ndef f(x):\n    "spec"\n    return Solution().f(x)', entry='f')
    copied = O.audit(case, 'class Solution:\n    def f(self, x): return x')
    changed = O.audit(case, 'class Solution:\n    def f(self, x): return 12345')
    assert copied['entry_ast_similarity'] == changed['entry_ast_similarity'] == 1
    assert copied['implementation_ast_similarity'] == 1
    assert changed['implementation_ast_similarity'] < 1


def test_real_worker_two_second_validity_timeout_keeps_next_public_call(tmp_path):
    source = 'import time\ndef f(x):\n    if x == 0: time.sleep(4)\n    return x\n'
    result = O.batch(tmp_path / 'two_seconds', {'p0': source}, ['p0'], 'f', ['(0,)', '(1,)'], 2)
    assert result['p0'] == [['timeout'], ok(1)]
    assert O.rejection([ok(0), ok(1)], result['p0']) == ['timeout']
    job = json.loads((tmp_path / 'two_seconds' / 'job.json').read_text())
    assert job['per_call_timeout'] == 2 and job['max_timeouts'] == 3


def test_batch_cache_key_includes_call_limit(tmp_path, monkeypatch):
    calls = []
    def sandbox(python, worker, job, output, timeout):
        calls.append(json.loads(job.read_text())['per_call_timeout'])
        result = {'p0': [ok(1)]}
        output.write_text(json.dumps(result))
        return result
    monkeypatch.setattr(O.E.oracle, 'sandbox', sandbox)
    args = (tmp_path, {'p0': 'def f(x): return x'}, ['p0'], 'f', ['(1,)'])
    O.batch(*args, 2)
    O.batch(*args, 2)
    O.batch(*args, 1)
    assert calls == [2, 1]


def test_crash_fallback_is_per_program_chunk_and_root_restored(tmp_path, monkeypatch):
    original = O.E.oracle.OUT
    calls = []
    def batch(path, sources, order, entry, inputs, per_call_timeout):
        calls.append((tuple(order), len(inputs), per_call_timeout))
        if order == ['p1'] or (len(inputs) > O.SUBCHUNK and inputs[0] == '(0,)'):
            raise RuntimeError('crash')
        return {order[0]: [ok(1)] * len(inputs)}
    monkeypatch.setattr(O, 'batch', batch)
    inputs = [repr((i,)) for i in range(O.CHUNK + 30)]
    with O.E.execution_root(tmp_path):
        result = O.run_programs(dict(case_id='3', source='def f(x): return x', entry='f'), 'defn',
                                ['def f(x): return x', 'bad'], inputs, 'base', 2)
    # p0: first chunk crashes as a whole but every sub-chunk runs; p1 crashes everywhere -> skipped (abstains).
    assert result['p0'] == [ok(1)] * len(inputs)
    assert result['p1'] == [['skipped']] * len(inputs)
    assert all(c[0] in (('p0',), ('p1',)) and c[2] == 2 for c in calls)
    assert O.E.oracle.OUT == original


def test_metrics_unconfirmed_is_fa_and_cap_follows_sha_order():
    inputs = {repr((i,)) for i in range(25)}
    rows = {lit: dict(put=ok(0), programs=[ok(1), ok(1)], **O.votes(ok(0), [ok(1), ok(1)])) for lit in inputs}
    truth = {lit: dict(valid=True, ref=O.E.iorel.value(ok(1)), exposing=False) for lit in inputs}
    result = O.metrics(inputs, rows, truth, 2)
    assert result['primary']['capped']['tests'] == result['primary']['capped']['unconfirmed'] == 20
    assert result['primary']['capped']['fa_tests'] == 20
    assert result['primary']['uncapped']['tests'] == 25
    assert result['primary']['capped']['eligible_inputs'] == 25
    assert O.E.emitted(inputs, rows, 'primary') == O.E.ordered(inputs)[:20]


def test_status_counts_partial_records_and_overflow_without_evaluator(tmp_path, monkeypatch):
    monkeypatch.setattr(O, 'OUT', tmp_path / 'v49')
    monkeypatch.setattr(O.E.oracle, 'OUT', tmp_path / 'v46')
    monkeypatch.setattr(O.E, 'planned', lambda inv: (['3', '6'], {'3'}))
    monkeypatch.setattr(O.E.ft_run, 'FTRun', lambda *a: pytest.fail('reference loader entered'))
    for arm, finish in (('defn', 'length'), ('brute', 'context_overflow'), ('tc', 'context_overflow')):
        root = O.E.oracle.OUT if arm == 'tc' else O.OUT
        path = root / 'programs' / arm / '3' / '0.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(dict(text='', finish_reason=finish, digest='test')))
    state = O.status()
    assert state['v49_planned'] == 30 and state['v49_present'] == 2
    assert state['arms']['defn']['finish_reason']['length'] == 1
    assert state['v46_tc']['planned'] == 10 and state['v46_tc']['present'] == 1
    assert state['tc_unplanned_tasks'] == ['6'] and not state['complete']


def test_score_preflight_stops_before_references_when_incomplete(tmp_path, monkeypatch):
    monkeypatch.setattr(O, 'OUT', tmp_path)
    monkeypatch.setattr(O, 'status', lambda inv: {'complete': False})
    monkeypatch.setattr(O.E, 'planned', lambda inv: (['3'], {'3'}))
    monkeypatch.setattr(O.E.ft_run, 'FTRun', lambda *a: pytest.fail('reference loader entered'))
    incomplete, ready = O.score_inputs(O.Inventory())
    assert ready is None and incomplete['missing_execution'] == ['3']


def test_reference_redirect_restored_on_error(tmp_path):
    original = O.E.OUT
    with pytest.raises(ValueError):
        with O.reference_root(tmp_path):
            assert O.E.OUT == tmp_path
            raise ValueError('test')
    assert O.E.OUT == original


def test_task_truth_passes_diag_and_adds_lazy_official_check(tmp_path, monkeypatch):
    record, _ = toy_record()
    official, inv = object(), O.Inventory()
    original = O.E.OUT
    monkeypatch.setattr(O, 'OUT', tmp_path)
    monkeypatch.setattr(O.E.ft_run, 'FTRun', lambda *a: pytest.fail('reference loader entered'))
    def reference_truth(got_inv, case, view, got_official, diag):
        assert got_inv is inv and got_official is official
        assert O.E.OUT == tmp_path
        assert diag == {'(1,)'} and set(view['inputs']) == set(record['inputs'])
        assert all(r['vote'] is r['consensus'] is None for r in view['inputs'].values())
        return {lit: dict(exposing=None, reference_skipped=True, valid=False, ref=None) for lit in view['inputs']}
    monkeypatch.setattr(O.E, 'reference_truth', reference_truth)
    truth = O.task_truth(inv, dict(case_id='3'), record, official, {'(1,)'})
    assert set(truth) == set(record['inputs']) and O.E.OUT == original
    assert all(callable(t['exposes']) for t in truth.values())


def test_unknown_exposure_and_skipped_reference_are_reported_separately():
    record, truth = toy_record()
    record['families']['tc'].update(validation={}, crashed_base=[], crashed_universe=[], finish_reason={})
    truth['(1,)'].update(exposing=None, ref=None, reference_skipped=True)
    rows = O.oracle_rows(record, 'tc')
    d = O.diagnostics(record, 'tc', rows, truth)
    assert d['exposing_inputs'] == d['exposure_evaluated_inputs'] == 1
    assert d['exposure_uncomputed_inputs'] == d['reference_skipped_inputs'] == ['(1,)']
    assert not d['common_mode_inputs']  # all programs agree with PUT on the uncomputed input only
    totals = O.diagnostic_totals([dict(case_id='3', diagnostics={a: d for a in O.FAMILIES})])
    assert totals['tc']['exposure_uncomputed_inputs'] == totals['tc']['reference_skipped_inputs'] == 1


def test_new_metric_keys_skipped_reference_and_unknown_exposure_aggregate():
    puts = [ok(0)] * 3 + [['exception', 'ValueError'], ['timeout'], ['skipped'], ['ok', 'bad(']]
    rows = {repr((i,)): dict(put=p, programs=[ok(1), ok(1)], **O.votes(p, [ok(1), ok(1)])) for i, p in enumerate(puts)}
    truth = {lit: dict(valid=True, ref=O.E.iorel.value(ok(1)), exposing=True, reference_skipped=False) for lit in rows}
    truth['(0,)'].update(ref=None, exposing=False, reference_skipped=True)
    truth['(1,)']['exposing'] = None
    labels = O.labels_for(rows, truth)
    assert labels['(0,)']['primary'] == 'fa'
    assert labels['(1,)']['primary'] == 'unconfirmed'
    result = O.metrics(rows, rows, truth, 2)
    m = result['primary']['capped']
    assert m['tests'] == m['eligible_inputs'] == 3
    assert m['put_no_test_inputs'] == 4 and 'put_exception_inputs' not in m
    assert m['confirmed_tests'] == m['unconfirmed'] == m['reference_skipped_tests'] == 1
    assert m['fa_tests'] == 2
    totals = O.aggregate([dict(case_id='3', input_sets={s: dict(defn=result) for s in ('decisive', 'llm_code')})], {'3'})
    total = totals['decisive']['defn']['primary']['capped']
    assert total['put_no_test_inputs'] == 4 and total['reference_skipped_tests'] == 1
    assert total['confirmed_tasks_31'] == total['confirmed_tasks_33'] == 1


def test_inventory_uses_rel_for_paths_outside_repo(tmp_path, monkeypatch):
    monkeypatch.setattr(O.E, 'REPO', tmp_path / 'different_repo')
    artifact = tmp_path / 'artifact.json'
    artifact.write_text('{}')
    inv = O.Inventory()
    path = inv.add(artifact)
    assert O.E.rel(path) == str(artifact.resolve())
    assert O.E.rel(path) in inv.finish()


def test_execute_case_is_tool_only_strict_for_every_family(tmp_path, monkeypatch):
    class Inputs:
        def tree(self, path):
            pass
        def finish(self):
            return {}
    case = dict(case_id='3', entry='f', source='def f(x):\n    "task"\n    return x', base='', valid_code=None)
    monkeypatch.setattr(O.E, 'pool_inputs', lambda *a: ['(0,)'])
    monkeypatch.setattr(O.E, 'all_inputs', lambda *a: {'(1,)'})
    monkeypatch.setattr(O.E.ft_run, 'base_inputs', lambda *a: [(0,), (1,)])
    monkeypatch.setattr(O.E.ft_run, 'FTRun', lambda *a: pytest.fail('reference loader entered'))
    called = []
    def run(case, arm, srcs, inputs, tag, per_call_timeout=1):
        called.append((arm, tag, per_call_timeout))
        result = {f'p{i}': [ok(ast.literal_eval(lit)[0]) for lit in inputs] for i in range(len(srcs))}
        if tag == 'base' and arm in O.FAMILIES:
            result['p0'][0] = ['timeout']
        return result
    monkeypatch.setattr(O, 'run_programs', run)
    loaded = {a: dict(planned=5, present=2, missing=[2, 3, 4], context_overflow=[],
                     finish_reason={'0': 'stop', '1': 'stop'}, sources={0: 'def f(x): return x', 1: 'def f(x): return x'}) for a in O.FAMILIES}
    summary = O.execute_case(Inputs(), case, {}, loaded, tmp_path)
    record = json.loads((tmp_path / 'tasks' / '3.json').read_text())
    assert summary['inputs'] == 2
    assert summary['put_no_test_inputs'] == 0 and 'put_exception_inputs' not in summary
    for family in O.FAMILIES:
        f = record['families'][family]
        assert f['valid_programs'] == [1]
        assert f['validation']['0']['reason'] == 'timeout' and f['validation']['0']['resource_only']
        assert all(set(row['programs'][family]) == {'1'} for row in record['inputs'].values())
    assert all(limit == (2 if tag == 'base' else 1) for _, tag, limit in called)


def test_problem_span_uses_per_problem_net():
    def row(cid, pid, a, b):
        cell = lambda c: dict(primary=dict(capped=dict(confirmed_tasks=c, fa_tests=0)))
        return dict(case_id=cid, problem_id=pid, input_sets=dict(decisive=dict(defn=cell(a), brute=cell(b))))
    # Review case: defn-only 46/75/77 (P1), 3 (P2), 61 (P3); brute-only 96 (P2), 65 (P3): all net from P1.
    rows = [row('46', 'P1', 1, 0), row('75', 'P1', 1, 0), row('77', 'P1', 1, 0), row('3', 'P2', 1, 0), row('96', 'P2', 0, 1),
            row('61', 'P3', 1, 0), row('65', 'P3', 0, 1)]
    c = O.comparison(rows, 'defn', 'brute')
    assert c['task_margin'] == 3 and c['extra_problems'] == ['P1'] and c['verdict'] == 'NO-GO'
    rows += [row('90', 'P4', 1, 0), row('91', 'P5', 1, 0)]
    assert O.comparison(rows, 'defn', 'brute')['verdict'] == 'GO'
