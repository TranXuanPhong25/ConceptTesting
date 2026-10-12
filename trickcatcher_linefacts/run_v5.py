"""V5 steps 1/2 only: frozen v3 fuzz, optional mutmut, per-gap Hypothesis fallback."""
import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from trickcatcher_linefacts import gen_inputs, generate, preconditions, v4_prompts, v4_runtime, v4_strategies
from trickcatcher_linefacts.llm_client import Client, atomic_json

INPUT = HERE/'out/tasks_v3m2_all.json'
PRECOND = HERE/'out/precond_qwen7b_v2'
STAGE = 4  # v4 uses stages 0..3; this stage is reserved for v5 gap mining/draws.


def digest(obj):
    return preconditions.sha(json.dumps(obj, sort_keys=True, ensure_ascii=False))


def sources():
    names = ('run_v5.py','v5_worker.py','v5_offline.py','facts.py','tracer.py','fuzz_validity.py',
             'v4_tools.py','v4_worker.py','v4_strategies.py','v4_prompts.py','v4_runtime.py',
             'preconditions.py','gen_inputs.py','llm_client.py','offline.py','offline_metrics_v3m.py')
    return {name: preconditions.sha((HERE/name).read_bytes()) for name in names}


def writable(path):
    path = Path(path).resolve(); out = HERE/'out'
    if path == out or path in out.parents:
        raise ValueError('choose a fresh dedicated output path')
    if out in path.parents and path.relative_to(out).parts[0] not in {
        'facts_v3mm','tasks_v3mm_all.json','offline_v3mm','strategy_qwen7b_v5',
        'facts_v5','tasks_v5_all.json','offline_v5'}:
        raise ValueError('historical out paths are read-only')
    return path


def manifest(directory, value):
    directory = writable(directory)
    if directory.exists() and any(directory.iterdir()) and not (directory/'manifest.json').exists():
        raise ValueError(f'nonempty output without v5 manifest: {directory}')
    v4_runtime.immutable(directory/'manifest.json', dict(pipeline='v5-steps-1-2', **value))
    return directory


def isolated(mode, job, directory, python, timeout=3600):
    directory = Path(directory).resolve(); directory.mkdir(parents=True, exist_ok=True)
    jp, op = directory/'job.json', directory/'result.json'
    v4_runtime.immutable(jp, dict(mode=mode, **job))
    result = gen_inputs.sandbox(python, HERE/'v5_worker.py', jp, op, timeout)
    if 'worker_error' in result: raise RuntimeError(result['worker_error'])
    return result


def inputs(path, precond_dir, ids=None):
    bundle = json.loads(Path(path).read_text())
    tasks = bundle['tasks']
    if ids is not None:
        if len(set(ids)) != len(ids) or not set(ids) <= {t['task'] for t in tasks}:
            raise ValueError('expected distinct non-design task ids in the v3m2 bundle')
        tasks = [t for t in tasks if t['task'] in ids]
    if not tasks or any(t['task'] in bundle['design_excluded'] for t in tasks):
        raise ValueError('empty/design task selection')
    for t in tasks:
        code = (Path(precond_dir)/str(t['task'])/'valid.py').read_text()
        if t['facts_version'] != 'v3m' or t['mined_valid_src'] != code or t['valid_sha256'] != preconditions.sha(code):
            raise ValueError('v3m2 bundle/validator mismatch')
    he = {int(r['task_id'].split('/')[1]): r for r in map(json.loads, generate.HE.open())}
    for t in tasks:
        if t['base'] != he[t['task']]['test'] or t['entry'] != he[t['task']]['entry_point']:
            raise ValueError('base-test source mismatch')
    return bundle, tasks, he


def provenance(tasks, he, precond_dir, source, experiment):
    return dict(experiment=experiment, mutant_source=source, tasks_sha256=digest(tasks),
                specifications_sha256=digest({t['task']:he[t['task']]['prompt'] for t in tasks}),
                precond_dir=str(Path(precond_dir).resolve()), tools=v4_runtime.VERSIONS, sources=sources(),
                prereg_sha256=preconditions.sha((HERE/'PREREG.md').read_bytes()))


