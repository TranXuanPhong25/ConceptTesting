"""DEV-only v3mm/v5 versus v3m2 using the frozen v3m2 worker and metric tables."""
import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from trickcatcher_linefacts import offline, offline_metrics_v3m as metrics, preconditions, run_v5
from trickcatcher_linefacts.llm_client import atomic_json


def evaluate(experiment, tasks_path, facts_dir, out_dir, python, workers=12, ids=None):
    if os.environ.get('OFFLINE_SKIP_PILOT', '1') != '1': raise ValueError('OFFLINE_SKIP_PILOT=1 required')
    bundle = json.loads(Path(tasks_path).read_text())
    excluded = offline.excluded()
    # Exclude pilot/design before opening labels or scheduling any plus workers.
    tasks = [t for t in bundle['tasks'] if t['split'] == 'dev' and t['task'] not in excluded
             and (ids is None or t['task'] in ids)]
    if not tasks: raise ValueError('no DEV tasks')
    versions = (experiment, 'v3m2', 'v3c', 'v3f'); frs = {}; old = {}
    for version in versions:
        fd = Path(facts_dir) if version == experiment else HERE/'out'/f'facts_{version}'
        frs[version] = {t['task']:json.loads((fd/f"{t['task']}.json").read_text()) for t in tasks}
        if version != experiment:
            od = HERE/'out'/f'offline_{version}'
            old[version] = {t['task']:json.loads((od/f"{t['task']}.json").read_text()) for t in tasks}
    config = dict(experiment=experiment, tasks_sha256=run_v5.digest(tasks), sources=run_v5.sources(),
                  facts_sha256={v:run_v5.digest(frs[v]) for v in versions},
                  old_labels_sha256={v:run_v5.digest(r) for v,r in old.items()})
    directory = run_v5.manifest(out_dir, config)
    def work(t):
        n = t['task']; fr = frs[experiment][n]
        if fr['experiment'] != experiment or fr['valid_sha256'] != t['valid_sha256']:
            raise ValueError('facts experiment/validator mismatch')
        path = directory/f'{n}.json'
        if not path.exists():
            row = run_v5.isolated('offline', dict(task=n, facts_path=str((Path(facts_dir)/f'{n}.json').resolve())),
                                  directory/'jobs'/str(n), python)
            atomic_json(path, row)
        return n, json.loads(path.read_text())
    with ThreadPoolExecutor(max_workers=workers) as pool: current = dict(pool.map(work, tasks))
    results = {}; labels = {}; strong = {}
    for version in versions:
        scored = []; zero = []; records = current if version == experiment else old[version]
        strong[version] = {}
        for t in tasks:
            n = t['task']; fr, row = frs[version][n], records[n]
            if row['task'] != n or len(row['concept']) != len(fr['facts']) or len(row['placebo']) != len(fr['placebo_all']):
                raise ValueError('offline task/fact mismatch')
            labels.setdefault(n, {})[version] = [row['n_plus'], row['n_fail']]
            strong[version][n] = any(metrics.pf(row['concept'][i]) is not None and
                                     metrics.pf(row['concept'][i]) >= .5 for i in fr['top3'])
            if not row['n_fail']: zero.append(n); continue
            scored.append(dict(n=n, base=row['n_fail']/row['n_plus'], fr=fr, nr=row,
                new_pf=[metrics.pf(h) for h in row['concept']], placebo_pf=[metrics.pf(h) for h in row['placebo']]))
        results[version] = dict(zero_fail_tasks=zero, cohorts={name:metrics.analyze(ts) for name,ts in
            {'overall':scored, 'even':[t for t in scored if t['n']%2 == 0], 'odd':[t for t in scored if t['n']%2]}.items() if ts})
    mismatch = {str(n):v for n,v in labels.items() if len({tuple(a) for a in v.values()}) > 1}
    if mismatch: print('WARNING: version-specific labels differ; retaining all labels: '+json.dumps(mismatch))
    wins = [n for n in strong[experiment] if strong[experiment][n] and not strong['v3m2'][n]]
    losses = [n for n in strong[experiment] if strong['v3m2'][n] and not strong[experiment][n]]
    paired = dict(better=wins, worse=losses, ties=len(tasks)-len(wins)-len(losses), sign_p=metrics.sign_p(len(wins),len(losses)))
    allowed = {int(n) for n in (HERE/'tasks.txt').read_text().split()} - excluded
    full = {t['task'] for t in tasks} == allowed
    selected = results[experiment].get('cohorts', {}).get('overall', {}).get('results', {}).get('selected@3', {})
    decision = dict(complete_dev=full, selected_strong=selected.get('strong'), scored_tasks=selected.get('n'),
                    threshold='44/112', mutant_source=None)
    if experiment == 'v3mm' and full and selected.get('n') == 112:
        decision['mutant_source'] = 'mutmut' if selected['strong'] >= 44 else 'handwritten'
    quality = dict(reach={v:{k:dict(total=sum(frs[v][t['task']]['counts'].get(k,0) for t in tasks),
                    reached=sum(frs[v][t['task']]['reached'].get(k,0) for t in tasks)) for k in metrics.facts.SLOTS} for v in versions},
                   paired_selected_at_3=paired, step1_rule=decision)
    atomic_json(directory/'dev_metrics.json', results)
    atomic_json(directory/'quality.json', quality)
    atomic_json(directory/'labels_by_version.json', labels)
    atomic_json(directory/'label_mismatch.json', mismatch)
    fmt = lambda v: 'undefined' if v is None else f'{v:.6g}'
    lines = [f'# {experiment} offline evaluation (DEV only)', '',
        'Frozen v3m2 metrics, gates and ranking. Each version retains its own official labels.', '',
        '| Cohort | Version | Variant | Tasks with facts | Strong | Mean PF | Matched base | Better/worse | Sign p | Tie/no score | Shown/scored |',
        '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for version,result in results.items():
        for cohort,body in result['cohorts'].items():
            for variant,m in body['results'].items():
                lines.append(f"| {cohort} | {version} | {variant} | {fmt(m['have_shown'])}/{m['n']} | {fmt(m['strong'])}/{m['n']} | {fmt(m['mean_pf'])} | {fmt(m['base'])} | {fmt(m['better'])}/{fmt(m['worse'])} | {fmt(m['sign_p'])} | {fmt(m['tie'])}/{fmt(m['no_score'])} | {fmt(m['shown'])}/{fmt(m['scored'])} |")
    lines += ['', f"Paired selected@3 strong versus v3m2: {len(wins)} better, {len(losses)} worse, sign p={paired['sign_p']:.6g}.",
              f'Step-1 rule (only full DEV): `{json.dumps(decision)}`.', '',
              '## Per-kind DEV diagnostics', '',
              '| Cohort | Version | Pool | Kind | Reached | Scored/reached | Mean PF | Matched base | Strong facts | Strong tasks |',
              '|---|---|---|---|---:|---:|---:|---:|---:|---:|']
    for version,result in results.items():
        for cohort,body in result['cohorts'].items():
            for pool in ('by_kind','shown_by_kind'):
                for kind,m in body[pool].items():
                    lines.append(f"| {cohort} | {version} | {pool} | {kind} | {m['reached']} | {fmt(m['valid_reach'])} | {fmt(m['mean_pf'])} | {fmt(m['base'])} | {m['strong_facts']} | {m['strong']}/{m['n']} |")
    (directory/'REPORT.md').write_text('\n'.join(lines)+'\n')
    print(f'offline report ready: {directory}/REPORT.md', flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('experiment', choices=('v3mm','v5'))
    p.add_argument('--tasks-path', type=Path)
    p.add_argument('--facts-dir', type=Path)
    p.add_argument('--out-dir', type=Path)
    p.add_argument('--python', type=Path)
    p.add_argument('--workers', type=int, default=12)
    p.add_argument('--task-ids', type=int, nargs='+')
    a = p.parse_args(); v = a.experiment
    evaluate(v, a.tasks_path or HERE/'out'/f'tasks_{v}_all.json', a.facts_dir or HERE/'out'/f'facts_{v}',
             a.out_dir or HERE/'out'/f'offline_{v}', run_v5.v4_runtime.interpreter(a.python), a.workers, a.task_ids)


if __name__ == '__main__': main()
