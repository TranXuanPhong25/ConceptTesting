"""Re-parse saved Direct/Soft batch responses with the literal-fallback parser and rescore.

No model or tokenizer call. The saved responses of a completed matched-batch run
are decoded again with the current batch-arm parser (strict JSON, then a Python
literal fallback). Tasks whose inputs do not change keep their native evaluation
checkpoints; only changed tasks are evaluated again. The source run stays unchanged.
"""
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
from types import SimpleNamespace

from .continue_bva_evaluation import read, save, checksum, digest
from .resume_bva_batch import inventory
from . import run_bva_batch as batch

ROOT = Path(__file__).resolve().parents[3]
CHANGED_SOURCES = ('final/src/modular/arms/base.py', 'final/src/modular/response_json.py',
                   'final/src/audits/reparse_bva_batch.py', 'final/src/audits/detection_kinds.py')


class ReplayCalls:
    """Return the saved response after checking the request equals the saved request."""

    def __init__(self, call_directory):
        self.request = read(call_directory / 'request.json')
        self.response = read(call_directory / 'response.json')

    def complete(self, task_number, call_name, messages, *, temperature, max_tokens, seed):
        replayed = {'messages': messages, 'temperature': temperature, 'max_tokens': max_tokens, 'seed': seed}
        if digest(replayed) != digest(self.request):
            raise ValueError(f'Request differs from saved request: {task_number}/{call_name}')
        from final.src.models.core_model import ModelResponse
        return ModelResponse(self.response['text'], usage=self.response.get('usage', {}),
                             finish_reason=self.response.get('finish_reason'))


def reparse_task(task, packet, settings, generation, original):
    """Return new arm batches for one task, or the original record when not model-generated."""
    if original.get('skip') or any(row.get('status') == 'prompt_too_large' for row in original['arms'].values()):
        return original
    number = int(task['task_id'].split('/')[-1])
    batches = {}
    for arm in batch.ARMS:
        calls = ReplayCalls(generation / 'tasks' / str(number) / 'calls' / arm.name)
        context = SimpleNamespace(task=task, task_number=number, packet=packet, calls=calls, settings=settings)
        batches[arm.name] = arm.run(context)
    return {'task_id': task['task_id'], 'arms': batches}


def prepare(source, directory):
    from final.src.modular.context import PipelineSettings
    from final.src.modular.dataset import load_tasks
    source, directory = Path(source).resolve(), Path(directory).resolve()
    if directory.exists():
        raise ValueError('Use a fresh output directory')
    if read(source / 'status.json')['state'] != 'complete':
        raise ValueError('Source run must be complete')
    original_files = inventory(source)
    plan = read(source / 'launch_plan.json')
    settings = PipelineSettings(**plan['settings'])
    directory.mkdir(parents=True)

    runtime = directory / 'runtime'
    shutil.copytree(source / 'runtime', runtime, ignore=shutil.ignore_patterns('__pycache__'))
    runtime_changes = []
    for relative in CHANGED_SOURCES:
        target = runtime / relative
        before = checksum(target) if target.exists() else None
        if target.exists():
            target.chmod(0o644)
        shutil.copyfile(ROOT / relative, target)
        runtime_changes.append({'path': relative, 'before': before, 'after': checksum(target)})

    shutil.copytree(source / 'generation', directory / 'generation')
    generation = directory / 'generation'
    reparse_rows, changed_tasks = [], []
    for task in load_tasks():
        number = task['task_id'].split('/')[-1]
        inputs_path = generation / 'tasks' / number / 'inputs.json'
        original = read(inputs_path)
        packet = read(generation / 'tasks' / number / 'packet.json')
        updated = reparse_task(task, packet, settings, source / 'generation', original)
        repairs = {name: row.get('response_repairs', []) for name, row in updated.get('arms', {}).items()}
        if updated != original:
            if not any(repairs.values()):
                raise ValueError('Inputs changed without a recorded response repair: ' + task['task_id'])
            save(inputs_path, updated)
            changed_tasks.append(task['task_id'])
        row = {'task_id': task['task_id'], 'changed': updated != original}
        for name, arm_row in updated.get('arms', {}).items():
            row[name] = {'valid_before': len(original['arms'][name]['inputs']),
                         'valid_after': len(arm_row['inputs']), 'response_repairs': arm_row.get('response_repairs', [])}
        reparse_rows.append(row)
    ledger = {task['task_id']: digest(read(generation / 'tasks' / task['task_id'].split('/')[-1] / 'inputs.json'))
              for task in load_tasks()}
    frozen = read(generation / 'generation_frozen.json')
    save(generation / 'generation_frozen.json', {**frozen, 'inputs': ledger, 'inputs_sha256': digest(ledger)})
    manifest = read(generation / 'modular_manifest.json')
    save(generation / 'modular_manifest.json', {**manifest, 'protocol': 'matched-batch-inputs-v1+literal-fallback-reparse'})

    receipts = []
    for task_directory in (source / 'evaluation/tasks').iterdir():
        task_id = 'HumanEval/' + task_directory.name
        if task_id in changed_tasks:
            continue
        paths = list(task_directory.glob('oracle*.json')) + list(task_directory.glob('result.json'))
        paths += list((task_directory / 'evaluation').glob('*.json'))
        for path in paths:
            target = directory / 'evaluation' / path.relative_to(source / 'evaluation')
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            receipts.append({'source': str(path), 'destination': str(target), 'sha256': checksum(path)})

    for name in ('request_plan.json', 'generation_usage.json'):
        shutil.copyfile(source / name, directory / name)
    new_plan = {**plan, 'runtime': str(runtime),
        'cohort': str(runtime / Path(plan['cohort']).relative_to(source / 'runtime')),
        'continuation_source': str(source), 'new_model_calls': 0, 'tasks': manifest['tasks'],
        'runtime_changes': runtime_changes, 'reparsed_changed_tasks': changed_tasks,
        'imported_task_results': len(list((directory / 'evaluation/tasks').glob('*/result.json'))),
        'recovery_policy': 'saved responses re-parsed with literal fallback; unchanged tasks keep native checkpoints'}
    save(directory / 'launch_plan.json', new_plan)
    save(directory / 'reparse_receipts.json', {'tasks': reparse_rows, 'changed_tasks': changed_tasks,
        'new_model_calls': 0, 'source_response_count': batch.call_usage(source / 'generation')['received']})
    save(directory / 'import_receipts.json', {'source_files': original_files, 'checkpoints': receipts,
        'writer_usage': batch.call_usage(generation), 'new_model_calls': 0})
    sources = dict(original_files)
    for path in runtime.rglob('*'):
        if path.is_file():
            path.chmod(0o444)
            sources[str(path)] = checksum(path)
    for path in generation.rglob('*'):
        if path.is_file():
            sources[str(path)] = checksum(path)
    for receipt in receipts:
        sources[receipt['destination']] = receipt['sha256']
    for name in ('launch_plan.json', 'reparse_receipts.json', 'import_receipts.json',
                 'request_plan.json', 'generation_usage.json'):
        sources[str(directory / name)] = checksum(directory / name)
    save(directory / 'source_snapshot.json', {'sources': sources, 'archive': {}})
    if inventory(source) != original_files:
        raise ValueError('Preparation changed the source run')
    save(directory / 'status.json', {'state': 'prepared', 'new_model_calls': 0, 'changed_tasks': changed_tasks})
    return new_plan


