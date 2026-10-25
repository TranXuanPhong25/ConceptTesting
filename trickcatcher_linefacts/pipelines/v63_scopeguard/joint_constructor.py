"""Compositional input solving + native exact-site verification.

Supports scalar int/bool, strings and homogeneous depth-two integer sequences.
Shape bounds are search bounds, never inferred normative input constraints.
"""
import ast
import itertools
import time
import z3
from .predicates import validate,evaluate,symbolic,local_names
from .construction import replay


def profile(examples):
    def kind(values,depth=0):
        types={type(x) for x in values}
        if len(types)!=1:raise ValueError('heterogeneous_type_profile')
        t=type(values[0])
        if t in (int,bool):return {'kind':t.__name__}
        if t is str:
            observed={ord(c)for s in values for c in s};alphabet=set(observed)
            for low,high in ((48,57),(65,90),(97,122)):
                if any(low<=c<=high for c in observed):alphabet.update(range(low,high+1))
            return {'kind':'str','alphabet':sorted(alphabet or set(range(97,123))),
                    'alphabet_origin':'public_example_character_categories'if observed else 'empty_example_search_fallback'}
        if t in (list,tuple) and depth<2:
            children=[x for xs in values for x in xs]
            if not children:raise ValueError('empty_only_element_type')
            return {'kind':t.__name__,'element':kind(children,depth+1)}
        raise ValueError('unsupported_input_type')
    if not examples or any(len(x)!=len(examples[0]) for x in examples):raise ValueError('input_arity')
    return [kind([x[i] for x in examples]) for i in range(len(examples[0]))]


def solve_inputs(examples,predicate,deadline,max_candidates=64,max_queries=64):
    signature=profile(examples);validate(predicate,len(signature))
    containers=[i for i,k in enumerate(signature) if k['kind'] in ('str','list','tuple')]
    # Enumerate bounded joint shapes; limit is explicit and reported.
    shapes=itertools.product(range(0,7),repeat=len(containers))
    result=[];queries=0;unknown=0;issues=set();seen=set()
    for sizes in shapes:
        if time.monotonic()>=deadline:issues.add('deadline');break
        if queries>=max_queries or len(result)>=max_candidates:issues.add('query_or_candidate_cap');break
        shape=dict(zip(containers,sizes));variables=[];bounds=[]
        def value(k,name,length=None):
            if k['kind']=='int':
                x=z3.Int(name);bounds.extend([x>=-16,x<=16]);variables.append(x);return x
            if k['kind']=='bool':
                x=z3.Bool(name);variables.append(x);return x
            if k['kind']=='str':
                xs=[z3.Int(f'{name}_{i}') for i in range(length)]
                for x in xs:bounds.append(z3.Or(*[x==code for code in k['alphabet']]));variables.append(x)
                return xs
            if k['kind'] in ('list','tuple'):
                n=length if length is not None else 2
                return [value(k['element'],f'{name}_{i}',2 if k['element']['kind']in ('list','tuple','str') else None) for i in range(n)]
            raise ValueError('input_sort')
        try:
            args=[value(k,f'arg{i}',shape.get(i)) for i,k in enumerate(signature)]
            solver=z3.Solver();solver.set(timeout=max(1,min(100,int((deadline-time.monotonic())*1000))))
            solver.add(*bounds,symbolic(predicate,args))
            def concrete(v,k):
                if k['kind']=='int':return model.eval(v,model_completion=True).as_long()
                if k['kind']=='bool':return z3.is_true(model.eval(v,model_completion=True))
                if k['kind']=='str':return ''.join(chr(model.eval(x,model_completion=True).as_long()) for x in v)
                seq=[concrete(x,k['element']) for x in v]
                return tuple(seq) if k['kind']=='tuple' else seq
            for _ in range(4):
                if queries>=max_queries or len(result)>=max_candidates or time.monotonic()>=deadline:
                    issues.add('query_candidate_or_deadline_cap');break
                queries+=1;status=solver.check()
                if status==z3.unknown:unknown+=1;break
                if status!=z3.sat:break
                model=solver.model()
                candidate=tuple(concrete(v,k) for v,k in zip(args,signature))
                if evaluate(predicate,candidate) is not True:issues.add('symbolic_concrete_predicate_mismatch')
                else:
                    key=repr(candidate)
                    if key not in seen:seen.add(key);result.append(candidate)
                solver.add(z3.Or(*[v!=model.eval(v,model_completion=True)for v in variables]))
        except (ValueError,TypeError,z3.Z3Exception) as exc:issues.add(str(exc)[:120])
    return {'inputs':result,'queries':queries,'solver_unknown':unknown,'issues':sorted(issues),
            'domain':{'integer':[-16,16],'input_profiles':signature,'max_length':6,'nested_width':2},
            'status':'bounded_search_no_equivalence_claim'}


