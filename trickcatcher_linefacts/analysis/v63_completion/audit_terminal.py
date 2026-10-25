import json,hashlib
from pathlib import Path
from collections import Counter
from trickcatcher_linefacts.pipelines.v63_scopeguard.pipeline import readiness_identity,check_freeze
from trickcatcher_linefacts.pipelines.v63_scopeguard.continuation import verify_manifest
R=Path(__file__).resolve().parents[3];root=R/'trickcatcher_linefacts/out/pipelines/v63_scopeguard/pilot6_20261025';g=root/'generation'
req=R/'trickcatcher_linefacts/out/pipelines/v57_pathfault/ngrok_pilot6_20261024/preparation/requests.json'
assert json.loads((root/'reviewed_ready.json').read_text())=={'status':'reviewed_ready','identity':readiness_identity(req,g/'continuation.json')}
check_freeze(g);manifest=verify_manifest(g)
score=json.loads((R/'trickcatcher_linefacts/analysis/v63_completion/out_reviewed/score.json').read_text())
qual=lambda x:all(x.get(k)is True for k in ('normal','stable','site_realized','predicate_realized','event_realized'))and x.get('event_unknown')is False
responses=[(p,json.loads(p.read_text()))for p in g.rglob('response.json')]
requests=[json.loads((p.parent/'request.json').read_text())for p,_ in responses]
assert all(v['request_sha256']==hashlib.sha256(json.dumps(i,sort_keys=True).encode()).hexdigest()for (_,v),i in zip(responses,requests))
assert len(set(v['request_sha256']for _,v in responses))==108
assert all(json.loads((p.parent/'attempt_01_result.json').read_text())['response']==v['response'] for p,v in responses)
errors=[{'slot':str(p.parent.relative_to(g)),'error':v['error']}for p,v in responses if v['error']]
usage={k:sum(v['response'][k]for _,v in responses)for k in ('input_tokens','output_tokens')}
final={};percase=[];probes=Counter();construction_executions=0
for arm in score['summary']:
 stat=Counter()
 for p in g.glob('*/result.json'):
  d=json.loads(p.read_text());a=d['arms'][arm]['final_realization'];stat['native_executions']+=a['native_executions']
  for row in a['rows']:
   rr=row['realization'];n=sum(qual(x)for x in rr);stat['realized_hypothesis_input_pairs']+=n;stat['realized_final_inputs']+=n>0
   stat['sensitive_pairs']+=sum(x.get('output_sensitivity')is True for x in rr)
   stat['unknown_capture_pairs']+=sum(x.get('event_unknown')is True for x in rr)
   stat['unsupported_module_pairs']+=sum(x.get('status')=='unsupported_module_scope'for x in rr)
  for st in d['arms'][arm]['stages']:
   for f in st['feedback']:probes[f.get('put_observation',{}).get('status',f.get('status','missing'))]+=1
 final[arm]=dict(stat)
for p in g.glob('*/construction.json'):
 d=json.loads(p.read_text());construction_executions+=d['native_executions']
 percase.append({'case_id':d['case_id'],'native_executions':d['native_executions'],'candidates':d['candidates_tested'],
  'run_statuses':dict(Counter(x.get('status','evaluated')for rec in d['records']for x in rec['runs']))})
# Matching generated tests are compared separately from request/response identities.
identical={}
for p in g.glob('*/result.json'):
 d=json.loads(p.read_text());plain=d['arms']['plain']['stages'][-1]['final_tests']
 identical[d['case_id']]=[a for a,v in d['arms'].items()if a!='plain'and v['stages'][-1]['final_tests']==plain]
out={'integrity':{'readiness':True,'generation_freeze':True,'continuation':True,'freeze_entries':len(json.loads((g/'generation_frozen.json').read_text())),'original_inventory_entries':len(manifest['original_inventory']),'imported_inventory_entries':len(manifest['imported_inventory']),'unique_request_hashes':108,'attempt_response_identity':True},
 'usage':dict(usage,total_tokens=sum(usage.values()),responses=108,physical_dispatches=108,imported_dispatches=6,new_dispatches=102,unknown_completions=0,finish_reasons=dict(Counter(v['response']['finish_reason']for _,v in responses)),exact_tokenization_matches=sum(json.loads((p.parent/'tokenization.json').read_text())['count']==v['response']['input_tokens']for p,v in responses)),
 'response_errors':errors,'construction':percase,'checkpointed_construction_native_executions':construction_executions,'old_case85_uncheckpointed_native_executions':'unknown','final_realization':final,'probe_statuses':dict(probes),'identical_final_lists_to_plain':identical,'summary':score['summary'],'score_provisional':score['provisional'],'score_review_required':score['review_required']}
(R/'trickcatcher_linefacts/analysis/v63_completion/terminal_audit.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:out[k]for k in ('integrity','usage','construction','probe_statuses','identical_final_lists_to_plain')},indent=2))
