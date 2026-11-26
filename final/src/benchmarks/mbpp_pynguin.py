"""Evaluate Pynguin and its guided follow-up on the saved MBPP+ cohort."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial
import fcntl
import json
import os
from pathlib import Path
import runpy
import sys
import time

from final.src.modular.artifacts import ArtifactStore
from final.src.modular.call_builder import CallBuilder
from final.src.modular.calls import RecordedModelCalls
from final.src.modular.cohort import call_usage
from final.src.modular.context import PipelineSettings, TaskContext
from final.src.modular.input_prompts import structured_input_prompt
from final.src.modular.pynguin.adapter import PynguinInputGenerator
from final.src.modular.pynguin.config import PynguinSettings
from final.src.runtime.artifacts import digest, save
from .language_runtime import execute_program
from .pipeline import evaluate_task


def context_for(task, programs, store, settings, calls):
    declaration, _, _ = task['declaration'].rpartition('\n    pass')
    if not declaration:
        raise ValueError('Expected a saved MBPP signature stub')
    prompt = declaration + '\n    ' + repr(task['prompt']) + '\n'
    public_task = {'task_id': task['task_id'], 'entry_point': task['entry_point'], 'prompt': prompt,
                   'test': task['example_test']}
    return TaskContext(public_task, {'contract': '', 'mbpp_signature_only': True}, store, settings,
                       calls=calls, cohort_task={'programs': programs},
                       packet={'visible_put_ids': [p['id'] for p in programs]})


def generate_guided(context, seed_batch, hybrid):
    if not seed_batch['inputs']:
        return {'status': 'unavailable', 'inputs': [], 'reason': 'no_pynguin_seed_inputs'}
    # The historical loop generates feedback from signature checks and membership only.
    context.packet['common'] = structured_input_prompt(context.task, context.cohort_task['programs'],
                                                       '', context.settings.input_budget)
    result = hybrid.generate_guided(context, seed_batch)
    result['seed_batch_sha256'] = digest(seed_batch)
    rounds = [context.artifacts.read(context.task_directory + '/pynguin_guided/' + row['call_name'] + '_decoded.json')
              for row in result.get('rounds', [])]
    if rounds and not result['raw_guided_inputs'] and not any(row['explicit_empty'] for row in rounds):
        result.update(status='failed', reason='no_usable_guided_response')
    elif result.get('feedback_skip'):
        result['status'] = 'partial'
    return result


def evaluated(task, programs, store, arm, batch, timeout):
    prefix = f"tasks/{task['task_id'].split('/')[1]}"
    builder = CallBuilder.for_source(task['declaration'], task['entry_point'])
    records, rejected = [], []
    for index, row in enumerate(batch['inputs']):
        try:
            call = {field: row[field] for field in ('args', 'kwargs')}
            builder.validate_call(call)
        except (ValueError, TypeError, SyntaxError, KeyError, RecursionError) as error:
            rejected.append({'index': index, 'reason': str(error)[:200]})
        else:
            records.append({'call': call})
    batches = {arm: {**batch, 'inputs': records}}
    # Persist the exact typed calls before observing any output from the reference or a PUT.
    store.write(prefix + '/input_admission.json', {'rejected': rejected})
    store.write(prefix + '/inputs.json', batches)
    return evaluate_task(task, programs, batches, store, timeout=timeout, input_field='call',
                         executor=partial(execute_program, literal_calls=True))


def report(directory, config, results):
    classifier = runpy.run_path(str(directory.parent / 'table_reader.py'))
    arm = config['arm']
    detections = classifier['adapter_maps'](directory).get(arm, {})
    kinds = classifier['kind_counts'](detections)
    measured = [row for row in results if 'arms' in row]
    unavailable = [row for row in results if 'arms' not in row]
    statuses = Counter(row['generation_status'] for row in results)
    owner_statuses = Counter(status for row in results for status in row.get('owner_statuses', []))
    usage = call_usage(directory)
    evaluated_puts = sum(row['base_pass'] for row in measured)
    valid_inputs = sum(row['arms'][arm]['valid_inputs'] for row in measured)
    assert len(detections) == sum(row['arms'][arm]['detected'] for row in measured)
    assert usage['invocations'] <= config['physical_attempt_cap']
    assert usage['received'] <= config['logical_call_cap']
    if config.get('evaluation_repair'):
        assert usage['invocations'] == config['imported_calls']['attempts']
        assert usage['received'] == config['imported_calls']['responses']
    summary = {
        'dataset': 'mbpp', 'config': config, 'tasks': len(measured),
        'evaluated_base_pass': evaluated_puts, 'tester_calls': usage,
        'arms': {arm: {'detected': len(detections) if measured else None,
                       'valid_inputs': valid_inputs if measured else None,
                       'tasks_detected': len({task_id for task_id, _ in detections}) if measured else None,
                       **{key: (count if measured else None) for key, count in kinds.items() if key != 'total'}}},
        'task_ids': [row['task_id'] for row in measured], 'skips': unavailable,
        'generation_statuses': dict(statuses), 'pynguin_owner_statuses': dict(owner_statuses),
        'pynguin_executions_measured': sum(row.get('owner_executions', 0) for row in results),
        'pynguin_owners_missing_execution_stats': sum(row.get('owners_without_stats', 0) for row in results),
        'failed_tasks': [row['task_id'] for row in unavailable if row.get('error_type')],
    }
    save(directory / 'result_digest.json', summary)
    # Artifact keys preserve task identity for the common-task union.
    save(directory / 'detections.json', [dict(task_id=task_id, put_id=put_id, kind=kind)
                                        for (task_id, put_id), kind in sorted(detections.items())])
    outcome = f'{len(detections)} PUT phát hiện trên {evaluated_puts} PUT đã evaluation' if measured else 'Kết quả pending'
    (directory / 'REPORT.md').write_text(
        f'# MBPP+ · {config["label"]}\n\n{outcome}. '
        'Các phát hiện là reference disagreement ổn định qua hai lần execution. '
        'MBPP+ dùng signature và reference admission. Spec audit còn pending.\n\n'
        f'Đã evaluation {len(measured)}/{config["requested_tasks"]} task, {evaluated_puts}/{config["requested_puts"]} PUT '
        f'và {valid_inputs} input memberships được reference chấp nhận. '
        f'Có {len(unavailable)} task chưa có evaluation cho arm này. Chi tiết fail và skip nằm trong JSON.\n\n'
        'Đơn vị failure type là unique PUT. Chọn Wrong-value → Exception → Timeout. '
        'Exception gồm cả MemoryError và RecursionError. Lỗi encode/output của harness ghi riêng. '
        'Số token chỉ gồm usage thực nhận.\n\n```json\n' + json.dumps(summary, ensure_ascii=False, indent=2) + '\n```\n')
    return summary


def run(directory):
    store = ArtifactStore(directory)
    config = store.read('config_snapshot.json')
    tasks = json.loads((directory.parent / 'tasks_snapshot.json').read_text())
    cohort = json.loads((directory.parent / 'cohort.json').read_text())
    arm = config['arm']
    settings = PipelineSettings.from_snapshot(config['settings'])
    pynguin_settings = PynguinSettings(**config['pynguin'])
    seed_store = ArtifactStore(Path(config['seed_source'] or directory), read_only=True)
    search = PynguinInputGenerator(pynguin_settings, allow_missing_contract=True)
    calls, hybrid = None, None
    if arm == 'pynguin_guided' and not config.get('evaluation_repair'):
        from final.src.models import create_model
        from final.src.modular.generators.pynguin_hybrid import PynguinHybridInputGenerator
        from .mbpp_mechanism_snapshot import MechanismArm
        model = create_model(backend='vertex', model_name=config['model'], context=settings.context_tokens)
        store.write('endpoint_readiness.json', model.check_endpoint())
        calls = RecordedModelCalls(model, store)
        hybrid = PynguinHybridInputGenerator(pynguin_settings)
        hybrid.guided = MechanismArm()

    def guided_seed(task):
        programs = cohort[task['task_id']]
        context = context_for(task, programs, store, settings, calls)
        plan = seed_store.read(context.task_directory + '/seed_ready.json')
        if 'error_type' in plan:
            return context, {'status': 'unavailable', 'inputs': [], 'reason': 'pynguin_search_failed',
                             'error_type': plan['error_type']}
        seed = seed_store.read(context.task_directory + '/pynguin/batch.json')
        if digest(seed['batch']) != seed['batch_sha256'] or seed['batch_sha256'] != plan['batch_sha256']:
            raise ValueError('Saved Pynguin input digest mismatch')
        if seed['batch']['inputs']:
            store.load_or_compute(context.task_directory + '/pynguin_hybrid/coverage_evidence.json',
                                  lambda: hybrid.coverage_evidence(context, seed['batch']))
        return context, seed['batch']

    def prepare_task(task, evidence=None):
        prefix = 'tasks/' + task['task_id'].split('/')[1]
        try:
            if arm == 'pynguin':
                context = context_for(task, cohort[task['task_id']], store, settings, calls)
                batch = search.run(context)
                store.write(prefix + '/seed_ready.json', {'batch_sha256': digest(batch)})
                return batch
            context, seed = evidence.result()
            if seed.get('reason') == 'pynguin_search_failed':
                return seed
            return generate_guided(context, seed, hybrid)
        except Exception as error:
            detail = error.details() if hasattr(error, 'details') else {'error_type': type(error).__name__}
            if arm == 'pynguin':
                store.write(prefix + '/seed_ready.json', {'error_type': type(error).__name__})
            return {'status': 'failed', 'reason': 'generation_failed', 'inputs': [],
                    'error_type': type(error).__name__, 'error': detail}

    def score(task, batch):
        programs = cohort[task['task_id']]
        prefix = 'tasks/' + task['task_id'].split('/')[1]
        if batch['status'] in ('failed', 'timeout', 'unsupported_input', 'unsupported_environment', 'unavailable', 'prompt_too_large'):
            result = {'task_id': task['task_id'], 'skip': batch.get('reason') or batch['status'],
                      'pending_puts': len(programs)}
            if batch.get('error_type') or batch['status'] in ('failed', 'timeout', 'unsupported_environment'):
                result['error_type'] = batch.get('error_type', batch['status'])
            if batch.get('error'):
                result['error'] = batch['error']
        else:
            try:
                result = evaluated(task, programs, store, arm, batch, settings.timeout_seconds)
            except Exception as error:
                result = {'task_id': task['task_id'], 'skip': 'evaluation_failed',
                          'pending_puts': len(programs), 'error_type': type(error).__name__}
        result['generation_status'] = batch['status']
        if arm == 'pynguin':
            owners = batch.get('pynguin', {}).get('owners', [])
            stats = [owner['native_statistics']['values'] for owner in owners
                     if isinstance(owner.get('native_statistics'), dict) and owner['native_statistics']['status'] == 'measured']
            result.update(owner_statuses=[owner['status'] for owner in owners],
                          owner_executions=sum(int(row['Executed']) for row in stats),
                          owners_without_stats=len(owners) - len(stats))
        store.write(prefix + '/result.json', result)
        return result

    def progress(results):
        save(directory / 'progress.json', {'phase': 'generation_and_evaluation',
             'tasks_processed': len(results), 'tasks_requested': len(tasks),
             'tasks_evaluated': sum('arms' in row for row in results),
             'puts_evaluated': sum(row.get('base_pass', 0) for row in results),
             'skipped_or_failed': sum('skip' in row for row in results)})

    completed = [task for task in tasks if store.exists('tasks/' + task['task_id'].split('/')[1] + '/result.json')]
    results = [store.read('tasks/' + task['task_id'].split('/')[1] + '/result.json') for task in completed]
    remaining = [task for task in tasks if task not in completed]
    with (directory / '.worker.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if store.exists('worker_started.json'):
            raise RuntimeError('Use the existing run receipt to resume this experiment')
        store.write('worker_started.json', {'pid': os.getpid()})
        save(directory / 'status.json', {'state': 'running', 'pid': os.getpid(), 'phase': 'generation_and_evaluation'})
        progress(results)
        if arm == 'pynguin':
            pynguin_settings.validate_environment()
        with ThreadPoolExecutor(max_workers=config['workers']) as pool:
            if arm == 'pynguin':
                def search_and_score(task):
                    return score(task, prepare_task(task))
                futures = [pool.submit(search_and_score, task) for task in remaining]
            elif config.get('evaluation_repair'):
                futures = []
                for task in remaining:
                    number = task['task_id'].split('/')[1]
                    batch = store.read(f'tasks/{number}/previous_inputs.json')[arm]
                    batch['inputs'] = [record['call'] for record in batch['inputs']]
                    futures.append(pool.submit(score, task, batch))
            else:
                futures, pending = [], remaining
                while pending:
                    pure_terminal = seed_store.read('status.json')['state'] in ('complete', 'failed', 'interrupted')
                    ready = [task for task in pending if seed_store.exists(
                        'tasks/' + task['task_id'].split('/')[1] + '/seed_ready.json')]
                    if ready:
                        with ThreadPoolExecutor(max_workers=2) as observers:
                            evidence = [observers.submit(guided_seed, task) for task in ready]
                            for task, observed in zip(ready, evidence):
                                futures.append(pool.submit(score, task, prepare_task(task, observed)))
                                pending.remove(task)
                                finished = {future for future in futures if future.done()}
                                results.extend(future.result() for future in finished)
                                futures = [future for future in futures if future not in finished]
                                progress(results)
                    if not ready:
                        if pure_terminal:
                            futures.extend(pool.submit(score, task, {'status': 'unavailable', 'inputs': [],
                                'reason': 'pynguin_seed_pending'}) for task in pending)
                            break
                        time.sleep(2)
            for future in as_completed(futures):
                results.append(future.result())
                progress(results)
        assert len(results) == len(tasks) == len({row['task_id'] for row in results})
        summary = report(directory, config, results)
        failed = bool(summary['failed_tasks']) or not summary['tasks']
        save(directory / 'status.json', {'state': 'failed' if failed else 'complete', 'pid': os.getpid(),
             'phase': 'terminal', 'tasks_evaluated': summary['tasks'], 'failed_tasks': summary['failed_tasks']})


if __name__ == '__main__':
    destination = Path(sys.argv[1]).resolve()
    try:
        run(destination)
    except BaseException as error:
        failure = {'state': 'failed', 'phase': 'worker', 'error_type': type(error).__name__}
        if hasattr(error, 'details'):
            failure['error'] = error.details()
        save(destination / 'failure.json', failure)
        save(destination / 'status.json', failure)
        raise
