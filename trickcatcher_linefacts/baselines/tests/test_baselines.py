"""Offline tests for the CoverUp and MuTAP adapters (scripted client; no endpoint, no credentials)."""
import json
import subprocess
import sys
from types import SimpleNamespace

import pytest

from trickcatcher_linefacts.baselines import common
from trickcatcher_linefacts.baselines.common import (HERE, Session, ScriptedClient, base_assertions, extract_assertions,
                                                     visible_task, worker)
from trickcatcher_linefacts.baselines.coverup.run import generate as coverup
from trickcatcher_linefacts.baselines.mutap.run import generate as mutap, greedy, load_prompts

TASK = dict(task='synthetic/class', entry='f', split='dev',
            put='def f(x):\n    """Return 1 for positive x, otherwise 0."""\n    if x > 0:\n        return 1\n    return 0\n',
            base='def check(candidate):\n    assert candidate(0) == 0\n')
CONFIG = SimpleNamespace(max_tests=20, max_mutants=12, max_surviving_mutants=7)
SYSTEM = 'You are a python coding assistant. Always answer with python code.'


def session(tmp_path, arm, responses, budget=6, task=TASK, sample=0):
    return Session(task, arm, sample, ScriptedClient(responses), tmp_path, budget, 123)


def response(code):
    return '```python\n'+code+'\n```'


def prompt(tmp_path, i):
    return json.loads((tmp_path/f'call_{i:03d}_prompt.json').read_text())


# ------------------------------------------------------------------ extraction
def test_extract_aliases_parametrize_loops_and_rejections():
    code = '''import pytest
from put import f as target
import put as p
CASES = [(1, 2), (3, 4)]
@pytest.mark.parametrize("x, y", [(5, 6), pytest.param(7, 8)])
def test_param(x, y):
    assert target(x) == y
def test_values(tmp_path):
    value = [1, 2]
    result = target(value)
    assert result == [3]
    assert p.f(2) is True
    assert target(unknown) == 2
    assert target(tmp_path) == 1
    for a, b in CASES:
        assert f(a) == b
    for x in range(2):
        if x:
            break
        assert target(x) == 1
    assert f(1.5) == pytest.approx(0.5)
    assert _heldout_same(f(9), 10, 0)
    assert not f(0)
    value.append(3)
    assert f(value) == 1
    assert len([i for i in range(3)]) == 3
class TestX:
    def test_m(self):
        self.assertEqual(f(11), 12)
'''
    rows, rejected = extract_assertions(code, 'f', TASK['put'], {'_heldout_same'})
    assert rows == ['assert f(5) == 6', 'assert f(7) == 8', 'assert f([1, 2]) == [3]', 'assert f(2) == True',
                    'assert f(1) == 2', 'assert f(3) == 4', 'assert f(1.5) == 0.5', 'assert f(9) == 10',
                    'assert not f(0)', 'assert f(11) == 12']
    reasons = [r['reason'] for r in rejected]
    assert reasons == ['unresolved names: unknown', 'unresolved names: tmp_path', 'unresolved names: x',
                       'unresolved names: value', 'does not call f']


def test_extract_star_import_globals_and_base_copies():
    put = 'from math import *\ndef f(x):\n    return x\n'
    assert extract_assertions('assert f(inf) == inf', 'f', put)[0] == ['assert f(inf) == inf']
    assert extract_assertions('assert f(inf) == inf', 'f', 'def f(x):\n    return x\n')[0] == []
    heldout = dict(TASK, base='def _heldout_same(x, y, atol):\n    return x == y\n\ndef check(candidate):\n'
                              '    assert _heldout_same(candidate(3), 1, 0)\n')
    assert base_assertions(heldout) == {'assert f(3) == 1'}


