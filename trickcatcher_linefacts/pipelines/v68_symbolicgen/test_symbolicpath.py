"""v66 regressions: CrossHair construction + native replay on authored constructs (engineering only)."""
import json
from pathlib import Path

import pytest

from . import hypotheses, path_instrument, value_graph
from .crosshair_construct import construct

CFG = dict(json.loads((Path(__file__).parent / 'config.json').read_text())['symbolicpath'], case_timeout_seconds=15)


def pick(source, entry, before, after):
    rows, _ = hypotheses.catalog(source, entry, cap=200)
    return next(r for r in rows if r['before'] == before and r['after'] == after)


def run(source, entry, seeds, before, after, **extra):
    return construct(source, entry, seeds, pick(source, entry, before, after), dict(CFG, **extra))


def verified(report):
    json.loads(json.dumps(report))  # artifacts must be plain JSON (no CrossHair shell containers)
    assert report['status'] == 'verified_behavioral_difference', report
    assert all(type(row) is dict for row in report['inputs'])
    for row in report['inputs']:
        assert row['verification'] == 'exact_site_prestate_path_and_output_replayed'
    return [row['arguments'] for row in report['inputs']]


HELPER = '''def f(xs, k):
    def bump(v):
        nonlocal total
        total += v
    total = 0
    for x in xs:
        if x > k:
            bump(x)
    return total
'''


def test_nested_helper_nonlocal_accumulation():
    assert verified(run(HELPER, 'f', [([1, 2], 5)], 'x > k', 'x >= k'))


def test_listcomp_dict_and_joint_conditions():
    src = '''def f(xs, k):
    seen = {}
    for x in xs:
        seen[x] = seen.get(x, 0) + 1
    if k > 0 and len(xs) == k + 2:
        return len(set(xs)) + sum([y for y in xs if y > k])
    return 0
'''
    args = verified(run(src, 'f', [([1, 2], 5)], 'len(set(xs))', 'len(xs)'))
    for text in args:
        xs, k = eval(text)
        assert k > 0 and len(xs) == k + 2 and len(set(xs)) < len(xs)


def test_store_subscript_index_site():
    src = '''def f(xs):
    out = [0] * (len(xs) + 2)
    for i in range(len(xs)):
        out[i] = xs[i]
    return out[0]
'''
    assert verified(run(src, 'f', [([1, 2],)], 'out[i]', 'out[i + 1]'))


def test_defaultdict_and_while():
    src = '''import collections
def f(s):
    c = collections.defaultdict(int)
    i = 0
    while i < len(s):
        c[s[i]] += 1
        i += 1
    return max(c.values()) if c else 0
'''
    for text in verified(run(src, 'f', [('ab',)], 'max(c.values())', 'min(c.values())')):
        s = eval(text)[0]
        assert len(set(s.count(ch) for ch in s)) > 1
    # Off-by-one loop guard only raises IndexError: exception paths, no witness.
    report = run(src, 'f', [('ab',)], 'i < len(s)', 'i <= len(s)')
    assert report['status'] in ('bounded_no_witness', 'unknown_timeout_or_cap') and 'exception:IndexError' in report['path_outcomes']


def test_exception_paths_are_never_witnesses():
    src = '''def f(xs):
    return xs[len(xs) - 1]
'''
    report = run(src, 'f', [([1, 2],)], 'len(xs) - 1', 'len(xs) + 1')
    assert report['status'] != 'verified_behavioral_difference'
    assert any(k.startswith('exception:') for k in report['path_outcomes'])


def test_sorting_bisect_and_ceil():
    src = '''import bisect, math
def f(xs, t):
    ys = sorted(xs)
    k = bisect.bisect_right(ys, t)
    if k > 1:
        return math.ceil(k / 2)
    return 0
'''
    for text in verified(run(src, 'f', [([3, 1], 2)], 'k > 1', 'k >= 1')):
        xs, t = eval(text)
        assert sum(1 for x in xs if x <= t) == 1


def test_seeded_random_replays_deterministically():
    src = '''import random
def f(n):
    rng = random.Random(7)
    xs = list(range(4))
    rng.shuffle(xs)
    return xs[0] + n if n > 2 else 0
'''
    r = run(src, 'f', [(1,)], 'n > 2', 'n >= 2')
    assert r['status'] in ('verified_behavioral_difference', 'bounded_no_witness')
    for row in r['inputs']:
        assert eval(row['arguments']) == (2,)


def test_unseeded_global_random_is_not_certified():
    src = '''import random
def f(n):
    return random.randint(0, 9) + n if n > 2 else 0
'''
    r = run(src, 'f', [(1,)], 'n > 2', 'n >= 2')
    assert r['status'] != 'verified_behavioral_difference' or all(
        row['observations']['runs'][0] == row['observations']['runs'][1] for row in r['inputs'])


def test_annotation_sites_excluded_from_catalog():
    src = '''from typing import List
def f(xs: List[int]) -> List[int]:
    return [xs[0]]
'''
    rows, _ = hypotheses.catalog(src, 'f', cap=200)
    assert all(r['before'] != 'List[int]' for r in rows)


def test_aliasing_preserved_by_value_graph():
    shared = [1, 2]
    graph = value_graph.encode(([shared, shared], 3))
    decoded = value_graph.decode(graph)
    assert decoded[0][0] is decoded[0][1]
    assert value_graph.encode(decoded) == graph


def test_site_inside_comprehension_records_comprehension_variable():
    src = '''def f(xs):
    return sum([y for y in xs if y > 1])
'''
    h = pick(src, 'f', 'y > 1', 'y >= 1')
    rec = path_instrument.Recorder()
    fn = path_instrument.load_program(src, 'f', h, recorder=rec)
    assert fn([1, 2]) == 2 and rec.events and all(dict(e[0][2]).get('y') is not None for e in rec.events)


def test_external_proposal_with_new_call_rejected():
    src = '''def f(x):
    return x + 1
'''
    h = dict(pick(src, 'f', 'x + 1', 'x - 1'), after='print(x)', origin='external_proposal')
    with pytest.raises(ValueError):
        path_instrument.instrument(src, h, variant=True)
