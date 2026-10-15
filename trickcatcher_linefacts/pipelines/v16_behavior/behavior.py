"""Source-grounded control/state artifacts. Observed FSMs are under-approximations.

No symbolic execution/completeness claim. All target execution belongs in a sandbox worker.
"""
from __future__ import annotations
import ast
import copy
import contextlib
import io
import json
import sys
from . import tracer

BUILTINS = {'len','range','enumerate','zip','min','max','sum','abs','all','any','sorted',
            'reversed','list','tuple','set','dict','str','int','bool','filter','map'}
METHODS = {'append','extend','pop','insert','remove','clear','sort','reverse','count','index',
           'lower','upper','swapcase','replace','join','split','strip','startswith','endswith',
           'isalpha','isdigit','isupper','islower','add','discard'}
MUTATING = {'append','extend','pop','insert','remove','clear','sort','reverse','add','discard'}

def uid(node):
    return f'N{node.lineno}_{node.col_offset}_{type(node).__name__}'

def function(source, entry):
    return next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name==entry)

def docstmt(n):
    return isinstance(n,ast.Expr) and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str)

def expr(n):
    return ast.unparse(n)

def rootname(n):
    while isinstance(n,(ast.Attribute,ast.Subscript)):n=n.value
    return n.id if isinstance(n,ast.Name) else None

def local_effects(n):
    # A block's own expression, excluding nested statement bodies.
    if isinstance(n,(ast.If,ast.While)):parts=[n.test]
    elif isinstance(n,ast.For):parts=[n.target,n.iter]
    else:parts=[n]
    nodes=[v for part in parts for v in ast.walk(part)]
    reads=sorted({v.id for v in nodes if isinstance(v,ast.Name) and isinstance(v.ctx,ast.Load)})
    writes={v.id for v in nodes if isinstance(v,ast.Name) and isinstance(v.ctx,ast.Store)}
    heap=set()
    for v in nodes:
        if isinstance(v,ast.Subscript) and isinstance(v.ctx,ast.Store):heap.add(rootname(v))
        if isinstance(v,ast.Call) and isinstance(v.func,ast.Attribute) and v.func.attr in MUTATING:
            heap.add(rootname(v.func.value))
    return dict(reads=reads,writes=sorted(writes),heap_writes=sorted(x for x in heap if x))

