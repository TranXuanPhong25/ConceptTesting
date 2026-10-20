"""CPU tests for v31 fault-template concepts (no model, no reference). Run with the V4 python:
  PYTHONPATH=. $V4_PYTHON -m pytest -q trickcatcher_linefacts/pipelines/v31_faulttemplate/test_faulttemplate.py
"""
import json
import tempfile
from pathlib import Path

from . import ft_concepts as fc
from . import ft_run

PUT = '''def count_below(xs, k):
    """Count elements strictly below k."""
    n = 0
    for x in xs:
        if x <= k:
            n += 1
    return n
'''


def m(family, before='a', after='b', boundary=False):
    return dict(family=family, before=before, after=after, boundary=boundary)


def test_fault_type_mapping():
    assert fc.fault_type(m('ROR', '<', '<=', True), 'if x < k:') == 'BOUNDARY'
    assert fc.fault_type(m('ROR', '==', '!='), 'if x == k:') == 'OPERATOR'
    assert fc.fault_type(m('CRP constant', '1', '2'), 'for i in range(1, n):') == 'BOUNDARY'
    assert fc.fault_type(m('CRP constant', '1', '2'), 'total = 1') == 'VALUE'
    assert fc.fault_type(m('CRP constant', "'a'", "'XXaXX'"), "s = 'a'") == 'VALUE'
    assert fc.fault_type(m('AOR'), 'n += 1') == 'OPERATOR'
    assert fc.fault_type(m('assignment replacement'), 'n = 0') == 'VALUE'
    assert fc.fault_type(m('argument replacement/removal'), 'f(a, b)') == 'CALL'


def test_site_constants():
    src = 'def f(x):\n    if x > 10 and x < 99:\n        return 3\n    return 0\n'
    assert fc.site_constants(src, 2) == [0, 1, 10, 99]


def test_templates_are_single_edits_deterministic_and_unique():
    seeds = [([3, 1, 2], 2)]
    a = fc.templates(seeds, {'BOUNDARY': [0, 1, 2]}, domain=False)
    b = fc.templates(seeds, {'BOUNDARY': [0, 1, 2]}, domain=False)
    assert a == b
    keys = [repr(c['args']) for c in a]
    assert len(keys) == len(set(keys)) and repr(seeds[0]) not in keys
    types = {c['type'] for c in a}
    assert types == set(fc.TYPES)
    for c in a:  # one position changed
        diff = sum(x != y for x, y in zip(c['args'], seeds[0]))
        assert diff == 1, c
    assert any(c['args'] == ([], 2) and c['type'] == 'MISSING_CASE' for c in a)
    assert any(c['args'] == ([3, 1, 2], 3) and c['type'] == 'BOUNDARY' for c in a)


def test_templates_respect_caps_and_literals():
    seeds = [(list(range(40)), 'x' * 30, 5)] * 3
    out = fc.templates(seeds, {'BOUNDARY': list(range(8))})
    assert len(out) <= fc.MAX_TOTAL
    for t in fc.TYPES:
        assert sum(c['type'] == t for c in out) <= fc.MAX_PER_TYPE
    assert all(fc.ok_literal(c['args']) for c in out)


def test_rank_and_select():
    cands = [dict(type='BOUNDARY', args=(1,), template='t0'), dict(type='MISSING_CASE', args=(0,), template='t1'),
             dict(type='OPERATOR', args=(2,), template='t2')]
    put = [['ok', '1'], ['ok', '0'], ['ok', '2']]
    muts = [dict(k=0, line=5, type='BOUNDARY', before='<=', after='<'), dict(k=1, line=7, type='VALUE', before='a', after='b'),
            dict(k=2, line=5, type='BOUNDARY', before='k', after='k+1')]
    out = {0: [['ok', '0'], ['ok', '0'], ['ok', '2']], 1: [['ok', '1'], ['ok', '0'], ['timeout']], 2: [['ok', '1'], ['ok', '0'], ['ok', '3']]}
    lines = ['l%d' % i for i in range(1, 10)]
    groups = fc.rank(muts, cands, put, out, lines)
    assert (groups[0]['line'], groups[0]['type'], groups[0]['distinguished']) == (5, 'BOUNDARY', 2)
    assert groups[1]['distinguished'] == 0  # timeouts never count as a difference
    sel = fc.select(groups, cands, put, out)
    assert sel[0]['type'] == 'BOUNDARY' and sel[0]['line'] == 5
    assert {r['index'] for r in sel[0]['inputs']} == {0, 2}
    assert sel[-1]['type'] == 'MISSING_CASE' and [r['index'] for r in sel[-1]['inputs']] == [1]


