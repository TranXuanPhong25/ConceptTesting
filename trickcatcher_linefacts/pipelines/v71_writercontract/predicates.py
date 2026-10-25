"""Closed compositional predicates for input construction and native local events.

Values are data ASTs. No eval/exec, attribute access, or arbitrary function calls.
"""
import z3


class SymbolicString(list):
    """Codepoints with a string tag; never confused with an integer list."""


class SymbolicTuple(list):
    """Preserve tuple/list distinction through symbolic equality."""


def string_order(a, b, inclusive=False):
    if not isinstance(a, (str, SymbolicString)) or not isinstance(b, (str, SymbolicString)):
        raise ValueError('symbolic_string_type_mismatch')
    a = [ord(c) for c in a] if isinstance(a, str) else a
    b = [ord(c) for c in b] if isinstance(b, str) else b
    prefix = z3.BoolVal(True)
    less = []
    for left, right in zip(a, b):
        less.append(z3.And(prefix, left < right))
        prefix = z3.And(prefix, left == right)
    if len(a) < len(b) or inclusive and len(a) == len(b):
        less.append(prefix)
    return z3.Or(*less)

SIGNATURES={
    'literal':(), 'input':(), 'local':(),
    'len':('value',), 'add':('left','right'), 'sub':('left','right'), 'mod':('left','right'),
    'index':('value','index'), 'count_distinct':('value',),
    'and':('items',), 'or':('items',), 'not':('value',),
    'eq':('left','right'), 'lt':('left','right'), 'le':('left','right'),
    'has_duplicate':('value',), 'all_distinct':('value',),
}


def validate(node,arity,allow_local=False,depth=0):
    if depth>24 or not isinstance(node,dict):raise ValueError('predicate_depth_or_type')
    op=node.get('op')
    if op not in SIGNATURES:raise ValueError('predicate_operator')
    extra={'literal':{'value'},'input':{'arg'},'local':{'name'}}.get(op,set(SIGNATURES[op]))
    if set(node)!={'op'}|extra:raise ValueError('predicate_fields')
    if op=='literal':
        if type(node['value'])not in (bool,int,str):raise ValueError('predicate_literal')
    elif op=='input':
        if type(node['arg'])is not int or not 0<=node['arg']<arity:raise ValueError('predicate_input_binding')
    elif op=='local':
        if not allow_local or not isinstance(node['name'],str) or not node['name'].isidentifier():raise ValueError('predicate_local_binding')
    elif op in ('and','or'):
        if not isinstance(node['items'],list) or not 1<=len(node['items'])<=16:raise ValueError('predicate_boolean_items')
        for child in node['items']:validate(child,arity,allow_local,depth+1)
    else:
        for key in SIGNATURES[op]:validate(node[key],arity,allow_local,depth+1)
    return node


def local_names(node):
    if node['op']=='local':return {node['name']}
    result=set()
    for value in node.values():
        if isinstance(value,dict):result|=local_names(value)
        elif isinstance(value,list):
            for item in value:
                if isinstance(item,dict):result|=local_names(item)
    return result


def evaluate(node,args,locals_map=None):
    op=node['op'];get=lambda key:evaluate(node[key],args,locals_map)
    if op=='literal':return node['value']
    if op=='input':return args[node['arg']]
    if op=='local':
        if locals_map is None or node['name'] not in locals_map:raise ValueError('unobserved_local')
        return locals_map[node['name']]
    if op=='len':return len(get('value'))
    if op=='add':return get('left')+get('right')
    if op=='sub':return get('left')-get('right')
    if op=='mod':return get('left')%get('right')
    if op=='index':
        value,index=get('value'),get('index')
        if type(index)is not int:raise ValueError('predicate_index')
        return value[index]
    if op=='count_distinct':return len(set(get('value')))
    if op=='and':return all(bool(evaluate(x,args,locals_map)) for x in node['items'])
    if op=='or':return any(bool(evaluate(x,args,locals_map)) for x in node['items'])
    if op=='not':return not get('value')
    if op=='eq':return get('left')==get('right')
    if op=='lt':return get('left')<get('right')
    if op=='le':return get('left')<=get('right')
    if op=='has_duplicate':return len(set(get('value')))<len(get('value'))
    if op=='all_distinct':return len(set(get('value')))==len(get('value'))
    raise ValueError('predicate_operator')


def symbolic(node,args):
    op=node['op'];get=lambda key:symbolic(node[key],args)
    if op=='literal':return node['value']
    if op=='input':return args[node['arg']]
    if op=='len':return len(get('value'))
    if op=='add':return get('left')+get('right')
    if op=='sub':return get('left')-get('right')
    if op=='mod':
        # Positive concrete modulus only; avoids silently changing Python negative-divisor semantics.
        divisor=get('right')
        if type(divisor)is not int or divisor<=0:raise ValueError('symbolic_modulus')
        return get('left')%divisor
    if op=='eq':return symbolic_equal(get('left'),get('right'))
    if op in ('lt','le'):
        a,b=get('left'),get('right')
        if isinstance(a,(str,SymbolicString)) or isinstance(b,(str,SymbolicString)):
            return string_order(a,b,inclusive=op=='le')
        if isinstance(a,(list,tuple,str))or isinstance(b,(list,tuple,str)):raise ValueError('unsupported_sequence_ordering')
        return a<b if op=='lt' else a<=b
    if op=='and':return z3.And(*[symbolic(x,args) for x in node['items']])
    if op=='or':return z3.Or(*[symbolic(x,args) for x in node['items']])
    if op=='not':return z3.Not(get('value'))
    if op in ('all_distinct','has_duplicate'):
        xs=get('value');xs=[ord(c)for c in xs]if isinstance(xs,str)else xs
        condition=z3.And(*[z3.Not(symbolic_equal(xs[i],xs[j]))for i in range(len(xs))for j in range(i)])
        return z3.Not(condition) if op=='has_duplicate' else condition
    raise ValueError('symbolic_predicate_unsupported:'+op)


def symbolic_equal(a,b):
    if isinstance(a,(str,SymbolicString)) or isinstance(b,(str,SymbolicString)):
        if not isinstance(a,(str,SymbolicString)) or not isinstance(b,(str,SymbolicString)):return z3.BoolVal(False)
        if isinstance(a,str):a=SymbolicString(ord(c)for c in a)
        if isinstance(b,str):b=SymbolicString(ord(c)for c in b)
    elif isinstance(a,SymbolicTuple)!=isinstance(b,SymbolicTuple):return z3.BoolVal(False)
    if isinstance(a,list)or isinstance(b,list):
        if not isinstance(a,list)or not isinstance(b,list)or len(a)!=len(b):return z3.BoolVal(False)
        return z3.And(*[symbolic_equal(x,y)for x,y in zip(a,b)])
    return a==b
