"""Final protocol amendment 1: 10 variants + 4 generators shared by K=3 resamples.

Exactly 14 logical requests/task (<=3*8), and <=20 assertions/sample. No reduced
pool mode. Calls/tokens are attributed once across rows, round-robin by request
index (5/5/4 calls); this is accounting, not independent sample generation.
No canonical/contract source enters generation or vote. Offline replay is default.
"""
import argparse
import ast
import json
import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from ...pipelines.v11_fair_vp import gen_inputs, v4_runtime
from ...pipelines.v11_fair_vp.llm_client import Client
from ..symprompt import tc
from . import tc_full as original

HERE=Path(__file__).resolve().parent
VARIANTS, GENERATORS, K, ASSERTION_CAP = 10, 4, 3, 20
TASK_CALLS, TASK_BUDGET = VARIANTS + GENERATORS, K * 8


class ScriptedClient:
    model=tc.MODEL
    def __init__(self,task,template):
        self.task=task; self.template=template
        # Only public base arguments; choose a clearly different input to exercise export.
        assertion=sorted(tc.base_assertions(task))[0]
        tree=ast.parse(assertion)
        call=next(n for n in ast.walk(tree) if isinstance(n,ast.Call) and
                  isinstance(n.func,ast.Name) and n.func.id==task['entry'])
        self.args=[ast.literal_eval(a) for a in call.args]
        if isinstance(self.args[0],list):self.args[0]=self.args[0]+[987654321]
        elif type(self.args[0]) is int:self.args[0]=987654321
        else:self.args[0]=str(self.args[0])+'scripted'
    def chat(self,messages,seed,**params):
        if messages[0]['content']==self.template['genprog_tc_sys']:
            entry=self.task['entry']
            code=self.task['put']+f'\n_tc_original = {entry}\ndef {entry}(*args, **kwargs):\n' + \
                 f'    if args == {tuple(self.args)!r}: return "scripted-variant"\n' + \
                 '    return _tc_original(*args, **kwargs)\n'
        else:
            code=f'def sample_one():\n    return {tuple(self.args)!r}\n'
        text='```python\n'+code+'```'
        return dict(text=text,key=tc.digest(dict(messages=messages,seed=seed,**params)),
                    params=dict(model=self.model,seed=seed,**params),n_in=0,n_out=0,
                    seconds=0,cache_hit=False,transport_attempts=0)


def isolated(mode,job,directory,python,timeout):
    directory.mkdir(parents=True,exist_ok=True)
    jp=directory/'job.json';op=directory/'result.json'
    tc.immutable(jp,dict(job,mode=mode))
    if op.exists():return json.loads(op.read_text())
    return gen_inputs.sandbox(python,HERE/'final_worker.py',jp,op,timeout)


