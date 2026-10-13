"""One CLI for the frozen v7 recipe; offline replay is the default."""
from __future__ import annotations
import argparse
import copy
import json
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from . import paths

STAGES = ('mine', 'facts', 'specfacts', 'bundle', 'arms', 'evaluate', 'oracle-collect',
          'oracle-llm', 'oracle-score', 'strict', 'report')
NOTE = ('v6: v3m2 pipeline, fuzz validated by B5 preconditions (out/facts_v6)'
        ' | v7: + specification input-class facts (spec_facts.py) for tasks without code facts')


class Layout:
    def __init__(self, dataset='humaneval', root=None):
        self.dataset = dataset
        self.data = paths.dataset_paths(dataset)
        self.root = paths.safe_output(root) if root else paths.DATA_OUT
        self.precond = self.root / 'preconditions'
        self.strategy = self.root / 'strategies'
        self.facts = self.root / 'facts'
        self.specfacts = self.root / 'specfacts'
        self.generation = self.root / 'generation'
        self.oracle = self.root / 'oracle'
        self.all = self.root / 'tasks_all.json'
        self.hybrid = self.root / 'tasks_hybrid.json'


def task_sources(layout, ids=None):
    selection = json.loads(layout.data['selection'].read_text())
    selected = selection['tasks']
    if ids is not None:
        if not ids or len(set(ids)) != len(ids) or set(ids) - {t['task'] for t in selected}:
            raise ValueError('expected distinct selected task ids')
        selected = [t for t in selected if t['task'] in ids]
    he = {int(r['task_id'].split('/')[1]): r for r in map(json.loads, layout.data['he'].read_text().splitlines())}
    tasks = [dict(task=t['task'], entry=he[t['task']]['entry_point'], base=he[t['task']]['test'],
                  put=(layout.data['puts'] / f"HumanEval_{t['task']}/put0.py").read_text(), split=t['split'])
             for t in selected]
    return tasks, he, selection


def code_bundle(layout):
    from . import generate, preconditions, run_v4
    tasks, he, selection = task_sources(layout)
    result = []
    for raw in tasks:
        n = raw['task']
        mining = run_v4.mined_task(raw, layout.precond, layout.strategy)
        r = json.loads((layout.facts / f'{n}.json').read_text())
        if r.get('facts_version') != 'v3m' or r.get('valid_sha256') != mining['valid_sha256']:
            raise ValueError(f'task {n}: expected v6 facts under this B5 validator')
        if r.get('base_ok') is not True:
            raise ValueError(f'task {n}: facts base check failed')
        b = generate.bundle(n, he[n], layout.facts)
        b.update(placebo_meta=r['placebo3'], split=raw['split'], facts_version='v3m',
                 mined_valid_src=mining['mined_valid_src'], valid_sha256=mining['valid_sha256'])
        b['tool_inputs'] = [c for c in b['tool_inputs'] if c]
        result.append(b)
    return dict(facts_version='v3m', pilot=selection.get('pilot', []),
                design_excluded=selection.get('design_excluded', []), tasks=result, note=NOTE)


def bundle(layout):
    from . import oracle_b01 as ob, run_v4, v4_runtime
    standard = code_bundle(layout)
    for t in standard['tasks']:
        if t['concept_facts']: continue
        r = json.loads((layout.specfacts / f"{t['task']}.json").read_text())
        if r['facts']:
            top = r['facts'][:3]
            t.update(concept_meta=top, concept_facts=[f['text'] for f in top],
                     placebo_meta=r['placebo'][:3], placebo_facts=[f['text'] for f in r['placebo'][:3]],
                     tool_inputs=[f['witness_call'] for f in top if f['witness_call']], spec_facts=True)
    hybrid = copy.deepcopy(standard)
    for t in hybrid['tasks']:
        c = run_v4.mined_task(t, layout.precond, layout.strategy)
        for key in ('strategy_src', 'strategy_sha256', 'strategy_fallback', 'mining_summary'):
            t[key] = c[key]
        t['facts_version'] = 'v4'
        for key in ('concept_meta', 'placebo_meta'):
            for f in t[key]:
                if f['kind'] == 'MUTANT' and 'mutant_src' not in f:
                    f['mutant_src'] = ob.mutant_source(t['put'], f['k'])
    hybrid['facts_version'] = 'v4'
    v4_runtime.immutable(layout.all, standard)
    v4_runtime.immutable(layout.hybrid, hybrid)
    return standard, hybrid


