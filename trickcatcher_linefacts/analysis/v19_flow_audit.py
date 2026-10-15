"""CPU audit of implementation scope and frozen v19 prompt wiring; no experiment repair."""
import ast
import json
from pathlib import Path
import sys
REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO))
from trickcatcher_linefacts.pipelines.v19_rulegen import behavior as b,behavior_experiment as e,templates


def load(p):return json.loads(p.read_text())


def main():
    e.verify();e.freeze_generation()
    counterexample='''def f(xs):
    total = 0
    for x in xs:
        total += x
    match total:
        case 0:
            return "zero"
        case _:
            return "nonzero"
'''
    ir=b.build(counterexample,'f');update=next(r for r in ir['blocks'] if r['id'].endswith('AugAssign'))
    match=next(r for r in ir['blocks'] if r['id'].endswith('Match'))
    assert 'total' not in update['reads']
    assert ir['structural_supported'] and match['kind']=='STEP'
    assert not any(r['kind']=='RETURN' for r in ir['blocks'])
    records=[];omissions=[]
    for t in e.tasks():
        tid=t['task'];prepared=e.prepared(t);cards=load(e.ROOT/'proposals'/str(tid)/'summary.json')['shown']
        if not cards:continue
        missing=templates.alternatives(cards[0]['model'],6)[len(cards):]
        omissions.append(dict(task=tid,shown=[r['fault']['change'] for r in cards],omitted=[r['change'] for r in missing]))
        for slot in range(e.CFG['strategy_slots']):
            prompt=load(e.ROOT/'generation/samples'/str(tid)/'behavior+concept/0'/str(slot)/'prompt.json')
            pool=load(e.ROOT/'prepared'/str(tid)/'common_pool.json')
            guide=e.guidance(t,'behavior+concept',prepared,cards,pool,slot)
            assert prompt[1]['content'].endswith(guide+'\nRespect original admissible input domain. Generate inputs distinguishing spec from plausible faults.')
            records.append(dict(task=tid,slot=slot,has_card=slot<len(cards),blocks_bound=cards[slot]['block_ids'] if slot<len(cards) else [],has_catalog_definition=any(templates.CATALOG[k] in prompt[1]['content'] for k in templates.CATALOG)))
    p149=e.prepared({'task':149});cards149=load(e.ROOT/'proposals/149/summary.json')['shown'];model=cards149[0]['model']
    distinct=next(r for r in templates.alternatives(model,6) if r['change']['field']=='distinct')
    assert not any(c['fault']['change']['field']=='distinct' for c in cards149)
    args=(['aa','aa'],)
    assert templates.expected(model,args)==['aa','aa']
    assert templates.expected(distinct['model'],args)==['aa']
    prepared_read='machine' in __import__('inspect').getsource(e.guidance)
    assert not prepared_read
    findings=dict(frozen_verified=True,scope='implementation audit only; no new generation/scoring',
        augmented_assignment_read_omission=dict(source='total += x',actual=update,expected_reads=['total','x']),
        unsupported_match_accepted=dict(source=counterexample,structural_supported=ir['structural_supported'],blocks=ir['blocks'],edges=ir['edges']),
        prompt_wiring=dict(audited_slots=len(records),concept_slots=sum(r['has_card'] for r in records),all_source_bindings_empty=all(not r['blocks_bound'] for r in records),catalog_definitions_provided=sum(r['has_catalog_definition'] for r in records),guidance_reads_machine=prepared_read),
        fault_truncation=omissions,
        task149=dict(put=e.tasks()[e.CFG['task_ids'].index(149)]['put'],pseudocode=p149['pseudocode'],selected_faults=[c['fault']['change'] for c in cards149],missing_relevant_fault=distinct['change'],input_repr=repr(args),model_output=templates.expected(model,args),dedup_alternative_output=templates.expected(distinct['model'],args)),
        interpretation='Generic model parameters + AST pseudocode prompt augmentation; no connected obligation-to-node-to-trigger engine, symbolic path solving, causal localization, or search over the observed machine.')
    Path(__file__).with_suffix('.json').write_text(json.dumps(findings,indent=2)+'\n')
    print(json.dumps(dict(frozen_verified=True,prompt_wiring=findings['prompt_wiring'],task149_fault_omitted=True,read_write_counterexample=True,unsupported_match_counterexample=True),indent=2))


if __name__=='__main__':main()
