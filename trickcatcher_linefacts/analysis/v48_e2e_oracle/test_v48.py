"""Reference-free CPU checks, using synthetic outcomes and public tool artifacts only."""
import ast
import hashlib
import itertools
import json
import random
from pathlib import Path

import pytest

from trickcatcher_linefacts.analysis.v48_e2e_oracle import e2e as E, menu_fixed as F


def ok(v):
    return ['ok', repr(v)]


def test_vote_singleton_and_ties():
    assert E.vote(ok(0), [ok(1)])[0] == E.iorel.value(ok(1))
    assert E.vote(ok(0), [ok(2), ok(1)])[0] == E.iorel.value(ok(2))
    assert E.vote(ok(0), [ok(2), ok(1), ok(1)])[0] == E.iorel.value(ok(1))
    assert E.vote(ok(0), [ok(2), ok(1), ok(1), ok(2)])[0] == E.iorel.value(ok(2))


def test_vote_none_is_a_value_and_equality_is_typed():
    assert E.vote(ok(0), [ok(None)])[0] == E.iorel.value(ok(None))
    assert E.vote(ok(None), [ok(None)]) == (None, None)
    assert E.vote(ok(1), [ok(True)])[0] == E.iorel.value(ok(True))
    assert E.vote(ok(1), [ok(1.0)])[0] == E.iorel.value(ok(1.0))


@pytest.mark.parametrize('put', [['exception', 'ValueError'], ['timeout'], ['skipped'], ['ok', 'bad(']])
def test_put_failure_emits_nothing(put):
    assert E.vote(put, [ok(1)] * 3) == (None, None)


def test_exclude_unusable_variants_and_consensus():
    assert E.vote(ok(0), [['timeout'], ['exception', 'ValueError'], ['ok', 'bad('], ok(2)])[0] == E.iorel.value(ok(2))
    assert E.vote(ok(0), [ok(2), ok(2)])[1] is None
    assert E.vote(ok(0), [ok(2)] * 3)[1] == E.iorel.value(ok(2))
    assert E.vote(ok(0), [ok(None)] * 3)[1] == E.iorel.value(ok(None))
    assert E.vote(ok(0), [ok(2)] * 3 + [['timeout']])[1] is None
    assert E.vote(ok(0), [ok(0)] * 3) == (None, None)


def synthetic_rows(n=30):
    return {repr((i,)): dict(put=ok(0), programs={'p0': ok(1)}, vote=ok(1), consensus=None) for i in range(n)}


@pytest.mark.parametrize('value', [None, b'bytes', [1, (2, None)], {'key': [1.0, None]}, 1.0000001])
def test_persisted_vote_preserves_v46_equality_after_json(value):
    v, c = E.raw_votes(ok(0), [ok(value)] * 3)
    saved = json.loads(json.dumps(dict(vote=v, consensus=c)))
    ref = E.iorel.value(ok(value))
    assert E.same(E.iorel.value(saved['vote']), ref)
    assert E.same(E.iorel.value(saved['consensus']), ref)
    assert E.judge(E.iorel.value(saved['vote']), ok(None), ref, E.iorel.value(ok(0)), lambda: True) == 'confirmed'


def test_sha_order_and_cap_identical_across_arms():
    rows = synthetic_rows()
    inputs = list(rows)
    expected = sorted(inputs, key=lambda l: hashlib.sha256(l.encode()).hexdigest())[:20]
    for batch in (inputs, inputs[::-1], set(inputs), inputs + inputs):
        assert E.emitted(batch, rows) == expected
    # The cap applies to emitted tests, after abstentions have been removed.
    rows[expected[0]]['vote'] = None
    assert len(E.emitted(inputs, rows)) == 20
    assert len(E.emitted(inputs, rows, cap=None)) == 29


def toy():
    items = [dict(id=f'M{i + 1}', kind='class' if i < 3 else 'boundary', instance=str(i)) for i in range(5)]
    prep = dict(kinds={'class': {'0': ['(0,)', '(1,)'], '1': ['(1,)'], '2': ['(2,)']},
                      'boundary': {'3': ['(3,)'], '4': ['(0,)', '(4,)']}})
    rows = synthetic_rows(5)
    labels = {lit: dict(vote='confirmed' if lit == '(4,)' else 'fa', consensus='fa') for lit in rows}
    return items, prep, rows, labels


