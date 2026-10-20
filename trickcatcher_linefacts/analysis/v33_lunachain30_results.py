"""Verify frozen paired run and summarize evidence without model calls or secret access."""
from pathlib import Path
from collections import Counter
import hashlib,json,sys
REPO=Path(__file__).resolve().parents[2];sys.path.insert(0,str(REPO));HERE=REPO/'trickcatcher_linefacts/pipelines/v33_lunachain30';ROOT=REPO/'trickcatcher_linefacts/out/pipelines/v33_lunachain30/humaneval/comparison';LOG=REPO/'trickcatcher_linefacts/out/runlogs_v33_lunachain30'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    protocol=json.loads((ROOT/'protocol.json').read_text());assert all(sha(HERE/k)==v for k,v in protocol.items())
    canary_protocol=json.loads((ROOT.parent/'canary/protocol.json').read_text());assert all(sha(HERE/k)==v for k,v in canary_protocol.items())
    parent=HERE.parent/'v32_qwenchain_or30';assert sha(HERE/'prepared.json')==sha(parent/'prepared.json')
    status=json.loads((LOG/'status.json').read_text());frozen=(ROOT/'generation_frozen.json').exists()
    if frozen:assert all(sha(ROOT/k)==v for k,v in json.loads((ROOT/'generation_frozen.json').read_text()).items())
    completed=ROOT/'completed_evidence_frozen.json'
    if completed.exists():assert all(sha(ROOT/k)==v for k,v in json.loads(completed.read_text()).items())
    report=json.loads((ROOT/'report.json').read_text()) if (ROOT/'report.json').exists() else None
    score=json.loads((ROOT/'io_score.json').read_text()) if (ROOT/'io_score.json').exists() else None
    decisions=Counter();retention=Counter();rawfail=[];concepts=[]
    for path in sorted((ROOT/'cases').glob('*/chain/state.json'),key=lambda p:int(p.parent.parent.name)):
        d=json.loads(path.read_text());n=int(path.parent.parent.name)
        s3=d['stages'].get('S3',{})
        if s3.get('artifact',{}).get('selected_ids'):concepts.append(dict(task_id=n,artifact=s3['artifact']))
        for s,row in d['stages'].items():
            if row['state']=='failed':rawfail.append(dict(task_id=n,stage=s,error=row.get('reason'),raw=row.get('raw')))
            if s=='S5' and row['state']=='valid':
                for x in row['artifact']['decisions']:decisions[x['decision']]+=1
        for x in d.get('final_retention',[]):retention[x['status']]+=1
    # Post-hoc descriptive sensitivity only, leaving frozen primary scores unchanged.
    numeric_equal_only=[]
    if score:
        from trickcatcher_linefacts.pipelines.v33_lunachain30.chain_inputs import parse_literal
        for row in score['rows']:
            for arm,values in row['arms'].items():
                for v in values['inputs']:
                    if not v['different'] or v.get('put_exception'):continue
                    try:
                        if parse_literal(v['put'],output=True)==parse_literal(v['canonical'],output=True):numeric_equal_only.append(dict(task_id=row['task_id'],arm=arm,input_repr=v['input_repr'],put=v['put'],canonical=v['canonical']))
                    except (ValueError,TypeError,KeyError):pass
    equal_keys={(r['task_id'],r['arm'],r['input_repr']) for r in numeric_equal_only}
    value_detection={a:0 for a in ('chain','direct')};value_final={a:0 for a in value_detection};value_paired=[]
    loss_causes=Counter();cap_rejects=[]
    if score:
        for row in score['rows']:
            flags={}
            for arm in value_detection:
                diffs=[v for v in row['arms'][arm]['inputs'] if v['different'] and (row['task_id'],arm,v['input_repr']) not in equal_keys]
                flags[arm]=bool(diffs);value_detection[arm]+=bool(diffs);value_final[arm]+=any(v['final'] for v in diffs)
            value_paired.append(flags)
            if flags['direct'] and not flags['chain']:
                state=json.loads((ROOT/'cases'/str(row['task_id'])/'chain/state.json').read_text());failed=[(k,v) for k,v in state['stages'].items() if v['state']=='failed']
                if failed:cause=failed[0][0]+':'+failed[0][1].get('reason','unknown')
                else:
                    a=state['stages'].get('S3',{}).get('artifact',{});cause='S3_terminal_'+a.get('status','missing') if not a.get('selected_ids') else 'input_search_no_discriminator'
                loss_causes[cause]+=1
        from trickcatcher_linefacts.pipelines.v33_lunachain30 import schemas
        for rejected in rawfail:
            if rejected['error'] not in ('source_refs','comparison_source_refs'):continue
            try:
                raw,_=schemas.extract(rejected['raw']);lengths=[len(x.get('source_ids',[])) for x in raw.get('items',raw.get('comparisons',[]))]
                if any(n>12 for n in lengths):cap_rejects.append(dict(task_id=rejected['task_id'],stage=rejected['stage'],reference_lengths=lengths))
            except ValueError:pass
    sensitivity=dict(scope='post-hoc Python-value equality sensitivity; frozen typed primary unchanged',detection=value_detection,final_detection=value_final,chain_only=sum(x['chain'] and not x['direct'] for x in value_paired),direct_only=sum(x['direct'] and not x['chain'] for x in value_paired))
    shared=sum(all(r['arms'][a]['inputs'] for a in ('chain','direct')) for r in score['rows']) if score else None
    data=dict(value_equality_sensitivity=sensitivity,direct_only_loss_causes=dict(loss_causes),legacy_reference_cap_rejections=cap_rejects,type_only_value_equal_differences=numeric_equal_only,status=status,source_verified=True,generation_verified=frozen,report=report,io_score=score,chain_S5_decisions=dict(decisions),chain_retention_status=dict(retention),shared_nonempty_input_tasks=shared,selected_concepts=concepts,raw_chain_rejects=rawfail,semantic_accuracy=None)
    base=Path(__file__).with_suffix('');base.with_suffix('.json').write_text(json.dumps(data,indent=2)+'\n')
    lines=['# GPT-5.6 Luna low: chain vs direct30 — 2026-10-20','','State: '+status['state']+'. Source frozen verified; generation verified='+str(frozen)+'. Requested CLI identity gpt-5.6-luna/low; server identity not independently reported unless event metadata supplies it. Empty ephemeral cwd, execution host disabled, tool schemas may remain exposed. No paid endpoint/env access.','', 'Same30dev tasks as v32, maximum5calls+12unique inputs per arm/task. Direct allocates3/3/2/2/2new-input slots; chain uses S1/S2/S3 then ≤6S4+≤6S5inputs. Actual calls/tokens may differ due upstream abstention/failure. IDs and orchestration status compiled mechanically; semantics remain model-authored.']
    if report:
        lines+=['','| Arm | Tasks with inputs | Unique inputs | Tasks with final retained inputs | Selected concept tasks |','|---|---:|---:|---:|---:|']
        for arm,s in report['arms'].items():lines.append(f"| {arm} | {s['tasks_with_inputs']} | {s['inputs']} | {s['final_tasks']} | {s['selected_concept_tasks']} |")
        lines+=['','Stage outcomes: '+json.dumps({a:s['stages'] for a,s in report['arms'].items()})+'.','','Errors: '+json.dumps({a:s['errors'] for a,s in report['arms'].items()})+'.','','Task cost/accounting: '+json.dumps(report['costs'])+'. By arm: '+json.dumps(report['arm_costs'])+'. Canary separately: '+json.dumps(report['canary'])+'. Actual dollars/internal HTTP retries unobserved.']
    if score:
        lines+=['','## Post-generation canonical IO','','| Metric | Chain | Direct |','|---|---:|---:|',f"| Any-stage task detection /30 | {score['detection']['chain']} | {score['detection']['direct']} |",f"| Final-retained task detection /30 | {score['final_detection']['chain']} | {score['final_detection']['direct']} |",f"| Random equal-input mean /30 | {score['equal_input_mean']['chain']:.3f} | {score['equal_input_mean']['direct']:.3f} |",'',f"Paired outcomes: chain-only={score['chain_only']}, direct-only={score['direct_only']}. Shared nonempty-input cohort={shared}/30. Equal-input analysis uses200registered random subsets at per-task minimum counts, zero-count tasks stay in denominator; it is descriptive, not a new generation trial."]
    else:lines+=['','No completed IO scoring; do not report partial efficacy.']
    lines+=['','Post-hoc equality audit: '+str(len(numeric_equal_only))+' strict typed-signature differences have equal Python values. These are separately listed and cannot automatically be called semantic bugs; frozen primary scores are unchanged.']
    lines+=['','Python-value sensitivity (post-hoc): '+json.dumps(sensitivity)+'. Direct-only losses by chain stage: '+json.dumps(dict(loss_causes))+'.','','Remaining interface defect: '+str(len(cap_rejects))+' rejects are due to >12 valid source references (legacy cap not clearly stated in the simplified prompt), not evidence of semantic misunderstanding. Another reject omits required uncertainty fields. Frozen outputs are not repaired. The7blocked tasks could add at most7detections if all were rescued; even that upper bound8+7=15 is below direct25. This bound only addresses those gates, not changes to14terminal decisions.','','Recommendation: do not promote this hard-gated five-stage chain as the main method. Direct is stronger under the registered maximum budgets and chain has no unique discoveries. This does not disprove concepts generally; structured reasoning/input prioritization without stopping general generation would be a different method requiring a separate experiment.']
    lines+=['','Chain S5 decisions: '+json.dumps(dict(decisions))+'. Retention statuses: '+json.dumps(dict(retention))+'.','','Canonical comparisons require normal verified reference returns and verified candidate execution. Results remain conditional on spec-domain/mined-filter admissibility; unresolved/reference-exception cases are not counted as confirmed differences. No matched actual-token estimate, held-out generalization, human concept-accuracy certification or mechanism-only causal claim. This is a whole-workflow maximum-budget comparison with direct feedback/generation allocated differently. No additional model calls/retries/expansion are implied.']
    base.with_suffix('.md').write_text('\n'.join(lines)+'\n');print(dict(state=status['state'],complete_score=bool(score),shared_nonempty_input_tasks=shared))
if __name__=='__main__':main()
