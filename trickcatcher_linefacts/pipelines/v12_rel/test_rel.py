"""Offline B3 correctness/integration tests; sockets forbidden, fake LLM only."""
import contextlib
import json
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from . import relations, rel_prompts, rel_report, run_v4, paths, offline_client, v4_prompts
from ..v11_fair import run_v4 as old_run, v4_prompts as old_prompts
from ..v11_fair import prompts as old_direct, offline_client as old_cache


def task(n_hints=3):
    put = ('def f(x):\n    """Return the value x plus one when x is positive. Return zero otherwise."""\n'
           '    value = x + 1\n    if x > 0:\n        return value\n    return 0\n')
    valid = 'def valid(x):\n    return True\n'
    strategy = 'def strategy():\n    return st.just((100,))\n'
    facts = [dict(kind='STMT',line=5,lines=[5],text=f'Unique hint {i}: line 5 is untested.',
                  witness_call='f(100)') for i in range(n_hints)]
    return dict(task=0,entry='f',put=put,base='def check(candidate):\n    assert candidate(0) == 0\n',
                split='dev',doc_fail=False,facts_version='v4',mined_valid_src=valid,
                valid_sha256=run_v4.preconditions.sha(valid),strategy_src=strategy,
                strategy_sha256=run_v4.preconditions.sha(strategy),concept_meta=facts,placebo_meta=facts,
                concept_facts=[f['text'] for f in facts],placebo_facts=[f['text'] for f in facts],tool_inputs=['f(100)'])


class FakeClient:
    model = paths.CONFIG['model']

    def __init__(self, assertions=1):
        self.requests = []
        self.assertions = assertions

    def chat(self,messages,seed,**kwargs):
        key,params = offline_client.request(messages,seed,**kwargs)
        self.requests.append(dict(messages=messages,seed=seed,key=key,params=params))
        if 'Hypothesis' in messages[0]['content']:
            text = 'def strategy():\n    return st.just((100,))'
        elif 'sample_one' in messages[0]['content']:
            text = 'def sample_one():\n    return (100,)'
        elif 'For EXACTLY' in messages[-1]['content']:
            text = 'assert f(999) == 999\nassert f(101) == 102\nassert f(100) == 101'
        else:
            text = '\n'.join(f'assert f({i}) == {i}' for i in range(self.assertions))
        return dict(text=text,n_in=1,n_out=1,seconds=0,key=key,params=params)