def test_random3_exact_matches_ordered_bruteforce():
    items, prep, rows, labels = toy()
    batches = [E.item_inputs(prep, b) for b in E.random3(items)]
    count, actual = E.expectation(batches, rows, labels)
    brute = []
    for p in itertools.permutations(items, 3):
        brute.append(E.metric(E.item_inputs(prep, p), rows, labels, 'vote', 20))
    assert count == 10
    for key in E.METRICS:
        assert actual['vote']['capped'][key] == pytest.approx(sum(x[key] for x in brute) / len(brute))
    assert len(list(E.random3(items[:2]))) == 1


def test_random3_runs_union_and_cap_before_scoring():
    rows = synthetic_rows(40)
    items = [dict(kind='class', instance=str(i)) for i in range(4)]
    prep = dict(kinds={'class': {str(i): [repr((j,)) for j in range(i * 10, (i + 1) * 10)] for i in range(4)}})
    target = E.ordered(rows)[-1]
    labels = {l: dict(vote='confirmed' if l == target else 'fa', consensus='fa') for l in rows}
    batches = [E.item_inputs(prep, b) for b in E.random3(items)]
    _, actual = E.expectation(batches, rows, labels)
    assert actual['vote']['capped']['correct_assertions'] == 0
    assert actual['vote']['uncapped']['correct_assertions'] == 0.75
    assert actual['vote']['capped']['tests'] == 20
    assert actual['vote']['uncapped']['tests'] == 30


def test_kind_matched_preserves_counts_and_exact_weighting():
    items, _, _, _ = toy()
    actual = list(E.kind_matched(items, [items[0], items[1], items[3]]))
    expected = [b for b in itertools.combinations(items, 3) if sum(i['kind'] == 'class' for i in b) == 2]
    assert {frozenset(i['id'] for i in b) for b in actual} == {frozenset(i['id'] for i in b) for b in expected}
    assert len(actual) == 6
    assert list(E.kind_matched(items, [])) == [()]


def test_count_matched_exact_and_seeded_deterministic():
    meta, it = E.count_matched(['(1,)', '(2,)', '(3,)'], 2, 'toy')
    assert meta['method'] == 'exact' and len(list(it)) == 3
    u = [repr((i,)) for i in range(40)]
    meta, a = E.count_matched(u, 10, 'toy', exact_max=1, draws=30)
    _, b = E.count_matched(u[::-1], 10, 'toy', exact_max=1, draws=30)
    draws = list(a)
    assert draws == list(b) and len(draws) == 30 and all(len(set(d)) == 10 for d in draws)
    assert meta['method'] == 'seeded_draws'
    assert list(E.count_matched([], 0, 'toy')[1]) == [()]
    with pytest.raises(ValueError):
        E.count_matched(u, 41, 'toy')


def test_pool_subset_is_seeded_and_capped():
    u = [repr((i,)) for i in range(1000)]
    assert E.pool_subset(u, '3') == random.Random('v48/pool/3').sample(u, 600)
    assert len(E.pool_subset(['(1,)', '(1,)'], '3')) == 1


@pytest.mark.parametrize('text,key,bounds', [
    ('-100 <= nums[i] <= 10**9', (0, 'elem'), (-100, 10**9)),
    ('0 <= len(nums) <= 30', (0, 'length'), (0, 30)),
    ('1 <= nums[i] <= 10^9', (0, 'elem'), (1, 10**9)),
    ('1 < nums.length < 30', (0, 'length'), (2, 29)),
    ('-2 * 10**9 <= nums[i][j] <= 2*10^9', (0, 'elem2'), (-2*10**9, 2*10**9)),
])
def test_constraints(text, key, bounds):
    assert F.constraints(text, ['nums']) == {key: bounds}


@pytest.mark.parametrize('text', ['0 <= nums[i] <= 10**limit', '0 <= nums[i] <= 10**',
                                      '0 <= nums[i] <= 10^', '0 <= nums[i] <= 10**999', '0 <= nums[i] <= 10**9 + 1'])
def test_unsupported_bounds_are_never_truncated(text):
    cons, report = F.constraints_report(text, ['nums'])
    assert not cons and report
    with pytest.raises(ValueError):
        F.constraints(text, ['nums'])


