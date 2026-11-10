"""Controlled Plain-guidance rerun, followed by V2 during native evaluation.

Only public visibility packets cross into the new baseline. Received V2 calls are
preserved by the existing resume preparer. Neither gate runs a model or program.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import shutil
import time
from uuid import UUID

from prefect import flow, get_run_logger
from prefect.artifacts import create_markdown_artifact
from prefect.client.orchestration import get_client
from prefect.client.schemas.actions import ArtifactUpdate
from prefect.context import get_run_context

from .config import ROOT, normalize
from .flows import BENCHMARK_PYTHON, active_external_writers, attach_outputs, command, watch_worker
from .followup import predecessor_output_directory, save_json, validate_completed_predecessor
from .worker import checksum
from final.src.runtime.artifacts import digest

OUT = ROOT / 'final/out'
POLL_SECONDS = 15
FAILED_STATES = {'FAILED', 'CANCELLED', 'CRASHED'}


def validate_console_source(value):
    """Accept an existing saved run inside final/out; never a credential path."""
    source = (ROOT / value).resolve()
    if not source.is_relative_to(OUT.resolve()) or not (source / 'config_snapshot.json').is_file():
        raise ValueError('Source must be a saved console run inside final/out')
    return source


def baseline_configuration(source):
    """Keep Direct's generation/evaluation settings and change only arm guidance."""
    validate_completed_predecessor(source)
    config = normalize(json.loads((source / 'config_snapshot.json').read_text()))
    if config['mode'] != 'batch' or 'direct' not in config['arms']:
        raise ValueError('Controlled guidance rerun requires a completed Direct batch source')
    if config['cohort'] != 'humaneval164' or config['task_numbers']:
        raise ValueError('Controlled full rerun requires the complete HumanEval cohort')
    return normalize({**config, 'arms': ['plain']})


def validate_source_packet_requests(source, selected_task_numbers, source_config):
    """Direct source requests must use exactly the stored shared visibility packet."""
    records = []
    for number in selected_task_numbers:
        packet_path = source / 'tasks' / str(number) / 'packet.json'
        packet = json.loads(packet_path.read_text())
        if packet.get('task_id') != f'HumanEval/{number}':
            raise ValueError('Source packet task ID differs from selected cohort')
        if not packet.get('skip'):
            request_path = packet_path.parent / 'calls/direct/request.json'
            request = json.loads(request_path.read_text())
            messages = request.get('messages')
            if (not isinstance(messages, list) or len(messages) != 2
                    or messages[1].get('content') != packet.get('common', '') + '\n'):
                raise ValueError('Direct request is not the unmodified shared packet')
            expected = {'max_tokens': source_config['completion_tokens'],
                        'temperature': source_config['temperature'],
                        'seed': source_config['input_seed'] + number}
            if any(request.get(name) != value for name, value in expected.items()):
                raise ValueError('Direct request settings differ from its frozen config')
        records.append((packet_path, checksum(packet_path)))
    return records


