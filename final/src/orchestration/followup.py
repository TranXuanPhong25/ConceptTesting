"""Prepare one immutable benchmark now; run it after verified predecessors finish.

Waiting performs only local/API reads. The original followup flow owns the worker,
config/progress/results/report artifacts and terminal state; no child flow is made.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import os
from pathlib import Path
import time
from uuid import UUID

from prefect import flow, get_run_logger
from prefect.artifacts import create_markdown_artifact
from prefect.client.orchestration import get_client
from prefect.client.schemas.actions import ArtifactUpdate
from prefect.context import get_run_context

from .config import ROOT, normalize, preview
from .flows import BENCHMARK_PYTHON, active_external_writers, attach_outputs, command, watch_worker
from .names import benchmark_run_name

OUT = ROOT / 'final/out'
POLL_SECONDS = 30
FAILED_PREDECESSOR_STATES = {'FAILED', 'CANCELLED', 'CRASHED'}


def validate_predecessor_ids(values, current_flow_run_id):
    """Require distinct existing run IDs and forbid a dependency on this run itself."""
    identifiers = [UUID(str(value)) for value in values]
    if not identifiers or len(identifiers) != len(set(identifiers)):
        raise ValueError('Predecessor flow IDs must be nonempty and unique')
    if UUID(str(current_flow_run_id)) in identifiers:
        raise ValueError('Followup cannot depend on its own flow ID')
    return identifiers


def predecessor_output_directory(flow_run_id):
    """Resolve the saved console/resume output without accepting arbitrary paths."""
    identifier = str(UUID(str(flow_run_id)))
    candidates = [OUT / ('console_' + identifier) / 'run',
                  OUT / ('console_resume_' + identifier)]
    existing = [directory for directory in candidates if directory.is_dir()]
    if len(existing) != 1:
        raise ValueError('Completed predecessor needs exactly one saved output directory: ' + identifier)
    return existing[0]


def validate_completed_predecessor(output):
    """Completed means native evaluation, source checks and immutable replay all finished."""
    try:
        status = json.loads((output / 'status.json').read_text())
        result = json.loads((output / 'result_digest.json').read_text())
        progress = json.loads((output / 'progress.json').read_text())
    except (OSError, ValueError) as error:
        raise ValueError('Completed predecessor has missing/invalid final artifacts') from error
    if status.get('state') != 'complete':
        raise ValueError('Completed predecessor output is not complete')
    if result.get('read_only_replay_matches') is not True or result.get('source_hashes_verified') is not True:
        raise ValueError('Completed predecessor lacks verified source hashes or immutable replay')
    total_tasks = progress.get('total_tasks')
    if type(total_tasks) is not int or total_tasks < 1 or progress.get('evaluated_tasks') != total_tasks:
        raise ValueError('Completed predecessor has unfinished native task evaluation')
    return {'output_directory': str(output), 'evaluated_tasks': total_tasks,
            'read_only_replay_matches': True, 'source_hashes_verified': True}


async def predecessor_status(client, flow_run_id):
    """A failed predecessor blocks v2; a merely running predecessor keeps it waiting."""
    record = await client.read_flow_run(flow_run_id)
    if record.state is None:
        raise ValueError('Predecessor has no Prefect state: ' + str(flow_run_id))
    state_type = record.state.type.value
    result = {'flow_run_id': str(flow_run_id), 'state': record.state.name, 'ready': False}
    if state_type in FAILED_PREDECESSOR_STATES:
        raise RuntimeError('Predecessor ' + str(flow_run_id) + ' kết thúc ở ' + record.state.name +
                           '; followup chưa chạy workload. Cần quyết định continuation rõ ràng.')
    if record.state.is_completed():
        result.update(validate_completed_predecessor(predecessor_output_directory(flow_run_id)))
        result['ready'] = True
    return result


def save_json(path, value):
    """Atomically update followup metadata; the worker snapshot stays untouched."""
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def waiting_markdown(statuses, budget, *, ready=False, reason=None):
    if reason:
        opening = 'Followup chưa chạy workload; bị chặn: ' + reason
    elif ready:
        opening = 'Đã xác nhận mọi predecessor hoàn tất evaluation/replay; chuẩn bị chạy followup.'
    else:
        opening = 'Đang chờ mọi predecessor hoàn tất; chưa có model/tokenizer/native call của followup.'
    return (opening + '\n\nKết quả detection và coverage của followup: pending.\n\n'
            + f"Budget tối đa {budget['logical_call_cap']} logical calls; "
            + f"{budget['config']['inputs_per_task']} inputs/task/arm; "
            + f"{budget['config']['completion_tokens']} completion tokens/call.\n\n"
            + 'Source/config/cohort được snapshot trước khi chờ; không dùng code worktree mới lúc bắt đầu.\n\n'
            + '```json\n' + json.dumps(statuses, ensure_ascii=False, indent=2) + '\n```')


def scheduled_start_epoch(not_before_utc):
    """Require an explicit timezone so a scheduled workload cannot start early."""
    if not_before_utc is None:
        return None
    parsed = dt.datetime.fromisoformat(not_before_utc.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('not_before_utc must include a timezone')
    return parsed.timestamp()


async def wait_for_predecessors(client, identifiers, *, directory, budget, progress_artifact_id,
                                not_before_utc=None):
    """Only API/artifact reads until every predecessor has a verified final result."""
    deadline = scheduled_start_epoch(not_before_utc)
    statuses = []
    try:
        while True:
            statuses = [await predecessor_status(client, identifier) for identifier in identifiers]
            predecessors_ready = all(status['ready'] for status in statuses)
            deadline_reached = deadline is None or time.time() >= deadline
            ready = predecessors_ready and deadline_reached
            waiting_state = 'waiting_deadline' if predecessors_ready else 'waiting_predecessors'
            save_json(directory / 'followup_status.json', {'state': 'ready' if ready else waiting_state,
                'predecessors': statuses, 'model_calls': 0, 'not_before_utc': not_before_utc,
                'updated_utc': time.time()})
            message = waiting_markdown(statuses, budget, ready=ready)
            if not_before_utc:
                message += ('\n\nKhông bắt đầu workload trước ' + not_before_utc +
                            '; vẫn cần predecessor hoàn tất evaluation/source checks/replay.')
            await client.update_artifact(progress_artifact_id, ArtifactUpdate(data=message))
            if ready:
                return statuses
            await asyncio.sleep(POLL_SECONDS)
    except BaseException as error:
        # Cancellation/failure must never fall through to the worker launch.
        reason = type(error).__name__ if isinstance(error, asyncio.CancelledError) else str(error)
        save_json(directory / 'followup_status.json', {'state': 'blocked', 'predecessors': statuses,
            'reason': reason, 'model_calls': 0, 'updated_utc': time.time()})
        await client.update_artifact(progress_artifact_id,
            ArtifactUpdate(data=waiting_markdown(statuses, budget, reason=reason)))
        raise


@flow(name='Testing arms followup', retries=0, log_prints=False, persist_result=False)
async def benchmark_after_predecessors(predecessor_flow_run_ids: list[str], benchmark_parameters: dict,
                                       not_before_utc: str | None = None):
    """Run exactly one prepared benchmark after all explicitly selected predecessors.

    predecessor_flow_run_ids: Both current full runs; failure blocks rather than auto-resuming.
    benchmark_parameters: Explicit normalized budget/config; endpoint stays in private environment.
    """
    scheduled_start_epoch(not_before_utc)
    run_id = str(get_run_context().flow_run.id)
    identifiers = validate_predecessor_ids(predecessor_flow_run_ids, run_id)
    config = normalize(benchmark_parameters)
    budget = preview(config)
    directory = OUT / ('console_' + run_id)
    # Existing output is evidence of a previous execution, not permission to rerun it.
    directory.mkdir(parents=True, exist_ok=False)
    save_json(directory / 'submitted_config.json', config)
    save_json(directory / 'predecessors.json', {'flow_run_ids': list(map(str, identifiers)),
        'not_before_utc': not_before_utc})
    save_json(directory / 'preview.json', budget)
    async with get_client() as client:
        await client.update_flow_run(get_run_context().flow_run.id,
            name='Waiting · ' + benchmark_run_name(config))
    await create_markdown_artifact(markdown='Budget đã đăng ký trước khi chờ.\n\n```json\n' +
        json.dumps(budget, ensure_ascii=False, indent=2) + '\n```', key='budget-preview',
        description='Config và budget thật; các metrics chưa chạy là pending.')
    output = directory / 'run'
    # Preparation freezes code/cohort/config/private route but performs no workload.
    await command([BENCHMARK_PYTHON, '-m', 'final.src.orchestration.worker', '--config',
        directory / 'submitted_config.json', '--artifacts', output, '--prepare-only'],
        log_path=directory / 'prepare.log')
    await attach_outputs(output)
    progress_artifact_id = await create_markdown_artifact(
        markdown=waiting_markdown([], budget), key='followup-progress',
        description='Chờ predecessor; update cùng artifact ID, không tạo history lặp.')
    async with get_client() as client:
        completed = await wait_for_predecessors(client, identifiers, directory=directory,
            budget=budget, progress_artifact_id=progress_artifact_id, not_before_utc=not_before_utc)
        save_json(directory / 'predecessors_completed.json', {'predecessors': completed})
        # A new unrelated writer on the same endpoint still gets serialization.
        while active_external_writers(exclude=output):
            get_run_logger().info('Predecessors đã xong; chờ writer khác trên cùng endpoint.')
            await asyncio.sleep(POLL_SECONDS)
        await client.update_flow_run(get_run_context().flow_run.id, name=benchmark_run_name(config))
        await client.update_artifact(progress_artifact_id,
            ArtifactUpdate(data='Predecessors đã hoàn tất và xác minh. Followup bắt đầu trên immutable snapshot. '
                           'Kết quả detection/coverage: pending.'))
    save_json(directory / 'followup_status.json', {'state': 'launching', 'updated_utc': time.time()})
    plan = json.loads((output / 'launch_plan.json').read_text())
    environment = {key: value for key, value in os.environ.items()
                   if key in ('HOME', 'LANG', 'LC_ALL', 'TZ', 'TMPDIR')}
    environment.update(PATH=os.defpath, PYTHONPATH=plan['runtime'], PYTHONDONTWRITEBYTECODE='1')
    await watch_worker([BENCHMARK_PYTHON, '-P', '-B', '-m', 'final.src.orchestration.worker',
                        '--worker', '--artifacts', output], output, environment)
    result = await attach_outputs(output)
    save_json(directory / 'followup_status.json', {'state': 'complete', 'updated_utc': time.time()})
    async with get_client() as client:
        await client.update_artifact(progress_artifact_id,
            ArtifactUpdate(data='Followup hoàn tất evaluation, source checks và immutable replay. '
                           'Xem benchmark-results và benchmark-report trên cùng flow run.'))
    return result
