"""CPU check for class-method PUTs (VibePass): v7 vs v7_vp facts, counted per kind and per code location.

Runs pipelines/<version>/facts.py (unchanged worker CLI) for both versions in `unshare -rn ... -I -B`, with
`--validity evalplus` (the held-out root's embedded contract, no LLM) and/or `--validity none` (the smoke check
in BUILD_REPORT.md), writing only below out/pipelines/v7_vp/<dataset>/vp_check/. Each fact is located by its
line: inside a method of a class (`class`), inside the module-level entry wrapper (`wrapper`), or elsewhere.

    python -B -m trickcatcher_linefacts.pipelines.v7_vp.vp_check \
        --dataset trickcatcher_linefacts/out/heldout_vibepass_real/he --tasks 3,103,120
"""
from __future__ import annotations
import argparse
import ast
import json
import subprocess
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from . import paths

VERSIONS = ('v7', 'v7_vp')


def regions(src, entry):
    tree = ast.parse(src)
    cls = {i for c in ast.walk(tree) if isinstance(c, ast.ClassDef)
           for f in c.body if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))
           for i in range(f.lineno, f.end_lineno + 1)}
    wrap = {i for f in tree.body if isinstance(f, ast.FunctionDef) and f.name == entry
            for i in range(f.lineno, f.end_lineno + 1)}
    return cls, wrap


def where(line, cls, wrap):
    return 'class' if line in cls else 'wrapper' if line in wrap else 'other'


def slot(f):  # facts.slot, without importing the worker module (it sets process limits)
    return 'MUTANT-X' if f.get('extended') else f['kind']


def summarize(result, src):
    cls, wrap = regions(src, result['entry'])
    out = dict(total=len(result['facts']), base_ok=result['base_ok'])
    for name, key in (('facts', lambda f: True), ('reached', lambda f: f['reached'])):
        c = Counter(f"{where(f['line'], cls, wrap)}:{slot(f)}" for f in result['facts'] if key(f))
        out[name] = dict(sorted(c.items()))
    out['boundary_mutants'] = dict(Counter(where(f['line'], cls, wrap) for f in result['facts']
                                           if f['kind'] == 'MUTANT' and f.get('boundary')))
    out['mutants'] = sorted([f['text'], f['reached']] for f in result['facts'] if f['kind'] == 'MUTANT')
    out['top3'] = [f"{where(result['facts'][i]['line'], cls, wrap)}:{slot(result['facts'][i])}" for i in result['top3']]
    return out


def run(root, tasks, validities, python, workers, out_root):
    data = paths.dataset_paths(str(root))
    he = {int(r['task_id'].split('/')[1]): r for r in map(json.loads, data['he'].read_text().splitlines())}
    jobs = [(v, val, n) for v in VERSIONS for val in validities for n in tasks]

    def one(job):
        version, validity, n = job
        out = out_root / f'{version}-{validity}' / f'{n}.json'
        if not out.exists():
            out.parent.mkdir(parents=True, exist_ok=True)
            cmd = ['timeout', '3600', 'unshare', '-rn', str(python), '-I', '-B',
                   str(paths.REPO / 'trickcatcher_linefacts/pipelines' / version / 'facts.py'), str(n),
                   str(data['puts'] / f'HumanEval_{n}/put0.py'), str(data['he']), str(out),
                   '--validity', validity, '--contract-data', str(data['contracts'])]
            env = dict(paths.worker_env(), LINEFACTS_DATASET=str(root))
            r = subprocess.run(cmd, env=env, capture_output=True, text=True)
            if r.returncode or not out.exists():
                return job, dict(error=f'rc={r.returncode}: {r.stderr[-400:]}')
        src = (data['puts'] / f'HumanEval_{n}/put0.py').read_text()
        return job, summarize(json.loads(out.read_text()), src)

    with ThreadPoolExecutor(workers) as pool:
        results = list(pool.map(one, jobs))
    report = {}
    for (version, validity, n), s in results:
        report.setdefault(f'{version}-{validity}', {})[n] = s
    agg = {}
    for name, per in report.items():
        a = dict(tasks=len(per), errors=[n for n, s in per.items() if 'error' in s],
                 facts=Counter(), reached=Counter(), top3=Counter(),
                 tasks_with_class_nonmutant=sum(any(k.startswith('class:') and 'MUTANT' not in k for k in s.get('facts', {}))
                                                for s in per.values()))
        for s in per.values():
            for key in ('facts', 'reached'):
                a[key].update(s.get(key, {}))
            a['top3'].update(s.get('top3', []))
            a.setdefault('boundary_mutants', Counter()).update(s.get('boundary_mutants', {}))
        agg[name] = {k: dict(sorted(v.items())) if isinstance(v, Counter) else v for k, v in a.items()}
    for validity in validities:  # mutant facts: same texts and reached flags in both versions?
        old, new = report.get(f'v7-{validity}', {}), report.get(f'v7_vp-{validity}', {})
        diff = {n: dict(only_v7=[m for m in old[n]['mutants'] if m not in new[n]['mutants']],
                        only_v7_vp=[m for m in new[n]['mutants'] if m not in old[n]['mutants']])
                for n in tasks if 'mutants' in old.get(n, {}) and 'mutants' in new.get(n, {})}
        agg[f'mutant_diff-{validity}'] = {n: d for n, d in diff.items() if d['only_v7'] or d['only_v7_vp']}
    return dict(tasks=tasks, per_task=report, aggregate=agg)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--dataset', required=True, help='held-out he/ root (VibePass layout)')
    ap.add_argument('--tasks', help='comma-separated task ids (default: all in tasks.json)')
    ap.add_argument('--validity', default='evalplus,none')
    ap.add_argument('--python', type=Path)
    ap.add_argument('--workers', type=int, default=paths.CONFIG['workers'])
    a = ap.parse_args()
    root = Path(a.dataset).expanduser().resolve()
    paths.set_dataset(str(root))
    from . import v4_runtime
    selection = json.loads(paths.dataset_paths()['selection'].read_text())['tasks']
    tasks = [int(x) for x in a.tasks.split(',')] if a.tasks else [t['task'] for t in selection]
    out_root = paths.DATA_OUT / 'vp_check'
    report = run(root, tasks, a.validity.split(','), v4_runtime.interpreter(a.python), a.workers, out_root)
    name = 'report_all.json' if not a.tasks else f"report_{'_'.join(map(str, tasks))}.json"
    (out_root / name).write_text(json.dumps(report, indent=1) + '\n')
    print(json.dumps(report['aggregate'], indent=1))
    print(f'wrote {out_root / name}')


if __name__ == '__main__':
    main()
