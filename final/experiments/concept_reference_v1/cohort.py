"""Write-once PUT cohort. Later benchmarks only load and verify the frozen file."""
from __future__ import annotations

import fcntl
import hashlib
import json
import importlib.metadata
import platform
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from final.contracts import fingerprint, parse_json
from final.pipeline import Pipeline, Settings, digest, save
from final.prompts import programs as program_prompt
from final.run import DATA_SHA256
import final.contracts
import final.prompts
import final.pipeline
from .execution import execute


def build_task(task, client, directory: Path):
    final = directory / 'cohort_task.json'
    if final.exists():
        return json.loads(final.read_text())
    retained, seen, rejected = [], set(), []
    for round_index in range(10):
        if len(retained) == 10:
            break
        # Up to five compact solutions per batch; never needs all 10 in one output.
        count = min(5, 10 - len(retained))
        messages = program_prompt(task, retained[-3:], count)
        if len(retained)>3:
            messages[-1]['content'] += '\nEarlier retained approaches (also avoid): ' + json.dumps(
                [r['approach'][:200] for r in retained[:-3]])
        response = client.query(directory, f'programs_{round_index:02d}', messages,
                                temperature=.9, max_tokens=3072,
                                seed=20261030 + int(task['task_id'].split('/')[1])*100 + round_index)
        try:
            records = parse_json(response.text)['programs']
            if not isinstance(records, list) or len(records) > 30:
                raise ValueError()
        except (ValueError, TypeError, KeyError):
            rejected.append(dict(round=round_index, reason='invalid_json'))
            continue
        for record in records:
            if len(retained) == 10:
                break
            try:
                if not isinstance(record, dict) or not isinstance(record.get('code'), str):
                    raise ValueError()
                if len(record['code']) > 30000 or not isinstance(record.get('approach'), str):
                    raise ValueError()
                key = fingerprint(record['code'], task['entry_point'])
            except (ValueError, SyntaxError, RecursionError, TypeError):
                rejected.append(dict(round=round_index, reason='invalid_program'))
                continue
            if key in seen:
                rejected.append(dict(round=round_index, reason='duplicate'))
                continue
            seen.add(key)
            retained.append(dict(id=len(retained), code=record['code'], approach=record['approach'], fingerprint=key))
    rows, base_keys = [], set()
    for record in retained:
        path = directory / 'base' / f"{record['id']}.json"
        if path.exists():
            result = json.loads(path.read_text())
        else:
            result = execute(dict(mode='base', context=task['prompt'], source=record['code'],
                                  entry=task['entry_point'], base=task['test'], timeout=3,
                                  seed=20261030 + int(task['task_id'].split('/')[1]), trace=True))
            save(path, result)
        base_keys.update(result.get('input_keys', []))
        rows.append(dict(record, base=result))
    result = dict(task_id=task['task_id'], programs=rows, generated=len(rows),
                  base_pass=sum(r['base']['status']=='pass' for r in rows),
                  base_input_keys=sorted(base_keys), generation_rejections=rejected,
                  status='complete' if len(rows)==10 else 'shortfall')
    save(final, result)
    return result


def load_cohort(path: Path):
    data = json.loads(path.read_text())
    if data['cohort_sha256'] != digest(data['tasks']):
        raise ValueError('Frozen cohort checksum mismatch')
    if data['dataset_sha256'] != DATA_SHA256:
        raise ValueError('Frozen cohort dataset mismatch')
    return data


def call_usage(directory):
    attempts=list(directory.glob('tasks/*/calls/*/attempt.json'))
    responses=list(directory.glob('tasks/*/calls/*/response.json'))
    totals={key:0 for key in ('prompt_tokens','completion_tokens','total_tokens')}
    for path in responses:
        usage=json.loads(path.read_text()).get('usage',{})
        for key in totals:
            value=usage.get(key,0)
            if type(value) in (int,float):
                totals[key]+=value
    return dict(invocations=len(attempts),received=len(responses),unknown=len(attempts)-len(responses),known_usage=totals)


def build_cohort(model, tasks, directory: Path, workers=2):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / 'cohort.json'
    if path.exists():
        cohort = load_cohort(path)
        if [t['task_id'] for t in cohort['tasks']] != [t['task_id'] for t in tasks]:
            raise ValueError('Frozen cohort task set differs')
        return cohort
    with (directory / '.build.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        manifest = dict(model=model.model_id, dataset_sha256=DATA_SHA256,
                        task_ids=[t['task_id'] for t in tasks], target=10, max_rounds=10,
                        batch_size=5, max_tokens=3072, temperature=.9,
                        python=platform.python_version(),packages={p:importlib.metadata.version(p) for p in ('coverage','numpy','evalplus')},
                        sources={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                            [Path(__file__),Path(final.contracts.__file__),Path(final.prompts.__file__),
                             Path(final.pipeline.__file__),Path(__file__).with_name('execution.py'),
                             Path(__file__).with_name('worker.py'),Path(__file__).with_name('contracts.py'),
                             Path(__file__).with_name('model.py')]})
        mp = directory / 'generation_manifest.json'
        if mp.exists() and json.loads(mp.read_text()) != manifest:
            raise ValueError('Generation settings/source changed; existing frozen cohorts can still be loaded')
        save(mp, manifest)
        client = Pipeline(model, directory, Settings())
        executor = ThreadPoolExecutor(max_workers=workers)
        pending, iterator, results = {}, iter(tasks), {}

        def submit():
            task = next(iterator, None)
            if task:
                pending[executor.submit(build_task, task, client,
                    directory/'tasks'/task['task_id'].split('/')[1])] = task['task_id']

        for _ in range(workers):
            submit()
        try:
            while pending:
                future = next(as_completed(pending))
                task_id = pending.pop(future)
                result = future.result()
                results[task_id] = result
                save(directory/'status.json', dict(state='building', finished=len(results), expected=len(tasks),
                    generated=sum(r['generated'] for r in results.values()), base_pass=sum(r['base_pass'] for r in results.values())))
                print(f"cohort {len(results)}/{len(tasks)} {task_id} generated={result['generated']} base_pass={result['base_pass']}", flush=True)
                submit()
        finally:
            for future in pending:
                future.cancel()
            executor.shutdown(wait=True, cancel_futures=True)
        rows = [results[t['task_id']] for t in tasks]
        cohort = dict(schema='fixed-put-cohort-v1', model=model.model_id, dataset_sha256=DATA_SHA256,
                      tasks=rows, cohort_sha256=digest(rows),generation_usage=call_usage(directory))
        save(path, cohort)
        save(directory/'status.json',dict(state='frozen',tasks=len(rows),generated=sum(r['generated'] for r in rows),
                                         base_pass=sum(r['base_pass'] for r in rows)))
        return cohort
