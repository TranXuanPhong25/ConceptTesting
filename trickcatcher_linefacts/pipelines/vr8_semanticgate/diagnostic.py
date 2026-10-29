"""VR8 saved-round1/shared-ref diagnostic; canonical data is scoring-only."""
import argparse
from copy import deepcopy
import fcntl
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor,as_completed
from .paths import HERE,REPO,CONFIG,DATA_OUT
from .llm_client import atomic_json
from .semantic_gate import bind,FAMILIES
from . import v4_runtime,run_v4

ROOT=DATA_OUT/'diagnostic'
MODES=('old','semantic','generic')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify():
    freeze=json.loads((HERE/'FREEZE.json').read_text())
    for name,digest in freeze['files'].items():
        if sha(REPO/name)!=digest:raise ValueError('vr8_frozen_file_changed: '+name)
    parent=json.loads((HERE/'PARENT.json').read_text())
    for name,digest in parent['files'].items():
        if sha(REPO/parent['source']/name)!=digest:raise ValueError('parent_source_changed')


def prepare(parent_root):
    if (HERE/'FREEZE.json').exists():raise ValueError('preserve_registered_inputs')
    if not (parent_root/'HANDOFF_COMPLETE.json').exists():raise ValueError('parent_not_complete')
    frozen=json.loads((parent_root/'GENERATION_FREEZE.json').read_text())['files']
    candidates=[];source_hashes={}
    for p in (parent_root/'prepared').glob('*.json'):
        assert sha(p)==frozen[str(p.relative_to(parent_root))]
        task=json.loads(p.read_text())['retrieval']
        for i,fact in enumerate(task['concept_meta']):
            if fact.get('card_id') in FAMILIES:
                candidates.append(dict(task=task['task'],index=i,binding=bind(task,fact)))
    selected=[];used=set()
    for family in ('ordering','membership','normalization'):
        pool=sorted((x for x in candidates if x['binding']['family']==family and x['binding']['status']=='supported'),
                    key=lambda x:(hashlib.sha256(str(x['task']).encode()).hexdigest(),x['index']))
        take=[]
        for x in pool:
            if x['task'] not in used:
                take.append(x);used.add(x['task'])
            if len(take)==2:break
        if len(take)!=2:raise ValueError('insufficient_registered_family_support')
        selected.extend(take)
    assets=HERE/'assets';assets.mkdir(exist_ok=True)
    records=[];refs={}
    for item in selected:
        n=item['task'];p=parent_root/'prepared'/f'{n}.json'
        task=json.loads(p.read_text())['retrieval']
        gen=parent_root/'generation/retrieval'/str(n)/'gen.jsonl'
        assert sha(gen)==frozen[str(gen.relative_to(parent_root))]
        first=next(json.loads(l) for l in gen.read_text().splitlines() if json.loads(l)['arm']=='concept')
        assert first['llm_calls']==len(first['calls'])==1
        response=first['calls'][0]
        receipt=parent_root/'transport/calls'/response['key']/'response.json'
        assert response==json.loads(receipt.read_text()) and sha(receipt)==frozen[str(receipt.relative_to(parent_root))]
        records.append(dict(task=task,target_index=item['index'],binding=item['binding'],round1=response))
        refs[str(n)]=[]
        for sample in range(10):
            oracle=parent_root/'oracles'/str(n)/f'{sample}.json'
            assert sha(oracle)==frozen[str(oracle.relative_to(parent_root))]
            refs[str(n)].append(json.loads(oracle.read_text()))
            source_hashes[str(oracle.relative_to(parent_root))]=sha(oracle)
        source_hashes.update({str(q.relative_to(parent_root)):sha(q) for q in (p,gen,receipt)})
    atomic_json(assets/'prepared.json',records)
    atomic_json(assets/'refs.json',refs)
    atomic_json(assets/'selection.json',dict(rule='SHA256 task; ordering,membership,normalization;2unique/family',selected=selected,candidates=candidates))
    atomic_json(assets/'INHERITED.json',dict(parent_run=str(parent_root.relative_to(REPO)),files=source_hashes,
                reused_round1_calls=len(records),reused_reference_calls=10*len(records),new_calls_at_prepare=0))
    # Opaque copy only; decoding is confined to score() after generation freeze.
    shutil.copyfile(REPO/'trickcatcher_linefacts/pipelines/v85_retrievalhybrid/assets/grading_references.json',assets/'grading_references.json')
    freeze()
    print(json.dumps(dict(selected_tasks=[x['task'] for x in selected],candidates=len(candidates),new_completion_cap=54)))


