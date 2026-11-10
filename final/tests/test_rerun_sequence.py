"""Offline public-packet pinning and evaluation-phase V2 release fixtures."""
import asyncio
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

try:
    from prefect.states import Running, Completed, Failed
    from final.src.orchestration import rerun
except ImportError:
    raise unittest.SkipTest('Uses isolated orchestration Python')

from final.src.runtime.artifacts import digest


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value))


class RerunSequenceTests(unittest.TestCase):
    def source_fixture(self,root):
        source=root/'source';runtime=source/'runtime';runtime.mkdir(parents=True)
        (runtime/'original.py').write_text('# original frozen source\n')
        (runtime/'cohort.json').write_text('{"original":"cohort"}')
        config=rerun.normalize({'arms':['direct','soft_bva'],'completion_tokens':2048,'timeout_seconds':8})
        save(source/'config_snapshot.json',config)
        save(source/'status.json',{'state':'complete'})
        save(source/'result_digest.json',{'read_only_replay_matches':True,'source_hashes_verified':True})
        save(source/'progress.json',{'total_tasks':2,'generated_tasks':2,'evaluated_tasks':2})
        save(source/'preview.json',{'selected_task_numbers':[0,1],'cohort_sha256':'cohort'})
        save(source/'launch_plan.json',{'runtime':str(runtime),'cohort':str(runtime/'cohort.json')})
        for n in [0,1]:
            packet={'task_id':f'HumanEval/{n}','common':f'public specification and PUT {n}','visible_put_ids':[4],
                    'prompt_tokens':{'direct':12,'soft_bva':20}}
            save(source/f'tasks/{n}/packet.json',packet)
            request={'messages':[{'role':'system','content':'sharedsystem'}, {'role':'user','content':packet['common']+'\n'}],
                     'max_tokens':2048,'temperature':config['temperature'],'seed':config['input_seed']+n}
            save(source/f'tasks/{n}/calls/direct/request.json',request)
            save(source/f'tasks/{n}/calls/direct/response.json',{'secret_from_generation':'not copied'})
            save(source/f'tasks/{n}/inputs.json',{'not':'copied'})
            save(source/f'tasks/{n}/oracle_valid.json',{'not':'copied'})
        return source

    def prepared_fixture(self,root,source):
        output=root/'target';runtime=output/'runtime';runtime.mkdir(parents=True)
        (runtime/'fresh.py').write_text('# new worktree source should not execute\n')
        config=rerun.baseline_configuration(source)
        save(output/'config_snapshot.json',config)
        save(output/'preview.json',{'selected_task_numbers':[0,1],'cohort_sha256':'cohort'})
        save(output/'launch_plan.json',{'runtime':str(runtime),'cohort':str(runtime/'cohort.json')})
        save(output/'source_snapshot.json',{'sources':{str(runtime/'fresh.py'):'stale'},'archive':{}})
        return output

    def test_baseline_changes_only_selected_arm_preserving_direct_cap(self):
        with TemporaryDirectory() as folder:
            source=self.source_fixture(Path(folder));original=json.loads((source/'config_snapshot.json').read_text())
            actual=rerun.baseline_configuration(source)
            self.assertEqual(actual,{**original,'arms':['plain']})
            self.assertEqual(actual['completion_tokens'],2048)

    def test_packets_and_runtime_exactly_pinned_without_generation_or_oracle(self):
        with TemporaryDirectory() as folder:
            root=Path(folder);source=self.source_fixture(root);output=self.prepared_fixture(root,source)
            before={str(p.relative_to(source)):p.read_bytes() for p in source.rglob('*') if p.is_file()}
            receipt=rerun.pin_baseline_source(source,output)
            self.assertEqual(receipt['copied_packets'],2)
            self.assertFalse((output/'runtime/fresh.py').exists())
            self.assertEqual((output/'runtime/original.py').read_bytes(),(source/'runtime/original.py').read_bytes())
            for n in [0,1]:
                self.assertEqual((output/f'tasks/{n}/packet.json').read_bytes(),(source/f'tasks/{n}/packet.json').read_bytes())
            self.assertFalse(list(output.glob('tasks/*/calls/*/response.json')))
            self.assertFalse(list(output.glob('tasks/*/inputs.json')))
            self.assertFalse(list(output.glob('tasks/*/oracle_valid.json')))
            snapshot=json.loads((output/'source_snapshot.json').read_text())
            for name,expected in snapshot['sources'].items():self.assertEqual(rerun.checksum(Path(name)),expected)
            self.assertEqual(before,{str(p.relative_to(source)):p.read_bytes() for p in source.rglob('*') if p.is_file()})

    def test_changed_direct_request_is_rejected_before_copy(self):
        with TemporaryDirectory() as folder:
            root=Path(folder);source=self.source_fixture(root);output=self.prepared_fixture(root,source)
            p=source/'tasks/0/calls/direct/request.json';record=json.loads(p.read_text());record['messages'][1]['content']+='extra guidance';save(p,record)
            with self.assertRaisesRegex(ValueError,'unmodified shared packet'):rerun.pin_baseline_source(source,output)
            self.assertTrue((output/'runtime/fresh.py').exists())

    def test_invalid_cohort_or_config_does_not_replace_fresh_runtime(self):
        with TemporaryDirectory() as folder:
            root=Path(folder);source=self.source_fixture(root);output=self.prepared_fixture(root,source)
            record=json.loads((output/'config_snapshot.json').read_text());record['completion_tokens']=4096;save(output/'config_snapshot.json',record)
            with self.assertRaisesRegex(ValueError,'differ only'):rerun.pin_baseline_source(source,output)
            self.assertTrue((output/'runtime/fresh.py').exists())

    def generation_output(self,root):
        output=root/'baseline';output.mkdir()
        save(output/'preview.json',{'selected_task_numbers':[0,1],'cohort_sha256':'cohort'})
        hashes={}
        for n in [0,1]:
            batch={'task_id':f'HumanEval/{n}','arms':{'plain':{'inputs':[]}}};save(output/f'tasks/{n}/inputs.json',batch)
            hashes[f'HumanEval/{n}']=digest(batch)
        save(output/'generation_frozen.json',{'cohort_sha256':'cohort','inputs':hashes,'inputs_sha256':digest(hashes)})
        save(output/'progress.json',{'generated_tasks':2,'evaluated_tasks':0,'total_tasks':2})
        return output

    def test_v2_waits_during_generation_then_releases_only_after_evaluation_begins(self):
        with TemporaryDirectory() as folder:
            output=self.generation_output(Path(folder));client=SimpleNamespace(read_flow_run=AsyncMock(return_value=SimpleNamespace(state=Running())))
            save(output/'status.json',{'state':'running','phase':'generation'})
            with patch.object(rerun,'predecessor_output_directory',return_value=output):
                self.assertFalse(asyncio.run(rerun.baseline_evaluation_readiness(client,uuid4()))['ready'])
                save(output/'status.json',{'state':'waiting_native_lock'})
                self.assertFalse(asyncio.run(rerun.baseline_evaluation_readiness(client,uuid4()))['ready'])
                save(output/'status.json',{'state':'running','phase':'evaluation'})
                self.assertTrue(asyncio.run(rerun.baseline_evaluation_readiness(client,uuid4()))['ready'])

    def test_changed_input_after_freeze_blocks_release(self):
        with TemporaryDirectory() as folder:
            output=self.generation_output(Path(folder));save(output/'status.json',{'state':'running','phase':'evaluation'})
            save(output/'tasks/0/inputs.json',{'changed':True})
            client=SimpleNamespace(read_flow_run=AsyncMock(return_value=SimpleNamespace(state=Running())))
            with patch.object(rerun,'predecessor_output_directory',return_value=output),self.assertRaisesRegex(ValueError,'changed after'):
                asyncio.run(rerun.baseline_evaluation_readiness(client,uuid4()))

    def test_new_running_baseline_without_prepared_output_keeps_waiting(self):
        with TemporaryDirectory() as folder,patch.object(rerun,'OUT',Path(folder)):
            client=SimpleNamespace(read_flow_run=AsyncMock(return_value=SimpleNamespace(state=Running())))
            with patch.object(rerun,'predecessor_output_directory',side_effect=ValueError('not prepared yet')):
                self.assertFalse(asyncio.run(rerun.baseline_evaluation_readiness(client,uuid4()))['ready'])

    def test_failed_baseline_blocks_v2(self):
        client=SimpleNamespace(read_flow_run=AsyncMock(return_value=SimpleNamespace(state=Failed())))
        with self.assertRaisesRegex(RuntimeError,'chưa được chạy'):asyncio.run(rerun.baseline_evaluation_readiness(client,uuid4()))

    def test_sequence_poll_does_not_release_on_first_unready_poll(self):
        with TemporaryDirectory() as folder:
            client=SimpleNamespace(update_artifact=AsyncMock())
            with patch.object(rerun,'baseline_evaluation_readiness',new_callable=AsyncMock,side_effect=[{'ready':False},{'ready':True}]),\
                 patch.object(rerun.asyncio,'sleep',new_callable=AsyncMock) as sleep:
                result=asyncio.run(rerun.wait_for_baseline_evaluation(client,uuid4(),directory=Path(folder),artifact_id=uuid4()))
                self.assertTrue(result['ready']);sleep.assert_awaited_once_with(15)
            self.assertEqual(json.loads((Path(folder)/'sequence_status.json').read_text())['new_generation_calls'],0)


if __name__=='__main__':unittest.main()
