import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from ..v85_retrievalhybrid import transport
from ..v85_contextfit.transport import Client
from .resume import record_cumulative_costs


class ResumeAccountingTests(unittest.TestCase):
    def test_both_historical_failures_remain_unknown_and_count_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = dict(completion_attempts=600,unknown_completion_usage=0,usage={'total_tokens':1234})
            (root/'RESULTS.json').write_text(json.dumps(original))
            (root/'STATUS.json').write_text(json.dumps({'stage':'complete'}))
            record_cumulative_costs(root)
            result = json.loads((root/'RESULTS.json').read_text())
            self.assertEqual(result['completion_attempts'],602)
            self.assertEqual(result['completion_attempts_current_ledger'],600)
            self.assertEqual(result['unknown_completion_usage'],2)
            self.assertEqual(result['usage'],original['usage'])
            self.assertEqual(json.loads((root/'COMPLETE.json').read_text())['unknown_completion_usage'],2)
            with self.assertRaisesRegex(ValueError,'already_counted'):
                record_cumulative_costs(root)

    def test_attempt_limit_includes_both_prior_failures(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict('os.environ',{'CT_RETRIEVAL_BASE_URL':'https://fixture.ngrok-free.dev/v1'}):
            client = Client(directory)
            (client.root/'attempts.jsonl').write_text(''.join(json.dumps({'key':str(i)})+'\n' for i in range(3500)))
            with patch.object(transport,'MAX_ATTEMPTS',3501):
                client.reserve('last_permitted')
                with self.assertRaisesRegex(RuntimeError,'completion_cap'):
                    client.reserve('would_exceed_cumulative3503')

    def test_over_budget_cost_report_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            before = json.dumps(dict(completion_attempts=3503,unknown_completion_usage=0))
            (root/'RESULTS.json').write_text(before)
            with self.assertRaisesRegex(ValueError,'cumulative_attempt_cap'):
                record_cumulative_costs(root)
            self.assertEqual((root/'RESULTS.json').read_text(),before)
