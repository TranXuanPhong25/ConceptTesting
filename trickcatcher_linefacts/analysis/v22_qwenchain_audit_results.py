"""Audit a frozen contract/alignment-audit pilot without changing its treatment or responses."""
from collections import Counter
import json
from pathlib import Path
import sys
REPO=Path(__file__).resolve().parents[2];sys.path.insert(0,str(REPO))
from trickcatcher_linefacts.pipelines.v22_qwenchain_audit import pilot,schemas
from trickcatcher_linefacts.pipelines.v22_qwenchain_audit.chain_inputs import parse_arguments,literal_for_transport,parse_literal
from trickcatcher_linefacts.pipelines.v22_qwenchain_audit.evidence import compare_prediction


def main():
    report=pilot.report();errors=Counter();forms=Counter();predictions=Counter();examples=[];copied=[];executions=Counter();semantic_samples=[]
    seed=literal_for_transport(parse_literal('([1,1],)'))
    for path in sorted((pilot.ROOT/'cases').glob('*/state.json')):
        state=json.loads(path.read_text());fixture=path.parent.name
        for stage,row in state['stages'].items():
            if row['state']=='failed':
                error=row.get('reason','unknown');errors[stage,error]+=1
                try:
                    obj,_=schemas.extract(row.get('raw',''),row.get('finish_reason','stop'))
                    form='bare_item' if 'items' not in obj and 'id' in obj else 'contract_wrapper' if 'envelope' in obj or 'exact_shape' in obj else 'root_object_with_field_or_reference_failure'
                except ValueError:form='unparseable'
                forms[stage,form]+=1
                if len(examples)<12:examples.append(dict(fixture=fixture,stage=stage,error=error,raw=row.get('raw','')))
            if stage=='S3' and row['state']=='valid':semantic_samples.append(dict(fixture=fixture,artifact=row['artifact']))
            if stage in ('S4','S5') and row['state']=='valid':
                context=json.loads((path.parent/'context.json').read_text());arity=context['task']['arity']
                for probe in row['artifact']['items']:
                    try:literal=literal_for_transport(parse_arguments(probe['input_repr'],arity))
                    except ValueError:continue
                    if literal==seed:copied.append(dict(fixture=fixture,stage=stage,input_repr=probe['input_repr']))
                    match=next((x for x in state['inputs'].values() if x['input_repr']==literal),None)
                    if match and match.get('result'):predictions[stage,compare_prediction(probe['prediction'],match['result'])['result']]+=1
        for r in state['inputs'].values():
            if r.get('result'):executions[r['result']['status']]+=1
    audits=[dict(fixture=row['fixture'],comparison=audit) for row in semantic_samples for audit in row['artifact'].get('comparisons',[])]
    diagnostic=dict(comparisons=audits,report=report,errors=[dict(stage=k[0],reason=k[1],count=v) for k,v in sorted(errors.items())],failure_forms=[dict(stage=k[0],form=k[1],count=v) for k,v in sorted(forms.items())],prediction_checks=[dict(stage=k[0],result=k[1],count=v) for k,v in sorted(predictions.items())],unique_execution_statuses=dict(executions),former_seed_tuple_matches=copied,failed_response_examples=examples,valid_S3_samples=semantic_samples,semantic_accuracy=None,D_IO=None,repair_applied=False)
    base=Path(__file__).with_suffix('');base.with_suffix('.json').write_text(json.dumps(diagnostic,indent=2)+'\n')
    lines=['# Qwen chain contract/alignment diagnostic — 2026-10-16','','Separate preregistered v22 adaptation after observing v21. Same16 seen diagnostic fixtures; S3 cap increased1024 to2048. No unseen generalization or matched-budget effect claim. Source/generation snapshot verified. No response repair or automatic real20/D_IO.','','| Stage | Valid | Failed | Blocked | N/A |','|---|---:|---:|---:|---:|']
    for stage,c in report['stage_counts'].items():lines.append(f"| {stage} | {c.get('valid',0)} | {c.get('failed',0)} | {c.get('blocked',0)} | {c.get('not_applicable',0)} |")
    lines+=['','Costs: '+json.dumps(report['costs'])+'.','','Mechanical gates: '+json.dumps(report['mechanical_gates'])+'.','','## Interface failures','']
    lines += [f"- {r['stage']}: {r['reason']} = {r['count']}." for r in diagnostic['errors']]
    lines+=['','Prediction checks: '+json.dumps(diagnostic['prediction_checks'])+'. Unique native execution statuses: '+json.dumps(diagnostic['unique_execution_statuses'])+'.','','## Model-authored comparisons','']
    for row in semantic_samples:
        a=row['artifact'];lines.append('- '+row['fixture']+': '+a['status']+', selected hypotheses='+str(len(a['selected_ids']))+', verdicts='+json.dumps([x['verdict'] for x in a.get('comparisons',[])])+'.')
    lines+=['','## Limits','','Comparison verdicts, obligations and mismatch statements are Qwen claims, not trusted semantic certificates. Tools validate coverage, references and internal consistency only. Whole-spec quote/span supplied in S1 proves provenance transport, not clause-level entailment. Unknown source observation capabilities remain unknown. Native exact-output prediction matches establish runtime behavior on those inputs, not specification correctness. No canonical/reference scoring or D_IO; human semantic12/16 adjudication remains pending. Former duplicate format seed is absent from this version; tuple-copy tracking against the old seed is descriptive only. Raw failures and valid S3 comparisons are saved in JSON.']
    lines+=['','## Qualitative follow-up','','Accepted f06 S3 distinguishes allowed extra container values from exact set equality. S4 supplies6 admissible unique inputs, including required=[1,2],container=[1,2,3], native result False. Three predictions match native outputs and3 contradict; native checks do not supply a trusted spec oracle. S5 marks unknown and emits0 final inputs.','','f12 is blocked at S2 local_id, so its original alignment miss was not validated in this end-to-end run. A separate S3-only replay appears in v22_qwenchain_s3replay_results.md and must not be pooled into coverage. No empty-guard or quote-span failures remain. Main failures are N aliases used as behavior IDs, item caps, terminal status structure and source references.']
    base.with_suffix('.md').write_text('\n'.join(lines)+'\n');print('Saved',base.with_suffix('.md'))

if __name__=='__main__':main()
