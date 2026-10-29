import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from . import diagnostic as d,run_v4,v4_runtime
from .semantic_gate import bind
from .test_fair import task


def record():
    t=task();t['put']='def f(x):\n    """Return the original string unchanged."""\n    return x.lower()\n'
    valid='def valid(x):\n    return isinstance(x,str)\n'
    t.update(mined_valid_src=valid,valid_sha256=run_v4.preconditions.sha(valid),
             strategy_src='def strategy():\n    return st.tuples(st.text())\n')
    t['strategy_sha256']=run_v4.preconditions.sha(t['strategy_src'])
    f=dict(kind='STMT',line=3,lines=[3],text='Execute line3',card_id='py.text-normalization-contract',
           card={'title':'Normalization changes required text'},retrieval_evidence=dict(line=3,end_line=3,expression='x.lower()'))
    t.update(concept_meta=[f],concept_facts=[f['text']],placebo_meta=[],placebo_facts=[])
    return dict(task=t,target_index=0,binding=bind(t,f),round1=dict(text="assert f('abc') == 'abc'",key='inherited',n_in=1,n_out=1,seconds=0))


class FakeClient:
    model='qwen3.5-27b-awq'
    def __init__(self):self.requests=[]
    def chat(self,messages,seed,**kwargs):
        self.requests.append((messages,seed))
        text="def strategy():\n    return st.just(('ABC',))" if 'Hypothesis' in messages[0]['content'] else "assert f('ABC') == 'ABC'"
        return dict(text=text,key=str(seed),n_in=1,n_out=1,seconds=0)


class DiagnosticTests(unittest.TestCase):
    def test_external_fairness_overrides_rejected(self):
        with patch.dict(os.environ,{'LINEFACTS_FAIR_FLAGS':'{}'}):
            with self.assertRaisesRegex(SystemExit,'rejects_external'):d.main()

    def test_native_semantic_hits_differ_from_line_hits(self):
        r=record();candidates=[dict(input_repr="('abc',)"),dict(input_repr="('ABC',)")]
        with tempfile.TemporaryDirectory() as folder:
            for mode,expected in [('old',[True,True]),('semantic',[False,True])]:
                t=d.make_task(r,mode)
                got=v4_runtime.isolated('classify',dict(task=t,shown=t['concept_meta'],candidates=candidates),Path(folder)/mode)
                self.assertEqual([x['shown_hits'][0] for x in got['records']],expected)
                self.assertEqual([x['semantic_measurements'][0]['state'] for x in got['records']],[False,True])
                self.assertTrue(all(x['semantic_line_reached']==[True] for x in got['records']))

    def test_fixed_strategy_slots_shared_round1_and_strict_injection_native(self):
        r=record();before=json.dumps(r,sort_keys=True)
        with tempfile.TemporaryDirectory() as folder,patch.object(run_v4,'safe_path',side_effect=Path):
            for mode in d.MODES:
                client=FakeClient();t=d.make_task(r,mode)
                output=run_v4.run([t],Path(folder)/mode,v4_runtime.interpreter(),client=client,k=1,workers=1,arms=('concept','concept-hybrid'))
                final=json.loads(output.read_text().splitlines()[-1])
                self.assertEqual(final['round2_strategy_requests'],2)
                self.assertEqual(len(client.requests),3)
                self.assertEqual(final['llm_calls'],4)
                self.assertEqual(final['calls'][0]['key'],'inherited')
                self.assertEqual(final['assertions'],["assert f('abc') == 'abc'","assert f('ABC') == 'ABC'"])
                targeted='\nFACT:\n' in client.requests[0][0][-1]['content']
                self.assertEqual(targeted,mode!='generic')
        self.assertEqual(json.dumps(r,sort_keys=True),before)

    def test_failed_or_unresolved_receipt_blocks_resume(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(d,'ROOT',Path(folder)):
            (Path(folder)/'transport').mkdir();(Path(folder)/'transport/attempts.jsonl').write_text('{"key":"x"}\n')
            with self.assertRaisesRegex(ValueError,'no_automatic_retry'):d.ledger()

    def test_final_scorer_native_with_saved_ten_reference_programs(self):
        from .diagnostic_score import score
        from .llm_client import atomic_json
        r=record()
        with tempfile.TemporaryDirectory() as folder,patch.object(run_v4,'safe_path',side_effect=Path):
            root=Path(folder);assets=root/'assets';assets.mkdir()
            atomic_json(assets/'grading_references.json',[dict(task_id='HumanEval/0',prompt='def f(x):\n',canonical_solution='    return x\n',contract='    assert isinstance(x,str)\n')])
            atomic_json(assets/'refs.json',{'0':[dict(response=dict(text='def f(x):\n return x')) for _ in range(10)]})
            atomic_json(assets/'INHERITED.json',dict(synthetic_fixture=True))
            for mode in d.MODES:
                run_v4.run([d.make_task(r,mode)],root/'generation'/mode/'0',v4_runtime.interpreter(),client=FakeClient(),k=1,workers=1,arms=('concept','concept-hybrid'))
            files={str(p.relative_to(root)):d.sha(p) for p in (root/'generation').rglob('*.json')}
            atomic_json(root/'GENERATION_FREEZE.json',dict(files=files))
            with patch.object(d,'ROOT',root),patch.object(d,'HERE',root),patch.object(d,'verify'):
                score([r])
            result=json.loads((root/'RESULTS.json').read_text())
            self.assertTrue((root/'COMPLETE.json').exists())
            for mode in d.MODES:
                self.assertEqual(result['results']['ref']['arms'][mode]['confirmed_tasks'],[0])
                self.assertEqual(result['results']['ref']['arms'][mode]['false_alarm_tasks'],[])
            self.assertEqual(result['mechanism']['applicable']['0']['novel_semantic_inputs'],1)
            self.assertEqual(result['logical_round2_calls_including_replay'],12)
            self.assertEqual(result['inherited_unknown_usage'],11)
            scored=json.loads((root/'scored/0.json').read_text())
            row=next(x for x in scored['rows'] if x['arm']=='applicable')
            self.assertEqual([x['hits'][0] for x in row['asserts']],[False,True])


if __name__=='__main__':unittest.main()
