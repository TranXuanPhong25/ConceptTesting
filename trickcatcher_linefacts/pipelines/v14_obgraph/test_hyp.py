"""Offline B4 tests: fake LLM client only, sockets forbidden. Real-sandbox tests use the dedicated v4 venv (CPU)."""
import contextlib
import json
import re
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from . import hypotheses, hyp_prompts, offline_client, paths, preconditions, rel_prompts, relations, run_v4, v4_prompts, v4_runtime
from . import hyp_report
from ..v12_rel import run_v4 as v12_run, v4_prompts as v12_prompts

PUT = ('def f(x):\n    """Return the value x plus one when x is positive. Return zero otherwise."""\n'
       '    value = x + 1\n    if x > 0:\n        return value\n    return 0\n')
REAL_PUT = ('def f(x):\n    """Return x plus one when x is positive. Return zero otherwise."""\n'
            '    value = x + 1\n    if x > 0:\n        if x > 50:\n            return value + 1\n'
            '        return value\n    return 0\n')
WITNESS = {0: '(272,)', 1: '(-417,)'}
HYPS = [dict(R='Return the value x plus one when x is positive.', chain=dict(lines=[3, 4, 5], explanation='large x'),
             T='def trigger(x):\n    return x > 100', expected_violation='wrong value for large x'),
        dict(R='Return zero otherwise.', chain=dict(lines=[4, 6], explanation='negative x'),
             T='x < -40', expected_violation='nonzero for negative x'),
        dict(R='Return zero otherwise.', chain='line 4 -> line 6: huge x', T='lambda x: x > 10**9',
             expected_violation='overflow')]


def task(n_hints=3, put=PUT):
    valid = 'def valid(x):\n    return isinstance(x, int) and -1000 <= x <= 1000\n'
    strategy = 'def strategy():\n    return st.tuples(st.integers(-1000, 1000))\n'
    facts = [dict(kind='STMT', line=5, lines=[5], text=f'Unique hint {i}: line 5 is untested.',
                  witness_call='f(100)') for i in range(n_hints)]
    return dict(task=0, entry='f', put=put, base='def check(candidate):\n    assert candidate(0) == 0\n',
                split='dev', doc_fail=False, facts_version='v4', mined_valid_src=valid,
                valid_sha256=preconditions.sha(valid), strategy_src=strategy, strategy_sha256=preconditions.sha(strategy),
                concept_meta=facts, placebo_meta=facts, concept_facts=[f['text'] for f in facts],
                placebo_facts=[f['text'] for f in facts], tool_inputs=['f(100)'])


def candidates_for(t):
    return dict(sites=[dict(line=n, covered=n != 5, chain=f'line {n} (line)') for n in range(1, 7)], base_ok=True,
                base_trace_statuses={}, survivor_mutants=[], mutation_errors=[])


def predicate(h):
    return preconditions.load_predicate(h['trigger_src'], 'trigger')   # test process only; our own fixed sources


class FakeClient:
    model = paths.CONFIG['model']

    def __init__(self, round1=(0,), proposal=None):
        self.requests, self.round1 = [], round1
        self.proposal = proposal if proposal is not None else json.dumps(HYPS)

    def chat(self, messages, seed, **kwargs):
        key, params = offline_client.request(messages, seed, **kwargs)
        self.requests.append(dict(messages=messages, seed=seed, key=key, params=params))
        if 'JSON only' in messages[0]['content']:
            text = 'Hypotheses:\n```json\n' + self.proposal + '\n```'
        elif 'Hypothesis' in messages[0]['content']:
            text = 'def strategy():\n    return st.just((100,))'
        elif 'sample_one' in messages[0]['content']:
            text = 'def sample_one():\n    return (100,)'
        elif 'For EXACTLY' in messages[-1]['content']:
            text = 'assert f(999) == 999\nassert f(101) == 102\nassert f(100) == 101\nassert f(150) == 151\nassert f(-50) == 0'
        else:
            text = '\n'.join(f'assert f({i}) == {i}' for i in self.round1)
        return dict(text=text, n_in=1, n_out=1, seconds=0, key=key, params=params)


