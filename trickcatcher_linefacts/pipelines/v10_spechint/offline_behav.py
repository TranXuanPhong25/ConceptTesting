"""DEV-only HumanEval+ labels for measurement; never used in mining or selection."""
import contextlib
import io
import json
from concurrent.futures import ThreadPoolExecutor
from . import behaviour, facts, offline, paths, preconditions, v4_runtime
from .llm_client import atomic_json


def identity(f):
    return json.dumps(f, sort_keys=True)


def measure(task, hep):
    """Isolated worker: official HumanEval+ assertions label PUT calls as in offline.py."""
    from .tracer import HOOKS, alarm, call, dcopy, fact_hit, instrument, load_module, trace
    if task['split'] != 'dev':
        raise ValueError('offline-behav requires DEV tasks')
    pg = load_module(task['put']); put = pg[task['entry']]
    valid = preconditions.load_predicate(task['mined_valid_src'], 'valid')
    cur, rec, fail, pout = [None], {}, {}, {}

    def candidate(*args, **kwargs):
        rec[cur[0]] = (dcopy(args), dcopy(kwargs))
        result = call(put, (args, kwargs)); pout[cur[0]] = result
        if result[0] != 'ok': raise RuntimeError(result[0])
        return result[1]

    ns = dict(pg, __cur=cur, __fail=lambda i, exc: fail.__setitem__(i, type(exc).__name__))
    with contextlib.redirect_stdout(io.StringIO()), alarm(600):
        exec(offline.plus_check_src(hep['test']), ns)
        ns['check'](candidate)
    pool, seen = [], set()
    for f in task['behav_pool'] + task['v7_concept_meta'] + task['concept_meta']:
        key = identity(f)
        if key not in seen: pool.append(f); seen.add(key)
    code, _ = instrument(task['put']); iput = load_module(code, HOOKS)[task['entry']]
    traces = {i: trace(iput, inputs) for i, inputs in rec.items()}
    mutants = {}
    for f in pool:
        if f['kind'] == 'MUTANT' and f['k'] not in mutants:
            if 'mutant_src' in f: src = f['mutant_src']
            else:
                from . import oracle_b01
                src = oracle_b01.mutant_source(task['put'], f['k'])
            mutants[f['k']] = load_module(src)[task['entry']]
    mouts = {k: {i: call(fn, inputs) for i, inputs in rec.items()} for k, fn in mutants.items()}
    scored = []
    for f in pool:
        hits = [i for i in rec if fact_hit(f, traces[i], pout[i], mouts.get(f.get('k'), {}).get(i),
                                          args=rec[i], valid=valid)]
        n, bad = len(hits), sum(i in fail for i in hits)
        scored.append(dict(fact=f, fail_hits=bad, pass_hits=n-bad, hits=n, pf=bad/n if n else None))
    return dict(task=task['task'], n_plus=len(rec), n_fail=len(fail), facts=scored)


