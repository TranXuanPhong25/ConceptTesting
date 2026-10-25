"""Observed type profiles and explicit finite SEARCH bounds, not validity rules."""
import ast
import inspect


def profiles(examples):
    def infer(values, depth=0):
        kinds = {type(v) for v in values}
        if len(kinds) != 1 or depth > 4:
            raise ValueError('mixed_or_deep_input_profile')
        kind = type(values[0])
        if kind in (int, bool):
            return {'kind': kind.__name__}
        if kind is str:
            observed = {ord(c) for v in values for c in v}
            alphabet = set(observed)
            for lo, hi in ((48,57), (65,90), (97,122)):
                if any(lo <= c <= hi for c in observed):
                    alphabet.update(range(lo, hi+1))
            return {'kind': 'str', 'alphabet': sorted(alphabet or set(range(97,123))),
                    'origin': 'public_character_categories' if observed else 'empty_example_search_fallback'}
        if kind is list:
            children = [x for v in values for x in v]
            if not children:
                raise ValueError('unknown_empty_list_element_type')
            return {'kind': 'list', 'element': infer(children, depth+1)}
        if kind is tuple:
            if len({len(v) for v in values}) != 1:
                raise ValueError('variable_tuple_arity')
            return {'kind': 'tuple', 'elements': [infer([v[i] for v in values], depth+1) for i in range(len(values[0]))]}
        raise ValueError('unsupported_input_profile:' + kind.__name__)
    if not examples or len({len(v) for v in examples}) != 1:
        raise ValueError('input_arity')
    return [infer([v[i] for v in examples]) for i in range(len(examples[0]))]


def annotation(profile):
    kind = profile['kind']
    if kind in ('int','bool','str'):
        return {'int':int,'bool':bool,'str':str}[kind]
    if kind == 'list':
        return list[annotation(profile['element'])]
    if kind == 'tuple':
        return tuple[tuple(annotation(p) for p in profile['elements'])]
    raise ValueError('profile_annotation')


def signature(source, entry, prof):
    fn = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == entry)
    names = [a.arg for a in fn.args.posonlyargs + fn.args.args]
    if fn.args.vararg or fn.args.kwarg or fn.args.kwonlyargs or fn.args.defaults or len(names) != len(prof):
        raise ValueError('unsupported_entry_signature')
    return inspect.Signature([inspect.Parameter(name, inspect.Parameter.POSITIONAL_OR_KEYWORD,
                            annotation=annotation(p)) for name, p in zip(names, prof)])


def in_domain(value, prof, bounds, depth=0):
    kind = prof['kind']
    if kind == 'int':
        return -bounds['int_bound'] <= value <= bounds['int_bound']
    if kind == 'bool':
        return True
    if kind == 'str':
        return len(value) <= bounds['max_seq_len'] and all(ord(c) in prof['alphabet'] for c in value)
    if kind == 'list':
        limit = bounds['max_seq_len'] if depth == 0 else bounds['nested_max_len']
        return len(value) <= limit and all(in_domain(v, prof['element'], bounds, depth+1) for v in value)
    if kind == 'tuple':
        return len(value) == len(prof['elements']) and all(in_domain(v,p,bounds,depth+1) for v,p in zip(value,prof['elements']))
    return False