def test_tool_stage_end_to_end_finds_boundary_site():
    case = dict(case_id='t1', source=PUT, entry='count_below', base='assert count_below([1, 5, 9], 4) == 1\n'
                'assert count_below([], 3) == 0\n', witnesses=[])
    with tempfile.TemporaryDirectory() as d:
        rec = ft_run.tool_stage(case, 'pilot20', Path(d))
        assert rec['mutants'] > 0 and rec['survivors'] > 0
        top = rec['concepts'][0]
        assert top['type'] == 'BOUNDARY' and top['line'] == 5, json.dumps(rec['concepts'])[:500]
        # the concept inputs include one where x == k, the input class that separates < from <=
        assert any("4" in r['input'] and r['put_output'] != r['alternative_output'] for r in top['inputs'])
        assert len(rec['selected_inputs']) <= 6
        g = ft_run.guidance(rec)
        assert g['fault_concepts'][0]['site'] == 'L5' and g['fault_concepts'][0]['provenance'] == 'tool_derived'


def test_domain_filter_uses_public_examples_only():
    seeds = [([3, 1, 2], 2, 'ab'), ([5, 4, 6, 7], 3, 'c')]
    prof = fc.domain_profile(seeds)
    assert fc.in_domain(([1, 1, 1], 1, 'a'), prof)
    assert not fc.in_domain(([], 1, 'a'), prof)          # shorter than every public list
    assert not fc.in_domain(([3, 0, 2], 1, 'a'), prof)   # public elements are all >= 1
    assert not fc.in_domain(([3, 1, 2], -1, 'a'), prof)  # public ints are all >= 1
    assert not fc.in_domain(([3, 1, 2], 1, 'A'), prof)   # public strings are lowercase only
    out = fc.templates(seeds, {'BOUNDARY': [0, 1, 2]})
    assert out and all(fc.in_domain(c['args'], prof) for c in out)


def test_kills_only_where_put_returns_normally():
    cands = [dict(type='BOUNDARY', args=(1,), template='t0'), dict(type='BOUNDARY', args=(2,), template='t1')]
    put = [['exception', 'ValueError'], ['ok', '1']]
    muts = [dict(k=0, line=3, type='BOUNDARY', before='<', after='<=')]
    out = {0: [['ok', '5'], ['ok', '1']]}
    g = fc.rank(muts, cands, put, out, ['a', 'b', 'c'])
    assert g[0]['distinguished'] == 0


def test_vibepass_prompts_contain_no_evaluator_code():
    from .flow_run import cohort
    import json as _json
    from .paths import CONFIG, REPO
    root = REPO / CONFIG['vibepass']['root']
    plus = {int(r['task_id'].split('/')[1]): r for r in map(_json.loads, (root / 'humaneval_mbpp_plus.jsonl').read_text().splitlines())}
    for case in cohort('vibepass'):
        r = plus[int(case['case_id'])]
        visible = case['source'] + case['base']
        prompt_lines = set(r['prompt'].split('\n')) | set(case['source'].split('\n'))
        secret = [l.strip() for l in (r['canonical_solution'] + '\n' + r['contract']).split('\n')
                  if len(l.strip()) > 25 and l not in prompt_lines and l.strip() not in case['source']]
        assert not [l for l in secret if l in visible], case['case_id']
        public = [list(a) for a in r['base_input']]
        hidden = [a for a in r['plus_input'] if list(a) not in public]
        assert not [a for a in hidden if 'candidate(' + repr(tuple(a))[1:-1].rstrip(',') + ')' in case['base']], case['case_id']


def test_placebo_guidance_has_inputs_but_no_concept():
    tool = dict(concepts=[
        dict(type='BOUNDARY', line=5, code='if x <= k:', alternatives=['`<=` -> `<`'], survivors=3, distinguished=2,
             inputs=[dict(input='([1, 4], 4)', template='+1 at argument 2', put_output=['ok', '2'], alternative='`<=` -> `<`',
                          alternative_output=['ok', '1'])]),
        dict(type='MISSING_CASE', line=None, code=None, alternatives=[], survivors=0, distinguished=0,
             inputs=[dict(input='([], 4)', template='empty argument 1', put_output=['ok', '0'], alternative=None, alternative_output=None)])])
    g = ft_run.placebo_guidance(tool)
    assert [r['input'] for r in g['inputs']] == ['([1, 4], 4)', '([], 4)'] and set(g['inputs'][0]) == {'input', 'put_output'}
    text = json.dumps(g)
    for leak in ('BOUNDARY', 'MISSING_CASE', 'L5', '<=', 'template', 'alternative', 'hypothesis', 'rank', 'site', 'fault'):
        assert leak not in text, leak
    assert {r['input'] for c in ft_run.guidance(tool)['fault_concepts'] for r in c['inputs']} == {r['input'] for r in g['inputs']}
