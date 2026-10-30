"""Read saved VR12 artifacts only; no workers, network, or credential reads."""
import json, hashlib, fcntl, os
from pathlib import Path
from trickcatcher_linefacts.pipelines.vr12_expanded import diagnostic as d, oracle_b01 as ob
O=Path(__file__).resolve().parent
load=lambda p:json.loads(p.read_text())
checks={}
d.verify(); checks['source_parent_review']={'pass':True,'source_files':79,'parent_files':64}
pid=int((d.ROOT/'controller.pid').read_text())
checks['controller_pid_exists']=Path('/proc',str(pid)).exists()
with (d.ROOT/'RUN.lock').open('r') as f:
 try: fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB); checks['run_lock_free']=True
 except BlockingIOError: checks['run_lock_free']=False
freeze=load(d.ROOT/'GENERATION_FREEZE.json')
checks['generation_freeze']={'files':len(freeze['files']),'pass':all(d.sha(d.ROOT/p)==s for p,s in freeze['files'].items()),'target_reference_used':freeze['target_reference_used']}
ledger=d.ledger(); receipts=[load(p) for p in (d.ROOT/'transport/calls').glob('*/response.json')]
assert {r['key'] for r in ledger}=={r['key'] for r in receipts}
checks['ledger_identity']={'pass':True,'attempts':len(ledger),'received':len(receipts),'cap':132}
R=load(d.ROOT/'RESULTS.json'); records=load(d.HERE/'assets/prepared.json'); tasks={r['task']['task']:r['task'] for r in records}
saved={int(p.stem):load(p) for p in (d.ROOT/'scored').glob('*.json')}
assert set(saved)==set(tasks) and len(saved)==11
checks['score_recomputed']={}
for oracle in ('ref','o0'):
 arms={}
 for mode in (*d.MODES,*(m+'_round1' for m in d.MODES)):
  bugs=set(); alarms=set(); abstained=0
  for n,pack in saved.items():
   for row in pack['rows']:
    if row['arm']!=mode: continue
    seen=set()
    for assertion in row['asserts']:
     call=ob.call_of(assertion['src'],tasks[n]['entry'])
     if call is None or oracle=='ref' and call in seen: continue
     seen.add(call); rec=pack['execution']['calls'].get(call,{})
     emit,correct,passes=ob.decide(oracle,rec,None,ob.expected_of(assertion['src']),assertion)
     abstained+=not emit
     if emit and not passes: (bugs if rec.get('valid',False) and correct else alarms).add(n)
  arms[mode]=dict(tasks=11,confirmed_tasks=sorted(bugs),false_alarm_tasks=sorted(alarms),abstained_calls=abstained)
 checks.setdefault('score_differences',{})[oracle]={m:{'recomputed':v,'saved':R['results'][oracle]['arms'][m]} for m,v in arms.items() if v!=R['results'][oracle]['arms'][m]}
 checks['score_recomputed'][oracle]=arms
pool=[]; exposure={}
for n,pack in saved.items():
 def artifact(mode): return d.ROOT/'generation'/mode/str(n)/'artifacts'/str(n)/'0/concept-hybrid'
 equal=[]
 for p in artifact('strict').glob('request_*/draw_result.json'):
  q=artifact('retain')/p.relative_to(artifact('strict'))
  equal.append(q.exists() and load(p)==load(q))
 pool.append({'task':n,'draw_receipts':len(equal),'equal':all(equal)})
 for row in pack['rows']:
  mode=row['arm']
  if mode not in d.MODES: continue
  selected={r['call'] for r in row['selected_inputs']}
  exposing=sorted(c for c in selected if pack['execution']['calls'].get(c,{}).get('valid') and pack['execution']['calls'][c].get('d_i'))
  assert exposing==R['mechanism'][mode][str(n)]['selected_bug_exposing_calls']
  exposure.setdefault(mode,{})[str(n)]={'selected':len(row['selected_inputs']),'exposing':len(exposing),'missing_expected':R['mechanism'][mode][str(n)]['missing_expected']}
checks['strict_retain_draw_pool_equality']=pool
checks['selected_exposure']=exposure
losses={}
for mode in d.MODES:
 losses[mode]={}
 for n,pack in saved.items():
  row=next(r for r in pack['rows'] if r['arm']==mode)
  exposing={r['call'] for r in row['selected_inputs'] if pack['execution']['calls'].get(r['call'],{}).get('valid') and pack['execution']['calls'][r['call']].get('d_i')}
  correct=set(); asserted=set()
  for a in row['asserts']:
   c=ob.call_of(a['src'],tasks[n]['entry']); asserted.add(c)
   emit,ok,passes=ob.decide('o0',pack['execution']['calls'].get(c,{}),None,ob.expected_of(a['src']),a)
   if emit and ok and not passes: correct.add(c)
  losses[mode][str(n)]={'selected_exposing':len(exposing),'without_assertion':len(exposing-asserted),'without_correct_expected_failure':len(exposing-correct)}
checks['selected_expected_losses']=losses
keys=('prompt_tokens','completion_tokens','total_tokens')
def usage(rs): return {k:sum((r.get('usage') or {}).get(k) or 0 for r in rs) for k in keys}
def unknown(rs): return sum(any(type((r.get('usage') or {}).get(k)) is not int for k in keys) for r in rs)
assert usage(receipts)==R['new_usage'] and unknown(receipts)==R['new_unknown_usage']==0
refs=load(d.HERE/'assets/refs.json'); inherited=[r['round1'] for r in records]+[r['response'] for group in refs.values() for r in group]
assert usage(inherited)==R['inherited_round1_ref_usage'] and unknown(inherited)==R['inherited_unknown_usage']==0
checks['usage']={'new':usage(receipts),'new_unknown':unknown(receipts),'inherited':usage(inherited),'inherited_unknown':unknown(inherited),'reused_R1':len(records),'reused_reference':sum(map(len,refs.values())),'logical_round2':R['logical_round2_calls_including_replay']}
checks['artifacts']={str(p.relative_to(d.REPO)):d.sha(p) for p in [d.ROOT/'RESULTS.json',d.ROOT/'GENERATION_FREEZE.json',O/'events.jsonl',*sorted((d.ROOT/'scored').glob('*.json'))]}
checks['limitations']=['Saved execution receipts audited; no code execution/scorer worker rerun.','Only 2 OBS-uncovered targets; development census, no held-out claim.','Separate vr13 retriever is not integrated.','Quota screenshot is not evidence of current quota.']
(O/'AUDIT_CHECKS.json').write_text(json.dumps(checks,indent=2)+'\n')
print(json.dumps({'tasks':len(saved),'physical':len(receipts),'pool_equal':all(x['equal'] for x in pool),'freeze':checks['generation_freeze'],'usage':checks['usage']}))
