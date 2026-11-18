"""Resume frozen Direct/Soft batch evaluation without model or tokenizer calls."""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

from .continue_bva_evaluation import read, save, checksum, digest
from .resume_bva_batch import inventory
from . import run_bva_batch as batch

ROOT = Path(__file__).resolve().parents[3]


def prepare(source, directory):
    source, directory = Path(source).resolve(), Path(directory).resolve()
    if directory.exists():
        raise ValueError('Use a fresh evaluation continuation directory')
    with (source / '.worker.lock').open('r') as worker_lock, (source / 'evaluation/.run.lock').open('r') as evaluation_lock:
        for lock in (worker_lock, evaluation_lock):
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if read(source / 'status.json')['state'] != 'interrupted':
            raise ValueError('Source evaluation is not stopped')

        original_files = inventory(source)
        generation = source / 'generation'
        manifest = read(generation / 'modular_manifest.json')
        evaluation_manifest = read(source / 'evaluation/modular_manifest.json')
        freeze = read(generation / 'generation_frozen.json')
        requests = read(source / 'request_plan.json')['requests']
        usage = batch.call_usage(generation)
        if usage['received'] != len(requests):
            raise ValueError('Evaluation-only continuation requires every planned response')
        if evaluation_manifest['python'] != platform.python_version():
            raise ValueError('Python version differs from frozen generation')
        for name, version in evaluation_manifest['packages'].items():
            if importlib.metadata.version(name) != version:
                raise ValueError('Dependency version differs: ' + name)
        if (digest(freeze['inputs']) != freeze['inputs_sha256']
                or set(freeze['inputs']) != set(manifest['tasks'])):
            raise ValueError('Frozen task ledger differs')
        for task, expected in freeze['inputs'].items():
            if digest(read(generation / 'tasks' / task.split('/')[-1] / 'inputs.json')) != expected:
                raise ValueError('Frozen input changed: ' + task)
        plan = read(source / 'launch_plan.json')
        if (plan['settings'] != manifest['settings'] or plan['settings'] != evaluation_manifest['settings']
                or [arm['name'] for arm in manifest['arms']] != ['direct', 'soft_bva']):
            raise ValueError('Paired generation/evaluation settings or arms differ')
        directory.mkdir(parents=True)
        runtime = directory / 'runtime'
        shutil.copytree(source / 'runtime', runtime, ignore=shutil.ignore_patterns('__pycache__'))
        changes = []
        for name in ('execution.py', 'worker.py'):
            target = runtime / 'final/src/runtime' / name
            original_hash = checksum(target)
            target.chmod(0o644)
            shutil.copyfile(ROOT / 'final/src/runtime' / name, target)
            changes.append({'path': str(target.relative_to(runtime)), 'before': original_hash, 'after': checksum(target)})
        controller = runtime / 'final/src/audits/resume_bva_batch_evaluation.py'
        shutil.copyfile(__file__, controller)
        shutil.copytree(generation, directory / 'generation')
        for name in ('request_plan.json', 'generation_usage.json'):
            shutil.copyfile(source / name, directory / name)
        receipts = []
        for task_directory in (source / 'evaluation/tasks').iterdir():
            paths = list(task_directory.glob('oracle*.json')) + list(task_directory.glob('result.json'))
            paths += list((task_directory / 'evaluation').glob('*.json'))
            for path in paths:
                target = directory / 'evaluation' / path.relative_to(source / 'evaluation')
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
                receipts.append({'source': str(path), 'destination': str(target), 'sha256': checksum(path)})
        new_plan = {**plan, 'runtime': str(runtime),
            'cohort': str(runtime / Path(plan['cohort']).relative_to(source / 'runtime')),
            'continuation_source': str(source), 'new_model_calls': 0,
            'tasks': manifest['tasks'], 'runtime_changes': changes,
            'imported_task_results': len(list((source / 'evaluation/tasks').glob('*/result.json'))),
            'native_evaluation_lock': plan['native_evaluation_lock'],
            'recovery_policy': 'frozen inputs and scorer; single-input C timeout fallback; preserve native checkpoints'}
        save(directory / 'launch_plan.json', new_plan)
        save(directory / 'import_receipts.json', {'source_files': original_files, 'checkpoints': receipts,
            'writer_usage': usage, 'new_model_calls': 0,
            'provenance_policy': 'reference_program path rebuilt; oracle values and native results preserved'})
        shutil.copyfile(ROOT / 'final/src/modular/PREREG.md', directory / 'PREREG.md')
        sources = dict(original_files)
        for path in runtime.rglob('*'):
            if path.is_file():
                path.chmod(0o444)
                sources[str(path)] = checksum(path)
        for path in (directory / 'generation').rglob('*'):
            if path.is_file():
                sources[str(path)] = checksum(path)
        for receipt in receipts:
            sources[receipt['destination']] = receipt['sha256']
        for name in ('launch_plan.json', 'import_receipts.json', 'request_plan.json', 'generation_usage.json', 'PREREG.md'):
            sources[str(directory / name)] = checksum(directory / name)
        save(directory / 'source_snapshot.json', {'sources': sources, 'archive': {}})
        if inventory(source) != original_files:
            raise ValueError('Preparation changed original source')
        save(directory / 'status.json', {'state': 'prepared', 'new_model_calls': 0,
            'imported_task_results': new_plan['imported_task_results']})
        return new_plan


