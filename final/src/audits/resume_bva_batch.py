"""Continue saved paired batch calls in their frozen runtime without regenerating responses."""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from . import run_bva_batch as frozen
from .continue_bva_evaluation import read, save, digest, checksum

ROOT = Path(__file__).resolve().parents[3]


def inventory(directory):
    return {str(path): checksum(path) for path in directory.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts
            and path.name not in ('.worker.lock', '.run.lock')}


def checkpoints(source, requests):
    received, unfinished = [], []
    for attempt_path in (source / 'generation').glob('tasks/*/calls/*/attempt.json'):
        task = attempt_path.parents[2].name
        name = attempt_path.parent.name.split('_unknown_attempt_', 1)[0]
        key = task + '/' + name
        if key not in requests:
            raise ValueError('Unregistered imported checkpoint: ' + key)
        request = read(attempt_path.parent / 'request.json')
        attempt = read(attempt_path)
        if digest(request) != requests[key]['request_sha256'] or attempt['request_id'] != digest(request):
            raise ValueError('Imported request identity differs: ' + key)
        response = attempt_path.parent / 'response.json'
        if response.exists():
            if '_unknown_attempt_' in attempt_path.parent.name or attempt['state'] != 'received':
                raise ValueError('Response does not belong to a received current checkpoint')
            received.append(key)
        else:
            if attempt['state'] not in ('unknown', 'started'):
                raise ValueError('Non-received checkpoint has unexpected state')
            if attempt.get('error', {}).get('retryable') is False:
                raise ValueError('Permanent historical transport error cannot be retried')
            unfinished.append({'key': key, 'directory': str(attempt_path.parent),
                               'state': attempt['state'], 'attempt_number': attempt.get('attempt_number')})
    if len(received) != len(set(received)):
        raise ValueError('Duplicate logical received checkpoints')
    for key in set(row['key'] for row in unfinished) - set(received):
        prior = sum(row['key'] == key for row in unfinished)
        if prior >= 3:
            raise ValueError('Historical completion retry cap exhausted: ' + key)
    return received, unfinished


def prepare(source, directory):
    if directory.exists():
        raise ValueError('Use a fresh continuation output')
    with (source / '.worker.lock').open('r') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if read(source / 'status.json')['state'] != 'interrupted':
            raise ValueError('Source batch is not stopped/interrupted')

        original_files = inventory(source)
        plan = read(source / 'launch_plan.json')
        saved_plan = read(source / 'request_plan.json')
        requests = saved_plan['requests']
        if len(requests) != saved_plan['logical_calls'] or len(requests) > plan['logical_call_cap']:
            raise ValueError('Saved logical request plan differs')
        for record in requests.values():
            if digest(record['request']) != record['request_sha256']:
                raise ValueError('Saved request digest differs')
        received, unfinished = checkpoints(source, requests)
        directory.mkdir(parents=True)
        runtime = directory / 'runtime'
        shutil.copytree(source / 'runtime', runtime, ignore=shutil.ignore_patterns('__pycache__'))
        controller = runtime / 'final/src/audits/resume_bva_batch.py'
        controller.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(__file__, controller)
        controller.chmod(0o444)
        shutil.copytree(source / 'generation', directory / 'generation')
        if (source / 'keepalive').exists():
            shutil.copytree(source / 'keepalive', directory / 'keepalive')
        shutil.copyfile(source / 'request_plan.json', directory / 'request_plan.json')
        cohort_relative = Path(plan['cohort']).relative_to(Path(plan['runtime']))
        new_plan = {**plan, 'runtime': str(runtime), 'cohort': str(runtime / cohort_relative),
            'continuation_source': str(source), 'imported_received_calls': len(received),
            'remaining_logical_call_cap': len(requests)-len(received),
            'request_plan_sha256': checksum(source / 'request_plan.json'),
            'recovery_policy': 'reuse exact request plan/runtime; preserve all received and unknown calls'}
        save(directory / 'launch_plan.json', new_plan)
        receipts = []
        snapshot = dict(original_files)
        for path in (directory / 'generation').rglob('*'):
            if not path.is_file():
                continue
            relative = path.relative_to(directory)
            old = source / relative
            expected = original_files[str(old)]
            if checksum(path) != expected:
                raise ValueError('Imported file copy differs')
            mutable = False
            if 'calls' in path.parts and '_unknown_attempt_' not in path.parent.name:
                attempt_path = path.parent / 'attempt.json'
                mutable = attempt_path.exists() and read(attempt_path).get('state') != 'received'
            receipts.append({'source': str(old), 'destination': str(path), 'sha256': expected,
                             'mutable_unreceived_checkpoint': mutable})
            if not mutable:
                snapshot[str(path)] = expected
        for path in runtime.rglob('*'):
            if path.is_file():
                path.chmod(0o444)
                snapshot[str(path)] = checksum(path)
        for path in (directory / 'keepalive').glob('*.json'):
            snapshot[str(path)] = checksum(path)
        old_usage = frozen.call_usage(source / 'generation')
        save(directory / 'import_receipts.json', {'files': receipts, 'source_files': original_files,
             'source_received_keys': sorted(received), 'unfinished_history': unfinished,
             'original_writer_usage': old_usage, 'original_keepalive_usage': frozen.keepalive_usage(source),
             'response_hash_policy': 'received identity verified; response byte hashes captured at recovery, no earlier global response freeze'})
        for name in ('launch_plan.json', 'request_plan.json', 'import_receipts.json'):
            snapshot[str(directory / name)] = checksum(directory / name)
        save(directory / 'source_snapshot.json', {'sources': snapshot, 'archive': {}})
        if inventory(source) != original_files:
            raise ValueError('Continuation changed original source run')
        save(directory / 'status.json', {'state': 'prepared', 'imported_received_calls': len(received),
             'remaining_logical_call_cap': len(requests)-len(received), 'new_model_calls': 0})
        return new_plan


