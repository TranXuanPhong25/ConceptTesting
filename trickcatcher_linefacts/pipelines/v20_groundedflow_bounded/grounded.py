"""Pure, bounded multiplicity evidence. No symbolic execution or trusted inferred specs."""
import ast
import builtins
import collections
import copy
import hashlib

CALLS={'list','set','sorted','filter','len'}
ALLOWED={ast.Module,ast.FunctionDef,ast.arguments,ast.arg,ast.Assign,ast.Return,ast.Expr,
         ast.Name,ast.Load,ast.Store,ast.Constant,ast.List,ast.Tuple,ast.Set,ast.Call,ast.keyword,
         ast.Lambda,ast.BinOp,ast.UnaryOp,ast.Compare,
         ast.Add,ast.Sub,ast.Mult,ast.Mod,ast.USub,ast.UAdd,ast.Not,
         ast.Eq,ast.NotEq,ast.Lt,ast.LtE,ast.Gt,ast.GtE}
RESERVED=CALLS|{'__gf_before','__gf_after'}


def node_id(n):return f'{type(n).__name__}:{n.lineno}:{n.col_offset}:{n.end_lineno}:{n.end_col_offset}'


def checked_input(args):
    """Must precede repr/JSON transport: reject graph topology we cannot serialize faithfully."""
    if type(args) is not tuple or len(args)>4:raise ValueError('positional_tuple_required')
    active=set();mutable=set();count=0
    def visit(v):
        nonlocal count
        count+=1
        if count>512:raise ValueError('input_size')
        if type(v) in (list,tuple):
            if id(v) in active:raise ValueError('input_cycle')
            if type(v) is list:
                if id(v) in mutable:raise ValueError('shared_mutable_input')
                mutable.add(id(v))
            active.add(id(v))
            if len(v)>64:raise ValueError('sequence_size')
            for x in v:visit(x)
            active.remove(id(v))
        elif type(v) not in (int,str,bool,type(None)):raise ValueError('input_type')
        elif type(v) is int and abs(v)>1000000:raise ValueError('integer_size')
        elif type(v) is str and len(v)>256:raise ValueError('string_size')
    visit(args)
    for a in args:
        if type(a) in (list,tuple) and any(type(x) not in (int,str) for x in a):raise ValueError('flat_immutable_elements_required')
    return args


def snapshot(v,depth=0):
    if depth>8:return {'type':'unknown','reason':'depth'}
    t=type(v)
    if t in (type(None),bool,int,str):
        if t is str and len(v)>4096:return {'type':'unknown','reason':'oversize'}
        if t is int and v.bit_length()>4096:return {'type':'unknown','reason':'integer_size'}
        return {'type':t.__name__,'value':v}
    if t in (list,tuple,set,frozenset):
        if len(v)>256:return {'type':'unknown','reason':'oversize'}
        items=[snapshot(x,depth+1) for x in v]
        if t in (set,frozenset):items.sort(key=repr)
        return {'type':t.__name__,'items':items}
    # Do not iterate/consume filter objects to log them.
    return {'type':'unknown','reason':t.__name__}


def _names(n,bound=()):
    if isinstance(n,ast.Lambda):return _names(n.body,set(bound)|{a.arg for a in n.args.args})
    if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Load):return {n.id}-set(bound)
    return set().union(*(_names(x,bound) for x in ast.iter_child_nodes(n))) if list(ast.iter_child_nodes(n)) else set()


def scoped_nodes(node,bound=frozenset()):
    yield node,bound
    if isinstance(node,ast.Lambda):
        yield from scoped_nodes(node.body,bound|{a.arg for a in node.args.args})
    else:
        for child in ast.iter_child_nodes(node):yield from scoped_nodes(child,bound)


