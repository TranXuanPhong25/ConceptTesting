"""Lexically scoped AST evidence graph; syntactic dependencies, no semantic proof."""
import ast
import hashlib


def build(source):
    tree=ast.parse(source); sha=hashlib.sha256(source.encode()).hexdigest()
    nodes=[];edges=[]
    def walk(node,scope,definitions,guards):
        if isinstance(node,(ast.FunctionDef,ast.ClassDef)):
            scope=scope+[f'{node.name}@{node.lineno}'];definitions=dict(definitions)
        if isinstance(node,(ast.expr,ast.stmt)):
            span=[node.lineno,node.col_offset,node.end_lineno,node.end_col_offset]
            ident=hashlib.sha256(repr((sha,scope,span,type(node).__name__)).encode()).hexdigest()[:16]
            nodes.append({'id':ident,'span':span,'kind':type(node).__name__,'scope':scope,'code':ast.unparse(node)[:1600]})
            for guard in guards: edges.append({'from':guard,'to':ident,'kind':'syntactic_control_context'})
            if isinstance(node,ast.Name):
                if isinstance(node.ctx,ast.Load) and node.id in definitions:
                    edges.append({'from':definitions[node.id],'to':ident,'kind':'lexical_prior_definition_candidate'})
                if isinstance(node.ctx,ast.Store):definitions[node.id]=ident
            if isinstance(node,(ast.If,ast.While)): guards=guards+[ident]
        for child in ast.iter_child_nodes(node):walk(child,scope,definitions,guards)
    walk(tree,[],{},[])
    return {'source_sha256':sha,'nodes':nodes,'edges':edges,
            'status':'syntactic_candidate_graph','limitations':['not SSA/reaching-definition proof','control context does not assert branch outcome']}
