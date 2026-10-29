"""VR12 fresh-strategy census of new VR9-compatible tasks; saved R1/ref only."""
import argparse
from copy import deepcopy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from .paths import HERE, REPO, CONFIG, DATA_OUT
from .llm_client import atomic_json
from . import v4_runtime, run_v4

ROOT = DATA_OUT / 'diagnostic'
MODES = ('strict','retain','applicable','generic')
TASKS = 11
MAX_CALLS = TASKS * len(MODES) * 3


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify(require_review=True):
    freeze = json.loads((HERE/'FREEZE.json').read_text())
    for name, digest in freeze['files'].items():
        if sha(REPO/name) != digest:
            raise ValueError('vr12_source_or_input_changed: '+name)
    parent = json.loads((HERE/'PARENT.json').read_text())
    for name,digest in parent['files'].items():
        if sha(REPO/parent['source']/name) != digest:
            raise ValueError('vr9_parent_changed: '+name)
    if require_review:
        review = json.loads((HERE/'REVIEW_APPROVAL.json').read_text())
        if (review.get('status')!='approved' or review.get('must_fixes_remaining')!=[]
                or review.get('freeze_sha256')!=sha(HERE/'FREEZE.json')):
            raise ValueError('independent_review_missing_or_stale')


def freeze():
    if (HERE/'FREEZE.json').exists():
        raise ValueError('Preserve frozen experiment; amendment needs explicit new freeze')
    files = list(HERE.glob('*.py')) + list(HERE.glob('*.json')) + [HERE/'PREREG.md']
    files += list((HERE/'assets').rglob('*')) + list((HERE/'tc_templates').rglob('*'))
    files += [REPO/'trickcatcher_linefacts/pipelines'/f/n for f,n in
              [('v85_retrievalhybrid','transport.py'),('v85_contextfit','transport.py'),
               ('v85_transport_longwait','transport.py'),('v85_retrievalhybrid','paths.py'),
               ('v85_retrievalhybrid','config.json'),('v85_retrievalhybrid','llm_client.py')]]
    excluded={'FREEZE.json','REVIEW_APPROVAL.json','CPU_CHECKS.json'}
    atomic_json(HERE/'FREEZE.json',dict(files={str(p.relative_to(REPO)):sha(p)
        for p in sorted(set(files)) if p.is_file() and p.name not in excluded},
        selected_tasks=TASKS,K=1,max_new_completions=MAX_CALLS))
    verify(False)


def make_task(record,mode):
    task=deepcopy(record['task']);i=record['target_index'];binding=record['binding']
    from .applicability import assess
    assessment=assess(task['put'],task['entry'],binding)
    semantic=mode in ('strict','retain','applicable','semantic')
    task.update(vr8_mode='semantic' if semantic else 'generic',vr8_target_indices=[i],
                vr8_measurements=[binding],vr8_round1_response=record['round1'],
                vr9_retain=mode in ('retain','applicable'),
                vr9_use_applicability=mode=='applicable',vr9_applicability=assessment)
    if semantic:
        old=task['concept_meta'][i]
        fact={k:old[k] for k in ('card_id','card','retrieval_evidence')}
        fact.update(kind='SEMANTIC',line=binding['site'][0],semantic_index=0,
                    text=json.dumps(old['card'],ensure_ascii=False)+'\nTool target OBS: '+binding['predicate']+
                    '. This is a measured property, not a bug verdict; use the public specification for required behavior.')
        task['concept_meta'][i]=fact
        task['concept_facts']=[f['text'] for f in task['concept_meta']]
    if 'vr9_saved_pools' in task:
        raise ValueError('new_tasks_must_not_receive_historical_strategy_pools')
    return task


def ledger():
    p=ROOT/'transport/attempts.jsonl'
    rows=[json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []
    if len(rows)!=len({r['key'] for r in rows}) or len(rows)>MAX_CALLS:
        raise ValueError('completion_ledger_invalid_or_over_cap')
    for row in rows:
        p=ROOT/'transport/calls'/row['key']/'response.json'
        if not p.exists() or json.loads(p.read_text()).get('status')!='received':
            raise ValueError('unresolved_or_failed_attempt_no_automatic_retry')
        body=json.loads(p.with_name('request.json').read_text())['body']
        expected=hashlib.sha256(json.dumps(body,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        if json.loads(p.read_text()).get('key')!=expected or row['key']!=expected:
            raise ValueError('request_receipt_identity_changed')
    return rows


def run():
    ROOT.mkdir(parents=True,exist_ok=True)
    with (ROOT/'RUN.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        verify();ledger();v4_runtime.require_versions()
        if (ROOT/'COMPLETE.json').exists():
            return
        (ROOT/'controller.pid').write_text(str(os.getpid())+'\n')
        from ..v85_retrievalhybrid import transport as base
        from ..v85_transport_longwait.transport import Client
        base.MAX_ATTEMPTS=MAX_CALLS
        client=Client(ROOT/'transport')
        try:
            atomic_json(ROOT/'STATUS.json',dict(stage='preflight',tasks=TASKS,max_completions=MAX_CALLS))
            client.preflight()
            records=json.loads((HERE/'assets/prepared.json').read_text())
            if len(records)!=TASKS or len({x['task']['task'] for x in records})!=TASKS:
                raise ValueError('registered_task_count_mismatch')
            # Shared cache gives exact same physical response for identical requests.
            # Same task/arm seeds and strategy code also give identical input pools.
            def one(pair):
                index,record=pair
                modes=MODES[index%len(MODES):]+MODES[:index%len(MODES)]
                for mode in modes:
                    task=make_task(record,mode)
                    run_v4.run([task],ROOT/'generation'/mode/str(task['task']),v4_runtime.interpreter(),
                        client=client,k=1,workers=1,arms=('concept','concept-hybrid'))
                return record['task']['task']
            records.sort(key=lambda r:hashlib.sha256(str(r['task']['task']).encode()).hexdigest())
            atomic_json(ROOT/'STATUS.json',dict(stage='generation',completed=0,total=TASKS))
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures=[pool.submit(one,pair) for pair in enumerate(records)]
                for done,future in enumerate(as_completed(futures),1):
                    future.result()
                    atomic_json(ROOT/'STATUS.json',dict(stage='generation',completed=done,total=TASKS))
                    print('generation',done,'/',TASKS,flush=True)
            verify();ledger()
            files=[p for part in ('generation','transport') for p in (ROOT/part).rglob('*')
                   if p.is_file() and p.suffix in ('.json','.jsonl','.py')]
            atomic_json(ROOT/'GENERATION_FREEZE.json',dict(files={str(p.relative_to(ROOT)):sha(p) for p in files},target_reference_used=False))
            from .diagnostic_score import score
            score(records)
        except Exception as exc:
            atomic_json(ROOT/'STATUS.json',dict(stage='blocked',error_type=type(exc).__name__))
            raise SystemExit('vr12_blocked: '+type(exc).__name__) from None


def main():
    if any(k.startswith('LINEFACTS_') for k in os.environ):
        raise SystemExit('vr12_rejects_external_LINEFACTS_overrides')
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['freeze','check','run'])
    args=p.parse_args()
    CONFIG['V4_PYTHON']=str(Path(sys.executable).absolute());os.environ['V4_PYTHON']=CONFIG['V4_PYTHON']
    if args.command=='freeze':freeze()
    elif args.command=='check':verify();ledger();v4_runtime.require_versions();print('VR12 frozen source/ledger/runtime PASS')
    else:run()


if __name__=='__main__':main()
