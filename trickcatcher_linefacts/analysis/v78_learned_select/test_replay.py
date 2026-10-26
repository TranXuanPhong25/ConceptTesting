import math

import pytest

from trickcatcher_linefacts.analysis.v78_learned_select import replay as r


def task():
    items = [dict(id=f'M{i+1}', kind=k, instance=f'arg0:{i}', text=k) for i, k in enumerate(['class', 'boundary', 'mutation', 'class'])]
    bundles = [['a', 'b'], ['b', 'c'], ['a'], ['d']]
    ys = [1, 0, 0, 0]
    return dict(cid='synthetic', items=items, bundles=bundles, y=ys, triples=r.triple_table(ys, bundles, items))


def test_exact_tie_and_cost():
    t = task()
    got = r.evaluate_policy(t, [0, 0, 0, 0])
    assert got['reach'] == .75
    assert got['tie_subsets'] == 4
    assert got['unique_inputs'] == pytest.approx(t['triples']['uniform']['unique_inputs'])
    assert r.evaluate_policy(t, [3, 2, 1, 0])['representative_picks'] == ['M1', 'M2', 'M3']
    assert got['cost_random'] <= 1


def test_per_kind_weights_match_bruteforce():
    t = task()
    # All three distinct kinds must be represented: one of the two class items.
    assert t['triples']['per_kind']['reach'] == .5
    assert t['triples']['per_kind']['mass'] == 1
    assert t['triples']['cost_random'][3] == 1
    assert t['triples']['cost_random'][4] == .75


def test_rounding_and_partial_tie():
    assert r.tie_choices([2, 1, 1, 1, 0]) == [(0, 1, 2), (0, 1, 3), (0, 2, 3)]
    assert len(r.tie_choices([0, 1e-14, 0, 0])) == 4


def test_historical_typed_tolerance():
    assert not r.same(r.observation(['ok', 'True']), r.observation(['ok', '1']))
    assert r.same(r.observation(['ok', '[1.0]']), r.observation(['ok', '[1.0000001]']))
    assert not r.same(r.observation(['ok', '[1.0]']), r.observation(['ok', '[1.01]']))
    assert r.observation(['timeout', '']) is None
    assert r.observation(dict(status='ok', output_repr='None'), official=True) == ('ok', ('NoneType', None))
    assert r.observation(dict(status='ok', output_repr=None), official=True) is None


def test_feature_allowlist_and_spec_only():
    public = dict(spec='Return sorted unique numbers', code='def f(xs):\n return sorted(set(xs))\n', entry='f')
    spec = r.context_features(public, 'spec-only')
    code = r.context_features(public, 'spec+code')
    assert all(k.startswith('spec:') for k in spec)
    assert code['call:set'] == 1 and code['call:sorted'] == 1
    item = dict(id='M999', kind='class', instance='arg2:singleton', text='xs: a single element', covered=True, case_id='SECRET')
    features = r.candidate_features(item, ['([1],)'], code)
    assert not any('SECRET' in k or 'M999' in k or 'covered' in k for k in features)
    item.update(id='changed', case_id='other', covered=False)
    assert features == r.candidate_features(item, ['([1],)'], code)
    assert r.normalize(dict(kind='mutation', instance='m12345'))[0] == 'mutation:mutation'


def test_training_does_not_read_heldout_labels():
    train = [dict(cid=str(i), group=str(i), y=[i % 2, 1-i % 2], x=[{'a': 1.}, {'b': 1.}]) for i in range(4)]
    test = dict(y=[0, 0], x=[{'a': 1.}, {'new_only_in_test': 1.}])
    scores = r.fit_scores(train, test, 'x')
    test['y'] = [1, 1]
    assert scores == r.fit_scores(train, test, 'x')
    assert all(math.isfinite(x) for x in scores)


def test_priors_task_balanced_and_fallback():
    item = dict(kind='class', instance='arg0:singleton')
    other = dict(kind='class', instance='arg0:all_equal')
    train = [dict(group='a', items=[item]*10, y=[1]*10), dict(group='b', items=[item], y=[0])]
    assert r.prior_scores(train, dict(items=[other]), True) == [.5]
    assert r.prior_scores(train, dict(items=[item]), True) == [.5]
    train.append(dict(group='a', items=[item], y=[1]))
    assert r.prior_scores(train, dict(items=[item]), True) == [.5]


def test_missing_cache_fails_closed(tmp_path):
    with pytest.raises(FileNotFoundError):
        r.Cache().read(tmp_path / 'missing.json')


def test_zero_exposure_and_full_exposure():
    t = task()
    for ys in ([0]*4, [1]*4):
        table = r.triple_table(ys, t['bundles'], t['items'])
        assert table['uniform']['reach'] == ys[0]
        assert table['per_kind']['reach'] == ys[0]


def test_per_kind_historical_fewer_than_three_kinds():
    t = task()
    items = [dict(it, kind='class') for it in t['items']]
    got = r.triple_table(t['y'], t['bundles'], items)['per_kind']
    assert got['candidate_count'] == 1
    assert got['reach'] == .25
    assert got['unique_inputs'] == 1.5


def test_problem_group_exclusion_and_cluster_bootstrap():
    tasks = [dict(cid='a1', group='a'), dict(cid='a2', group='a'), dict(cid='b', group='b')]
    assert r.training_tasks(tasks, tasks[0]) == [tasks[2]]
    got = r.bootstrap_difference([1, 1, 0], [0, 0, 1], ['a', 'a', 'b'])
    assert got['task_total_difference'] == 1
    assert got['groups'] == 2
    assert got['ci95'] == [-2, 4]
