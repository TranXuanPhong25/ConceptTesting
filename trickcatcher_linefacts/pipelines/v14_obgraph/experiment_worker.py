"""Sandboxed execution for obligation-graph and conditional-MR experiments."""
import sys
from pathlib import Path
if not __package__:
    here=Path(__file__).resolve().parent
    sys.path.insert(0,str(here.parents[2]))
    __package__='trickcatcher_linefacts.pipelines.'+here.name
import ast
import inspect
import json
from collections import Counter
from . import experiment_schema as schema, hyp_worker, preconditions, tracer, v4_worker, scorer


def load(card, method):
    # Re-check serialized model code inside the sandbox.
    t=schema.hypotheses.trigger_source(card['T'],load.task)
    out=dict(trigger=preconditions.load_predicate(t,'trigger'))
    if method=='obgraph':
        source=schema.pure(card['O'],'obligation',('args','result'))
        out['obligation']=preconditions.load_predicate(source,'obligation')
    else:
        out['transform']=preconditions.load_predicate(schema.pure(card['tau'],'transform',('args',)),'transform')
        out['relation']=preconditions.load_predicate(schema.pure(card['rho'],'relation',
            ('args','followup_args','result','followup_result')),'relation')
    return out


def truth(fn,*args):
    status,value=tracer.call(fn,(args,{}),T=1)
    return value if status=='ok' and type(value) is bool else None


def valid_args(task,valid,args):
    from .gen_inputs import arity, MAX_INPUT_CHARS
    if type(args) is not tuple or len(args)!=arity(task):return False
    if len(repr(args))>MAX_INPUT_CHARS:return False
    try:
        if ast.literal_eval(repr(args))!=args:return False
    except (ValueError,SyntaxError):return False
    return truth(valid,*args) is True


def pair(card,funcs,task,valid,args):
    status,y=tracer.call(funcs['transform'],((args,),{}),T=1)
    if status!='ok' or not valid_args(task,valid,y) or repr(args)==repr(y):return None
    if card['family']=='PERMUTATION':
        p=card['parameter']
        if type(args[p]) not in (list,tuple,str) or type(y[p]) is not type(args[p]):return None
        if Counter(map(repr,args[p]))!=Counter(map(repr,y[p])):return None
        if any(repr(a)!=repr(b) for i,(a,b) in enumerate(zip(args,y)) if i!=p):return None
    return y


def path_hit(card,trace,probe_sites):
    cells,lines,status,_=trace
    if status=='timeout':return False
    for e in card['path']:
        start,end=int(e['source'][1:]),int(e['target'][1:])
        if end not in lines:return False
        if e['type']=='DATA':
            expected=f'du|{e["scope"]}|{e["name"]}|{start}|{end}|{e["kind"]}'
            if (-2,expected) not in cells:return False
        else:
            probes=[i for i,s in enumerate(probe_sites) if s['line']==start and s['kind'] in ('cond','loop')]
            hit=False
            for sid,value in cells:
                if sid not in probes:continue
                if value==e['outcome']:hit=True
                if value.startswith('loop:'):
                    hit |= ('T' if int(value[5:]) else 'F')==e['outcome']
            if not hit:return False
    return True


def make_context(task):
    pg=tracer.load_module(task['put']);fn=pg[task['entry']]
    valid=preconditions.load_predicate(task['mined_valid_src'],'valid')
    code,sites=tracer.instrument(task['put'])
    iput=tracer.load_module(code,tracer.HOOKS)[task['entry']]
    return fn,valid,iput,sites


def observe(card,funcs,task,ctx,args,method,require_path=True):
    put,valid,iput,sites=ctx
    row=dict(input_repr=repr(args),valid=valid_args(task,valid,args))
    if not row['valid']:return row
    hit=truth(funcs['trigger'],*args)
    row['trigger_hit']=hit is True
    if hit is not True:return row
    if method=='obgraph':
        tr=tracer.trace(iput,(args,{}),T=2)
        row.update(path_hit=path_hit(card,tr,sites),trace_status=tr[2])
        if require_path and not row['path_hit']:return row
        pout=tracer.call(put,(args,{}),T=2)
        o=truth(funcs['obligation'],args,pout[1]) if pout[0]=='ok' else None
        row.update(eligible=True,put_status=pout[0],obligation=o,potential_violation=o is False)
    else:
        y=pair(card,funcs,task,valid,args)
        if y is None:return row
        pout=tracer.call(put,(args,{}),T=2); yout=tracer.call(put,(y,{}),T=2)
        r=truth(funcs['relation'],args,y,pout[1],yout[1]) if pout[0]==yout[0]=='ok' else None
        row.update(eligible=True,followup_repr=repr(y),put_status=pout[0],followup_status=yout[0],
                   relation=r,potential_violation=r is False)
    return row


