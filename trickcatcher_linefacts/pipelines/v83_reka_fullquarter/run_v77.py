"""Fixed task-major protocol; each model and dataset has its own capped ledger."""
import argparse
from datetime import datetime,timezone
import fcntl
import json
from pathlib import Path
import shutil
from .paths import HERE,CONFIG,select_model
from . import datasets,provenance,v4_runtime,combined_generation,scoring
from .llm_client import atomic_json

ROOT=HERE/'out/combined'


def archive_denials(root):
    transport=root/'transport'
    archive=root.parent/'resume_archives'/root.name/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    for p in transport.glob('calls/**/attempts.json'):
        rows=json.loads(p.read_text())
        if rows and rows[-1]['state']=='workspace_403':
            target=archive/p.relative_to(transport);target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(p,target)
            atomic_json(p,[r for r in rows if r['state']!='workspace_403'])


def prepare(root,python,names=None):
    names=tuple(names or CONFIG['combined']['tasks'])
    v4_runtime.immutable(root/'protocol.json',dict(sources=provenance.sources(),model=CONFIG['model_choice'],
        model_package=CONFIG['openrouter'],K=3,datasets={n:CONFIG['combined']['tasks'][n] for n in names},
        scope='public generation; task-major serial; score only after freeze'))
    prepared={}
    for name in names:
        path=root/name/'prepared.json'
        if path.exists():prepared[name]=json.loads(path.read_text());continue
        from .prepare_cpu import load
        rows=load(name)
        if rows is None:
            rows=[datasets.prepare_one(name,t,root/name/'prepare'/str(t['task']),python) for t in datasets.cohort(name)]
        v4_runtime.immutable(path,rows);prepared[name]=rows
    return prepared


def freeze(root):
    files={str(p.relative_to(root)):provenance.sha(p) for name in CONFIG['combined']['tasks']
           for part in ('generation','paired_subset') for p in (root/name/part).rglob('*')
           if p.is_file() and p.suffix in ('.json','.jsonl','.py')}
    v4_runtime.immutable(root/'generation_frozen.json',files)


def finalize_partial(root,name):
    """Offline terminal selection: whole tasks, all six arms, all K; never pick by score."""
    run=root/name/'generation';bundles=json.loads((run/'tasks.json').read_text())
    selected=[];rows=[];arms=CONFIG['combined']['arms']
    for task in bundles['tasks']:
        paths=[run/'artifacts'/str(task['task'])/str(sample)/arm/'result.json' for sample in range(3) for arm in arms]
        if not all(p.exists() for p in paths):break
        selected.append(task);rows.extend(json.loads(p.read_text()) for p in paths)
    out=root/name/'paired_subset'
    v4_runtime.immutable(out/'tasks.json',dict(facts_version='v4',tasks=selected))
    if (out/'gen.jsonl').exists():raise ValueError('partial_already_finalized')
    (out/'gen.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    v4_runtime.immutable(root/'partial_status.json',dict(status='partial; descriptive only, no efficacy verdict',
        dataset=name,complete_tasks=[t['task'] for t in selected],expected=CONFIG['combined']['tasks'][name],excluded_unfinished_task=True))
    freeze(root)
    if not selected:return None
    return scoring.humaneval(out,root) if name=='humaneval' else scoring.vibepass(out,root)


def launch(root=None,model='gpt-oss-120b',dataset='humaneval'):
    select_model(model)
    from .prepared import verify
    verify()
    from .cost import estimate
    from .context_preflight import preflight
    from .openrouter_client import OpenRouterClient
    from .transport import Client
    root=Path(root or ROOT/model/dataset);root.mkdir(parents=True,exist_ok=True)
    with (root/'.run.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (root/'partial_status.json').exists():raise ValueError('terminal_partial_cannot_resume_or_enlarge')
        cap=estimate()['dataset_caps_usd'][dataset]
        python=v4_runtime.interpreter()
        for rel in json.loads((HERE/'INPUTS.json').read_text())['files']:
            provenance.verify_file(datasets.REPO/rel)
        prepared=prepare(root,python,[dataset])
        atomic_json(root/'context_preflight.json',preflight(prepared))
        archive_denials(root)
        transport=OpenRouterClient(root/'transport',budget_limit=cap);client=Client(transport)
        try:
            if not (root/'generation_frozen.json').exists():
                combined_generation.run(prepared[dataset],root/dataset/'generation',python,client=client,k=3,workers=1)
                freeze(root)
            scoring.verify_freeze(root)
            run=root/dataset/'generation'
            if not (run/'score.json').exists():
                if dataset=='humaneval':scoring.humaneval(run,root,client=client)
                else:scoring.vibepass(run,root)
        finally:transport.close()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--launch',action='store_true')
    parser.add_argument('--finalize-partial',action='store_true')
    parser.add_argument('--model',choices=tuple(CONFIG['models']),default='gpt-oss-120b')
    parser.add_argument('--dataset',choices=tuple(CONFIG['combined']['tasks']),required=True)
    args=parser.parse_args();select_model(args.model)
    if args.finalize_partial:
        if args.launch:parser.error('mutually exclusive actions')
        finalize_partial(ROOT/args.model/args.dataset,args.dataset)
    elif args.launch:launch(model=args.model,dataset=args.dataset)
    else:parser.error('preparation only: --launch requires explicit user go-ahead')

if __name__=='__main__':main()
