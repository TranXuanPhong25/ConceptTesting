"""Read-only CPU mechanism report; no PUT/model/oracle execution."""
import hashlib
import importlib
import json
from pathlib import Path
import sys
REPO=Path(__file__).resolve().parents[2];sys.path.insert(0,str(REPO))
VERSIONS=[('v20_groundedflow','failed_semantic_audit'),('v20_groundedflow_checked','failed_cycle_audit'),('v20_groundedflow_bounded','failed_size_audit'),('v20_groundedflow_strict','failed_validator_integration'),('v20_groundedflow_domainfix','accepted_cpu_increment_with_limited_scope')]


def read(p):return json.loads(p.read_text())


def main():
    history=[]
    for name,status in VERSIONS:
        e=importlib.import_module('trickcatcher_linefacts.pipelines.'+name+'.grounded_experiment');e.freeze()
        gate=read(e.ROOT/'fixture_gate.json')
        history.append(dict(version=name,review_disposition=status,fixture_count=gate['cases'],fixture_expectations_passed=gate['passed'],source_protocol_verified=True,inventory=(read(e.ROOT/'inventory.json') if (e.ROOT/'inventory.json').exists() else None)))
    e=importlib.import_module('trickcatcher_linefacts.pipelines.v20_groundedflow_domainfix.grounded_experiment')
    inv=read(e.ROOT/'inventory.json');assert inv['tasks']==20 and {r['task'] for r in inv['rows']}==set(e.paths.CONFIG['behavior']['task_ids'])
    sample=[]
    for p in sorted((e.ROOT/'inventory').glob('*/*/result.json')):
        r=read(p)
        if r.get('complete_evidence'):
            assert r['native_checked'] and r['bindings'] and r['relation']['holds'] is False and r['confirmed_bug'] is None
            sample.append(dict(task=int(p.parents[1].name),input_repr=read(p.with_name('job.json'))['input_repr'],bindings=r['bindings'],relation=r['relation'],review_status=r['requirement_review_status']))
    saved=list((e.ROOT/'fixtures').glob('*/result.json'))
    result=dict(scope='known authored fixtures + all20 known dev CPU inventory; no benchmark gain/general correctness',history=history,
        final=dict(version=VERSIONS[-1][0],static_tests=14,fixtures_passed=35,fixture_results_saved=len(saved),fixture_original_plus_instrumented_executions=2*sum('native' in read(p) for p in saved),tasks=20,supported_tasks=inv['supported'],candidate_evidence_inputs=len(sample),reviewed_real_task_evidence=0,model_requests=0,D_IO=None,inventory=inv,evidence=sample,
            costs_limit='inventory reports per-task wall time and PUT execution bounds; total review/test CPU time not measured. Prior copies retained separately, not pooled as successes.'))
    Path(__file__).with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n')
    lines=['# v20 CPU mechanism and independent audit — 2026-10-15','','User requested plan → subagent audit → implementation. Plan was written before two independent read-only reviews; all must-fix resolutions were recorded before code. Both reviewers rechecked later corrections. See PLAN_GROUNDED_FLOW_V20.md and v20_plan_review.md.','','## Scope','','Initial active family is multiplicity only. Tool checks an explicit candidate count relation, links the original argument to an exact set-call source ID, records before/committed per-value losses, follows an approved transparent collection transport to return, and checks that the same eligible value has the same count loss in the final output. Source activation is operation-specific, not a line hit. Native/instrumented signatures include post-input and alias information. Candidate model truth, causality and independent bug confirmation remain separate.','','No symbolic execution, complete FSM, general branch/loop reasoning, arbitrary90-day predicates or automatic spec entailment. Unsupported source/alias/provenance gets an abstention; no coverage threshold.','','## Independent audit history','','| Version | Authored fixture expectations | Independent/integration disposition |','|---|---:|---|']
    for h in history:lines.append(f"| {h['version']} | {h['fixture_expectations_passed']}/{h['fixture_count']} | {h['review_disposition']} |")
    lines+=['','Passing finite fixtures did not override reviewer counterexamples. Lambda lexical scope, builtin entry shadowing, concrete argument provenance, wrong eligible-value losses, masked return flows, cyclic definitions and oversized AST failure were corrected in new copies. All earlier source/protocol/results preserved. cpu_v4 inventory found a validator invocation bug despite fixture success; cpu_v5 adds accepted/rejected validator integration cases and corrects only the calling convention.','','## Final CPU evidence','','-14 static/helper tests and35/35 authored fixture expectations pass. Both reviewers accept the narrow CPU inventory only.','-All20 known dev tasks retained; source subset supports1/20 (task149, already a known design example).19 explicitly unsupported; do not call this unseen validation.','-Task149:12 worker results/native signature checks;3 inputs have a complete candidate count-loss chain,0 reviewed-grounded real-task instances. All confirmed_bug fields remain null.','-No model requests, canonical/reference execution, GPU or D_IO. Costs are CPU-only; inventory PUT upper bound24, plus'+str(result['final']['fixture_original_plus_instrumented_executions'])+' original/instrumented fixture executions. Inventory elapsed time is measured per task; total engineering/review/test time is not.','','Example evidence:']
    for r in sample[:1]:lines+=['',f"Task {r['task']} input `{r['input_repr']}`",'','```json',json.dumps(dict(bindings=r['bindings'],relation=r['relation'],requirement_review_status=r['review_status'],confirmed_bug=None),indent=2),'```']
    lines+=['','## Remaining work','','The mechanism now has checkable operation-to-output evidence for a deliberately narrow direct-input collection subset. Real-task requirement remains an unreviewed v18 proposal; original-argument identity excludes derived collections, conditions/loops are unsupported, and a matching count-loss association does not prove a unique cause. Next changes need a new audited scope: review normative obligations independently, then extend selected branch/loop semantics with their own negative cases. Do not start a generation comparison merely because these fixtures pass. Any GPU pilot needs its own frozen protocol and fair shared-discovery controls.']
    Path(__file__).with_suffix('.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(result['final']|{'inventory':'see JSON','evidence':'see JSON'},indent=2))


if __name__=='__main__':main()
