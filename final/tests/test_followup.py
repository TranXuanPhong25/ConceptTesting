"""Dependency-gated followup tests: synthetic records, zero model/native calls."""
import asyncio
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

try:
    from prefect.states import Completed, Running, Failed
    from final.src.orchestration import followup
except ImportError:
    raise unittest.SkipTest('Uses the isolated orchestration environment')


class FollowupTests(unittest.TestCase):
    def valid_output(self, output):
        output.mkdir(parents=True)
        (output/'status.json').write_text(json.dumps({'state':'complete'}))
        (output/'result_digest.json').write_text(json.dumps({'read_only_replay_matches':True,'source_hashes_verified':True}))
        (output/'progress.json').write_text(json.dumps({'total_tasks':164,'evaluated_tasks':164}))

    def test_valid_ids_require_unique_distinct_predecessors(self):
        own=uuid4();other=uuid4()
        self.assertEqual(followup.validate_predecessor_ids([str(other)],own),[other])
        for values in [[],[str(other),str(other)],[str(own)]]:
            with self.assertRaises(ValueError):followup.validate_predecessor_ids(values,own)

    def test_completed_predecessor_requires_real_final_checks_and_evaluation(self):
        with TemporaryDirectory() as folder:
            output=Path(folder)/'run';self.valid_output(output)
            self.assertEqual(followup.validate_completed_predecessor(output)['evaluated_tasks'],164)
            for file,value in [('status.json',{'state':'running'}),('progress.json',{'total_tasks':164,'evaluated_tasks':163}),
                               ('result_digest.json',{'read_only_replay_matches':False,'source_hashes_verified':True})]:
                before=(output/file).read_text();(output/file).write_text(json.dumps(value))
                with self.assertRaises(ValueError):followup.validate_completed_predecessor(output)
                (output/file).write_text(before)

    def test_wait_does_not_release_on_one_complete_predecessor(self):
        with TemporaryDirectory() as folder:
            directory=Path(folder);ids=[uuid4(),uuid4()]
            client=SimpleNamespace(update_artifact=AsyncMock())
            ready={'ready':True};not_ready={'ready':False}
            checks=AsyncMock(side_effect=[ready,not_ready,ready,ready])
            with patch.object(followup,'predecessor_status',checks),patch.object(followup.asyncio,'sleep',new_callable=AsyncMock) as sleep:
                result=asyncio.run(followup.wait_for_predecessors(client,ids,directory=directory,
                    budget={'logical_call_cap':24,'config':{'inputs_per_task':20,'completion_tokens':4096}},progress_artifact_id=uuid4()))
                self.assertTrue(all(row['ready'] for row in result));sleep.assert_awaited_once_with(30)
            self.assertEqual(json.loads((directory/'followup_status.json').read_text())['model_calls'],0)

    def test_scheduled_deadline_keeps_ready_predecessor_waiting(self):
        with TemporaryDirectory() as folder:
            directory = Path(folder)
            client = SimpleNamespace(update_artifact=AsyncMock())
            checks = AsyncMock(return_value={'ready': True})
            deadline = '2026-11-09T20:00:00+00:00'
            deadline_epoch = followup.scheduled_start_epoch(deadline)
            with patch.object(followup, 'predecessor_status', checks), \
                 patch.object(followup.time, 'time', side_effect=[deadline_epoch-1, deadline_epoch-1,
                                                                 deadline_epoch, deadline_epoch]), \
                 patch.object(followup.asyncio, 'sleep', new_callable=AsyncMock) as sleep:
                asyncio.run(followup.wait_for_predecessors(client, [uuid4()], directory=directory,
                    budget={'logical_call_cap': 314, 'config': {'inputs_per_task': 20, 'completion_tokens': 4096}},
                    progress_artifact_id=uuid4(), not_before_utc=deadline))
            sleep.assert_awaited_once_with(30)
            status = json.loads((directory/'followup_status.json').read_text())
            self.assertEqual(status['state'], 'ready')
            self.assertEqual(status['model_calls'], 0)

    def test_deadline_requires_timezone(self):
        with self.assertRaisesRegex(ValueError, 'timezone'):
            followup.scheduled_start_epoch('2026-11-09T20:00:00')
        self.assertEqual(followup.scheduled_start_epoch('2026-11-09T20:00:00Z'),
                         followup.scheduled_start_epoch('2026-11-10T03:00:00+07:00'))

    def test_failed_predecessor_blocks_without_workload(self):
        with TemporaryDirectory() as folder:
            client=SimpleNamespace(update_artifact=AsyncMock())
            with patch.object(followup,'predecessor_status',new_callable=AsyncMock,side_effect=RuntimeError('predecessor failed')):
                with self.assertRaisesRegex(RuntimeError,'failed'):
                    asyncio.run(followup.wait_for_predecessors(client,[uuid4()],directory=Path(folder),
                        budget={'logical_call_cap':24,'config':{'inputs_per_task':20,'completion_tokens':4096}},progress_artifact_id=uuid4()))
            self.assertEqual(json.loads((Path(folder)/'followup_status.json').read_text())['state'],'blocked')

    def test_completed_state_without_final_artifacts_is_rejected(self):
        client=SimpleNamespace(read_flow_run=AsyncMock(return_value=SimpleNamespace(state=Completed())))
        with TemporaryDirectory() as folder,patch.object(followup,'OUT',Path(folder)):
            with self.assertRaisesRegex(ValueError,'saved output'):
                asyncio.run(followup.predecessor_status(client,uuid4()))

    def test_failed_record_does_not_get_treated_as_ready(self):
        client=SimpleNamespace(read_flow_run=AsyncMock(return_value=SimpleNamespace(state=Failed())))
        with self.assertRaisesRegex(RuntimeError,'chưa chạy workload'):
            asyncio.run(followup.predecessor_status(client,uuid4()))


if __name__=='__main__':unittest.main()
