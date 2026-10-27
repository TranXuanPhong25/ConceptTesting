"""Source-grounded local facts. No target execution and no benchmark imports."""
from __future__ import annotations
import ast
import hashlib
from collections import defaultdict
import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider, QualifiedNameProvider, ScopeProvider


def literal(node):
    if isinstance(node,ast.Constant):return node.value
    if isinstance(node,ast.UnaryOp) and isinstance(node.op,ast.USub) and isinstance(node.operand,ast.Constant) and type(node.operand.value) in (int,float):return -node.operand.value
    if isinstance(node,(ast.List,ast.Tuple,ast.Dict,ast.Set)) and not list(ast.iter_child_nodes(node)):return []
    return None


class Analysis:
    def __init__(self,source):
        self.source=source
        self.lines=source.splitlines()
        self.sha=hashlib.sha256(source.encode()).hexdigest()
        self.tree=ast.parse(source)
        self.parent={c:p for p in ast.walk(self.tree) for c in ast.iter_child_nodes(p)}
        annotation_roots=[n.annotation for n in ast.walk(self.tree) if isinstance(n,(ast.arg,ast.AnnAssign)) and n.annotation is not None]
        annotation_roots += [n.returns for n in ast.walk(self.tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.returns is not None]
        annotations={n for root in annotation_roots for n in ast.walk(root)}
        self.nodes=[n for n in ast.walk(self.tree) if n not in annotations]
        self.meta={}
        wrapper=MetadataWrapper(cst.parse_module(source))
        outer=self
        class Metadata(cst.CSTVisitor):
            METADATA_DEPENDENCIES=(PositionProvider,ScopeProvider,QualifiedNameProvider)
            def on_visit(self,node):
                pos=self.get_metadata(PositionProvider,node,None)
                if pos is not None:
                    names=self.get_metadata(QualifiedNameProvider,node,set())
                    scope=self.get_metadata(ScopeProvider,node,None)
                    key=(pos.start.line,pos.start.column,pos.end.line,pos.end.column)
                    record=outer.meta.setdefault(key,{'qualified_names':set(),'scope_kinds':set()})
                    record['qualified_names'].update(n.name for n in names)
                    if scope is not None:record['scope_kinds'].add(type(scope).__name__)
                return True
        wrapper.visit(Metadata())
        self.assignments=defaultdict(list)
        self.symbol_assignments=defaultdict(list)
        for node in self.nodes:
            targets=node.targets if isinstance(node,ast.Assign) else [node.target] if isinstance(node,(ast.AnnAssign,ast.AugAssign)) else []
            for target in targets:
                if isinstance(target,ast.Name):
                    self.assignments[(self.scope(node),target.id)].append(node)
                    symbol=self.qname(target)
                    if symbol:self.symbol_assignments[symbol].append(node)
        self.records={self.id(n):self.fact(n) for n in self.nodes if isinstance(n,(ast.Call,ast.Subscript,ast.Assign,ast.AnnAssign,ast.AugAssign,ast.Compare,ast.Return,ast.BinOp,ast.ListComp,ast.SetComp,ast.DictComp,ast.GeneratorExp,ast.IfExp))}

    def pos(self,node):
        def col(line,byte):
            return len(self.lines[line-1].encode()[:byte].decode())
        return (node.lineno,col(node.lineno,node.col_offset),node.end_lineno,col(node.end_lineno,node.end_col_offset))

    def id(self,node):
        return self.sha[:12]+':'+type(node).__name__+':'+':'.join(map(str,self.pos(node)))

    def owner(self,node):
        p=self.parent.get(node)
        while p is not None:
            if isinstance(p,(ast.FunctionDef,ast.AsyncFunctionDef,ast.Lambda,ast.ClassDef,ast.ListComp,ast.SetComp,ast.DictComp,ast.GeneratorExp)):return p
            p=self.parent.get(p)
        return self.tree

    def scope(self,node):
        owner=self.owner(node)
        return 'module' if owner is self.tree else f'{type(owner).__name__}:{getattr(owner,"name","")}:{owner.lineno}:{owner.col_offset}'

    def qname(self,node):
        values=self.meta.get(self.pos(node),{}).get('qualified_names',set())
        if len(values)==1:return next(iter(values))
        return None

    def api(self,node):
        q=self.qname(node.func)
        return q[9:] if q and q.startswith('builtins.') else q

    def text(self,node):
        return ast.get_source_segment(self.source,node) or ast.unparse(node)

    def spec(self,node):
        p=node
        while p is not None:
            if isinstance(p,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                return ast.get_docstring(p) or ''
            p=self.parent.get(p)
        return ast.get_docstring(self.tree) or ''

    def stable_definition(self,node,name,point=None):
        point=point or (node.lineno,node.col_offset)
        refs=[n for n in ast.walk(node) if isinstance(n,ast.Name) and n.id==name]
        symbols={self.qname(n) for n in refs if self.qname(n)}
        definitions=self.symbol_assignments.get(next(iter(symbols)),[]) if len(symbols)==1 else self.assignments.get((self.scope(node),name),[])
        candidates=[n for n in definitions if (n.lineno,n.col_offset)<point]
        if not candidates:return None
        chosen=max(candidates,key=lambda n:(n.lineno,n.col_offset))
        if isinstance(chosen,ast.AugAssign):return None
        p=self.parent.get(chosen)
        while p is not self.owner(chosen):
            if isinstance(p,(ast.If,ast.For,ast.AsyncFor,ast.While,ast.Try,ast.With,ast.AsyncWith,ast.Match)):return None
            p=self.parent.get(p)
            if p is None:return None
        return chosen

    def origins(self,node,seen=frozenset(),point=None,budget=None):
        """Conservative dependency/effect chain, not an executable abstraction."""
        if budget is None:budget=[256]
        budget[0]-=1
        if budget[0]<0:return [{'effect':'unknown','reason':'origin_node_budget'}]
        if len(seen)>20:return [{'effect':'unknown','reason':'origin_depth_limit'}]
        if isinstance(node,ast.Name):
            key=(self.scope(node),node.id,point)
            if key in seen:return [{'effect':'unknown','reason':'cyclic_origin'}]
            definition=self.stable_definition(node,node.id,point)
            if definition:
                return self.origins(definition.value,seen|{key},(definition.lineno,definition.col_offset),budget)+[{'effect':'assignment','fact_id':self.id(definition)}]
            return [{'effect':'symbol','name':node.id,'scope_id':self.scope(node),'status':'parameter_or_unresolved'}]
        if isinstance(node,(ast.ListComp,ast.SetComp,ast.DictComp,ast.GeneratorExp)):
            dependencies=[]
            for generator in node.generators:
                dependencies+=self.origins(generator.iter,seen,point,budget)
                for predicate in generator.ifs:dependencies+=self.origins(predicate,seen,point,budget)
            expressions=[node.key,node.value] if isinstance(node,ast.DictComp) else [node.elt]
            for expression in expressions:dependencies+=self.origins(expression,seen,point,budget)
            return dependencies+[{'effect':'comprehension_selection','fact_id':self.id(node)}]
        if isinstance(node,ast.Call):
            dependencies=[]
            if isinstance(node.func,ast.Attribute):dependencies=self.origins(node.func.value,seen,point,budget)
            for arg in node.args:dependencies+=self.origins(arg,seen,point,budget)
            api=self.api(node)
            effect={'int':'fraction_or_text_to_integer','float':'to_floating_point','set':'occurrences_to_membership','len':'measure_length','min':'minimum_first_tie','max':'maximum_first_tie'}.get(api,'call_unknown')
            # Attribute methods need receiver-domain evidence; record assumptions.
            if isinstance(node.func,ast.Attribute) and node.func.attr in {'lower','upper','casefold','encode','index'}:
                effect={'lower':'text_normalization','upper':'text_normalization','casefold':'text_normalization','encode':'text_to_bytes','index':'first_occurrence_position'}[node.func.attr]
            return dependencies+[{'effect':effect,'fact_id':self.id(node),'resolved_api':api,'receiver_semantics':'conditional' if isinstance(node.func,ast.Attribute) else 'builtin_resolved' if api in {'int','float','set','len','min','max'} else 'unknown'}]
        if isinstance(node,ast.Constant):return [{'effect':'literal','value':node.value if isinstance(node.value,(str,int,float,bool,type(None))) else repr(node.value)}]
        deps=[]
        for child in ast.iter_child_nodes(node):
            if isinstance(child,ast.expr):deps+=self.origins(child,seen,point,budget)
        return deps

    def fact(self,node):
        start,col,end,endcol=self.pos(node)
        fact={'id':self.id(node),'scope_id':self.scope(node),'node_type':type(node).__name__,'span':{'line':start,'column':col,'end_line':end,'end_column':endcol},'expression':self.text(node),'source_sha256':self.sha}
        if isinstance(node,ast.Call):fact.update(resolved_api=self.api(node),qualified_name_status='resolved' if self.qname(node.func) else 'unknown')
        return fact

    def output_origins(self):
        result={}
        for n in self.nodes:
            if isinstance(n,ast.Return) and n.value is not None:result[self.id(n)]=self.origins(n.value)
        return result

    def value_unchanged(self,name,start,end,scope):
        for node in self.nodes:
            if not hasattr(node,'lineno') or self.scope(node)!=scope:
                continue
            if not start<(node.lineno,getattr(node,'col_offset',0))<end:
                continue
            if isinstance(node,ast.Name) and node.id==name and isinstance(node.ctx,(ast.Store,ast.Del)):return False
            if isinstance(node,ast.Delete):return False
            if isinstance(node,(ast.Assign,ast.AugAssign,ast.AnnAssign)):
                targets=node.targets if isinstance(node,ast.Assign) else [node.target]
                if any(isinstance(target,ast.Subscript) for target in targets):return False
            if isinstance(node,ast.Call) and (node.end_lineno,node.end_col_offset)<=end:
                if self.api(node) not in {'len','ord'}:
                    return False
                if isinstance(node.func,ast.Attribute) and isinstance(node.func.value,ast.Name) and node.func.value.id==name:return False
                if any(isinstance(x,ast.Name) and x.id==name for arg in node.args for x in ast.walk(arg)):return False
        return True

    def sequence_domain(self,name,at):
        prior=[n for n in self.assignments.get((self.scope(at),name),[]) if (n.lineno,n.col_offset)<(at.lineno,at.col_offset)]
        if prior:
            definition=self.stable_definition(at,name)
            if definition is None:return None
            value=definition.value
            if isinstance(value,(ast.List,ast.Tuple)):
                return {'domain':'sequence','basis':'literal_definition','fact_id':self.id(definition)}
            if isinstance(value,ast.Constant) and isinstance(value.value,str):
                return {'domain':'str','basis':'literal_definition','fact_id':self.id(definition)}
            if isinstance(value,ast.Call) and self.api(value) in {'list','tuple','str'}:
                return {'domain':'str' if self.api(value)=='str' else 'sequence','basis':'resolved_builtin_constructor','fact_id':self.id(definition)}
            return None
        owner=self.owner(at)
        while isinstance(owner,(ast.ListComp,ast.SetComp,ast.DictComp,ast.GeneratorExp)):
            owner=self.owner(owner)
        if isinstance(owner,(ast.FunctionDef,ast.AsyncFunctionDef)):
            args=[*owner.args.posonlyargs,*owner.args.args,*owner.args.kwonlyargs]
            for arg in args:
                if arg.arg==name and arg.annotation is not None:
                    ann=ast.unparse(arg.annotation)
                    if ann in {'str','list','tuple'} or ann.startswith(('List[','list[','Tuple[','tuple[')):
                        return {'domain':'str' if ann=='str' else 'sequence','basis':'type_annotation_assumption','clause':ann}
            if len(args)==1 and args[0].arg==name:
                doc=ast.get_docstring(owner) or ''
                import re
                if re.search(r'\bstring\b',doc,re.I):return {'domain':'str','basis':'public_docstring_assumption','clause':doc[:350]}
                if re.search(r'\b(?:list|array|tuple)\b',doc,re.I):return {'domain':'sequence','basis':'public_docstring_assumption','clause':doc[:350]}
        return None

    def nonempty_condition(self,test,name,truth,at):
        domain=self.sequence_domain(name,at)
        if isinstance(test,ast.UnaryOp) and isinstance(test.op,ast.Not):return self.nonempty_condition(test.operand,name,not truth,at)
        if isinstance(test,ast.Name) and test.id==name and truth and domain:return domain
        if not isinstance(test,ast.Compare) or len(test.ops)!=1:return None
        left,right=test.left,test.comparators[0];op=test.ops[0]
        if isinstance(left,ast.Name) and left.id==name and domain:
            empty=(isinstance(right,ast.Constant) and right.value=='') if domain['domain']=='str' else isinstance(right,(ast.List,ast.Tuple)) and not right.elts
            if empty and (isinstance(op,ast.NotEq) and truth or isinstance(op,ast.Eq) and not truth):return domain
        if isinstance(left,ast.Call) and self.api(left)=='len' and len(left.args)==1 and isinstance(left.args[0],ast.Name) and left.args[0].id==name:
            value=literal(right)
            if type(value) is int and (truth and isinstance(op,ast.Gt) and value>=0 or truth and isinstance(op,ast.GtE) and value>=1 or not truth and isinstance(op,ast.Eq) and value==0 or not truth and isinstance(op,ast.Lt) and value==1 or not truth and isinstance(op,ast.LtE) and value==0):
                return {**domain,'condition':self.text(test)} if domain else None
        return None

    def guarded_nonempty(self,name,at):
        child=at;parent=self.parent.get(child)
        while parent is not None:
            if isinstance(parent,ast.If):
                for truth,body in [(True,parent.body),(False,parent.orelse)]:
                    if child in body:
                        domain=self.nonempty_condition(parent.test,name,truth,at)
                        if domain and self.value_unchanged(name,(parent.test.end_lineno,parent.test.end_col_offset),(at.lineno,at.col_offset),self.scope(at)):
                            return {'guard_span':self.pos(parent.test),'branch':truth,'domain':domain,'status':'guarded_under_recorded_domain_assumptions'}
            # Earlier sibling early returns constrain the continuing path.
            for attr in ['body','orelse']:
                body=getattr(parent,attr,None)
                if isinstance(body,list) and child in body:
                    for previous in reversed(body[:body.index(child)]):
                        if isinstance(previous,ast.If) and previous.body and isinstance(previous.body[-1],(ast.Return,ast.Raise)):
                            domain=self.nonempty_condition(previous.test,name,False,at)
                            if domain and self.value_unchanged(name,(previous.end_lineno,previous.end_col_offset),(at.lineno,at.col_offset),self.scope(at)):
                                return {'guard_span':self.pos(previous.test),'branch':False,'domain':domain,'status':'guarded_under_recorded_domain_assumptions'}
            if parent is self.owner(at):
                break
            child=parent;parent=self.parent.get(parent)
        return None

    def export(self):
        return {'source_sha256':self.sha,'backend':'LibCST metadata + AST local facts','facts':list(self.records.values()),'output_origins':self.output_origins(),'limits':['Origins are conservative local dependencies, not complete reaching-definitions or alias analysis.','Guard facts are conditional on recorded builtin/domain and value-stability assumptions.']}
