"""Library CFG/DFG + observed base input partitions. Never reads canonical code."""
from __future__ import annotations

import ast
import copy
import math

import networkx as nx
from python_graphs import program_graph, program_graph_dataclasses as pg


def shapes(value):
    found = set()
    if type(value) in (int,float):
        found.add('negative' if value<0 else 'zero' if value==0 else 'positive')
        if type(value)==int:
            found.add('odd' if value%2 else 'even')
    if isinstance(value,(str,list,tuple,dict,set)):
        found.add('empty' if len(value)==0 else 'singleton' if len(value)==1 else 'multiple')
    if isinstance(value,(list,tuple)):
        found.add('duplicates' if len({repr(v) for v in value})<len(value) else 'distinct')
    if isinstance(value,str):
        found.add('ascii' if value.isascii() else 'nonascii')
        found.add('whitespace' if any(c.isspace() for c in value) else 'no_whitespace')
    return found


def observations(base):
    values={}
    for call in base.get('calls',[]):
        for name,literal in call.get('bound',{}).items():
            try:
                value=ast.literal_eval(literal)
            except (ValueError,SyntaxError):
                continue
            values.setdefault(name,[]).append(value)
    return values


def parameter_expr(node,values):
    if isinstance(node,ast.Name) and node.id in values:
        return values[node.id]
    if (isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='len'
        and len(node.args)==1 and isinstance(node.args[0],ast.Name)):
        return [len(v) for v in values.get(node.args[0].id,[]) if hasattr(v,'__len__')]
    return []


def analyze_program(program):
    source, base, pid = program['code'],program['base'],program['id']
    tree=ast.parse(source)
    augmented_reads={(n.target.id,n.target.lineno,n.target.col_offset) for n in ast.walk(tree)
                     if isinstance(n,ast.AugAssign) and isinstance(n.target,ast.Name)}
    lines=set(base.get('coverage',{}).get('lines',[]))
    arcs={tuple(a) for a in base.get('coverage',{}).get('arcs',[])}
    values=observations(base)
    cards, covered, cfg, dfg = [],[],[],[]

    def emit(kind,text,is_missing,**evidence):
        record=dict(kind=kind,put_id=pid,text=text,evidence=evidence)
        (cards if is_missing else covered).append(record)

    for name,observed in sorted(values.items()):
        categories=set().union(*(shapes(v) for v in observed))
        universe=set()
        if any(type(v) in (int,float) for v in observed):
            universe|={'negative','zero','positive'}
        if any(type(v)==int for v in observed):
            universe|={'odd','even'}
        if any(isinstance(v,(str,list,tuple,dict,set)) for v in observed):
            universe|={'empty','singleton','multiple'}
        if any(isinstance(v,(list,tuple)) for v in observed):
            universe|={'duplicates','distinct'}
        if any(isinstance(v,str) for v in observed):
            universe|={'ascii','nonascii','whitespace','no_whitespace'}
        missing=sorted(universe-categories)
        if missing:
            emit('EQUIVALENCE',f'PUT {pid}, parameter {name}: base inputs never exercise classes {missing}; '
                 f'observed classes are {sorted(categories)}. Choose only classes allowed by the specification.',
                 True,parameter=name,missing=missing,observed=sorted(categories))
        emit('EQUIVALENCE',f'PUT {pid}, parameter {name}: base inputs exercise classes {sorted(categories)}.',
             False,parameter=name,observed=sorted(categories))
    for node in ast.walk(tree):
        if not isinstance(node,ast.Compare):
            continue
        operands=[node.left]+node.comparators
        for left,op,right in zip(operands,node.ops,operands[1:]):
            for expression,constant in ((left,right),(right,left)):
                try:
                    value=ast.literal_eval(constant)
                except (ValueError,TypeError):
                    continue
                if type(value) not in (int,float) or not math.isfinite(value):
                    continue
                seen=parameter_expr(expression,values)
                if not seen:
                    continue
                equality=any(type(x) in (int,float) and x==value for x in seen)
                emit('BOUNDARY',f'PUT {pid}, line {node.lineno}: comparison `{ast.unparse(node)}`. '
                     f'Equality of `{ast.unparse(expression)}` to {value!r} is '
                     f'{"observed" if equality else "absent"} in base inputs; exercise equality and its '
                     f'nearest valid values on both sides. Preserve input-domain constraints.',not equality,
                     line=node.lineno,expression=ast.unparse(expression),constant=value,equality_seen=equality)
    graph_error=None
    try:
        graph=program_graph.get_program_graph(source)
        flow=nx.DiGraph()
        for edge in graph.edges:
            if edge.type not in (pg.EdgeType.CFG_NEXT,pg.EdgeType.LAST_WRITE):
                continue
            left,right=graph.nodes[edge.id1].ast_node,graph.nodes[edge.id2].ast_node
            a,b=getattr(left,'lineno',None),getattr(right,'lineno',None)
            if a is None or b is None:
                continue
            if edge.type==pg.EdgeType.CFG_NEXT and a!=b:
                flow.add_edge(a,b)
            elif (edge.type==pg.EdgeType.LAST_WRITE and isinstance(getattr(left,'id',None),str)
                  and (type(getattr(left,'ctx',None)).__name__=='Load' or
                       (left.id,a,getattr(left,'col_offset',None)) in augmented_reads)):
                # python_graphs LAST_WRITE points from access to previous write.
                dfg.append(dict(name=left.id,define=b,use=a,endpoint_uncovered=b not in lines or a not in lines))
        for a,b in sorted(flow.edges):
            missing=(a,b) not in arcs
            cfg.append(dict(source=a,target=b,observed=(a,b) in arcs))
            if flow.out_degree(a)>1 or a not in lines or b not in lines:
                emit('CFG',f'PUT {pid}: static CFG edge {a} -> {b} '
                     f'{"does not appear" if missing else "appears"} in base coverage.py arcs. '
                     'Try a valid input following this edge; static feasibility is not established.',missing,
                     source=a,target=b,source_covered=a in lines,target_covered=b in lines)
        for pair in sorted({(p['name'],p['define'],p['use'],p['endpoint_uncovered']) for p in dfg}):
            name,define,use,missing=pair
            if define==use:
                continue
            emit('DEF_USE',f'PUT {pid}: possible def-use flow `{name}` from definition line {define} to use line {use}. '
                 f'{"At least one endpoint is not executed by base tests" if missing else "Both endpoints execute; pair coverage is unknown"}. '
                 'Exercise a path where this definition reaches that use without an intervening redefinition. '
                 'This is a static may-flow, not a proven feasible path.',missing,
                 variable=name,define=define,use=use,endpoint_uncovered=missing)
    except Exception as exc:
        graph_error=type(exc).__name__
    return dict(put_id=pid,cards=cards,covered_cards=covered,cfg=cfg,def_use=dfg,
                graph_error=graph_error,base_covered_lines=sorted(lines),base_arcs=sorted(arcs))


