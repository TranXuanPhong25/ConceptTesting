"""Bounded literal transport and exact typed values. No semantic input ranking."""
import ast
import math
from .paths import CONFIG
C=CONFIG['chain']


def check_topology(value,*,max_nodes=None,max_items=None):
    max_nodes=C['max_input_nodes'] if max_nodes is None else max_nodes
    max_items=C['max_items'] if max_items is None else max_items
    active=set();mutable=set();size=0
    def visit(v,depth):
        nonlocal size
        size+=1
        if size>max_nodes or depth>C['max_input_depth']:raise ValueError('literal_size_depth')
        typ=type(v)
        if typ in (list,tuple,dict,set,frozenset):
            if id(v) in active:raise ValueError('cycle')
            if typ in (list,dict,set):
                if id(v) in mutable:raise ValueError('shared_mutable_alias')
                mutable.add(id(v))
            if len(v)>max_items:raise ValueError('container_size')
            active.add(id(v))
            values=[x for pair in v.items() for x in pair] if typ is dict else v
            for child in values:visit(child,depth+1)
            active.remove(id(v))
        elif typ not in (int,float,str,bytes,bool,type(None)):raise ValueError('literal_type')
        elif typ in (str,bytes) and len(v)>C['max_input_chars']:raise ValueError('scalar_size')
        elif typ is float and not math.isfinite(v):raise ValueError('nonfinite_float')
        elif typ is int and v.bit_length()>4096:raise ValueError('integer_size')
    visit(value,0)
    return value


def parse_literal(text,*,output=False):
    chars=C['max_output_bytes'] if output else C['max_input_chars']
    max_nodes=2048 if output else C['max_input_nodes']
    if type(text) is not str or len(text.encode('utf-8'))>chars:raise ValueError('literal_text_size')
    try:tree=ast.parse(text,mode='eval')
    except (SyntaxError,ValueError,RecursionError) as exc:raise ValueError('literal_syntax') from exc
    pending=[(tree,0)];size=0
    while pending:
        node,depth=pending.pop();size+=1
        if size>max_nodes or depth>C['max_input_depth']:raise ValueError('literal_size_depth')
        pending.extend((x,depth+1) for x in ast.iter_child_nodes(node))
    try:value=ast.literal_eval(tree)
    except (SyntaxError,ValueError,TypeError,RecursionError,MemoryError) as exc:raise ValueError('not_literal') from exc
    return check_topology(value,max_nodes=max_nodes,max_items=512 if output else C['max_items'])


def parse_arguments(text,arity):
    args=parse_literal(text)
    if type(args) is not tuple:raise ValueError('full_positional_tuple_required')
    if arity['required_keyword_only']:raise ValueError('keyword_only_unsupported')
    if len(args)<arity['required'] or (not arity['varargs'] and len(args)>arity['positional']):raise ValueError('arity')
    return args


def literal_for_transport(args):
    check_topology(args)  # Must happen before repr loses topology.
    text=repr(args)
    if len(text)>C['max_input_chars']:raise ValueError('literal_text_size')
    return text


def typed_value(value):
    typ=type(value)
    if typ not in (int,float,str,bytes,bool,type(None),list,tuple,set,frozenset,dict):raise ValueError('unsupported_output_type')
    if typ is float and not math.isfinite(value):raise ValueError('nonfinite_float')
    if typ in (list,tuple):return (typ.__name__,tuple(typed_value(x) for x in value))
    if typ in (set,frozenset):return (typ.__name__,tuple(sorted((typed_value(x) for x in value),key=repr)))
    if typ is dict:return ('dict',tuple(sorted(((typed_value(k),typed_value(v)) for k,v in value.items()),key=repr)))
    return (typ.__name__,value)