def render_report(result, plan, source_result, kinds, reparse):
    detections, values = result['comparison']['detections'], result['comparison']['stable_wrong_values']
    before = source_result['comparison']['detections']
    counts = kinds['counts']
    lines = ['# Parse lại response Direct/Soft BVA với literal fallback', '',
        f"Sau khi parse lại, Direct phát hiện thêm lỗi ở **{detections['direct']} PUT** (trước {before['direct']}), "
        f"Soft BVA ở **{detections['soft_bva']} PUT** (trước {before['soft_bva']}), trên {result['evaluated_base_pass']} PUT vượt base tests.", '',
        'Giới hạn kết luận: cùng response đã lưu, chỉ đổi parser; không phải sample mới. Cohort đã dùng trong các phân tích trước, không phải held-out.', '',
        '## Detection theo kind (đơn vị PUT, mẫu số ' + str(result['evaluated_base_pass']) + ' PUT)', '',
        '`wrong_value`: cả hai lần trả giá trị khác reference. `crash`: exception khác RecursionError/MemoryError. '
        '`resource`: timeout, RecursionError hoặc MemoryError (phụ thuộc giới hạn harness, báo riêng).', '',
        '| Arm | Tổng | wrong_value | crash | resource | Không tính resource | Input mới hợp lệ |', '|---|---:|---:|---:|---:|---:|---:|']
    for arm in ('direct', 'soft_bva'):
        row = counts[arm]
        lines.append(f"| {arm} | {row['total']} | {row['wrong_value']} | {row['crash']} | {row['resource']} | "
                     f"{row['non_resource']} | {result['arms'][arm]['valid_inputs']} |")
    lines += ['', f"Shared {detections['shared']}; Direct-only {detections['direct_only']}; Soft-only {detections['soft_bva_only']}; "
              f"Soft − Direct {detections['net_soft_minus_direct']:+d} PUT. Stable wrong-value: Direct {values['direct']}, Soft {values['soft_bva']}.", '',
              '## Task thay đổi do parser', '', '| Task | Direct input trước→sau | Soft input trước→sau |', '|---|---|---|']
    for row in reparse['tasks']:
        if row['changed']:
            lines.append(f"| {row['task_id']} | {row['direct']['valid_before']}→{row['direct']['valid_after']} | "
                         f"{row['soft_bva']['valid_before']}→{row['soft_bva']['valid_after']} |")
    lines += ['', 'Số input ở bảng này là input parser chấp nhận, trước khi lọc reference/domain và trùng lặp giữa hai arm.', '',
        f"Config: input budget {plan['settings']['input_budget']}/task/arm, 1 call/task/arm, temperature {plan['settings']['input_temperature']}, "
        f"max output {plan['settings']['input_tokens']} token/call; timeout {plan['settings']['timeout_seconds']} s/input; scorer confirm-first-failures-v1, reference chạy 2 lần.",
        'Parser: strict JSON trước, chỉ khi lỗi mới đọc bằng `ast.literal_eval` (map true/false/null). Response truncation vẫn bị reject.',
        f"Task không đổi input dùng lại native checkpoint ({plan['imported_task_results']} task); task đổi input được chấm lại.",
        f"Model calls mới: **0**. Writer usage gốc: `{result['writer_usage']}`.",
        f"Source run: `{plan['continuation_source']}`. Source run không đổi; immutable replay khớp.", '']
    return '\n'.join(lines)


