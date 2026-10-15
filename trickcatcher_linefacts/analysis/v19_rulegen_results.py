"""Read-only audit of frozen v19 outputs; no model calls or generation repair."""
import ast
from collections import Counter
import json
from pathlib import Path
import re
import sys
REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO))
from trickcatcher_linefacts.pipelines.v19_rulegen import behavior_experiment as e, behavior_metrics as metrics, oracle_b01 as ob


def load(p):return json.loads(p.read_text())


def main():
    root=e.ROOT;e.verify();e.freeze_generation()
    tasks={t['task']:t for t in e.tasks()};rows=[json.loads(x) for x in (root/'generation/gen.jsonl').read_text().splitlines()]
    provenance=load(root/'parent_provenance.json');parent_snapshot=load(e.PARENT/'selection_pilot/selection_frozen.json')
    for i,t in tasks.items():
        pp=e.PARENT/'prepared'/str(i)/'prepare_result.json';cp=e.PARENT/'selection_pilot/prepared'/str(i)/'candidates_result.json'
        assert e.sha(cp.read_bytes())==provenance[str(i)]['candidate_sha256']==parent_snapshot['tasks'][str(i)]['candidates']
        assert e.sha(pp.read_bytes())==provenance[str(i)]['prepared_sha256']
        assert load(pp)==load(root/'prepared'/str(i)/'prepare_result.json')
        assert e.rule_cards(load(cp))==load(root/'proposals'/str(i)/'summary.json')['shown']
        assert e.common_pool(t,load(cp))==load(root/'prepared'/str(i)/'common_pool.json')
    refs=[r for r in load(e.SOURCE/'oracle/ref_responses.json') if int(r['task']) in tasks]
    assert refs==load(root/'oracle/ref_responses.json')
    indexed={};detected={a:[] for a in e.ARMS}
    for r in rows:
        observations=load(root/'oracle/exec'/f"{r['task']}.json")['calls'];entry=tasks[r['task']]['entry']
        records=[(ob.call_of(a,entry),observations[ob.call_of(a,entry)]) for a in r['assertions']]
        indexed[r['task'],0,r['arm']]=records
        if metrics.metrics([records])['D_IO_samples']:detected[r['arm']].append(r['task'])
    report=load(root/'report.json')
    for arm in e.ARMS:
        assert metrics.metrics([rs for (t,s,a),rs in indexed.items() if a==arm])==report['arms'][arm]
    for c in report['comparisons']:
        assert metrics.comparison(indexed,c['first'],c['second'],c['matched'])==c
    failures=Counter();extracted_valid=0;syntax_count=0;leading_prose=0;truncated=0
    for p in (root/'generation/samples').glob('*/*/0/*/response.json'):
        response=load(p);raw=response['text'];truncated+=response.get('n_out',0)>=1024
        try:e.v4_strategies.checked(raw)
        except (SyntaxError,ValueError) as exc:
            failures[type(exc).__name__]+=1
            if isinstance(exc,SyntaxError):syntax_count+=1
            blocks=re.findall(r'```(?:python|py)?\s*\n(.*?)\n```',raw,re.S)
            if blocks:
                leading_prose+=bool(raw[:raw.find('```')].strip())
                # Diagnostic only: never used to repair frozen generation or score.
                try:e.v4_strategies.checked(blocks[0]);extracted_valid+=1
                except (SyntaxError,ValueError):pass
    ledger=[json.loads(x) for x in (root/'model_cache/calls.jsonl').read_text().splitlines()]
    costs=load(root/'generation/accounting.json')|dict(physical_success_records=sum(not q.get('cache_hit',False) for q in ledger),cache_hits=sum(q.get('cache_hit',False) for q in ledger),transport_attempts=sum(q.get('transport_attempts',0) for q in ledger),new_reference_requests=0,physical_input_tokens=sum(q.get('n_in',0) for q in ledger if not q.get('cache_hit',False)),physical_output_tokens=sum(q.get('n_out',0) for q in ledger if not q.get('cache_hit',False)),shared_parent_preprocessing_excluded=True)
    arms={}
    for a in e.ARMS:
        rs=[r for r in rows if r['arm']==a]
        arms[a]=report['arms'][a]|dict(detected_tasks=sorted(detected[a]),selected_inputs=sum(r['input_calls'] for r in rs),nonempty_tasks=sum(bool(r['selected']) for r in rs),logical_calls=sum(r['llm_calls'] for r in rs),input_tokens=sum(q['input_tokens'] for r in rs for q in r['request_ledger']),output_tokens=sum(q['output_tokens'] for r in rs for q in r['request_ledger']),slot_errors=dict(Counter(q['error'] for r in rs for q in r['attempts'] if 'error' in q)))
    result=dict(verification='protocol, generation, parent provenance, guidance, pools, all20 native scores and comparisons verified',scope=report['scope'],gate=load(root/'concept_gate.json'),costs=costs,arms=arms,comparisons=[{k:v for k,v in c.items() if k!='budgets'} for c in report['comparisons']],candidate_properties=report['candidate_properties'],generation_diagnostics=dict(static_failures=dict(failures),rejected_with_leading_prose_and_fenced_code=leading_prose,rejected_but_first_fenced_block_passes_unchanged_checker=extracted_valid,responses_at_output_cap=truncated,diagnostic_only_no_repair=True))
    target=Path(__file__).with_suffix('.json');target.write_text(json.dumps(result,indent=2)+'\n')
    lines=['# v19_rulegen results — 2026-10-15','','Complete: 20 design dev tasks, K=1; 120 samples. Frozen protocol/generation, pre-gold provenance/guidance, all native scores and comparisons verified. No rerun needed.','','Representation17/20; rule-first model/fault coverage13/20. All20 remain denominator.','','| Arm | D_IO tasks /20 | D_IO input events | Selected inputs | Nonempty tasks | Calls |','|---|---:|---:|---:|---:|---:|']
    for a,r in arms.items():lines.append(f"| {a} | {r['D_IO_samples']} | {r['D_IO']} | {r['selected_inputs']} | {r['nonempty_tasks']} | {r['logical_calls']} |")
    lines+=['','D_IO task detection means at least one contract-valid PUT/reference discrepancy with a saved-reference assertion also passing canonical. Input events count within arms, not distinct bugs.','', 'Primary concept vs behavior:3/20 each; same detected tasks '+str(arms['behavior']['detected_tasks'])+'. Raw and equal-input:0 wins/0 losses, sign p=1. Concept6 input events vs behavior4 does not increase task coverage.','','Equal-input matched mean detecting tasks (100 fixed random subsets; fractional values are means, not new tasks):','']
    for c in result['comparisons']:
        if c['matched']:lines.append(f"- Concept vs {c['second']}: {c['detecting_samples'][0]:.2f} vs {c['detecting_samples'][1]:.2f}; wins/losses {c['wins']}/{c['losses']}, nominal sign p={c['sign_p']:.5g}.")
    lines+=['','Witness-only raw13/20 versus concept3/20; equal-input6.72 vs2.76. Matching discards tasks with zero concept inputs, so does not repair overall generation failure. Witness-only includes pre-gold candidate-model discrepancies plus prior frozen tool witnesses; this is reuse of shared discovery, not13 new LLM discoveries.','','Generation bottleneck: '+str(dict(failures))+' static rejections among300 replies; '+str(leading_prose)+' rejected replies contain leading prose and fenced code. Extracting the first code block would pass the unchanged checker in '+str(extracted_valid)+' cases (read-only diagnosis; no repaired output was generated/scored). Additional worker errors and domain rejection reduce yield. Sparse generation means this run does not isolate concept reasoning quality under a reliable output interface.','','Costs:300 logical requests,269 physical requests and31 exact-cache hits. Logical accounting210,367 input /77,150 output tokens; physical token totals in JSON exclude cache hits.0 new reference requests. Parent v18/preexisting discovery costs excluded from incremental totals; they are common reused preprocessing, not free end-to-end discovery. See JSON for arm costs and transport attempts.','','All arms have zero observed shared-reference false alarms. Candidate-property audit is separate: concept8 confirmed property/card events, behavior5, plain4, placebo6, toolinput12, witness-only51; zero observed property false alarms. These counts can repeat the same input across cards, and are not D_IO. Placebo has4 property abstentions. No global property-validity claim.','','Conclusion: no demonstrated concept generation gain; direct frozen witness reuse is stronger in this exploratory run. Before another comparison, preregister a separate version with a reliable output interface and assess validity/yield; do not change or repair this frozen run.']
    Path(__file__).with_suffix('.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(dict(verification=result['verification'],costs=costs,diagnostics=result['generation_diagnostics'],arms=arms),indent=2))


if __name__=='__main__':main()