def build(source,entry):
    fn=function(source,entry);blocks=[];edges=[];opaque=[];requirements=[]
    def edge(a,b,label):edges.append(dict(source=a,target=b,label=label))
    def seq(body,successor,loop=None):
        current=successor
        for n in reversed(body):
            if docstmt(n):continue
            name=uid(n); eff=local_effects(n)
            if isinstance(n,(ast.If,ast.While)):text=f'{type(n).__name__.upper()} {expr(n.test)}'
            elif isinstance(n,ast.For):text=f'FOR {expr(n.target)} IN {expr(n.iter)}'
            else:text=expr(n)
            kind=('CASE' if isinstance(n,ast.If) else 'LOOP' if isinstance(n,(ast.For,ast.While)) else
                  'RETURN' if isinstance(n,ast.Return) else 'STATE_WRITE' if eff['heap_writes'] else 'STEP')
            blocks.append(dict(id=name,line=n.lineno,end_line=n.end_lineno,kind=kind,text=text,**eff))
            if isinstance(n,ast.If):
                edge(name,seq(n.body,current,loop),'true');edge(name,seq(n.orelse,current,loop),'false')
            elif isinstance(n,(ast.For,ast.While)):
                exit_node=seq(n.orelse,current,loop)
                edge(name,seq(n.body,name,(current,name)),'iterate/true');edge(name,exit_node,'exhausted/false')
            elif isinstance(n,ast.Return):edge(name,'EXIT','return')
            elif isinstance(n,ast.Break):edge(name,loop[0] if loop else 'UNKNOWN','break')
            elif isinstance(n,ast.Continue):edge(name,loop[1] if loop else 'UNKNOWN','continue')
            else:edge(name,current,'next')
            current=name
        return current
    start=seq(fn.body,'EXIT')
    statements=sorted(blocks,key=lambda b:(b['line'],b['id']))
    for n in ast.walk(fn):
        reason=None
        if isinstance(n,(ast.Try,ast.TryStar,ast.With,ast.Raise,ast.Yield,ast.Global,ast.Nonlocal,ast.AsyncFor)):
            reason='unsupported_control'
        if isinstance(n,ast.BinOp) and isinstance(n.op,ast.Div):reason='float_division'
        if isinstance(n,ast.Constant) and isinstance(n.value,float):reason='float_value'
        if isinstance(n,ast.Call):
            if isinstance(n.func,ast.Name) and n.func.id not in BUILTINS:reason='unknown_or_recursive_call'
            elif isinstance(n.func,ast.Attribute) and n.func.attr not in METHODS:reason='unknown_method'
            if isinstance(n.func,ast.Name) and n.func.id in {'min','max'} and len(n.args)==1 and not any(k.arg=='default' for k in n.keywords):
                requirements.append(dict(id=uid(n),line=n.lineno,kind='NONEMPTY',
                                         expression=expr(n.args[0]),operation=n.func.id,
                                         required_condition=f'len({expr(n.args[0])}) > 0',
                                         status='type_applicability_pending'))
        if isinstance(n,ast.Subscript) and not isinstance(n.slice,ast.Slice):
            requirements.append(dict(id=uid(n),line=n.lineno,kind='INDEX_VALID',expression=expr(n),
                                     required_condition=f'index valid for {expr(n.value)}',status='type_applicability_pending'))
        if reason:opaque.append(dict(line=getattr(n,'lineno',fn.lineno),reason=reason,expression=expr(n)))
    # Compression only for a fresh local list with one append and no extra effects.
    summaries=[]
    for n in ast.walk(fn):
        if not isinstance(n,ast.For):continue
        if len(n.body)!=1:continue
        b=n.body[0];guards=[]
        if isinstance(b,ast.If) and len(b.body)==1 and not b.orelse:
            guards=[expr(b.test)];b=b.body[0]
        if not (isinstance(b,ast.Expr) and isinstance(b.value,ast.Call)):continue
        call=b.value
        if not (isinstance(call.func,ast.Attribute) and call.func.attr=='append' and
                isinstance(call.func.value,ast.Name) and len(call.args)==1 and not n.orelse):continue
        target=call.func.value.id
        fresh=any(isinstance(p,ast.Assign) and p.lineno<n.lineno and isinstance(p.value,ast.List) and not p.value.elts and
                  len(p.targets)==1 and isinstance(p.targets[0],ast.Name) and p.targets[0].id==target for p in fn.body)
        if not fresh:continue
        # Keep original blocks/loop effects even when providing a compact reading aid.
        summaries.append(dict(block=uid(n),kind='FILTER_MAP' if guards else 'MAP',target=target,
                              variable=expr(n.target),collection=expr(n.iter),expression=expr(call.args[0]),
                              guards=guards,status='syntactic_pattern_only',state='append updates collection; return reads latest state'))
    return dict(schema=1,entry=entry,parameters=[a.arg for a in fn.args.posonlyargs+fn.args.args],
                docstring=ast.get_docstring(fn,clean=False) or '',blocks=statements,edges=edges,start=start,
                exit='EXIT',requirements=requirements,summaries=summaries,opaque=opaque,
                structural_supported=not opaque,proof_scope='structured source plus bounded replay; no universal proof')

def abstract(value):
    t=type(value)
    if value is None:return 'none'
    if t is bool:return 'bool:'+str(value)
    if t is int:return 'int:'+('negative' if value<0 else 'zero' if value==0 else 'positive')
    if t in (list,tuple,str,set,dict):return t.__name__+':'+('empty' if not value else 'singleton' if len(value)==1 else 'many')
    return 'unknown:'+t.__name__

def freeze(value):
    if type(value) in (list,tuple):return (type(value).__name__,tuple(freeze(v) for v in value))
    if type(value) is dict:return ('dict',tuple(sorted((repr(k),freeze(v)) for k,v in value.items())))
    if type(value) is set:return ('set',tuple(sorted(repr(v) for v in value)))
    if type(value) in (type(None),bool,int,str,float):return (type(value).__name__,value)
    return ('unknown',type(value).__name__)

def replay(source,entry,args,*,max_events=20000,timeout=2):
    """Original Python semantics, with frame-local observations; preserves aliases and early returns."""
    filename='<behavior-put>';ns=tracer.load_module(source,filename=filename);fn=ns[entry]
    events=[];versions={};last={};objects={};steps=0;terminal=None
    def trace(frame,event,arg):
        nonlocal steps,terminal
        if frame.f_code.co_filename!=filename:return trace
        if event not in ('line','return','exception'):return trace
        steps+=1
        if steps>200000:raise tracer.Timeout()
        if frame.f_code.co_name!=entry:return trace
        if len(events)>=max_events:raise tracer.Timeout()
        state={};concrete={}
        for name,value in sorted(frame.f_locals.items()):
            snap=freeze(value)
            if name not in last or snap!=last[name]:versions[name]=versions.get(name,0)+1;last[name]=snap
            cell=dict(predicate=abstract(value),version=versions[name])
            if type(value) in (list,dict,set):cell['object']=objects.setdefault(id(value),'H'+str(len(objects)))
            state[name]=cell;concrete[name]=repr(value)[:1200]
        rec=dict(location=frame.f_lineno,event=event,state=state,concrete=concrete)
        if event=='return':rec['result']=repr(arg)[:1200];terminal=arg
        if event=='exception':rec['exception']=arg[0].__name__
        events.append(rec)
        return trace
    sys.settrace(trace)
    try:
        with contextlib.redirect_stdout(io.StringIO()),tracer.alarm(timeout):
            result=fn(*copy.deepcopy(args))
        status='ok';output=repr(result)
    except tracer.Timeout:status='timeout';output=None
    except BaseException as exc:status=type(exc).__name__;output=None
    finally:sys.settrace(None)
    return dict(input_repr=repr(args),status=status,output_repr=output,events=events,
                complete=status!='timeout',semantics='observed_original_python_execution')