def seed_reuse(layout, source):
    """Copy data, never link/write historical files or adopt old manifests/results."""
    source = Path(source).resolve()
    if source == layout.root.resolve():
        raise ValueError('reuse source must be separate from output')
    aliases = [(layout.precond, ['preconditions', 'precond_qwen7b_v4']),
               (layout.strategy, ['strategies', 'strategy_qwen7b_v4c']),
               (layout.facts, ['facts_v6', 'facts']), (layout.specfacts, ['specfacts', 'spec_facts_v7']),
               (layout.generation / 'cache', ['generation/cache', 'gen2_qwen7b_v7hyb_v4_r2/cache']),
               (layout.oracle / 'cache', ['oracle/cache', 'oracle_v7hyb/cache'])]
    if (source / 'cache').is_dir():
        target = layout.oracle if (source / 'calls.json').exists() else layout.generation
        aliases.append((target / 'cache', ['cache']))
    # A component directory itself is also a valid reuse source.
    names = {'precond_qwen7b_v4': layout.precond, 'strategy_qwen7b_v4c': layout.strategy,
             'facts_v6': layout.facts, 'spec_facts_v7': layout.specfacts}
    if source.name in names: aliases.append((names[source.name], ['.']))
    count = 0
    for target, choices in aliases:
        candidate = next((source / n for n in choices if (source / n).is_dir()), None)
        if candidate is None: continue
        for item in candidate.rglob('*'):
            if not item.is_file() or item.suffix not in ('.json', '.py'): continue
            dest = target / item.relative_to(candidate)
            paths.safe_output(dest)
            if dest.exists():
                if dest.read_bytes() != item.read_bytes():
                    raise ValueError(f'reuse collision: {dest}')
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(item, dest); count += 1
    print(f'reused {count} cache/data files into {layout.root}', flush=True)


def facts_stage(layout, python, workers):
    tasks, _, _ = task_sources(layout)
    layout.facts.mkdir(parents=True, exist_ok=True)
    def one(t):
        n = t['task']; out = layout.facts / f'{n}.json'
        if out.exists(): return
        cmd = ['timeout', '3600', 'unshare', '-rn', str(python), '-I', '-B',
               str(paths.HERE / 'facts.py'), str(n),
               str(layout.data['puts'] / f'HumanEval_{n}/put0.py'), str(layout.data['he']), str(out),
               '--validity', 'mined', '--precond-dir', str(layout.precond),
               '--contract-data', str(layout.data['contracts'])]
        r = subprocess.run(cmd, env=paths.worker_env(), capture_output=True, text=True)
        if r.returncode or not out.exists():
            raise RuntimeError(f'task {n}: facts worker failed rc={r.returncode}: {r.stderr[-1000:]}')
    with ThreadPoolExecutor(workers) as pool: list(pool.map(one, tasks))
    code_bundle(layout)  # Validate cached files too.
    print(f'facts: {len(tasks)}/{len(tasks)}', flush=True)


def specfacts_stage(layout, python, workers):
    from . import preconditions, spec_facts as sf
    layout.specfacts.mkdir(parents=True, exist_ok=True)
    tasks = [t for t in code_bundle(layout)['tasks'] if not t['concept_facts']]
    def one(t):
        _, _, params = preconditions.specification(t)
        job = dict(entry=t['entry'], base=sf.base_args(t['base']),
                   params=[a.arg for a in params.posonlyargs + params.args], valid_src=t['mined_valid_src'])
        jp, rp = layout.specfacts / f"{t['task']}.job.json", layout.specfacts / f"{t['task']}.json"
        if rp.exists():
            if jp.exists() and json.loads(jp.read_text()) != job:
                raise ValueError(f'spec-fact cache changed: task {t["task"]}')
            return
        jp.write_text(json.dumps(job, default=repr))
        r = subprocess.run(['timeout', '600', 'unshare', '-rn', str(python), '-I', '-B', sf.__file__,
                            'worker', str(jp), str(rp)], env=paths.worker_env(), capture_output=True)
        if r.returncode or not rp.exists():
            raise RuntimeError(f'task {t["task"]}: spec-facts worker failed rc={r.returncode}')
    with ThreadPoolExecutor(workers) as pool: list(pool.map(one, tasks))
    print(f'specfacts: {len(tasks)} tasks without code facts', flush=True)


