"""DEV-only v4 versus frozen v3m2/v3c/v3f offline tables; never opens pilot labels."""
import argparse
import ast
import contextlib
import io
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from trickcatcher_linefacts import (generate, offline, offline_metrics_v3m as metrics,
                                   preconditions, run_gen, run_v4, v4_runtime)
from trickcatcher_linefacts.llm_client import atomic_json


def worker(job,directory):
    from tracer import HOOKS, alarm, call, dcopy, fact_hit, instrument, load_module
    from trickcatcher_linefacts.v4_tools import Coverage
    task=job['task']; n=task['task']
    if task['split']!='dev' or n in offline.excluded(): raise ValueError('pilot/design offline evaluation forbidden')
    # Only dev records are selected; no pilot canonical program or labels are executed.
    hep=next(r for r in map(json.loads,offline.HEP.open()) if r['task_id']==f'HumanEval/{n}')
    pg=load_module(task['put']); put=pg[task['entry']]
    cur,rec,fail,pout=[None],{},{},{}
    def candidate(*args,**kwargs):
        rec[cur[0]]=(dcopy(args),dcopy(kwargs)); result=call(put,(args,kwargs)); pout[cur[0]]=result
        if result[0]!='ok': raise RuntimeError(result[0])
        return result[1]
    ns=dict(pg,__cur=cur,__fail=lambda i,e:fail.__setitem__(i,type(e).__name__))
    with contextlib.redirect_stdout(io.StringIO()),alarm(600):
        exec(offline.plus_check_src(hep['test']),ns); ns['check'](candidate)
    fr=job['facts']; code,_=instrument(task['put']); iput=load_module(code,HOOKS)[task['entry']]
    coverage=Coverage(task['put'],task['entry'],directory)
    tr={i:coverage.trace(iput,a) for i,a in rec.items()}
    groups={'concept':fr['facts'],'placebo':fr['placebo_all']}
    mutants={f['k']:load_module(f['mutant_src'])[task['entry']] for fs in groups.values() for f in fs if f['kind']=='MUTANT'}
    mouts={k:{i:call(fn,a) for i,a in rec.items()} for k,fn in mutants.items()}
    result=dict(task=n,n_plus=len(rec),n_fail=len(fail))
    for name,fs in groups.items():
        result[name]=[dict(fail_hits=sum(fact_hit(f,tr[i],pout[i],mouts.get(f.get('k'),{}).get(i)) for i in rec if i in fail),
                           pass_hits=sum(fact_hit(f,tr[i],pout[i],mouts.get(f.get('k'),{}).get(i)) for i in rec if i not in fail)) for f in fs]
    valid=preconditions.load_predicate(task['mined_valid_src'],'valid')
    from trickcatcher_linefacts.v4_evaluation import validity
    result['plus_validity']=dict(inputs=len(rec),rejected=sum(not validity(valid,a,True) for a in rec.values()))
    return result


