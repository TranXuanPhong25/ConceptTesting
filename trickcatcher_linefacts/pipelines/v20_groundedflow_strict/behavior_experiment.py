"""v19 rule-first concepts, matched generation, frozen shared-reference scoring."""
import argparse
import ast
import hashlib
import json
import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from . import paths, gen_inputs, preconditions, v4_runtime, v4_strategies, template_semantic as semantic, templates, behavior
from .llm_client import Client,atomic_json
HERE=Path(__file__).resolve().parent
SOURCE=paths.REPO/'trickcatcher_linefacts/pipelines/v11_fair/out/humaneval'
ROOT=paths.DATA_OUT/'behavior_smoke'
CFG=paths.CONFIG['behavior']
ARMS=('plain','behavior','behavior+concept','placebo','toolinput','witness-only')
PARENT=HERE.parent/'v18_modelselect/out/humaneval/behavior_smoke'

def sha(value):return hashlib.sha256(value).hexdigest()

def tasks():
    data=json.loads((SOURCE/'tasks_hybrid.json').read_text())['tasks'];by_id={t['task']:t for t in data}
    ts=[by_id[i] for i in CFG['task_ids']]
    if any(t['split']!='dev' for t in ts):raise ValueError('dev-only design cohort')
    return ts

def protocol():
    return dict(version=paths.CONFIG['VERSION'],config=CFG,arms=ARMS,
                sources={p.name:sha(p.read_bytes()) for p in sorted(HERE.glob('*.py'))}|{'config.json':sha((HERE/'config.json').read_bytes())},
                task_hash=sha(json.dumps(tasks(),sort_keys=True).encode()))

def verify():v4_runtime.immutable(ROOT/'protocol.json',protocol())

def isolated(mode,job,directory):
    directory=Path(directory).resolve();directory.mkdir(parents=True,exist_ok=True)
    jp=directory/(mode+'_job.json');op=directory/(mode+'_result.json')
    v4_runtime.immutable(jp,dict(job,mode=mode))
    if op.exists():
        cached=json.loads(op.read_text())
        if 'worker_error' not in cached:return cached
        op.unlink()
    result=gen_inputs.sandbox(v4_runtime.interpreter(),HERE/'behavior_worker.py',jp,op,1800)
    if 'worker_error' in result:
        op.unlink(missing_ok=True);raise RuntimeError(result['worker_error'])
    return result

def prepared(t):
    return json.loads((ROOT/'prepared'/str(t['task'])/'prepare_result.json').read_text())

def rule_cards(candidate):
    if not candidate.get('pool'):return []
    selected=next(r for r in candidate['pool'] if r['id']==candidate['rule_first'])
    return [dict(id='R'+str(i),model=selected['model'],fault=f,
        evidence='All public base tests consistent; candidate requirement, not a proof.',
        block_ids=[],reasoning='Generate admissible inputs distinguishing requirement from this semantic mutation.')
        for i,f in enumerate(templates.alternatives(selected['model'],CFG['shown_cap']))]

def common_pool(t,candidate):
    # Pre-gold candidate discrepancies only. All arms share the same capped pool.
    values={}
    cards=rule_cards(candidate)
    for row in candidate.get('inputs',[]):
        obs=candidate.get('put_results',{}).get(row['input_repr'],{})
        if obs.get('status')!='ok' or not cards:continue
        args=ast.literal_eval(row['input_repr'])
        actual=ast.literal_eval(obs['output_repr'])
        if templates.holds(cards[0]['model'],args,actual) is False:
            values[row['input_repr']]=dict(input_repr=row['input_repr'])
    for r in gen_inputs.witness_candidates(t):
        literal=repr(tuple(r['args']));values.setdefault(literal,dict(input_repr=literal))
    pool=list(values.values())
    return random.Random(CFG['seed']+t['task']).sample(pool,min(12,len(pool)))