# ------------------------------------------------------------------ CoverUp
def test_coverup_original_loop_error_then_gain(tmp_path):
    bad = response('from put import f\ndef test_new():\n    assert f(1) == 999')
    good = response('from put import f\ndef test_new():\n    assert f(1) == 1')
    s = session(tmp_path, 'coverup', [bad, good])
    r = coverup(TASK, s, CONFIG)
    assert r['assertions'] == ['assert f(1) == 1']
    assert len(s.calls) == 2 and r['accepted_tests'] == 1 and r['stop_reason'] == 'segments_completed'
    first = prompt(tmp_path, 0)
    assert TASK['put'] in first[0]['content'] and 'check(f)' in first[0]['content']
    assert first[1]['content'].lstrip().startswith('You are an expert Python test-driven developer.')
    assert 'Executing the test yields an error' in prompt(tmp_path, 1)[-1]['content']
    assert not r['base_full_coverage'] and r['final_coverage_percent'] == 100.0
    assert not list(r['final_coverage']['coverage']['files'].values())[0]['missing_lines']


def test_coverup_missing_coverage_attempt_limit(tmp_path):
    s = session(tmp_path, 'coverup', [response('from put import f\ndef test_old():\n    assert f(0) == 0')])
    r = coverup(TASK, s, CONFIG)
    assert r['assertions'] == [] and len(s.calls) == 3   # the authors' max_attempts = 3 per segment
    assert 'tests still lack coverage' in prompt(tmp_path, 1)[-1]['content']


def test_coverup_full_base_and_zero_budget(tmp_path):
    full = dict(TASK, base=TASK['base']+'    assert candidate(1) == 1\n')
    s = session(tmp_path/'full', 'coverup', ['must not be queried'], task=full)
    r = coverup(full, s, CONFIG)
    assert r['stop_reason'] == 'full_base_coverage' and r['base_full_coverage'] and not s.calls
    s = session(tmp_path/'empty', 'coverup', ['must not be queried'], budget=0)
    assert coverup(TASK, s, CONFIG)['stop_reason'] == 'llm_budget' and not s.calls


# ------------------------------------------------------------------ MuTAP
def test_mutap_dialogs_syntax_semantics_survivor_and_greedy(tmp_path):
    replies = [response('def test():\n    assert f(0) =='),
               response('def test():\n    assert f(0) == 999\n    assert f(-5) == 0'),
               response('def test():\n    assert f(1) == 999')]
    s = session(tmp_path, 'mutap', replies, budget=3)
    r = mutap(TASK, s, CONFIG)
    assert [c['stage'] for c in s.calls] == ['initial', 'syntax_fix', r['raw_tests'][-1]['stage']]
    assert s.calls[2]['stage'].startswith('augment_')
    initial, fix, augment = prompt(tmp_path, 0), prompt(tmp_path, 1), prompt(tmp_path, 2)
    assert [m['role'] for m in initial] == ['system', 'user'] and initial[0]['content'] == SYSTEM
    assert initial[1]['content'].startswith(' Generate test cases for\n```python\n' + TASK['put'].rstrip())
    assert TASK['base'].strip() in initial[1]['content'] and initial[1]['content'].endswith('def test():\n    assert \n')
    assert fix[1]['content'].startswith(' Fix the syntax error the last line of the following code:')
    assert [m['role'] for m in augment] == ['system', 'user', 'assistant', 'user']
    assert augment[0]['content'] == '#' + SYSTEM
    assert 'The pervious test case cannot detect' in augment[-1]['content']
    assert 'assert f(0) == 0' in augment[-1]['content'] and 'assert f(0) == 0' in augment[2]['content']
    # Functional repair replaces the expected value with the PUT's output (authors' semantic correction).
    assert {d['status'] for d in r['semantic_repairs']} >= {'repaired', 'pass'}
    assert r['refined_passing'] == ['assert f(0) == 0', 'assert f(-5) == 0', 'assert f(1) == 1']
    # Greedy minimization is a separate diagnostic; comparison assertions retain generation order.
    assert r['greedy_selected'] and r['assertions'] == r['refined_passing']
    assert 'assert f(1) == 1' in r['greedy_selected']
    assert set(r['assertions']) == set(r['refined_passing'])
    assert r['mutation_backend'] == 'mutmut' and r['n_live_after_base'] >= 1