class RelTests(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(socket.socket,'connect',side_effect=AssertionError('network forbidden')))
        self.stack.enter_context(patch.object(socket,'create_connection',side_effect=AssertionError('network forbidden')))

    def generate(self,module=run_v4,arms=None,*,n_assertions=1,fail=False,good=True,n_hints=3):
        t = task(n_hints)
        client = FakeClient(n_assertions)
        def classify(t,d,python,*,assertions=None,shown=(),**kwargs):
            records = [] if assertions is not None else [dict(input_repr=f'({i},)',call=f'f({i})',
                        valid=good,shown_hits=[good]*len(shown)) for i in (100,101)]
            return dict(records=records,summary=dict(shown_hit_counts=[0]*len(shown),
                        valid=sum(r['valid'] for r in records),removed=0))
        def draws(*args,**kwargs):
            if fail: raise ValueError('fake rejection')
            return dict(candidates=[],nonliteral=0,wrong_arity=0,errors=[])
        def isolated(mode,job,*args,**kwargs):
            self.assertEqual(mode,'relations')
            return relations.extract(job['task'])
        with tempfile.TemporaryDirectory(dir=paths.HERE) as d, contextlib.ExitStack() as stack:
            for obj,name,value in [(module,'safe_path',Path),(module,'classify',classify),
                                   (module.v4_runtime,'interpreter',lambda *a:Path('/usr/bin/python3')),
                                   (module.v4_runtime,'isolated',isolated),
                                   (module.v4_strategies,'draws',draws),
                                   (module.gen_inputs,'generate_candidates',lambda *a:dict(candidates=[],errors=[])),
                                   (module.gen_inputs,'feedback',lambda *a:None)]:
                stack.enter_context(patch.object(obj,name,side_effect=value))
            kw = dict(client=client,k=1,workers=1)
            if module is run_v4: kw['arms'] = arms
            module.run([t],d,Path('/usr/bin/python3'),**kw)
            rows = [json.loads(l) for l in (Path(d)/'gen.jsonl').read_text().splitlines()]
        return {r['arm']:r for r in rows},client

    def test_synthetic_observed_chain(self):
        r = relations.extract(task())
        self.assertTrue(r['base_ok'])
        h = r['hints'][0]
        self.assertEqual([(d['name'],d['definition'],d['use']) for d in h['data']],[('value',3,5)])
        self.assertEqual([(c['line'],c['outcome'],c['base']) for c in h['control']],[(4,'T','never')])
        self.assertEqual(h['spec']['clause'],1)
        text = relations.render(h)
        self.assertIn('condition line 4',text)
        self.assertIn('value `value` from line 3',text)
        self.assertNotIn('f(100)',text)
        self.assertNotIn('spec clause',relations.render(h,False))

    def test_else_always_and_unobserved_data(self):
        t=task(1);t['put']=t['put'].replace('    return 0\n','    else:\n        return 0\n');t['concept_meta'][0].update(line=7,lines=[7])
        r=relations.extract(t)['hints'][0]
        self.assertEqual(r['control'][0]['outcome'],'F')
        self.assertEqual(r['control'][0]['base'],'always')
        self.assertFalse(r['data'])
        t=task(1);t['concept_meta'][0]['witness_call']=None
        r=relations.extract(t)['hints'][0]
        self.assertFalse(r['data'])  # don't invent a static edge on the unseen return

    def test_redefinitions_and_loop_carried_du(self):
        t=task(1)
        t.update(put='def f(x):\n    """Sum x."""\n    value = 0\n    for item in x:\n        value += item\n    return value\n',
                 base='def check(candidate):\n    assert candidate([2, 3]) == 5\n')
        t['concept_meta'][0].update(line=5,lines=[5],witness_call='f([4])')
        h=relations.extract(t)['hints'][0]
        self.assertEqual({(d['name'],d['definition']) for d in h['data']},
                         {('item',4),('value',3),('value',5)})
        self.assertEqual(h['control'][0]['base'],'always')

    def test_nested_guards_and_no_lexical_match(self):
        t=task(1)
        t.update(put='def f(x):\n    """Bananas."""\n    if x > 0:\n        if x < 2:\n            return x\n    return 0\n',
                 base='def check(candidate):\n    assert candidate(3) == 0\n')
        h=relations.extract(t)['hints'][0]
        self.assertEqual([(c['line'],c['base']) for c in h['control']],[(3,'always'),(4,'never')])
        self.assertIsNone(h['spec'])

    def test_real_humaneval_chains(self):
        source=paths.REPO/'trickcatcher_linefacts/out/tasks_v7hyb_v4.json'
        tasks={t['task']:t for t in json.loads(source.read_text())['tasks']}
        h=relations.extract(tasks[3])['hints'][0]
        self.assertEqual([(d['name'],d['definition'],d['use']) for d in h['data']],
                         [('balance_sum',24,26)])
        self.assertIn('balance',h['spec']['text'])
        h=relations.extract(tasks[0])['hints'][0]
        self.assertEqual({(d['name'],d['definition']) for d in h['data']},
                         {('i',12),('j',13),('numbers',4),('threshold',4)})
        self.assertEqual([c['line'] for c in h['control']],[12,13])
        h=relations.extract(tasks[2])['hints'][0]
        self.assertEqual([(d['name'],d['definition']) for d in h['data']],[('number',3)])

    def test_raw_flat_byte_identical_for_all_133_tasks(self):
        source=paths.REPO/'trickcatcher_linefacts/out/tasks_v7hyb_v4.json'
        for t in json.loads(source.read_text())['tasks']:
            self.assertEqual(rel_prompts.round1('flat-hybrid',t,equalize=False)[0],
                             old_run.gen_prompts.messages(*old_direct.build('concept',t)))
            for i,f in enumerate(t['concept_meta']):
                self.assertEqual(rel_prompts.hybrid('flat-hybrid',t,i,[],equalize=False)[0],
                                 old_prompts.hybrid_messages(t,f,[]))

    def test_prompt_blocks_and_budgets(self):
        t=task();t['relation_meta']=relations.extract(t)
        for i in (None,0,1,2):
            blocks=[rel_prompts.block(a,t,i) for a in rel_prompts.NEW_ARMS+rel_prompts.REFERENCES if a!='witness-only']
            self.assertEqual(len({rel_prompts.tokens(b) for b,r in blocks}),1)
            self.assertTrue(all(r['target']==r['actual'] for b,r in blocks))
        review=rel_prompts.round1('review-hybrid',t)[0][-1]['content']
        self.assertIn('boundaries, off-by-one',review)
        self.assertNotIn('Unique hint',review)
        rel=rel_prompts.hybrid('rel-hybrid',t,0)[0][-1]['content']
        self.assertIn('Unique hint 0',rel);self.assertIn('[control]',rel);self.assertIn('[data,',rel)
        self.assertIn('spec clause',rel)
        nospec=rel_prompts.hybrid('rel-nospec-hybrid',t,0)[0][-1]['content']
        self.assertNotIn('spec clause',nospec);self.assertIn('[data,',nospec)
        hidden=rel_prompts.hybrid('review-hybrid',t,0)[0][-1]['content']
        self.assertNotIn('Unique hint',hidden)
        self.assertNotIn('f(100)',rel)

    def test_new_arms_strict_requests_and_references(self):
        rows,client=self.generate(arms=rel_prompts.NEW_ARMS+rel_prompts.REFERENCES)
        self.assertEqual(set(rows),set(rel_prompts.NEW_ARMS+rel_prompts.REFERENCES))
        for arm in rel_prompts.NEW_ARMS:
            r=rows[arm]
            self.assertEqual(r['round2_strategy_requests'],3)
            self.assertEqual([a['fact_index'] for a in r['generator_attempts']],[0,1,2])
            self.assertEqual(r['assertions'][-2:],[f"assert {s['call']} == {101 if s['call']=='f(100)' else 102}" for s in r['selected_inputs']])
            self.assertNotIn('assert f(999) == 999',r['assertions'])
            self.assertTrue(all(b['actual']==b['target'] for b in r['hint_budgets']))
        self.assertEqual(rows['witness-only']['llm_calls'],0)
        self.assertEqual(rows['witness-only']['assertions'],['assert f(100) == None','assert f(101) == None'])
        for a in ('placebo-hybrid','plain-hybrid'):
            self.assertEqual(rows[a]['matched_strategy_requests'],rows['flat-hybrid']['round2_strategy_requests'])
        # Equal budget per unit (round-one block, or one round-two hint) across arms.
        per={}
        for r in rows.values():
            for b in r['hint_budgets']: per.setdefault(b.get('hint_index'),set()).add(b['actual'])
        self.assertTrue(per and all(len(v)==1 for v in per.values()), per)

    def test_retry_call_and_assertion_caps(self):
        for kwargs in (dict(fail=True),dict(n_assertions=21),dict(fail=True,n_hints=10)):
            rows,_=self.generate(arms=rel_prompts.NEW_ARMS,**kwargs)
            for r in rows.values():
                self.assertLessEqual(r['llm_calls'],8)
                self.assertLessEqual(r['n_assertions'],20)
            if kwargs.get('fail'):
                self.assertTrue(all(r['round2_strategy_requests']==6 for r in rows.values()))
            if kwargs.get('n_assertions'):
                self.assertTrue(all(r['dropped_assertions']>=1 for r in rows.values()))

    def test_config_selection_and_required_flags(self):
        with patch.dict(paths.CONFIG,arms=['rel-hybrid']):
            rows,_=self.generate()
        self.assertEqual(set(rows),{'rel-hybrid'})
        with patch.dict(paths.CONFIG,strict_round2=False):
            with self.assertRaisesRegex(ValueError,'four fairness flags'):
                run_v4.run([],paths.HERE/'unused',Path('/usr/bin/python3'),arms=['rel-hybrid'])

    def test_empty_hints_and_empty_verified_inputs(self):
        for kwargs in (dict(n_hints=0),dict(good=False)):
            rows,_=self.generate(arms=rel_prompts.NEW_ARMS,**kwargs)
            self.assertTrue(all(r['selected_inputs']==[] for r in rows.values()))
            self.assertTrue(all(r['assertions']==r['round1_assertions'] for r in rows.values()))

    def test_actual_isolated_relation_worker(self):
        t=task(1)
        with tempfile.TemporaryDirectory(dir=paths.HERE) as d:
            actual=run_v4.v4_runtime.isolated('relations',dict(task=t),d)
        self.assertEqual(actual,relations.extract(t))

    def test_supplied_traces_incomplete_guards_and_loop_else(self):
        t=task(1)
        sites,base,witnesses,_=relations.collect_traces(t)
        truncated=[(base[0][0],base[0][1],'timeout',None)]
        h=relations.extract(t,sites=sites,base_traces=truncated,witness_traces=witnesses)['hints'][0]
        self.assertEqual(h['control'][0]['base'],'unknown (incomplete base trace)')
        t.update(put='def f(x):\n    """Return x."""\n    for item in x:\n        pass\n    else:\n        return len(x)\n',
                 base='def check(candidate):\n    assert candidate([1]) == 1\n')
        t['concept_meta'][0].update(line=6,lines=[6],witness_call='f([2])')
        self.assertFalse(relations.extract(t)['hints'][0]['control'])

    def test_ref_report_and_random_subsets(self):
        good=dict(valid=True,d_i=True,ref=dict(emit=True,canon_ok=True,put_ok=False))
        invalid=dict(valid=False,d_i=True,ref=dict(emit=True,canon_ok=True,put_ok=False))
        self.assertEqual(rel_report.metrics([[('f(0)',good),('f(0)',good),('f(1)',invalid)]]),
                         dict(D_I=1,D_IO=1,D_I_samples=1,D_IO_samples=1,correct_failing=1,
                              failing=2,precision=.5,false_alarms=1))
        indexed={(0,0,'rel-hybrid'):[('f(0)',{}),('f(1)',good)],
                 (0,0,'flat-hybrid'):[('f(2)',{})]}
        c=rel_report.comparison(indexed,'rel-hybrid','flat-hybrid',True)
        self.assertEqual(c,rel_report.comparison(indexed,'rel-hybrid','flat-hybrid',True))
        self.assertEqual(c['draws'],100)
        self.assertGreater(c['detecting_samples'][0],0)  # cannot be prefix truncation
        self.assertLess(c['detecting_samples'][0],1)
        rows=[dict(task=0,sample=0,arm=a,split='dev',asserts=[dict(src='assert f(1) == None')])
              for a in ('rel-hybrid','flat-hybrid','witness-only')]
        report=rel_report.summarize({0:dict(entry='f')},rows,{'0':dict(calls={'f(1)':good})})
        self.assertEqual(report['oracle'],'ref')
        self.assertEqual(report['cohorts']['dev']['arms']['witness-only']['D_IO'],1)
        with self.assertRaises(ValueError): rel_report.summarize({0:dict(entry='f')},rows,{})

    def test_disabled_legacy_end_to_end_equal_and_cache_keys(self):
        old,oc=self.generate(old_run)
        new,nc=self.generate(arms=v4_prompts.LEGACY_ARMS)
        self.assertEqual(oc.requests,nc.requests)
        for arm in old:
            self.assertNotIn('hint_budgets',new[arm])
            self.assertEqual({k:v for k,v in old[arm].items() if k!='run_id'},
                             {k:v for k,v in new[arm].items() if k!='run_id'})
        for a in v4_prompts.LEGACY_ARMS:
            for stage in range(4):
                self.assertEqual(v4_prompts.seed(37,a,2,stage,1,1),old_prompts.seed(37,a,2,stage,1,1))
        for r in nc.requests:
            self.assertEqual(offline_client.request(r['messages'],r['seed'],**{k:v for k,v in r['params'].items() if k not in ('seed','model')}),
                             old_cache.request(r['messages'],r['seed'],**{k:v for k,v in r['params'].items() if k not in ('seed','model')}))


if __name__=='__main__': unittest.main()