def evaluate(tasks_path,facts_dir,out_dir,python=None,workers=12,ids=None):
    if os.environ.get('OFFLINE_SKIP_PILOT','1')!='1': raise ValueError('OFFLINE_SKIP_PILOT=1 required')
    tasks=json.loads(Path(tasks_path).read_text())['tasks']
    # Exclude pilots before reading any per-task offline labels or scheduling workers.
    tasks=[t for t in tasks if t['split']=='dev' and t['task'] not in offline.excluded() and (ids is None or t['task'] in ids)]
    if not tasks: raise ValueError('no dev tasks')
    out_dir=run_v4.safe_path(out_dir); out_dir.mkdir(parents=True,exist_ok=True)
    facts_dir=Path(facts_dir)
    versions=('v4','v3m2','v3c','v3f'); frs={}; old={}
    for version in versions:
        fd=facts_dir if version=='v4' else HERE/'out'/f'facts_{version}'
        frs[version]={t['task']:json.loads((fd/f"{t['task']}.json").read_text()) for t in tasks}
        if version!='v4':
            od=HERE/'out'/f'offline_{version}'
            old[version]={t['task']:json.loads((od/f"{t['task']}.json").read_text()) for t in tasks}
    manifest=dict(tasks_sha256=run_gen._digest(tasks),versions=versions,tools=v4_runtime.VERSIONS,
                  sources=v4_runtime.source_hashes(),facts_sha256={v:run_gen._digest(frs[v]) for v in versions},
                  old_labels_sha256={v:run_gen._digest(r) for v,r in old.items()})
    v4_runtime.immutable(out_dir/'manifest.json',manifest)
    def work(t):
        n=t['task']; fr=frs['v4'][n]
        if fr.get('facts_version')!='v4' or fr['valid_sha256']!=t['valid_sha256']: raise ValueError('v4 facts mismatch')
        path=out_dir/f'{n}.json'
        if not path.exists():
            result=v4_runtime.isolated('offline',dict(task=t,facts=fr),out_dir/'jobs'/str(n),python,3600)
            atomic_json(path,result)
        return n,json.loads(path.read_text())
    with ThreadPoolExecutor(max_workers=workers) as pool: current=dict(pool.map(work,tasks))
    results={}; labels={}; mismatch={}
    for version in versions:
        scored=[]; zero=[]; nr=current if version=='v4' else old[version]
        for t in tasks:
            n=t['task']; fr,r=frs[version][n],nr[n]
            if r['task']!=n or len(r['concept'])!=len(fr['facts']) or len(r['placebo'])!=len(fr['placebo_all']):
                raise ValueError('offline fact count mismatch')
            labels.setdefault(n,{})[version]=[r['n_plus'],r['n_fail']]
            if not r['n_fail']: zero.append(n); continue
            scored.append(dict(n=n,base=r['n_fail']/r['n_plus'],fr=fr,nr=r,
                               new_pf=[metrics.pf(h) for h in r['concept']],placebo_pf=[metrics.pf(h) for h in r['placebo']]))
        results[version]=dict(zero_fail_tasks=zero,cohorts={name:metrics.analyze(ts) for name,ts in
                        {'overall':scored,'even':[t for t in scored if t['n']%2==0],'odd':[t for t in scored if t['n']%2]}.items() if ts})
    mismatch={str(n):v for n,v in labels.items() if len({tuple(a) for a in v.values()})>1}
    if mismatch: print('WARNING: version-specific labels differ (hash-order-sensitive PUTs 34/58); retaining all labels: '+json.dumps(mismatch))
    reach={v:{kind:dict(total=sum(frs[v][t['task']]['counts'].get(kind,0) for t in tasks),
                       reached=sum(frs[v][t['task']]['reached'].get(kind,0) for t in tasks))
              for kind in metrics.facts.SLOTS} for v in versions}
    def fuzz_stat(fr):
        s=fr.get('fuzz_validity',{}); checked=s.get('checked',0); accepted=s.get('accepted',checked-s.get('invalid',0))
        return dict(attempts=s.get('attempts',0),checked=checked,valid=accepted,kept=fr['n_fuzz'],
                    validity_rate=accepted/checked if checked else None,unique_yield=fr['n_fuzz']/max(1,s.get('attempts',0)))
    quality=dict(fuzz_validity=[dict(task=t['task'],v4=fuzz_stat(frs['v4'][t['task']]),v3c=fuzz_stat(frs['v3c'][t['task']])) for t in tasks],
                 mining=[t['mining_summary'] for t in tasks],
                 strategy_fallback_tasks=[t['task'] for t in tasks if t['strategy_fallback']],
                 reach=reach,plus_validity={str(n):r['plus_validity'] for n,r in current.items()},
                 string_format_tasks={str(t['task']):dict(facts_v4=frs['v4'][t['task']]['counts'],fuzz=fuzz_stat(frs['v4'][t['task']])) for t in tasks if t['task'] in (17,19)})
    atomic_json(out_dir/'dev_metrics.json',results); atomic_json(out_dir/'quality.json',quality)
    atomic_json(out_dir/'label_mismatch.json',mismatch); atomic_json(out_dir/'labels_by_version.json',labels)
    fmt=lambda v:'undefined' if v is None else f'{v:.6g}'
    lines=['# v4 offline evaluation (DEV only)','',
           'Frozen gates and ranking remain fixed. Each version keeps its own official labels; tasks 34/58 can vary with hash order.','',
           '| Cohort | Version | Variant | Tasks with facts | Strong | Mean PF | Matched base | Better/worse | Sign p | Tie/no score | Shown/scored |',
           '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for v,body in results.items():
        for cohort,data in body['cohorts'].items():
            for variant,m in data['results'].items():
                lines.append(f"| {cohort} | {v} | {variant} | {fmt(m['have_shown'])}/{m['n']} | {fmt(m['strong'])}/{m['n']} | {fmt(m['mean_pf'])} | {fmt(m['base'])} | {fmt(m['better'])}/{fmt(m['worse'])} | {fmt(m['sign_p'])} | {fmt(m['tie'])}/{fmt(m['no_score'])} | {fmt(m['shown'])}/{fmt(m['scored'])} |")
    lines += ['', '## Per-kind DEV diagnostics','', '| Cohort | Version | Pool | Kind | Reached | Scored/reached | Mean PF | Matched base | Strong facts | Strong tasks |',
              '|---|---|---|---|---:|---:|---:|---:|---:|---:|']
    for v,body in results.items():
        for cohort,data in body['cohorts'].items():
            for pool in ('by_kind','shown_by_kind'):
                for kind,m in data[pool].items():
                    lines.append(f"| {cohort} | {v} | {pool} | {kind} | {m['reached']} | {fmt(m['valid_reach'])} | {fmt(m['mean_pf'])} | {fmt(m['base'])} | {m['strong_facts']} | {m['strong']}/{m['n']} |")
    lines += ['', '## Fuzz validity','', '| Task | v4 valid/checked | v4 rate | v3c valid/checked | v3c rate | v4/v3c kept |', '|---|---:|---:|---:|---:|---:|']
    for r in quality['fuzz_validity']:
        a,b=r['v4'],r['v3c']; lines.append(f"| {r['task']} | {a['valid']}/{a['checked']} | {fmt(a['validity_rate'])} | {b['valid']}/{b['checked']} | {fmt(b['validity_rate'])} | {a['kept']}/{b['kept']} |")
    lines += ['', '## B5 mining quality','',
              '| Task | Candidates | Confirmed | Surviving | Plus inputs | Plus rejected |', '|---|---:|---:|---:|---:|---:|']
    for m in quality['mining']:
        p=quality['plus_validity'][str(m['task'])]
        lines.append(f"| {m['task']} | {m['candidates']} | {m['confirmed']} | {m['surviving']} | {p['inputs']} | {p['rejected']} |")
    lines += ['', 'Fallback strategies: '+str(quality['strategy_fallback_tasks']), '', '## Dropped condition examples','']
    for m in quality['mining']:
        for drop in m['dropped_confirmation'][:2]: lines.append(f"- Task {m['task']}: {drop}")
        for drop in m['dropped_verifier'][:2]: lines.append(f"- Task {m['task']}: {drop}")
    lines += ['', '## String-format tasks 17 and 19','',json.dumps(quality['string_format_tasks'],indent=1),
              '', '## Reach by kind','',json.dumps(reach,indent=1), '', '## Label warnings','',json.dumps(mismatch,indent=1)]
    (out_dir/'REPORT.md').write_text('\n'.join(lines)+'\n')
    print(f'offline v4 report ready: {out_dir}/REPORT.md')
    return results


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tasks',type=Path,default=HERE/'out/tasks_v4_all.json')
    p.add_argument('--facts-dir',type=Path,default=HERE/'out/facts_v4')
    p.add_argument('--out-dir',type=Path,default=HERE/'out/offline_v4')
    p.add_argument('--python',type=Path,default=os.environ.get('V4_PYTHON'))
    p.add_argument('--workers',type=int,default=12);p.add_argument('--task-ids',type=int,nargs='+')
    a=p.parse_args();evaluate(a.tasks,a.facts_dir,a.out_dir,a.python,a.workers,a.task_ids)


if __name__=='__main__':main()