def test_mutap_keeps_assertions_whose_call_raises(tmp_path):
    task = dict(TASK, put='def f(x):\n    if x < 0:\n        raise ValueError(x)\n    return x\n',
                base='def check(candidate):\n    assert candidate(2) == 2\n')
    s = session(tmp_path, 'mutap', [response('def test():\n    assert f(-1) == 0\n    assert f(3) == 3')], budget=1)
    r = mutap(task, s, CONFIG)
    assert r['kept_raising'] == ['assert f(-1) == 0'] and r['assertions'][0] == 'assert f(-1) == 0'
    assert 'assert f(-1) == 0' not in r['kill_matrix']


def test_greedy_matches_authors_rule():
    kills = {'a': [1], 'b': [1, 2, 3], 'c': [3, 4], 'd': [], 'e': [2]}
    chosen, covered = greedy(['a', 'b', 'c', 'd', 'e'], kills)
    assert chosen == ['b', 'c'] and covered == {1, 2, 3, 4}


def test_mutant_pool_is_spread_and_fails_without_mutmut(tmp_path):
    put = 'def f(x):\n' + ''.join(f'    if x == {i}:\n        return {i + 1}\n' for i in range(20)) + '    return 0\n'
    r = worker('mutants', dict(put=put, max_mutants=5), tmp_path/'pool')
    assert r['ok'] and len(r['mutants']) == 5 and r['n_generated'] > 5
    lines = put.splitlines()
    changed = [next(i for i, (a, b) in enumerate(zip(lines, m['source'].splitlines())) if a != b) for m in r['mutants']]
    assert changed == sorted(changed) and changed[-1] > len(lines) // 2   # not just the first mutants in the file
    job, output = tmp_path/'job.json', tmp_path/'output.json'
    job.write_text(json.dumps(dict(mode='mutants', put=TASK['put'], max_mutants=4)))
    # Hide the dependency only in the child: a missing backend must not change the method.
    bootstrap = "import runpy,sys; sys.modules['mutmut']=None; sys.argv=sys.argv[1:]; runpy.run_path(sys.argv[0],run_name='__main__')"
    subprocess.run(['unshare', '-rn', sys.executable, '-I', '-B', '-c', bootstrap, str(HERE/'worker.py'), str(job), str(output)],
                   cwd=tmp_path, env={'PATH': '/usr/bin:/bin'}, check=True, timeout=30)
    r = json.loads(output.read_text())
    assert not r['ok'] and r['backend'] == 'mutmut' and 'mutants' not in r


def test_prompts_are_exact_author_functions():
    p = load_prompts()
    assert p['initalPromptGenerator']('PUT').startswith(' Generate test cases for\n```python\nPUT')
    assert 'survivor' in p['mutatePromptGenerator']('PUT + TESTS', 'survivor')
    assert p['synxtaxfixer']('assert f(1) == 1\nassert f(') == 'assert f(1) == 1'


# ------------------------------------------------------------------ shared
def test_seeded_budget_no_endpoint_or_secret_access(tmp_path, monkeypatch):
    monkeypatch.setattr(common, 'QwenClient', lambda *a, **kw: pytest.fail('Qwen client constructed'))
    seeds = []
    for directory, sample in [('a', 0), ('b', 0), ('c', 1)]:
        s = session(tmp_path/directory, 'mutap', [response('assert f(1) == 1')], budget=1, sample=sample)
        mutap(TASK, s, CONFIG)
        assert len(s.calls) == 1
        seeds.append(s.calls[0]['seed'])
    assert seeds[0] == seeds[1] != seeds[2]


def test_visibility_and_class_adapter(tmp_path):
    task = dict(TASK, put='class Solution:\n    def method(self,x):\n        return x + 1\ndef f(x):\n    return Solution().method(x)\n',
                base='def check(candidate):\n    assert candidate(1) == 2\n', concept_facts=['FORBIDDEN'], silver='FORBIDDEN')
    assert 'concept_facts' not in visible_task(task) and 'silver' not in visible_task(task)
    r = worker('screen', dict(visible_task(task), assertions=['assert f(2) == 3'], mutants=[]), tmp_path/'screen')
    assert r['ok']
    r = worker('mutants', dict(put=task['put'], max_mutants=12), tmp_path/'mutants')
    assert r['ok'] and r['mutants']
    assert any('return x + 1' not in m['source'] for m in r['mutants'])