def multiplicity_sources(node,definitions,visited=frozenset()):
    # Only explicit value-preserving collection transports, not key/control/count expressions.
    if isinstance(node,ast.Name) and node.id in definitions:
        if node.id in visited:return set()
        return multiplicity_sources(definitions[node.id],definitions,visited|{node.id})
    if isinstance(node,ast.Call) and isinstance(node.func,ast.Name):
        name=node.func.id
        if name in ('set','list','sorted') and node.args:
            own={node_id(node)} if name=='set' else set()
            return own|multiplicity_sources(node.args[0],definitions,visited)
        if name=='filter' and len(node.args)==2:return multiplicity_sources(node.args[1],definitions,visited)
    if isinstance(node,ast.BinOp) and isinstance(node.op,ast.Sub):
        return multiplicity_sources(node.left,definitions,visited)  # Set RHS supplies membership only.
    return set()


def analyze(source,entry):
    reasons=[];nodes=[];edges=[]
    try:tree=ast.parse(source)
    except SyntaxError:return dict(supported=False,reasons=['syntax'],nodes=[],edges=[])
    module=[n for n in tree.body if not (isinstance(n,ast.Expr) and isinstance(n.value,ast.Constant) and type(n.value.value) is str)]
    if len(module)!=1 or not isinstance(module[0],ast.FunctionDef) or module[0].name!=entry:
        return dict(supported=False,reasons=['single_function_module_required'],nodes=[],edges=[])
    fn=module[0]
    if fn.name in RESERVED or fn.name.startswith('_'):reasons.append('shadowed_or_private_entry')
    if sum(1 for _ in ast.walk(fn))>512:reasons.append('ast_size')
    if fn.decorator_list or fn.returns or fn.type_comment or fn.args.defaults or fn.args.kw_defaults or fn.args.vararg or fn.args.kwarg or fn.args.kwonlyargs or fn.args.posonlyargs:
        reasons.append('function_signature')
    parameters=[a.arg for a in fn.args.args]
    if any(a.annotation for a in fn.args.args):reasons.append('function_annotations')
    body=[n for n in fn.body if not (isinstance(n,ast.Expr) and isinstance(n.value,ast.Constant) and type(n.value.value) is str)]
    if not body or not isinstance(body[-1],ast.Return) or any(not isinstance(n,ast.Assign) for n in body[:-1]):reasons.append('straight_line_assignments_final_return_required')
    known=set(parameters);definitions={};definition_exprs={};operations=[]
    parameter_ids={a.arg:node_id(a) for a in fn.args.args}
    nodes.extend(dict(id=uid,kind='Parameter',source=name) for name,uid in parameter_ids.items())
    for n in ast.walk(tree):
        if isinstance(n,ast.Constant) and (type(n.value) not in (int,str,bool,type(None)) or (type(n.value) is int and abs(n.value)>1000000) or (type(n.value) is str and len(n.value)>4096)):
            reasons.append('unsupported_or_oversize_constant')
        if type(n) not in ALLOWED:reasons.append('unsupported_ast:'+type(n).__name__)
        if isinstance(n,ast.FunctionDef) and n is not fn:reasons.append('nested_function')
        if isinstance(n,ast.Name) and n.id.startswith('_'):reasons.append('private_name')
        if isinstance(n,ast.arg) and (n.arg in RESERVED or n.arg.startswith('_')):reasons.append('shadowed_or_private_binder')
        if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Store) and n.id in RESERVED:reasons.append('shadowed_builtin')
        if isinstance(n,ast.Call):
            if not isinstance(n.func,ast.Name) or n.func.id not in CALLS:reasons.append('unresolved_call')
            elif n.func.id=='set':
                if len(n.args)!=1 or n.keywords:reasons.append('set_arity')
                operations.append(dict(id=node_id(n),operation='DEDUP_SET',span=[n.lineno,n.col_offset,n.end_lineno,n.end_col_offset],expression=ast.unparse(n)))
        if isinstance(n,ast.Lambda):
            if n.args.defaults or n.args.kw_defaults or n.args.vararg or n.args.kwarg or n.args.posonlyargs or n.args.kwonlyargs or len(n.args.args)!=1:reasons.append('lambda_signature')
            if any(isinstance(x,ast.Call) and isinstance(x.func,ast.Name) and x.func.id=='set' for x in ast.walk(n.body)):reasons.append('set_in_lambda')
    if set(parameters)&RESERVED:reasons.append('shadowed_builtin')
    for statement in body:
        value=getattr(statement,'value',None)
        if value is None:reasons.append('missing_value');continue
        unknown=_names(value)-known-CALLS
        if unknown:reasons.append('unbound_name:'+','.join(sorted(unknown)))
        for x,bound in scoped_nodes(value):
            if hasattr(x,'lineno'):
                uid=node_id(x);nodes.append(dict(id=uid,kind=type(x).__name__,source=ast.unparse(x)))
                for child in ast.iter_child_nodes(x):
                    if hasattr(child,'lineno'):edges.append(dict(source=node_id(child),target=uid,kind='expression_input'))
                if isinstance(x,ast.Name) and x.id not in bound and x.id in parameter_ids:edges.append(dict(source=parameter_ids[x.id],target=uid,kind='parameter_use'))
                if isinstance(x,ast.Name) and x.id not in bound and x.id in definitions:edges.append(dict(source=definitions[x.id],target=uid,kind='definition_use'))
        if isinstance(statement,ast.Assign):
            if len(statement.targets)!=1 or not isinstance(statement.targets[0],ast.Name):reasons.append('local_name_assignment_required');continue
            target=statement.targets[0].id
            if target in known:reasons.append('reassignment_or_argument_write')
            definitions[target]=node_id(value);definition_exprs[target]=value;known.add(target)
    if reasons:
        return dict(supported=False,reasons=sorted(set(reasons)),entry=entry,parameters=parameters,nodes=nodes,edges=edges,operations=operations,return_slice=[])
    if not body or not isinstance(body[-1],ast.Return) or body[-1].value is None:return_slice=set()
    else:
        return_id=node_id(body[-1].value);reverse=collections.defaultdict(list)
        for edge in edges:reverse[edge['target']].append(edge['source'])
        return_slice=set();todo=[return_id]
        while todo:
            x=todo.pop()
            if x not in return_slice:return_slice.add(x);todo.extend(reverse[x])
    transports=multiplicity_sources(body[-1].value,definition_exprs) if body and isinstance(body[-1],ast.Return) and body[-1].value is not None else set()
    for operation in operations:
        operation['multiplicity_transport_to_return']=operation['id'] in transports
        operation['in_return_slice']=operation['id'] in return_slice
        ancestors=set();todo=[operation['id']];reverse=collections.defaultdict(list)
        for edge in edges:reverse[edge['target']].append(edge['source'])
        while todo:
            x=todo.pop()
            if x not in ancestors:ancestors.add(x);todo.extend(reverse[x])
        operation['input_arguments']=[i for i,name in enumerate(parameters) if parameter_ids[name] in ancestors]
    return dict(supported=not reasons,reasons=sorted(set(reasons)),entry=entry,parameters=parameters,
                source_hash=hashlib.sha256(source.encode()).hexdigest(),nodes=nodes,edges=edges,
                operations=operations,return_slice=sorted(return_slice),scope='pure native straight-line/conditional-expression; no symbolic CFG or causality proof')


