"""Regression checks for recovery, provenance, fallback and offline execution."""
import copy
import json
import unittest
from pathlib import Path
from .engine import parse_recovered, interleave, retrieve
from ..retrieval_v3.prompts import CODE_TO_CARD

class RetrievalTests(unittest.TestCase):
    def response(self):
        key = next(iter(CODE_TO_CARD))
        row = {'id':key,'line':1,'where':'site','how':'mechanism','what':'consequence'}
        return {'status':'received','parsed':{'selected':[row,copy.deepcopy(row)]}}

    def test_duplicate_recovery_without_mutation(self):
        response=self.response();before=copy.deepcopy(response)
        rows,error,recovered=parse_recovered(response,'x = 0')
        self.assertTrue(recovered)
        self.assertIsNone(error)
        self.assertEqual(len(rows),1)
        self.assertEqual(response,before)

    def test_duplicate_does_not_bypass_line_validation(self):
        response=self.response();response['parsed']['selected'][0]['line']=999
        rows,error,recovered=parse_recovered(response,'x = 0')
        self.assertEqual(rows,[])
        self.assertFalse(recovered)
        self.assertEqual(error,'invalid_source_line')

    def test_incomplete_json_remains_failure(self):
        rows,error,recovered=parse_recovered({'status':'received','parse_error':True},'x = 0')
        self.assertEqual(rows,[])
        self.assertFalse(recovered)

    def test_interleave_deduplicates_and_retains_binding(self):
        q=[{'concept_id':'a','line':7},{'concept_id':'b','line':8}]
        s=[{'concept_id':'a','line':1},{'concept_id':'c','line':2}]
        rows=interleave(q,s)
        self.assertEqual([r['concept_id'] for r in rows],['a','b','c'])
        self.assertEqual(rows[0]['line'],7)
        self.assertEqual(rows[-1]['origin'],'v2')

    def test_offline_api_matches_all_saved_rankings(self):
        root=Path(__file__).resolve().parents[1]
        out=root/'retrieval_v3/out/run_20261026'
        records=json.loads((root/'retrieval_v3/continuation_20261027/RANKING.json').read_text())['records']
        tasks={r['task_id']:r for r in json.loads((root/'retrieval_v2/evaluation/inputs.json').read_text())}
        for record in records:
            tid=record['task_id']
            raw=json.loads((out/'retrieved'/f"{tid.replace('/', '_')}.json").read_text())['response']
            actual=retrieve(tasks[tid]['code'],response=raw)
            expected=record['systems']['fusion']['selected']
            self.assertEqual([(r['concept']['id'],r['instantiated']['line']) for r in actual['results']],[(r['concept_id'],r['line']) for r in expected],tid)

if __name__=='__main__':
    unittest.main()
