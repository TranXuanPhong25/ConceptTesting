"""One prospective literal policy for generation, final audit, and scoring."""
import ast
import math


def bounded(value,depth=0):
    if depth>12:raise ValueError('literal_depth')
    if value is None or type(value)in (bool,int):return value
    if type(value)is float:
        if not math.isfinite(value):raise ValueError('nonfinite_literal')
        return value
    if type(value)is str:
        if len(value)>8000:raise ValueError('literal_size')
        return value
    if type(value)in (list,tuple,set,dict):
        if len(value)>256:raise ValueError('literal_size')
        if type(value)is dict:
            for k,v in value.items():bounded(k,depth+1);bounded(v,depth+1)
        else:
            for v in value:bounded(v,depth+1)
        return value
    raise ValueError('unsupported_literal')


def parse_expected(raw):
    # Strings retain the established Python-literal convention: "'abc'" means
    # the string abc; "3" means integer3. A bare abc is never guessed/coerced.
    if type(raw)is str:
        if len(raw)>16000:raise ValueError('literal_size')
        value=ast.literal_eval(raw)
    else:
        # JSON scalar/container values preserve their actual types. Object keys
        # are already JSON strings; we never infer numeric keys from their text.
        value=raw
    return bounded(value)


def parse_arguments(raw):
    if type(raw)is not str or len(raw)>16000:raise ValueError('argument_literal')
    value=bounded(ast.literal_eval(raw))
    if type(value)is not tuple:raise ValueError('argument_tuple')
    return value