def prepare(job,directory):
    candidates=hyp_worker.candidates(job['task'],directory)
    g=schema.graph(job['task'],candidates)
    return dict(graph=g,candidates=candidates)


def check(job,directory):
    task=job['task'];method=job['method'];load.task=task
    ctx=make_context(task);put,valid,_,_=ctx
    pg=tracer.load_module(task['put'])
    base,ok=tracer.run_base(pg[task['entry']],task['base'],ns=pg)
    if ok is not True:return dict(cards=[],failures=[dict(reason='base_tests_failed')])
    base_keys={}
    signature=inspect.signature(put)
    for args,kwargs in base:
        bound=signature.bind(*args,**kwargs);bound.apply_defaults()
        positional=tuple(bound.arguments[name] for name in signature.parameters)
        base_keys[repr(positional)]=(positional,{})
    # Draw pool is identical for all cards in a task, with no canonical or ref code.
    pool=v4_worker.draw(dict(task=task,code=task['strategy_src'],seed=job['seed'],n=200,cap=200))
    mutants=[]
    if method=='obgraph':
        for m in job['prepared']['candidates']['survivor_mutants']:
            try:mutants.append((m['k'],tracer.load_module(m['mutant_src'])[task['entry']]))
            except BaseException:pass
    kept,failures=[],[]
    for card in job['cards']:
        try:
            funcs=load(card,method)
            if method=='obgraph': schema.validate_path(job['prepared']['graph'],card['path_ids'],card['concept_ids'])
            base_hits=0;contradiction=False
            for args,kwargs in base_keys.values():
                if truth(funcs['trigger'],*args) is not True:continue
                base_hits+=1
                pout=tracer.call(put,(args,kwargs),T=2)
                if method=='obgraph':
                    if pout[0]=='ok' and truth(funcs['obligation'],args,pout[1]) is False:contradiction=True
                else:
                    y=pair(card,funcs,task,valid,args)
                    if y is not None and repr(y) in base_keys:
                        yout=tracer.call(put,(y,{}),T=2)
                        if pout[0]==yout[0]=='ok' and truth(funcs['relation'],args,y,pout[1],yout[1]) is False:
                            contradiction=True
            if contradiction:raise ValueError('contradicted_by_already_base_tested_behavior')
            observations=[]
            for candidate in pool['candidates']:
                args=tuple(ast.literal_eval(candidate['input_repr']))
                r=observe(card,funcs,task,ctx,args,method)
                if r.get('eligible'):observations.append(r)
            repair_support=[]
            if method=='obgraph':
                for r in [r for r in observations if r.get('potential_violation')][:20]:
                    args=ast.literal_eval(r['input_repr'])
                    for k,mut in mutants:
                        outcome=tracer.call(mut,(args,{}),T=1)
                        if outcome[0]=='ok' and truth(funcs['obligation'],args,outcome[1]) is True:
                            repair_support.append(dict(input_repr=r['input_repr'],mutant=k))
            witness=next((r for r in observations if any(s['input_repr']==r['input_repr'] for s in repair_support)),None)
            witness=witness or next((r for r in observations if r.get('potential_violation')),None)
            witness=witness or next(iter(observations),None)
            kept.append(dict(card,base_trigger_hits=base_hits,witness=witness,witnessed=bool(witness),
                             repair_support=repair_support,eligible_draws=len(observations),
                             potential_violations=sum(r.get('potential_violation',False) for r in observations)))
        except (ValueError,TypeError,SyntaxError,KeyError) as exc:
            failures.append(dict(order=card['order'],reason='card_check_rejected',error=str(exc)[:240]))
    kept.sort(key=lambda h:(0 if h['repair_support'] else 1 if h['potential_violations'] else
                           2 if h['witnessed'] else 3,h['order']))
    return dict(cards=kept,shown=kept[:3],failures=failures,
                domain_draws={k:v for k,v in pool.items() if k!='candidates'},
                counters=dict(discovery_candidates=len(pool['candidates']),base_calls=len(base_keys)))