def run(args):
    if args.k != K or args.workers < 1:
        raise ValueError('Final protocol amendment 1 requires K=3 and positive workers')
    meta,tasks=tc.load_tasks(args.tasks)
    if any(t.get('split')!='heldout' for t in tasks):raise ValueError('final adapter requires heldout tasks')
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    template=original.templates();python=v4_runtime.interpreter(args.python)
    settings=dict(method='tc-full',adapter='tc_full_v2-heldout-final',model=tc.MODEL,
                  k=K,variant_calls=VARIANTS,generator_calls=GENERATORS,
                  budget_scope='task',llm_budget_per_task=TASK_BUDGET,
                  generation_calls_per_task=TASK_CALLS,shared_generation=True,
                  amendment='Final protocol amendment 1',
                  cost_accounting='shared requests partitioned round-robin across K rows, counted once',
                  max_tests=ASSERTION_CAP,draws_per_generator=100,parameters=original.PARAMS,
                  template_sha256=original.SHA,tasks_sha256=tc.digest(tasks),sources=tc.source_hashes(HERE),
                  python=str(python),shared_comparison='v11_fair_vp/scorer.py',
                  scorer_sha256=tc.sha((HERE.parents[1]/'pipelines/v11_fair_vp/scorer.py').read_bytes()))
    tc.immutable(out/'manifest.json',settings);tc.immutable(out/'tasks.json',dict(meta,tasks=tasks))
    run_id=tc.digest(settings)
    online_client=None if args.fake else Client(out/'cache',offline=not args.online,workers=args.workers)
    def task_job(task):
        task_dir=out/'artifacts'/str(task['task']);task_dir.mkdir(parents=True,exist_ok=True)
        result_paths=[task_dir/str(s)/'result.json' for s in range(K)]
        if all(p.exists() for p in result_paths):
            return [json.loads(p.read_text()) for p in result_paths]
        visible=tc.visible(task)
        client=ScriptedClient(visible,template) if args.fake else online_client
        shared_dir=task_dir/'shared';shared_path=shared_dir/'generation.json'
        if shared_path.exists():
            shared=json.loads(shared_path.read_text())
        else:
            session=tc.Session(client,shared_dir/'requests',TASK_CALLS)
            responses=[]
            for stage,count in [('variant',VARIANTS),('generator',GENERATORS)]:
                for i in range(count):
                    seed=original.seed(task['task'],stage,i)
                    text=session.query(original.messages(visible,stage,template),seed,f'{stage}{i}',**original.PARAMS)
                    responses.append(dict(stage=stage,index=i,src=original.source(text)))
            shared=dict(responses=responses,calls=session.calls)
            tc.atomic_json(shared_path,shared)
        responses=shared['responses']
        if (len(shared['calls']) != TASK_CALLS or
                {r['stage']:sum(x['stage']==r['stage'] for x in responses) for r in responses}
                != {'variant':VARIANTS,'generator':GENERATORS}):
            raise ValueError('Shared generation must contain exactly 10 variants and 4 generators')
        atol=float(task.get('atol',0.0))
        filtered=isolated('filter',dict(entry=task['entry'],base=task['base'],atol=atol,
                      variants=[r for r in responses if r['stage']=='variant'],**original.TIMEOUTS),
                      shared_dir/'filter',python,260)
        pool=[];diagnostics=[]
        for response in (r for r in responses if r['stage']=='generator'):
            i=response['index']
            generator_dir=shared_dir/'generators'/str(i)
            generated_path=generator_dir/'generated.json'
            if generated_path.exists():
                generated=json.loads(generated_path.read_text())
            else:
                try:
                    code=gen_inputs.extract_generator(response['src'])
                    generated=original.generate_candidates(code,visible,python,generator_dir,
                             original.seed(task['task'],'draw',i),n=100)
                except (SyntaxError,ValueError) as exc:
                    generated=dict(candidates=[],attempted=0,returned=0,errors=[type(exc).__name__])
                tc.atomic_json(generated_path,generated)
            diagnostics.append({k:v for k,v in generated.items() if k!='candidates'})
            for c in generated['candidates']:
                pool.extend([dict(input_repr=c['input_repr'],generator=i)]*c.get('occurrences',1))
        tc.immutable(shared_dir/'pool.json',pool)
        generation_id=tc.digest(shared['responses'])
        rows=[]
        for s,rp in enumerate(result_paths):
            if rp.exists():
                rows.append(json.loads(rp.read_text()));continue
            directory=rp.parent;directory.mkdir(parents=True,exist_ok=True)
            indices=random.Random(original.seed(task['task'],'resample',s)).sample(range(len(pool)),min(100,len(pool)))
            evidence=isolated('vote',dict(entry=task['entry'],put=task['put'],atol=atol,
                           variants=filtered['survivors'],pool=[pool[i] for i in indices],**original.TIMEOUTS),
                           directory/'vote',python,max(120,len(indices)*(len(filtered['survivors'])+1)+60))
            ordered=list(dict.fromkeys(r['assertion'] for r in evidence['records'] if 'assertion' in r))
            assertions=ordered[:ASSERTION_CAP]
            # Partition a shared cost ledger, not generation. Summing K rows
            # counts each request/token exactly once; mean calls/sample = 14/3.
            attributed_calls=shared['calls'][s::K]
            result=tc.row(task,'tc-full',s,run_id,client.model,assertions,attributed_calls,
                          offline=args.fake,scripted=args.fake,shared_generation=True,
                          generation_id=generation_id,llm_calls_per_task=TASK_CALLS,
                          budget_scope='task',llm_budget_per_task=TASK_BUDGET,
                          resample_seed=original.seed(task['task'],'resample',s),
                          resample_positions=indices,pool_sha256=tc.digest(pool),
                          n_assertions_uncapped=len(ordered),
                          n_assertions_dropped=max(0,len(ordered)-ASSERTION_CAP),n_pool=len(pool),n_inputs=len(indices),
                          n_survivors=len(filtered['survivors']),base_results=filtered['base_results'],
                          generators=diagnostics,put_crashes=sum(r['put_status']!='ok' for r in evidence['records']),
                          put_timeouts=sum(r['put_status'] in ('CallTimeout','Timeout','timeout') for r in evidence['records']),
                          variant_crashes=sum(v['status']!='ok' for r in evidence['records'] for v in r['variant_outcomes']))
            tc.atomic_json(rp,result);rows.append(result)
        return rows
    with ThreadPoolExecutor(args.workers) as pool:
        rows=[r for group in pool.map(task_job,tasks) for r in group]
    tc.write_rows(out,rows)
    print(f'tc-full: {len(rows)} rows, {sum(r["llm_calls"] for r in rows)} logical calls, {sum(r["n_assertions"] for r in rows)} assertions')
    return rows


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--tasks',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--k',type=int,default=3);ap.add_argument('--workers',type=int,default=4)
    ap.add_argument('--python',type=Path)
    mode=ap.add_mutually_exclusive_group();mode.add_argument('--online',action='store_true');mode.add_argument('--fake',action='store_true')
    a=ap.parse_args(argv)
    if a.k!=K or a.workers<1:
        ap.error('Final protocol amendment 1: K=3, positive workers; fixed shared 10+4 pool')
    return run(a)

if __name__=='__main__':main()
