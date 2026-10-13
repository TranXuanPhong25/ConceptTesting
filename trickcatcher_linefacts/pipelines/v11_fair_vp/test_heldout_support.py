"""CPU regression checks for baseline scoring and empty-task reference collection."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from . import evaluate, gen_inputs, heldout_support, paths, scorer


class HeldoutAdapters(unittest.TestCase):
    def test_twenty_exported_assertions_are_scored_with_clean_worker_env(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            put='import os\nclass Solution:\n    def f(self,x):\n        assert "QWEN_BASE_URL" not in os.environ\n        return x\ndef f(x):\n    return Solution().f(x)\n'
            task=dict(task=9999,entry='f',put=put,base='def check(candidate):\n    assert candidate(0)==0\n',
                      split='heldout',concept_meta=[])
            (root/'tasks.json').write_text(json.dumps(dict(tasks=[task])))
            assertions=[f'assert f({i}) == {i}' for i in range(20)]
            row=dict(task=9999,arm='symprompt',sample=0,run_id='cpu-fixture',split='heldout',
                     assertions=assertions,text='```python\n'+'\n'.join(assertions)+'\n```')
            (root/'gen.jsonl').write_text(json.dumps(row)+'\n')
            (root/'plus.jsonl').write_text(json.dumps(dict(task_id='HumanEval/9999',prompt='def f(x):\n',
                                                      canonical_solution='    return x\n'))+'\n')
            contracts={9999:dict(contract_src='def f(x):\n    assert isinstance(x,int)\n',entry='f')}
            with patch.object(evaluate,'HEP',root/'plus.jsonl'), \
                 patch.object(gen_inputs,'load_contracts',return_value=contracts), \
                 patch.object(scorer,'task_atols',return_value={9999:0.0}), \
                 patch.dict(paths.CONFIG,caps=True,shared_scorer=True), \
                 patch.dict('os.environ',{'QWEN_BASE_URL':'private-test-sentinel'}):
                evaluate.evaluate(root/'tasks.json',root/'gen.jsonl',root/'eval.jsonl')
            [scored]=[json.loads(l) for l in (root/'eval.jsonl').read_text().splitlines()]
            self.assertEqual(len(scored['asserts']),20)
            self.assertTrue(all(a['put']=='ok' and a['canon']=='ok' for a in scored['asserts']))

    def test_empty_assertion_tasks_remain_in_reference_collection(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);oracle=root/'oracle';oracle.mkdir()
            tasks=[dict(task=i,entry='f',put='def f(x): return x',base='def check(candidate): pass',split='heldout') for i in (1,2)]
            (root/'tasks.json').write_text(json.dumps(dict(tasks=tasks)))
            rows=[dict(task=i,arm='plain',sample=0,split='heldout',asserts=[] if i==2 else [dict(src='assert f(1)==1')]) for i in (1,2)]
            (root/'eval.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
            heldout_support.collect(root,oracle)
            self.assertEqual(json.loads((oracle/'calls.json').read_text()),{'1':['f(1)'],'2':[]})

if __name__=='__main__':unittest.main()