def select(job,directory):
    task,card,method=job['task'],job.get('card'),job['method'];load.task=task
    ctx=make_context(task);funcs=load(card,method) if card else None
    rows=[]
    for candidate in job['candidates']:
        try:
            args=tuple(ast.literal_eval(candidate['input_repr']))
            if card:
                r=observe(card,funcs,task,ctx,args,method)
                # In graph controls only guidance-free plain/placebo/original-tool arms use validity-only filtering.
                if not job.get('targeted',True) and method=='obgraph':
                    r['eligible']=r['valid']
            else:r=dict(input_repr=repr(args),valid=valid_args(task,ctx[1],args),eligible=False)
            if not card:r['eligible']=r['valid']
            rows.append(r)
        except (ValueError,SyntaxError,TypeError) as exc:
            rows.append(dict(input_repr=candidate.get('input_repr'),eligible=False,error=type(exc).__name__))
    return dict(records=rows,counters=dict(candidates=len(rows),valid=sum(r.get('valid',False) for r in rows),
                trigger_hits=sum(r.get('trigger_hit',False) for r in rows),path_hits=sum(r.get('path_hit',False) for r in rows),
                eligible=sum(r.get('eligible',False) for r in rows)))


def property_score(job,directory):
    """Canonical code enters this scoring-only mode, after immutable generation is complete."""
    task=job['task'];method=job['method'];load.task=task
    canon=tracer.load_module(job['canon'])[task['entry']]
    contract=tracer.load_module(job['contract_src'])[task['entry']]
    put=tracer.load_module(task['put'])[task['entry']]
    records=[]
    for sample in job['samples']:
        for selected in sample['selected']:
            card=selected.get('card')
            if not card:continue
            funcs=load(card,method);args=ast.literal_eval(selected['input_repr'])
            if truth(funcs['trigger'],*args) is not True:continue
            if scorer_valid(contract,args) is not True:continue
            c=tracer.call(canon,(args,{}),T=2);p=tracer.call(put,(args,{}),T=2)
            rec=dict(arm=sample['arm'],sample=sample['sample'],order=card['order'],input_repr=repr(args),
                     canonical_status=c[0],put_status=p[0],canonical_property=None,put_property=None)
            if method=='obgraph' and c[0]==p[0]=='ok':
                rec.update(canonical_property=truth(funcs['obligation'],args,c[1]),
                           put_property=truth(funcs['obligation'],args,p[1]))
            if method=='mr' and selected.get('followup_repr'):
                y=ast.literal_eval(selected['followup_repr'])
                expected=pair(card,funcs,task,preconditions.load_predicate(task['mined_valid_src'],'valid'),args)
                if expected is None or repr(expected)!=repr(y):continue
                if scorer_valid(contract,y) is not True:continue
                cy=tracer.call(canon,(y,{}),T=2);py=tracer.call(put,(y,{}),T=2)
                if c[0]==p[0]==cy[0]==py[0]=='ok':
                    rec.update(canonical_property=truth(funcs['relation'],args,y,c[1],cy[1]),
                               put_property=truth(funcs['relation'],args,y,p[1],py[1]))
            rec.update(candidate_report=rec['put_property'] is False,
                       confirmed_report=rec['put_property'] is False and rec['canonical_property'] is True,
                       false_alarm=rec['put_property'] is False and rec['canonical_property'] is False,
                       abstain=rec['canonical_property'] is None or rec['put_property'] is None)
            records.append(rec)
    return dict(records=records)


def scorer_valid(contract,args):
    status,_=tracer.call(contract,(args,{}),T=1)
    return status=='ok'


def main():
    from .llm_client import atomic_json
    from .v4_evaluation import guard_alarm
    guard_alarm()
    job=json.loads(Path(sys.argv[1]).read_text());directory=Path(sys.argv[1]).parent
    try:
        result={'prepare':prepare,'check':check,'select':select,'property_score':property_score}[job['mode']](job,directory)
    except BaseException as exc:
        result=dict(worker_error=type(exc).__name__+': '+str(exc)[:300])
    atomic_json(Path(sys.argv[2]),result)

if __name__=='__main__':main()