def pin_baseline_source(source, output):
    """Freeze original runtime and packet bytes in the new output before generation.

    Config/routing remain fresh. No responses, generated inputs, oracle results or
    evaluation checkpoints are imported into this new baseline.
    """
    source_config = baseline_configuration(source)
    source_plan = json.loads((source / 'launch_plan.json').read_text())
    source_runtime = Path(source_plan['runtime'])
    plan_path = output / 'launch_plan.json'
    plan = json.loads(plan_path.read_text())
    runtime = Path(plan['runtime'])
    description = json.loads((output / 'preview.json').read_text())
    selected = description['selected_task_numbers']
    source_preview = json.loads((source / 'preview.json').read_text())
    if selected != source_preview['selected_task_numbers']:
        raise ValueError('New rerun task selection differs from source')
    if description['cohort_sha256'] != source_preview['cohort_sha256']:
        raise ValueError('New rerun cohort differs from source')
    if json.loads((output / 'config_snapshot.json').read_text()) != source_config:
        raise ValueError('Rerun config must differ only in selected Plain arm')
    packets = validate_source_packet_requests(source, selected, source_config)
    if (output / 'tasks').exists() or (output / 'worker_started.json').exists():
        raise ValueError('Pin packets before any rerun worker/task output exists')

    # Copy author/run source as data; preserve all original runtime bytes.
    shutil.rmtree(runtime)
    shutil.copytree(source_runtime, runtime, ignore=shutil.ignore_patterns('__pycache__'))
    cohort_relative = Path(source_plan['cohort']).relative_to(source_runtime)
    plan['cohort'] = str(runtime / cohort_relative)
    save_json(plan_path, plan)
    snapshot_path = output / 'source_snapshot.json'
    snapshot = json.loads(snapshot_path.read_text())
    # Remove old runtime identities before replacing them with the source clone.
    snapshot['sources'] = {name: value for name, value in snapshot['sources'].items()
                           if not Path(name).is_relative_to(runtime)}
    for path in runtime.rglob('*'):
        if path.is_file() and '__pycache__' not in path.parts:
            expected_hash = checksum(source_runtime / path.relative_to(runtime))
            if checksum(path) != expected_hash:
                raise ValueError('Original runtime changed while preparing controlled baseline')
            snapshot['sources'][str(path)] = expected_hash
    copied = []
    for packet_path, expected_hash in packets:
        target = output / packet_path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(packet_path, target)
        if checksum(packet_path) != expected_hash or checksum(target) != expected_hash:
            raise ValueError('Source packet changed while preparing controlled baseline')
        snapshot['sources'][str(target)] = expected_hash
        copied.append({'relative_path': str(packet_path.relative_to(source)), 'sha256': expected_hash})
    receipt = output / 'baseline_packet_receipts.json'
    driver_snapshot = output / 'preparation/rerun.py'
    driver_snapshot.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(Path(__file__), driver_snapshot)
    snapshot['sources'][str(driver_snapshot)] = checksum(driver_snapshot)
    save_json(receipt, {'source': str(source), 'source_cohort_sha256': source_preview['cohort_sha256'],
        'runtime_policy': 'byte-identical original Direct runtime', 'packets': copied,
        'preparer_source_snapshot': str(driver_snapshot), 'preparer_sha256': checksum(driver_snapshot),
        'original_prompt_tokens_are_historical': True,
        'generation_policy': 'new Plain calls; no received generation or evaluation imported'})
    snapshot['sources'][str(plan_path)] = checksum(plan_path)
    snapshot['sources'][str(receipt)] = checksum(receipt)
    save_json(snapshot_path, snapshot)
    return {'source': str(source), 'copied_packets': len(copied), 'new_model_calls': 0}


async def verify_source_guard(directory, log_path):
    """Use the benchmark's existing guard without importing its dependencies here."""
    await command([BENCHMARK_PYTHON, '-c',
        'import sys;from pathlib import Path;from final.src.audits.run_bva_full import SourceGuard;SourceGuard(Path(sys.argv[1])).verify()',
        directory], log_path=log_path)


def frozen_worker_environment(plan):
    environment = {key: value for key, value in os.environ.items()
                   if key in ('HOME', 'LANG', 'LC_ALL', 'TZ', 'TMPDIR')}
    environment.update(PATH=os.defpath, PYTHONPATH=plan['runtime'], PYTHONDONTWRITEBYTECODE='1')
    return environment


async def run_frozen_worker(output):
    plan = json.loads((output / 'launch_plan.json').read_text())
    await watch_worker([BENCHMARK_PYTHON, '-P', '-B', '-m', 'final.src.orchestration.worker',
                        '--worker', '--artifacts', output], output, frozen_worker_environment(plan))
    return await attach_outputs(output)