def test_failed_base_and_zero_budget(tmp_path):
    bad = dict(TASK, base='def check(candidate):\n    assert candidate(0) == 10')
    for arm, generate in [('coverup', coverup), ('mutap', mutap)]:
        s = session(tmp_path/arm, arm, ['unused'])
        assert generate(bad, s, CONFIG)['stop_reason'] == 'base_failed'
        assert not s.calls
    s = session(tmp_path/'zero', 'mutap', ['unused'], budget=0)
    assert mutap(TASK, s, CONFIG)['assertions'] == [] and not s.calls


def test_cli_rows_parallel_resume_and_base_copies(tmp_path):
    bundle = tmp_path/'bundle.json'
    tasks = [dict(TASK, task=7, facts_version='v4', concept_facts=['secret']), dict(TASK, task=8, split='pilot')]
    bundle.write_text(json.dumps(dict(facts_version='v4', tasks=tasks)))
    scripts = tmp_path/'scripts.json'
    scripts.write_text(json.dumps({'7': [response('def test():\n    assert f(0) == 0\n    assert f(2) == 1')]}))
    out = tmp_path/'run'
    argv = ['--tasks', str(bundle), '--out', str(out), '--k', '2', '--split', 'dev', '--responses', str(scripts),
            '--llm-budget', '2', '--workers', '2']
    common.cli('mutap', mutap, lambda: dict(test=True), argv)
    rows = [json.loads(l) for l in (out/'gen.jsonl').read_text().splitlines()]
    assert [(r['task'], r['sample']) for r in rows] == [(7, 0), (7, 1)]
    for r in rows:
        assert r['assertions'] == ['assert f(2) == 1'] and r['base_copies'] == ['assert f(0) == 0']
        assert r['text'] == '```python\nassert f(2) == 1\n```' and r['split'] == 'dev' and r['facts_version'] == 'v4'
        assert r['llm_calls'] <= 2 and r['model'] == 'offline-scripted' and r['run_id']
        assert 'secret' not in json.dumps(r)
    with pytest.raises(SystemExit):
        common.cli('mutap', mutap, lambda: dict(test=True), argv)          # fresh directory required
    common.cli('mutap', mutap, lambda: dict(test=True), argv + ['--resume'])
    assert [json.loads(l) for l in (out/'gen.jsonl').read_text().splitlines()] == rows


@pytest.mark.parametrize('arm,generate', [('coverup', coverup), ('mutap', mutap)])
def test_real_generation_cap_in_order_and_explicit_spec(tmp_path, arm, generate):
    task = dict(TASK, task=1, spec='EXPLICIT SPEC: return one on positive inputs.', private_tests='HIDDEN')
    bundle, scripts, out = tmp_path/'bundle.json', tmp_path/'scripts.json', tmp_path/'run'
    bundle.write_text(json.dumps(dict(tasks=[task])))
    assertions = [f'assert f({i}) == 1' for i in range(1, 26)]
    code = 'from put import f\ndef test_new():\n    ' + '\n    '.join(assertions)
    scripts.write_text(json.dumps({'1': [response(code)]}))
    common.cli(arm, generate, lambda: dict(test=True),
               ['--tasks', str(bundle), '--out', str(out), '--responses', str(scripts)])
    rows = [json.loads(l) for l in (out/'gen.jsonl').read_text().splitlines()]
    assert len(rows) == 3
    manifest = json.loads((out/'manifest.json').read_text())
    assert manifest['llm_budget'] == 8 and manifest['max_tests'] == 20
    assert manifest['max_surviving_mutants'] == 7
    for row in rows:
        assert row['assertions'] == assertions[:20]
        assert row['n_assertions_uncapped'] == 25 and row['n_assertions_dropped'] == 5
        assert row['truncated_assertions'] == assertions[20:] and row['llm_calls'] <= 8
    prompts = list((out/'artifacts').glob('*/*/call_000_prompt.json'))
    assert len(prompts) == 3
    for path in prompts:
        text = path.read_text()
        assert task['spec'] in text and 'HIDDEN' not in text