def machine(replays):
    # Versions/object IDs are observations, not unbounded state coordinates.
    # Local predicate values are finite per fixed vocabulary. Edges are witnessed only.
    states={};edges=set()
    for run in replays:
        previous=None
        for event in run['events']:
            valuation={k:v['predicate'] for k,v in event['state'].items()}
            key=json.dumps([event['location'],event['event'],valuation],sort_keys=True)
            sid=states.setdefault(key,dict(id='S'+str(len(states)),location=event['location'],
                                          event=event['event'],predicates=valuation))['id']
            if previous is not None:edges.add((previous,sid))
            previous=sid
    return dict(kind='finite_observed_projection',under_approximation=True,states=list(states.values()),
                transitions=[dict(source=a,target=b,evidence='observed') for a,b in sorted(edges)],
                warning='Merging projections is for display/search only; composed paths need concrete replay.')

def mutants(source,entry,cap=12):
    """First-order implementation-origin hypotheses; each mutation acts on one original node."""
    original=ast.parse(source);fn=function(source,entry);candidates=[]
    for n in sorted(ast.walk(fn),key=lambda n:(getattr(n,'lineno',0),getattr(n,'col_offset',0),type(n).__name__)):
        if isinstance(n,ast.If):
            candidates.extend([(uid(n),'SKIP_THEN',None),(uid(n),'UNGUARD_THEN',None)])
            if isinstance(n.test,ast.BoolOp) and isinstance(n.test.op,ast.And):
                for i in range(len(n.test.values)):candidates.append((uid(n),'DELETE_CONJUNCT',i))
        if isinstance(n,ast.Compare) and len(n.ops)==1 and isinstance(n.ops[0],(ast.Lt,ast.LtE,ast.Gt,ast.GtE,ast.Eq,ast.NotEq)):
            candidates.append((uid(n),'RELATION_SWAP',None))
        if isinstance(n,ast.ListComp) and len(n.generators)==1 and n.generators[0].ifs:
            candidates.append((uid(n),'BYPASS_FILTER',None))
    rows=[]
    for target,op,param in candidates[:cap]:
        class Mutator(ast.NodeTransformer):
            def generic_visit(self,node):
                if hasattr(node,'lineno') and uid(node)==target:
                    if op=='SKIP_THEN':node.body=[ast.copy_location(ast.Pass(),node.body[0])]
                    elif op=='UNGUARD_THEN':return node.body
                    elif op=='DELETE_CONJUNCT':
                        values=[v for i,v in enumerate(node.test.values) if i!=param]
                        node.test=values[0] if len(values)==1 else ast.BoolOp(op=ast.And(),values=values)
                    elif op=='BYPASS_FILTER':node.generators[0].ifs=[]
                    elif op=='RELATION_SWAP':
                        swap={ast.Lt:ast.LtE,ast.LtE:ast.Lt,ast.Gt:ast.GtE,ast.GtE:ast.Gt,ast.Eq:ast.NotEq,ast.NotEq:ast.Eq}
                        node.ops=[swap[type(node.ops[0])]()] 
                    return node
                return super().generic_visit(node)
        tree=ast.fix_missing_locations(Mutator().visit(copy.deepcopy(original)))
        text=ast.unparse(tree)
        try:compile(tree,'<mutant>','exec');valid=True
        except (SyntaxError,TypeError,ValueError):valid=False
        rows.append(dict(id=f'M{len(rows)}',origin='implementation',target=target,operator=op,parameter=param,
                         source=text,syntactically_valid=valid,
                         semantic_status='unknown_until_replay; not a specification oracle'))
    return rows

def pseudocode(ir):
    lines=['# Source-mapped behavior; expressions retain Python semantics.']
    for b in ir['blocks']:
        lines.append(f"{b['id']} [L{b['line']}] {b['text']}")
        if b['heap_writes']:lines.append('  MUTATE '+', '.join(b['heap_writes'])+'; downstream reads use latest object state')
    lines+=['# Transitions']+[f"{e['source']} --{e['label']}--> {e['target']}" for e in ir['edges']]
    return '\n'.join(lines)+'\n'
