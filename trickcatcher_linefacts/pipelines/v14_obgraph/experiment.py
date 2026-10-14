"""Exploratory LineFacts variants; all generated code runs in namespace-isolated workers.

python -B -m trickcatcher_linefacts.pipelines.<version>.experiment prepare|all --online
Offline prepare needs no endpoint. Online stages consume only the user's Qwen environment.
"""
import argparse
import ast
import collections
import json
import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from . import experiment_schema as schema, gen_inputs, paths, preconditions, v4_runtime, v4_strategies
from .llm_client import Client, atomic_json

HERE=Path(__file__).resolve().parent
ROOT=paths.DATA_OUT/'experiment_smoke'
SOURCE=paths.REPO/'trickcatcher_linefacts/pipelines/v11_fair/out/humaneval'
CFG=paths.CONFIG['experiment']
METHOD=paths.CONFIG['experiment_method']


def isolated(mode,job,directory,python=None,timeout=900):
    directory=Path(directory).resolve();directory.mkdir(parents=True,exist_ok=True)
    jp,op=directory/(mode+'_job.json'),directory/(mode+'_result.json')
    v4_runtime.immutable(jp,dict(job,mode=mode))
    if op.exists():
        cached=json.loads(op.read_text())
        if 'worker_error' not in cached:return cached
        op.unlink()
    result=gen_inputs.sandbox(v4_runtime.interpreter(python),HERE/'experiment_worker.py',jp,op,timeout)
    if 'worker_error' in result:
        op.unlink(missing_ok=True)
        raise RuntimeError(result['worker_error'])
    return result


def source_hashes():
    return v4_runtime.source_hashes() | {f:preconditions.sha((HERE/f).read_bytes()) for f in
        ('experiment.py','experiment_schema.py','experiment_worker.py')}


def tasks():
    bundle=json.loads((SOURCE/'tasks_hybrid.json').read_text())
    by_id={t['task']:t for t in bundle['tasks']}
    selected=[by_id[i] for i in CFG['task_ids']]
    if any(t['split']!='dev' for t in selected):raise ValueError('dev-only experiment')
    return selected


def verify_protocol():
    path=ROOT/'protocol.json'
    if not path.exists():raise RuntimeError('run prepare first')
    frozen=json.loads(path.read_text())
    if (frozen['sources']!=source_hashes() or frozen['config']!=CFG or
        frozen['task_hash']!=preconditions.sha(json.dumps(tasks(),sort_keys=True))):
        raise RuntimeError('source/config/task bundle changed; use a fresh experiment output')


def prepare(workers=4):
    ROOT.mkdir(parents=True,exist_ok=True)
    ts=tasks()
    v4_runtime.immutable(ROOT/'protocol.json',dict(version=paths.CONFIG['VERSION'],method=METHOD,
        config=CFG,task_hash=preconditions.sha(json.dumps(ts,sort_keys=True)),sources=source_hashes()))
    v4_runtime.immutable(ROOT/'generation/tasks.json',dict(tasks=ts,facts_version='v4'))
    def one(t):
        d=ROOT/'prepared'/str(t['task'])
        r=isolated('prepare',dict(task=t),d)
        atomic_json(d/'summary.json',r)
        return dict(task=t['task'],nodes=len(r['graph']['nodes']),edges=len(r['graph']['edges']),
                    concepts=len(r['graph']['concepts']),clauses=len(r['graph']['clauses']),base_ok=r['graph']['base_ok'])
    with ThreadPoolExecutor(workers) as pool:rows=list(pool.map(one,ts))
    atomic_json(ROOT/'preparation.json',rows)
    print('prepare:',len(rows),'tasks;',sum(r['edges'] for r in rows),'typed edges',flush=True)


def client(online,workers):return Client(ROOT/'generation/cache',offline=not online,workers=workers)


