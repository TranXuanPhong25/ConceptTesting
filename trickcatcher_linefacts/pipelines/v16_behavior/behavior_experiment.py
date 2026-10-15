"""v16 staged runner. prepare is CPU-only; all stops at failed gates or transport errors."""
import argparse
import ast
import hashlib
import json
import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from . import paths, gen_inputs, preconditions, v4_runtime, v4_strategies, semantic
from .llm_client import Client,atomic_json
HERE=Path(__file__).resolve().parent
SOURCE=paths.REPO/'trickcatcher_linefacts/pipelines/v11_fair/out/humaneval'
ROOT=paths.DATA_OUT/'behavior_smoke'
CFG=paths.CONFIG['behavior']
ARMS=('plain','flat-facts','behavior','behavior+concept','placebo','toolinput','witness-only')

def sha(value):return hashlib.sha256(value).hexdigest()

def tasks():
    data=json.loads((SOURCE/'tasks_hybrid.json').read_text())['tasks'];by_id={t['task']:t for t in data}
    ts=[by_id[i] for i in CFG['task_ids']]
    if any(t['split']!='dev' for t in ts):raise ValueError('dev-only design cohort')
    return ts

def protocol():
    return dict(version='v16_behavior',config=CFG,arms=ARMS,
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

def prepare(workers):
    verify();ts=tasks()
    v4_runtime.immutable(ROOT/'generation/tasks.json',dict(tasks=ts,facts_version='v4'))
    def one(t):
        r=isolated('prepare',dict(task=t),ROOT/'prepared'/str(t['task']))
        d=ROOT/'prepared'/str(t['task'])
        atomic_json(d/'behavior_ir.json',r['ir']);atomic_json(d/'abstract_machine.json',r['machine'])
        (d/'pseudocode.txt').write_text(r['pseudocode'])
        row=dict(task=t['task'],usable=r['usable'],opaque=r['ir']['opaque'],base_ok=r['base_ok'],
                 mismatches=r['mismatches'],states=len(r['machine']['states']),transitions=len(r['machine']['transitions']),
                 completed_replays=sum(x['complete'] for x in r['replays']),
                 mutants=len(r['mutants']),distinguished=sum(bool(m.get('witnesses')) for m in r['mutants']))
        print('representation',t['task'],'usable',r['usable'],'states',row['states'],flush=True)
        return row
    with ThreadPoolExecutor(workers) as pool:rows=list(pool.map(one,ts))
    passing=sum(r['usable'] for r in rows);gate=dict(tasks=len(rows),usable=passing,required=CFG['representation_gate'],passed=passing>=CFG['representation_gate'],rows=rows)
    atomic_json(ROOT/'representation_gate.json',gate)
    print('Representation gate:',passing,'/',len(rows),'passed',gate['passed'],flush=True)
    return gate

def prepared(t):return json.loads((ROOT/'prepared'/str(t['task'])/'prepare_result.json').read_text())

def propose(client,workers):
    if not json.loads((ROOT/'representation_gate.json').read_text())['passed']:raise RuntimeError('representation gate failed')
    def one(t):
        p=prepared(t);d=ROOT/'proposals'/str(t['task']);out=d/'summary.json'
        if out.exists():return json.loads(out.read_text())
        ledger=[];errors=[]
        msgs=semantic.messages('spec',t,p);v4_runtime.immutable(d/'spec_prompt.json',msgs)
        response=client.chat(msgs,CFG['seed']+t['task']*10,temperature=0,top_p=1,max_tokens=CFG['proposal_max_tokens'])
        atomic_json(d/'spec_response.json',response);ledger.append(response)
        try:obs,rejected=semantic.obligations(response['text'],p['ir'],CFG['proposal_cap']);errors+=rejected
        except (ValueError,KeyError,TypeError) as exc:obs=[];errors.append(dict(reason='spec_parse',error=type(exc).__name__))
        msgs=semantic.messages('bind',t,p,obs);v4_runtime.immutable(d/'binding_prompt.json',msgs)
        response=client.chat(msgs,CFG['seed']+t['task']*10+1,temperature=0,top_p=1,max_tokens=CFG['proposal_max_tokens'])
        atomic_json(d/'binding_response.json',response);ledger.append(response)
        try:cards,rejected=semantic.cards(response['text'],p['ir'],obs,p['mutants'],CFG['proposal_cap']);errors+=rejected
        except (ValueError,KeyError,TypeError) as exc:cards=[];errors.append(dict(reason='binding_parse',error=type(exc).__name__))
        checked=isolated('check',dict(task=t,cards=cards,prepared=p),d/'check')
        # Unsupported implementation semantics cannot qualify as grounded treatment.
        shown=checked['shown'] if p['usable'] else []
        result=dict(task=t['task'],obligations=obs,shown=shown,cards=checked['cards'],rejections=errors+checked['rejections'],
                    proposal_calls=len(ledger),input_tokens=sum(x.get('n_in',0) for x in ledger),
                    output_tokens=sum(x.get('n_out',0) for x in ledger),qualified=bool(shown),
                    cache_hits=sum(x.get('cache_hit',False) for x in ledger))
        atomic_json(out,result);print('concept',t['task'],'shown',len(shown),flush=True);return result
    with ThreadPoolExecutor(workers) as pool:rows=list(pool.map(one,tasks()))
    qualifying=sum(r['qualified'] for r in rows)
    gate=dict(tasks=len(rows),qualified=qualifying,required=CFG['concept_gate'],passed=qualifying>=CFG['concept_gate'],
              proposal_calls=sum(r['proposal_calls'] for r in rows),input_tokens=sum(r['input_tokens'] for r in rows),
              output_tokens=sum(r['output_tokens'] for r in rows),rows=rows)
    atomic_json(ROOT/'concept_gate.json',gate);return gate

def guidance(t,arm,p,cards,pool,slot):
    generic='Explore valid boundary inputs, sizes, ordering, ties, duplicates and signs.'
    if arm=='plain':return generic
    if arm=='flat-facts':return '\n'.join(t['concept_facts'][:3])
    if arm=='placebo':return '\n'.join(t['placebo_facts'][:3])
    if arm=='toolinput':return 'Existing common witnesses: '+str([r['input_repr'] for r in pool])
    if not p['usable']:return 'Behavior summary unavailable within supported scope. '+generic
    text=p['pseudocode']
    if arm=='behavior+concept' and slot<len(cards):
        c={k:v for k,v in cards[slot].items() if k not in ('observations','witness','activation_count')}
        text+='\nCandidate semantic concept (not a proof): '+json.dumps(c)
    return text

def generate(client,workers):
    gate=json.loads((ROOT/'concept_gate.json').read_text())
    if not gate['passed']:raise RuntimeError('concept gate failed; no generation')
    v4_runtime.immutable(ROOT/'generation/manifest.json',dict(version='v16_behavior',arms=ARMS,K=CFG['k'],
        task_ids=CFG['task_ids'],sources=protocol()['sources'],expected_placeholders=True,oracle='shared-ref'))
    def one(job):
        t,arm=job;d=ROOT/'generation/samples'/str(t['task'])/arm/'0';out=d/'summary.json'
        if out.exists():return json.loads(out.read_text())
        p=prepared(t);cards=json.loads((ROOT/'proposals'/str(t['task'])/'summary.json').read_text())['shown']
        # Common pool for every task: old frozen witnesses + bounded new mutant witnesses.
        pool={repr(tuple(r['args'])):dict(input_repr=repr(tuple(r['args']))) for r in gen_inputs.witness_candidates(t)}
        for m in p['mutants']:
            for w in m.get('witnesses',[]):pool.setdefault(w['input_repr'],dict(input_repr=w['input_repr']))
        pool=list(pool.values());selected=[];ledger=[];attempts=[]
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
            r['activated_concepts']=[c['id'] for c in cards if semantic.truth(c['discriminator'],args) is True and semantic.truth(c['obligation']['domain'],args) is True]
        row=dict(task=t['task'],split=t['split'],arm=arm,sample=0,assertions=assertions,selected=selected,
                 request_ledger=ledger,llm_calls=len(ledger),input_calls=len(selected),attempts=attempts,
                 expected_placeholders=True,oracle_mode='shared-ref-only',run_id='v16_behavior')
        atomic_json(out,row);print('generated',t['task'],arm,len(selected),flush=True);return row
    with ThreadPoolExecutor(workers) as pool:rows=list(pool.map(one,[(t,a) for t in tasks() for a in ARMS]))
    (ROOT/'generation/gen.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    desc=[dict(r,asserts=[dict(src=s,canon='not-scored',put='not-scored') for s in r['assertions']],evaluation_kind='ref-input-collection-only') for r in rows]
    (ROOT/'generation/eval.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in desc))
    atomic_json(ROOT/'generation/accounting.json',dict(rows=len(rows),generation_calls=sum(r['llm_calls'] for r in rows),
                input_tokens=sum(q['input_tokens'] for r in rows for q in r['request_ledger']),
                output_tokens=sum(q['output_tokens'] for r in rows for q in r['request_ledger'])))

def oracle():
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
    pairs=[('behavior+concept','behavior'),('behavior','flat-facts')]+[('behavior+concept',a) for a in ARMS if a not in ('behavior+concept','behavior')]
    result=dict(scope='20-task design dev K=1, exploratory',primary=['behavior+concept','behavior'],
                arms={a:metrics.metrics([rs for (t,s,arm),rs in indexed.items() if arm==a]) for a in ARMS},
                comparisons=[metrics.comparison(indexed,a,b,matched) for a,b in pairs for matched in (False,True)])
    atomic_json(ROOT/'report.json',result)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('stage',choices=['prepare','propose','generate','oracle','score','all']);ap.add_argument('--online',action='store_true');ap.add_argument('--workers',type=int,default=2);a=ap.parse_args()
    if a.workers<1:ap.error('positive workers required')
    if a.stage in ('prepare','all'):
        gate=prepare(a.workers)
        if not gate['passed']:return
    verify()
    if a.stage in ('propose','generate','all'):
        c=Client(ROOT/'model_cache',offline=not a.online,workers=a.workers)
        if a.stage in ('propose','all'):
            if not propose(c,a.workers)['passed']:return
        if a.stage in ('generate','all'):generate(c,a.workers)
    if a.stage in ('oracle','all'):oracle()
    if a.stage in ('score','all'):score(a.workers)
if __name__=='__main__':main()
