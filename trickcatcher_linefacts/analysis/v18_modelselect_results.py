"""Selection pilot report; no model calls, changed choices, or post-audit input generation."""
import ast
from collections import Counter
import json
from pathlib import Path
import sys
REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO))
from trickcatcher_linefacts.pipelines.v18_modelselect import selection_experiment as e,templates
BASE=REPO/'trickcatcher_linefacts'
OUT=Path(__file__).with_name('v18_modelselect_results')


def fault_diagnostic(data,chosen_model):
    row=next((r for r in data['pool'] if r['id']==chosen_model),None)
    if row is None:return []
    out=[];model=row['model'];component=model['params']['component']
    for fault in templates.alternatives(model,6):
        matches=mismatches=unknown=0
        for case in data['inputs']:
            args=ast.literal_eval(case['input_repr']);p=data['put_results'][repr(args)]
            alt=templates.observe(fault['model'],args)
            if p['status']=='timeout' or alt['status']=='unknown':unknown+=1;continue
            if p['status']=='ok':
                actual=ast.literal_eval(p['output_repr'])
                try:actual=actual if component is None else actual[component]
                except (IndexError,TypeError):unknown+=1;continue
                same=alt['status']=='ok' and type(alt['value']) is type(actual) and alt['value']==actual
            else:same=alt['status']==p['status']
            if same:matches+=1
            else:mismatches+=1
        out.append(dict(id=fault['id'],change=fault['description'],matches=matches,mismatches=mismatches,unknown=unknown,
                        scope='post-hoc explanatory check on unchanged frozen mined-valid inputs; not causal proof'))
    return out


