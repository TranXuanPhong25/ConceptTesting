"""Offline regression tests: scripted LLM replies, local synthetic tasks, no Client construction."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from . import behaviour, behav_facts, evaluate, facts, gen_inputs, offline_behav, paths, preconditions, run, tracer

PUT = '''def order(xs):
    """Return elements in ascending order; retain duplicates."""
    return sorted(xs)
'''
BASE = 'def check(candidate):\n    assert candidate([1, 2]) == [1, 2]\n'
VALID = 'def valid(xs):\n    return isinstance(xs, list) and all(isinstance(x, int) for x in xs)\n'


def task(n=1):
    return dict(task=n, entry='order', put=PUT, base=BASE, split='dev',
                mined_valid_src=VALID, valid_sha256=preconditions.sha(VALID))


def requirement(D='return xs != sorted(xs)', R=None, rid='B1', statement='Sort the output'):
    params = preconditions.specification(task())[2]
    return dict(id=rid, statement=statement, quote='ascending order',
                D_src=behaviour.checked_predicate('def D(xs):\n    ' + D + '\n', 'D', params),
                R_src=behaviour.checked_predicate('def R(xs, *, out):\n    ' + R + '\n', 'R',
                                                behaviour.output_params(params)) if R else None)


def scripted(candidate_rows, code_rows):
    return [candidate_rows, [dict(id=c['id'], keep=True, quote=c['quote']) for c in candidate_rows], code_rows]


class FakeClient:
    model = 'qwen2.5-coder-7b-instruct'

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def chat(self, messages, seed, **settings):
        self.calls.append((messages, seed, settings))
        if not self.replies: raise AssertionError('unexpected LLM query')
        raw = self.replies.pop(0)
        return dict(text=raw if isinstance(raw, str) else json.dumps(raw), n_in=0, n_out=0)


def local_worker(job, directory, name, python=None, timeout=600):
    """Only test fixtures run locally; production retains namespace isolation."""
    directory.mkdir(parents=True, exist_ok=True)
    jp, op = directory / (name + '_job.json'), directory / (name + '.json')
    jp.write_text(json.dumps(job))
    behaviour.worker(jp, op)
    return json.loads(op.read_text())


class SpecHintTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='test-spechint-', dir=paths.HERE)
        self.root = Path(self.temporary.name)
        self.worker = patch.object(behaviour, 'isolated', side_effect=local_worker)
        self.worker.start()

    def tearDown(self):
        self.worker.stop()
        self.temporary.cleanup()

    def mine(self, client, **kw):
        return behaviour.mine(task(), client, self.root / 'mining', k=kw.pop('k', 1), **kw)

    def test_mining_gates_and_spec_only_prompts(self):
        candidates = [dict(id=f'B{i}', statement=statement, quote=quote) for i, statement, quote in (
            (1, 'Sort output', 'ascending order'), (2, 'Invented', 'stable sort'),
            (3, 'Crashes', 'retain duplicates'), (4, 'Bad output check', 'ascending order'),
            (5, 'Optional output check', 'retain duplicates'), (6, 'Nonboolean', 'ascending order'),
            (7, 'Unsafe', 'retain duplicates'))]
        code = [dict(id='B1', D='def D(xs):\n    return xs != sorted(xs)',
                     R='def R(xs, *, out):\n    return out == sorted(xs)'),
                dict(id='B3', D='def D(xs):\n    return 1 // (len(xs)-2) == 0'),
                dict(id='B4', D='def D(xs):\n    return False', R='def R(xs, *, out):\n    return False'),
                dict(id='B5', D='def D(xs):\n    return len(xs) != len(set(xs))'),
                dict(id='B6', D='def D(xs):\n    return len(xs)'),
                dict(id='B7', D='def D(xs):\n    return open("bad")')]
        client = FakeClient(scripted(candidates, code))
        result = self.mine(client)
        self.assertEqual(result['surviving'], 2)
        reasons = {r['reason'] for r in result['samples'][0]['dropped']}
        self.assertEqual(reasons, {'quote_not_in_specification', 'D_crashes_on_base', 'R_fails_on_base',
                                   'D_nonboolean_on_base', 'code_rejected'})
        for messages, seed, settings in client.calls:
            text = json.dumps(messages)
            self.assertNotIn('return sorted(xs)', text)
            self.assertNotIn('assert candidate', text)
            self.assertNotIn('mined_valid_src', text)
            self.assertEqual(seed, paths.CONFIG['seeds']['mining'] + 1)
            self.assertEqual(settings, dict(temperature=0, top_p=1, max_tokens=4096))

    def test_exact_quotes_and_negative_confirmation(self):
        # Amendment 1: whitespace differences are accepted; a quote with words absent from the spec is not.
        candidates = [dict(id='B1', statement='Sort', quote='ascending order of magnitude'),
                      dict(id='B2', statement='Keep duplicates', quote='retain duplicates'),
                      dict(id='B3', statement='Sort', quote='ascending order')]
        decisions = [dict(id='B1', keep=True, quote='ascending order of magnitude'),
                     dict(id='B2', keep=False, quote='retain duplicates'),
                     dict(id='B3', keep=True, quote='order')]
        result = self.mine(FakeClient([candidates, decisions]))
        self.assertEqual(result['surviving'], 0)
        self.assertEqual({r['reason'] for r in result['samples'][0]['dropped']},
                         {'quote_not_in_specification', 'confirmation_false', 'quote_changed'})

    def test_whitespace_quote_and_renamed_params(self):
        tree = behaviour.ast.parse('def f(xs):\n    pass')
        params = tree.body[0].args
        src = behaviour.checked_predicate('def D(ys):\n    return len(ys) > 1\n', 'D', params)
        self.assertIn('def D_m(xs)', src)
        self.assertIn('def D(xs)', src)
        self.assertEqual(behaviour._norm('a\n    b  c'), 'a b c')

    def test_malformed_replies_fail_closed(self):
        result = self.mine(FakeClient(['not json']))
        self.assertEqual(result['surviving'], 0)
        self.assertIsNotNone(result['samples'][0]['mining_failure'])

    def test_K_union_and_cached_mining(self):
        a = dict(id='B1', statement='Sort', quote='ascending order')
        b = dict(id='B2', statement='Keep duplicates', quote='retain duplicates')
        ca = dict(id='B1', D='def D(xs):\n    return xs != sorted(xs)')
        cb = dict(id='B2', D='def D(xs):\n    return len(xs) != len(set(xs))')
        client = FakeClient(scripted([a], [ca]) + scripted([a, b], [ca, cb]))
        result = self.mine(client, k=2)
        self.assertEqual(result['surviving'], 2)
        rows = json.loads((self.root / 'mining/1/requirements.json').read_text())
        self.assertEqual([r['samples'] for r in rows], [[0, 1], [1]])
        self.assertEqual([c[1] for c in client.calls],
                         [behaviour.SEED + 1]*3 + [behaviour.SEED + 1 + 100000]*3)
        self.assertEqual(self.mine(FakeClient([]), k=2), result)
        with self.assertRaisesRegex(ValueError, 'cache changed'):
            self.mine(FakeClient([]), k=1)

    def test_R_checked_on_all_base_pairs_even_outside_D(self):
        r = requirement('return False', 'return out != sorted(xs)')
        result = behaviour.verify(task(), [r])
        self.assertEqual(result['requirements'], [])
        self.assertEqual(result['dropped'][0]['reason'], 'R_fails_on_base')

    def test_predicate_keyword_defaults_and_optional_R(self):
        t = dict(task(), put='def order(xs, *, reverse=False):\n    """Sort ascending."""\n    return sorted(xs)\n')
        params = preconditions.specification(t)[2]
        src = behaviour.checked_predicate('def D(xs, *, reverse=False):\n    return xs != sorted(xs)', 'D', params)
        D = preconditions.load_predicate(src, 'D')
        self.assertTrue(D([2, 1]))
        self.assertFalse(D([1, 2], reverse=True))

    def test_fact_emission_first_valid_witness_and_no_leak(self):
        r = requirement()
        base = [(([1, 2],), {})]
        fuzz = [(([2, 'bad'],), {}), (([2, 1],), {}), (([4, 1],), {})]
        valid = preconditions.load_predicate(VALID, 'valid')
        emitted = behav_facts.emit([r], base, fuzz, valid, 'order')
        self.assertEqual(len(emitted), 1)
        f = emitted[0]
        self.assertEqual(f['witness'], 1)
        self.assertEqual(f['witness_call'], 'order([2, 1])')
        self.assertEqual(f['text'], 'Specification requirement (behaviour): Sort the output ("ascending order"). '
                         'No existing test uses an input where this matters.')
        self.assertNotIn('[2, 1]', f['text'])
        self.assertEqual(behav_facts.emit([r], [(([2, 1],), {})], fuzz, valid, 'order'), [])
        self.assertEqual(behav_facts.emit([r], base, [(([1, 3],), {})], valid, 'order'), [])

    def test_B5_fuzz_pool_replay_is_deterministic(self):
        requirements = [requirement()]
        first, second = behav_facts.build(task(), requirements), behav_facts.build(task(), requirements)
        self.assertEqual(first, second)
        self.assertTrue(first['facts'])
        # Independent invocation of the unchanged v7 pool, with exactly the same B5 checker.
        import random
        valid = preconditions.load_predicate(VALID, 'valid'); stats = {}
        base = [inputs for inputs, _ in behaviour.base_pairs(task())]
        pool = facts.fuzz_inputs(base, random.Random(facts.SEED + 1), lambda n, a: valid(*a[0], **a[1]), 1, stats)
        self.assertEqual(first['fuzz_sha256'], preconditions.sha(repr(pool)))
        witness = first['facts'][0]
        self.assertEqual(witness['witness_call'], facts.call_src('order', pool[witness['witness']]))

    def test_hit_is_valid_D_membership_independent_of_output(self):
        f = dict(requirement(), kind='BEHAV')
        tr = (set(), set(), 'timeout', None)
        valid = preconditions.load_predicate(VALID, 'valid')
        self.assertTrue(tracer.fact_hit(f, tr, args=(([2, 1],), {}), valid=valid))
        self.assertFalse(tracer.fact_hit(f, tr, args=(([1, 2],), {}), valid=valid))
        self.assertFalse(tracer.fact_hit(f, tr, args=(([2, 1],), {}), valid=False))
        self.assertFalse(tracer.fact_hit(f, tr, args=(([2, 1],), {})))
        broken = dict(requirement('return xs[100] == 1'), kind='BEHAV')
        self.assertFalse(tracer.fact_hit(broken, tr, args=(([2, 1],), {}), valid=valid))
        spec = dict(kind='SPEC', input_class=dict(cls='DUP', param=0))
        self.assertTrue(tracer.fact_hit(spec, tr, args=(([2, 2],), {})))

    def test_pick_tiers_kind_rotation_and_unchanged_without_BEHAV(self):
        def code(kind, block, demote=False):
            return dict(kind=kind, block=block, reached=True, g_demote=demote, text=str(block), witness_call='order([1, 2])')
        b = dict(requirement(), kind='BEHAV', block='BEHAV:B1', reached=True, witness_call='order([2, 1])', text='behaviour')
        old = [code('OUTCOME', 1), code('STMT', 2), code('MUTANT', 3, True)]
        self.assertEqual([f['kind'] for f in behav_facts.select(old, [b], 1)], ['OUTCOME', 'STMT', 'BEHAV'])
        self.assertEqual(behav_facts.select(old, [], 1), old)
        duplicates = [code('OUTCOME', i) for i in range(3)]
        top = behav_facts.select(duplicates, [b], 1)
        self.assertEqual([f['kind'] for f in top], ['OUTCOME', 'BEHAV', 'OUTCOME'])
        all_tier0 = [code('OUTCOME', 1), code('STMT', 2), code('MUTANT', 3)]
        self.assertNotIn('BEHAV', [f['kind'] for f in behav_facts.select(all_tier0, [b], 1)])
        spec = dict(kind='SPEC', text='spec', witness_call='order([1, 1])', reached=True)
        self.assertEqual([f['kind'] for f in behav_facts.select([spec], [b], 1)], ['SPEC', 'BEHAV'])
        self.assertEqual([f['kind'] for f in behav_facts.select([], [b], 1)], ['BEHAV'])

    def test_bundle_adds_pool_and_updates_toolinput_preserving_other_fields(self):
        t = dict(task(), concept_meta=[], concept_facts=[], placebo_meta=[], placebo_facts=[], tool_inputs=[])
        emitted = behav_facts.build(t, [requirement()])['facts']
        layout = run.Layout()
        layout.all, layout.hybrid = self.root / 'tasks_all.json', self.root / 'tasks_hybrid.json'
        layout.behavfacts = self.root / 'behavfacts'; layout.behavfacts.mkdir()
        (layout.behavfacts / '1.json').write_text(json.dumps(dict(facts=emitted, valid_sha256=t['valid_sha256'])))
        with patch.object(run, 'code_bundle', return_value=dict(tasks=[t], note='v7')), \
             patch('trickcatcher_linefacts.pipelines.v10_spechint.run_v4.mined_task',
                   return_value=dict(strategy_src='strategy', strategy_sha256='s', strategy_fallback=False, mining_summary={})):
            layout.specfacts = self.root / 'specfacts'; layout.specfacts.mkdir()
            (layout.specfacts / '1.json').write_text(json.dumps(dict(facts=[], placebo=[])))
            standard, hybrid = run.bundle(layout)
        out = standard['tasks'][0]
        self.assertEqual(out['concept_facts'], [f['text'] for f in emitted])
        self.assertEqual(out['tool_inputs'], [f['witness_call'] for f in emitted])
        self.assertEqual(out['v7_concept_meta'], [])
        self.assertEqual(out['put'], PUT)
        self.assertEqual(out['placebo_meta'], [])
        self.assertEqual(hybrid['tasks'][0]['facts_version'], 'v4')
        self.assertEqual(hybrid['tasks'][0]['concept_meta'], out['concept_meta'])

    def test_no_BEHAV_preserves_v7_hints_and_witness_order(self):
        old = [dict(kind='SPEC', text='old spec', reached=True, witness_call='order([1, 1])')]
        t = dict(task(), concept_meta=copy.deepcopy(old), concept_facts=['old spec'],
                 tool_inputs=['order([1, 1])', 'order([1, 1])'])
        before = copy.deepcopy(t)
        behav_facts.augment(t, [])
        self.assertEqual({k: t[k] for k in before}, before)

    def test_generator_classification_and_evaluation_dispatch(self):
        f = dict(requirement(), kind='BEHAV')
        jp, op = self.root / 'job.json', self.root / 'result.json'
        job = dict(entry='order', put=PUT, mined_src=VALID, concept=[f], shown=[f], requested_draws=3,
                   candidates=[dict(input_repr='[[2, 1]]'), dict(input_repr='[[1, 2]]'), dict(input_repr='[[2, "x"]]')])
        jp.write_text(json.dumps(job)); gen_inputs.classify_worker(jp, op)
        result = json.loads(op.read_text())
        self.assertEqual([r['concept_hits'] for r in result['records']], [[True], [False], [False]])
        self.assertEqual(result['summary']['valid'], 2)
        ejob = dict(entry='order', put=PUT, canon=PUT, mined_valid_src=VALID, facts=[f],
                    rows=[dict(task=1, arm='concept', sample=0,
                               asserts=['assert order([2, 1]) == [1, 2]', 'assert order([1, 2]) == [1, 2]'])])
        jp.write_text(json.dumps(ejob)); evaluate.worker(jp, op)
        self.assertEqual([r['hits'] for r in json.loads(op.read_text())[0]['asserts']], [[True], [False]])

    def test_offline_labels_PF_split_and_new_coverage(self):
        t = dict(task(), put=PUT.replace('return sorted(xs)', 'return xs'), concept_meta=[], concept_facts=[], tool_inputs=[])
        emitted = behav_facts.build(t, [requirement()])['facts']
        behav_facts.augment(t, emitted)
        hep = dict(test='def check(candidate):\n    for i, xs in enumerate([[1, 2], [2, 1], [3, 1]]):\n        assert candidate(xs) == sorted(xs)\n')
        measured = offline_behav.measure(t, hep)
        self.assertEqual((measured['n_plus'], measured['n_fail']), (3, 2))
        self.assertEqual(measured['facts'][0]['pf'], 1.0)
        result = offline_behav.report([t], {1: measured})
        self.assertEqual(result['cohorts']['odd']['good_at_3']['v10']['count'], 1)
        self.assertEqual(result['cohorts']['odd']['good_at_3']['v7']['count'], 0)
        self.assertEqual(result['cohorts']['odd']['newly_covered'], [1])
        self.assertEqual(result['cohorts']['odd']['newly_good'], [1])
        self.assertEqual(result['cohorts']['even']['n_dev'], 0)
        self.assertEqual(len(result['examples']), 1)
        self.assertEqual(result['examples'][0]['hits'], 2)
        with self.assertRaisesRegex(ValueError, 'DEV'):
            offline_behav.measure(dict(t, split='pilot'), hep)

    def test_hybrid_classification_and_timeout_evaluation_dispatch(self):
        from . import v4_worker, v4_tools, v4_evaluation
        class TestCoverage:
            def __init__(self, *args): pass
            def trace(self, fn, args): return tracer.trace(fn, args)
        f = dict(requirement(), kind='BEHAV')
        t = dict(task(), concept_meta=[f])
        job = dict(task=t, candidates=[dict(input_repr='([2, 1],)'), dict(input_repr='([1, 2],)'),
                                      dict(input_repr='([2, "x"],)')], shown=[f])
        with patch.object(v4_tools, 'Coverage', TestCoverage):
            r = v4_worker.classify(job, self.root)
        self.assertEqual([r['concept_hits'] for r in r['records']], [[True], [False], [False]])
        t = dict(t, put=PUT.replace('return sorted(xs)', 'return xs'))
        ejob = dict(task=t, canon=PUT, contract_src='def order(xs):\n    assert isinstance(xs, list)\n',
                    rows=[dict(task=1, arm='concept-hybrid', sample=0,
                               assertions=['assert order([2, 1]) == [1, 2]'])])
        real_call = tracer.call
        def timed_out(fn, args):
            return ('timeout', None) if 'sorted' not in fn.__code__.co_names else real_call(fn, args)
        with patch.object(v4_tools, 'Coverage', TestCoverage), \
             patch.object(v4_evaluation, 'guard_alarm'), patch.object(tracer, 'call', side_effect=timed_out):
            scored = v4_evaluation.worker(ejob, self.root)
        self.assertEqual(scored[0]['asserts'][0]['hits'], [True])
        self.assertEqual(scored[0]['input_metrics'][0]['put_status'], 'timeout')
        self.assertEqual(scored[0]['input_metrics'][0]['hits'], [True])

    def test_offline_scores_unshown_BEHAV_and_reports_losses(self):
        t = dict(task(2), put=PUT.replace('return sorted(xs)', 'return xs'),
                 concept_meta=[], concept_facts=[], tool_inputs=[])
        requirements = [requirement(rid=f'B{i}', statement=f'Sort requirement {i}') for i in range(1, 5)]
        emitted = behav_facts.build(t, requirements)['facts']
        behav_facts.augment(t, emitted)
        self.assertEqual(len(t['behav_pool']), 4)
        self.assertEqual(len(t['concept_meta']), 3)
        hep = dict(test='def check(candidate):\n    for i, xs in enumerate([[1, 2], [2, 1]]):\n        assert candidate(xs) == sorted(xs)\n')
        measured = offline_behav.measure(t, hep)
        result = offline_behav.report([t], {2: measured})
        self.assertEqual(len(result['examples']), 4)
        self.assertEqual(sum(e['selected'] for e in result['examples']), 3)
        self.assertTrue(all(e['pf'] == 1.0 for e in result['examples']))
        self.assertEqual(result['cohorts']['even']['newly_good'], [2])
        # The measurement also exposes a loss if a formerly good hint leaves the selection.
        lost = dict(t, v7_concept_meta=[emitted[0]], concept_meta=[], behav_pool=emitted)
        report = offline_behav.report([lost], {2: measured})
        self.assertEqual(report['cohorts']['even']['lost_good'], [2])


if __name__ == '__main__': unittest.main()