def contrastive_cards(programs):
    """Cross-PUT predicates: evidence of syntax disagreement, not claimed bugs."""
    groups={}
    for program in programs:
        tree=ast.parse(program['code'])
        for fn in [n for n in tree.body if isinstance(n,ast.FunctionDef)]:
            names={a.arg:f'arg{i}' for i,a in enumerate(fn.args.posonlyargs+fn.args.args)}

            class Rename(ast.NodeTransformer):
                def visit_Name(self,node):
                    node.id=names.get(node.id,node.id)
                    return node

            for node in ast.walk(fn):
                if not isinstance(node,ast.Compare) or len(node.ops)!=1:
                    continue
                normalized=Rename().visit(copy.deepcopy(node))
                if not any(isinstance(n,ast.Name) and n.id in names.values() for n in ast.walk(normalized)):
                    continue
                key=(ast.dump(normalized.left),ast.dump(normalized.comparators[0]))
                groups.setdefault(key,[]).append(dict(put_id=program['id'],line=node.lineno,
                    operator=type(node.ops[0]).__name__,expression=ast.unparse(node)))
    cards=[]
    for group in groups.values():
        if len({p['operator'] for p in group})<2 or len({p['put_id'] for p in group})<2:
            continue
        records=sorted(group,key=lambda p:(p['put_id'],p['line']))
        cards.append(dict(kind='CONTRASTIVE',put_id=None,evidence=dict(predicates=records),
            text='Base-passing PUTs use different comparison operators for corresponding input expressions: '
                 + '; '.join(f"PUT {r['put_id']} line {r['line']}: `{r['expression']}`" for r in records[:6])
                 + '. Test equality and both sides of this relation within the valid domain. These syntactic '
                 'differences may be equivalent algorithms; they are not evidence that any PUT is wrong.'))
    return cards


def pick_balanced(cards,limit=4):
    chosen=[]
    for kind in ('BOUNDARY','EQUIVALENCE','CFG','DEF_USE','CONTRASTIVE'):
        match=next((c for c in cards if c['kind']==kind),None)
        if match and len(chosen)<limit:
            chosen.append(match)
    for card in cards:
        if len(chosen)==limit:
            break
        if card not in chosen:
            chosen.append(card)
    return [dict(c,id=f"c{i}") for i,c in enumerate(chosen)]


def analyze_task(cohort_task):
    passing=[p for p in cohort_task['programs'] if p['base']['status']=='pass']
    analyses=[analyze_program(p) for p in passing]
    missing=[c for a in analyses for c in a['cards']]
    covered=[c for a in analyses for c in a['covered_cards']]
    classical=pick_balanced(missing)
    # If no endpoint is uncovered, expose a truthful static def-use obligation
    # rather than inventing pair coverage. Its evidence says coverage is unknown.
    if not any(c['kind']=='DEF_USE' for c in classical):
        fallback=next((c for c in covered if c['kind']=='DEF_USE'),None)
        if fallback:
            classical=pick_balanced(missing+[fallback])
    contrast=contrastive_cards(passing)
    alternative=pick_balanced(contrast+missing)
    if contrast:
        alternative=[dict(contrast[0],id='c0')]+[dict(c,id=f'c{i+1}') for i,c in enumerate(classical[:3])]
    return dict(task_id=cohort_task['task_id'],analyses=analyses,classical=classical,
                contrastive=alternative,placebo=pick_balanced(covered,limit=len(classical)),
                contrastive_available=bool(contrast),all_missing_cards=len(missing))
