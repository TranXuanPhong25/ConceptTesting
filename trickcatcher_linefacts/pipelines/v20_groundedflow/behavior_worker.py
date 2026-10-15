"""Isolated target execution and semantic checks for v16."""
import sys
from pathlib import Path
if not __package__:
    here=Path(__file__).resolve().parent;sys.path.insert(0,str(here.parents[2]))
    __package__='trickcatcher_linefacts.pipelines.'+here.name
import ast
import inspect
import json
from . import behavior as b, semantic as s, tracer, preconditions, v4_worker, templates
from .llm_client import atomic_json
from .paths import CONFIG
CFG=CONFIG['behavior']

def context(task):
    ns=tracer.load_module(task['put']);fn=ns[task['entry']]
    valid=preconditions.load_predicate(task['mined_valid_src'],'valid')
    return fn,valid,ns

def valid_args(task,valid,args):
    if type(args) is not tuple or len(repr(args))>1000:return False
    if len(args)!=len(b.function(task['put'],task['entry']).args.args):return False
    status,value=tracer.call(valid,(args,{}),T=1)
    return status=='ok' and value is True

def output(fn,args):
    status,value=tracer.call(fn,(args,{}),T=CFG['operation_timeout'])
    return dict(status=status,output_repr=repr(value) if status=='ok' else None)

def prepare(job,directory):
    t=job['task'];ir=b.build(t['put'],t['entry']);fn,valid,ns=context(t)
    calls,base_ok=tracer.run_base(fn,t['base'],ns=ns)
    sig=inspect.signature(fn);base=[]
    for args,kwargs in calls:
        bound=sig.bind(*args,**kwargs);bound.apply_defaults();a=tuple(bound.arguments[p] for p in sig.parameters)
        if repr(a) not in {repr(x) for x in base}:base.append(a)
    all_base=list(base)
    base=base[:CFG['base_replays']]
    draw=v4_worker.draw(dict(task=t,code=t['strategy_src'],seed=CFG['seed']+t['task'],
                             n=CFG['discovery_draws'],cap=CFG['discovery_draws']))
    pool=list(base)
    for r in draw['candidates']:
        try:a=tuple(ast.literal_eval(r['input_repr']))
        except (ValueError,SyntaxError,TypeError):continue
        if repr(a) not in {repr(x) for x in pool} and valid_args(t,valid,a):pool.append(a)
    replays=[];mismatches=[]
    for args in base:
        replay=b.replay(t['put'],t['entry'],args,max_events=CFG['max_events'],timeout=CFG['operation_timeout'])
        original=output(fn,args)
        replay['native_comparison']=original
        # Timeouts indicate unresolved replay; do not label timeout/non-timeout as semantic inequality.
        replay['matches_native']=None if 'timeout' in (replay['status'],original['status']) else all(replay[k]==original[k] for k in original)
        if replay['matches_native'] is False:mismatches.append(repr(args))
        replays.append(replay)
    mutations=b.mutants(t['put'],t['entry'],CFG['max_mutants']);common=pool[:CFG['mutant_replays']]
    originals={repr(a):output(fn,a) for a in common}
    for m in mutations:
        witnesses=[]
        try:mut=tracer.load_module(m['source'])[t['entry']]
        except BaseException:m['semantic_status']='invalid_load';continue
        for args in common:
            old=originals[repr(args)];new=output(mut,args)
            if old['status']=='timeout' or new['status']=='timeout':continue
            if old!=new:witnesses.append(dict(input_repr=repr(args),original=old,alternative=new,
                                              base_distinguished=repr(args) in {repr(x) for x in base}))
        m['witnesses']=witnesses;m['semantic_status']='bounded_distinguished' if witnesses else 'unknown_not_equivalent'
    observed_machine=b.machine(replays)
    # Preserve first/last observations after building full observed projection; reduce IPC size only.
    for replay in replays:
        events=replay['events'];replay['recorded_events']=len(events)
        replay['omitted_events']=max(0,len(events)-128)
        if len(events)>128:replay['events']=events[:64]+events[-64:]
        replay['trace_retention']='first64+last64; machine built before retention'
    usable=ir['structural_supported'] and base_ok is True and any(r['matches_native'] is True and r['status']=='ok' for r in replays) and not mismatches
    return dict(ir=ir,pseudocode=b.pseudocode(ir),machine=observed_machine,replays=replays,
                base_ok=base_ok,mismatches=mismatches,usable=usable,mutants=mutations,
                discovery_pool=[dict(input_repr=repr(a)) for a in pool],base_inputs=[repr(a) for a in base],
                all_base_inputs=[repr(a) for a in all_base[:CFG['base_verification_cap']]],
                base_verification_complete=len(all_base)<=CFG['base_verification_cap'],
                draw_accounting={k:v for k,v in draw.items() if k!='candidates'})

