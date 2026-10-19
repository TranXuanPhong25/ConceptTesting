"""Read-only frozen-run audit/report; never reads secrets or performs model calls."""
from pathlib import Path
from collections import Counter
import hashlib,json
REPO=Path(__file__).resolve().parents[2];HERE=REPO/'trickcatcher_linefacts/pipelines/v32_qwenchain_or30';ROOT=REPO/'trickcatcher_linefacts/out/pipelines/v32_qwenchain_or30/humaneval/dev30';LOG=REPO/'trickcatcher_linefacts/out/runlogs_v32_qwenchain_or30'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    status=json.loads((LOG/'status.json').read_text());protocol=json.loads((ROOT/'protocol.json').read_text());assert all(sha(HERE/k)==v for k,v in protocol.items())
    frozen=(ROOT/'generation_frozen.json').exists()
    if frozen:assert all(sha(ROOT/k)==v for k,v in json.loads((ROOT/'generation_frozen.json').read_text()).items())
    evidence_snapshot=ROOT/'completed_evidence_frozen.json'
    if evidence_snapshot.exists():assert all(sha(ROOT/k)==v for k,v in json.loads(evidence_snapshot.read_text()).items())
    report=json.loads((ROOT/'report.json').read_text()) if (ROOT/'report.json').exists() else None
    score=json.loads((ROOT/'io_score.json').read_text()) if (ROOT/'io_score.json').exists() else None
    inputs=Counter();selected=[];decisions=Counter();predictions=Counter();raw_failed=[];stage_artifacts=Counter();proposals=Counter();with_inputs=0;with_final=0
    for p in sorted((ROOT/'cases').glob('*/state.json'),key=lambda x:int(x.parent.name)):
        state=json.loads(p.read_text());with_inputs+=bool(state['inputs']);task=p.parent.name
        for s,v in state['stages'].items():
            if v['state']=='failed':raw_failed.append(dict(task_id=task,stage=s,error=v.get('reason'),raw=v.get('raw')))
            if v['state']!='valid':continue
            a=v['artifact'];stage_artifacts[s,a['status']]+=1
            if s=='S3' and a['selected_ids']:selected.append(dict(task_id=task,comparisons=a.get('comparisons'),hypotheses=a['items'],selected_ids=a['selected_ids']))
            if s in ('S4','S5'):proposals[s]+=len(a['items'])
            if s=='S5':
                with_final+=bool(a['items'])
                for d in a['decisions']:decisions[d['decision']]+=1
        for x in state['inputs'].values():
            r=x.get('result');inputs['unique']+=1
            if r:inputs[r['status']]+=1;inputs['native_checked']+=bool(r.get('native_checked'))
        for f in state['feedback']:predictions[f.get('prediction_check',{}).get('result','not_checked')]+=1
    ledger=json.loads((ROOT/'transport/ledger.json').read_text()) if (ROOT/'transport/ledger.json').exists() else {}
    evidence=dict(status=status,source_frozen_verified=True,generation_frozen_verified=frozen,report=report,canonical_score=score,selected_concept_tasks=len(selected),selected_claims=selected,input_counts=dict(inputs),tasks_with_inputs=with_inputs,tasks_with_final_proposals=with_final,proposal_counts=dict(proposals),S5_decisions=dict(decisions),S4_prediction_checks=dict(predictions),artifact_statuses=[dict(stage=s,status=v,count=n) for (s,v),n in stage_artifacts.items()],reasoning_tokens=sum(x.get('reasoning_tokens',0) or 0 for x in ledger.values()),providers=sorted(set(x.get('provider') for x in ledger.values() if x.get('provider'))),raw_failed=raw_failed,semantic_accuracy=None)
    out=Path(__file__).with_suffix('');out.with_suffix('.json').write_text(json.dumps(evidence,indent=2)+'\n')
    lines=['# Qwen3.5 OpenRouter30dev feasibility — 2026-10-19','','State: '+status['state']+'. Frozen source verified; generation snapshot verified='+str(frozen)+'. Exact model qwen/qwen3.5-35b-a3b, same v22 prompts/validators; larger visible caps, reasoning requested disabled.30fixed dev tasks, seed20261019. Real secret env only sourced; never read/printed.','','| Stage | Valid | Failed | Blocked | Other |','|---|---:|---:|---:|---:|']
    if report:
        for s,c in report['stage_counts'].items():lines.append(f"| {s} | {c.get('valid',0)} | {c.get('failed',0)} | {c.get('blocked',0)} | {sum(n for k,n in c.items() if k not in ('valid','failed','blocked'))} |")
        lines+=['','Costs: '+json.dumps({k:report[k] for k in ('calls','received','unknown','input_tokens','output_tokens','cost_usd','reserved_unknown_usd')})+'. Reasoning tokens='+str(evidence['reasoning_tokens'])+'.','','Interface failures: '+json.dumps(report['errors'])+'.']
    lines+=['','Accepted selected-concept tasks='+str(len(selected))+'; tasks with any parsed inputs='+str(with_inputs)+'; tasks with final proposals='+str(with_final)+'. Proposals='+json.dumps(dict(proposals))+'. Native inputs='+json.dumps(dict(inputs))+'. S5 decisions='+json.dumps(dict(decisions))+'. S4 prediction checks='+json.dumps(dict(predictions))+'.']
    if score:lines+=['','Post-generation canonical comparison: any-stage discrepancy tasks='+str(score['any_stage_tasks'])+'/30; final-S5 discrepancy tasks='+str(score['final_S5_tasks'])+'/30. Canonical normal native result and matched admissible inputs required for decisive comparison; all unresolved cases remain explicit. This is conditional on mined-filter/spec-domain validity, not a certified semantic success score.']
    else:lines+=['','No completed canonical IO scoring. Do not report D_IO.']
    lines+=['','Qualitative examples: task58 requires sorted common elements but code returns set iteration order; ([10,2,5],[5,2,10]) produces [2,10,5] vs canonical [2,5,10]. Task137 compares normalized numeric strings lexicographically: (\"10\",\"2\") returns \"2\" vs canonical \"10\". Task79 adds a0..255 bound absent from the described conversion domain:256 raises ValueError while canonical returns db100000000db. These selected cases are promising candidate reasoning/input evidence; no aggregate semantic accuracy is inferred.']
    lines+=['','No baseline arms or human semantic adjudication in this small feasibility run. No claim concepts improve over plain/toolinput/placebo; no causal model comparison with earlier runs. Dev tasks have prior exposure; not held-out. Schema-valid claims can still be wrong, and invalid raw claims remain rejected rather than repaired. No model/spend expansion or retry is implied. Detailed raw rejects/claims and task-level IO evidence in JSON.']
    out.with_suffix('.md').write_text('\n'.join(lines)+'\n');print({k:evidence[k] for k in ('selected_concept_tasks','tasks_with_inputs','tasks_with_final_proposals','input_counts')})
if __name__=='__main__':main()
