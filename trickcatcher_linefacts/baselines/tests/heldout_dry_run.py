"""Offline adapter checks: three visible PUTs per held-out set, K=3, no oracle/LLM.

Artifacts are ignored under heldout_dry; only summary.json and its ignore rule
are tracked. Use a fresh --out under baselines/tests for another check.
"""
import argparse
import ast
import json
import os
import socket
import subprocess
import sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from ..common import extract_assertions, atomic_json
from ...pipelines.v11_fair_vp.run import Layout, task_sources

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]


def scripted_tests(t):
    found,_=extract_assertions(t['base'],t['entry'],t['put'])
    out=[]
    for src in found[:4]:
        tree=ast.parse(src)
        call=next((n for n in ast.walk(tree) if isinstance(n,ast.Call) and
                   isinstance(n.func,ast.Name) and n.func.id==t['entry']),None)
        if call is None: continue
        for arg in call.args:
            if isinstance(arg,ast.List) and arg.elts:
                arg.elts=arg.elts[::-1]; break
            if isinstance(arg,ast.Constant) and type(arg.value) is int:
                arg.value+=1; break
        out.append(ast.unparse(tree))
    return '```python\n'+'\n'.join(out)+'\n```'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,default=HERE/'heldout_dry')
    p.add_argument('--include-tc',action='store_true')
    a=p.parse_args(); out=a.out.resolve(); out.relative_to(HERE)
    out.mkdir(parents=True,exist_ok=True)
    summary=dict(offline=True,network_requests=0,k=3,call_cap=8,assertion_cap=20,
                 tc_full_v2=dict(amendment='Final protocol amendment 1',budget_scope='task',
                                 calls_per_task=14,task_call_cap=24,variants=10,generators=4,
                                 shared_generation=True),datasets={})
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
    # Children use fake/scripted modes, never online; remove endpoint credentials too.
    for k in tuple(env):
        if k.startswith(('QWEN_','OPENAI_','ANTHROPIC_','VERTEX_','GOOGLE_')): env.pop(k,None)
    for name,root,ids in [('vibepass','heldout_vibepass_real',[3,103,120]),
                          ('mbpp','heldout_mbpp_real12',[93,99,126])]:
        all_tasks,_,_=task_sources(Layout(str(REPO/'trickcatcher_linefacts/out'/root/'he')))
        tasks=[t for t in all_tasks if t['task'] in ids]
        bundle=out/f'{name}_tasks.json'; atomic_json(bundle,dict(tasks=tasks))
        responses=out/f'{name}_responses.json'
        atomic_json(responses,{str(t['task']):[scripted_tests(t)] for t in tasks})
        ds=dict(ids=ids,entries=[t['entry'] for t in tasks],baselines={})
        names=['symprompt','ach','coverup','mutap']+(['tc_full_v2'] if a.include_tc else [])
        for method in names:
            dest=out/name/method
            if (dest/'gen.jsonl').exists():
                status=0 # inspect existing artifacts from this exact dry-run destination
            else:
                if method=='tc_full_v2':
                    module='trickcatcher_linefacts.baselines.tc_full_v2.final_run'
                    args=['--tasks',str(bundle),'--out',str(dest),'--fake','--k','3','--workers','1']
                else:
                    module=f'trickcatcher_linefacts.baselines.{method}.run'
                    args=['--tasks',str(bundle),'--out',str(dest),'--k','3','--llm-budget','8','--max-tests','20','--workers','1']
                    args+=['--fake'] if method in ('symprompt','ach') else ['--responses',str(responses)]
                    if method=='ach': args+=['--filter','run']
                r=subprocess.run([sys.executable,'-B','-m',module,*args],cwd=REPO,env=env,
                                 text=True,capture_output=True)
                (out/f'{name}_{method}.log').write_text(r.stdout+r.stderr); status=r.returncode
            f=dest/'gen.jsonl'
            rows=[json.loads(l) for l in f.read_text().splitlines()] if f.exists() else []
            errors=[x for r in rows for x in (r.get('error'),) if x]
            stops=Counter(r.get('stop_reason','completed') for r in rows)
            task_calls={t['task']:sum(r['llm_calls'] for r in rows if r['task']==t['task']) for t in tasks}
            task_cap=method=='tc_full_v2'
            shared_verified=(all(task_calls[t['task']]==14 and
                            len({r.get('generation_id') for r in rows if r['task']==t['task']})==1 and
                            len({c['key'] for r in rows if r['task']==t['task'] for c in r['calls']})==14 and
                            all(r.get('shared_generation') is True and r.get('budget_scope')=='task'
                                for r in rows if r['task']==t['task']) for t in tasks)
                            if task_cap else None)
            rec=dict(exit_code=status,rows=len(rows),expected_rows=9,
                     llm_calls=sum(r['llm_calls'] for r in rows),assertions=sum(r['n_assertions'] for r in rows),
                     budget_scope='task' if task_cap else 'sample',calls_per_task=task_calls,
                     shared_generation_verified=shared_verified,
                     capped=all(r['n_assertions']<=20 for r in rows) and
                            (all(n<=24 for n in task_calls.values()) if task_cap else all(r['llm_calls']<=8 for r in rows)),
                     wrapper_calls_only=all(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and
                                       n.func.id==next(t['entry'] for t in tasks if t['task']==r['task'])
                                       for n in ast.walk(ast.parse(src))) for r in rows for src in r['assertions']),
                     samples=sorted([r['task'],r['sample']] for r in rows),
                     stop_reasons=dict(stops),errors=errors,
                     per_sample=[{k:r.get(k) for k in ('task','sample','llm_calls','n_assertions','stop_reason',
                                                      'n_mutants_killed','n_live_selected','mutation_backend','focal')}
                                 for r in rows],output=str(f.relative_to(out)))
            bad={'base_failed','base_screen_failed','mutation_failed','suite_failed'}
            rec['ok']=status==0 and len(rows)==9 and rec['capped'] and not errors and not bad.intersection(stops)
            if task_cap:rec['ok'] &= shared_verified
            ds['baselines'][method]=rec
            print(name,method,{k:rec[k] for k in ('rows','llm_calls','assertions','stop_reasons','ok')},flush=True)
        summary['datasets'][name]=ds
    summary['ok']=all(r['ok'] for ds in summary['datasets'].values() for r in ds['baselines'].values())
    atomic_json(out/'summary.json',summary)
    raise SystemExit(0 if summary['ok'] else 1)

if __name__=='__main__':main()
