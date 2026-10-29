"""VR9 saved-pool applicability/retention diagnostic; canonical data is scoring-only."""
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
MODES=('strict','retain','applicable','generic')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify():
    freeze=json.loads((HERE/'FREEZE.json').read_text())
    for name,digest in freeze['files'].items():
        if sha(REPO/name)!=digest:raise ValueError('vr9_frozen_file_changed: '+name)
    parent=json.loads((HERE/'PARENT.json').read_text())
    for name,digest in parent['files'].items():
        if sha(REPO/parent['source']/name)!=digest:raise ValueError('parent_source_changed')


def prepare(parent_root):
    if (HERE/'FREEZE.json').exists():raise ValueError('preserve_registered_inputs')
    parent=REPO/'trickcatcher_linefacts/pipelines/vr8_semanticgate'
    if not (parent_root/'COMPLETE.json').exists():raise ValueError('parent_not_complete')
    frozen=json.loads((parent_root/'GENERATION_FREEZE.json').read_text())['files']
    source=json.loads((parent/'FREEZE.json').read_text())['files']
    for name,digest in source.items():
        if sha(REPO/name)!=digest:raise ValueError('parent_source_changed')
    for name,digest in frozen.items():
        if sha(parent_root/name)!=digest:raise ValueError('parent_generation_changed')
    records=json.loads((parent/'assets/prepared.json').read_text())
    receipts={}
    for folder in (parent_root/'transport/calls').iterdir():
        receipt=json.loads((folder/'response.json').read_text())
        request=json.loads((folder/'request.json').read_text())
        assert receipt['status']=='received'
        body=request['body'];body['max_tokens']=receipt['allocation']['requested_max_tokens']
        from .replay import key
        assert key(body)==receipt['allocation']['requested_key']
        receipts[key(body)]=receipt
    for record in records:
        n=record['task']['task'];record['pools']={}
        for mode in ('semantic','generic'):
            root=parent_root/'generation'/mode/str(n)
            rows=[json.loads(l) for l in (root/'gen.jsonl').read_text().splitlines()]
            row=next(x for x in rows if x['arm']=='concept-hybrid')
            assert len(row['generator_attempts'])==2
            pools=[]
            for request,attempt in enumerate(row['generator_attempts']):
                assert attempt['request']==request and attempt['retry']==0 and attempt['generated'] is not None
                code=(root/'artifacts'/str(n)/'0/concept-hybrid'/f'request_{request}_0/strategy.py').read_text()
                pools.append(dict(strategy_src=code,generated=attempt['generated'],response_key=row['calls'][request+1]['key']))
            record['pools'][mode]=pools
    assets=HERE/'assets';assets.mkdir(exist_ok=True)
    atomic_json(assets/'prepared.json',records)
    atomic_json(assets/'REPLAY.json',receipts)
    for name in ('refs.json','selection.json','grading_references.json'):
        shutil.copyfile(parent/'assets'/name,assets/name)
    atomic_json(assets/'INHERITED.json',dict(parent_run=str(parent_root.relative_to(REPO)),
        parent_generation_freeze=sha(parent_root/'GENERATION_FREEZE.json'),
        reused_round1_calls=6,reused_reference_calls=60,replay_receipts=len(receipts),new_calls_at_prepare=0))
    freeze()
    print(json.dumps(dict(selected_tasks=[x['task']['task'] for x in records],new_completion_cap=12)))


def freeze():
    files=[p for p in HERE.rglob('*') if p.is_file() and not any(x in ('out','__pycache__') for x in p.relative_to(HERE).parts)
           and p.name not in ('FREEZE.json','runner.log','README.md','CHANGELOG.md','CPU_CHECKS.json')]
    files += [REPO/'trickcatcher_linefacts/pipelines'/folder/'transport.py'
              for folder in ('v85_retrievalhybrid','v85_contextfit','v85_transport_longwait')]
    # The transport imports original paths/config and no other mutable dependency.
    files += [REPO/'trickcatcher_linefacts/pipelines/v85_retrievalhybrid'/name for name in ('paths.py','config.json','llm_client.py')]
    atomic_json(HERE/'FREEZE.json',dict(files={str(p.relative_to(REPO)):sha(p) for p in sorted(set(files))},max_new_completions=12))
    verify()


def make_task(record,mode):
    task=deepcopy(record['task']);i=record['target_index'];binding=record['binding']
    from .applicability import assess
    assessment=assess(task['put'],task['entry'],binding)
    semantic=mode in ('semantic','strict','retain','applicable')
    task.update(vr8_mode='semantic' if semantic else mode,vr8_target_indices=[i],vr8_measurements=[binding],
                vr8_round1_response=record['round1'],vr9_retain=mode in ('retain','applicable'),
                vr9_use_applicability=mode=='applicable',vr9_applicability=assessment)
    if 'pools' in record:
        source='generic' if mode=='generic' or mode=='applicable' and assessment['status']=='refuted_for_supported_values' else 'semantic'
        task['vr9_saved_pools']=record['pools'][source]
    if semantic:
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
    assert len(rows)==len({x['key'] for x in rows})<=12
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
        base.MAX_ATTEMPTS=12
        client=Client(ROOT/'transport')
        try:
            atomic_json(ROOT/'STATUS.json',dict(stage='preflight'))
            client.preflight()
            records=json.loads((HERE/'assets/prepared.json').read_text())
            receipts=json.loads((HERE/'assets/REPLAY.json').read_text())
            from .replay import Client as ReplayClient
            def one(pair):
                index,record=pair
                modes=MODES[index%len(MODES):]+MODES[:index%len(MODES)]
                for mode in modes:
                    task=make_task(record,mode)
                    run_v4.run([task],ROOT/'generation'/mode/str(task['task']),v4_runtime.interpreter(),
                               client=ReplayClient(client,receipts,mode in ('retain','applicable')),k=1,workers=1,arms=('concept','concept-hybrid'))
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
            raise SystemExit('vr9_blocked: '+type(exc).__name__) from None


def main():
    if any(k.startswith('LINEFACTS_') for k in os.environ):
        raise SystemExit('vr9_rejects_external_LINEFACTS_overrides')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('prepare','check','run'))
    parser.add_argument('--parent-root',type=Path)
    args=parser.parse_args()
    CONFIG['V4_PYTHON']=str(Path(sys.executable).absolute())
    os.environ['V4_PYTHON']=CONFIG['V4_PYTHON']
    if args.command=='prepare':
        if args.parent_root is None:parser.error('--parent-root required')
        prepare(args.parent_root.absolute())
    elif args.command=='check':verify();ledger();v4_runtime.require_versions();print('VR9 integrity/ledger/tool versions pass; no model calls')
    else:run()


if __name__=='__main__':main()