def test_per_argument_range_does_not_use_other_arguments():
    xs = [([1, 2], 10**9)]
    cons = {(0, 'elem'): (1, 1000), (1, 'value'): (1, 10**9)}
    inst = F.spec_range_members('toy', xs, cons)
    assert 'arg0:elem_spread_all' in inst
    assert F.argument_range(xs, 0, 'elem') == (1, 2)
    assert all(1 <= n <= 1000 for l in inst['arg0:elem_spread_all'] for n in ast.literal_eval(l)[0])


def test_set_dedupe_within_kind_and_across_menu():
    a, b = '(1,)', '(2,)'
    d = F.dedupe({'first': [a, b], 'second': [b, a]})
    assert list(d) == ['first'] and d['first']['merged'] == 1
    kinds = {k: {} for k in F.INPUT_KINDS}
    kinds['class'] = {'arg0:singleton': dict(flagged=[a, b])}
    kinds['boundary'] = {'arg0:elem_all_min': dict(flagged=[b, a])}
    result = F.menu(kinds, ['nums'], {}, {}, 'toy', 'spec+code')
    assert len(result['items']) == 1 and result['merged'] == 1


@pytest.mark.parametrize('lo,hi', [(-10**9, -100), (-1000, 1000), (-10, 0), (-1, -1), (0, 0), (3, 10**9)])
def test_negative_log_uniform(lo, hi):
    rng = random.Random('toy')
    values = [F.log_uniform(rng, lo, hi) for _ in range(1000)]
    assert all(lo <= v <= hi for v in values)
    if lo < 0 < hi:
        assert min(values) < 0 and max(values) > 0 and 0 in values
    if lo < hi < 0:
        assert len(set(values)) > 30


def test_cache_requires_matching_prompt_digest(tmp_path):
    path = tmp_path / 'call.json'
    msgs = [{'role': 'user', 'content': 'toy'}]
    sha = hashlib.sha256(json.dumps(msgs, sort_keys=True).encode()).hexdigest()
    path.write_text(json.dumps(dict(text='{}', prompt_sha256=sha)))
    assert F.cached_call(path, msgs)['text'] == '{}'
    with pytest.raises(ValueError):
        F.cached_call(path, [{'role': 'user', 'content': 'changed'}])


def test_kind_build_error_marks_case_incomplete(monkeypatch):
    case = dict(case_id='toy', source='def f(nums): return 0', entry='f', base='', valid_code=None)
    class Inputs:
        def read(self, path):
            return {'put': [ok(0)]}
    monkeypatch.setattr(E, 'pool_inputs', lambda *a: ['([1],)'])
    monkeypatch.setattr(F.ft_run, 'base_inputs', lambda *a: [([1],)])
    monkeypatch.setattr(F.iorel, 'sample', lambda *a: [([1],)])
    monkeypatch.setattr(F, 'coverage_cached', lambda *a: (_ for _ in ()).throw(ValueError('toy failed')))
    monkeypatch.setattr(F.M, 'mutation', lambda *a: {})
    monkeypatch.setattr(F.old, 'mutant_texts', lambda *a: {})
    result = F.prepare_case(case, Inputs())
    assert result['complete'] is False and 'coverage' in result['errors']


def test_judge_none_value_and_unconfirmed():
    value, put = E.iorel.value(ok(None)), E.iorel.value(ok(0))
    assert E.judge(value, ok(None), value, put, lambda: True) == 'confirmed'
    assert E.judge(value, ok(None), value, put, lambda: False) == 'unconfirmed'
    assert E.judge(value, ['exception', 'AssertionError'], value, put, lambda: True) == 'fa'
    rows = synthetic_rows(1)
    labels = {'(0,)': dict(vote='unconfirmed')}
    m = E.metric(rows, rows, labels, 'vote', 20)
    assert m['fa_tests'] == m['unconfirmed'] == 1


def test_smoke_redirect_restores_v46_root_even_on_error():
    original = E.oracle.OUT
    with pytest.raises(ValueError):
        with E.execution_root(E.OUT / 'smoke'):
            assert E.oracle.OUT == E.OUT / 'smoke'
            raise ValueError('toy')
    assert E.oracle.OUT == original


