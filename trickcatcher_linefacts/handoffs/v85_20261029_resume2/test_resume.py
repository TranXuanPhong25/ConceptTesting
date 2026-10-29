"""Offline handoff invariants; never instantiate a model client."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import resume


class HandoffTests(unittest.TestCase):
    def test_snapshot_allows_ledger_append_but_rejects_history_change(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); (root/'snapshot').mkdir()
            ledger=root/'snapshot/attempts.jsonl'; ledger.write_bytes(b'old\n')
            (root/'checkpoint.tar.gz').write_bytes(b'archive')
            manifest=dict(archive_sha256=resume.sha(root/'checkpoint.tar.gz'),
                          files={'snapshot/attempts.jsonl':resume.sha(ledger)},
                          ledger={'path':'snapshot/attempts.jsonl','bytes':4})
            (root/'MANIFEST.json').write_text(json.dumps(manifest))
            with patch.object(resume,'HERE',root):
                ledger.write_bytes(b'old\nnew\n'); resume.unpack(root)
                ledger.write_bytes(b'bad\nnew\n')
                with self.assertRaisesRegex(ValueError,'checkpoint_changed'): resume.unpack(root)

    def test_saved_oracle_identity_and_no_duplicate_job(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            job=dict(task=1,sample=0,messages=[{'role':'user','content':'spec'}],seed=5)
            request=dict(messages=job['messages'],seed=5,model='qwen3.5-27b-awq',temperature=.8,top_p=.95,max_tokens=1024)
            key=hashlib.sha256(json.dumps(request,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
            call=root/'transport/calls'/key; call.mkdir(parents=True)
            response=dict(key=key,status='received')
            (call/'request.json').write_text(json.dumps({'body':request}))
            (call/'response.json').write_text(json.dumps(response))
            (root/'transport/attempts.jsonl').write_text(json.dumps({'key':key})+'\n')
            history=[{'response':{'unknown_completion_usage':i<4}} for i in range(18)]
            (root/'HISTORY.json').write_text(json.dumps(history))
            self.assertEqual(resume.check_ledger(root),(1,history))
            saved=root/'oracles/1/0.json'; saved.parent.mkdir(parents=True)
            saved.write_text(json.dumps(dict(task=1,sample=0,response=response)))
            other=dict(job,sample=1,seed=6)
            self.assertEqual(resume.missing_oracles(root,[job,other]),[other])
            with self.assertRaisesRegex(ValueError,'identity_mismatch'):
                resume.missing_oracles(root,[dict(job,seed=6)])
            (call/'response.json').unlink()
            with self.assertRaisesRegex(ValueError,'unresolved_attempt'):
                resume.check_ledger(root)

    def test_historical_unknowns_count_once(self):
        history=[dict(response=dict(unknown_completion_usage=i<4),duplicate=False) for i in range(5)]
        history += [dict(response=dict(usage={'total_tokens':10}),duplicate=True) for _ in range(13)]
        result=resume.cumulative_results(dict(completion_attempts=2030,unknown_completion_usage=0,usage={'total_tokens':100}),history)
        self.assertEqual(result['completion_attempts'],2048)
        self.assertEqual(result['unknown_completion_usage'],4)
        self.assertEqual(result['duplicate_received_attempts'],13)
        self.assertEqual(result['usage']['total_tokens'],230)
        with self.assertRaisesRegex(ValueError,'already_counted'): resume.cumulative_results(result,history)
        with self.assertRaisesRegex(ValueError,'cap_exceeded'):
            resume.cumulative_results(dict(completion_attempts=3501,unknown_completion_usage=0),history)


if __name__=='__main__': unittest.main()