def worker(directory):
    from final.src.runtime.execution import execute
    from final.src.audits import detection_kinds
    with (directory / '.worker.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with (directory / 'worker_started.json').open('x') as marker:
            json.dump({'pid': os.getpid(), 'new_model_calls': 0}, marker)
        try:
            plan = read(directory / 'launch_plan.json')
            guard = batch.SourceGuard(directory)
            guard.verify(archive=True)
            for expected, status in (('1', 'pass'), ('2', 'fail')):
                outcome = execute({'mode': 'evaluate', 'context': 'def f(x):\n    pass\n',
                    'source': 'def f(x): return x', 'entry': 'f', 'timeout': 3,
                    'tests': [{'args': '(1,)', 'kwargs': '{}', 'expected': expected}], 'atol': 0})
                if outcome['tests'][0]['status'] != status:
                    raise RuntimeError('Native sandbox smoke failed')
            save(directory / 'sandbox_readiness.json', {'identity_pass': True, 'wrong_value_fail': True,
                'python_executable': sys.executable, 'new_model_calls': 0})
            save(directory / 'status.json', {'state': 'running', 'phase': 'evaluation_only', 'pid': os.getpid(),
                'new_model_calls': 0, 'imported_task_results': plan['imported_task_results']})
            summary = batch.evaluate(directory, plan)
            if batch.evaluate(directory, plan, read_only=True) != summary:
                raise ValueError('Immutable replay differs')
            guard.verify(archive=True)
            receipts = read(directory / 'import_receipts.json')
            source = Path(plan['continuation_source'])
            if inventory(source) != receipts['source_files']:
                raise ValueError('Source run changed')
            if read(directory / 'evaluation/generation_frozen.json') != read(directory / 'generation/generation_frozen.json'):
                raise ValueError('Global input freeze changed')
            kinds = {'counts': {}}
            for arm in ('direct', 'soft_bva'):
                kinds['counts'][arm] = detection_kinds.kind_counts(detection_kinds.classify_arm(directory / 'evaluation', arm))
            result = {'arms': summary['arms'], 'evaluated_base_pass': summary['evaluated_base_pass'],
                'requested_tasks': len(plan['tasks']), 'skips': summary['skips'],
                'writer_usage': receipts['writer_usage'], 'new_model_calls': 0,
                'comparison': batch.paired_verdicts(directory / 'evaluation'),
                'detection_kinds': kinds['counts'], 'reparsed_changed_tasks': plan['reparsed_changed_tasks'],
                'read_only_replay_matches': True, 'source_hashes_verified': True,
                'original_run_unchanged': True, 'continuation_source': plan['continuation_source']}
            save(directory / 'result_digest.json', result)
            (directory / 'REPORT.md').write_text(render_report(result, plan, read(source / 'result_digest.json'),
                                                               kinds, read(directory / 'reparse_receipts.json')))
            save(directory / 'status.json', {'state': 'complete', 'pid': os.getpid(),
                'finished_utc': time.time(), 'new_model_calls': 0})
            print(json.dumps(result['comparison']['detections'], ensure_ascii=False), flush=True)
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
            '-P', '-B', '-u', '-m', 'final.src.audits.reparse_bva_batch', '--worker', '--artifacts', str(directory)]
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
    directory = (options.artifacts or ROOT / ('final/out/bva_batch_matched164_reparse_'
                 + dt.datetime.now().strftime('%Y%m%d_%H%M%S'))).resolve()
    if options.worker:
        worker(directory)
        return
    plan = prepare(options.source_run, directory)
    receipt = {'artifacts': str(directory), 'changed_tasks': plan['reparsed_changed_tasks'],
               'imported_task_results': plan['imported_task_results'], 'new_model_calls': 0}
    if not options.prepare_only:
        receipt['pid'] = launch(directory)
    print(json.dumps(receipt), flush=True)


if __name__ == '__main__':
    main()