def strict_stage(layout):
    from . import v8_strict_est as vs
    vs.SRC, vs.SRC_ORACLE = layout.generation, layout.oracle
    vs.RUN, vs.ORACLE = layout.root / 'strict/generation', layout.root / 'strict/oracle'
    vs.RUN.mkdir(parents=True, exist_ok=True)
    vs.build()  # Construction only; no endpoint, expected-value placeholders retained.


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('stage', choices=STAGES)
    ap.add_argument('--dataset', default='humaneval', help='humaneval or a normalized heldout he/ root')
    ap.add_argument('--reuse-from', type=Path, action='append', default=[])
    ap.add_argument('--python', type=Path)
    ap.add_argument('--workers', type=int, default=paths.CONFIG['workers'])
    ap.add_argument('--k', type=int, default=paths.CONFIG['K'])
    ap.add_argument('--arms',nargs='+',help='arm names; defaults to config arms')
    ap.add_argument('--online', action='store_true', help='explicitly enable the copied endpoint client')
    ap.add_argument('--oracle-stages', default='ref')
    a = ap.parse_args()
    if a.workers < 1 or not 1 <= a.k < 1000: ap.error('positive workers; K=1..999 required')
    paths.set_dataset(a.dataset)
    from . import evaluate, oracle_b01 as ob, run_v4, v4_runtime
    from .llm_client import Client
    layout = Layout(a.dataset); layout.root.mkdir(parents=True, exist_ok=True)
    for source in a.reuse_from: seed_reuse(layout, source)
    python = v4_runtime.interpreter(a.python)
    # All modules imported only after selecting the dataset; workers carry the same selection.
    run_v4.safe_path = paths.safe_output
    ob.Client = lambda directory, **kw: Client(directory, offline=not a.online, model=paths.CONFIG['model'], **kw)
    if a.stage == 'mine':
        tasks, _, _ = task_sources(layout)
        pending = []
        for t in tasks:
            if (layout.precond / str(t['task']) / 'summary.json').exists() and (layout.strategy / str(t['task']) / 'summary.json').exists():
                run_v4.mined_task(t, layout.precond, layout.strategy)
            else: pending.append(t)
        if pending:
            run_v4.mine(pending, Client(layout.strategy / 'cache', offline=not a.online, workers=a.workers),
                        layout.precond, layout.strategy, python, a.workers)
        print(f'mine: {len(tasks)} ready ({len(pending)} processed)')
    elif a.stage == 'facts': facts_stage(layout, python, a.workers)
    elif a.stage == 'specfacts': specfacts_stage(layout, python, a.workers)
    elif a.stage == 'bundle':
        _, hybrid = bundle(layout); print(f'bundle: {len(hybrid["tasks"])} tasks')
    elif a.stage == 'arms':
        tasks = json.loads(layout.hybrid.read_text())['tasks']
        run_v4.run(tasks, layout.generation, python, k=a.k, workers=a.workers,
                   client=Client(layout.generation / 'cache', offline=not a.online, workers=a.workers), arms=a.arms)
    elif a.stage == 'evaluate':
        evaluate.evaluate(layout.generation / 'tasks.json', layout.generation / 'gen.jsonl', layout.generation / 'eval.jsonl', python)
    elif a.stage == 'oracle-collect': ob.collect(layout.generation, layout.oracle)
    elif a.stage == 'oracle-llm':
        manifest = json.loads((layout.generation/'manifest.json').read_text())
        if manifest.get('relation_version') and a.oracle_stages != 'ref':
            ap.error('B3 oracle is ref only')
        ob.llm(layout.generation, layout.oracle, workers=a.workers, stages=tuple(a.oracle_stages.split(',')))
    elif a.stage == 'oracle-score':
        manifest = json.loads((layout.generation/'manifest.json').read_text())
        if manifest.get('relation_version'):
            from .rel_report import report
            report(layout.generation,layout.oracle,a.workers)
        else: ob.score(layout.generation, layout.oracle, workers=a.workers, use_llm=True)
    elif a.stage == 'strict': strict_stage(layout)
    else:
        from .v4_evaluation import report
        report(layout.generation / 'tasks.json',layout.generation / 'eval.jsonl')


if __name__ == '__main__': main()