def prepare(workers):
    verify();ts=tasks();provenance={};rows=[]
    snapshot=json.loads((PARENT/'selection_pilot/selection_frozen.json').read_text())
    for t in ts:
        i=str(t['task'])
        pp=PARENT/'prepared'/i/'prepare_result.json'
        cp=PARENT/'selection_pilot/prepared'/i/'candidates_result.json'
        # Frozen candidates are checked against their pre-audit snapshot.
        digest=sha(cp.read_bytes())
        if digest != snapshot['tasks'][i]['candidates']:raise RuntimeError('parent candidate snapshot mismatch')
        p=json.loads(pp.read_text());candidate=json.loads(cp.read_text());cards=rule_cards(candidate)
        provenance[i]=dict(prepared_sha256=sha(pp.read_bytes()),candidate_sha256=digest)
        v4_runtime.immutable(ROOT/'prepared'/i/'prepare_result.json',p)
        v4_runtime.immutable(ROOT/'proposals'/i/'summary.json',dict(shown=cards,cards=cards,rule_first=candidate.get('rule_first')))
        v4_runtime.immutable(ROOT/'prepared'/i/'common_pool.json',common_pool(t,candidate))
        rows.append(dict(task=t['task'],usable=p['usable'],model=bool(cards),cards=len(cards)))
    v4_runtime.immutable(ROOT/'parent_provenance.json',provenance)
    v4_runtime.immutable(ROOT/'generation/tasks.json',dict(tasks=ts,facts_version='v4'))
    n=sum(r['model'] for r in rows);u=sum(r['usable'] for r in rows)
    gate=dict(tasks=len(ts),qualified=n,usable=u,required=CFG['concept_gate'],passed=n>=CFG['concept_gate'] and u>=CFG['representation_gate'],rows=rows,proposal_calls=0)
    v4_runtime.immutable(ROOT/'concept_gate.json',gate)
    print('Rule concept gate',n,'/20; representation',u,'/20; passed',gate['passed'],flush=True)
    return gate


def guidance(t,arm,p,cards,pool,slot):
    generic='Explore valid boundary inputs, sizes, ordering, ties, duplicates and signs.'
    if arm=='plain':return generic
    if arm=='flat-facts':return '\n'.join(t['concept_facts'][:3])
    if arm=='placebo':return '\n'.join(t['placebo_facts'][:3])
    if arm=='toolinput':return 'Existing common witnesses: '+str([r['input_repr'] for r in pool])
    if not p['usable']:return 'Behavior summary unavailable within supported scope. '+generic
    text=p['pseudocode']
    if arm=='behavior+concept' and slot<len(cards):
        c=templates.visible(cards[slot])
        text+='\nCandidate semantic concept (not a proof): '+json.dumps(c)
    return text

