"""Isolated public-evidence construction and post-freeze canonical audit."""
import sys
from pathlib import Path
if not __package__:
    here=Path(__file__).resolve().parent;sys.path.insert(0,str(here.parents[2]))
    __package__='trickcatcher_linefacts.pipelines.'+here.name
import ast
import json
import random
from . import behavior,templates,candidate_models as cm,tracer
from .behavior_worker import context,valid_args,output
from .gen_inputs import witness_candidates
from .llm_client import atomic_json
from .paths import CONFIG
CFG=CONFIG['selection_pilot']


def candidates(job,directory):
    task=job['task'];prepared=job['prepared'];fn,valid,_=context(task)
    base=[]
    for literal in prepared['all_base_inputs']:
        args=ast.literal_eval(literal);status,value=tracer.call(fn,(args,{}),T=2)
        if status!='ok':return dict(pool=[],menu=[],inputs=[],reason='base_execution_unresolved')
        base.append(dict(args=args,result=value))
    if not prepared['usable'] or not prepared['base_verification_complete']:
        return dict(pool=[],menu=[],inputs=[],reason='unsupported_representation_or_base_scope')
    if not base:return dict(pool=[],menu=[],inputs=[],reason='no_public_base_evidence')
    spec=prepared['ir']['docstring'];arity=len(prepared['ir']['parameters'])
    models=cm.enumerate_models(base,spec,arity,CFG['max_enumerated'])
    pool,survived=cm.retain(models,base,spec,CFG['max_retained'])
    if not pool:return dict(pool=[],menu=[],inputs=[],reason='no_base_consistent_candidate',enumerated=len(models),survived=survived)
    base_keys={repr(r['args']) for r in base};inputs={}
    def add(args):
        if len(inputs)>=CFG['max_pool_inputs']:return
        args=ast.literal_eval(repr(args))
        if valid_args(task,valid,args):inputs.setdefault(repr(args),args)
    for row in base:add(row['args'])
    for row in witness_candidates(task):add(tuple(row['args']))
    extra=cm.structured_inputs(base,arity,CFG['seed']+task['task'],CFG['max_structured_proposals'])
    extra += [ast.literal_eval(r['input_repr']) for r in prepared['discovery_pool']]
    random.Random(CFG['seed']+task['task']).shuffle(extra)
    for args in extra:add(args)
    inputs=list(inputs.values())
    menu=cm.display(pool,inputs,CFG['seed']+task['task'],CFG['max_displayed'])
    scope_classes={}
    for row in menu:
        scope=row['model']['params']['component'];scope_classes.setdefault(str(scope),set()).add(cm.fingerprint(row['model'],inputs))
    put_results={repr(args):output(fn,args) for args in inputs}
    return dict(pool=pool,menu=menu,inputs=[dict(input_repr=repr(a),base=repr(a) in base_keys) for a in inputs],
                put_results=put_results,enumerated=len(models),survived=survived,at_enumeration_cap=len(models)>=CFG['max_enumerated'],
                rule_first=pool[0]['id'],ambiguous_within_scope=any(len(xs)>1 for xs in scope_classes.values()),
                scopes=sorted(scope_classes),base_calls=len(base),reason='candidates_available')


def input_class(args):
    out=[]
    for a in args:
        item=dict(kind=behavior.abstract(a))
        if type(a) is str:item.update(ascii=a.isascii(),has_upper=any(x.isupper() for x in a),has_lower=any(x.islower() for x in a))
        if type(a) in (list,tuple):
            item['duplicates']=len({repr(x) for x in a})<len(a)
            if all(type(x) is int for x in a):item.update(negative=sum(x<0 for x in a),zero=sum(x==0 for x in a),positive=sum(x>0 for x in a))
        out.append(item)
    if len(args)==2 and all(type(a) in (list,tuple) for a in args) and len(args[0])==len(args[1]) and all(type(x) is int for a in args for x in a):
        return dict(arguments=out,equal_length=True,any_negative_pair_difference=any(x<y for x,y in zip(*args)))
    return dict(arguments=out)


