"""Run an already submitted Prefect record in a dedicated detached process.

The existing flow ID is claimed as Pending before dispatch. The benchmark flow
retains snapshots, worker locks, evaluation serialization and Prefect reporting.
No new flow record or benchmark request budget is created here.
"""
from __future__ import annotations

import argparse
import asyncio
import fcntl
import json
import os
from uuid import UUID

from prefect.client.orchestration import get_client
from prefect.flow_engine import run_flow
from prefect.states import Pending
from prefect.client.schemas.responses import SetStateStatus

from .config import ROOT
from .flows import benchmark, resume_saved_batch
from .followup import benchmark_after_predecessors


def validate_dispatchable_run(flow_run):
    """Only an unstarted scheduled record may leave the shared listener queue."""
    if flow_run.state is None or not flow_run.state.is_scheduled() or flow_run.start_time is not None:
        raise ValueError("Dedicated dispatch requires an unstarted scheduled flow run")
    for prefix in ('console_', 'console_resume_'):
        output = ROOT / 'final/out' / (prefix + str(flow_run.id))
        if output.exists():
            raise ValueError("Flow output already exists; refuse duplicate generation")


async def dispatch(flow_run_id):
    state_directory = ROOT / 'final/out/run_console'
    state_directory.mkdir(parents=True, exist_ok=True)
    receipt_path = state_directory / ('dispatch_' + str(flow_run_id) + '.json')
    lock_path = receipt_path.with_suffix('.lock')
    with lock_path.open('a+') as lock:
        # One dispatcher per existing record, even if the CLI is invoked twice.
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        async with get_client() as client:
            flow_run = await client.read_flow_run(flow_run_id)
            validate_dispatchable_run(flow_run)
            # Prefect's atomic Scheduled -> Pending transition excludes a listener
            # racing to submit this record. Never bypass it with force=True.
            claim = await client.set_flow_run_state(flow_run_id, Pending(), force=False)
            if claim.status != SetStateStatus.ACCEPT:
                raise RuntimeError("Another runner claimed this flow run; no worker launched")
            flow_run = await client.read_flow_run(flow_run_id)
            parameters = flow_run.parameters
        receipt_path.write_text(json.dumps({'flow_run_id':str(flow_run_id), 'pid':os.getpid(),
            'state':'claimed'})+'\n')
        # The Prefect engine executes the original record and owns terminal state.
        try:
            if 'union_source_directory' in parameters:
                from .union import evaluate_saved_union
                flow = evaluate_saved_union
            elif 'baseline_packet_source' in parameters:
                from .rerun import plain_guidance_rerun
                flow = plain_guidance_rerun
            elif 'baseline_flow_run_id' in parameters:
                from .rerun import resume_after_baseline_generation
                flow = resume_after_baseline_generation
            elif 'predecessor_flow_run_ids' in parameters:
                flow = benchmark_after_predecessors
            elif 'source_directory' in parameters:
                flow = resume_saved_batch
            else:
                flow = benchmark
            result = await run_flow(flow, flow_run=flow_run, parameters=parameters, return_type='state')
        except BaseException as error:
            receipt_path.write_text(json.dumps({'flow_run_id':str(flow_run_id), 'pid':os.getpid(),
                'state':'dispatch_error', 'error_type':type(error).__name__})+'\n')
            raise
        receipt_path.write_text(json.dumps({'flow_run_id':str(flow_run_id), 'pid':os.getpid(),
            'state':result.name})+'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--flow-run-id', type=UUID, required=True)
    options = parser.parse_args()
    asyncio.run(dispatch(options.flow_run_id))


if __name__ == '__main__':
    main()