@flow(name='Controlled Plain guidance rerun', retries=0, log_prints=False, persist_result=False)
async def plain_guidance_rerun(baseline_packet_source: str):
    """Generate new Plain inputs with Direct's original packets, cap and seeds."""
    source = validate_console_source(baseline_packet_source)
    config = baseline_configuration(source)
    run_id = str(get_run_context().flow_run.id)
    directory = OUT / ('console_' + run_id)
    directory.mkdir(parents=True, exist_ok=False)
    save_json(directory / 'submitted_config.json', config)
    async with get_client() as client:
        await client.update_flow_run(get_run_context().flow_run.id,
            name=f'Full164 · Plain guidance rerun · {config["completion_tokens"]} tokens · {config["timeout_seconds"]:g}s')
    await verify_source_guard(source, directory / 'source_guard.log')
    output = directory / 'run'
    await command([BENCHMARK_PYTHON, '-m', 'final.src.orchestration.worker', '--config',
        directory / 'submitted_config.json', '--artifacts', output, '--prepare-only'], log_path=directory / 'prepare.log')
    receipt = pin_baseline_source(source, output)
    await verify_source_guard(output, directory / 'prepared_guard.log')
    await attach_outputs(output)
    await create_markdown_artifact(markdown='Chỉ thêm guidance của Plain vào packet gốc của Direct. '
        'Giữ cap, seeds, visibility và frozen runtime; sinh inputs mới, không tái dùng responses.\n\n```json\n' +
        json.dumps(receipt, ensure_ascii=False, indent=2) + '\n```', key='baseline-packet-source',
        description='Nguồn public packets và runtime được pin; không import oracle hoặc outcome vào generation.')
    while active_external_writers(exclude=output):
        get_run_logger().info('Chờ model writer khác trên cùng endpoint trước baseline rerun.')
        await asyncio.sleep(POLL_SECONDS)
    return await run_frozen_worker(output)


def validate_generation_freeze(output):
    """Every selected task input batch must match the global generation freeze."""
    freeze = json.loads((output / 'generation_frozen.json').read_text())
    preview = json.loads((output / 'preview.json').read_text())
    expected_tasks = {f'HumanEval/{number}' for number in preview['selected_task_numbers']}
    if set(freeze.get('inputs', {})) != expected_tasks:
        raise ValueError('Baseline freeze is missing selected tasks')
    if freeze.get('cohort_sha256') != preview['cohort_sha256']:
        raise ValueError('Baseline freeze cohort differs')
    if freeze.get('inputs_sha256') != digest(freeze['inputs']):
        raise ValueError('Baseline generation-freeze summary hash differs')
    for task_id, expected_hash in freeze['inputs'].items():
        path = output / 'tasks' / task_id.split('/')[-1] / 'inputs.json'
        if digest(json.loads(path.read_text())) != expected_hash:
            raise ValueError('Baseline input changed after generation freeze')
    return len(expected_tasks)


async def baseline_evaluation_readiness(client, baseline_flow_run_id):
    """Release V2 only after frozen baseline generation reaches native evaluation."""
    record = await client.read_flow_run(baseline_flow_run_id)
    if record.state is None:
        raise ValueError('Baseline has no Prefect state')
    if record.state.type.value in FAILED_STATES:
        raise RuntimeError('Baseline kết thúc ở ' + record.state.name + '; V2 chưa được chạy tiếp.')
    result = {'flow_run_id': str(baseline_flow_run_id), 'state': record.state.name, 'ready': False}
    if not record.state.is_running() and not record.state.is_completed():
        return result
    try:
        output = predecessor_output_directory(baseline_flow_run_id)
    except ValueError:
        # A newly Running flow can precede its prepare subprocess by a few polls.
        candidates = [OUT / ('console_' + str(baseline_flow_run_id)) / 'run',
                      OUT / ('console_resume_' + str(baseline_flow_run_id))]
        if not record.state.is_completed() and not any(path.is_dir() for path in candidates):
            return result
        raise
    status_path = output / 'status.json'
    if not status_path.exists():
        return result
    status = json.loads(status_path.read_text())
    progress_path = output / 'progress.json'
    progress = json.loads(progress_path.read_text()) if progress_path.exists() else {}
    if record.state.is_completed():
        validate_completed_predecessor(output)
    elif status.get('state') != 'running' or status.get('phase') != 'evaluation':
        return result
    total = progress.get('total_tasks')
    if type(total) is not int or total < 1 or progress.get('generated_tasks') != total:
        raise ValueError('Baseline entered evaluation without all generation task records')
    frozen_count = validate_generation_freeze(output)
    if frozen_count != total:
        raise ValueError('Baseline progress count differs from frozen task count')
    result.update(ready=True, output_directory=str(output), frozen_tasks=frozen_count,
                  release_condition='generation frozen and native evaluation begun')
    return result


