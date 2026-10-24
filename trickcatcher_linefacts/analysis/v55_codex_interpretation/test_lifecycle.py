"""Engineering gates only: no model calls, PUTs, hidden tests or outcomes."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from trickcatcher_linefacts.analysis.v55_codex_interpretation import experiment as X


class Lifecycle(unittest.TestCase):
    def test_timeout_leaves_unresolved_attempt(self):
        with tempfile.TemporaryDirectory() as temp:
            call = Path(temp)/'call'
            with patch.object(X.subprocess, 'run', side_effect=subprocess.TimeoutExpired('codex', 900)):
                with self.assertRaises(subprocess.TimeoutExpired):
                    X.isolated('synthetic transport-only text', call)
            self.assertEqual(json.loads((call/'attempt.json').read_text())['status'], 'unresolved')
            self.assertFalse(json.loads((call/'failure.json').read_text())['retry_allowed'])
            # The same call cannot be launched a second time.
            with self.assertRaises(FileExistsError):
                X.isolated('synthetic transport-only text', call)

    def test_isolated_quota_wins_over_stale_host(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'quota_observations').mkdir()
            fresh = dict(timestamp='2026-10-24T12:00:00Z', remaining_percent=14, resets_at=123)
            (root/'quota_observations/call.json').write_text(json.dumps(fresh))
            with patch.object(X, 'OUT', root), patch.object(X, 'latest_primary', return_value=dict(
                    timestamp='2026-10-24T10:00:00Z', remaining_percent=99, resets_at=123)):
                self.assertEqual(X.quota(), fresh)

    def test_manifest_is_paired_and_k_separate_calls(self):
        jobs = json.loads((X.OUT/'manifest.json').read_text())
        self.assertEqual(jobs, json.loads((X.HERE/'MANIFEST.json').read_text()))
        self.assertEqual(len(jobs), 33)
        by = {}
        for job in jobs:
            prompt = (X.OUT/'prompts'/(job['call']+'.txt')).read_text()
            self.assertEqual(X.digest(prompt), job['prompt_sha256'])
            for pid in job['problems']:
                by.setdefault((pid, job['kind']), []).append(job['call'])
        problems = {pid for pid, kind in by}
        self.assertEqual(len(problems), 24)
        for pid in problems:
            for kind in (*X.ARMS, 'plain', 'open'):
                calls = by[pid, kind]
                self.assertEqual(len(set(calls)), 3 if kind in X.ARMS else 1)
        self.assertFalse((X.OUT/'score.json').exists())

    def test_changed_source_fails_review_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'experiment.py').write_text('changed')
            (root/'REVIEW_APPROVED.json').write_text(json.dumps({'sha256': {'experiment.py': 'old'}}))
            with patch.object(X, 'HERE', root):
                with self.assertRaisesRegex(RuntimeError, 'reviewed file changed'):
                    X.review_gate()

    def test_syntax_and_entrypoint_gate(self):
        with self.assertRaises(SyntaxError):
            X.validate_answer('```python\ndef inputs(:\n pass\n```', 'plain', 'inputs')
        with self.assertRaisesRegex(ValueError, 'entrypoint'):
            X.validate_answer('```python\ndef other():\n return []\n```', 'plain', 'inputs')
        X.validate_answer('```python\ndef inputs():\n return []\n```', 'plain', 'inputs')


if __name__ == '__main__':
    unittest.main()
