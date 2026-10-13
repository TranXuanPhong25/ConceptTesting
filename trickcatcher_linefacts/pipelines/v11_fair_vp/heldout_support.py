"""Visible bundles and ref-only scoring for held-out baselines; offline by default.

No model response is fabricated. Ref generation needs explicit --online, or a
complete local cache. Every empty-assertion task remains in the scored cohort.
"""
import argparse
import json
import shutil
from pathlib import Path
from . import paths


def visible_bundle(layout):
    from .run import task_sources
    from . import v4_runtime
    tasks,_,selection=task_sources(layout)
    plus={int(r['task_id'].split('/')[1]):r for r in map(json.loads,layout.data['oracle_hep'].read_text().splitlines())}
    questions={}
    if 'root' in layout.data:
        manifest=layout.data['root']/'manifest.json'
        if manifest.exists():
            questions={r['task']:r['question_id'] for r in json.loads(manifest.read_text()).get('puts',[]) if 'question_id' in r}
    for t in tasks:
        # Empty metadata supports evaluation without showing tool facts to baselines.
        t.update(concept_meta=[],atol=float(plus[t['task']].get('atol',0.0)))
        if t['task'] in questions:t['question_id']=questions[t['task']]
    result=dict(tasks=tasks,pilot=[],design_excluded=[],dataset=layout.data['name'])
    target=layout.root/'baseline_tasks.json';v4_runtime.immutable(target,result)
    print(target)
    return result


def collect(run,out):
    from . import oracle_b01 as ob
    from .llm_client import atomic_json
    ob.collect(run,out)
    tasks,_=ob.load_run(run)
    calls=json.loads((out/'calls.json').read_text())
    # The underlying collector skips empty assertions. All N PUTs still need refs.
    for n in tasks:calls.setdefault(str(n),[])
    atomic_json(out/'calls.json',calls)


def score(run,out,ref_from,python,workers):
    from . import evaluate,oracle_b01 as ob
    from .llm_client import atomic_json
    if not (run/'eval.jsonl').exists():
        evaluate.evaluate(run/'tasks.json',run/'gen.jsonl',run/'eval.jsonl',python)
    collect(run,out)
    if ref_from.resolve()!=out.resolve():
        source_tasks={t['task']:t for t in json.loads((ref_from.parent/'generation/tasks.json').read_text())['tasks']}
        for t in json.loads((run/'tasks.json').read_text())['tasks']:
            source=source_tasks[t['task']]
            if any(t[k]!=source[k] for k in ('entry','put','base')):
                raise ValueError('reference programs belong to a different task bundle')
        source=ref_from/'ref_responses.json';target=out/'ref_responses.json'
        if target.exists() and target.read_bytes()!=source.read_bytes():raise ValueError('reference response collision')
        if not target.exists():shutil.copyfile(source,target)
    refs=json.loads((out/'ref_responses.json').read_text())
    expected={t['task'] for t in json.loads((run/'tasks.json').read_text())['tasks']}
    for n in expected:
        if {r['sample'] for r in refs if int(r['task'])==n}!=set(range(ob.NREF)):
            raise ValueError(f'missing spec-only reference programs for task {n}')
    # Ref-only runs must never acquire postconditions/judge artifacts on resume.
    if any((out/f'{stage}_responses.json').exists() for stage in ('b1','post','judge')):
        raise ValueError('ref-only output contains another oracle stage; use a fresh destination')
    ob.score(run,out,workers=workers,use_llm=False)
    if any(not (out/'exec'/f'{n}.json').exists() for n in expected):
        # There is one job plus one result per task, including zero-assertion tasks.
        raise RuntimeError('incomplete oracle execution cohort')
    metrics=json.loads((out/'fair_metrics.json').read_text())
    atomic_json(out/'ref_metrics.json',{arm:dict(D_I=v['D_I'],D_I_samples=v['D_I_samples'],**v['oracles']['ref'])
                                      for arm,v in metrics.items()})


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('stage',choices=('visible','collect','references','score'))
    ap.add_argument('--dataset',required=True);ap.add_argument('--run',type=Path)
    ap.add_argument('--out',type=Path);ap.add_argument('--ref-from',type=Path)
    ap.add_argument('--online',action='store_true');ap.add_argument('--workers',type=int,default=4)
    ap.add_argument('--python',type=Path)
    a=ap.parse_args();paths.set_dataset(a.dataset)
    from .run import Layout
    from . import oracle_b01 as ob,v4_runtime
    from .llm_client import Client
    layout=Layout(a.dataset);layout.root.mkdir(parents=True,exist_ok=True)
    run=paths.safe_output(a.run) if a.run else layout.generation
    out=paths.safe_output(a.out) if a.out else layout.oracle
    out.mkdir(parents=True,exist_ok=True)
    if a.stage=='visible':visible_bundle(layout)
    elif a.stage=='collect':collect(run,out)
    elif a.stage=='references':
        collect(run,out)
        ob.Client=lambda directory,**kw:Client(directory,offline=not a.online,model=paths.CONFIG['model'],**kw)
        ob.llm(run,out,workers=a.workers,stages=('ref',))
    else:score(run,out,a.ref_from or layout.oracle,v4_runtime.interpreter(a.python),a.workers)

if __name__=='__main__':main()