def propose(c,workers=4):
    def one(t):
        d=ROOT/'proposals'/str(t['task']);summary=d/'summary.json'
        if summary.exists():return json.loads(summary.read_text())
        prepared=json.loads((ROOT/'prepared'/str(t['task'])/'summary.json').read_text())
        msgs=schema.proposal_messages(t,prepared['graph'],METHOD)
        v4_runtime.immutable(d/'prompt.json',msgs)
        response=c.chat(msgs,CFG['seed']+700000+t['task'],temperature=0,top_p=1,
                        max_tokens=CFG['proposal_max_tokens'])
        atomic_json(d/'response.json',response)
        cards,failures=schema.parse(response['text'],t,prepared['graph'],METHOD,CFG['proposal_cap'])
        checked=isolated('check',dict(task=t,method=METHOD,cards=cards,prepared=prepared,
                                     seed=CFG['seed']+t['task']),d/'check',timeout=1800)
        result=dict(task=t['task'],parsed=len(cards),rejections=failures+checked['failures'],**
                    {k:v for k,v in checked.items() if k!='failures'},
                    proposal_calls=1,proposal_tokens_in=response.get('n_in',0),
                    proposal_tokens_out=response.get('n_out',0),proposal_cache_hit=response.get('cache_hit',False))
        atomic_json(summary,result)
        print('proposal task',t['task'],':',len(result['shown']),'shown;',len(result['rejections']),'rejected',flush=True)
        return result
    with ThreadPoolExecutor(workers) as pool:rows=list(pool.map(one,tasks()))
    atomic_json(ROOT/'proposals/accounting.json',dict(tasks=len(rows),proposal_calls=sum(r['proposal_calls'] for r in rows),
        input_tokens=sum(r['proposal_tokens_in'] for r in rows),output_tokens=sum(r['proposal_tokens_out'] for r in rows),
        shown=sum(len(r['shown']) for r in rows),witnessed=sum(h['witnessed'] for r in rows for h in r['shown']),
        rejections=dict(collections.Counter(x['reason'] for r in rows for x in r['rejections']))))


def witness_pool(task,shown,new=False):
    if new:
        rows=[]
        for h in shown:
            if not h.get('witness'):continue
            rows.append(dict(input_repr=h['witness']['input_repr'],card=h))
            if h['witness'].get('followup_repr'):
                rows.append(dict(input_repr=h['witness']['followup_repr']))
        return rows
    return [dict(input_repr=repr(tuple(r['args']))) for r in gen_inputs.witness_candidates(task)]


def messages(task,arm,card,pool,slot):
    system=('Write one Python def strategy() returning a Hypothesis strategy of FULL positional argument tuples. '
            'Use hypothesis.strategies as st. Reply with Python code only. No imports besides st, no calls to the PUT.')
    if arm in ('plain-strategy','mr-blind'):
        guide='Generate diverse valid boundary inputs; check ordering, ties, duplicates, signs and input sizes.'
    elif arm=='placebo-strategy':
        guide='Covered behavior from existing tests:\n'+ '\n'.join(f['text'] for f in task['placebo_meta'][:3])
    elif arm in ('toolinput','new-toolinput'):
        guide='Use these existing input tuples as seeds and generate diverse valid variants:\n'+str([r['input_repr'] for r in pool])
    else:guide=schema.visible(card,arm)
    user=(f'SPEC AND PUT:\n{task["put"]}\nBASE TESTS:\n{task["base"]}\nGUIDANCE FOR SLOT {slot}:\n{guide}\n'
          'Propose inputs that distinguish the specification from a plausible incorrect behavior. '
          'Respect the domain. A hypothesis/relation is a candidate, not an established truth.')
    return [dict(role='system',content=system),dict(role='user',content=user)]