class Base(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(socket.socket, 'connect', side_effect=AssertionError('network forbidden')))
        self.stack.enter_context(patch.object(socket, 'create_connection', side_effect=AssertionError('network forbidden')))


class FakeRunTests(Base):
    def generate(self, module=run_v4, arms=None, *, client=None, k=1, fail=False, pool=((150,), (101,), (-50,), (5,)),
                 n_hints=3, witnesses=WITNESS):
        t = task(n_hints)
        client = client or FakeClient()
        self.isolated_modes = []

        def classify(t, d, python, *, assertions=None, shown=(), **kwargs):
            records = [] if assertions is not None else [dict(input_repr=f'({i},)', call=f'f({i})', valid=True,
                        shown_hits=[True]*len(shown)) for i in (100, 101)]
            return dict(records=records, summary=dict(shown_hit_counts=[0]*len(shown), valid=len(records), removed=0))

        def records_of(job):
            if 'assertions' in job:
                return [dict(input_repr=f'({m},)') for a in job['assertions'] for m in re.findall(r'f\((-?\d+)\)', a)]
            return [dict(c) for c in job.get('candidates', [])]

        def isolated(mode, job, *args, **kwargs):
            self.isolated_modes.append(mode)
            if mode == 'relations': return relations.extract(job['task'])
            if mode == 'hyp_candidates': return candidates_for(job['task'])
            if mode == 'hyp_check':
                rows = []
                for h in job['hypotheses']:
                    w = witnesses.get(h['order'])
                    rows.append(dict(h, witness=dict(input_repr=w, call='f'+w[:-2]+')') if w else None, witnessed=bool(w),
                                     unwitnessed=not w, mutant_diff=h['order'] == 1, differing_mutants=[],
                                     filter_usable=bool(w)))
                return dict(hypotheses=rows, failures=[])
            if mode == 'hyp_draw':
                p = predicate(job['hypothesis'])
                return dict(candidates=[dict(input_repr=repr(a)) for a in pool if p(*a)], errors=[])
            if mode in ('hyp_classify', 'hyp_attribution'):
                recs = records_of(job)
                ps = [predicate(h) for h in job['hypotheses']]
                for r in recs:
                    a = eval(r['input_repr'])
                    r.update(valid=-1000 <= a[0] <= 1000, call=f'f({a[0]})', hypothesis_hits=[p(*a) is True for p in ps])
                if mode == 'hyp_attribution': return dict(records=recs)
                counts = [sum(r['valid'] and r['hypothesis_hits'][i] for r in recs) for i in range(len(ps))]
                return dict(records=recs, summary=dict(shown_hit_counts=counts, valid=len(recs)))
            raise AssertionError(mode)

        def draws(*args, **kwargs):
            if fail: raise ValueError('fake rejection')
            return dict(candidates=[], nonliteral=0, wrong_arity=0, errors=[])
        with tempfile.TemporaryDirectory(dir=paths.HERE) as d, contextlib.ExitStack() as stack:
            for obj, name, value in [(module, 'safe_path', Path), (module, 'classify', classify),
                                     (module.v4_runtime, 'interpreter', lambda *a: Path('/usr/bin/python3')),
                                     (module.v4_runtime, 'isolated', isolated),
                                     (module.v4_strategies, 'draws', draws),
                                     (module.gen_inputs, 'generate_candidates', lambda *a: dict(candidates=[], errors=[])),
                                     (module.gen_inputs, 'feedback', lambda *a: None)]:
                stack.enter_context(patch.object(obj, name, side_effect=value))
            module.run([t], d, Path('/usr/bin/python3'), client=client, k=k, workers=1, arms=arms)
            rows = [json.loads(l) for l in (Path(d)/'gen.jsonl').read_text().splitlines()]
            self.manifest = json.loads((Path(d)/'manifest.json').read_text())
            self.accounting = (json.loads((Path(d)/'hypotheses/proposal_accounting.json').read_text())
                               if (Path(d)/'hypotheses').exists() else None)
        return {(r['arm'], r['sample']): r for r in rows}, client

    def test_hyp_hybrid_flow_and_strict_round2(self):
        rows, client = self.generate(arms=['hyp-hybrid', 'hyp-witness-only'], client=FakeClient(round1=(0, -50)))
        r = rows['hyp-hybrid', 0]
        # Ranking: mutant-diff witnessed (order 1) first, then witnessed (0), then unwitnessed (2).
        self.assertEqual([h['order'] for h in r['shown_hypotheses']], [1, 0, 2])
        # Round 1 input f(-50) satisfies T of order 1 (shown index 0): only indices 1 and 2 are targeted.
        self.assertEqual(r['missed_hypothesis_indices'], [1, 2])
        methods = [(a['hypothesis_index'], a['method']) for a in r['generator_attempts']]
        # Index 1 (x > 100): T usable as a filter, no LLM. Index 2 (x > 10**9): unusable -> LLM strategy (+1 retry).
        self.assertEqual(methods, [(1, 'T-filter'), (2, 'T-filter'), (2, 'LLM-strategy'), (2, 'LLM-strategy')])
        self.assertEqual(r['round2_strategy_requests'], 2)
        self.assertEqual(r['t_filter_requests'], 2)
        self.assertEqual({s['call'] for s in r['selected_inputs']} <= {'f(150)', 'f(101)'}, True)
        self.assertEqual(len(r['selected_inputs']), 2)
        # Strict: only requested calls are admitted (f(999) is not); round-1 assertions kept first.
        self.assertEqual(r['assertions'][:2], r['round1_assertions'])
        self.assertNotIn('assert f(999) == 999', r['assertions'])
        self.assertEqual(r['llm_calls'], 1 + 2 + 1)
        # Proposal: one per task, counted separately.
        proposals = [q for q in client.requests if 'JSON only' in q['messages'][0]['content']]
        self.assertEqual(len(proposals), 1)
        self.assertEqual(r['hypothesis_proposal']['calls_per_task'], 1)
        self.assertFalse(r['hypothesis_proposal']['counted_in_llm_calls'])
        self.assertEqual(self.accounting['proposal_calls'], 1)
        self.assertEqual(self.manifest['hypothesis_proposal_calls'], 1)
        w = rows['hyp-witness-only', 0]
        self.assertEqual(w['llm_calls'], 0)
        self.assertEqual(w['assertions'], ['assert f(-417) == None', 'assert f(272) == None'])
        self.assertTrue(w['expected_placeholders'])
        self.assertEqual(len(r['hypothesis_input_records']), len(r['assertions']))

    def test_proposal_shared_by_samples_and_fixed_seed(self):
        rows, client = self.generate(arms=['hyp-hybrid'], k=2)
        proposals = [q for q in client.requests if 'JSON only' in q['messages'][0]['content']]
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0]['seed'], paths.CONFIG['seeds']['hypotheses'])
        self.assertEqual(proposals[0]['params']['temperature'], 0)
        self.assertEqual(rows['hyp-hybrid', 0]['shown_hypotheses'], rows['hyp-hybrid', 1]['shown_hypotheses'])
        r1 = [q['seed'] for q in client.requests if 'Hypotheses about how' in q['messages'][-1]['content']]
        self.assertEqual(len(set(r1)), 2)   # round-one seeds differ per sample

    def test_no_witness_values_in_any_prompt(self):
        _, client = self.generate(arms=['hyp-hybrid', 'hyp-witness-only'], fail=True)
        texts = [m['content'] for q in client.requests for m in q['messages']]
        self.assertTrue(texts)
        for text in texts:
            for value in ('272', '417'):
                self.assertNotIn(value, text)
        hyp = [t for t in texts if 'Hypotheses about how the code' in t]
        self.assertEqual(len(hyp), 1)
        self.assertIn('T:', hyp[0]); self.assertIn('R: "Return zero otherwise."', hyp[0])
        block = hyp_prompts.raw_block(dict(task(), hypothesis_meta=dict(shown=[dict(R='r', chain='c', T='x > 1',
                                     witness=dict(input_repr='(272,)', call='f(272)'))])))
        self.assertNotIn('272', block)

    def test_caps_and_retries(self):
        for kwargs in (dict(fail=True, pool=()), dict(client=FakeClient(round1=range(25))),
                       dict(fail=True, pool=(), n_hints=0)):
            rows, _ = self.generate(arms=['hyp-hybrid', 'flat-hybrid', 'plain-hybrid'], **kwargs)
            for r in rows.values():
                self.assertLessEqual(r['llm_calls'], 8)
                self.assertLessEqual(r['n_assertions'], 20)
            h = rows['hyp-hybrid', 0]
            if kwargs.get('fail'):
                self.assertEqual(h['round2_strategy_requests'], 6)
                self.assertEqual(h['llm_calls'], 7)
            else:
                self.assertGreaterEqual(h['dropped_assertions'], 5)

    def test_budgets_equal_rel_per_unit(self):
        rows, _ = self.generate(arms=['hyp-hybrid', 'rel-hybrid', 'flat-hybrid', 'plain-hybrid'], fail=True)
        per = {}
        for r in rows.values():
            for b in r['hint_budgets']:
                self.assertEqual(b['actual'], b['target'])
                per.setdefault(b.get('hint_index'), set()).add(b['actual'])
        self.assertTrue(per and all(len(v) == 1 for v in per.values()), per)
        t = dict(task(), hypothesis_meta=dict(shown=[dict(R='r', chain='c', T='x > 1')]))
        t['relation_meta'] = relations.extract(t)
        for i in (None, 0):
            self.assertEqual(hyp_prompts.block(t, i)[1]['target'], rel_prompts.block('rel-hybrid', t, i)[1]['target'])

    def test_disabled_new_arms_equal_v12_rel(self):
        for arms in (rel_prompts.NEW_ARMS + rel_prompts.REFERENCES, v4_prompts.LEGACY_ARMS):
            old, oc = self.generate(v12_run, arms=arms)
            new, nc = self.generate(arms=arms)
            self.assertNotIn('hypothesis_version', self.manifest)
            self.assertNotIn('hyp_candidates', self.isolated_modes)
            self.assertEqual([(q['key'], q['seed']) for q in oc.requests], [(q['key'], q['seed']) for q in nc.requests])
            self.assertEqual(oc.requests, nc.requests)
            for key in old:
                self.assertEqual({k: v for k, v in old[key].items() if k != 'run_id'},
                                 {k: v for k, v in new[key].items() if k != 'run_id'})
        for a in v12_prompts.ARMS:
            if a == 'witness-only': continue   # no LLM request, no seed
            for stage in range(4):
                self.assertEqual(v4_prompts.seed(37, a, 2, stage, 1, 1), v12_prompts.seed(37, a, 2, stage, 1, 1))
        arms = [a for a in v4_prompts.ARMS if a != 'witness-only']
        seeds = {v4_prompts.seed(n, a, s, st, rq, rt) for n in range(164) for a in arms
                 for s in range(3) for st in range(3) for rq in range(3) for rt in range(2)}
        self.assertEqual(len(seeds), 164*(len(arms)-1)*3*3*3*2)  # only flat == concept-hybrid (registered reuse)


