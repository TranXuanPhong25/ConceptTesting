"""Gemini PUT generation and Plain/DT V2 evaluation on HumanEval-X Java."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import time

from final.src.models import create_model
from final.src.models.core_model import ModelError
from final.src.modular.artifacts import ArtifactStore
from final.src.modular.calls import RecordedModelCalls
from final.src.modular.cohort import call_usage
from final.src.runtime.artifacts import save
from .PUT_generation import generate_puts
from .language_runtime import execute_program
from .pipeline import run_benchmark, render


def prepare(directory):
    from .run import prepare as prepare_runtime
    root = Path(__file__).resolve().parents[3]
    config = {'dataset': 'humaneval_x_java', 'arms': ['plain', 'decision_table_v2'],
        'backend': 'vertex', 'model_name': 'gemini-3.1-flash-lite',
        'inputs_per_task': 20, 'completion_tokens': 4096, 'context_tokens': 18192,
        'temperature': .7, 'seed': 314159, 'timeout_seconds': 8}
    description = prepare_runtime(config, directory)
    experiment = {'dataset': 'HumanEval-X Java', 'tasks': 164, 'puts_per_task': 10,
        'writer_logical_call_cap': 164, 'tester_logical_call_cap': 328,
        'physical_attempt_cap': 1476, 'writer_max_tokens': 4072,
        'writer_temperature': .9, 'writer_seed': 20261030,
        'base_tests': 'public examples only', 'source_directory': str(root / 'final/data/benchmarks'),
        'output_directory': str(directory), 'config': description['config']}
    save(directory / 'experiment_config.json', experiment)
    save(directory / 'budget.json', {'cap_usd': 20, 'reserved_usd': 0, 'attempts': 0,
        'reservation_rates_usd_per_million': {'input': 1, 'output': 5},
        'policy': 'conservative full-output reservation per physical attempt; unknown attempts remain charged'})
    return experiment


class BudgetModel:
    """Reserve a conservative cost before every paid attempt, including retries."""
    def __init__(self, model, store):
        self.model, self.store = model, store

    @property
    def model_id(self):
        return self.model.model_id

    def tokens(self, messages):
        return self.model.tokens(messages)

    def prepare_generation(self, messages, max_tokens):
        return self.model.prepare_generation(messages, max_tokens)

    def generate_prepared(self, prepared, **options):
        budget = self.store.read('budget.json')
        reserve = (prepared.prompt_tokens + 5 * prepared.output_tokens) / 1_000_000
        if budget['reserved_usd'] + reserve > budget['cap_usd'] or budget['attempts'] >= 1476:
            raise RuntimeError('Authorized model budget exhausted; saved work retained')
        budget['reserved_usd'] += reserve
        budget['attempts'] += 1
        save(self.store.path('budget.json'), budget)
        return self.model.generate_prepared(prepared, **options)


class Writer:
    def __init__(self, calls, number):
        self.calls, self.number = calls, number

    def generate(self, messages, **options):
        return self.calls.complete(self.number, 'put_generation', messages,
            response_format={'type': 'json_object'}, **options)


def run(directory):
    store = ArtifactStore(directory)
    config = store.read('config_snapshot.json')
    experiment = store.read('experiment_config.json')
    plan = store.read('launch_plan.json')
    if not Path(__file__).resolve().is_relative_to(Path(plan['runtime'])):
        raise RuntimeError('Java worker must use its prepared runtime')
    with store.path('.worker.lock').open('a+') as owner:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with store.path('worker_started.json').open('x') as marker:
            json.dump({'pid': os.getpid(), 'started_epoch': time.time()}, marker)
        tasks = []
        cohort, records, skipped = {}, [], []

        def native(*args, **kwargs):
            with (Path(plan['workspace']) / 'final/out/.boundary_native.lock').open('a+') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                return execute_program(*args, **kwargs)

        def progress(phase, task_id=None):
            data = {'state': 'running', 'phase': phase, 'pid': os.getpid(), 'task_id': task_id,
                'writer_tasks_saved': len(records), 'requested_tasks': len(tasks),
                'generated_PUTs': sum(len(r['programs']) for r in records),
                'base_pass_PUTs': sum(r['base_pass'] for r in records),
                'skips': skipped, 'model_calls': call_usage(directory), 'metrics': 'pending'}
            save(store.path('status.json'), data)
            save(store.path('progress.json'), data)

        try:
            tasks = store.read('tasks_snapshot.json')
            model = BudgetModel(create_model(backend='vertex', model_name=config['model_name'],
                context=config['context_tokens']), store)
            calls = RecordedModelCalls(model, store)
            progress('put_generation')
            for task in tasks:
                number = int(task['task_id'].split('/')[1])
                progress('put_generation', task['task_id'])
                cohort[task['task_id']] = []
                if number == 32:
                    skipped.append({'task_id': task['task_id'], 'reason': 'non_unique_root_oracle_not_supported'})
                    continue
                reference = store.load_or_compute(f'tasks/{number}/reference_base.json',
                    lambda: native(task, task['reference_source'], [], timeout=config['timeout_seconds'], base=True))
                if reference['status'] != 'ok' or reference['tests'] != [{'status': 'ok'}]:
                    skipped.append({'task_id': task['task_id'], 'reason': 'reference_public_tests_failed', 'outcome': reference})
                    continue
                programs = generate_puts(Writer(calls, number), task, count=experiment['puts_per_task'])
                for program in programs:
                    program['id'] = str(program['id'])
                    program['base'] = store.load_or_compute(f'tasks/{number}/base/{program["id"]}.json',
                        lambda: native(task, program['code'], [], timeout=config['timeout_seconds'], base=True))
                record = {'task_id': task['task_id'], 'programs': programs,
                    'base_pass': sum(p['base']['status'] == 'ok' and p['base']['tests'] == [{'status': 'ok'}] for p in programs)}
                records.append(record)
                cohort[task['task_id']] = [{'id': p['id'], 'code': p['code']} for p in programs]
                save(store.path('put_cohort.json'), {'tasks': records})
            config['candidate_path'] = str(store.path('candidates.jsonl'))
            store.path('candidates.jsonl').write_text(''.join(json.dumps({'task_id': identifier, **program}) + '\n'
                for identifier, programs in cohort.items() for program in programs))
            progress('generation')
            result = run_benchmark(tasks, cohort, store, config, calls=calls, executor=native)
            result.update(writer_tasks=len(records), writer_skips=skipped,
                generated_PUTs=sum(len(r['programs']) for r in records), budget=store.read('budget.json'))
            save(store.path('result_digest.json'), result)
            store.path('REPORT.md').write_text(render(result) + '\nPUT được Gemini sinh độc lập từ spec, không lấy canonical source làm PUT. '
                'Generation và evaluation dùng cùng model; chưa kiểm specification admission đầy đủ. '
                'tester_calls gồm cả writer PUT và hai input arms.\n')
            save(store.path('status.json'), {'state': 'complete', 'phase': 'complete', 'pid': os.getpid()})
            return result
        except BaseException as error:
            detail = error.details() if isinstance(error, ModelError) and hasattr(error, 'details') else {'error_type': type(error).__name__}
            if isinstance(error, RuntimeError) and str(error).startswith('Authorized model budget exhausted'):
                detail['reason'] = 'Authorized model budget exhausted; saved work retained'
            save(store.path('status.json'), {'state': 'failed', 'pid': os.getpid(), 'error': detail})
            store.path('REPORT.md').write_text('Run chưa hoàn tất; metrics còn thiếu là pending.\n\n```json\n' +
                json.dumps({'error': detail, 'calls': call_usage(directory), 'budget': store.read('budget.json'),
                    'saved_writer_tasks': len(records), 'skips': skipped}, ensure_ascii=False, indent=2) + '\n```\n')
            raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', type=Path, required=True)
    run(parser.parse_args().artifacts.resolve())
