"""Audit a frozen single-shape pilot without changing its treatment or responses."""
from collections import Counter
import json
from pathlib import Path
import sys
REPO=Path(__file__).resolve().parents[2];sys.path.insert(0,str(REPO))
from trickcatcher_linefacts.pipelines.v21_qwenchain_singlejson import pilot,schemas
from trickcatcher_linefacts.pipelines.v21_qwenchain_singlejson.chain_inputs import parse_arguments,literal_for_transport,parse_literal
from trickcatcher_linefacts.pipelines.v21_qwenchain_singlejson.evidence import compare_prediction


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
    diagnostic=dict(report=report,errors=[dict(stage=k[0],reason=k[1],count=v) for k,v in sorted(errors.items())],failure_forms=[dict(stage=k[0],form=k[1],count=v) for k,v in sorted(forms.items())],prediction_checks=[dict(stage=k[0],result=k[1],count=v) for k,v in sorted(predictions.items())],unique_execution_statuses=dict(executions),supplied_seed_copies=copied,failed_response_examples=examples,valid_S3_samples=semantic_samples,semantic_accuracy=None,D_IO=None,repair_applied=False)
    base=Path(__file__).with_suffix('');base.with_suffix('.json').write_text(json.dumps(diagnostic,indent=2)+'\n')
    lines=['# Qwen chain single-output-shape adaptation — 2026-10-16','','Separate exploratory prompt-only adaptation after first pilot format failures. Same16 fixtures/validators/caps/gates. Source and generation snapshot verified by pilot.report. No response repair, pooled score, real20 or D_IO.','','| Stage | Valid | Failed | Blocked | N/A |','|---|---:|---:|---:|---:|']
    for stage,c in report['stage_counts'].items():lines.append(f"| {stage} | {c.get('valid',0)} | {c.get('failed',0)} | {c.get('blocked',0)} | {c.get('not_applicable',0)} |")
    lines+=['','Costs: '+json.dumps(report['costs'])+'.','','Mechanical gates: '+json.dumps(report['mechanical_gates'])+'.','','## Earliest failures','']
    lines += [f"- {r['stage']}: {r['reason']} = {r['count']}." for r in diagnostic['errors']]
    lines+=['','Prediction checks: '+json.dumps(diagnostic['prediction_checks'])+'. Unique native executions: '+json.dumps(diagnostic['unique_execution_statuses'])+'.','','## Interpretation limits','','S1 full-spec quote and span were supplied in the prompt: passing these verifies provenance transport, not independent clause extraction/entailment. S4 includes the concrete format seed ([1,1],); '+str(len(copied))+' proposal slots copied that tuple, so these do not demonstrate novel discriminator discovery. Output predictions describe candidate runtime behavior; a native match does not establish specification correctness. Semantic accuracy remains unadjudicated; the independent human12/16 gate is pending. Operation-value observations remain unknown.','','Post-run audit identified a prompt/validator contract gap: the prompt permits empty strings where needed, while S2 requires nonempty guard/effect. For unconditional code an empty guard is natural, so this rejection is not evidence of misunderstood flow. S3 condition/alternative and S5 condition have related latent gaps. The preflight review and74 offline checks missed this live negative case. Frozen rejections are retained.', '', 'Qualitative independent review: f02 describes sorted(set(xs)) as sorted unique output; f04 distinguishes spec >=limit from implementation >limit in raw claims. Both S2 replies are rejected for an empty guard, so these plausible descriptions do not reach alignment. Conversely f13 passes S1/S2/S3 but overclaims consistency: suitable is undefined in the spec, S1 leaves ambiguity empty and S3 treats first-element behavior as correct based on the empty-list example. A mechanically valid abstention is not a justified semantic conclusion.', '', 'All three valid S3 artifacts abstain (f11/f12/f13). f12 exposes a semantic alignment miss: S2 correctly describes len(xs)>2 returning False, whereas the spec explicitly allows any length; S3 nevertheless says no clear mismatch. The preregistered evaluator marks f12 probe-applicable. This is a qualitative missed mismatch, not a measured D_IO score. f11 is the corresponding correct implementation; f13 remains ambiguous.', '', 'Failed response samples and valid S3 claims are preserved in the JSON report for review. No further prompt changes or generation continuation are implied by this report.']
    base.with_suffix('.md').write_text('\n'.join(lines)+'\n');print('Saved',base.with_suffix('.md'))

if __name__=='__main__':main()