def verify_saved_batches(directory, plan):
    """Re-decode saved complete batches using cached calls only, without model/tokenizer."""
    from final.src.modular.calls import CachedModelCalls
    from final.src.modular.artifacts import ArtifactStore
    from final.src.modular.context import PipelineSettings, TaskContext
    tasks = {task['task_id']: task for task in frozen.load_tasks()}
    metadata = frozen.load_metadata()
    calls = CachedModelCalls(ArtifactStore(directory / 'generation', read_only=True))
    for path in (directory / 'generation').glob('tasks/*/inputs.json'):
        batch = read(path)
        if batch.get('skip'):
            continue
        packet = read(path.parent / 'packet.json')
        if packet.get('skip'):
            if any(row['inputs'] for row in batch['arms'].values()):
                raise ValueError('Skipped writer packet has nonempty inputs')
            continue
        task = tasks[batch['task_id']]
        context = TaskContext(task, metadata[task['task_id']], ArtifactStore(directory / 'generation', read_only=True),
                              PipelineSettings(**plan['settings']), calls)
        context.packet = packet
        reconstructed = {arm.name: arm.run(context) for arm in frozen.ARMS}
        if reconstructed != batch['arms']:
            raise ValueError('Cached response decode differs from imported batch: ' + batch['task_id'])


def finalize(directory, summary, plan):
    receipts = read(directory / 'import_receipts.json')
    source = Path(plan['continuation_source'])
    if inventory(source) != receipts['source_files']:
        raise ValueError('Original interrupted run changed during continuation')
    for receipt in receipts['files']:
        if not receipt['mutable_unreceived_checkpoint'] and checksum(receipt['destination']) != receipt['sha256']:
            raise ValueError('Imported received data changed')
    current = read(directory / 'generation_usage.json')
    old = receipts['original_writer_usage']
    difference = {key: current[key]-old[key] for key in ('invocations','received','unknown')}
    difference['known_usage'] = {key: current['known_usage'][key]-old['known_usage'][key] for key in old['known_usage']}
    if difference['received'] != plan['remaining_logical_call_cap']:
        raise ValueError('New generation exceeded missing logical slots')
    result = {'arms': summary['arms'], 'evaluated_base_pass': summary['evaluated_base_pass'],
        'writer_usage': current, 'new_writer_usage': difference, 'imported_writer_usage': old,
        'keepalive_usage': frozen.keepalive_usage(directory),
        'comparison': frozen.paired_verdicts(directory / 'evaluation'),
        'read_only_replay_matches': True, 'source_hashes_verified': None,
        'original_run_unchanged': True, 'imported_responses_unchanged': True,
        'continuation_source': str(source)}
    save(directory / 'result_digest.json', result)
    comparison = result['comparison']['detections']
    lines = ['# Matched batch Direct versus Soft BVA', '',
        'Continued from saved responses with the exact original request plan, packet visibility and frozen generator/scorer. No received response regenerated. Original transport history/attempt cap preserved.', '',
        '| Metric | Direct | Soft BVA |', '|---|---:|---:|',
        f"| Detected PUTs | {comparison['direct']} | {comparison['soft_bva']} |",
        f"| Novel valid inputs | {summary['arms']['direct']['valid_inputs']} | {summary['arms']['soft_bva']['valid_inputs']} |",
        f"| Tasks with detection | {summary['arms']['direct']['tasks_detected']} | {summary['arms']['soft_bva']['tasks_detected']} |", '',
        f"Shared {comparison['shared']}; Direct-only {comparison['direct_only']}; Soft-only {comparison['soft_bva_only']}; net Soft-minus-Direct {comparison['net_soft_minus_direct']:+d}.", '',
        f"Stable wrong-value comparisons: {result['comparison']['stable_wrong_values']}.",
        f"Task wins by detected PUT count: {result['comparison']['task_wins_by_detected_put_count']}.", '',
        f"Cumulative writer usage (imports counted once): {current}.",
        f"New continuation usage: {difference}. Cumulative keepalive usage separate: {result['keepalive_usage']}.", '',
        'One batch call per arm/task; same schema/parser, sampling and visible PUTs, only guidance differs. All tasks including empty/invalid responses retained. Both arms use the original confirm-first-failures scorer, twice-run corrected reference and 3 s timeout.', '',
        'All inputs froze before evaluation. Source/input hashes, original-run immutability, imported response hashes and read-only replay passed. This previously used cohort is not a new held-out sample.', '',
        '| Task | Direct-only PUTs | Soft-only PUTs | Shared PUTs |', '|---|---|---|---|']
    for row in result['comparison']['tasks']:
        if not row.get('skip'):
            lines.append(f"| {row['task_id']} | {', '.join(row['direct_only']) or '—'} | {', '.join(row['soft_bva_only']) or '—'} | {', '.join(row['shared']) or '—'} |")
    (directory / 'REPORT.md').write_text('\n'.join(lines)+'\n')
    return result