def report(tasks, measurements):
    rows, examples = [], []
    for t in tasks:
        r = measurements[t['task']]
        scores = {identity(x['fact']): x for x in r['facts']}
        pools = dict(v7=t['v7_concept_meta'], v10=t['concept_meta'], behav_pool=t['behav_pool'],
                     behav_top3=facts.pick(t['behav_pool'], t['task'], extra_slots=('BEHAV',)))
        good = {name: any(scores[identity(f)]['pf'] is not None and
                          scores[identity(f)]['pf'] >= .5 for f in pool) for name, pool in pools.items()}
        rows.append(dict(task=t['task'], n_plus=r['n_plus'], n_fail=r['n_fail'], good=good,
                         coverage={name: bool(pool) for name, pool in pools.items()}))
        for f in t['behav_pool']:
            score = scores[identity(f)]
            examples.append(dict(task=t['task'], statement=f['statement'], quote=f['quote'],
                                 selected=f in t['concept_meta'], witness_call=f.get('witness_call'),
                                 **{k: score[k] for k in ('fail_hits', 'pass_hits', 'hits', 'pf')}))
    cohorts = {}
    for name, group in (('all', rows), ('even', [r for r in rows if r['task'] % 2 == 0]),
                        ('odd', [r for r in rows if r['task'] % 2])):
        bug = [r for r in group if r['n_fail'] > 0]
        cohorts[name] = dict(n_dev=len(group), n_bug_tasks=len(bug),
            zero_fail_tasks=[r['task'] for r in group if not r['n_fail']],
            good_at_3={kind: dict(tasks=[r['task'] for r in bug if r['good'][kind]],
                                 count=sum(r['good'][kind] for r in bug),
                                 rate=sum(r['good'][kind] for r in bug)/len(bug) if bug else None)
                       for kind in ('v7', 'v10', 'behav_top3')},
            behav_pool_good=[r['task'] for r in bug if r['good']['behav_pool']],
            coverage={kind: sum(r['coverage'][kind] for r in group) for kind in ('v7', 'v10', 'behav_pool')},
            newly_covered=[r['task'] for r in group if r['coverage']['v10'] and not r['coverage']['v7']],
            newly_good=[r['task'] for r in bug if r['good']['v10'] and not r['good']['v7']],
            lost_good=[r['task'] for r in bug if r['good']['v7'] and not r['good']['v10']])
    return dict(version=paths.VERSION,
        definition='PF=fail_hits/(fail_hits+pass_hits); good@3=any shown fact PF>=0.5; '
                   'good@3 denominator excludes zero-failing-input tasks, as offline.py; coverage uses all DEV tasks',
        cohorts=cohorts, tasks=rows, examples=examples,
        measurements=[measurements[t['task']] for t in tasks])


def evaluate(layout, python, workers):
    tasks = json.loads(layout.all.read_text())['tasks']
    bundle = json.loads(layout.all.read_text())
    excluded = set(bundle.get('pilot', [])) | set(bundle.get('design_excluded', []))
    tasks = [t for t in tasks if t['split'] == 'dev' and t['task'] not in excluded]
    if not tasks: raise ValueError('no eligible DEV tasks')
    ids = {t['task'] for t in tasks}
    hep = {int(r['task_id'].split('/')[1]): r for r in map(json.loads, layout.data['hep'].read_text().splitlines())
           if int(r['task_id'].split('/')[1]) in ids}
    out = layout.root / 'offline_behav'; out.mkdir(parents=True, exist_ok=True)
    sources = {p: preconditions.sha((paths.HERE / p).read_bytes()) for p in
               ('offline_behav.py', 'behav_facts.py', 'tracer.py', 'offline.py', 'preconditions.py', 'facts.py')}
    v4_runtime.immutable(out / 'manifest.json', dict(tasks_sha256=preconditions.sha(json.dumps(tasks, sort_keys=True)),
        labels_sha256=preconditions.sha(json.dumps(hep, sort_keys=True)), sources=sources))

    def one(t):
        rp = out / f"{t['task']}.json"
        if not rp.exists():
            r = behaviour.isolated(dict(mode='offline', task=t, hep=hep[t['task']]),
                                   out / 'jobs' / str(t['task']), 'offline', python, timeout=3600)
            atomic_json(rp, r)
        return t['task'], json.loads(rp.read_text())

    with ThreadPoolExecutor(workers) as pool: measured = dict(pool.map(one, tasks))
    result = report(tasks, measured)
    atomic_json(out / 'report.json', result)
    lines = ['# v10_spechint offline-behav (DEV only)', '', result['definition'], '',
             '| Split | Bug tasks | v7 good@3 | v10 good@3 | BEHAV alone good@3 | Newly covered | Newly good | Lost good |',
             '|---|---:|---:|---:|---:|---|---|---|']
    for name, r in result['cohorts'].items():
        counts = [r['good_at_3'][kind]['count'] for kind in ('v7', 'v10', 'behav_top3')]
        lines.append(f'| {name} | {r["n_bug_tasks"]} | {counts[0]} | {counts[1]} | {counts[2]} | '
                     f'{r["newly_covered"]} | {r["newly_good"]} | {r["lost_good"]} |')
    lines += ['', '## Every BEHAV fact (including unshown facts)', '']
    for x in result['examples']:
        lines.append(f'- Task {x["task"]}, shown={x["selected"]}: {x["statement"]}; '
                     f'quote={json.dumps(x["quote"])}; PF={x["fail_hits"]}/{x["hits"]} '
                     f'({x["pf"]}); witness={x["witness_call"]}')
    (out / 'report.md').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines[:10]))