def compile_models(job,directory):
    t=job['task'];p=job['prepared'];fn,valid,_=context(t)
    if not p['base_verification_complete']:return dict(proposals=[],rejections=[dict(reason='base_verification_cap_exceeded')])
    base=[]
    for literal in p['all_base_inputs']:
        args=ast.literal_eval(literal);status,value=tracer.call(fn,(args,{}),T=2)
        base.append((args,status,value))
    accepted=[];reject=[]
    for proposal in job['proposals']:
        bad=False;unknown=False
        for args,status,value in base:
            relation=templates.holds(proposal['model'],args,value) if status=='ok' else None
            bad|=relation is False;unknown|=relation is None
        if bad or unknown:
            reject.append(dict(proposal=proposal['id'],reason='base_contradiction' if bad else 'base_unknown'))
            continue
        faults=[]
        for fault in templates.alternatives(proposal['model'],CFG['template_fault_cap']):
            # Remove alternatives incompatible with observed argument types, not merely unhit alternatives.
            if any(templates.observe(fault['model'],args)['status']=='unknown' for args,_,_ in base):continue
            fault=dict(fault,id='F'+str(len(faults)));faults.append(fault)
        if not faults:
            reject.append(dict(proposal=proposal['id'],reason='no_typed_alternative'));continue
        accepted.append(dict(proposal,id='P'+str(len(accepted)),faults=faults,base_checked=len(base)))
    return dict(proposals=accepted,rejections=reject,base_calls=len(base))


def check(job,directory):
    t=job['task'];fn,valid,_=context(t);p=job['prepared'];out=[];reject=[]
    bases=set(p['all_base_inputs']);blocks={x['id']:x for x in p['ir']['blocks']}
    pool={r['input_repr']:r for r in p['discovery_pool']}
    from .gen_inputs import witness_candidates
    for r in witness_candidates(t):
        literal=repr(tuple(r['args']));pool.setdefault(literal,dict(input_repr=literal))
    for card in job['cards']:
        observations=[]
        for row in pool.values():
            args=ast.literal_eval(row['input_repr'])
            if not valid_args(t,valid,args) or not templates.activates(card,args):continue
            status,result=tracer.call(fn,(args,{}),T=2)
            relation=templates.holds(card['model'],args,result) if status=='ok' else None
            observations.append(dict(input_repr=repr(args),status=status,relation=relation,
                candidate_violation=status not in ('ok','timeout') or relation is False,
                base_distinguished=repr(args) in bases))
        observations.sort(key=lambda r:(r['base_distinguished'],not r['candidate_violation'],r['input_repr']))
        source_lines={blocks[x]['line'] for x in card['block_ids']};witness=None
        for row in observations[:3]:
            replay=b.replay(t['put'],t['entry'],ast.literal_eval(row['input_repr']),max_events=CFG['max_events'],timeout=2)
            row['anchor_hit']=any(e['location'] in source_lines for e in replay['events'])
            row['trace_status']=replay['status']
            if row['anchor_hit'] and replay['complete']:witness=row;break
        if witness is None:
            reject.append(dict(id=card['id'],reason='no_replayed_discriminator_with_anchor'));continue
        out.append(dict(card,observations=observations,witness=witness,
                        activation_count=len(observations),base_contradiction_checked=True))
    out.sort(key=lambda c:(c['witness']['base_distinguished'],not c['witness']['candidate_violation'],c['id']))
    return dict(cards=out,shown=out[:CFG['shown_cap']],rejections=reject)


def select(job,directory):
    t=job['task'];_,valid,_=context(t);rows=[]
    for row in job['candidates']:
        try:
            a=tuple(ast.literal_eval(row['input_repr']));good=valid_args(t,valid,a)
            rows.append(dict(input_repr=repr(a),eligible=good))
        except (ValueError,SyntaxError,TypeError):rows.append(dict(input_repr=row.get('input_repr'),eligible=False))
    return dict(records=rows)

def property_score(job,directory):
    # This mode is invoked only after immutable generation and native shared-ref scoring.
    task=job['task'];fn,_,_=context(task)
    canon=tracer.load_module(job['canon'])[task['entry']]
    contract=tracer.load_module(job['contract'])[task['entry']]
    cache={};records=[]
    for sample in job['samples']:
        for row in sample['selected']:
            literal=row['input_repr'];args=ast.literal_eval(literal)
            if literal not in cache:
                valid=tracer.call(contract,(args,{}),T=1)[0]=='ok'
                c=tracer.call(canon,(args,{}),T=2) if valid else ('invalid',None)
                p=tracer.call(fn,(args,{}),T=2) if valid else ('invalid',None)
                cache[literal]=(valid,c,p)
            valid,c,p=cache[literal]
            for card in job['cards']:
                active=templates.activates(card,args)
                cp=templates.holds(card['model'],args,c[1]) if valid and c[0]=='ok' else False if valid and c[0] not in ('timeout','invalid') else None
                pp=templates.holds(card['model'],args,p[1]) if valid and p[0]=='ok' else False if valid and p[0] not in ('timeout','invalid') else None
                candidate=active and pp is False
                records.append(dict(arm=sample['arm'],card=card['id'],input_repr=literal,active=active,
                    canonical_property=cp,put_property=pp,candidate_report=candidate,
                    confirmed_report=candidate and cp is True,false_alarm=candidate and cp is False,
                    abstain=cp is None or pp is None))
    return dict(records=records)


def main():
    from .v4_evaluation import guard_alarm
    guard_alarm();job=json.loads(Path(sys.argv[1]).read_text())
    try:r={'prepare':prepare,'compile':compile_models,'check':check,'select':select,'property_score':property_score}[job['mode']](job,Path(sys.argv[1]).parent)
    except BaseException as exc:r=dict(worker_error=type(exc).__name__+': '+str(exc)[:200])
    atomic_json(Path(sys.argv[2]),r)
if __name__=='__main__':main()
