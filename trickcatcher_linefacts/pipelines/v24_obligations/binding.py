"""Named JSON calls bound with inspect; no model-authored Python argument strings."""
import ast
import inspect
import json

from .chain_inputs import check_topology, literal_for_transport
from .common import D, parse_literal


def signature(task):
    fn = next(n for n in ast.parse(task['source_original']).body
              if isinstance(n, ast.FunctionDef) and n.name == task['entry'])
    if fn.args.posonlyargs or fn.args.vararg or fn.args.kwarg or fn.args.kwonlyargs:
        raise ValueError('unsupported_signature')
    defaults = [inspect.Parameter.empty] * (len(fn.args.args) - len(fn.args.defaults))
    defaults += [ast.literal_eval(x) for x in fn.args.defaults]
    return inspect.Signature([inspect.Parameter(n.arg, inspect.Parameter.POSITIONAL_OR_KEYWORD, default=d)
                              for n, d in zip(fn.args.args, defaults)])


def check_json(value):
    check_topology(value)
    def walk(v, depth):
        if depth > D['input_depth']:
            raise ValueError('JSON_depth')
        if type(v) is int and v.bit_length() > D['integer_bits']:
            raise ValueError('JSON_integer_size')
        if type(v) is dict:
            if any(type(k) is not str for k in v):
                raise ValueError('JSON_object_keys')
            for child in v.values():
                walk(child, depth + 1)
        elif type(v) is list:
            for child in v:
                walk(child, depth + 1)
        elif type(v) not in (str, int, float, bool, type(None)):
            raise ValueError('JSON_type')
    walk(value, 0)
    return json.loads(json.dumps(value, allow_nan=False))


def bind(task, arguments):
    if type(arguments) is not dict:
        raise ValueError('named_arguments_required')
    arguments = check_json(arguments)
    try:
        bound = signature(task).bind(**arguments)
    except TypeError as exc:
        raise ValueError('argument_binding') from exc
    bound.apply_defaults()
    normalized = check_json(dict(bound.arguments))
    return normalized, literal_for_transport(tuple(bound.args))


def from_literal(task, text):
    args = parse_literal(text)
    if type(args) is not tuple:
        raise ValueError('base_positional_tuple')
    bound = signature(task).bind(*args)
    bound.apply_defaults()
    return check_json(dict(bound.arguments))


def observation(result):
    if not result.get('native_checked'):
        return None
    if result['status'] == 'ok':
        return {'status': 'ok', 'value': check_json(parse_literal(result['output_repr'], output=True))}
    if result['status'] == 'exception':
        return {'status': 'exception', 'exception_type': result['exception_type']}
    return None