def build_one(task, he, precond_dir, source, directory, python, experiment, gaps=None):
    n = task['task']; output = directory/f'{n}.json'
    job = dict(task=task, he=he[n], precond_dir=str(Path(precond_dir).resolve()),
               mutant_source=source, experiment=experiment)
    if gaps is not None: job['gaps'] = gaps
    marker = output.with_suffix('.manifest.json')
    if output.exists():
        expected = dict(job_sha256=digest(job), facts_sha256=preconditions.sha(output.read_bytes()))
        if not marker.exists() or json.loads(marker.read_text()) != expected:
            raise ValueError('facts cache changed; choose a fresh directory')
        return json.loads(output.read_text())
    result = isolated('facts', job, directory/'jobs'/str(n), python)
    atomic_json(output, result)
    atomic_json(marker, dict(job_sha256=digest(job), facts_sha256=preconditions.sha(output.read_bytes())))
    return result


def bundle_facts(bundle, tasks, records, output, config):
    result = []
    for task, fr in zip(tasks, records):
        top = [fr['facts'][i] for i in fr['top3']]
        result.append(dict(task, concept_meta=top, concept_facts=[f['text'] for f in top],
            placebo_meta=fr['placebo3'], placebo_facts=[f['text'] for f in fr['placebo3']],
            tool_inputs=list(dict.fromkeys(f['witness_call'] for f in top if f['witness_call'])), doc_fail=fr['doc_fail']))
    # Keep facts_version=v3m: run_gen --from-bundle dispatches mined validators by this schema tag.
    value = dict(bundle, tasks=result)
    output = writable(output)
    v4_runtime.immutable(output, value)
    v4_runtime.immutable(output.with_suffix('.manifest.json'), dict(config, bundle_sha256=digest(value)))


def messages(task, fact, base):
    body = v4_prompts.TARGET.replace('Use the supplied domain strategy as a starting point.',
                                   'Use the supplied base-test inputs as examples.')
    body += '\n\nSPECIFICATION:\n'+preconditions.specification(task)[0]
    body += '\n\nPUT:\n'+task['put']+'\n\nEXISTING TESTS:\n'+task['base']
    body += '\n\nBASE-TEST INPUTS (args, kwargs):\n'+'\n'.join(base)
    body += '\n\nFACT:\n'+fact['text']
    return [dict(role='system', content=v4_prompts.SYSTEM), dict(role='user', content=body)]


def mine_gap(task, fact, index, request, base, client, directory, python):
    prompt = messages(task, fact, base)
    trials = []; witness = None
    for retry in range(2):
        attempt = directory/f'attempt_{retry}'; attempt.mkdir(parents=True, exist_ok=True)
        seed = v4_prompts.seed(task['task'], 'concept', 0, STAGE, request, retry)
        v4_runtime.immutable(attempt/'prompt.json', prompt)
        response = client.chat(prompt, seed, temperature=0, top_p=1, max_tokens=4096)
        atomic_json(attempt/'response.json', response)
        stats = None; error = None; code = None
        try:
            code = v4_strategies.checked(response['text'])
            (attempt/'strategy.py').write_text(code)
            stats = isolated('targeted', dict(task=task, fact=fact, code=code, seed=seed), attempt/'draw', python, 180)
            atomic_json(attempt/'draw_stats.json', stats)
            if stats['errors'] or stats['nonliteral'] or stats['wrong_arity']:
                error = json.dumps({k:stats[k] for k in ('errors','nonliteral','wrong_arity','valid')})
            elif stats['witness'] is None:
                error = f"{stats['valid']} valid draws, none reached the fact"
            else: witness = stats['witness']
        except (SyntaxError, ValueError, RuntimeError) as exc:
            error = f'{type(exc).__name__}: {exc}'
        trial = dict(retry=retry, seed=seed, cap=200, error=error, draw_stats=stats,
                     strategy_sha256=preconditions.sha(code) if code else None)
        atomic_json(attempt/'verification.json', trial); trials.append(trial)
        if error is None: break
        prompt = prompt + [dict(role='assistant', content=response['text']),
                           dict(role='user', content=v4_prompts.RETRY.format(error=error))]
    result = dict(fact_index=index, fact=fact, request=request, witness=witness, attempts=trials)
    atomic_json(directory/'summary.json', result)
    return result