def generate(client,workers):
    gate=json.loads((ROOT/'concept_gate.json').read_text())
    if not gate['passed']:raise RuntimeError('concept gate failed; no generation')
    v4_runtime.immutable(ROOT/'generation/manifest.json',dict(version=paths.CONFIG['VERSION'],arms=ARMS,K=CFG['k'],
        task_ids=CFG['task_ids'],sources=protocol()['sources'],expected_placeholders=True,oracle='shared-ref'))
    def one(job):
        t,arm=job;d=ROOT/'generation/samples'/str(t['task'])/arm/'0';out=d/'summary.json'
        if out.exists():return json.loads(out.read_text())
        p=prepared(t);proposal=json.loads((ROOT/'proposals'/str(t['task'])/'summary.json').read_text());cards=proposal['shown']
        pool=json.loads((ROOT/'prepared'/str(t['task'])/'common_pool.json').read_text())
        selected=[];ledger=[];attempts=[]
        for slot in range(CFG['strategy_slots']):
            seed=CFG['seed']+t['task']*10000+slot;sd=d/str(slot)
            if arm=='witness-only':candidates=pool if slot==0 else []
            else:
                guide=guidance(t,arm,p,cards,pool,slot)
                msgs=[dict(role='system',content='Write only Python def strategy() returning a Hypothesis strategy of FULL positional argument tuples. Use hypothesis.strategies as st. No PUT calls.'),
                      dict(role='user',content=f'SPEC AND PUT:\n{t["put"]}\nBASE TESTS:\n{t["base"]}\nGUIDANCE:\n{guide}\nRespect original admissible input domain. Generate inputs distinguishing spec from plausible faults.')]
                v4_runtime.immutable(sd/'prompt.json',msgs)
                response=client.chat(msgs,seed,temperature=.7,top_p=.95,max_tokens=CFG['strategy_max_tokens'])
                atomic_json(sd/'response.json',response)
                ledger.append(dict(slot=slot,logical_calls=1,input_tokens=response.get('n_in',0),output_tokens=response.get('n_out',0),cache_hit=response.get('cache_hit',False)))
                try:
                    code=v4_strategies.checked(response['text'])
                    generated=v4_strategies.draws(code,t,sd/'draw',v4_runtime.interpreter(),seed,n=CFG['draws'],cap=CFG['draws'])
                    candidates=generated['candidates']
                except (ValueError,RuntimeError,SyntaxError) as exc:
                    candidates=[];attempts.append(dict(slot=slot,error=type(exc).__name__))
            checked=isolated('select',dict(task=t,candidates=candidates),sd/'select')
            good=[r for r in checked['records'] if r['eligible']]
            chosen=random.Random(seed).sample(good,min(6 if arm=='witness-only' else CFG['selected_per_slot'],len(good)))
            selected+=chosen;attempts.append(dict(slot=slot,candidates=len(candidates),valid=len(good),selected=len(chosen)))
        selected=list({r['input_repr']:r for r in selected}.values())[:CFG['max_input_calls']]
        assertions=[]
        for r in selected:
            args=ast.literal_eval(r['input_repr']);call=t['entry']+'('+', '.join(repr(a) for a in args)+')'
            assertions.append('assert '+call+' == None')
            # Activation measured AFTER common selection, not used to accept/rank inputs.
            r['activated_concepts']=[c['id'] for c in cards if templates.activates(c,args)]
        row=dict(task=t['task'],split=t['split'],arm=arm,sample=0,assertions=assertions,selected=selected,
                 request_ledger=ledger,llm_calls=len(ledger),input_calls=len(selected),attempts=attempts,
                 expected_placeholders=True,oracle_mode='shared-ref-only',run_id=paths.CONFIG['VERSION'])
        atomic_json(out,row);print('generated',t['task'],arm,len(selected),flush=True);return row
    with ThreadPoolExecutor(workers) as pool:rows=list(pool.map(one,[(t,a) for t in tasks() for a in ARMS]))
    (ROOT/'generation/gen.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    desc=[dict(r,asserts=[dict(src=s,canon='not-scored',put='not-scored') for s in r['assertions']],evaluation_kind='ref-input-collection-only') for r in rows]
    (ROOT/'generation/eval.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in desc))
    atomic_json(ROOT/'generation/accounting.json',dict(rows=len(rows),generation_calls=sum(r['llm_calls'] for r in rows),
                input_tokens=sum(q['input_tokens'] for r in rows for q in r['request_ledger']),
                output_tokens=sum(q['output_tokens'] for r in rows for q in r['request_ledger'])))

def freeze_generation():
    rows=[json.loads(line) for line in (ROOT/'generation/gen.jsonl').read_text().splitlines()]
    expected={(i,a,0) for i in CFG['task_ids'] for a in ARMS}
    if len(rows)!=len(expected) or {(r['task'],r['arm'],r['sample']) for r in rows}!=expected:
        raise RuntimeError('generation incomplete; no gold access')
    files=list((ROOT/'generation').rglob('*.json'))+list((ROOT/'generation').glob('*.jsonl'))
    snapshot={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in sorted(files)}
    v4_runtime.immutable(ROOT/'generation_frozen.json',snapshot)

def oracle():
    freeze_generation()
    from . import oracle_b01 as ob
    ob.collect(ROOT/'generation',ROOT/'oracle');calls=json.loads((ROOT/'oracle/calls.json').read_text())
    for i in CFG['task_ids']:calls.setdefault(str(i),[])
    atomic_json(ROOT/'oracle/calls.json',calls)
    refs=[r for r in json.loads((SOURCE/'oracle/ref_responses.json').read_text()) if int(r['task']) in CFG['task_ids']]
    v4_runtime.immutable(ROOT/'oracle/ref_responses.json',refs)
    atomic_json(ROOT/'oracle/reference_provenance.json',dict(source=str(SOURCE/'oracle/ref_responses.json'),sha256=sha(json.dumps(refs,sort_keys=True).encode()),new_reference_calls=0))

def score(workers):
    from . import oracle_b01 as ob, behavior_metrics as metrics
    ob.variants=lambda *args:[]
    ex=ob.execute(ROOT/'generation',ROOT/'oracle',workers);ts,rows=ob.load_run(ROOT/'generation')
    keys={(r['task'],r['arm'],r['sample']) for r in rows}
    if len(rows)!=len(keys) or keys!={(t,a,0) for t in ts for a in ARMS}:raise RuntimeError('incomplete cohort')
    if set(map(str,ts))-set(ex):raise RuntimeError('incomplete ref execution; resume score')
    indexed={}
    for r in rows:
        observations=ex[str(r['task'])]['calls'];entry=ts[r['task']]['entry']
        indexed[r['task'],0,r['arm']]=[(ob.call_of(a['src'],entry),observations[ob.call_of(a['src'],entry)]) for a in r['asserts']]
    pairs=[('behavior+concept','behavior')]+[('behavior+concept',a) for a in ARMS if a not in ('behavior+concept','behavior')]
    result=dict(scope='20-task design dev K=1, exploratory',primary=['behavior+concept','behavior'],
                arms={a:metrics.metrics([rs for (t,s,arm),rs in indexed.items() if arm==a]) for a in ARMS},
                comparisons=[metrics.comparison(indexed,a,b,matched) for a,b in pairs for matched in (False,True)])
    # Canonical source enters only this scoring path, after generation froze.
    def property_one(t):
        native=json.loads((ROOT/'oracle/exec'/(str(t['task'])+'.job.json')).read_text())
        cards=json.loads((ROOT/'proposals'/str(t['task'])/'summary.json').read_text())['shown']
        return isolated('property_score',dict(task=t,canon=native['canon'],contract=native['contract'],
            cards=cards,samples=[r for r in rows if r['task']==t['task']]),ROOT/'property_scores'/str(t['task']))
    with ThreadPoolExecutor(workers) as pool:properties=list(pool.map(property_one,tasks()))
    records=[r for task in properties for r in task['records']]
    result['candidate_properties']={a:dict(records=len(rs),active=sum(r['active'] for r in rs),
        canonical_holds=sum(r['canonical_property'] is True for r in rs),
        canonical_fails=sum(r['canonical_property'] is False for r in rs),
        candidate_reports=sum(r['candidate_report'] for r in rs),confirmed_reports=sum(r['confirmed_report'] for r in rs),
        false_alarms=sum(r['false_alarm'] for r in rs),abstains=sum(r['abstain'] for r in rs))
        for a in ARMS for rs in [[r for r in records if r['arm']==a]]}
    atomic_json(ROOT/'report.json',result)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('stage',choices=['prepare','generate','oracle','score','all']);ap.add_argument('--online',action='store_true');ap.add_argument('--workers',type=int,default=2);a=ap.parse_args()
    if a.workers<1:ap.error('positive workers required')
    if a.stage in ('prepare','all'):
        gate=prepare(a.workers)
        if not gate['passed']:return
    verify()
    if a.stage in ('generate','all'):
        c=Client(ROOT/'model_cache',offline=not a.online,workers=a.workers)
        if a.stage in ('generate','all'):generate(c,a.workers)
    if a.stage in ('oracle','all'):oracle()
    if a.stage in ('score','all'):
        freeze_generation();score(a.workers)
if __name__ == '__main__':
    raise SystemExit('Legacy entrypoint disabled in v20; use grounded_experiment CPU stages.')
