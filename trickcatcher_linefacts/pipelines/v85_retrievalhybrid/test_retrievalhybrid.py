import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from . import paths, prompts, retrieval_adapter, v4_runtime, gen_inputs, comparison, transport
from .prepare_comparison import public_projection
from .test_fair import FakeClient, task


class RetrievalHybridTests(unittest.TestCase):
    def card(self):
        return dict(id='fixture', title='Empty input', where={'summary':'sequence'},
                    how={'mechanism':'wrong empty guard','trigger_template':'empty list'},
                    what={'observable_failure':'wrong result'})

    def test_binding_retains_executable_gate_and_keeps_baseline_unchanged(self):
        original = task()
        fact = dict(kind='OUTCOME', line=3, cell=[7,'F'], reached=True, block=3,
                    text='Take false branch', witness_call='f([])')
        packet = dict(warning=None, results=[dict(concept=self.card(), evidence=[dict(line=3,end_line=3)])])
        before = json.dumps(original, sort_keys=True)
        with patch.object(retrieval_adapter,'search',return_value=packet), patch.object(retrieval_adapter.facts,'pick',return_value=[fact]):
            adapted, audit = retrieval_adapter.adapt(original,[fact],Path('unused'))
        self.assertEqual(adapted['concept_meta'][0]['cell'], [7,'F'])
        self.assertEqual(adapted['concept_meta'][0]['witness_call'], 'f([])')
        self.assertEqual(audit[0]['status'],'existing_v11_gap')
        self.assertEqual(json.dumps(original, sort_keys=True), before)
        self.assertIn('unverified', prompts.build('concept',adapted)[1])
        self.assertNotIn('Retrieved bug hypotheses', prompts.build('concept',original)[1])

    def test_weak_gate_and_unbound_card_are_explicit(self):
        packet = dict(warning=None, results=[dict(concept=self.card(),evidence=[dict(line=3)]),dict(concept=self.card(),evidence=[])])
        with patch.object(retrieval_adapter,'search',return_value=packet), patch.object(retrieval_adapter.facts,'pick',return_value=[]):
            adapted,audit=retrieval_adapter.adapt(task(),[],Path('unused'))
        self.assertEqual([r['status'] for r in audit],['line_reachability_only','no_executable_site'])
        self.assertEqual(adapted['concept_meta'][0]['lines'],[3])
        self.assertEqual(adapted['tool_inputs'],[])

    def test_public_projection_skips_reference_and_roundtrips_escapes(self):
        row=dict(task_id='HumanEval/0',prompt='def f(x):\n    """quote \\"""',test='def check(candidate):\n pass',entry_point='f',canonical_solution='SECRET_CANONICAL')
        projected=public_projection(json.dumps(row))
        self.assertEqual(projected,{k:v for k,v in row.items() if k!='canonical_solution'})
        self.assertNotIn('SECRET_CANONICAL',json.dumps(projected))

    def test_only_requested_arms_keep_original_seed_indices_and_strict_inputs(self):
        client=FakeClient()
        fixture=task();fixture['concept_meta']=fixture['concept_meta'][:1]
        def classify(t,directory,python,*,candidates=None,assertions=None,shown=(),requested_draws=None):
            records=[] if assertions is not None else [dict(input_repr='(100,)',call='f(100)',valid=True,shown_hits=[True]*len(shown))]
            return dict(records=records,summary=dict(shown_hit_counts=[0]*len(shown),valid=len(records)))
        from . import run_v4
        with tempfile.TemporaryDirectory() as directory, patch.object(run_v4,'safe_path',side_effect=Path), patch.object(v4_runtime,'interpreter',return_value=Path('/usr/bin/python3')), patch.object(run_v4,'classify',side_effect=classify), patch.object(run_v4.v4_strategies,'draws',return_value=dict(candidates=[],nonliteral=0,wrong_arity=0,errors=[])):
            path=run_v4.run([fixture],directory,Path('/usr/bin/python3'),client=client,k=1,workers=1,arms=('concept','concept-hybrid'))
            rows=[json.loads(line) for line in path.read_text().splitlines()]
        self.assertEqual([r['arm'] for r in rows],['concept','concept-hybrid'])
        self.assertEqual(client.requests[0][1],run_v4.v4_prompts.seed(0,'concept',0))
        self.assertEqual(rows[1]['assertions'],['assert f(0) == 0','assert f(100) == 100'])
        self.assertEqual(len(client.requests),3)

    def test_shared_oracle_is_spec_only_ten_per_task(self):
        t=task();t['put']+='\n# IMPLEMENTATION_ONLY_MARKER\n'
        jobs=list(comparison.oracle_jobs([dict(v11=t,retrieval={'secret':'TREATMENT_MARKER'})]))
        self.assertEqual(len(jobs),10)
        self.assertEqual(len({j['seed'] for j in jobs}),10)
        self.assertNotIn('IMPLEMENTATION_ONLY_MARKER',json.dumps(jobs))
        self.assertNotIn('TREATMENT_MARKER',json.dumps(jobs))

    def test_attempt_budget_and_duplicate_stop_without_network(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict('os.environ',{'CT_RETRIEVAL_BASE_URL':'https://fixture.ngrok-free.dev/v1'}):
            client=transport.Client(directory)
            client.reserve('first')
            with self.assertRaisesRegex(RuntimeError,'must_not_retry'):client.reserve('first')
            with patch.object(transport,'MAX_ATTEMPTS',1):
                with self.assertRaisesRegex(RuntimeError,'completion_cap'):client.reserve('second')

    def test_native_target_hit_draw_and_network_denial(self):
        t=task();t.update(concept_meta=[dict(kind='STMT',line=3,lines=[3],text='reach3')],placebo_meta=[])
        t['mined_valid_src']='def valid(x):\n    return x >= 0\n'
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            result=v4_runtime.isolated('classify',dict(task=t,shown=t['concept_meta'],candidates=[dict(input_repr='(2,)'),dict(input_repr='(-1,)')]),root/'classify')
            self.assertEqual(result['summary']['shown_hit_counts'],[1])
            self.assertEqual(result['summary']['valid'],1)
            draws=v4_runtime.isolated('draw',dict(task=t,code='def strategy():\n    return st.just((3,))\n',seed=1,n=1,cap=5),root/'draw')
            self.assertEqual(draws['candidates'],[dict(input_repr='(3,)')])
            script=root/'network.py';job=root/'job.json';output=root/'output.json';job.write_text('{}')
            script.write_text('import json,socket,sys\nfrom pathlib import Path\ntry:\n socket.create_connection(("127.0.0.1",9),timeout=1)\n status="allowed"\nexcept PermissionError:\n status="denied"\nPath(sys.argv[2]).write_text(json.dumps({"status":status}))\n')
            self.assertEqual(gen_inputs.sandbox(v4_runtime.interpreter(),script,job,output,5)['status'],'denied')

    def test_native_shared_oracle_requires_agreement_and_three_survivors(self):
        job=dict(entry='f',put='def f(x):\n return x',canon='def f(x):\n return x+1',
                 base='def check(candidate):\n assert candidate(0)==1',contract='def f(x):\n assert x>=0',
                 spec='def f(x):\n """Add one."""',dpp=[],tc=[],post=[],mutants=[],calls=['f(2)'],b1={},o0={},atol=0)
        with tempfile.TemporaryDirectory() as directory:
            for count in (2,3):
                result=v4_runtime.isolated('oracle',dict(job,ref=['def f(x):\n return x+1']*count),Path(directory)/str(count))
                self.assertEqual(result['calls']['f(2)']['ref']['emit'],count==3)
            mixed=['def f(x):\n return x+1']*2+['def f(x):\n return 1 if x==0 else 99']
            result=v4_runtime.isolated('oracle',dict(job,ref=mixed),Path(directory)/'disagree')
            self.assertFalse(result['calls']['f(2)']['ref']['emit'])

    def test_shared_preparation_through_native_facts_and_adapter(self):
        class PreparationClient:
            model=paths.CONFIG['model']
            def chat(self,messages,seed,**kwargs):
                instruction=messages[1]['content']
                if instruction.startswith('List every condition'):
                    text='[{"id":"P1","condition":"x is an integer"}]'
                elif instruction.startswith('For each candidate'):
                    text='[{"id":"P1","keep":true,"evidence":"integer x"}]'
                elif instruction.startswith('Write one Python predicate'):
                    text='def P1(x):\n    return isinstance(x,int)'
                else:
                    text='def strategy():\n    return st.tuples(st.integers(min_value=-10,max_value=10))'
                return dict(text=text,n_in=1,n_out=1,seconds=0,key=str(seed))
        public=dict(task_id='Fixture/999',entry_point='f',prompt='def f(x):\n    """Return the absolute value of integer x."""\n',
                    test='def check(candidate):\n    assert candidate(0)==0\n    assert candidate(1)==1\n')
        raw=dict(task=999,entry='f',base=public['test'],put=public['prompt']+'    if x >= 0:\n        return x\n    return 0\n',split='fixture',public=public)
        with tempfile.TemporaryDirectory() as directory, patch.object(comparison,'ROOT',Path(directory)):
            result=comparison.prepare_one(raw,PreparationClient())
        self.assertEqual(result['v11']['valid_sha256'],result['retrieval']['valid_sha256'])
        self.assertEqual(result['v11']['strategy_sha256'],result['retrieval']['strategy_sha256'])
        self.assertEqual(result['v11']['put'],result['retrieval']['put'])
        self.assertTrue(result['v11']['concept_meta'])
        self.assertEqual(result['retrieval']['retrieval_method'],'v2_compact_site_bound')


if __name__=='__main__':
    unittest.main()
