"""CPU vote/export semantics, independent of any held-out oracle or endpoint."""
import signal
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from . import final_worker as fw
from . import final_run as fr
from ...pipelines.v11_fair_vp import scorer


class FinalVote(unittest.TestCase):
    def setUp(self):
        self.old=signal.signal(signal.SIGALRM,fw.native.expired)
    def tearDown(self):
        signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,self.old)
    def job(self,put,variants):
        return dict(entry='f',put=put,variants=[dict(index=i,src=s) for i,s in enumerate(variants)],
                    pool=[dict(input_repr='(1,)')],atol=0.01,call_timeout=1,load_timeout=1)
    def test_crashing_put_keeps_successful_variant_vote(self):
        job=self.job('def f(x): raise ValueError()', ['def f(x): return 7']*3)
        [r]=fw.vote(job)['records']
        self.assertEqual(r['put_status'],'ValueError')
        self.assertEqual(r['assertion'],'assert f(1) == 7')
    def test_tolerance_suppresses_spurious_disagreement(self):
        job=self.job('def f(x): return [1.0]', ['def f(x): return [1.005]'])
        self.assertNotIn('assertion',fw.vote(job)['records'][0])
    def test_container_types_stay_distinct(self):
        job=self.job('def f(x): return [1]', ['def f(x): return (1,)'])
        [r]=fw.vote(job)['records']
        self.assertEqual(r['assertion'],'assert f(1) == (1,)')
        self.assertFalse(scorer.output_equal([1],(1,)))
    def test_failed_variants_cannot_vote(self):
        job=self.job('def f(x): return 0',['def f(x): raise TypeError()'])
        [r]=fw.vote(job)['records']
        self.assertNotIn('assertion',r)
        self.assertEqual(r['variant_outcomes'],[dict(index=0,status='TypeError')])
    def test_vote_tie_keeps_generation_order(self):
        job=self.job('def f(x): return 0',['def f(x): return 7','def f(x): return 8'])
        self.assertEqual(fw.vote(job)['records'][0]['assertion'],'assert f(1) == 7')


class SharedGeneration(unittest.TestCase):
    def test_one_pool_fourteen_calls_tokens_cap_and_partial_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);task=dict(task=7,entry='f',put='def f(x): return x',
                    base='def check(candidate):\n    assert candidate(0)==0\n',split='heldout',
                    canon='hidden-answer-fixture',mined_valid_src='hidden-validator-fixture',atol=0.01)
            bundle=root/'tasks.json';bundle.write_text(json.dumps(dict(tasks=[task])))
            args=SimpleNamespace(tasks=bundle,out=root/'run',fake=True,online=False,k=3,workers=1,python=None)
            requests=[]
            original_client=fr.ScriptedClient
            class CountingClient(original_client):
                def chat(self,messages,seed,**params):
                    self_test.assertNotIn('hidden-answer-fixture',json.dumps(messages))
                    requests.append(seed)
                    response=super().chat(messages,seed,**params)
                    response.update(n_in=len(requests),n_out=2*len(requests))
                    return response
            self_test=self
            def isolated(mode,job,directory,python,timeout):
                self.assertNotIn('hidden-answer-fixture',json.dumps(job))
                if mode=='filter':return dict(survivors=job['variants'],base_results=[])
                return dict(records=[dict(assertion=f"assert f({i}) == {i}",put_status='ok',variant_outcomes=[])
                                     for i in range(len(job['pool']))])
            def generate(code,visible,*args,**kwargs):
                self.assertEqual(set(visible),{'task','entry','put','base','split'})
                return dict(candidates=[dict(input_repr=f'({i},)',occurrences=1) for i in range(40)],errors=[])
            with patch.object(fr,'ScriptedClient',CountingClient), \
                 patch.object(fr,'isolated',side_effect=isolated), \
                 patch.object(fr.original,'generate_candidates',side_effect=generate) as generator, \
                 patch.object(fr.v4_runtime,'interpreter',return_value=Path(sys.executable)), \
                 contextlib.redirect_stdout(io.StringIO()):
                rows=fr.run(args)
                self.assertEqual(len(requests),14)
                self.assertEqual(requests,[fr.original.seed(7,stage,i) for stage,n in [('variant',10),('generator',4)] for i in range(n)])
                self.assertEqual(generator.call_count,4)
                self.assertEqual([r['llm_calls'] for r in rows],[5,5,4])
                self.assertEqual(sum(r['n_in'] for r in rows),105)
                self.assertEqual(sum(r['n_out'] for r in rows),210)
                self.assertEqual(len({r['generation_id'] for r in rows}),1)
                self.assertEqual(len({r['pool_sha256'] for r in rows}),1)
                self.assertEqual(len({tuple(r['resample_positions']) for r in rows}),3)
                self.assertTrue(all(r['n_assertions']==20 and r['n_assertions_dropped']==80 for r in rows))
                self.assertEqual([r['n_pool'] for r in rows],[160]*3)
                ledger=json.loads((args.out/'artifacts/7/shared/generation.json').read_text())
                self.assertEqual(len(ledger['calls']),14)
                (args.out/'artifacts/7/1/result.json').unlink()
                resumed=fr.run(args)
                self.assertEqual(resumed,rows)
                self.assertEqual(len(requests),14)
                self.assertEqual(generator.call_count,4)
            manifest=json.loads((args.out/'manifest.json').read_text())
            self.assertEqual((manifest['variant_calls'],manifest['generator_calls'],manifest['budget_scope']), (10,4,'task'))
            self.assertEqual(manifest['llm_budget_per_task'],24)

    def test_reduced_mode_and_non_three_k_are_rejected(self):
        for options in (['--variant-calls','4'],['--generator-calls','2'],['--k','2']):
            with self.subTest(options=options), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                fr.main(['--tasks','absent.json','--out','unused',*options])
            self.assertEqual(caught.exception.code,2)

if __name__=='__main__':unittest.main()
