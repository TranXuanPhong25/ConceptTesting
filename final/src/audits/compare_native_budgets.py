"""Compare 64/128 native observations on one frozen candidate pool; no model or oracle."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import fcntl
import hashlib
import json
import os
from pathlib import Path
import time

from .recheck_saved_coverage import ROOT, SavedScenarios, measure
from final.src.modular.arms.coverage_feedback import interleave, observation_pairs
from final.src.modular.control_flow.analysis import hit
from final.src.runtime.artifacts import digest, save
from final.src.runtime.execution import execute


def saved_pool(generation, cohort_task, checker):
    base_keys = set()
    for program in cohort_task['programs']:
        for call in program['base'].get('calls', []):
            base_keys.add(checker.key({'kwargs': '{}', **call}))
    candidates, groups = {}, {}
    for row in generation['candidate_ledger']:
        if row.get('canonical_args') is None or row['errors'] or row.get('domain') != 'true':
            continue
        call = row['canonical_args'];key = checker.key(call)
        if key in base_keys:
            continue
        candidate = candidates.setdefault(key, {'call': call, 'candidate_id': row['candidate_id'],
            'sources': [], 'observations': {}, 'target_hits': [], 'obligation_hits': []})
        for origin in row['sources']:
            if origin not in candidate['sources']:
                candidate['sources'].append(origin)
            label = 'direct' if origin['tool'] == 'llm' else origin.get('concept_id') or origin.get('obligation_id')
            draw = origin.get('index', origin.get('draw_index', 0))
            groups.setdefault((origin['round'], label), []).append((draw, key))
    round_queues = []
    rounds = sorted({round_index for round_index, _ in groups})
    for round_index in rounds:
        labels = ['direct'] + [row['id'] for row in [*generation.get('concepts', []), *generation.get('obligations', [])]
                               if row.get('round') == round_index]
        queue = []
        for _, key in interleave([sorted(groups.get((round_index, label), []), key=lambda item: item[0]) for label in labels]):
            if key not in queue:
                queue.append(key)
        round_queues.append(queue)
    priority = list(dict.fromkeys(interleave(round_queues)))
    priority.extend(key for key in candidates if key not in priority)
    assert len(priority) == len(candidates) == generation['candidate_count']
    return candidates, priority


def compare_task(task, metadata, cohort_task, generation, packet, trace, caps=(64, 128)):
    checker = SavedScenarios(task)
    candidates, priority = saved_pool(generation, cohort_task, checker)
    original_inputs = digest(generation['inputs'])
    programs = {program['id']: program for program in cohort_task['programs']}
    targets, obligations = generation['selected_targets'], generation.get('obligations', [])
    labels = {c['id']: next(t['program_id'] for t in targets if t['id'] == c['target_id'])
              for c in generation.get('concepts', [])}
    labels.update({o['id']: o['program_id'] for o in obligations})
    receipts = []
    fallback_owners = [row['program_id'] for row in generation['analysis']]
    assert set(fallback_owners) <= set(packet['visible_put_ids'])
    for candidate, owner in observation_pairs(candidates, priority, targets, obligations, labels,
                                              fallback_owners, checker.scenario):
        if len(receipts) >= max(caps):
            break
        job = {'mode': 'control_flow', 'source': programs[owner]['code'], 'entry': task['entry_point'],
               'context': task['prompt'], 'contract': metadata.get('contract', ''), 'tests': [candidate['call']],
               'timeout': 1, 'seed': 314159}
        observation, seconds = trace(owner, job)
        candidate['observations'][owner] = observation
        hits = [t['id'] for t in targets if t['program_id'] == owner and hit(t, observation)]
        candidate['target_hits'] = list(dict.fromkeys(candidate['target_hits'] + hits))
        receipts.append({'candidate_key': checker.key(candidate['call']), 'program_id': owner,
                         'trace_seconds': seconds, 'call': candidate['call'], 'hit_targets': hits, **observation})
    assert digest(generation['inputs']) == original_inputs
    keys = list(candidates)
    indices = {key: index for index, key in enumerate(keys)}
    pool_generation = {**generation, 'inputs': [candidates[key]['call'] for key in keys]}
    results = {}
    for cap in caps:
        prefix = receipts[:cap]
        rows = measure(task, pool_generation,
            {(row['program_id'], indices[row['candidate_key']]): {k: v for k, v in row.items()
              if k not in ('candidate_key', 'trace_seconds', 'call', 'hit_targets', 'program_id')}
             for row in prefix})
        assert rows['target_coverage']['covered'] == len({identifier for row in prefix for identifier in row['hit_targets']})
        rows.update(observations=len(prefix), trace_seconds=sum(row['trace_seconds'] for row in prefix),
                    input_put_order=[digest((row['candidate_key'], row['program_id'])) for row in prefix])
        results[str(cap)] = rows
    low, high = (results[str(cap)] for cap in sorted(caps))
    assert high['input_put_order'][:len(low['input_put_order'])] == low['input_put_order']
    assert {r['target_id'] for r in low['target_measurements'] if r['status'] == 'hit'} <= {
        r['target_id'] for r in high['target_measurements'] if r['status'] == 'hit'}
    assert {r['id'] for r in low['obligations'] if r['new_membership']['status'] == 'hit'} <= {
        r['id'] for r in high['obligations'] if r['new_membership']['status'] == 'hit'}
    return {'task_id': task['task_id'], 'candidate_count': len(candidates), 'frozen_selected_inputs': len(generation['inputs']),
            'frozen_selected_inputs_sha256': original_inputs, 'caps': results}


def prepare(config, output):
    hashes = {}

    def read(path):
        path = Path(path);raw = path.read_bytes();hashes[str(path)] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw)

    source = Path(config['source_directory'])
    cohort = {row['task_id']: row for row in read(source / 'cohort.json')['tasks']}
    data, metadata, seen, tasks, skipped = {}, {}, set(), [], []
    for path in sorted((source / 'task_receipts').glob('*.json')):
        receipt = read(path);tid = receipt['task_id']
        assert tid not in seen;seen.add(tid)
        if receipt['state'] != 'complete':
            assert receipt['state'] == 'skipped';skipped.append(tid);continue
        leaf = Path(receipt['generation_directory']);number = tid.split('/')[-1]
        manifest = read(leaf / 'modular_manifest.json')
        assert manifest['settings']['input_seed'] == config['input_seed'] == 314159
        runtime = Path(read(source / 'launch_plan.json').get('runtime', ROOT)) if (source / 'launch_plan.json').exists() else ROOT
        dp = str(runtime / 'final/data/humaneval.jsonl')
        mp = str(runtime / 'final/data/contracts.json')
        if dp not in data:
            raw = Path(dp).read_bytes();hashes[dp] = hashlib.sha256(raw).hexdigest()
            data[dp] = {r['task_id']: r for r in map(json.loads, raw.decode().splitlines())}
        if mp not in metadata:
            metadata[mp] = read(mp)
        generation = read(leaf / f'tasks/{number}/control_flow_obligation/generation.json')
        packet = read(leaf / f'tasks/{number}/packet.json')
        programs = {p['id']: p for p in cohort[tid]['programs']}
        for row in generation['analysis']:
            assert hashlib.sha256(programs[row['program_id']]['code'].encode()).hexdigest() == row['source_sha256']
        assert {t['program_id'] for t in generation['selected_targets']} <= set(packet['visible_put_ids'])
        assert {o['program_id'] for o in generation.get('obligations', [])} <= set(packet['visible_put_ids'])
        checker = SavedScenarios(data[dp][tid]);saved_pool(generation, cohort[tid], checker)
        tasks.append((data[dp][tid], metadata[mp][tid], cohort[tid], generation, packet))
    assert seen == set(cohort) and len(seen) == 164 and len(tasks) == 157 and len(skipped) == 7
    assert sum(len(g['selected_targets']) for _, _, _, g, _ in tasks) == 407
    assert sum(len(g.get('obligations', [])) for _, _, _, g, _ in tasks) == 28
    inventory = {'slots': len(seen), 'eligible_tasks': len(tasks), 'skipped': skipped,
                 'candidates': sum(g['candidate_count'] for _, _, _, g, _ in tasks),
                 'frozen_selected_inputs': sum(len(g['inputs']) for _, _, _, g, _ in tasks),
                 'selected_targets': 407, 'declared_obligations': 28,
                 'maximum_native_pairs': len(tasks) * max(config['caps']), 'new_model_calls': 0, 'new_model_tokens': 0}
    save(output / 'source_hashes.json', hashes);save(output / 'inventory.json', inventory)
    return tasks, hashes


def run(config, output, *, prepare_only=False):
    tasks, hashes = prepare(config, output)
    if prepare_only:
        save(output / 'status.json', {'state': 'prepared', 'new_model_calls': 0, 'new_model_tokens': 0})
        return
    results = []
    started = time.monotonic()

    def progress(state, error=None):
        save(output / 'status.json', {'state': state, 'pid': os.getpid(), 'completed_tasks': len(results),
            'total_tasks': len(tasks), 'completed_pairs': sum(r['caps']['128']['observations'] for r in results),
            'elapsed_seconds': time.monotonic() - started, 'error': error,
            'new_model_calls': 0, 'new_model_tokens': 0})

    def process(arguments):
        task, metadata, cohort, generation, packet = arguments
        destination = output / 'tasks' / task['task_id'].split('/')[-1]

        def trace(owner, job):
            key = digest((owner, job));path = destination / 'traces' / (key + '.json')
            if path.exists():
                record = json.loads(path.read_text())
            else:
                start = time.monotonic();observation = execute(job)['tests'][0]
                record = {'observation': observation, 'seconds': time.monotonic() - start}
                save(path, record)
            return record['observation'], record['seconds']

        result = compare_task(task, metadata, cohort, generation, packet, trace, tuple(config['caps']))
        save(destination / 'result.json', result)
        return result

    try:
        for offset in range(0, len(tasks), config['cpu_workers']):
            progress('waiting_native_lock')
            with Path(config['native_lock']).open('a+') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                progress('running')
                with ThreadPoolExecutor(max_workers=config['cpu_workers']) as executor:
                    futures = [executor.submit(process, task) for task in tasks[offset:offset + config['cpu_workers']]]
                    for future in as_completed(futures):
                        results.append(future.result());progress('running')
        assert all(hashlib.sha256(Path(path).read_bytes()).hexdigest() == value for path, value in hashes.items())
        summary = {}
        for cap in config['caps']:
            rows = [r['caps'][str(cap)] for r in results]
            summary[str(cap)] = {'observations': sum(r['observations'] for r in rows),
                'trace_seconds': sum(r['trace_seconds'] for r in rows),
                'tasks_at_cap': sum(r['observations'] == cap for r in rows),
                'target_hits': sum(r['target_coverage']['covered'] for r in rows), 'target_total': 407,
                'obligation_statuses': dict(Counter(o['new_membership']['status'] for r in rows for o in r['obligations'])),
                'obligation_unknown_reasons': dict(Counter(reason for r in rows for o in r['obligations']
                    if o['new_membership']['status'] == 'unknown'
                    for reason in {e['reason'] for e in o['new_membership']['errors']})),
                'target_statuses': dict(Counter(t['status'] for r in rows for t in r['target_measurements']))}
        gains = [{'task_id': r['task_id'],
                  'target_gain': r['caps']['128']['target_coverage']['covered'] - r['caps']['64']['target_coverage']['covered'],
                  'obligation_gain': sum(o['new_membership']['status'] == 'hit' for o in r['caps']['128']['obligations']) -
                                     sum(o['new_membership']['status'] == 'hit' for o in r['caps']['64']['obligations'])} for r in results]
        digest_result = {'caps': summary, 'gains': gains, 'tasks': len(results), 'source_hashes_verified': len(hashes),
            'selected_input_changes': 0, 'new_model_calls': 0, 'new_model_tokens': 0,
            'elapsed_wall_seconds': time.monotonic() - started, 'put_detections': 'not_evaluated',
            'online_feedback_effect': 'pending_new_generation'}
        save(output / 'result_digest.json', digest_result)
        report = ['# CPU comparison: native budget64 vs128 trên frozen candidate pool', '',
            'Hai caps đã đo đủ157eligible tasks/164slots, giữ407selected targets và28declared obligations. '
            '64làprefix của128trong cùng observation order. Không sinh inputs mới, không chạy LLM/tokenizer/oracle hoặc tính PUT gain.', '',
            '| Cap observations/task | Observations thực | C1/C2 hit /407 | Obligation hit /28 | Obligation unknown /28 | Tổng sandbox seconds |',
            '|---|---:|---:|---:|---:|---:|']
        for cap, row in summary.items():
            report.append(f"| {cap} | {row['observations']} | {row['target_hits']} | {row['obligation_statuses'].get('hit',0)} | "
                          f"{row['obligation_statuses'].get('unknown',0)} | {row['trace_seconds']:.2f} |")
        report.extend(['', f'Wall time toàn comparison (bao gồm chờ shared native lock): {digest_result["elapsed_wall_seconds"]:.2f}giây. '
            'Sandbox seconds là tổng thời gian từng singleton execution, không phải wall time khi chạy4workers.', '',
            'Frozen pool gồm candidates của cả hai responses/sampling rounds cũ; đây là diagnostic cap trên pool cố định, '
            'không phải replay online hai rounds hoặc chứng minh prompt mới tốt hơn. Native order dùng shared production scheduler; '
            'candidate priority interleave frozen round0/round1 queues để cảhai rounds có cơhội trongprefix64. '
            'Final selected inputs giữ nguyên; pool coverage không phải coverage của suite≤20inputs. '
            'Predicate support giữ nguyên declarations; unknown không biến thành miss hoặc0bug.', '',
            'Model calls/tokens mới:0/0. Timeout1giây/input–PUT,4CPUworkers, shared native lock. '
            'Source/checkpoints được kiểm hash và giữ nguyên. Per-task cap results, prefix proof và trace durations trong tasks/.'])
        (output / 'REPORT.md').write_text('\n'.join(report) + '\n')
        progress('complete')
    except BaseException as error:
        progress('failed', type(error).__name__ + ':' + str(error))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args();destination = args.output.resolve()
    run(json.loads((destination / 'config_snapshot.json').read_text()), destination, prepare_only=args.prepare_only)