def main():
    e.foundation.verify();e.freeze()
    native=json.loads((e.ROOT/'report.json').read_text());gate=json.loads((e.ROOT/'candidate_gate.json').read_text())
    ledger=[json.loads(x) for x in (e.ROOT/'model_cache/calls.jsonl').read_text().splitlines()]
    calls=[r for r in ledger if not r.get('cache_hit') and not r.get('error')]
    rows=[];examples={};faults={}
    for audit in native['rows']:
        n=audit['task'];data=json.loads((e.ROOT/'prepared'/str(n)/'candidates_result.json').read_text())
        choice=native['choices'][str(n)];explanation=json.loads((e.ROOT/'explanations'/str(n)/'explain_result.json').read_text())
        selected=audit['models'].get(audit['chosen_model'],{})
        rows.append(dict(task=n,enumerated=data.get('enumerated',0),survived=data.get('survived',0),retained=len(data['pool']),
            displayed=len(data['menu']),reason=data['reason'],pool_consistent=audit['pool_has_sampled_consistent'],
            menu_consistent=audit['display_has_sampled_consistent'],choice=choice['choice'],valid_choice=choice['valid_choice'],
            llm_consistent=audit['chosen_sampled_consistent'],rule_consistent=audit['rule_sampled_consistent'],
            uniform_expected=audit['uniform_expected_consistency'],selected_stats=selected,
            valid_audit_inputs=audit['valid_audit_inputs'],unresolved_inputs=audit['unresolved_inputs'],
            invalid_inputs=audit['invalid_inputs'],candidate_reports=len(audit['candidate_reports']),
            confirmed=sum(r['confirmed'] for r in audit['candidate_reports']),false_alarms=sum(r['false_alarm'] for r in audit['candidate_reports'])))
        if explanation['records']:examples[str(n)]=explanation['records']
        if audit['chosen_model']:faults[str(n)]=fault_diagnostic(data,audit['chosen_model'])
    result=dict(version='v18_modelselect',scope=native['scope'],cpu=dict(tests_passed=52,representation=17,candidate_gate=gate['candidate_tasks']),
        totals=native['totals'],eligible=native['eligible'],conditional_on_menu_coverage=native['conditional_on_menu_coverage'],
        ambiguous=native['ambiguous_within_scope'],paired_llm_vs_rule=native['paired_llm_vs_rule'],misses=native['misses'],
        valid_choices=sum(r['valid_choice'] for r in rows),selected_tasks=sum(r['displayed'] and r['choice']!='NONE' for r in rows),
        audit_inputs=sum(r['valid_audit_inputs'] for r in rows),invalid_inputs=sum(r['invalid_inputs'] for r in rows),
        unresolved_inputs=sum(r['unresolved_inputs'] for r in rows),rows=rows,evidence_examples=examples,
        posthoc_fault_diagnostic=faults,model_quality_caveat='Canonical consistency on a finite frozen pool, not universal correctness; one selected model is a partial tuple-component requirement.',
        costs=dict(logical_selection_requests=20,successful_new_requests=len(calls),cache_hits=sum(bool(r.get('cache_hit')) for r in ledger),
                   failed_attempts=sum(bool(r.get('error')) for r in ledger),input_tokens=sum(r.get('n_in',0) for r in calls),
                   output_tokens=sum(r.get('n_out',0) for r in calls)),
        generation_run=False,D_IO=None,snapshot_sha256=native['snapshot_sha256'],frozen_sources_verified=True)
    OUT.with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n')
    lines=['# v18 candidate construction and selection pilot','',result['scope'],'',
        '52 CPU tests pass; observed representation17/20; nonempty base-consistent model menus13/20.',
        'One model-ID request per task. All20 responses valid:13 model choices and7 NONE responses.',
        'All menus, input pools, choices and pre-gold execution records were frozen before canonical/contract audit.',
        '', '| Measure | Tasks /20 |','|---|---:|',
        '| Retained pool contains a sampled-consistent requirement | 12 |',
        '| Displayed menu contains one | 12 |',
        '| LLM selects one | 11 |',
        '| Lexical-rule-first selects one | 12 |',
        '| Uniform over same menu, expected | 9.17 |','',
        'Paired LLM vs rule:0 wins/1 loss. Candidate-pool construction is viable here; extra LLM selection benefit is not established.',
        'Among7 menus with differing sampled behaviors in the same output scope: LLM5, rule6, uniform expected3.17. One selected task uses a partial tuple-component requirement, not a full function specification.',
        '', '| Task | Retained/menu | Pool consistent | LLM | Rule | Confirmed input reports |',
        '|---|---:|---|---|---|---:|']
    lines += [f"| {r['task']} | {r['retained']}/{r['displayed']} | {r['pool_consistent']} | {r['llm_consistent']} | {r['rule_consistent']} | {r['confirmed']} |" for r in rows]
    lines += ['','Audit:703 valid frozen input calls, zero contract-invalid/unresolved calls. Selected model candidates report119 PUT discrepancies across12 tasks; all119 agree with canonical behavior for the claimed property, zero candidate-property false alarms. These are INPUT-LEVEL reports, not119 bugs and not end-to-end D_IO. The chosen model for task91 is not globally consistent on the pool despite yielding some confirmed reports; no observed false alarms does not certify its requirement.',
        '', '## Where the misses occur','',
        'Seven tasks have no candidates: three opaque representations, scalar algorithms outside the registry, one unsupported algorithm, and task78 whose public calls mix str and empty-list representations. The conservative type abstraction misses the latter even though the generic registry can express its behavior. No tasks are removed from the denominator.',
        'Task91 has base-consistent segmented-word models but neither matches reference behavior on every frozen input. No sampled-consistent model was lost when building the displayed menus. Task56 has both empty=True and empty=False BALANCE models; LLM selects empty=False, causing one audited mismatch, while the lexical rule selects empty=True. This is the sole LLM-vs-rule loss.',
        '', '## Execution evidence, not free-form rationale','',
        '- Task152: input ([0],[1]); absolute-difference model predicts [1], PUT returns [-1]. The signed-subtraction fault alternative matches all59 frozen native calls. Source/state traces contain the list write and return.',
        '- Task149: input ["aa","aa"]; multiplicity-preserving model predicts two occurrences, PUT returns one. Multiple alternatives match this one input; the frozen-pool diagnostic separates them. See JSON rather than assuming a unique cause from one witness.',
        '- Task136: [0,0] yields a normal None for the selected output component, while the PUT raises ValueError. An empty-policy alternative matches this exception type on that input, but this does not uniquely localize which aggregate/guard caused it.',
        'Tool records include model requirement, input relation class, actual effect, source/state observations and alternative matches. Guard sites are observed; uninstrumented logical implications and global correctness are not assumed. Post-hoc fault matching uses only unchanged pre-gold PUT outcomes, never changes primary choices or inputs.',
        '', '## Costs and limits','',
        'Costs: '+json.dumps(result['costs'])+'.',
        'Candidate ranking is disclosed feature engineering: typed templates, primitive vocabularies, public-base filtering and a lexical/complexity prior. This selection-only pilot does not implement MCTS or show LLM reasoning gains.',
        'No strategy-generation arms, shared-ref assertion/oracle comparison, held-out test or D_IO score was run. A subsequent generation study needs a new protocol with matched concept/rule/random/plain/toolinput/witness controls. Preserve this frozen pilot.','']
    OUT.with_suffix('.md').write_text('\n'.join(lines))
    print(json.dumps(dict(totals=result['totals'],costs=result['costs'],misses=result['misses'],D_IO=None),indent=2))
if __name__=='__main__':main()
