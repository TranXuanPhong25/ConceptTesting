"""Restricted expression -> typed predicate IR; no eval, prose inference or repair."""
import ast
import copy

from .predicates import validate


def normalize_aliases(node, changes=None, path='$', depth=0):
    if depth > 24 or not isinstance(node, dict):
        raise ValueError('predicate_depth_or_type')
    changes = [] if changes is None else changes
    out = copy.deepcopy(node)
    for key, value in list(out.items()):
        if isinstance(value, dict):
            out[key] = normalize_aliases(value, changes, path+'.'+key, depth+1)
        elif isinstance(value, list):
            out[key] = [normalize_aliases(v, changes, f'{path}.{key}[{i}]', depth+1)
                        if isinstance(v, dict) else v for i, v in enumerate(value)]
    op = out.get('op')
    if op in ('gt', 'ge', 'ne'):
        if set(out) != {'op', 'left', 'right'}:
            raise ValueError('predicate_fields')
        changes.append({'path': path, 'rewrite': op})
        if op == 'ne':
            return {'op': 'not', 'value': dict(out, op='eq')}
        return {'op': 'lt' if op == 'gt' else 'le', 'left': out['right'], 'right': out['left']}
    return out


def compile_condition(text, arity, *, event=False):
    if not isinstance(text, str) or not 1 <= len(text) <= 1600:
        raise ValueError('condition_string_size')
    root = ast.parse(text, mode='eval').body
    if sum(1 for _ in ast.walk(root)) > 128:
        raise ValueError('condition_ast_size')
    names = {f'arg{i}': i for i in range(arity)}

    def compile_node(node):
        if isinstance(node, ast.Constant) and type(node.value) in (bool, int, str):
            return {'op': 'literal', 'value': node.value}
        if isinstance(node, ast.Name) and node.id in names:
            return {'op': 'input', 'arg': names[node.id]}
        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.Not):
                return {'op': 'not', 'value': compile_node(node.operand)}
            if isinstance(node.op, (ast.USub, ast.UAdd)) and isinstance(node.operand, ast.Constant) and type(node.operand.value) is int:
                return {'op': 'literal', 'value': -node.operand.value if isinstance(node.op, ast.USub) else node.operand.value}
        if isinstance(node, ast.BinOp) and type(node.op) in (ast.Add, ast.Sub, ast.Mod):
            return {'op': {ast.Add: 'add', ast.Sub: 'sub', ast.Mod: 'mod'}[type(node.op)],
                    'left': compile_node(node.left), 'right': compile_node(node.right)}
        if isinstance(node, ast.BoolOp) and type(node.op) in (ast.And, ast.Or):
            return {'op': 'and' if isinstance(node.op, ast.And) else 'or',
                    'items': [compile_node(v) for v in node.values]}
        if isinstance(node, ast.Compare):
            parts = []
            previous = node.left
            mapping = {ast.Eq: 'eq', ast.NotEq: 'ne', ast.Lt: 'lt', ast.LtE: 'le', ast.Gt: 'gt', ast.GtE: 'ge'}
            for operator, right in zip(node.ops, node.comparators):
                if type(operator) not in mapping:
                    raise ValueError('condition_comparison')
                parts.append({'op': mapping[type(operator)], 'left': compile_node(previous), 'right': compile_node(right)})
                previous = right
            return parts[0] if len(parts) == 1 else {'op': 'and', 'items': parts}
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and not node.keywords and len(node.args) == 1:
            if node.func.id in ('len', 'has_duplicate', 'all_distinct'):
                return {'op': node.func.id, 'value': compile_node(node.args[0])}
            if event and node.func.id == 'local' and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                return {'op': 'local', 'name': node.args[0].value}
        raise ValueError('condition_unsupported_syntax:'+type(node).__name__)

    changes = []
    ir = normalize_aliases(compile_node(root), changes)
    validate(ir, arity, allow_local=event)
    return ir, changes


def check_types(node, profiles, *, event=False):
    """Types observed in public examples define support, not normative validity."""
    validate(node, len(profiles), allow_local=event)

    def require(actual, kinds, label):
        if actual['kind'] not in kinds and not (event and actual['kind'] == 'unknown'):
            raise ValueError('predicate_type:'+label+':'+actual['kind'])

    def infer(n):
        op = n['op']
        if op == 'literal':
            return {'kind': type(n['value']).__name__}
        if op == 'input':
            return strip_profile(profiles[n['arg']])
        if op == 'local':
            return {'kind': 'unknown'}
        if op in ('and', 'or', 'not'):
            children = n['items'] if op != 'not' else [n['value']]
            for child in children:
                require(infer(child), ('bool',), 'boolean_operand')
            return {'kind': 'bool'}
        if op in ('len', 'has_duplicate', 'all_distinct'):
            value = infer(n['value'])
            require(value, ('str', 'list', 'tuple'), 'sequence_operand')
            if op != 'len' and value['kind'] not in ('str', 'unknown'):
                def hashable(t):
                    return t['kind'] in ('int', 'bool', 'str') or t['kind'] == 'tuple' and hashable(t['element'])
                if not hashable(value['element']):
                    raise ValueError('predicate_type:unhashable_duplicate_element')
            return {'kind': 'int' if op == 'len' else 'bool'}
        if op in ('add', 'sub', 'mod'):
            require(infer(n['left']), ('int',), 'arithmetic_left')
            require(infer(n['right']), ('int',), 'arithmetic_right')
            if op == 'mod' and not event and not (n['right']['op'] == 'literal' and type(n['right']['value']) is int and n['right']['value'] > 0):
                raise ValueError('predicate_type:positive_literal_modulus_required')
            return {'kind': 'int'}
        if op in ('eq', 'lt', 'le'):
            left, right = infer(n['left']), infer(n['right'])
            if left['kind'] == 'unknown' or right['kind'] == 'unknown':
                return {'kind': 'bool'}  # Native event evaluation must resolve unknown locals.
            if left != right:
                raise ValueError('predicate_type:incompatible_'+left['kind']+'_'+right['kind'])
            if op != 'eq':
                require(left, ('int', 'str'), 'ordered_operand')
            return {'kind': 'bool'}
        # These inherited concrete-only operators are not advertised to this writer.
        if event and op in ('index', 'count_distinct'):
            return {'kind': 'unknown'}
        raise ValueError('predicate_backend_unsupported:'+op)

    result = infer(node)
    if result['kind'] != 'bool':
        raise ValueError('predicate_type:boolean_root_required')
    return result


def strip_profile(profile):
    result = {'kind': profile['kind']}
    if 'element' in profile:
        result['element'] = strip_profile(profile['element'])
    return result