def test_status_skips_error_and_empty_menu_and_counts_overflow(tmp_path, monkeypatch):
    v47, v46 = tmp_path / 'v47', tmp_path / 'v46'
    monkeypatch.setattr(E.select, 'OUT', v47)
    monkeypatch.setattr(E.oracle, 'OUT', v46)
    monkeypatch.setattr(E, 'planned', lambda inv: (['3', '6', '9'], {'3'}))
    def forbidden(*args, **kwargs):
        raise AssertionError('status must not execute or instantiate the evaluator loader')
    monkeypatch.setattr(E.oracle, 'run_programs', forbidden)
    monkeypatch.setattr(E.ft_run, 'FTRun', forbidden)
    v47.mkdir()
    prep = {'3': dict(menus={a: dict(items=[dict(id='M1')]) for a in E.select.ARMS}),
            '6': dict(error='toy'), '9': dict(menus={a: dict(items=[]) for a in E.select.ARMS})}
    (v47 / 'prepared.json').write_text(json.dumps(prep))
    for a in E.select.ARMS:
        p = v47 / 'calls' / '3' / f'{a}.json'
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(dict(text='{}', finish_reason='stop')))
    for i in range(10):
        p = v46 / 'programs' / 'tc' / '3' / f'{i}.json'
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(dict(text='', finish_reason='context_overflow', digest='toy')))
    result = E.status()
    assert result['complete'] and result['v47']['planned'] == 2 and len(result['skipped_v47']) == 4
    assert result['v46_tc']['planned'] == result['v46_tc']['present'] == result['v46_tc']['context_overflow'] == 10
    p.unlink()
    assert not E.status()['complete']


def test_failure_decomposition_and_fa_split():
    rows = synthetic_rows(4)
    truth = {lit: dict(valid=True, ref=E.iorel.value(ok(2)), exposing=True, vote='fa') for lit in rows}
    # One correct variant loses the vote; invalid and PUT-right alarms have separate buckets.
    rows['(0,)']['programs']['p1'] = ok(2)
    truth['(1,)']['valid'] = False
    truth['(2,)'].update(ref=E.iorel.value(ok(0)), exposing=False)
    truth['(3,)'].update(ref=E.iorel.value(ok(1)), vote='unconfirmed')
    d = E.decomposition(rows, rows, truth, [0, 1])
    assert d['c_vote_wrong'] == ['(0,)'] and d['d_emitted_wrong_value']
    assert d['fa_split']['uncapped'] == dict(invalid_input=1, put_right=1, put_wrong_wrong_value=1, unconfirmed_official=1)
    assert not d['e_no_valid_program']
    for row in rows.values():
        row['programs'] = {'p0': ok(0)}
    assert E.decomposition(rows, rows, truth, [0])['b_common_mode']
    assert E.decomposition(rows, rows, truth, [])['e_no_valid_program']


def test_inventory_detects_changed_artifact(tmp_path):
    p = tmp_path / 'artifact.json'
    p.write_text('{}')
    inv = E.Inventory()
    inv.add(p)
    p.write_text('{"changed": true}')
    with pytest.raises(ValueError, match='changed during run'):
        inv.add(p)


def test_decision_uses_every_amendment_control():
    arms = {a: dict(vote=dict(capped=dict(confirmed_tasks=1, fa_tests=0)))
            for a in ('llm_code', 'random3', 'menu_matched', 'pool_matched', 'kind_matched', 'heuristic')}
    arms['llm_code']['vote']['capped']['confirmed_tasks'] = 4
    assert E.decision(arms)['verdict'] == 'GO'
    arms['menu_matched']['vote']['capped']['confirmed_tasks'] = 2
    assert E.decision(arms)['verdict'] == 'NO-GO'


def test_primary_failure_and_exposing_classes():
    rows = synthetic_rows(2)
    truth = {lit: dict(valid=True, ref=E.iorel.value(ok(2)), exposing=True, vote='fa') for lit in rows}
    for row in rows.values():
        row['programs'], row['vote'] = {'p0': ok(0)}, None
    d = E.decomposition(rows, rows, truth, [0])
    assert d['primary'] == 'b_common_mode' and d['exposing_classes'] == dict(common_mode=2)
    for row in rows.values():
        row['programs'] = {'p0': ['timeout']}
    assert E.decomposition(rows, rows, truth, [0])['primary'] == 'b2_variants_failed'
    for lit in truth:
        truth[lit]['exposing'] = False
    assert E.decomposition(rows, rows, truth, [0])['primary'] == 'a_no_exposing_input'
    assert E.decomposition(rows, rows, truth, [])['primary'] == 'e_no_valid_program'
