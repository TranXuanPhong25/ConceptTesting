"""CPU-only C1/C2 and scenario measurement of frozen selected inputs; no generation or oracle."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import fcntl
import hashlib
import json
import os
from pathlib import Path
import time

from final.src.modular.call_builder import CallBuilder
from final.src.modular.catalogue_membership import membership_row
from final.src.modular.control_flow.analysis import hit, measure_targets
from final.src.modular.spec_obligation.evidence import Evidence
from final.src.runtime.artifacts import digest, save
from final.src.runtime.execution import execute

ROOT = Path(__file__).resolve().parents[3]


class SavedScenarios(Evidence):
    """Use the existing scenario checker with supplied traces, without base replay or discovery."""
    def __init__(self, task):
        self.builder = CallBuilder.for_source(task['prompt'], task['entry_point'])
        self.predicate_checks, self.predicate_seconds = 0, 0
        self.predicate_results = {}


def measure(task, generation, observations):
    checker = SavedScenarios(task)
    rows = []
    inputs = generation['inputs']
    for obligation in generation.get('obligations', []):
        outcomes = [checker.scenario(obligation, call, observations.get((obligation['program_id'], index)))
                    for index, call in enumerate(inputs)]
        rows.append({'id': obligation['id'], 'program_id': obligation['program_id'],
                     'old_membership': obligation['new_membership'],
                     'new_membership': membership_row(obligation['id'], outcomes, list(range(len(inputs))))})
    targets = generation.get('selected_targets', [])
    traces = [{'program_id': owner, **row} for (owner, _), row in observations.items()]
    return {'task_id': task['task_id'], 'selected_inputs': len(inputs),
            'target_coverage': {'covered': sum(any(hit(target, row) for (owner, _), row in observations.items()
                if owner == target['program_id']) for target in targets), 'total': len(targets)},
            'old_target_coverage': generation.get('target_coverage'),
            'target_measurements': measure_targets(targets, traces,
                [{**r, 'round': r.get('round', index)} for index, r in enumerate(generation.get('rounds', []))
                 if 'supplied_target_ids' in r]),
            'obligations': rows}


def run(config, output, *, prepare_only=False):
    hashes, cache_jobs, tasks = {}, {}, []

    def read(path):
        path = Path(path);raw = path.read_bytes()
        hashes[str(path)] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw)

    def dataset(path):
        raw = Path(path).read_bytes();hashes[str(path)] = hashlib.sha256(raw).hexdigest()
        return {r['task_id']: r for r in map(json.loads, raw.decode().splitlines())}

    loaded_data = {}
    counts = Counter()
    for variant, options in config['variants'].items():
        source = Path(options['source'])
        cohort = {r['task_id']: r for r in read(source / 'cohort.json')['tasks']}
        seen = set()
        for receipt_path in sorted((source / 'task_receipts').glob('*.json')):
            receipt = read(receipt_path)
            assert receipt['task_id'] not in seen
            seen.add(receipt['task_id'])
            if receipt['state'] != 'complete':
                assert receipt['state'] == 'skipped', receipt
                counts[variant + ':skipped'] += 1
                continue
            number = receipt['task_id'].split('/')[-1]
            leaf = Path(receipt['generation_directory'])
            manifest = read(leaf / 'modular_manifest.json')
            runtime = Path(read(source / 'launch_plan.json').get('runtime', ROOT)) if (source / 'launch_plan.json').exists() else ROOT
            data_path = str(runtime / 'final/data/humaneval.jsonl')
            metadata_path = str(runtime / 'final/data/contracts.json')
            if data_path not in loaded_data:
                loaded_data[data_path] = dataset(data_path)
            if metadata_path not in loaded_data:
                loaded_data[metadata_path] = read(metadata_path)
            task = loaded_data[data_path][receipt['task_id']]
            metadata = loaded_data[metadata_path][receipt['task_id']]
            generation = read(leaf / f'tasks/{number}/{options["arm"]}/generation.json')
            packet = read(leaf / f'tasks/{number}/packet.json')
            programs = {p['id']: p for p in cohort[task['task_id']]['programs']}
            analyses = generation.get('analysis')
            if analyses is None:
                analyses = read(leaf / f'tasks/{number}/{options["arm"]}/analysis.json')['programs']
            source_bindings = {row['program_id']: row['source_sha256'] for row in analyses}
            for analysis in analyses:
                assert hashlib.sha256(programs[analysis['program_id']]['code'].encode()).hexdigest() == analysis['source_sha256']
            owners = {t['program_id'] for t in generation.get('selected_targets', [])}
            owners.update(o['program_id'] for o in generation.get('obligations', []))
            assert owners <= set(packet['visible_put_ids'])
            assert owners <= set(source_bindings)
            bindings = [*generation.get('selected_targets', []), *generation.get('obligations', [])]
            for binding in bindings:
                actual = hashlib.sha256(programs[binding['program_id']]['code'].encode()).hexdigest()
                assert binding.get('source_sha256', actual) == actual
            pairs = {}
            for owner in sorted(owners, key=repr):
                for index, call in enumerate(generation['inputs']):
                    job = {'mode': 'control_flow', 'source': programs[owner]['code'], 'entry': task['entry_point'],
                           'context': task['prompt'], 'contract': metadata.get('contract', ''), 'tests': [call],
                           'timeout': config['trace_timeout_seconds'], 'seed': manifest['settings']['input_seed']}
                    key = digest(job);cache_jobs[key] = job;pairs[(owner, index)] = key
            tasks.append((variant, task, generation, pairs))
            counts[variant + ':tasks'] += 1
            counts[variant + ':selected_inputs'] += len(generation['inputs'])
            counts[variant + ':input_put_pairs'] += len(pairs)
        assert seen == set(cohort) and len(seen) == options['expected_slots']
        assert counts[variant + ':tasks'] == options['expected_eligible_tasks']
        assert counts[variant + ':skipped'] == options['expected_slots'] - options['expected_eligible_tasks']
        assert sum(len(g.get('selected_targets', [])) for v, _, g, _ in tasks if v == variant) == options['expected_targets']
    save(output / 'source_hashes.json', hashes)
    save(output / 'inventory.json', {'counts': dict(counts), 'unique_jobs': len(cache_jobs)})
    if prepare_only:
        save(output / 'status.json', {'state': 'prepared', 'total_pairs': len(cache_jobs),
                                     'new_model_calls': 0, 'new_model_tokens': 0})
        return
    receipts, failures = {}, []

    def progress(state):
        save(output / 'status.json', {'state': state, 'pid': os.getpid(), 'updated_epoch': time.time(),
            'completed_pairs': len(receipts), 'total_pairs': len(cache_jobs), 'failures': len(failures),
            'new_model_calls': 0, 'new_model_tokens': 0})

    def trace(key, job):
        path = output / 'traces' / (key + '.json')
        if path.exists():
            return json.loads(path.read_text())
        result = execute(job)['tests'][0]
        save(path, result)
        return result

    progress('waiting_native_lock')
    with Path(config['native_lock']).open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        progress('running')
        with ThreadPoolExecutor(max_workers=config['cpu_workers']) as pool:
            futures = {pool.submit(trace, key, job): key for key, job in cache_jobs.items()}
            for future in as_completed(futures):
                key = futures[future]
                try:
                    receipts[key] = future.result()
                except Exception as error:
                    failures.append({'trace_id': key, 'error': type(error).__name__ + ':' + str(error)})
                if (len(receipts) + len(failures)) % 100 == 0:
                    progress('running')
    save(output / 'failures.json', failures)
    if failures:
        progress('failed')
        raise RuntimeError(f'{len(failures)} native infrastructure failures; incomplete metrics remain pending')
    results = {}
    for variant, task, generation, pairs in tasks:
        row = measure(task, generation, {pair: receipts[key] for pair, key in pairs.items()})
        save(output / 'variants' / variant / (task['task_id'].split('/')[-1] + '.json'), row)
        results.setdefault(variant, []).append(row)
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == value for p, value in hashes.items())
    summary = {}
    for variant, rows in results.items():
        obs = [o for row in rows for o in row['obligations']]
        summary[variant] = {'tasks': len(rows), 'skipped': counts[variant + ':skipped'],
            'selected_inputs': sum(r['selected_inputs'] for r in rows),
            'input_put_pairs': counts[variant + ':input_put_pairs'],
            'target_hits': sum(r['target_coverage']['covered'] for r in rows),
            'target_total': sum(r['target_coverage']['total'] for r in rows),
            'target_statuses': dict(Counter(t['status'] for r in rows for t in r['target_measurements'])),
            'obligations': len(obs), 'obligation_statuses': dict(Counter(o['new_membership']['status'] for o in obs)),
            'old_obligation_statuses': dict(Counter(o['old_membership']['status'] for o in obs))}
    save(output / 'result_digest.json', {'variants': summary, 'unique_native_pairs': len(receipts),
         'observation_statuses': dict(Counter(r['status'] for r in receipts.values())),
         'new_model_calls': 0, 'new_model_tokens': 0, 'source_hashes_verified': len(hashes),
         'prompt_fix_effect': 'pending_new_generation', 'put_detections': 'not_evaluated'})
    report = ['# Đo lại coverage bằng CPU trên selected inputs đã lưu', '',
        'Đã đo lại toàn bộ scope; không sinh inputs mới. Coverage này kiểm tra trace đầy đủ hơn trên đúng owner PUT, '
        'không đo tác động của prompt mới hay chứng minh semantic bug. PUT detections không được evaluation lại.', '',
        f"Native timeout {config['trace_timeout_seconds']} giây/cặp input–PUT; {config['cpu_workers']} CPU workers; "
        f'{len(receipts)} unique native pairs. Model calls/tokens mới: 0/0. Source artifacts được kiểm hash và giữ nguyên.', '',
        '| Collection | Task | Selected input records | C1/C2 hit / selected targets | Obligation hit / declared | Unknown obligations |',
        '|---|---:|---:|---:|---:|---:|']
    for name, row in summary.items():
        report.append(f"| {name} | {row['tasks']} | {row['selected_inputs']} | {row['target_hits']}/{row['target_total']} | "
                      f"{row['obligation_statuses'].get('hit',0)}/{row['obligations']} | {row['obligation_statuses'].get('unknown',0)} |")
    report.extend(['', 'Mẫu số structural giữ nguyên targets đã chọn; miss không phải infeasible. '
        'Đo raw selected generation inputs (gồm input bị reference loại sau freeze), không đồng nhất oracle-valid inputs '
        'trong report efficacy cũ. Predicate support/declarations giữ nguyên source generation; base membership không chạy lại.', '',
        'Chi tiết config/source/output trong config_snapshot.json và source_hashes.json; per-task measurements trong variants/.'])
    (output / 'REPORT.md').write_text('\n'.join(report) + '\n')
    progress('complete')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--prepare-only', action='store_true')
    options = parser.parse_args()
    destination = options.output.resolve()
    try:
        run(json.loads((destination / 'config_snapshot.json').read_text()), destination, prepare_only=options.prepare_only)
    except BaseException as error:
        save(destination / 'status.json', {'state': 'failed', 'pid': os.getpid(),
             'error': type(error).__name__ + ':' + str(error), 'new_model_calls': 0, 'new_model_tokens': 0})
        raise
