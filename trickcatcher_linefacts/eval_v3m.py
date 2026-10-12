"""Offline v3m evaluation only: contract agreement (133) and DEV-only plus/PF tables."""
from __future__ import annotations
import argparse
import ast
import contextlib
import io
import json
import os
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from trickcatcher_linefacts import gen_inputs, generate, preconditions, run_gen
from trickcatcher_linefacts.llm_client import atomic_json


def worker(job_path, output_path):
    from trickcatcher_linefacts import facts, offline
    from trickcatcher_linefacts.tracer import alarm, dcopy, load_module, run_base
    job = json.loads(Path(job_path).read_text())
    n = job['task']
    if n in run_gen.DESIGN:
        raise ValueError('design evaluation is forbidden')
    src = (generate.PUTS/f'HumanEval_{n}/put0.py').read_text()
    he = next(r for r in map(json.loads, generate.HE.open()) if r['task_id']==f'HumanEval/{n}')
    with alarm(5):
        pg = load_module(src)
        mined = preconditions.load_predicate(Path(job['valid_path']).read_text(), 'valid')
        row = gen_inputs.load_contracts(job['contract_data'])[n]
        contract = load_module(row['contract_src'])[row['entry']]
    base, ok = run_base(pg[he['entry_point']], he['test'], ns=pg)
    if ok is not True:
        raise ValueError('base capture failed')
    facts.CONSTS[:] = sorted({node.value for node in ast.walk(ast.parse(src)) if isinstance(node, ast.Constant)
                              and isinstance(node.value, (int,float)) and not isinstance(node.value,bool)
                              and abs(node.value)<10**6} - {0,1,-1})[:12]
    draws = facts.fuzz_inputs(base, random.Random(facts.SEED+n), valid=None)

    def accepts(fn, args, boolean):
        try:
            with alarm(1):
                result=fn(*dcopy(args[0]), **dcopy(args[1]))
            return result is True if boolean else True
        except BaseException:
            return False

    counts = dict(both_valid=0, mined_only=0, contract_only=0, both_invalid=0)
    for args in draws:
        m,c = accepts(mined,args,True),accepts(contract,args,False)
        counts['both_valid' if m and c else 'mined_only' if m else 'contract_only' if c else 'both_invalid'] += 1
    result = dict(task=n, draws=len(draws), counts=counts)
    if job['dev']:
        if n in offline.excluded():
            raise ValueError('pilot/design plus evaluation forbidden')
        # Capture actual Python arguments, preserving EvalPlus test-side conversions.
        # No expected values, canonical execution, or failure labels enter the method.
        hep = next(r for r in map(json.loads, offline.HEP.open()) if r['task_id']==f'HumanEval/{n}')
        captured = {}
        current=[None]
        def candidate(*args, **kwargs):
            captured[current[0]]=(dcopy(args),dcopy(kwargs))
            raise RuntimeError('capture only')
        namespace=dict(pg, __cur=current, __fail=lambda *args: None)
        with alarm(120), contextlib.redirect_stdout(io.StringIO()):
            exec(offline.plus_check_src(hep['test']), namespace)
            namespace['check'](candidate)
        rejected=sum(not accepts(mined,a,True) for a in captured.values())
        result['plus']=dict(inputs=len(captured),rejected=rejected,rejection_rate=rejected/len(captured) if captured else None)
    atomic_json(output_path,result)


def agreement(counts):
    b,m,c=counts['both_valid'],counts['mined_only'],counts['contract_only']
    total=sum(counts.values())
    return dict(counts=counts, valid_precision=b/(b+m) if b+m else None,
                valid_recall=b/(b+c) if b+c else None, agreement=(b+counts['both_invalid'])/total if total else None)