async def wait_for_baseline_evaluation(client, identifier, *, directory, artifact_id):
    try:
        while True:
            readiness = await baseline_evaluation_readiness(client, identifier)
            save_json(directory / 'sequence_status.json', {'state': 'ready' if readiness['ready'] else 'waiting_baseline_generation',
                'baseline': readiness, 'new_generation_calls': 0, 'updated_utc': time.time()})
            await client.update_artifact(artifact_id, ArtifactUpdate(data=
                ('Baseline đã freeze inputs và bắt đầu evaluation; V2 được tiếp tục.' if readiness['ready'] else
                 'Chờ baseline sinh xong inputs và bắt đầu evaluation; chưa có generation call mới của V2.') +
                '\n\n```json\n' + json.dumps(readiness, ensure_ascii=False, indent=2) + '\n```'))
            if readiness['ready']:
                return readiness
            await asyncio.sleep(POLL_SECONDS)
    except BaseException as error:
        reason = type(error).__name__ if isinstance(error, asyncio.CancelledError) else str(error)
        save_json(directory / 'sequence_status.json', {'state': 'blocked', 'reason': reason,
            'new_generation_calls': 0, 'updated_utc': time.time()})
        await client.update_artifact(artifact_id, ArtifactUpdate(data='V2 chưa chạy tiếp; bị chặn: ' + reason))
        raise


@flow(name='Resume V2 during baseline evaluation', retries=0, log_prints=False, persist_result=False)
async def resume_after_baseline_generation(source_directory: str, baseline_flow_run_id: str):
    """Preserve received V2 calls, then overlap generation with baseline evaluation."""
    source = validate_console_source(source_directory)
    baseline_id = UUID(baseline_flow_run_id)
    current_id = get_run_context().flow_run.id
    if baseline_id == current_id:
        raise ValueError('V2 cannot wait on its own flow ID')
    directory = OUT / ('console_resume_' + str(current_id))
    async with get_client() as client:
        await client.update_flow_run(current_id, name='Waiting baseline evaluation · V2 smoke continuation')
    await command([BENCHMARK_PYTHON, '-m', 'final.src.orchestration.worker', '--resume-from', source,
        '--artifacts', directory, '--prepare-only'], log_path=directory.parent / ('prepare_' + str(current_id) + '.log'))
    await attach_outputs(directory)
    receipt = json.loads((directory / 'import_receipts.json').read_text())
    artifact_id = await create_markdown_artifact(markdown='Đã giữ nguyên responses và retry history của V2; '
        'chờ baseline bắt đầu evaluation.\n\n```json\n' + json.dumps(receipt.get('original_writer_usage', {}), indent=2) + '\n```',
        key='sequence-progress', description='Resume V2 sau baseline generation freeze; không gọi lại received responses.')
    async with get_client() as client:
        readiness = await wait_for_baseline_evaluation(client, baseline_id, directory=directory, artifact_id=artifact_id)
        save_json(directory / 'baseline_generation_ready.json', readiness)
        while active_external_writers(exclude=directory):
            get_run_logger().info('Baseline đang evaluation; chờ writer khác trên cùng endpoint trước resume V2.')
            await asyncio.sleep(POLL_SECONDS)
        await client.update_flow_run(current_id, name='V2 smoke continuation · during Plain rerun evaluation')
    result = await run_frozen_worker(directory)
    async with get_client() as client:
        await client.update_artifact(artifact_id, ArtifactUpdate(data='V2 đã hoàn tất evaluation/source checks/replay; xem report trên cùng run.'))
    return result