def sample(task,arm,sample_index,c):
    d=ROOT/'generation/samples'/str(task['task'])/arm/str(sample_index)
    path=d/'summary.json'
    if path.exists():return json.loads(path.read_text())
    proposed=json.loads((ROOT/'proposals'/str(task['task'])/'summary.json').read_text())
    shown=proposed['shown'];new=arm.startswith('new-')
    pool=witness_pool(task,shown,new)
    selected=[];attempts=[];ledger=[]
    if arm in ('witness-only','new-witness-only'):
        # New MR witnesses retain complete pairs; original frozen witnesses are singleton input references.
        if new:
            for h in shown:
                if h.get('witness'):selected.append(dict(h['witness'],card=h,slot=len(selected)))
        else:
            result=isolated('select',dict(task=task,method=METHOD,card=None,candidates=pool,targeted=False),d/'witness')
            selected=[dict(r,slot=0) for r in result['records'] if r.get('eligible')][:3]
    else:
        for slot in range(CFG['strategy_slots']):
            card=shown[slot] if slot<len(shown) else None
            seed=CFG['seed']+task['task']*10000+sample_index*100+slot
            msgs=messages(task,arm,card,pool,slot)
            sd=d/('slot_'+str(slot));v4_runtime.immutable(sd/'prompt.json',msgs)
            # A missing/corrupt response or transport failure aborts for resume, never becomes an empty model answer.
            response=c.chat(msgs,seed,temperature=.7,top_p=.95,max_tokens=CFG['strategy_max_tokens'])
            atomic_json(sd/'response.json',response)
            ledger.append(dict(slot=slot,logical_calls=1,input_tokens=response.get('n_in',0),
                               output_tokens=response.get('n_out',0),cache_hit=response.get('cache_hit',False)))
            try:
                code=v4_strategies.checked(response['text'])
                generated=v4_strategies.draws(code,task,sd/'draw',v4_runtime.interpreter(),seed,
                                               n=CFG['draws'],cap=CFG['draw_cap'])
                targeted=(METHOD=='mr' or arm in ('graph-strategy','card-strategy','graph-noconcept','new-toolinput'))
                flagged=isolated('select',dict(task=task,method=METHOD,card=card,candidates=generated['candidates'],
                                               targeted=targeted),sd/'select')
                good=[r for r in flagged['records'] if r.get('eligible')]
                picked=random.Random(seed).sample(good,min(CFG['selected_per_slot'],len(good)))
                selected.extend(dict(r,slot=slot,card=card) for r in picked)
                attempts.append(dict(slot=slot,counters=flagged['counters'],draws={k:v for k,v in generated.items() if k!='candidates'},
                                     selected=len(picked),has_card=bool(card)))
            except (RuntimeError,ValueError,SyntaxError) as exc:
                attempts.append(dict(slot=slot,error=type(exc).__name__+': '+str(exc)[:240],selected=0))
    inputs={}; retained=[]
    for r in selected:
        literals=[r['input_repr']]+([r['followup_repr']] if r.get('followup_repr') else [])
        needed=[x for x in literals if x not in inputs]
        if len(inputs)+len(set(needed))>CFG['max_input_calls']:continue
        for literal in literals:
            args=ast.literal_eval(literal)
            inputs.setdefault(literal,task['entry']+'('+', '.join(repr(a) for a in args)+')')
        retained.append(r)
    assertions=['assert '+call+' == None' for call in inputs.values()]
    row=dict(task=task['task'],split=task['split'],arm=arm,sample=sample_index,
             assertions=assertions,selected=retained,attempts=attempts,request_ledger=ledger,
             llm_calls=sum(x['logical_calls'] for x in ledger),n_assertions=len(assertions),
             input_calls=len(inputs),expected_placeholders=True,oracle_mode='shared-ref-only',
             proposal_cost_shared_per_task=True,run_id=paths.CONFIG['VERSION'])
    atomic_json(path,row)
    return row


