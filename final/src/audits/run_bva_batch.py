"""Scheduled full-cohort Direct/Soft BVA comparison with one batch call per arm/task."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from final.src.modular.arms.batch import DirectBatchArm, SoftBvaBatchArm
from final.src.modular.artifacts import ArtifactStore
from final.src.modular.calls import RecordedModelCalls
from final.src.modular.cohort import load_cohort, call_usage
from final.src.modular.context import PipelineSettings, TaskContext
from final.src.modular.dataset import load_tasks, load_metadata
from final.src.modular.execution_cache import InputExecutionCache
from final.src.modular.generators.frozen import FrozenInputsGenerator
from final.src.modular.stages.input_preparation import InputPreparationStage
from final.src.runtime.keepalive import KeepAlive
from final.src.runtime.model import QwenModel, TransportError
from .continue_bva_evaluation import read, save, digest, checksum
from .run_bva_full import SourceGuard, ProgressPipeline
from .run_prompt_style import configure_endpoint
from .run_bva_precision import evaluation_observations


ROOT = Path(__file__).resolve().parents[3]
ARMS = (DirectBatchArm(), SoftBvaBatchArm())


def wait_until_deadline(directory, deadline):
    while time.time() < deadline:
        state(directory, 'scheduled', not_before_utc_epoch=deadline, new_model_calls=0)
        remaining = deadline - time.time()
        if remaining > 0:
            time.sleep(min(30, remaining))


def keepalive_usage(directory):
    records = [read(path) for path in (directory / 'keepalive').glob('*.json')]
    return {'records': len(records), 'received': sum(row['state'] == 'received' for row in records),
            'unknown': sum(row['state'] not in ('received', 'not_sent') for row in records),
            'not_sent': sum(row['state'] == 'not_sent' for row in records),
            'known_total_tokens': sum(row.get('usage', {}).get('total_tokens', 0) for row in records)}


def paired_verdicts(evaluation_directory):
    detected = {arm.name: set() for arm in ARMS}
    stable_values = {arm.name: set() for arm in ARMS}
    rows, witnesses = [], []
    task_wins = {'direct': 0, 'soft_bva': 0, 'tie': 0}
    for path in sorted(evaluation_directory.glob('tasks/*/result.json')):
        result = read(path)
        if result.get('skip'):
            rows.append({'task_id': result['task_id'], 'skip': result['skip']})
            continue
        sets = {arm.name: set(result['arms'][arm.name]['detected_put_ids']) for arm in ARMS}
        for arm in ARMS:
            detected[arm.name].update((result['task_id'], put) for put in sets[arm.name])
        row = {'task_id': result['task_id'], 'shared': sorted(sets['direct'] & sets['soft_bva']),
               'direct_only': sorted(sets['direct'] - sets['soft_bva']),
               'soft_bva_only': sorted(sets['soft_bva'] - sets['direct']),
               'valid_inputs': {arm.name: result['arms'][arm.name]['valid_inputs'] for arm in ARMS}}
        task_wins['direct' if len(sets['direct']) > len(sets['soft_bva']) else
                  'soft_bva' if len(sets['soft_bva']) > len(sets['direct']) else 'tie'] += 1
        rows.append(row)
        oracle = read(path.parent / 'oracle_valid.json')
        for put in sets['direct'] | sets['soft_bva']:
            observations = evaluation_observations(path.parent, put, result['outcomes'][put])
            for arm in ARMS:
                failures = set(result['arm_indices'][arm.name]) & set(result['outcomes'][put]['failing'])
                for index in failures:
                    observed = observations[index]
                    if len(observed) == 2 and all(item['status'] == 'fail' for item in observed):
                        stable_values[arm.name].add((result['task_id'], put))
                if put in sets[arm.name] - sets['soft_bva' if arm.name == 'direct' else 'direct']:
                    index = min(failures)
                    witnesses.append({'task_id': result['task_id'], 'put_id': put, 'arm': arm.name,
                                      'input': oracle['tests'][index], 'observations': observations[index]})
    def counts(sets):
        left, right = sets['direct'], sets['soft_bva']
        return {'direct': len(left), 'soft_bva': len(right), 'shared': len(left & right),
                'direct_only': len(left-right), 'soft_bva_only': len(right-left), 'union': len(left | right),
                'net_soft_minus_direct': len(right)-len(left)}
    return {'detections': counts(detected), 'stable_wrong_values': counts(stable_values),
            'task_wins_by_detected_put_count': task_wins, 'tasks': rows, 'unique_witnesses': witnesses}


def state(directory, name, **details):
    save(directory / 'status.json', {'state': name, 'pid': os.getpid(), 'updated_utc': time.time(), **details})


def prepare_run(directory, not_before, review_receipt):
    if directory.exists():
        raise ValueError('Use a new batch output directory')
    receipt = read(review_receipt)
    if receipt.get('must_fixes_remaining') or not receipt.get('tests_passed') or not receipt.get('review_passed'):
        raise ValueError('Independent review and tests must pass before scheduling')
    for name, expected in receipt['reviewed_sources'].items():
        if checksum(name) != expected:
            raise ValueError('Reviewed source changed: ' + name)
    directory.mkdir(parents=True)
    runtime = directory / 'runtime'
    hashes = {}
    paths = [path for path in (ROOT / 'final/src').rglob('*.py') if 'tests' not in path.parts]
    paths += [ROOT / 'final/__init__.py', ROOT / 'final/data/humaneval.jsonl', ROOT / 'final/data/contracts.json',
              ROOT / 'final/data/humanevalplus_v0.1.10_references.json']
    for source in paths:
        target = runtime / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        target.chmod(0o444)
        hashes[str(target)] = checksum(target)
    cohort = runtime / 'cohort.json'
    shutil.copyfile(ROOT / 'final/out/cohorts/qwen35_27b_humaneval164/cohort.json', cohort)
    cohort.chmod(0o444)
    hashes[str(cohort)] = checksum(cohort)
    settings = PipelineSettings()
    eligible, skips = [], []
    for row in load_cohort(cohort)['tasks']:
        if row['generated'] != settings.target_programs:
            skips.append({'task_id': row['task_id'], 'reason': 'generation_shortfall'})
        elif not any(program['base']['status'] == 'pass' for program in row['programs']):
            skips.append({'task_id': row['task_id'], 'reason': 'no_base_pass'})
        else:
            eligible.append(row['task_id'])
    save(directory / 'launch_plan.json', {'runtime': str(runtime), 'cohort': str(cohort), 'settings': asdict(settings),
        'not_before_utc_epoch': not_before, 'eligible_tasks': eligible, 'cohort_skips': skips,
        'logical_call_cap': 2 * len(eligible), 'arms': [arm.name for arm in ARMS],
        'native_evaluation_lock': str(ROOT / 'final/out/.boundary_native.lock'),
        'execution_cache': str(ROOT / 'final/out/execution_cache'),
        'policy': 'same-packet/same-builder/same-parser/one-call-per-task; only guidance differs'})
    shutil.copyfile(review_receipt, directory / 'review_receipt.json')
    shutil.copyfile(ROOT / 'final/src/modular/PREREG.md', directory / 'PREREG.md')
    for name in ('launch_plan.json', 'review_receipt.json', 'PREREG.md'):
        hashes[str(directory / name)] = checksum(directory / name)
    save(directory / 'source_snapshot.json', {'sources': hashes, 'archive': {}})
    save(directory / 'ready_to_launch.json', {'tests_passed': True, 'review_passed': True,
        'source_snapshot_sha256': checksum(directory / 'source_snapshot.json')})
    state(directory, 'scheduled', not_before_utc_epoch=not_before, new_model_calls=0)
    return read(directory / 'launch_plan.json')


def prepare_packets(directory, plan, model):
    """Tokenize both arms before selecting one common visibility set; no completions."""
    tasks, metadata = load_tasks(), load_metadata()
    cohort = {row['task_id']: row for row in load_cohort(Path(plan['cohort']))['tasks']}
    settings = PipelineSettings(**plan['settings'])
    source = directory / 'generation'
    requests, readiness = {}, []
    skips = {row['task_id']: row['reason'] for row in plan['cohort_skips']}
    class Tokenizer:
        def token_count(self, messages):
            return model.tokens(messages)
    for task in tasks:
        number = int(task['task_id'].split('/')[-1])
        context = TaskContext(task, metadata[task['task_id']], ArtifactStore(source), settings, Tokenizer())
        context.cohort_task = cohort[task['task_id']]
        packet = InputPreparationStage(ARMS).prepare(context)
        save(source / 'tasks' / str(number) / 'packet.json', packet)
        if task['task_id'] in skips:
            save(source / 'tasks' / str(number) / 'inputs.json', {'task_id': task['task_id'], 'skip': skips[task['task_id']]})
            continue
        if packet.get('skip'):
            # Keep all eligible targets in evaluation even when neither arm can fit.
            save(source / 'tasks' / str(number) / 'inputs.json', {'task_id': task['task_id'], 'arms': {
                arm.name: {'inputs': [], 'rejected': [], 'status': 'prompt_too_large'} for arm in ARMS}})
            readiness.append({'task_id': task['task_id'], 'skip': packet['skip']})
            continue
        for arm in ARMS:
            request = {'messages': arm.build_messages(packet), 'temperature': settings.input_temperature,
                       'max_tokens': settings.input_tokens, 'seed': settings.input_seed + number}
            requests[f'{number}/{arm.name}'] = {'request_sha256': digest(request), 'request': request}
        readiness.append({'task_id': task['task_id'], 'visible_put_ids': packet['visible_put_ids'],
            'all_base_pass_put_count': sum(program['base']['status'] == 'pass' for program in context.cohort_task['programs']),
            'prompt_tokens': packet['prompt_tokens']})
    save(directory / 'request_plan.json', {'requests': requests, 'readiness': readiness,
        'visibility_selected_before_completion': True, 'logical_calls': len(requests)})
    snapshot = read(directory / 'source_snapshot.json')
    snapshot['sources'][str(directory / 'request_plan.json')] = checksum(directory / 'request_plan.json')
    for path in source.glob('tasks/*/packet.json'):
        snapshot['sources'][str(path)] = checksum(path)
    save(directory / 'source_snapshot.json', snapshot)
    return requests


class RegisteredCalls(RecordedModelCalls):
    def __init__(self, model, artifacts, guard, requests):
        super().__init__(model, artifacts)
        self.guard, self.requests = guard, requests

    def complete(self, task_number, call_name, messages, *, temperature, max_tokens, seed):
        self.guard.verify()
        request = {'messages': messages, 'temperature': temperature, 'max_tokens': max_tokens, 'seed': seed}
        if digest(request) != self.requests[f'{task_number}/{call_name}']['request_sha256']:
            raise ValueError('Unregistered batch request')
        return super().complete(task_number, call_name, messages, temperature=temperature, max_tokens=max_tokens, seed=seed)


def generate(directory, plan, model, requests):
    source = directory / 'generation'
    settings = PipelineSettings(**plan['settings'])
    guard = SourceGuard(directory)
    calls = RegisteredCalls(model, ArtifactStore(source), guard, requests)
    metadata = load_metadata()
    for task in load_tasks():
        number = int(task['task_id'].split('/')[-1])
        path = source / 'tasks' / str(number) / 'inputs.json'
        if path.exists():
            continue
        context = TaskContext(task, metadata[task['task_id']], ArtifactStore(source), settings, calls)
        context.packet = read(source / 'tasks' / str(number) / 'packet.json')
        batches = {}
        order = ARMS if number % 2 == 0 else tuple(reversed(ARMS))
        for arm in order:
            state(directory, 'running', phase='generation', task=number, arm=arm.name)
            batches[arm.name] = arm.run(context)
        save(path, {'task_id': task['task_id'], 'arms': {arm.name: batches[arm.name] for arm in ARMS}})
    ledger = {task['task_id']: digest(read(source / 'tasks' / task['task_id'].split('/')[-1] / 'inputs.json'))
              for task in load_tasks()}
    cohort_sha = load_cohort(Path(plan['cohort']))['cohort_sha256']
    save(source / 'generation_frozen.json', {'cohort_sha256': cohort_sha, 'inputs': ledger, 'inputs_sha256': digest(ledger)})
    save(source / 'modular_manifest.json', {'protocol': 'matched-batch-inputs-v1', 'model': model.model_id,
        'settings': plan['settings'], 'cohort_sha256': cohort_sha, 'tasks': list(ledger),
        'arms': [{'name': arm.name} for arm in ARMS]})
    snapshot = read(directory / 'source_snapshot.json')
    for path in [*source.glob('tasks/*/inputs.json'), *source.glob('tasks/*/calls/*/*.json'),
                 source / 'generation_frozen.json', source / 'modular_manifest.json']:
        snapshot['sources'][str(path)] = checksum(path)
    save(directory / 'source_snapshot.json', snapshot)
    usage = call_usage(source)
    if usage['received'] != len(requests) or usage['received'] > plan['logical_call_cap']:
        raise ValueError('Paired call count mismatch')
    save(directory / 'generation_usage.json', usage)


def evaluate(directory, plan, *, read_only=False):
    output = directory / 'evaluation'
    cache = InputExecutionCache(Path(plan['execution_cache']), read_only=read_only)
    pipeline = ProgressPipeline(Path(plan['cohort']), ArtifactStore(output, read_only=read_only),
        input_generator=FrozenInputsGenerator(directory / 'generation', methods=ARMS),
        settings=PipelineSettings(**plan['settings']), execution_cache=cache, guard=SourceGuard(directory))
    return pipeline.run(load_tasks(), load_metadata())


def worker(directory):
    with (directory / '.worker.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with (directory / 'worker_started.json').open('x') as marker:
            json.dump({'pid': os.getpid(), 'automatic_restart': False}, marker)
        try:
            plan = read(directory / 'launch_plan.json')
            readiness = read(directory / 'ready_to_launch.json')
            if readiness != {'tests_passed': True, 'review_passed': True,
                             'source_snapshot_sha256': checksum(directory / 'source_snapshot.json')}:
                raise ValueError('Readiness gate changed')
            SourceGuard(directory).verify()
            wait_until_deadline(directory, plan['not_before_utc_epoch'])
            SourceGuard(directory).verify()
            configure_endpoint()
            model = QwenModel()
            endpoint_deadline = time.time() + 21600
            while True:
                try:
                    endpoint = model.check_endpoint()
                    break
                except TransportError as error:
                    state(directory, 'waiting_endpoint', error=error.details(), new_model_calls=0)
                    unavailable_model = error.error_type in ('ExpectedModelMissing', 'ContextTooSmall')
                    if (not error.retryable and not unavailable_model) or time.time() > endpoint_deadline:
                        raise
                    time.sleep(30)
            save(directory / 'endpoint_readiness.json', {'checked_utc': time.time(), **endpoint})
            requests = prepare_packets(directory, plan, model)
            SourceGuard(directory).verify()
            with KeepAlive(directory):
                generate(directory, plan, model, requests)
            state(directory, 'waiting_native_lock', new_writer_calls=call_usage(directory / 'generation')['received'])
            with Path(plan['native_evaluation_lock']).open('a+') as native_lock:
                fcntl.flock(native_lock, fcntl.LOCK_EX)
                state(directory, 'running', phase='evaluation')
                summary = evaluate(directory, plan)
                if summary != evaluate(directory, plan, read_only=True):
                    raise ValueError('Immutable replay mismatch')
            SourceGuard(directory).verify()
            result = {'arms': summary['arms'], 'evaluated_base_pass': summary['evaluated_base_pass'],
                'writer_usage': read(directory / 'generation_usage.json'), 'keepalive_usage': keepalive_usage(directory),
                'comparison': paired_verdicts(directory / 'evaluation'),
                'read_only_replay_matches': True, 'source_hashes_verified': True}
            save(directory / 'result_digest.json', result)
            comparison = result['comparison']['detections']
            report = ['# Matched batch Direct versus Soft BVA', '',
                'One new batch call per arm/task; same packet, schema, encoder, parser, sampling and scorer. Only the soft BVA guidance differs.', '',
                '| Metric | Direct | Soft BVA |', '|---|---:|---:|',
                f"| Detected PUTs | {comparison['direct']} | {comparison['soft_bva']} |",
                f"| Novel valid inputs | {summary['arms']['direct']['valid_inputs']} | {summary['arms']['soft_bva']['valid_inputs']} |",
                f"| Tasks with detection | {summary['arms']['direct']['tasks_detected']} | {summary['arms']['soft_bva']['tasks_detected']} |", '',
                f"Shared: {comparison['shared']}; Direct-only: {comparison['direct_only']}; Soft-only: {comparison['soft_bva_only']}; net Soft-minus-Direct: {comparison['net_soft_minus_direct']:+d}.", '',
                f"Task-level wins by detected PUT count: {result['comparison']['task_wins_by_detected_put_count']}.",
                f"Stable wrong-value witnesses: {result['comparison']['stable_wrong_values']}.", '',
                f"Writer usage: {result['writer_usage']}. Keepalive usage is separate: {result['keepalive_usage']}.", '',
                'All eligible tasks, including invalid or empty writer outputs, remain in the primary comparison. Both arms use confirm-first-failures-v1, corrected twice-run reference and a 3 s timeout. Historical packaging diagnostic uses the original full-two-repeat scorer; its totals are not a prompt-only comparison to these new arms.', '',
                'Input freezes, source/data hashes and immutable replay passed. Exact per-task sets and unique witnesses are in result_digest.json.', '',
                '| Task | Direct-only PUTs | Soft-only PUTs | Shared PUTs |', '|---|---|---|---|']
            for row in result['comparison']['tasks']:
                if not row.get('skip'):
                    report.append(f"| {row['task_id']} | {', '.join(row['direct_only']) or '—'} | {', '.join(row['soft_bva_only']) or '—'} | {', '.join(row['shared']) or '—'} |")
            (directory / 'REPORT.md').write_text('\n'.join(report) + '\n')
            state(directory, 'complete', **result)
            print(json.dumps(result), flush=True)
        except BaseException as error:
            state(directory, 'interrupted', error_type=type(error).__name__,
                  error=error.details() if hasattr(error, 'details') else str(error))
            raise


def launch(directory):
    plan = read(directory / 'launch_plan.json')
    environment = {key: os.environ[key] for key in ('HOME', 'LANG', 'LC_ALL', 'TZ', 'TMPDIR', 'FINAL_ENDPOINT_ENV_FILE') if key in os.environ}
    environment.update(PATH=os.defpath, PYTHONPATH=plan['runtime'], PYTHONDONTWRITEBYTECODE='1')
    with (directory / 'launch_reserved.json').open('x') as marker:
        json.dump({'automatic_restart': False}, marker)
    with (directory / 'runner.log').open('xb') as log:
        process = subprocess.Popen([sys.executable, '-P', '-B', '-u', '-m', 'final.src.audits.run_bva_batch',
            '--worker', '--artifacts', str(directory)], cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    (directory / 'runner.pid').write_text(str(process.pid) + '\n')
    return process.pid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--not-before-utc', help='ISO UTC time; no network or completion before this deadline')
    parser.add_argument('--review-receipt', type=Path)
    parser.add_argument('--worker', action='store_true')
    options = parser.parse_args()
    directory = options.artifacts.resolve()
    if options.worker:
        worker(directory)
        return
    if not options.not_before_utc or not options.review_receipt:
        parser.error('--not-before-utc and --review-receipt are required')
    deadline = dt.datetime.fromisoformat(options.not_before_utc.replace('Z', '+00:00')).timestamp()
    plan = prepare_run(directory, deadline, options.review_receipt.resolve())
    print(json.dumps({'artifacts': str(directory), 'pid': launch(directory), 'logical_call_cap': plan['logical_call_cap'],
                     'not_before_utc_epoch': deadline}), flush=True)


if __name__ == '__main__':
    main()
