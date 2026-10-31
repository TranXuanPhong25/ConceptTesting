"""Bounded source-only semantic instances; no target execution or defect labels."""
import ast
import hashlib
import re
from .facts import Analysis

MAX_SOURCE = 50000


def extract(source, entry=None):
    if not isinstance(source,str) or len(source)>MAX_SOURCE:
        raise ValueError('source must be text of at most 50000 characters')
    a=Analysis(source)
    functions=[n for n in a.tree.body if isinstance(n,ast.FunctionDef) and (entry is None or n.name==entry)]
    if len(functions)!=1:raise ValueError('select exactly one top-level function with entry')
    fn=functions[0];instances=[];unknown=[]
    def owner(node):
        while node is not None:
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.Lambda)):return node
            node=a.parent.get(node)
    nodes=[n for n in a.nodes if owner(n) is fn]
    params={n.arg:n for n in [*fn.args.posonlyargs,*fn.args.args,*fn.args.kwonlyargs]}
    other_writes=[]
    def collect_bindings(node):
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
            other_writes.append((node.name,node));return
        if isinstance(node,ast.Lambda):return
        if isinstance(node,(ast.Import,ast.ImportFrom)):
            for alias in node.names:
                other_writes.append((alias.asname or (alias.name.split('.')[0] if isinstance(node,ast.Import) else alias.name),node))
        if isinstance(node,(ast.ExceptHandler,ast.MatchAs,ast.MatchStar)) and node.name:
            other_writes.append((node.name,node))
        if isinstance(node,ast.MatchMapping) and node.rest:other_writes.append((node.rest,node))
        for child in ast.iter_child_nodes(node):collect_bindings(child)
    for statement in fn.body:collect_bindings(statement)
    def evidence(node):
        return dict(id=a.id(node),span=list(a.pos(node)),expression=a.text(node))
    def unresolved(node,reason):
        unknown.append(dict(reason=reason,evidence=evidence(node)))
    def unsupported_flow(node):
        while node is not None and node is not fn:
            if isinstance(node,(ast.For,ast.AsyncFor,ast.While,ast.Try,ast.TryStar,ast.With,ast.AsyncWith,ast.Match)):
                return True
            node=a.parent.get(node)
        return False
    def resolve(node,point=None,seen=()):
        if unsupported_flow(node):return node,[],False
        if not isinstance(node,ast.Name):return node,[],True
        if point is None:
            child=node;parent=a.parent.get(child)
            while parent is not None and parent is not fn:
                if isinstance(parent,(ast.Assign,ast.AnnAssign)) and child is parent.value:
                    if any(isinstance(x,ast.NamedExpr) for x in ast.walk(parent.value)):
                        return node,[],False
                    point=(parent.lineno,parent.col_offset);break
                child=parent;parent=a.parent.get(child)
        point=point or (node.lineno,node.col_offset)
        token=(a.qname(node),node.id,point)
        if token in seen or len(seen)>=12:return node,[],False
        definition=a.stable_definition(node,node.id,point)
        writes=[n for n in nodes if isinstance(n,ast.Name) and n.id==node.id and
                isinstance(n.ctx,(ast.Store,ast.Del)) and (n.lineno,n.col_offset)<point and
                (a.qname(n)==a.qname(node) or a.qname(n) is None or a.qname(node) is None)]
        writes += [n for name,n in other_writes if name==node.id and (n.lineno,n.col_offset)<point]
        if definition is None:
            return node,[],node.id in params and a.qname(node)==fn.name+'.<locals>.'+node.id and not writes
        if unsupported_flow(definition):return node,[],False
        # shortcut: only simple dominating lexical assignments; interprocedural/loop flow stays unknown.
        if not isinstance(definition,(ast.Assign,ast.AnnAssign)) or definition.value is None:return node,[],False
        targets=definition.targets if isinstance(definition,ast.Assign) else [definition.target]
        if len(targets)!=1 or not isinstance(targets[0],ast.Name):return node,[],False
        if any(n not in targets and (n.lineno,n.col_offset)>(definition.lineno,definition.col_offset) for n in writes):
            return node,[],False
        value,chain,known=resolve(definition.value,(definition.lineno,definition.col_offset),seen+(token,))
        return value,chain+[evidence(definition)],known
    def domain_info(node,seen=()):
        unknown=dict(kind='unknown',evidence=[],assumptions=[])
        if id(node) in seen or len(seen)>=12:return unknown
        value,chain,known=resolve(node)
        if not known:return unknown
        def receipt(kind,rule,site,parents=()):
            return dict(kind=kind,evidence=[*chain,dict(rule=rule,**evidence(site)),
                        *(e for p in parents for e in p['evidence'])],
                        assumptions=['conditional on successful evaluation and declared builtin semantics',
                                     *(s for p in parents for s in p['assumptions'])])
        def infer(x):return domain_info(x,seen+(id(node),))
        if isinstance(value,ast.Constant) and type(value.value) is str:
            return receipt('str','string_literal',value)
        if isinstance(value,(ast.List,ast.Tuple,ast.ListComp)):
            return receipt('sequence','sequence_construction',value)
        if isinstance(value,ast.Name) and value.id in params:
            ann=params[value.id].annotation
            base=ann.value if isinstance(ann,ast.Subscript) else ann
            q=a.qname(base) if base is not None else None
            annotation='str' if q=='builtins.str' else 'sequence' if q in ('builtins.list','builtins.tuple','typing.List','typing.Tuple') else None
            if ann is not None and annotation is None:return unknown
            doc=ast.get_docstring(fn) or '';claims=[]
            for line in doc.splitlines():
                line=line.strip()
                patterns=[rf':type\s+{re.escape(value.id)}:\s*(str|string|list|tuple)',
                          rf'{re.escape(value.id)}\s*\((str|string|list|tuple)\)\s*:\s*.*']
                if len(params)==1:
                    patterns.append(rf'{re.escape(fn.name)} is a function that takes (?:a )?(string|list|tuple) and returns [^.]+\.')
                for pattern in patterns:
                    m=re.fullmatch(pattern,line,re.IGNORECASE)
                    if m:claims.append(('str' if m[1].lower() in ('str','string') else 'sequence',line))
            types={t for t,_ in claims}|({annotation} if annotation else set())
            if len(types)!=1:return unknown
            if annotation:return receipt(annotation,'qualified_parameter_annotation',ann)
            result=receipt(next(iter(types)),'explicit_public_parameter_type',fn.body[0].value)
            result['public_quotes']=[line for _,line in claims]
            result['assumptions'].append('public type statement is unverified; not a runtime observation')
            return result
        if isinstance(value,ast.Call) and not value.keywords and not any(isinstance(x,ast.Starred) for x in value.args):
            api=a.api(value)
            if api in ('str','list','tuple','sorted') and len(value.args)<=1:
                return receipt('str' if api=='str' else 'sequence','qualified_builtin_constructor',value)
            if isinstance(value.func,ast.Attribute):
                parent=infer(value.func.value);method=value.func.attr
                if parent['kind']=='str':
                    if ((method=='replace' and len(value.args)==2 and all(isinstance(x,ast.Constant) and type(x.value) is str for x in value.args)) or
                        (method in ('lower','upper','casefold','strip','lstrip','rstrip') and not value.args) or
                        (method=='join' and len(value.args)==1)):
                        return receipt('str','builtin_string_result',value,[parent])
                    if method=='split' and len(value.args)<=1:
                        return receipt('sequence','builtin_string_split_result',value,[parent])
        if isinstance(value,ast.Subscript) and isinstance(value.slice,ast.Slice):
            parent=infer(value.value)
            if parent['kind']!='unknown':return receipt(parent['kind'],'builtin_sequence_slice',value,[parent])
        return unknown
    def domain(node):return domain_info(node)['kind']
    def add(kind,node,slots,properties,relations=(),assumptions=()):
        row=dict(id=a.id(node)+'/'+kind,kind=kind,scope=fn.name,evidence=evidence(node),
                 slots={k:dict(type=t,evidence=evidence(n)) for k,(t,n) in slots.items()},
                 properties=properties,relations=list(relations),assumptions=list(assumptions),
                 domain_evidence={k:info for k,(_,n) in slots.items() if (info:=domain_info(n))['kind']!='unknown'},
                 status='source_bound_conditional',bug_verdict='not_inferred')
        instances.append(row);return row
    def relation(subject,predicate,obj,sites):
        return dict(subject=subject,predicate=predicate,object=obj,evidence=[evidence(n) for n in sites],status='lexical_flow')
    operations={}
    for node in nodes:
        if not isinstance(node,ast.Call):continue
        api=a.api(node)
        if api in ('set','frozenset','len','collections.Counter') and len(node.args)==1 and not node.keywords and not isinstance(node.args[0],ast.Starred):
            kind={'set':'deduplication','frozenset':'deduplication','len':'cardinality','collections.Counter':'frequency_aggregation'}[api]
            if kind=='frequency_aggregation' and domain(node.args[0])=='unknown':
                unresolved(node,'counter_iterable_vs_mapping_domain_unknown');continue
            properties={'deduplication':['occurrences collapse to equality membership'],
                        'cardinality':['measure collection size'],
                        'frequency_aggregation':['aggregate occurrence frequencies']}[kind]
            operations[id(node)]=add(kind,node,dict(source=('iterable',node.args[0]),result=('value',node)),properties,
                                    assumptions=['builtin input domain must be valid']+
                                    ([domain(node.args[0]),'input follows its declared non-mapping iterable semantics'] if kind=='frequency_aggregation' else []))
        elif isinstance(node.func,ast.Attribute):
            method=node.func.attr;receiver=node.func.value;typ=domain(receiver)
            if method=='replace' and len(node.args)==2 and not node.keywords and all(isinstance(x,ast.Constant) and type(x.value) is str for x in node.args):
                if typ!='str':
                    unresolved(node,'replace_receiver_not_known_string');continue
                operations[id(node)]=add('sequence_transform',node,dict(source=('text',receiver),result=('text',node),pattern=('text',node.args[0]),replacement=('text',node.args[1])),
                                        ['replace matching text fragments'],assumptions=['receiver must use string replace semantics',typ])
            elif method in ('find','rfind','index') and len(node.args)==1 and not node.keywords:
                if isinstance(node.args[0],ast.Starred):unresolved(node,'unpacked_search_arguments');continue
                if typ=='unknown':unresolved(node,'search_receiver_domain_unknown');continue
                if method in ('find','rfind') and typ!='str':
                    unresolved(node,'find_receiver_not_string');continue
                absence='missing returns negative sentinel' if method in ('find','rfind') else 'missing raises exception'
                operations[id(node)]=add('position_lookup',node,dict(source=('sequence',receiver),needle=('element',node.args[0]),position=('index',node)),
                                        ['search produces position',absence],assumptions=[typ,'receiver follows its declared builtin semantics'])
    for node in nodes:
        if isinstance(node,(ast.ListComp,ast.GeneratorExp)):
            if len(node.generators)!=1 or node.generators[0].is_async:
                unresolved(node,'nested_or_async_comprehension');continue
            g=node.generators[0]
            if not isinstance(g.target,ast.Name):unresolved(node,'destructured_iteration');continue
            identity=isinstance(node.elt,ast.Name) and node.elt.id==g.target.id
            if identity and g.ifs:
                if len(g.ifs)!=1 or any(isinstance(x,(ast.Call,ast.NamedExpr,ast.Lambda)) for x in ast.walk(g.ifs[0])):
                    unresolved(node,'effectful_or_multiple_predicate');continue
                origin,chain,known=resolve(g.iter)
                properties=['identity selection', 'predicate true retained false removed', 'iteration order and occurrence positions retained locally']
                rel=[]
                if known and id(origin) in operations:
                    producer=operations[id(origin)]
                    rel.append(relation(producer['id'],'feeds_selection_source',a.id(node)+'/selective_filter',[origin,g.iter,node]))
                if not known:unresolved(g.iter,'selection_source_flow_unknown')
                row=add('selective_filter',node,dict(source=('iterable',g.iter),element=('element',g.target),predicate=('condition',g.ifs[0]),result=('sequence',node)),properties,rel,
                        ['predicate evaluation does not mutate the element or source'])
                row['source_chain']=chain
                operations[id(node)]=row
                if known and id(origin) in operations and operations[id(origin)]['kind']=='sequence_transform':
                    producer=operations[id(origin)]
                    add('transform_then_filter',node,dict(input_source=('text',origin.func.value),pattern=('text',origin.args[0]),
                        replacement=('text',origin.args[1]),filter_source=('iterable',g.iter),element=('element',g.target),
                        predicate=('condition',g.ifs[0]),result=('sequence',node)),
                        ['text transformation precedes identity selection','original input and filtered source may differ'],
                        [relation(producer['id'],'transform_flows_to_filter',a.id(node)+'/transform_then_filter',[origin,g.iter,node])],
                        producer['assumptions']+row['assumptions'])['source_chain']=chain
            elif not identity and not g.ifs:
                operations[id(node)]=add('element_mapping',node,dict(source=('iterable',g.iter),element=('element',g.target),transform=('expression',node.elt),result=('sequence',node)),['map each element to an expression'])
        elif isinstance(node,ast.Subscript) and isinstance(node.ctx,ast.Load) and not isinstance(node.slice,ast.Slice):
            typ=domain(node.value)
            if typ=='unknown':unresolved(node,'indexed_receiver_domain_unknown');continue
            value,chain,known=resolve(node.slice)
            producer=operations.get(id(value)) if known else None
            if producer and producer['kind']=='position_lookup':
                add('search_position_indexing',node,dict(search_source=('sequence',value.func.value),needle=('element',value.args[0]),position=('index',node.slice),indexed_source=('sequence',node.value),result=('element',node)),
                    ['search result consumed as index','missing found boundary position partitions'],
                    [relation(producer['id'],'position_flows_to_index',a.id(node)+'/search_position_indexing',[value,node.slice,node])],producer['assumptions'])['source_chain']=chain
            elif not known:unresolved(node,'index_origin_flow_unknown')
            else:
                add('direct_indexing',node,dict(source=('sequence',node.value),position=('index',node.slice),result=('element',node)),['indexed element access','index boundary partition'],
                    assumptions=[typ,'receiver follows its declared builtin semantics','index must be an integer'])
    for node in nodes:
        if isinstance(node,ast.Call) and id(node) in operations and operations[id(node)]['kind']=='cardinality':
            inner=node.args[0];producer=operations.get(id(inner))
            # shortcut: inline dedup only; alias mutation analysis is required before widening.
            if producer and producer['kind']=='deduplication':
                add('distinct_cardinality',node,dict(source=('iterable',inner.args[0]),distinct=('value',inner),result=('value',node)),
                    ['count equality classes rather than total occurrences','same support different multiplicities'],
                    [relation(producer['id'],'deduplication_flows_to_count',a.id(node)+'/distinct_cardinality',[inner,node])],
                    producer['assumptions'])
    doc=ast.get_docstring(fn) or ''
    cues=[]
    directives={'preserve order.':('order','preserved'),'keep duplicates.':('multiplicity','preserved'),
                'return unique values.':('multiplicity','collapsed'),'return -1 when absent.':('missing_policy','negative_sentinel')}
    for line in doc.splitlines():
        phrase=line.strip().lower()
        if phrase in directives:
            prop,value=directives[phrase];cues.append(dict(property=prop,value=value,evidence=line.strip(),status='explicit_doc_cue_unverified'))
    return dict(source_sha256=hashlib.sha256(source.encode()).hexdigest(),entry=fn.name,
                instances=sorted(instances,key=lambda r:(r['evidence']['span'],r['kind'])),unknown=unknown,
                requirement=dict(status='explicit_cues_unverified' if cues else 'unknown',cues=cues,public_docstring=doc))
