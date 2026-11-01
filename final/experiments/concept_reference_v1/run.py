"""Persistent cohort + replaceable concept experiments. Default: all 164 tasks."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.metadata
import json
import os
import platform
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from final.pipeline import digest, save
from final.run import load_tasks
from .benchmark import generate_inputs, score_task, report, BUDGET
from .cohort import build_cohort,load_cohort
from .model import QwenModel
from .prompts import ARMS
from .keepalive import KeepAlive

HERE=Path(__file__).resolve().parent


def parallel(items,workers,fn,on_done):
    pool=ThreadPoolExecutor(max_workers=workers)
    pending,iterator={},iter(items)

    def submit():
        item=next(iterator,None)
        if item is not None:
            pending[pool.submit(fn,item)]=item

    for _ in range(workers):
        submit()
    try:
        finished=0
        while pending:
            future=next(as_completed(pending))
            item=pending.pop(future)
            result=future.result()
            finished+=1
            on_done(item,result,finished)
            submit()
    finally:
        for future in pending:
            future.cancel()
        pool.shutdown(wait=True,cancel_futures=True)


def source_hashes():
    files=list(HERE.glob('*.py'))+[HERE.parents[1]/name for name in
        ('core_model.py','contracts.py','pipeline.py','prompts.py','run.py')]
    return {str(path.relative_to(HERE.parents[1])):hashlib.sha256(path.read_bytes()).hexdigest() for path in files}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cohort',type=Path,default=Path('final/out/cohorts/qwen35_27b_humaneval164'))
    parser.add_argument('--out',type=Path,default=Path('final/out/concept_reference_v1'))
    parser.add_argument('--workers',type=int,default=2)
    parser.add_argument('--phase',choices=('all','cohort','generate','score'),default='all')
    parser.add_argument('--task-ids',type=int,nargs='+',help='Engineering subsets only; default all164')
    args=parser.parse_args(argv)
    if args.workers<1 or args.workers>4:
        parser.error('workers must be 1..4')
    tasks=load_tasks()
    if args.task_ids is not None:
        if len(set(args.task_ids))!=len(args.task_ids) or any(i not in range(164) for i in args.task_ids):
            parser.error('task-ids must be unique 0..163')
        tasks=[t for t in tasks if int(t['task_id'].split('/')[1]) in args.task_ids]
    metadata=json.loads((HERE/'data'/'contracts.json').read_text())
    out=args.out.resolve()
    out.mkdir(parents=True,exist_ok=True)
    if args.phase=='score':
        if not (out/'manifest.json').exists() or not (args.cohort/'cohort.json').exists():
            parser.error('Offline score requires an existing manifest and frozen cohort')
        existing=json.loads((out/'manifest.json').read_text())
        model=None
        model_name,context=existing['model'],existing['context']
    else:
        model=QwenModel()
        model_name,context=model.model_id,model.context
    # Offline score never contacts the endpoint; active generation keeps a recorded
    # 20-minute notebook observer, separately accounted from experiment calls.
    from contextlib import nullcontext
    with (out/'.run.lock').open('w') as lock, (KeepAlive(out) if model is not None else nullcontext()):
        try:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            parser.error('Another controller owns this output directory')
        manifest=dict(protocol='concept-reference-v1',model=model_name,context=context,
            tasks=[t['task_id'] for t in tasks],arms=list(ARMS)+['witness_only'],inputs_per_arm=BUDGET,
            input_temperature=.7,input_max_tokens=2048,python=platform.python_version(),
            python_executable=str(Path(sys.executable).resolve()),sources=source_hashes(),
            contracts_sha256=hashlib.sha256((HERE/'data'/'contracts.json').read_bytes()).hexdigest(),
            packages={p:importlib.metadata.version(p) for p in ('python-graphs','networkx','coverage','hypothesis','numpy','scipy','evalplus')})
        mp=out/'manifest.json'
        if mp.exists() and json.loads(mp.read_text())!=manifest:
            parser.error('Experiment source/config changed; use a new experiment --out, reuse the same --cohort')
        save(mp,manifest)
        save(out/'status.json',dict(state='building_cohort',tasks=len(tasks),pid=os.getpid()))
        try:
            cohort=(load_cohort(args.cohort.resolve()/'cohort.json') if args.phase=='score'
                    else build_cohort(model,tasks,args.cohort.resolve(),args.workers))
            if args.phase=='cohort':
                save(out/'status.json',dict(state='cohort_frozen',cohort_sha256=cohort['cohort_sha256'],pid=os.getpid()))
                return 0
            cohort_tasks={t['task_id']:t for t in cohort['tasks']}
            if args.phase in ('all','generate'):
                def generate(task):
                    return generate_inputs(task,cohort_tasks[task['task_id']],metadata[task['task_id']],model,out)

                def generated(task,result,finished):
                    save(out/'status.json',dict(state='generating_inputs',finished=finished,tasks=len(tasks),pid=os.getpid()))
                    print(f"inputs {finished}/{len(tasks)} {task['task_id']}",flush=True)

                parallel(tasks,args.workers,generate,generated)
                inputs={t['task_id']:digest(json.loads((out/'tasks'/t['task_id'].split('/')[1]/'inputs.json').read_text())) for t in tasks}
                freeze=dict(cohort_sha256=cohort['cohort_sha256'],inputs=inputs,inputs_sha256=digest(inputs))
                fp=out/'generation_frozen.json'
                if fp.exists() and json.loads(fp.read_text())!=freeze:
                    raise ValueError('Input generation freeze mismatch')
                save(fp,freeze)
            if args.phase=='generate':
                save(out/'status.json',dict(state='inputs_frozen',tasks=len(tasks),pid=os.getpid()))
                return 0
            freeze=json.loads((out/'generation_frozen.json').read_text())
            actual={t['task_id']:digest(json.loads((out/'tasks'/t['task_id'].split('/')[1]/'inputs.json').read_text())) for t in tasks}
            if freeze['inputs_sha256']!=digest(actual) or freeze['cohort_sha256']!=cohort['cohort_sha256']:
                raise ValueError('Frozen generation or cohort changed before scoring')

            def score(task):
                return score_task(task,cohort_tasks[task['task_id']],metadata[task['task_id']],out)

            def scored(task,result,finished):
                save(out/'status.json',dict(state='scoring',finished=finished,tasks=len(tasks),pid=os.getpid()))
                print(f"scored {finished}/{len(tasks)} {task['task_id']}",flush=True)

            parallel(tasks,args.workers,score,scored)
            summary=report(out,cohort,len(tasks))
            save(out/'status.json',dict(state='complete',tasks=len(tasks),summary=summary,pid=os.getpid()))
            print(json.dumps({k:v for k,v in summary.items() if k!='comparisons'},indent=2),flush=True)
            return 0
        except BaseException as exc:
            save(out/'status.json',dict(state='interrupted',error_type=type(exc).__name__,pid=os.getpid()))
            print(f'Interrupted: {type(exc).__name__}. Durable responses preserved; no unknown request replay.',file=sys.stderr,flush=True)
            return 2


if __name__=='__main__':
    raise SystemExit(main())