def verify_input(request,h,args,config,deadline):
    from .semantic_contract import admit
    # Revalidate public binding and replacement before executing any hypothesis payload.
    raw={k:h[k]for k in ('site_id','family','required_relation','observed_relation','spec_quote','trigger','priority','alternative','event_predicate')}
    checked,errors=admit(request,[raw])
    if errors or not checked or checked[0]!=h:raise ValueError('hypothesis_integrity')
    # Module initialization is outside the current function-event certificate.
    # Keep the admitted claim visible, but never invent an input-trigger witness.
    if not h['site']['scope']:
        return {'arguments':repr(args),'predicate_realized':False,'site_realized':False,
                'event_realized':False,'event_unknown':True,'stable':False,'normal':False,
                'output_sensitivity':'unknown','observations':[],'native_executions':0,
                'status':'unsupported_module_scope','bug_truth':'unknown'}
    try:input_realized=evaluate(h['trigger'],args)is True
    except (ValueError,KeyError,TypeError,IndexError,ZeroDivisionError):
        return {'arguments':repr(args),'predicate_realized':False,'site_realized':False,'event_realized':False,
                'event_unknown':True,'stable':False,'normal':False,'output_sensitivity':'unknown',
                'observations':[],'native_executions':0,'status':'unsupported_input_predicate','bug_truth':'unknown'}
    tree=ast.parse(request['source']);target=next(n for n in ast.walk(tree)if isinstance(n,ast.expr)and [n.lineno,n.col_offset,n.end_lineno,n.end_col_offset]==h['site']['span'])
    alternative={'span':h['site']['span'],'node_kind':type(target).__name__,'before':ast.unparse(target),'after':h['alternative']or ast.unparse(target)}
    observed=[];names=sorted(local_names(h['event_predicate']))
    for seed in config['repeat_seeds']:
        for _ in range(config['repeats_per_program_seed']):
            observed.append(replay(request['source'],request['entry'],args,alternative,deadline=deadline,seed=seed,
                                   observe_only=h['alternative']is None,observation_names=names))
    first=observed[0];put=first.get('put',{});alt=first.get('alternative',{})
    stable=len({repr(o)for o in observed})==1
    frame=h['site']['scope'][-1].rsplit('@',1)[0]
    events=[e for e in put.get('site_events',[])if e.get('function')==frame]
    event_realized=False
    event_unknown=any(any(program.get('capture',{}).values())for observation in observed
                      for program in (observation.get('put',{}),observation.get('alternative',{})))
    for e in events:
        values={}
        try:
            def decode(encoded):
                if 'repr'in encoded:return ast.literal_eval(encoded['repr'])
                if encoded.get('type')in ('list','tuple')and 'items'in encoded:
                    items=[decode(x)for x in encoded['items']]
                    return tuple(items)if encoded['type']=='tuple'else items
                raise ValueError('unsupported_local_capture')
            for name,encoded in e.get('locals',{}).items():
                values[name]=decode(encoded)
            if evaluate(h['event_predicate'],args,values)is True:event_realized=True
        except (ValueError,KeyError,IndexError,TypeError,ZeroDivisionError):event_unknown=True
    normal=first.get('status')=='ok' and put.get('status')=='ok'
    realized=stable and normal and bool(events)and event_realized and input_realized and not event_unknown
    sensitivity='unknown'
    if realized and h['alternative']is not None and alt.get('status')=='ok' and alt.get('site_events'):
        sensitivity=put.get('output')!=alt.get('output') and [e['value']for e in events]!=[e['value']for e in alt['site_events']]
    return {'arguments':repr(args),'predicate_realized':input_realized,'site_realized':bool(events),
            'event_realized':event_realized,'event_unknown':event_unknown,'stable':stable,'normal':normal,
            'output_sensitivity':sensitivity,'bug_truth':'unknown','observations':observed,
            'native_executions':len(observed)*(2 if h['alternative']is not None else 1)}


def construct_case(request,hypotheses,config):
    examples=[ast.literal_eval(e['arguments']) for e in request['public_examples']]
    deadline=time.monotonic()+config['max_case_seconds']
    execution_count=0;candidate_count=0;records=[];tree=ast.parse(request['source'])
    for h in hypotheses[:3]:
        try:solved=solve_inputs(examples,h['trigger'],deadline,max_candidates=max(0,64-candidate_count))
        except (ValueError,TypeError,z3.Z3Exception)as exc:
            records.append({'hypothesis':h,'construction':{'status':'unsupported_input_profile_or_predicate','issues':[str(exc)[:120]]},'runs':[]})
            continue
        runs=[]
        for args in solved['inputs']:
            variants=2 if h['alternative']is not None else 1
            needed=variants*len(config['repeat_seeds'])*config['repeats_per_program_seed']
            if candidate_count>=64 or execution_count+needed>256 or time.monotonic()>=deadline:break
            candidate_count+=1
            verified=verify_input(request,h,args,config,deadline)
            execution_count+=verified['native_executions'];runs.append(verified)
        records.append({'hypothesis':h,'construction':{k:v for k,v in solved.items() if k!='inputs'},'runs':runs})
    return {'case_id':request['case_id'],'records':records,'native_executions':execution_count,
            'candidates_tested':candidate_count,'remaining_semantic_status':'unverified','private_data_used':False}
