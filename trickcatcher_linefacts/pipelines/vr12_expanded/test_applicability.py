import unittest
from .applicability import assess,pick_valid
from .semantic_gate import bind,Probe
from .test_semantic_gate import fixture


class ApplicabilityTests(unittest.TestCase):
    def binding(self,source):
        task,fact=fixture(source,'py.literal-classification-domain','c not in vowels')
        return bind(task,fact)

    def test_unchanged_literal_class_refutes_hypothesis_not_function(self):
        source='def f(c):\n """Remove vowels."""\n vowels="aeiouAEIOU"\n return c not in vowels'
        binding=self.binding(source)
        self.assertEqual(assess(source,'f',binding)['status'],'refuted_for_supported_values')
        self.assertIs(Probe(source,'f',[binding]).run(('a',))[0][0]['state'],False)

    def test_rebinding_controlflow_dynamic_and_missing_member_remain_unknown(self):
        cases=[
            'vowels="aeiouAEIOU"\n vowels="a"',
            'if c:\n  vowels="aeiouAEIOU"',
            'vowels="aeiouAEIOU"\n exec("vowels=\'a\'")',
            'vowels="aeouAEIOU"',
            'vowels="aeiouAEIOU"\n def change():\n  nonlocal vowels\n  vowels="a"',
        ]
        for body in cases:
            source='def f(c):\n """Remove vowels."""\n '+body+'\n return c not in vowels'
            self.assertEqual(assess(source,'f',self.binding(source))['status'],'unknown',source)

    def test_observed_false_does_not_refute_incomplete_table(self):
        source='def f(c):\n """Remove vowels."""\n vowels="aeouAEIOU"\n return c not in vowels'
        b=self.binding(source)
        self.assertIs(Probe(source,'f',[b]).run(('a',))[0][0]['state'],False)
        self.assertIs(Probe(source,'f',[b]).run(('i',))[0][0]['state'],True)
        self.assertEqual(assess(source,'f',b)['status'],'unknown')

    def test_retains_novel_nonhits_and_excludes_invalid_seen_duplicate(self):
        def row(x,hit=False,valid=True):return dict(call=f'f({x})',input_repr=str((x,)),shown_hits=[hit],valid=valid)
        rows=[row(0),row(1,True),row(2),row(2),row(3,False,False),row(4)]
        picked=pick_valid(rows,['assert f(0)==0'],'f',[row(4)],11,True)
        self.assertEqual({r['call'] for r in picked},{'f(1)','f(2)'})
        self.assertEqual(len(pick_valid([row(2),row(4)],[],'f',[],11,True)),2)



class ReplayTests(unittest.TestCase):
    def test_expansion_uses_fresh_strategies_even_if_record_has_old_pools(self):
        import json,tempfile
        from pathlib import Path
        from unittest.mock import patch
        from . import diagnostic as d,run_v4,v4_runtime
        from .test_diagnostic import record,FakeClient
        r=record();raw="def strategy():\n    return st.just(('ABC',))"
        generated=dict(nonliteral=0,wrong_arity=0,errors=[],candidates=[dict(input_repr="('ABC',)")])
        pools=[dict(strategy_src=run_v4.v4_strategies.checked(raw),generated=generated,
                    response_key=str(run_v4.v4_prompts.seed(0,'concept-hybrid',0,1,i,0))) for i in range(2)]
        r['pools']=dict(semantic=pools,generic=pools)
        with tempfile.TemporaryDirectory() as tmp,patch.object(run_v4,'safe_path',side_effect=Path),patch.object(run_v4.v4_strategies,'draws',return_value=generated) as draws:
            out=run_v4.run([d.make_task(r,'retain')],Path(tmp),v4_runtime.interpreter(),client=FakeClient(),k=1,workers=1,arms=('concept','concept-hybrid'))
            row=json.loads(out.read_text().splitlines()[-1])
            self.assertEqual([a['generated'] for a in row['generator_attempts']],[generated,generated])
            self.assertEqual(len(row['selected_inputs']),1)
            self.assertEqual(draws.call_count,2)

    def test_only_exact_cached_strategies_and_authorized_expected_calls(self):
        from .replay import Client,key
        class Live:
            model='qwen3.5-27b-awq'
            def __init__(self):self.calls=0
            def chat(self,*args,**kwargs):self.calls+=1;return {'text':'fresh expected'}
        live=Live();messages=[dict(role='user',content='fixture')]
        body=dict(model=live.model,messages=messages,seed=1,temperature=0,top_p=1,
                  max_tokens=4096,stream=False,chat_template_kwargs={'enable_thinking':False})
        saved={'text':'saved strategy'};client=Client(live,{key(body):saved},True)
        self.assertEqual(client.chat(messages,1,temperature=0,top_p=1,max_tokens=4096),saved)
        with self.assertRaisesRegex(RuntimeError,'unregistered'):client.chat(messages,2,max_tokens=4096)
        with self.assertRaisesRegex(RuntimeError,'unregistered'):Client(live,{},False).chat(messages,1)
        self.assertEqual(live.calls,0)
        self.assertEqual(client.chat(messages,1)['text'],'fresh expected')
        self.assertEqual(live.calls,1)

    def test_native_refutation_and_retention_fix_hard_filter(self):
        import json,tempfile
        from copy import deepcopy
        from pathlib import Path
        from unittest.mock import patch
        from . import diagnostic as d,run_v4,v4_runtime
        from .test_diagnostic import record,FakeClient
        r=record();t=r['task']
        t['put']='def f(c):\n """Remove vowels, preserving every other character."""\n vowels="aeiouAEIOU"\n return "".join(char for char in c if char not in vowels)'
        _,fact=fixture(t['put'],'py.literal-classification-domain','char not in vowels')
        fact.update(kind='STMT',line=4,lines=[4],text='Visit classification',card={'title':'Character-class membership'})
        t.update(concept_meta=[fact],concept_facts=[fact['text']]);r['binding']=bind(t,fact)
        r['round1']['text']="assert f('a') == ''"
        class Writer(FakeClient):
            def chat(self,messages,seed,**kwargs):
                self.requests.append((deepcopy(messages),seed))
                value="def strategy():\n return st.just(('w u',))" if 'Hypothesis' in messages[0]['content'] else "assert f('w u') == 'w '"
                return dict(text=value,key=str(seed),n_in=1,n_out=1,seconds=0)
        with tempfile.TemporaryDirectory() as tmp,patch.object(run_v4,'safe_path',side_effect=Path):
            for mode in ('strict','retain','applicable'):
                client=Writer();out=run_v4.run([d.make_task(r,mode)],Path(tmp)/mode,v4_runtime.interpreter(),client=client,k=1,workers=1,arms=('concept','concept-hybrid'))
                row=json.loads(out.read_text().splitlines()[-1])
                self.assertEqual(len(row['selected_inputs']),0 if mode=='strict' else 1)
                self.assertEqual(row['refuted_target_skipped'],mode=='applicable')
                self.assertEqual('\nFACT:\n' in client.requests[0][0][-1]['content'],mode!='applicable')
                self.assertEqual(row['round1_assertions'],["assert f('a') == ''"])
                if mode!='strict':self.assertIn("assert f('w u') == 'w '",row['assertions'])


if __name__=='__main__':unittest.main()