def render_report(result, plan):
    comparison = result['comparison']['detections']
    values = result['comparison']['stable_wrong_values']
    lines = ['# Kết quả full batch: Direct và Soft BVA', '',
        f"Trên {result['evaluated_base_pass']} PUT vượt base tests, Direct phát hiện thêm lỗi ở **{comparison['direct']} PUT**, Soft BVA ở **{comparison['soft_bva']} PUT**.", '',
        'Đây là cohort đã dùng trong các phân tích trước, không phải held-out sample mới. Số PUT phát hiện lỗi không phải detection rate trên tập bug đã biết.', '',
        '| Metric | Direct | Soft BVA |', '|---|---:|---:|',
        f"| PUT phát hiện thêm lỗi | {comparison['direct']} | {comparison['soft_bva']} |",
        f"| Input mới hợp lệ | {result['arms']['direct']['valid_inputs']} | {result['arms']['soft_bva']['valid_inputs']} |",
        f"| Task có phát hiện lỗi | {result['arms']['direct']['tasks_detected']} | {result['arms']['soft_bva']['tasks_detected']} |",
        f"| PUT có stable wrong-value witness | {values['direct']} | {values['soft_bva']} |", '',
        f"Hai arm cùng bắt {comparison['shared']} PUT; Direct-only {comparison['direct_only']}; Soft-only {comparison['soft_bva_only']}. Chênh lệch Soft − Direct: {comparison['net_soft_minus_direct']:+d} PUT.", '',
        f"Config: {len(plan['tasks'])} task được yêu cầu; input budget {plan['settings']['input_budget']}/task/arm; 1 call/task/arm, cùng batch gồm tối đa 10 PUT (có thể ít hơn do base pass/context budget). Hai arm dùng cùng packet, parser, sampling và scorer; Soft thêm boundary guidance.",
        f"Sampling: temperature {plan['settings']['input_temperature']}, max output tokens {plan['settings']['input_tokens']}/call, context {plan['settings']['context_tokens']}; input seed {plan['settings']['input_seed']} + task number, reference seed {plan['settings']['reference_seed']} + task number.",
        f"Evaluation: timeout {plan['settings']['timeout_seconds']} s/input; corrected reference chạy 2 lần; confirm-first-failures-v1 chỉ xác nhận lại fail/error/timeout. Timeout/error được tính trong tổng detection và tách khỏi stable wrong-value witness.", '',
        'Recovery: giữ input và response cũ, dùng lại native checkpoints. Thêm hard timeout cho C call không xử lý được SIGALRM; startup hang vẫn là infrastructure error. Cả hai arm dùng cùng executor đã sửa. Thay đổi runtime khiến cache key mới tự tách khỏi cache cũ; các checkpoint hoàn chỉnh được giữ nguyên.',
        f"Model calls mới trong evaluation này: **0**. Writer usage gốc (chỉ tính một lần): `{result['writer_usage']}`. Có unknown attempt lịch sử nên known tokens không phải tổng tuyệt đối.",
        f"Skip: `{result['skips']}`.",
        'Đã kiểm tra source/input/response hashes, source run không đổi và immutable replay khớp.', '',
        f"Source run: `{plan['continuation_source']}`", '',
        '| Task | Direct-only PUTs | Soft-only PUTs | Shared PUTs |', '|---|---|---|---|']
    for row in result['comparison']['tasks']:
        if not row.get('skip'):
            lines.append(f"| {row['task_id']} | {', '.join(row['direct_only']) or '—'} | {', '.join(row['soft_bva_only']) or '—'} | {', '.join(row['shared']) or '—'} |")
    return '\n'.join(lines) + '\n'