def test_surviving_mutant_limit_and_all_calls_count(tmp_path):
    config = SimpleNamespace(max_tests=20, max_mutants=32, max_surviving_mutants=1)
    s = session(tmp_path/'limited', 'mutap', [response('assert f(0) == 0')], budget=8)
    r = mutap(TASK, s, config)
    assert r['n_live_selected'] == 1 and r['n_live_after_base'] > 1
    assert len(r['targeted_mutants']) == 1 and len(s.calls) == 2
    assert r['stop_reason'] == 'surviving_mutant_limit'
    # Continuous invalid syntax consumes all eight calls (including repairs), never nine.
    s = session(tmp_path/'syntax', 'mutap', [response('assert f(')], budget=8)
    mutap(TASK, s, CONFIG)
    assert len(s.calls) == 8 and [c['stage'] for c in s.calls][1:] == ['syntax_fix'] * 7
    with pytest.raises(common.BudgetExhausted):
        s.query([], 'ninth')


@pytest.mark.parametrize('options', [['--llm-budget', '9'], ['--max-tests', '21'], ['--max-surviving-mutants', '0']])
def test_cli_rejects_protocol_violations_before_reading_tasks(tmp_path, options):
    with pytest.raises(SystemExit):
        common.cli('mutap', mutap, lambda: {}, ['--tasks', 'unused', '--out', str(tmp_path), *options])


def test_qwen_replay_never_reads_environment_and_transport_is_mocked(tmp_path, monkeypatch):
    import httpx

    class NoEnvironment:
        def get(self, *_):
            pytest.fail('replay inspected environment')

    monkeypatch.setattr(common, 'os', SimpleNamespace(environ=NoEnvironment()))
    replay = common.QwenClient(tmp_path/'cache', offline=True)
    with pytest.raises(RuntimeError, match='offline Qwen cache miss'):
        replay.chat([], 1)
    # Opaque placeholders are supplied by a fake environment, never from real configuration.
    monkeypatch.setattr(common.os, 'environ', {'QWEN_BASE_URL': 'opaque-base', 'QWEN_API_KEY': 'opaque-key'})
    requests = []
    class Response:
        def raise_for_status(self): pass
        def json(self):
            return dict(choices=[dict(message=dict(content='assert f(1) == 1'))],
                        usage=dict(prompt_tokens=4, completion_tokens=5))
    class FakeHTTP:
        def __init__(self, **kwargs): self.options = kwargs
        def post(self, endpoint, **kwargs):
            requests.append((endpoint, kwargs))
            return Response()
    monkeypatch.setattr(httpx, 'Client', FakeHTTP)
    online = common.QwenClient(tmp_path/'cache', offline=False)
    result = online.chat([], 1, max_tokens=10)
    assert requests[0][0] == 'opaque-base/chat/completions'
    assert requests[0][1]['json']['model'] == common.MODEL
    assert (result['n_in'], result['n_out']) == (4, 5)
    assert 'opaque' not in next((tmp_path/'cache').glob('*.json')).read_text()
    monkeypatch.setattr(common.os, 'environ', NoEnvironment())
    assert replay.chat([], 1, max_tokens=10)['cache_hit'] and len(requests) == 1


def test_mutation_failure_stops_without_llm(tmp_path, monkeypatch):
    from trickcatcher_linefacts.baselines.mutap import run
    original_worker = run.worker
    def failing_backend(mode, *args, **kwargs):
        if mode == 'mutants':
            return dict(ok=False, backend='mutmut', error='dependency missing')
        return original_worker(mode, *args, **kwargs)
    monkeypatch.setattr(run, 'worker', failing_backend)
    s = session(tmp_path, 'mutap', ['must not be queried'])
    assert mutap(TASK, s, CONFIG)['stop_reason'] == 'mutation_failed' and not s.calls