def worker(directory):
    with (directory / '.worker.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with (directory / 'worker_started.json').open('x') as marker:
            json.dump({'pid': os.getpid(), 'automatic_restart': False}, marker)
        try:
            plan = read(directory / 'launch_plan.json')

            verify_saved_batches(directory, plan)
            frozen.configure_endpoint()
            model = frozen.QwenModel()
            endpoint_deadline = time.time()+21600
            while True:
                try:
                    endpoint = model.check_endpoint()
                    model.tokens([{'role':'user','content':'ping'}])
                    break
                except frozen.TransportError as error:
                    frozen.state(directory, 'waiting_endpoint', error=error.details(), new_model_calls=0)
                    unavailable = error.error_type in ('ExpectedModelMissing','ContextTooSmall')
                    if (not error.retryable and not unavailable) or time.time()>endpoint_deadline:
                        raise
                    time.sleep(30)
            save(directory / 'endpoint_readiness.json', {'checked_utc': time.time(), **endpoint})
            requests = read(directory / 'request_plan.json')['requests']

            frozen.generate(directory, plan, model, requests)
            frozen.state(directory, 'waiting_native_lock', writer_calls=frozen.call_usage(directory/'generation')['received'])
            with Path(plan['native_evaluation_lock']).open('a+') as native_lock:
                fcntl.flock(native_lock, fcntl.LOCK_EX)
                frozen.state(directory, 'running', phase='evaluation')
                summary = frozen.evaluate(directory, plan)
                if summary != frozen.evaluate(directory, plan, read_only=True):
                    raise ValueError('Immutable replay differs')

            result = finalize(directory, summary, plan)
            frozen.state(directory, 'complete', **result)
            print(json.dumps(result), flush=True)
        except BaseException as error:
            frozen.state(directory, 'interrupted', error_type=type(error).__name__,
                         error=error.details() if hasattr(error,'details') else str(error))
            raise


def launch(directory):
    plan = read(directory / 'launch_plan.json')
    environment = {key:os.environ[key] for key in ('HOME','LANG','LC_ALL','TZ','TMPDIR','FINAL_ENDPOINT_ENV_FILE') if key in os.environ}
    environment.update(PATH=os.defpath, PYTHONPATH=plan['runtime'], PYTHONDONTWRITEBYTECODE='1')
    with (directory / 'launch_reserved.json').open('x') as marker:
        json.dump({'automatic_restart':False}, marker)
    with (directory / 'runner.log').open('xb') as log:
        process = subprocess.Popen([sys.executable,'-P','-B','-u','-m','final.src.audits.resume_bva_batch',
            '--worker','--artifacts',str(directory)],cwd=ROOT,env=environment,stdin=subprocess.DEVNULL,
            stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    (directory / 'runner.pid').write_text(str(process.pid)+'\n')
    return process.pid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=Path('final/out/bva_batch_matched164_20261108_021740'))
    parser.add_argument('--artifacts',type=Path)
    parser.add_argument('--prepare-only',action='store_true')
    parser.add_argument('--worker',action='store_true')
    options = parser.parse_args()
    directory = (options.artifacts or Path('final/out/bva_batch_matched164_resume_'+dt.datetime.now().strftime('%Y%m%d_%H%M%S'))).resolve()
    if options.worker:
        worker(directory)
        return
    frozen.configure_endpoint()
    plan = prepare(options.source.resolve(),directory)
    result = {'artifacts':str(directory),'imported_received_calls':plan['imported_received_calls'],
              'remaining_logical_call_cap':plan['remaining_logical_call_cap']}
    if not options.prepare_only:
        result['pid'] = launch(directory)
    print(json.dumps(result),flush=True)


if __name__ == '__main__':
    main()