def mine_tasks(tasks, he, precond_dir, source, root, python, workers, client):
    if client.model.lower() not in ('qwen2.5-coder-7b-instruct','qwen/qwen2.5-coder-7b-instruct'):
        raise ValueError('v5 strategies require Qwen2.5-Coder-7B-Instruct')
    config = provenance(tasks, he, precond_dir, source, 'v5')
    root = manifest(root, dict(config, model=client.model, stage=STAGE, cap=200, max_gaps=10, retries=1))
    base_dir = root/'base_facts'; base_dir.mkdir(exist_ok=True)
    def work(task):
        n = task['task']; directory = root/str(n); directory.mkdir(exist_ok=True)
        fr = build_one(task, he, precond_dir, source, base_dir, python, 'v5-base')
        gaps = [(i,f) for i,f in enumerate(fr['facts']) if not f['reached']][:10]
        # main's hook runs before reached/witness_call/guard metadata is attached.
        def raw_fact(f):
            return {k:v for k,v in f.items() if k not in ('reached','witness_call','block','g_demote','tier',
                                                        'guard_line','guard_forced','guard_class','guard_counts')}
        saved = directory/'summary.json'
        key = digest(dict(task=task, facts=fr, config=config, model=client.model))
        if saved.exists():
            result = json.loads(saved.read_text())
            if result['cache_key'] != key: raise ValueError('mining cache changed')
            return result
        rows = [mine_gap(task, raw_fact(f), i, request, fr['base_inputs'], client,
                         directory/f'gap_{i}', python) for request,(i,f) in enumerate(gaps)]
        result = dict(task=n, cache_key=key, mutant_source=source, base_facts_sha256=digest(fr), gaps=rows)
        atomic_json(saved, result)
        print(f'task {n}: {len(rows)} gaps, {sum(r["witness"] is not None for r in rows)} reached', flush=True)
        return result
    with ThreadPoolExecutor(max_workers=workers) as pool: results = list(pool.map(work, tasks))
    atomic_json(root/'mining_summary.json', dict(tasks=results))
    return results


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage', choices=('v3mm','mine','facts'))
    p.add_argument('--mutant-source', choices=('mutmut','handwritten'))
    p.add_argument('--python', type=Path)
    p.add_argument('--input-bundle', type=Path, default=INPUT)
    p.add_argument('--precond-dir', type=Path, default=PRECOND)
    p.add_argument('--strategy-dir', type=Path, default=HERE/'out/strategy_qwen7b_v5')
    p.add_argument('--facts-dir', type=Path)
    p.add_argument('--tasks-path', type=Path)
    p.add_argument('--task-ids', type=int, nargs='+')
    p.add_argument('--workers', type=int, default=12)
    a = p.parse_args()
    if a.stage != 'v3mm' and a.mutant_source is None: p.error('--mutant-source is required; apply the registered step-1 rule')
    if a.stage == 'v3mm' and a.mutant_source == 'handwritten': p.error('v3mm requires mutmut')
    source = a.mutant_source or 'mutmut'; python = v4_runtime.interpreter(a.python)
    bundle, tasks, he = inputs(a.input_bundle, a.precond_dir, a.task_ids)
    if a.stage == 'mine':
        # Establish the manifest before Client creates its cache directory.
        config = provenance(tasks, he, a.precond_dir, source, 'v5')
        import os
        root = manifest(a.strategy_dir, dict(config, model=os.environ.get('QWEN_MODEL','qwen2.5-coder-7b-instruct'),
                                            stage=STAGE, cap=200, max_gaps=10, retries=1))
        mine_tasks(tasks, he, a.precond_dir, source, root, python, a.workers, Client(root/'cache', workers=a.workers))
        return
    experiment = 'v3mm' if a.stage == 'v3mm' else 'v5'
    config = provenance(tasks, he, a.precond_dir, source, experiment)
    summaries = {}
    if a.stage == 'facts':
        root = Path(a.strategy_dir)
        mining = json.loads((root/'manifest.json').read_text())
        if any(mining.get(k) != v for k,v in config.items()): raise ValueError('strategy manifest mismatch')
        for t in tasks:
            n = t['task']; row = json.loads((root/str(n)/'summary.json').read_text())
            base = json.loads((root/'base_facts'/f'{n}.json').read_text())
            key = digest(dict(task=t, facts=base, config=config, model=mining['model']))
            if row['cache_key'] != key or row['mutant_source'] != source: raise ValueError('strategy/base facts mismatch')
            summaries[n] = row
        config['strategies_sha256'] = digest(summaries)
    directory = manifest(a.facts_dir or HERE/'out'/f'facts_{experiment}', config)
    def work(task):
        gaps = summaries[task['task']]['gaps'] if summaries else None
        return build_one(task, he, a.precond_dir, source, directory, python, experiment, gaps)
    with ThreadPoolExecutor(max_workers=a.workers) as pool: records = list(pool.map(work, tasks))
    bundle_facts(bundle, tasks, records, a.tasks_path or HERE/'out'/f'tasks_{experiment}_all.json', config)
    print(f'{experiment}: {len(tasks)} facts records and bundle ready', flush=True)


if __name__ == '__main__': main()
