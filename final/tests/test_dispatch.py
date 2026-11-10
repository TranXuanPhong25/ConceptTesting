"""Offline dispatcher and routing fixtures; run with the orchestration Python."""
import asyncio
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

try:
    from prefect.states import Scheduled, Pending, Completed
    from prefect.client.schemas.responses import SetStateStatus
    from final.src.orchestration import dispatch as dispatcher
except ImportError:
    raise unittest.SkipTest('Uses the isolated orchestration environment')

from final.src.orchestration.routing import endpoint_identity_for_run
from final.src.orchestration import flows


class DispatchTests(unittest.TestCase):
    def run_dispatch(self, accepted):
        with TemporaryDirectory() as directory:
            flow_run=SimpleNamespace(id=uuid4(),state=Scheduled(),start_time=None,parameters={'cohort':'fixture'})
            client=SimpleNamespace(read_flow_run=AsyncMock(return_value=flow_run),
                set_flow_run_state=AsyncMock(return_value=SimpleNamespace(status=accepted)))
            manager=AsyncMock()
            manager.__aenter__.return_value=client
            with patch.object(dispatcher,'ROOT',Path(directory)),patch.object(dispatcher,'get_client',return_value=manager),\
                 patch.object(dispatcher,'run_flow',new_callable=AsyncMock,return_value=Completed()) as engine:
                if accepted==SetStateStatus.ACCEPT:
                    asyncio.run(dispatcher.dispatch(flow_run.id))
                    engine.assert_awaited_once()
                    self.assertEqual(engine.call_args.kwargs['flow_run'].id,flow_run.id)
                else:
                    with self.assertRaisesRegex(RuntimeError,'Another runner'):
                        asyncio.run(dispatcher.dispatch(flow_run.id))
                    engine.assert_not_awaited()
                arguments=client.set_flow_run_state.call_args
                self.assertFalse(arguments.kwargs['force'])
                self.assertEqual(arguments.args[1].name,'Pending')

    def test_atomic_claim_accepts_then_executes_existing_id(self):
        self.run_dispatch(SetStateStatus.ACCEPT)

    def test_rejected_atomic_claim_never_launches_worker(self):
        self.run_dispatch(SetStateStatus.REJECT)

    def test_existing_output_or_started_record_rejects_duplicate(self):
        with TemporaryDirectory() as directory,patch.object(dispatcher,'ROOT',Path(directory)):
            flow_run=SimpleNamespace(id=uuid4(),state=Pending(),start_time=None)
            with self.assertRaises(ValueError):dispatcher.validate_dispatchable_run(flow_run)
            flow_run.state=Scheduled()
            output=Path(directory)/'final/out'/('console_'+str(flow_run.id));output.mkdir(parents=True)
            with self.assertRaisesRegex(ValueError,'already exists'):dispatcher.validate_dispatchable_run(flow_run)

    def test_endpoint_identity_matches_private_routes_without_exposing_them(self):
        with TemporaryDirectory() as directory:
            root=Path(directory)
            for index,endpoint in enumerate(['http://first.invalid/v1','http://first.invalid/v1/','http://second.invalid/v1']):
                folder=root/str(index);folder.mkdir()
                profile=folder/'private.env';profile.write_text('export FINAL_BASE_URL='+endpoint+'\n')
                (folder/'launch_plan.json').write_text(json.dumps({'endpoint_env_file':str(profile)}))
            self.assertEqual(endpoint_identity_for_run(root/'0'),endpoint_identity_for_run(root/'1'))
            self.assertNotEqual(endpoint_identity_for_run(root/'0'),endpoint_identity_for_run(root/'2'))
            self.assertIsNone(endpoint_identity_for_run(root/'missing'))
            (root/'0/private.env').write_text('FINAL_BASE_URL=http://old.invalid/v1\nFINAL_BASE_URL=http://second.invalid/v1\n')
            self.assertEqual(endpoint_identity_for_run(root/'0'),endpoint_identity_for_run(root/'2'))

    def test_nested_console_worker_is_checked_and_only_same_endpoint_blocks(self):
        with TemporaryDirectory() as directory:
            root=Path(directory)
            writer=root/'console_fixture/run';writer.mkdir(parents=True)
            (writer/'status.json').write_text(json.dumps({'state':'running','phase':'generation','pid':123}))
            requester=root/'console_request/run'
            original_read=Path.read_bytes
            def command_line(path):
                if str(path)=='/proc/123/cmdline':return ('python --artifacts '+str(writer)).encode()
                return original_read(path)
            with patch.object(flows,'OUT',root),patch.object(Path,'read_bytes',command_line),\
                 patch.object(flows,'endpoint_identity_for_run',return_value='same'):
                self.assertEqual(len(flows.active_external_writers(exclude=requester)),1)
            with patch.object(flows,'OUT',root),patch.object(Path,'read_bytes',command_line),\
                 patch.object(flows,'endpoint_identity_for_run',side_effect=lambda path:'selected' if path==requester else 'other'):
                self.assertEqual(flows.active_external_writers(exclude=requester),[])


if __name__=='__main__':unittest.main()