class Probe:
    def __init__(self,args=()):self.events=[];self.pending=collections.defaultdict(list);self.sequence=0;self.args=args
    def before(self,uid,value):
        self.sequence+=1;occurrence=self.sequence
        snap=snapshot(value);self.pending[uid].append((occurrence,snap,[i for i,a in enumerate(self.args) if type(a) in (list,tuple,str) and value is a]))
        self.events.append(dict(node_id=uid,occurrence=occurrence,phase='before',value=snap))
        return value
    def after(self,uid,value):
        occurrence,before,argument_identity=self.pending[uid].pop();after=snapshot(value)
        loss=None
        if before['type'] in ('list','tuple','str') and after['type']=='set':
            count=len(before.get('items',before.get('value',[])));loss=count>len(after['items'])
        losses=[]
        if loss:
            items=before.get('items',[{'type':'str','value':x} for x in before.get('value','')])
            if all(x['type'] in ('int','str') for x in items+after['items']):
                old=collections.Counter((x['type'],x['value']) for x in items)
                new=collections.Counter((x['type'],x['value']) for x in after['items'])
                losses=[dict(value_type=k[0],value=k[1],before_count=n,after_count=new[k]) for k,n in old.items() if n>new[k]]
        self.events.append(dict(node_id=uid,occurrence=occurrence,phase='committed',value=after,local_count_loss=loss,losses=losses,argument_identity=argument_identity))
        return value