class ParsingRankingTests(Base):
    def candidates(self):
        return candidates_for(task())

    def test_parsing_variants_and_failures(self):
        t, c = task(), self.candidates()
        rows, fails = hypotheses.parse_proposals('Sure!\n```json\n' + json.dumps(HYPS) + '\n```\nDone.', t, c)
        self.assertEqual([r['order'] for r in rows], [0, 1, 2]); self.assertEqual(fails, [])
        self.assertEqual(rows[2]['chain_lines'], [4, 6])
        self.assertTrue(rows[1]['covered_site']); self.assertEqual(rows[0]['covered_lines'], [3, 4])
        self.assertFalse(rows[0]['covered_site'])
        rows, _ = hypotheses.parse_proposals(json.dumps(dict(hypotheses=HYPS[:1])), t, c)
        self.assertEqual(len(rows), 1)
        for raw in ('no json here', '{"a": 1}', '', '[1, 2]'):
            self.assertEqual(hypotheses.parse_proposals(raw, t, c), ([], [dict(reason='proposal_parse_failed')]))
        bad = [dict(HYPS[0], R='a clause that is not in the docstring'),
               dict(HYPS[0], chain=dict(lines=[99], explanation='x')),
               dict(HYPS[0], chain=dict(lines=[3], explanation='')),
               dict(HYPS[0], T='def trigger(x):\n    import os\n    return True'),
               dict(HYPS[0], T='def trigger(x):\n    return f(x) > 1'),
               dict(HYPS[0], T='def trigger(x):\n    x.append(1)\n    return True'),
               dict(HYPS[0], T='def trigger(y):\n    return y'),
               dict(HYPS[0], T='def trigger(x):\n    return x >'),
               dict(HYPS[0], expected_violation=''), 'not an object']
        rows, fails = hypotheses.parse_proposals(json.dumps(bad + [HYPS[1]]*3), t, c)
        self.assertEqual(rows, [])
        self.assertEqual(len(fails), 13)
        self.assertTrue(all(f['reason'] == 'proposal_rejected' for f in fails))
        self.assertIn('cap', fails[-1]['error'])
        quoted, _ = hypotheses.parse_proposals(json.dumps([dict(HYPS[1], R='"return  ZERO otherwise"')]), t, c)
        self.assertEqual([q['R_quotation'] for q in quoted], ['exact'])
        near, _ = hypotheses.parse_proposals(json.dumps([dict(HYPS[1], R='Return zerro otherwise')]), t, c)
        self.assertEqual([q['R_quotation'] for q in near], ['near'])

    def test_rank_order(self):
        rows = [dict(order=0, witness=None, mutant_diff=False), dict(order=1, witness={'x': 1}, mutant_diff=False),
                dict(order=2, witness={'x': 2}, mutant_diff=True), dict(order=3, witness=None, mutant_diff=False),
                dict(order=4, witness={'x': 3}, mutant_diff=True)]
        self.assertEqual([r['order'] for r in hypotheses.rank(rows)], [2, 4, 1, 0, 3])

    def test_proposal_prompt_all_sites(self):
        t, c = task(), self.candidates()
        text = hypotheses.proposal_messages(t, c)[1]['content']
        self.assertEqual(text.count('[executed by existing tests]'), 5)
        self.assertEqual(text.count('[NOT executed by existing tests]'), 1)
        self.assertIn('  4|     if x > 0:', text)
        self.assertNotIn('f(100)', text)


