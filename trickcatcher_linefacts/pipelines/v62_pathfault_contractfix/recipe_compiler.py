"""Generic source-bound native recipes. No per-case answer table or private oracle."""
import ast
import hashlib
from .bindings import resolve
from .recipe_ir import multiplicity,odd_cardinality_unique


def compile_public(request,budget):
    source=request['source'];tree=ast.parse(source);fn,_=resolve(tree,request['entry'])
    sha=hashlib.sha256(source.encode()).hexdigest()
    examples=[ast.literal_eval(x['arguments']) for x in request['public_examples']]
    recipes=[];unsupported=[]
    arguments=[a.arg for a in fn.args.posonlyargs+fn.args.args]
    if arguments and arguments[0]=='self':arguments=arguments[1:]
    shadowed=set(arguments)
    for n in ast.walk(fn):
        if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Store):shadowed.add(n.id)
        if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n is not fn:shadowed.add(n.name)
    global_defs={n.name for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
    shadowed|=global_defs-{'Solution',request['entry']}
    def own_nodes(node):
        yield node
        for child in ast.iter_child_nodes(node):
            if isinstance(child,(ast.FunctionDef,ast.Lambda,ast.ClassDef)):
                unsupported.append('helper_scope_requires_separate_binding')
            else:yield from own_nodes(child)
    for node in own_nodes(fn):
        if not isinstance(node,ast.Call):continue
        span=[node.lineno,node.col_offset,node.end_lineno,node.end_col_offset]
        common=dict(source_sha256=sha,span=span,function=fn.name,budget=budget,
                    provenance={'origin':'source_bound_behavioral_candidate','normative_status':'unknown'})
        if isinstance(node.func,ast.Name) and node.func.id in ('len','sum') and len(node.args)==1:
            if node.func.id in shadowed or 'set' in shadowed:
                unsupported.append('shadowed_builtin_recipe');continue
            arg=node.args[0]
            if isinstance(arg,ast.Call) and isinstance(arg.func,ast.Name) and arg.func.id=='set' and len(arg.args)==1:arg=arg.args[0]
            if isinstance(arg,ast.Name) and arg.id in arguments:
                index=arguments.index(arg.id)
                if all(index<len(e) and type(e[index])is list and all(type(x)is int for x in e[index]) for e in examples):
                    after=(f'{node.func.id}({arg.id})' if isinstance(node.args[0],ast.Call) else f'{node.func.id}(set({arg.id}))')
                    alt={'span':span,'node_kind':'Call','before':ast.unparse(node),'after':after}
                    recipes.append(multiplicity(**common,seq_arg=index,require_length=None,alternative=alt))
        elif isinstance(node.func,ast.Attribute) and isinstance(node.func.value,ast.Name) and node.func.value.id=='math' and node.func.attr in ('ceil','floor') and len(node.args)==1:
            if 'math' in shadowed:unsupported.append('shadowed_math_recipe');continue
            expr=node.args[0]
            if isinstance(expr,ast.BinOp) and isinstance(expr.op,ast.Div) and isinstance(expr.left,ast.Name) and isinstance(expr.right,ast.Constant) and expr.right.value==2:
                list_args=[i for i in range(len(arguments)) if all(i<len(e) and type(e[i])is list and all(type(x)is int for x in e[i]) for e in examples)]
                if len(list_args)==1:
                    other='floor' if node.func.attr=='ceil' else 'ceil'
                    alt={'span':span,'node_kind':'Call','before':ast.unparse(node),'after':f'math.{other}({ast.unparse(expr)})'}
                    r=odd_cardinality_unique(**common,seq_arg=list_args[0],alternative=alt)
                    r.pop('recipe_id');r['event_predicate']['local_odd_equals_input_length']=expr.left.id
                    from .recipe_ir import validate
                    recipes.append(validate(r))
    # Explicitly report unavailable constructors rather than claiming all source code supported.
    if not recipes:unsupported.append('no_applicable_registered_native_recipe')
    return {'recipes':recipes[:3],'omitted_recipes':max(0,len(recipes)-3),'unsupported':unsupported}