class Instrument(ast.NodeTransformer):
    def visit_Call(self,node):
        uid=node_id(node);is_set=isinstance(node.func,ast.Name) and node.func.id=='set'
        node=self.generic_visit(node)
        if not is_set:return node
        node.args[0]=ast.copy_location(ast.Call(func=ast.Name(id='__gf_before',ctx=ast.Load()),args=[ast.Constant(uid),node.args[0]],keywords=[]),node.args[0])
        return ast.copy_location(ast.Call(func=ast.Name(id='__gf_after',ctx=ast.Load()),args=[ast.Constant(uid),node],keywords=[]),node)


def execute(source,entry,args,instrument=False):
    """Worker-only. Coordinator never calls this function."""
    checked_input(args);analysis=analyze(source,entry)
    if not analysis['supported']:return dict(status='unsupported',reasons=analysis['reasons'])
    args=copy.deepcopy(args);before=snapshot(args);probe=Probe(args);tree=ast.parse(source)
    if instrument:tree=ast.fix_missing_locations(Instrument().visit(tree))
    ns={'__builtins__':{name:getattr(builtins,name) for name in CALLS},'__gf_before':probe.before,'__gf_after':probe.after}
    exec(compile(tree,'<grounded-native>','exec'),ns)
    result=None
    try:result=ns[entry](*args);status='ok'
    except Exception as exc:status=type(exc).__name__
    return dict(status=status,output=snapshot(result) if status=='ok' else None,input_before=before,input_after=snapshot(args),
                output_aliases=[i for i,a in enumerate(args) if type(a) in (list,tuple) and result is a] if status=='ok' else [],events=probe.events)


def eligible(value,kind):
    if kind=='all':return True
    if kind=='length_even':return type(value) is str and len(value)%2==0
    if kind=='positive':return type(value) is int and value>0
    raise ValueError('eligibility_unsupported')


def validate_requirement(r,arity):
    if type(r) is not dict:return 'requirement_shape'
    if r.get('mode') not in ('preserve','unique') or r.get('eligibility') not in ('all','length_even','positive'):return 'unsupported_relation'
    if r.get('element_type') not in ('int','str') or type(r.get('argument')) is not int or not 0<=r['argument']<arity:return 'requirement_type_or_argument'
    if r.get('review_status') not in ('fixture_spec','reviewed_candidate','unreviewed'):return 'review_status'
    text=r.get('spec');quote=r.get('quote');span=r.get('span')
    if type(text) is not str or type(quote) is not str or not quote or type(span) is not list or len(span)!=2 or any(type(x) is not int for x in span):return 'quote_shape'
    if not 0<=span[0]<span[1]<=len(text) or text[span[0]:span[1]]!=quote:return 'quote_span'
    if type(r.get('provenance')) is not str or not r['provenance']:return 'requirement_provenance'
    return None


