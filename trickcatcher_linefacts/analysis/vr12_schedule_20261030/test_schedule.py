"""Automation guard checks; no experiment worker or network is invoked."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('vr12_schedule', Path(__file__).with_name('launch_once.py'))
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class ScheduleTests(unittest.TestCase):
    def exercise(self, condition=None, check_rc=0):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            here, out = root / 'schedule', root / 'out'
            here.mkdir()
            out.mkdir()
            if condition == 'attempted':
                (here / 'LAUNCH_ATTEMPTED.json').write_text('{}')
            if condition == 'complete':
                (out / 'COMPLETE.json').write_text('{}')
            if condition == 'ledger':
                (out / 'transport').mkdir()
                (out / 'transport/attempts.jsonl').write_text('{"key":"old"}\n')
            (out / 'STATUS.json').write_text('{"stage":"blocked"}')
            fake = patch.object(M.subprocess, 'run', side_effect=[SimpleNamespace(returncode=check_rc), SimpleNamespace(returncode=0)])
            with patch.object(M, 'HERE', here), patch.object(M, 'OUT', out), fake as run:
                endpoint = {} if condition == 'missing_endpoint' else {'CT_RETRIEVAL_BASE_URL': 'not-used-by-mocked-subprocess'}
                with patch.dict(M.os.environ, endpoint, clear=True):
                    M.main()
                events = (here / 'events.jsonl').read_text()
                backup = out / 'history/pre_schedule_20261030/STATUS.json'
                return run.call_count, events, backup.read_text() if backup.exists() else None

    def test_attempted_guard(self):
        count, events, _ = self.exercise('attempted')
        self.assertEqual(count, 0)
        self.assertIn('skip_already_attempted', events)

    def test_complete_guard(self):
        count, events, _ = self.exercise('complete')
        self.assertEqual(count, 0)
        self.assertIn('skip_experiment_complete', events)

    def test_ledger_guard(self):
        count, events, _ = self.exercise('ledger')
        self.assertEqual(count, 0)
        self.assertIn('blocked_existing_completion_attempts', events)

    def test_missing_endpoint_guard(self):
        count, events, _ = self.exercise('missing_endpoint')
        self.assertEqual(count, 0)
        self.assertIn('blocked_missing_endpoint_environment', events)

    def test_failed_check_does_not_launch(self):
        count, events, _ = self.exercise(check_rc=1)
        self.assertEqual(count, 1)
        self.assertIn('blocked_frozen_check', events)

    def test_success_path_keeps_initial_receipt(self):
        count, events, backup = self.exercise()
        self.assertEqual(count, 2)
        self.assertEqual(backup, '{"stage":"blocked"}')
        self.assertIn('controller_exited', events)


if __name__ == '__main__':
    unittest.main()
