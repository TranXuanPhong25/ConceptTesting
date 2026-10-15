"""Isolated target execution and semantic checks for v16."""
import sys
from pathlib import Path
if not __package__:
    here=Path(__file__).resolve().parent;sys.path.insert(0,str(here.parents[2]))
    __package__='trickcatcher_linefacts.pipelines.'+here.name
import ast
import inspect
import json
from . import behavior as b, semantic as s, tracer, preconditions, v4_worker
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
                draw_accounting={k:v for k,v in draw.items() if k!='candidates'})

def check(job,directory):
    t=job['task'];fn,valid,ns=context(t);p=job['prepared'];out=[];reject=[]
    bases=set(p['base_inputs'])
    for card in job['cards']:
        obs=[];bad=False
        for row in p['discovery_pool']:
            args=ast.literal_eval(row['input_repr'])
            if not valid_args(t,valid,args):continue
            domain=s.truth(card['obligation']['domain'],args)
            disc=s.truth(card['discriminator'],args)
            status,result=tracer.call(fn,(args,{}),T=2)
            relation=s.truth(card['obligation']['relation'],args,result) if domain is True and status=='ok' else None
            if repr(args) in bases and domain is True and relation is False:bad=True
            if domain is True and disc is True:obs.append(dict(input_repr=repr(args),status=status,relation=relation))
        if bad:reject.append(dict(id=card['id'],reason='base_contradiction'));continue
        # Input/output predicates remain candidates; a replay does not prove semantic entailment.
        out.append(dict(card,observations=obs,activation_count=len(obs),witness=next(iter(obs),None),
                        base_contradiction_checked=True))
    return dict(cards=out,shown=out[:CFG['shown_cap']],rejections=reject)

def select(job,directory):
    t=job['task'];_,valid,_=context(t);rows=[]
    for row in job['candidates']:
        try:
            a=tuple(ast.literal_eval(row['input_repr']));good=valid_args(t,valid,a)
            rows.append(dict(input_repr=repr(a),eligible=good))
        except (ValueError,SyntaxError,TypeError):rows.append(dict(input_repr=row.get('input_repr'),eligible=False))
    return dict(records=rows)

def main():
    from .v4_evaluation import guard_alarm
    guard_alarm();job=json.loads(Path(sys.argv[1]).read_text())
    try:r={'prepare':prepare,'check':check,'select':select}[job['mode']](job,Path(sys.argv[1]).parent)
    except BaseException as exc:r=dict(worker_error=type(exc).__name__+': '+str(exc)[:200])
    atomic_json(Path(sys.argv[2]),r)
if __name__=='__main__':main()