class SandboxTests(Base):
    """Real isolated CPU worker (dedicated v4 venv): purity, base satisfaction, witness search, mutants, hits."""

    def test_checks_on_synthetic_put(self):
        t = task(0, REAL_PUT)
        t['base'] = 'def check(candidate):\n    assert candidate(0) == 0\n    assert candidate(3) == 4\n'
        proposals = [dict(R='Return x plus one when x is positive.', chain=dict(lines=[3, 5, 6], explanation='x > 50'),
                          T='def trigger(x):\n    return x > 50', expected_violation='x + 2'),
                     dict(R='Return zero otherwise.', chain=dict(lines=[4, 8], explanation='x <= 0'),
                          T='x <= 0', expected_violation='nonzero'),
                     dict(R='Return zero otherwise.', chain=dict(lines=[4, 8], explanation='never'),
                          T='lambda x: x > 5000', expected_violation='none'),
                     dict(R='Return x plus one when x is positive.', chain=dict(lines=[4, 7], explanation='odd'),
                          T='x % 2 == 1 and x > 3', expected_violation='wrong')]
        with tempfile.TemporaryDirectory(dir=paths.HERE) as d:
            c = v4_runtime.isolated('hyp_candidates', dict(task=t), Path(d)/'c')
            self.assertTrue(c['base_ok'])
            covered = {s['line']: s['covered'] for s in c['sites']}
            self.assertEqual(covered, {1: True, 3: True, 4: True, 5: True, 6: False, 7: True, 8: True})
            self.assertTrue(c['survivor_mutants'])
            self.assertTrue(all('[data' in s['chain'] or '[control]' in s['chain'] or 'line' in s['chain'] for s in c['sites']))
            rows, fails = hypotheses.parse_proposals(json.dumps(proposals), t, c)
            self.assertEqual((len(rows), fails), (4, []))
            # A tampered (impure) trigger is rejected again inside the sandbox.
            rows.append(dict(rows[0], order=9, T='def trigger(x):\n    print(x)\n    return True'))
            chk = v4_runtime.isolated('hyp_check', dict(task=t, hypotheses=rows, candidates=c, seed=7), Path(d)/'k', timeout=600)
            reasons = {f['order']: f['reason'] for f in chk['failures']}
            self.assertEqual(reasons, {1: 'already tested', 9: 'trigger_rejected'})
            by = {h['order']: h for h in chk['hypotheses']}
            self.assertTrue(by[0]['witnessed'] and by[0]['mutant_diff'])
            self.assertGreater(int(by[0]['witness']['input_repr'][1:-2]), 50)
            self.assertEqual(by[0]['witness']['call'], 'f' + by[0]['witness']['input_repr'][:-2] + ')')
            self.assertTrue(by[2]['unwitnessed'] and not by[2]['witnessed'])   # kept, marked
            self.assertTrue(by[3]['witnessed'])
            self.assertEqual([h['order'] for h in hypotheses.rank(chk['hypotheses'])][0], 0)
            self.assertEqual([h['order'] for h in hypotheses.rank(chk['hypotheses'])][-1], 2)
            # Determinism of the seeded search.
            again = v4_runtime.isolated('hyp_check', dict(task=t, hypotheses=rows, candidates=c, seed=7), Path(d)/'k2', timeout=600)
            self.assertEqual([h['witness'] for h in again['hypotheses']], [h['witness'] for h in chk['hypotheses']])
            shown = hypotheses.rank(chk['hypotheses'])
            cl = v4_runtime.isolated('hyp_classify', dict(task=t, hypotheses=shown,
                                     assertions=['assert f(60) == 61', 'assert f(-5) == 0', 'assert f(2000) == 2001']), Path(d)/'cl')
            hits = {r['call']: (r['valid'], r['hypothesis_hits']) for r in cl['records']}
            self.assertEqual(hits['f(60)'][1][0], True)
            self.assertFalse(any(hits['f(-5)'][1]))
            self.assertFalse(hits['f(2000)'][0])  # outside the validator: not counted
            dr = v4_runtime.isolated('hyp_draw', dict(task=t, hypothesis=shown[0], seed=3), Path(d)/'dr')
            self.assertTrue(dr['candidates'])
            self.assertTrue(all(int(x['input_repr'][1:-2]) > 50 for x in dr['candidates']))
            at = v4_runtime.isolated('hyp_attribution', dict(task=t, hypotheses=shown, assertions=['assert f(60) == 61']), Path(d)/'at')
            self.assertEqual(at['records'][0]['call'], 'f(60)')
            self.assertTrue(at['records'][0]['hypothesis_hits'][0])

    def test_hyp_report_attribution(self):
        rows = [dict(task=0, sample=0, arm='hyp-hybrid',
                     shown_hypotheses=[dict(order=0, witnessed=False, mutant_diff=False, covered_site=True)],
                     hypothesis_input_records=[dict(call='f(1)', hypothesis_hits=[True]), dict(call='f(2)', hypothesis_hits=[False])])]
        good = dict(valid=True, d_i=True, ref=dict(emit=True, canon_ok=True))
        out = hyp_report.summarize(rows, {'0': dict(calls={'f(1)': good, 'f(2)': good})})['hyp-hybrid']
        self.assertEqual((out['d_io_inputs'], out['with_t_hit'], out['from_unwitnessed'], out['from_covered_site']), (2, 1, 1, 1))


if __name__ == '__main__': unittest.main()
