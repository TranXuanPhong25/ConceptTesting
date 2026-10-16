"""Read frozen controlled16 results; classify interface failures without repairing outputs."""
from collections import Counter
import json
from pathlib import Path
import sys
REPO=Path(__file__).resolve().parents[2];sys.path.insert(0,str(REPO))
from trickcatcher_linefacts.pipelines.v21_qwenchain_pilot import pilot,schemas


def main():
    result=pilot.report();root=pilot.ROOT;forms=Counter();errors=Counter();examples=[]
    for path in sorted((root/'cases').glob('*/state.json')):
        state=json.loads(path.read_text())
        for stage,row in state['stages'].items():
            if row['state']!='failed':continue
            errors[(stage,row.get('reason','unknown'))]+=1;raw=row.get('raw','');form='unparsed'
            try:
                obj,_=schemas.extract(raw,row.get('finish_reason','stop'))
                if 'items' not in obj and 'id' in obj:form='bare_item_missing_envelope'
                elif 'envelope' in obj or 'exact_shape' in obj:form='copied_contract_description'
                elif type(obj.get('items')) is not list:form='items_missing_or_not_list'
                else:form='other_schema_or_reference_error'
            except ValueError:form='truncated_or_unparseable'
            forms[stage,form]+=1
            if len(examples)<6:examples.append(dict(fixture=path.parent.name,stage=stage,error=row.get('reason'),form=form,raw_excerpt=raw[:300]))
    diagnostic=dict(report=result,failure_forms=[dict(stage=k[0],form=k[1],count=v) for k,v in sorted(forms.items())],errors=[dict(stage=k[0],error=k[1],count=v) for k,v in sorted(errors.items())],examples=examples,repair_applied=False,semantic_labels='not_adjudicated; no accuracy claim',D_IO=None)
    base=Path(__file__).with_suffix('');base.with_suffix('.json').write_text(json.dumps(diagnostic,indent=2)+'\n')
    lines=['# Qwen chain controlled16 pilot — 2026-10-16','','Actual Qwen endpoint run, not canned offline fixtures. Frozen source/generation verified by pilot.report. No prompts/validators/budgets repaired after first completion. Human semantic labels remain unadjudicated; no real20/canonical/ref/D_IO.','','| Stage | Valid | Failed | Blocked | N/A |','|---|---:|---:|---:|---:|']
    for stage,c in result['stage_counts'].items():lines.append(f"| {stage} | {c.get('valid',0)} | {c.get('failed',0)} | {c.get('blocked',0)} | {c.get('not_applicable',0)} |")
    lines+=['','Costs: '+json.dumps(result['costs'])+'.','','Mechanical gates: '+json.dumps(result['mechanical_gates'])+'.','','## Observed interface failure forms','']
    for row in diagnostic['failure_forms']:lines.append(f"- {row['stage']}: {row['form']} = {row['count']}.")
    lines+=['','These are output-interface failures, not scores for semantic extraction/alignment. A bare obligation/behavior may contain substantive statements but has not passed the frozen envelope/quote/reference checks. Copying the contract/meta-schema shows ambiguity in the prompt interface; offline parser checks did not establish that Qwen would follow it. Blocked downstream stages cannot measure hypothesis/discriminator quality. Raw responses, alias maps where parsed, stage errors and model usage are preserved.','','Next proposed change, if separately registered: simplify each stage prompt to one unambiguous JSON schema/response shape and validate the output interface on a fresh version before interpreting semantic accuracy. Do not silently wrap or extract exact_shape from these scored responses. A JSON-guided decoding interface could constrain syntax while leaving semantic claims open, but must be checked against the actual server and independently registered.']
    base.with_suffix('.md').write_text('\n'.join(lines)+'\n')
    print('Saved frozen diagnostic',base.with_suffix('.md'))


if __name__=='__main__':main()