def explain(job,directory):
    task=job['task'];data=job['candidates'];choice=job['choice'];model_id=next((r['model_id'] for r in data['menu'] if r['id']==choice),None)
    selected=next((r for r in data['pool'] if r['id']==model_id),None)
    if selected is None:return dict(records=[],selected_model=None)
    fn,_,_=context(task);model=selected['model'];prepared=job['prepared'];blocks={b['line']:b for b in prepared['ir']['blocks']}
    discrepancies=[]
    for row in data['inputs']:
        args=ast.literal_eval(row['input_repr']);pred=templates.observe(model,args);put=data['put_results'][repr(args)]
        if pred['status']!='ok' or put['status']=='timeout':continue
        result=ast.literal_eval(put['output_repr']) if put['status']=='ok' else None
        if put['status']=='ok' and templates.holds(model,args,result) is True:continue
        discrepancies.append((row,args,pred,put))
    discrepancies.sort(key=lambda r:(r[0]['base'],len(r[0]['input_repr']),r[0]['input_repr']))
    records=[]
    for row,args,pred,put in discrepancies[:3]:
        replay=behavior.replay(task['put'],task['entry'],args,max_events=20000,timeout=2)
        observed=[]
        for event in replay['events']:
            b=blocks.get(event['location'])
            if b and b['kind'] in ('CASE','RETURN','STATE_WRITE'):
                observed.append(dict(block=b['id'],kind=b['kind'],source=b['text'],state=event['state']))
        # Last observed occurrences retain the state near the effect; no universal guard implication.
        unique={}
        for item in reversed(observed):unique.setdefault(item['block'],item)
        source=list(reversed(list(unique.values())[:8]))
        fault_matches=[]
        for f in templates.alternatives(model,6):
            alternative=templates.observe(f['model'],args)
            if put['status']=='ok':
                value=ast.literal_eval(put['output_repr']);component=model['params']['component']
                try:actual=value if component is None else value[component]
                except (TypeError,IndexError):continue
                match=alternative['status']=='ok' and type(actual) is type(alternative['value']) and actual==alternative['value']
            else:match=alternative['status']==put['status']
            if match:fault_matches.append(dict(id=f['id'],description=f['description']))
        records.append(dict(input_repr=repr(args),input_class=input_class(args),requirement=model,
            predicted_value=pred['value'],actual_put=put,observed_source=source,fault_matches_on_this_input=fault_matches,
            trace_status=replay['status'],scope='bounded observed evidence; fault match is not unique causal proof',
            guard_scope='guard sites/states observed; no uninstrumented predicate implication assumed'))
    return dict(records=records,selected_model=model_id)


def audit(job,directory):
    task=job['task'];data=job['candidates'];canon=tracer.load_module(job['canon'])[task['entry']]
    contract=tracer.load_module(job['contract'])[task['entry']]
    native={};valid_inputs=[];invalid=0;unresolved=0
    for row in data['inputs']:
        args=ast.literal_eval(row['input_repr']);status,_=tracer.call(contract,(args,{}),T=1)
        if status!='ok':
            invalid+=1;unresolved+=status=='timeout';continue
        status,value=tracer.call(canon,(args,{}),T=2)
        if status!='ok':unresolved+=1;continue
        valid_inputs.append((args,value));native[repr(args)]=value
    stats={}
    for row in data['pool']:
        checks=[templates.holds(row['model'],args,value) for args,value in valid_inputs]
        stats[row['id']]=dict(scope_component=row['model']['params']['component'],checked=len(checks),
            matches=sum(x is True for x in checks),mismatches=sum(x is False for x in checks),unknown=sum(x is None for x in checks),
            sampled_consistent=bool(checks) and all(x is True for x in checks) and unresolved==0)
    menu={r['id']:r['model_id'] for r in data['menu']};chosen=menu.get(job['choice'])
    def consistent(mid):return bool(mid in stats and stats[mid]['sampled_consistent'])
    reports=[]
    if chosen:
        model=next(r['model'] for r in data['pool'] if r['id']==chosen)
        for args,canonical_value in valid_inputs:
            p=data['put_results'][repr(args)]
            if p['status']=='timeout':continue
            pout=ast.literal_eval(p['output_repr']) if p['status']=='ok' else None
            predicted=templates.observe(model,args)
            if predicted['status']!='ok':continue
            violation=p['status']!='ok' or templates.holds(model,args,pout) is False
            if not violation:continue
            correct=templates.holds(model,args,canonical_value)
            reports.append(dict(input_repr=repr(args),confirmed=correct is True,false_alarm=correct is False,unknown=correct is None))
    return dict(task=task['task'],pool_size=len(data['pool']),displayed=len(menu),models=stats,
        pool_has_sampled_consistent=any(s['sampled_consistent'] for s in stats.values()),
        display_has_sampled_consistent=any(consistent(mid) for mid in menu.values()),
        chosen_model=chosen,chosen_sampled_consistent=consistent(chosen),rule_sampled_consistent=consistent(data.get('rule_first')),
        uniform_expected_consistency=sum(consistent(mid) for mid in menu.values())/len(menu) if menu else 0,
        ambiguous_within_scope=data.get('ambiguous_within_scope',False),valid_audit_inputs=len(valid_inputs),
        invalid_inputs=invalid,unresolved_inputs=unresolved,candidate_reports=reports,
        partial_requirement=bool(chosen and stats[chosen]['scope_component'] is not None))


def main():
    from .v4_evaluation import guard_alarm
    guard_alarm();job=json.loads(Path(sys.argv[1]).read_text())
    try:result={'candidates':candidates,'explain':explain,'audit':audit}[job['mode']](job,Path(sys.argv[1]).parent)
    except BaseException as exc:result=dict(worker_error=type(exc).__name__+': '+str(exc)[:250])
    atomic_json(Path(sys.argv[2]),result)
if __name__=='__main__':main()
