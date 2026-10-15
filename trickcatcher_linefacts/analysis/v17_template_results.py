"""Summarize frozen v17 gate and the separate predeclared synthetic interface probe."""
from pathlib import Path
import collections
import json
import sys
REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO))
from trickcatcher_linefacts.pipelines.v17_templates import behavior_experiment as e
BASE=REPO/'trickcatcher_linefacts'
OUT=Path(__file__).with_name('v17_template_results')


def main():
    e.verify();g=json.loads((e.ROOT/'concept_gate.json').read_text());rows=g['rows']
    if len(rows)!=20 or {r['task'] for r in rows}!=set(e.CFG['task_ids']):raise ValueError('incomplete cohort')
    ledger=[json.loads(x) for x in (e.ROOT/'model_cache/calls.jsonl').read_text().splitlines()]
    calls=[r for r in ledger if not r.get('cache_hit') and not r.get('error')]
    placeholder={'operation and state observed in source','what the guards actually ensure','missing condition or plausible semantic misunderstanding'}
    cards=[]
    for row in rows:
        for c in row['shown']:
            cards.append(dict(task=row['task'],id=c['id'],model=c['model'],fault=c['fault']['description'],
                copied_placeholder=any(v in placeholder for v in c['reasoning'].values()),
                witness_candidate_violation=c['witness']['candidate_violation'],
                witness_anchor_hit=c['witness']['anchor_hit'],reasoning=c['reasoning']))
    result=dict(version='v17_templates',gate={k:g[k] for k in ('tasks','qualified','required','passed')},
        counts=dict(proposed=sum(len(r['proposed']) for r in rows),compiled=sum(len(r['compiled']) for r in rows),
                    checked_cards=sum(len(r['cards']) for r in rows),shown=sum(len(r['shown']) for r in rows),
                    shown_with_copied_placeholder=sum(c['copied_placeholder'] for c in cards)),
        rejections=dict(collections.Counter(x['reason'] for r in rows for x in r['rejections'])),
        costs=dict(logical_proposal_requests=g['proposal_calls'],successful_new_requests=len(calls),
                   failed_attempts=sum(bool(r.get('error')) for r in ledger),cache_hits=sum(bool(r.get('cache_hit')) for r in ledger),
                   input_tokens=sum(r.get('n_in',0) for r in calls),output_tokens=sum(r.get('n_out',0) for r in calls)),
        cards=cards,rows=[dict(task=r['task'],proposed=len(r['proposed']),compiled=len(r['compiled']),shown=len(r['shown']),rejections=r['rejections']) for r in rows],
        generation_rows=0,scored=(e.ROOT/'report.json').exists(),D_IO=None,frozen_protocol_verified=True)
    gen=e.ROOT/'generation/gen.jsonl'
    if gen.exists():result['generation_rows']=len(gen.read_text().splitlines())
    if not g['passed'] and (result['generation_rows'] or result['scored']):raise ValueError('unexpected work after failed gate')
    probe_root=BASE/'out/template_capability_probe';probe=json.loads((probe_root/'report.json').read_text())
    probe['summary']['synthesis_both_schema_valid_and_example_correct']=sum(r['synthesis_evidence_schema_valid'] and r['synthesis_semantics_on_declared_examples'] for r in probe['rows'])
    result['separate_synthetic_probe']=probe
    OUT.with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n')
    lines=['# v17 templates and separate interface probe','',
        'Frozen 20-task design-dev gate, followed by predeclared six synthetic interface cases. No D_IO evaluation.',
        '',f"Concept gate: **{g['qualified']}/20**, required {g['required']}: failed. Representation 17/20; 44 CPU tests pass.",
        f"Proposed {result['counts']['proposed']}; base-compiled {result['counts']['compiled']}; checked/shown cards {result['counts']['shown']}.",
        'Generation stopped; D_IO unmeasured.','',
        '| Task | Proposed | Base-compiled | Shown |','|---|---:|---:|---:|']
    lines += [f"| {r['task']} | {r['proposed']} | {r['compiled']} | {r['shown']} |" for r in result['rows']]
    lines += ['','Costs: '+json.dumps(result['costs'])+'.','Rejections: '+json.dumps(result['rejections'])+'.','',
        'Qualitative audit of the two shown cards: task 27 uses MAP swapcase with an alternative lower-case map. Its replay has a candidate Unicode behavior discrepancy and source anchor, but its rationale copies all three prompt placeholders. No canonical confirmation was run. Task 78 counts membership in the prime-digit alphabet; the source does equivalent per-digit counting, so the LLM claim that membership is inapplicable is unsupported. Its witness does not violate the candidate requirement. Neither card establishes explicit fault reasoning.',
        'Primary gate remains 2/20 exactly as frozen validators returned; this audit does not silently redefine it. One accepted placeholder rationale demonstrates that length/schema checks are insufficient for reasoning quality.',
        '', '## Separate synthetic interface probe','',
        'Six hand-authored requirements, with declared models/examples and randomized candidate ID positions, registered before these calls. No HumanEval PUT or gold code. Parameter synthesis and candidate-ID selection each have one request/case, temperature 0, max 512 output tokens. Prompts intentionally differ; this is a small interface probe, not an isolated causal test of output format.',
        '', '| Synthetic case | Compiles | Example semantics correct | Evidence schema valid | Choice correct |',
        '|---|---|---|---|---|']
    lines += [f"| {r['id']} | {r['synthesis_compiles']} | {r['synthesis_semantics_on_declared_examples']} | {r['synthesis_evidence_schema_valid']} | {r['choice_correct']} |" for r in probe['rows']]
    lines += ['','Probe counts: '+json.dumps(probe['summary'])+'.',
        'Probe costs: '+json.dumps(probe['costs'])+'.',
        f"Uniform-choice expected correct count: {probe['chance_expected_correct']:.2f}/6; always-C0 baseline: {probe['always_C0_correct']}/6. No generalization claim from six selected synthetic cases.",
        '',
        'Observed direction: parameter/evidence construction remains brittle, while choosing among supplied compiled models succeeds on all six declared cases. This supports investigating tool-built/base-filtered model candidates and LLM selection/ranking, with tool-generated execution evidence rather than free-form rationale. It does not prove bug-detection improvement or entailment on real specs. No v18 benchmark run is part of these results.','']
    OUT.with_suffix('.md').write_text('\n'.join(lines))
    print(json.dumps(dict(gate=result['gate'],counts=result['counts'],v17_costs=result['costs'],probe=probe['summary'],probe_costs=probe['costs']),indent=2))
if __name__=='__main__':main()