def requirement_check(requirement,args,output):
    if requirement.get('mode') not in ('preserve','unique'):return dict(domain=None,holds=None,reason='requirement_mode')
    if requirement.get('eligibility') not in ('all','length_even','positive'):return dict(domain=None,holds=None,reason='eligibility_unsupported')
    xs=args[requirement.get('argument',0)]
    typ={'int':int,'str':str}.get(requirement.get('element_type'))
    if type(xs) not in (list,tuple) or typ is None or any(type(x) is not typ for x in xs):return dict(domain=False,holds=None,reason='explicit_fixture_domain')
    wanted=collections.Counter(x for x in xs if eligible(x,requirement['eligibility']))
    if output.get('type') not in ('list','tuple'):return dict(domain=True,holds=None,reason='partial_output_scope')
    if any(x.get('type')!=typ.__name__ for x in output['items']):return dict(domain=True,holds=None,reason='output_element_type')
    actual=collections.Counter(x['value'] for x in output['items']);violations=[]
    for value,count in wanted.items():
        expected=count if requirement['mode']=='preserve' else 1
        if actual[value]!=expected:violations.append(dict(value=value,expected_count=expected,actual_count=actual[value]))
    trigger=any(count>1 for count in wanted.values())
    return dict(domain=True,holds=not violations,violations=violations,trigger=trigger,relation='eligible occurrence counts only; no invented full output')


def evidence(source,entry,args,requirement):
    """Worker-only pairing and partial-relation audit; never labels a confirmed bug."""
    checked_input(args);ir=analyze(source,entry)
    requirement_error=validate_requirement(requirement,len(args))
    if requirement_error:return dict(supported=False,reasons=[requirement_error],complete_evidence=False,confirmed_bug=None)
    if not ir['supported']:return dict(supported=False,reasons=ir['reasons'],complete_evidence=False,confirmed_bug=None)
    native=execute(source,entry,args);observed=execute(source,entry,args,True)
    keys=('status','output','input_before','input_after','output_aliases')
    native_checked=all(native[k]==observed[k] for k in keys) and native['input_before']==native['input_after']
    review=requirement.get('review_status','unreviewed');scope=requirement.get('provenance','unspecified')
    relation=requirement_check(requirement,args,native['output']) if native['status']=='ok' else dict(domain=None,holds=None,reason='native_exception')
    in_slice={x['id'] for x in ir['operations'] if x['in_return_slice'] and x['multiplicity_transport_to_return'] and requirement.get('argument',0) in x['input_arguments']}
    violations={v['value']:(v['expected_count'],v['actual_count']) for v in relation.get('violations',[])}
    active=[]
    for event in observed['events']:
        if event['phase']!='committed' or event['node_id'] not in in_slice or requirement['argument'] not in event['argument_identity'] or requirement['mode']!='preserve':continue
        matches=[loss for loss in event['losses'] if loss['value'] in violations and eligible(loss['value'],requirement['eligibility']) and violations[loss['value']]==(loss['before_count'],loss['after_count'])]
        if matches:active.append(dict(event,matched_eligible_losses=matches))
    # Association only: a live loss + final discrepancy is not unique causal localization.
    complete=native_checked and relation.get('domain') is True and relation.get('trigger') is True and relation.get('holds') is False and bool(active)
    return dict(supported=True,ir=ir,native=native,observed=observed,native_checked=native_checked,
                requirement=requirement,requirement_review_status=review,requirement_provenance=scope,relation=relation,
                candidate_output_violation=relation.get('holds') is False,complete_evidence=complete,
                grounded_reviewed=complete and review in ('fixture_spec','reviewed_candidate'),confirmed_bug=None,
                bindings=[dict(operation=r['node_id'],occurrence=r['occurrence'],requirement='eligible_multiplicity',matched_losses=r['matched_eligible_losses'],kind='observed_required_value_loss_transported_to_return') for r in active],
                hypothesis=dict(kind='observed_multiplicity_loss',origin='implementation_operation',competing_operation_ids=sorted({x['node_id'] for x in active}),not_a_repair=True),
                requirement_source_hash=hashlib.sha256(requirement['spec'].encode()).hexdigest(),
                trigger=dict(kind='eligible_duplicate',argument=requirement.get('argument',0),eligibility=requirement.get('eligibility')),
                limitations=['bounded concrete evidence','association, not unique cause','candidate requirement is not an independent oracle','static may-dependencies alone do not certify selected-expression provenance','complete loss evidence requires input identity and transparent collection transport; derived inputs abstain'])