def freeze():
    files=[p for p in HERE.rglob('*') if p.is_file() and not any(x in ('out','__pycache__') for x in p.relative_to(HERE).parts)
           and p.name not in ('FREEZE.json','runner.log','README.md','CHANGELOG.md','CPU_CHECKS.json')]
    files += [REPO/'trickcatcher_linefacts/pipelines'/folder/'transport.py'
              for folder in ('v85_retrievalhybrid','v85_contextfit','v85_transport_longwait')]
    # The transport imports original paths/config and no other mutable dependency.
    files += [REPO/'trickcatcher_linefacts/pipelines/v85_retrievalhybrid'/name for name in ('paths.py','config.json','llm_client.py')]
    atomic_json(HERE/'FREEZE.json',dict(files={str(p.relative_to(REPO)):sha(p) for p in sorted(set(files))},max_new_completions=54))
    verify()


def make_task(record,mode):
    task=deepcopy(record['task']);i=record['target_index'];binding=record['binding']
    task.update(vr8_mode=mode,vr8_target_indices=[i],vr8_measurements=[binding],vr8_round1_response=record['round1'])
    if mode=='semantic':
        old=task['concept_meta'][i]
        fact={k:old[k] for k in ('card_id','card','retrieval_evidence')}
        fact.update(kind='SEMANTIC',line=binding['site'][0],semantic_index=0,
                    text=json.dumps(old['card'],ensure_ascii=False)+'\nTool target OBS: '+binding['predicate']+
                    '. This is a measured property, not a bug verdict; use the public specification for required behavior.')
        task['concept_meta'][i]=fact
        task['concept_facts']=[f['text'] for f in task['concept_meta']]
    return task


def ledger():
    path=ROOT/'transport/attempts.jsonl'
    rows=[json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []
    assert len(rows)==len({x['key'] for x in rows})<=54
    for x in rows:
        p=ROOT/'transport/calls'/x['key']/'response.json'
        if not p.exists() or json.loads(p.read_text()).get('status')!='received':
            raise ValueError('failed_or_unresolved_attempt_no_automatic_retry')
        response=json.loads(p.read_text())
        body=json.loads(p.with_name('request.json').read_text())['body']
        key=hashlib.sha256(json.dumps(body,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        if response.get('key')!=key or key!=x['key']:
            raise ValueError('changed_request_receipt')
    return rows


def run():
    ROOT.mkdir(parents=True,exist_ok=True)
    with (ROOT/'RUN.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        verify();ledger();v4_runtime.require_versions()
        if (ROOT/'COMPLETE.json').exists():return
        (ROOT/'controller.pid').write_text(str(os.getpid())+'\n')
        from ..v85_retrievalhybrid import transport as base
        from ..v85_transport_longwait.transport import Client
        base.MAX_ATTEMPTS=54
        client=Client(ROOT/'transport')
        try:
            atomic_json(ROOT/'STATUS.json',dict(stage='preflight'))
            client.preflight()
            records=json.loads((HERE/'assets/prepared.json').read_text())
            def one(pair):
                index,record=pair
                modes=MODES[index%3:]+MODES[:index%3]
                for mode in modes:
                    task=make_task(record,mode)
                    run_v4.run([task],ROOT/'generation'/mode/str(task['task']),v4_runtime.interpreter(),
                               client=client,k=1,workers=1,arms=('concept','concept-hybrid'))
                return record['task']['task']
            records.sort(key=lambda x:hashlib.sha256(str(x['task']['task']).encode()).hexdigest())
            atomic_json(ROOT/'STATUS.json',dict(stage='generation',completed=0,total=len(records)))
            with ThreadPoolExecutor(max_workers=2) as pool:
                for done,future in enumerate(as_completed([pool.submit(one,pair) for pair in enumerate(records)]),1):
                    future.result();atomic_json(ROOT/'STATUS.json',dict(stage='generation',completed=done,total=len(records)))
            verify();ledger()
            files=[p for part in ('generation','transport') for p in (ROOT/part).rglob('*') if p.is_file() and p.suffix in ('.json','.jsonl','.py')]
            atomic_json(ROOT/'GENERATION_FREEZE.json',dict(files={str(p.relative_to(ROOT)):sha(p) for p in files},target_reference_used=False))
            from .diagnostic_score import score
            score(records)
        except Exception as exc:
            atomic_json(ROOT/'STATUS.json',dict(stage='blocked',error_type=type(exc).__name__))
            raise SystemExit('vr8_blocked: '+type(exc).__name__) from None


def main():
    if any(k.startswith('LINEFACTS_') for k in os.environ):
        raise SystemExit('vr8_rejects_external_LINEFACTS_overrides')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('prepare','check','run'))
    parser.add_argument('--parent-root',type=Path)
    args=parser.parse_args()
    CONFIG['V4_PYTHON']=str(Path(sys.executable).absolute())
    os.environ['V4_PYTHON']=CONFIG['V4_PYTHON']
    if args.command=='prepare':
        if args.parent_root is None:parser.error('--parent-root required')
        prepare(args.parent_root.absolute())
    elif args.command=='check':verify();ledger();v4_runtime.require_versions();print('VR8 integrity/ledger/tool versions pass; no model calls')
    else:run()


if __name__=='__main__':main()