def generate(c,workers=4):
    ts=tasks();arms=paths.CONFIG['arms'];k=CFG['k']
    v4_runtime.immutable(ROOT/'generation/manifest.json',dict(version=paths.CONFIG['VERSION'],method=METHOD,
        arms=arms,K=k,task_ids=CFG['task_ids'],sources=source_hashes(),experiment=True,oracle='ref',
        proposal_cost='shared once per task',generation_calls=3,max_input_calls=12))
    jobs=[(t,a,s) for t in ts for a in arms for s in range(k)]
    def one(job):
        r=sample(*job,c);print('generated',r['task'],r['arm'],r['sample'],r['input_calls'],'inputs',flush=True);return r
    with ThreadPoolExecutor(workers) as pool:rows=list(pool.map(one,jobs))
    (ROOT/'generation/gen.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    # Adapter for inherited ref-input collection. These descriptors are not o0 evaluation results.
    descriptors=[dict(r,asserts=[dict(src=src,canon='not-scored',put='not-scored') for src in r['assertions']],
                      evaluation_kind='ref-input-collection-only') for r in rows]
    (ROOT/'generation/eval.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in descriptors))
    atomic_json(ROOT/'generation/accounting.json',dict(rows=len(rows),generation_calls=sum(r['llm_calls'] for r in rows),
        input_tokens=sum(q.get('input_tokens',0) for r in rows for q in r['request_ledger']),
        output_tokens=sum(q.get('output_tokens',0) for r in rows for q in r['request_ledger'])))


def oracle():
    from . import oracle_b01 as ob
    ob.collect(ROOT/'generation',ROOT/'oracle')
    calls=json.loads((ROOT/'oracle/calls.json').read_text())
    for task_id in CFG['task_ids']:calls.setdefault(str(task_id),[])
    atomic_json(ROOT/'oracle/calls.json',calls)
    refs=json.loads((SOURCE/'oracle/ref_responses.json').read_text())
    refs=[r for r in refs if int(r['task']) in CFG['task_ids']]
    v4_runtime.immutable(ROOT/'oracle/ref_responses.json',refs)
    atomic_json(ROOT/'oracle/reference_provenance.json',dict(source='v11_fair saved spec-only reference responses',
        sha256=preconditions.sha(json.dumps(refs,sort_keys=True)),new_reference_calls=0,
        tasks_with_responses=len({r['task'] for r in refs}),selection_use=False))


def score(workers=4):
    from . import oracle_b01 as ob, rel_report
    ob.variants=lambda *args:[]
    executions=ob.execute(ROOT/'generation',ROOT/'oracle',workers)
    ts,rows=ob.load_run(ROOT/'generation')
    if set(map(str,ts))-set(executions):raise RuntimeError('incomplete ref execution; resume scoring')
    arms=paths.CONFIG['arms'];indexed={}
    for r in rows:
        observed=executions[str(r['task'])]['calls'];entry=ts[r['task']]['entry']
        indexed[r['task'],r['sample'],r['arm']]=[(ob.call_of(a['src'],entry),observed[ob.call_of(a['src'],entry)]) for a in r['asserts']]
    metrics={a:rel_report.metrics([recs for (t,s,arm),recs in indexed.items() if arm==a]) for a in arms}
    primary=('graph-strategy','card-strategy') if METHOD=='obgraph' else ('mr-strategy','mr-blind')
    pairs=[primary]+[(primary[0],a) for a in arms if a not in primary]
    comparisons=[rel_report.comparison(indexed,a,b,matched) for a,b in pairs for matched in (False,True)]
    # Canonical material is read ONLY here, after generation. No results feed back into proposals.
    material={int(r['task_id'].split('/')[1]):r for r in map(json.loads,paths.dataset_paths()['oracle_hep'].read_text().splitlines())}
    def property_one(t):
        h=material[t['task']]
        return isolated('property_score',dict(task=t,method=METHOD,canon=h['prompt']+h['canonical_solution'],
            contract_src=h['prompt']+h['contract']+'\n    pass\n',
            samples=[r for r in rows if r['task']==t['task']]),ROOT/'property_scores'/str(t['task']),timeout=1800)
    with ThreadPoolExecutor(workers) as pool:properties=list(pool.map(property_one,ts.values()))
    prop_records=[r for p in properties for r in p['records']]
    result=dict(scope='20-task dev exploratory smoke; K=1; no confirmatory claims',method=METHOD,
        primary=list(primary),arms=metrics,comparisons=comparisons,
        property_oracle={a:dict(records=len(rs),candidate_reports=sum(r['candidate_report'] for r in rs),
            confirmed_reports=sum(r['confirmed_report'] for r in rs),false_alarms=sum(r['false_alarm'] for r in rs),
            canonical_property_holds=sum(r['canonical_property'] is True for r in rs),
            canonical_property_fails=sum(r['canonical_property'] is False for r in rs),
            abstains=sum(r['abstain'] for r in rs)) for a in arms for rs in [[r for r in prop_records if r['arm']==a]]})
    atomic_json(ROOT/'report.json',result)
    lines=['# '+paths.CONFIG['VERSION']+' exploratory dev smoke','',result['scope'],'',
           '| Arm | D_I samples | D_IO samples | Precision |','|---|---:|---:|---:|']
    lines += [f'| {a} | {m["D_I_samples"]} | {m["D_IO_samples"]} | {m["precision"]} |' for a,m in metrics.items()]
    lines += ['','Primary: '+str(primary), 'Nominal paired comparisons and matched subsets: see report.json.',
              'Property/MR oracle checks are separate; no universal correctness claim.','']
    (ROOT/'REPORT.md').write_text('\n'.join(lines))
    print(json.dumps(result,indent=2),flush=True)
    return result


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('stage',choices=('prepare','propose','generate','oracle','score','all'))
    ap.add_argument('--online',action='store_true')
    ap.add_argument('--workers',type=int,default=4)
    a=ap.parse_args()
    if a.workers<1:ap.error('positive workers required')
    if a.stage in ('prepare','all'):prepare(a.workers)
    verify_protocol()
    if a.stage in ('propose','generate','all'):
        # Client model defaults to the pinned Qwen model; no paid API router is used.
        c=client(a.online,a.workers)
        if a.stage in ('propose','all'):propose(c,a.workers)
        if a.stage in ('generate','all'):generate(c,a.workers)
    if a.stage in ('oracle','all'):oracle()
    if a.stage in ('score','all'):score(a.workers)

if __name__=='__main__':main()
