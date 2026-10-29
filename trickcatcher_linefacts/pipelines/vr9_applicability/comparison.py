"""Paired v11/retrieval controller; target references enter only final scoring."""
import ast
import hashlib
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from .paths import HERE, DATA_OUT, CONFIG
from .llm_client import atomic_json
from . import preconditions, run_v4, v4_strategies, v4_runtime, spec_facts, oracle_b01
from .retrieval_adapter import adapt
from .prepare_comparison import verify, sha
from .transport import Client

ROOT = DATA_OUT / 'comparison'


def status(stage, done=0, total=113, **extra):
    atomic_json(ROOT/'STATUS.json', dict(stage=stage, completed=done, total=total, **extra))


def prepare_one(raw, client):
    task = {k:v for k,v in raw.items() if k != 'public'}
    n = task['task']
    precond, strategies = ROOT/'preconditions', ROOT/'strategies'
    preconditions.mine(task, client, precond, evidence_filter=False, python=CONFIG['V4_PYTHON'])
    v4_strategies.mine(task, client, precond, strategies, Path(CONFIG['V4_PYTHON']))
    task = run_v4.mined_task(task, precond, strategies)
    fr = v4_runtime.isolated('legacyfacts', dict(task=task, public=raw['public'], precond_dir=str(precond)),
                             ROOT/'facts'/str(n), timeout=3600)
    if fr['base_ok'] is not True:
        raise ValueError('public_base_tests_failed')
    top = [fr['facts'][i] for i in fr['top3']]
    placebo, pool = fr['placebo3'], fr['facts'][:]
    if not top:
        params = preconditions.specification(task)[2]
        result = v4_runtime.isolated('spec', dict(entry=task['entry'], base=spec_facts.base_args(task['base']),
            params=[p.arg for p in params.posonlyargs + params.args], valid_src=task['mined_valid_src']), ROOT/'specfacts'/str(n))
        top, placebo = result['facts'][:3], result['placebo'][:3]
        pool += result['facts']
    task.update(concept_meta=top, concept_facts=[f['text'] for f in top], placebo_meta=placebo,
                placebo_facts=[f['text'] for f in placebo], tool_inputs=list(dict.fromkeys(f['witness_call'] for f in top if f.get('witness_call'))),
                doc_fail=fr['doc_fail'], facts_version='v4')
    retrieved, bindings = adapt(task, pool, ROOT/'facts'/str(n)/'retrieval.sqlite3')
    result = dict(v11=task, retrieval=retrieved, bindings=bindings)
    atomic_json(ROOT/'prepared'/f'{n}.json', result)
    return result


def generate_pair(item, client):
    index, pair = item
    n = pair['v11']['task']
    for arm in (('v11','retrieval') if index % 2 == 0 else ('retrieval','v11')):
        run_v4.run([pair[arm]], ROOT/'generation'/arm/str(n), Path(CONFIG['V4_PYTHON']),
                   client=client, k=1, workers=1, arms=('concept','concept-hybrid'))
    return n


def oracle_jobs(prepared):
    system, user = oracle_b01.dpp_templates()
    for pair in prepared:
        task = pair['v11']
        spec = preconditions.specification(task)[0]
        for sample in range(10):
            yield dict(task=task['task'], sample=sample,
                       messages=oracle_b01.msgs(user.replace('{signature_and_doctoring}', spec), system=system),
                       seed=CONFIG['seeds']['oracle'] + 500000 + task['task']*100 + sample)


def run_pool(stage, items, function):
    items = list(items)
    status(stage, total=len(items))
    values = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(function, item) for item in items]
        for future in as_completed(futures):
            values.append(future.result())
            status(stage, len(values), len(items))
            print(stage, len(values), '/', len(items), flush=True)
    return values


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    with (ROOT/'CLAIM.json').open('x') as stream:
        json.dump(dict(pid=os.getpid(), tasks=113, K=1), stream)
    verify()
    v4_runtime.require_versions()
    client = Client(ROOT/'transport')
    client.preflight()
    tasks = json.loads((HERE/'assets/tasks.json').read_text())
    assert len(tasks) == 113 and len({t['task'] for t in tasks}) == 113
    prepared = run_pool('preparation', tasks, lambda task: prepare_one(task, client))
    prepared.sort(key=lambda p: hashlib.sha256(str(p['v11']['task']).encode()).hexdigest())
    atomic_json(ROOT/'PREPARATION_FREEZE.json', {str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'prepared').glob('*.json'))})
    run_pool('generation_pairs', enumerate(prepared), lambda item: generate_pair(item, client))

    def generate_oracle(job):
        response = client.chat(job['messages'], job['seed'], temperature=0.8, top_p=0.95, max_tokens=1024)
        record = dict(task=job['task'], sample=job['sample'], response=response)
        atomic_json(ROOT/'oracles'/str(job['task'])/f'{job["sample"]}.json', record)
        return record

    run_pool('shared_spec_oracle', oracle_jobs(prepared), generate_oracle)
    verify()
    files = [p for part in ('generation','oracles','transport','prepared') for p in (ROOT/part).rglob('*')
             if p.is_file() and p.suffix in ('.json','.jsonl','.py')]
    atomic_json(ROOT/'GENERATION_FREEZE.json', dict(files={str(p.relative_to(ROOT)):sha(p) for p in sorted(files)}, target_reference_used=False))
    from .comparison_score import score
    score(prepared)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        reason = str(exc) if re.fullmatch(r'[A-Za-z0-9_ ():.=-]+', str(exc)) else type(exc).__name__
        atomic_json(ROOT/'STATUS.json', dict(stage='blocked', error_type=type(exc).__name__, reason=reason))
        raise SystemExit(1)