def worker(directory):
    from final.src.runtime.execution import execute
    with (directory / '.worker.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with (directory / 'worker_started.json').open('x') as marker:
            json.dump({'pid': os.getpid(), 'new_model_calls': 0}, marker)
        try:
            plan = read(directory / 'launch_plan.json')


            for expected, status in (('1', 'pass'), ('2', 'fail')):
                outcome = execute({'mode': 'evaluate', 'context': 'def f(x):\n    pass\n',
                    'source': 'def f(x): return x', 'entry': 'f', 'timeout': 3,
                    'tests': [{'args': '(1,)', 'kwargs': '{}', 'expected': expected}], 'atol': 0})
                if outcome['tests'][0]['status'] != status:
                    raise RuntimeError('Native sandbox/NumPy smoke failed')
            save(directory / 'sandbox_readiness.json', {'identity_pass': True, 'wrong_value_fail': True,
                'python_executable': sys.executable, 'new_model_calls': 0})
            save(directory / 'status.json', {'state': 'running', 'phase': 'evaluation_only',
                'pid': os.getpid(), 'new_model_calls': 0, 'imported_task_results': plan['imported_task_results']})
            summary = batch.evaluate(directory, plan)
            if batch.evaluate(directory, plan, read_only=True) != summary:
                raise ValueError('Immutable replay differs')

            receipts = read(directory / 'import_receipts.json')
            if inventory(Path(plan['continuation_source'])) != receipts['source_files']:
                raise ValueError('Original interrupted run changed')
            if batch.call_usage(directory / 'generation') != receipts['writer_usage']:
                raise ValueError('Generation usage changed during evaluation')
            result = {'arms': summary['arms'], 'evaluated_base_pass': summary['evaluated_base_pass'],
                'requested_tasks': len(plan['tasks']), 'skips': summary['skips'],
                'writer_usage': receipts['writer_usage'], 'new_model_calls': 0,
                'comparison': batch.paired_verdicts(directory / 'evaluation'),
                'read_only_replay_matches': True, 'source_hashes_verified': None,
                'original_run_unchanged': True, 'imported_responses_unchanged': True,
                'continuation_source': plan['continuation_source']}
            save(directory / 'result_digest.json', result)
            (directory / 'REPORT.md').write_text(render_report(result, plan))
            save(directory / 'status.json', {'state': 'complete', 'pid': os.getpid(),
                'finished_utc': time.time(), 'new_model_calls': 0})
            print(json.dumps(result, ensure_ascii=False), flush=True)
        except BaseException as error:
            save(directory / 'status.json', {'state': 'interrupted', 'pid': os.getpid(),
                'new_model_calls': 0, 'error_type': type(error).__name__, 'error': str(error)})
            raise


def launch(directory):
    plan = read(directory / 'launch_plan.json')
    environment = {key: os.environ[key] for key in ('HOME', 'LANG', 'LC_ALL', 'TZ', 'TMPDIR') if key in os.environ}
    environment.update(PATH=os.defpath, PYTHONPATH=plan['runtime'], PYTHONDONTWRITEBYTECODE='1')
    with (directory / 'launch_reserved.json').open('x') as marker:
        json.dump({'automatic_restart': False, 'new_model_calls': 0}, marker)
    with (directory / 'runner.log').open('xb') as log:
        command = ['/usr/bin/flock', '--no-fork', plan['native_evaluation_lock'], sys.executable,
            '-P', '-B', '-u', '-m', 'final.src.audits.resume_bva_batch_evaluation', '--worker',
            '--artifacts', str(directory)]
        process = subprocess.Popen(command, cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    (directory / 'runner.pid').write_text(str(process.pid) + '\n')
    return process.pid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-run', type=Path)
    parser.add_argument('--artifacts', type=Path)
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    options = parser.parse_args()
    directory = (options.artifacts or ROOT / ('final/out/bva_batch_matched164_evaluation_' + dt.datetime.now().strftime('%Y%m%d_%H%M%S'))).resolve()
    if options.worker:
        worker(directory)
    else:
        plan = prepare(options.source_run, directory)
        receipt = {'artifacts': str(directory), 'imported_task_results': plan['imported_task_results'],
            'received_responses': read(directory / 'generation_usage.json')['received'], 'new_model_calls': 0}
        if not options.prepare_only:
            receipt['pid'] = launch(directory)
        print(json.dumps(receipt), flush=True)


if __name__ == '__main__':
    main()