def evaluate(ids, precond_dir, facts_dir, out_dir, contract_data, workers=12):
    from trickcatcher_linefacts import offline, offline_metrics_v3m as metrics
    if os.environ.get('OFFLINE_SKIP_PILOT','1')!='1':
        raise ValueError('OFFLINE_SKIP_PILOT=1 is required')
    allowed={int(n) for n in (HERE/'tasks.txt').read_text().split()}-run_gen.DESIGN
    if len(set(ids))!=len(ids) or not set(ids)<=allowed:
        raise ValueError('only distinct non-design tasks are permitted')
    excluded=offline.excluded()
    dev=[n for n in ids if n not in excluded]
    out_dir=Path(out_dir).resolve()
    if out_dir in [HERE/'out'/name for name in ('offline','offline_v2','offline_v3','offline_v3f','offline_v3c')]:
        raise ValueError('protected offline output directory')
    plan=json.loads((HERE/'eval_plan_v3m.json').read_text())
    # Require all requested mining/facts artifacts before opening evaluation data.
    for n in ids:
        summary=json.loads((Path(precond_dir)/str(n)/'summary.json').read_text())
        fr=json.loads((Path(facts_dir)/f'{n}.json').read_text())
        digest=preconditions.sha((Path(precond_dir)/str(n)/'valid.py').read_bytes())
        if digest!=summary['valid_sha256'] or digest!=fr.get('valid_sha256') or fr.get('facts_version')!='v3m':
            raise ValueError('mined validator/facts mismatch')
    out_dir.mkdir(parents=True,exist_ok=True)
    provenance=dict(plan=plan,ids=ids,
                    validators={str(n):preconditions.sha((Path(precond_dir)/str(n)/'valid.py').read_bytes()) for n in ids},
                    facts={str(n):preconditions.sha((Path(facts_dir)/f'{n}.json').read_bytes()) for n in ids},
                    sources={p:preconditions.sha((HERE/p).read_bytes()) for p in ('eval_v3m.py','offline.py','offline_metrics_v3m.py')})
    manifest=out_dir/'eval_manifest.json'
    if manifest.exists() and json.loads(manifest.read_text())!=provenance:
        raise ValueError('evaluation manifest changed; use a fresh output directory')
    atomic_json(manifest,provenance)
    def task(n):
        directory=out_dir/'quality'/str(n);directory.mkdir(parents=True,exist_ok=True)
        jp,op=directory/'job.json',directory/'result.json'
        atomic_json(jp,dict(task=n,dev=n in dev,valid_path=str((Path(precond_dir)/str(n)/'valid.py').resolve()),contract_data=str(Path(contract_data).resolve())))
        if not op.exists():
            gen_inputs.sandbox(sys.executable,Path(__file__),jp,op,3600)
        if n in dev and not (out_dir/f'{n}.json').exists():
            # offline.py uses exactly the frozen worker; no pilot ids are submitted.
            import subprocess
            env={'PATH':os.defpath,'LANG':'C.UTF-8','OFFLINE_SKIP_PILOT':'1','PYTHONDONTWRITEBYTECODE':'1'}
            subprocess.run(['unshare','-rn',sys.executable,'-I','-B',str(HERE/'offline.py'),'worker',str(n),
                            str((Path(facts_dir)/f'{n}.json').resolve()),str(out_dir/f'{n}.json')],
                           env=env,check=True,timeout=3600,stdout=subprocess.DEVNULL)
        row=json.loads(op.read_text())
        if n in dev and row['plus']['inputs'] != json.loads((out_dir/f'{n}.json').read_text())['n_plus']:
            raise ValueError('plus capture count differs from frozen offline worker')
        row.update(agreement(row['counts']))
        row['mining']=json.loads((Path(precond_dir)/str(n)/'summary.json').read_text())
        return row
    with ThreadPoolExecutor(max_workers=workers) as pool:
        rows=list(pool.map(task,ids))
    counts={key:sum(r['counts'][key] for r in rows) for key in rows[0]['counts']}
    quality=dict(per_task=rows,pooled=agreement(counts),
                 accepts_everything=[r['task'] for r in rows if r['draws'] and r['counts']['both_valid']+r['counts']['mined_only']==r['draws']],
                 rejects_everything=[r['task'] for r in rows if r['draws'] and r['counts']['both_valid']+r['counts']['mined_only']==0])
    plus=[r['plus'] for r in rows if 'plus' in r]
    np=sum(p['inputs'] for p in plus);nr=sum(p['rejected'] for p in plus)
    quality['dev_plus']=dict(inputs=np,rejected=nr,rejection_rate=nr/np if np else None)
    atomic_json(out_dir/'quality.json',quality)
    results={};labels={};mismatch={}
    for version in ('v3m','v3c','v3f'):
        tasks=[];zero=[]
        for n in dev:
            fd=Path(facts_dir) if version=='v3m' else HERE/'out'/f'facts_{version}'
            od=out_dir if version=='v3m' else HERE/'out'/f'offline_{version}'
            fr=json.loads((fd/f'{n}.json').read_text());nr=json.loads((od/f'{n}.json').read_text())
            if nr['task']!=n or len(nr['concept'])!=len(fr['facts']) or len(nr['placebo'])!=len(fr['placebo_all']):
                raise ValueError('offline task/fact mismatch')
            label=(nr['n_plus'],nr['n_fail'])
            if n in labels and labels[n]!=label:
                # PUTs returning list(set(...)) (tasks 34, 58) fail hash-order dependently; each version keeps its own labels
                mismatch.setdefault(n,{})[version]=label
            labels.setdefault(n,label)
            if not nr['n_fail']:
                zero.append(n);continue
            tasks.append(dict(n=n,base=nr['n_fail']/nr['n_plus'],fr=fr,nr=nr,
                              new_pf=[metrics.pf(h) for h in nr['concept']],placebo_pf=[metrics.pf(h) for h in nr['placebo']]))
        results[version]=dict(zero_fail_tasks=zero,cohorts={name:metrics.analyze(ts) for name,ts in
                               {'overall':tasks,'even':[t for t in tasks if t['n']%2==0],'odd':[t for t in tasks if t['n']%2]}.items() if ts})
    atomic_json(out_dir/'label_mismatch.json',{str(k):v for k,v in mismatch.items()})
    atomic_json(out_dir/'dev_metrics.json',results)
    lines=['# v3m offline evaluation (DEV only for HumanEval+)','',
           'No settings or method changes follow from these results. Detailed counts, dropped constraints, per-task metrics and per-kind tables are in quality.json and dev_metrics.json.','',
           '| Cohort | Version | Variant | Tasks with facts | Strong | Mean PF | Matched base | Better/worse | Sign p | Tie/no score | Shown/scored |',
           '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    def fmt(v):return 'undefined' if v is None else f'{v:.6g}'
    for version,result in results.items():
        for cohort,body in result['cohorts'].items():
            for variant,m in body['results'].items():
                lines.append(f"| {cohort} | {version} | {variant} | {fmt(m['have_shown'])}/{m['n']} | {fmt(m['strong'])}/{m['n']} | {fmt(m['mean_pf'])} | {fmt(m['base'])} | {fmt(m['better'])}/{fmt(m['worse'])} | {fmt(m['sign_p'])} | {fmt(m['tie'])}/{fmt(m['no_score'])} | {fmt(m['shown'])}/{fmt(m['scored'])} |")
    lines += ['', '## Mining quality', '',f"Pooled valid-precision: {fmt(quality['pooled']['valid_precision'])}; valid-recall: {fmt(quality['pooled']['valid_recall'])}.",
              f"Accept all: {quality['accepts_everything']}; reject all: {quality['rejects_everything']}.",
              f"DEV plus rejection: {quality['dev_plus']}",'',
              '| Task | Candidates | Confirmed | Surviving | Draws | Precision | Recall |','|---|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        m=r['mining'];lines.append(f"| {r['task']} | {m['candidates']} | {m['confirmed']} | {m['surviving']} | {r['draws']} | {fmt(r['valid_precision'])} | {fmt(r['valid_recall'])} |")
    lines += ['', '## Dropped condition examples', '']
    for row in rows:
        for drop in row['mining']['dropped_confirmation'][:2]:
            lines.append(f"- Task {row['task']}, {drop['id']}: {drop['condition']} — {drop['reason']}; evidence: {drop['evidence']!r}.")
        for drop in row['mining']['dropped_verifier'][:2]:
            first=drop['failures'][0]
            lines.append(f"- Task {row['task']}, {drop['id']}: verifier rejected {first['source']} input {first['input_repr']}; error={first['error']}.")
    lines += ['', '## Per-kind DEV diagnostics', '',
              '| Cohort | Version | Pool | Kind | Reached | Scored/reached | Mean PF | Matched base | Strong facts | Strong tasks |',
              '|---|---|---|---|---:|---:|---:|---:|---:|---:|']
    for version,result in results.items():
        for cohort,body in result['cohorts'].items():
            for pool_name in ('by_kind','shown_by_kind'):
                for kind,m in body[pool_name].items():
                    lines.append(f"| {cohort} | {version} | {pool_name} | {kind} | {m['reached']} | {fmt(m['valid_reach'])} | {fmt(m['mean_pf'])} | {fmt(m['base'])} | {m['strong_facts']} | {m['strong']}/{m['n']} |")
    (out_dir/'REPORT.md').write_text('\n'.join(lines)+'\n')
    print(f'offline report ready: {out_dir}/REPORT.md')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--precond-dir',type=Path,default=preconditions.ROOT)
    p.add_argument('--facts-dir',type=Path,default=HERE/'out/facts_v3m')
    p.add_argument('--out-dir',type=Path,default=HERE/'out/offline_v3m')
    p.add_argument('--contract-data',type=Path,default=gen_inputs.CONTRACTS)
    p.add_argument('--task-ids',type=int,nargs='+')
    p.add_argument('--workers',type=int,default=12)
    args=p.parse_args()
    ids=args.task_ids or [int(n) for n in (HERE/'tasks.txt').read_text().split() if int(n) not in run_gen.DESIGN]
    evaluate(ids,args.precond_dir,args.facts_dir,args.out_dir,args.contract_data,args.workers)


if __name__=='__main__':
    if len(sys.argv)==3 and not sys.argv[1].startswith('--'):
        worker(*sys.argv[1:])
    else:
        main()
