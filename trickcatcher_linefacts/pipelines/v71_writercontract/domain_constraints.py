"""Closed public-spec constraint grammar. No PUT, private labels or text eval.

Extraction is deliberately explicit: unsupported lines make the domain incomplete.
"""
import ast
import functools
import hashlib
import json
import re

import z3

from .predicates import SymbolicString, symbolic_equal


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def _term(node, names, aliases, element_args):
    if isinstance(node, ast.Constant) and type(node.value) is int and abs(node.value) <= 10**12:
        return {'kind': 'constant', 'value': node.value}
    if isinstance(node, ast.Name):
        if node.id in names:
            return {'kind': 'argument', 'arg': names[node.id]}
        if node.id in aliases:
            return aliases[node.id]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and not node.keywords:
        if node.func.id == 'len' and len(node.args) == 1 and isinstance(node.args[0], ast.Name) and node.args[0].id in names:
            return {'kind': 'length', 'arg': names[node.args[0].id]}
        if node.func.id in ('min', 'max') and 1 <= len(node.args) <= 8:
            return {'kind': node.func.id, 'items': [_term(x, names, aliases, element_args) for x in node.args]}
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id in names and isinstance(node.slice, ast.Name) and node.slice.id == 'i':
        index = names[node.value.id]
        element_args.add(index)
        return {'kind': 'element', 'arg': index}
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return {'kind': 'multiply', 'left': {'kind': 'constant', 'value': -1},
                'right': _term(node.operand, names, aliases, element_args)}
    if isinstance(node, ast.BinOp):
        if isinstance(node.op, ast.Pow) and isinstance(node.left, ast.Constant) and isinstance(node.right, ast.Constant):
            a, b = node.left.value, node.right.value
            if type(a) is int and type(b) is int and 0 <= a <= 10**6 and 0 <= b <= 12 and a**b <= 10**12:
                return {'kind': 'constant', 'value': a**b}
        ops = {ast.Add: 'add', ast.Sub: 'subtract', ast.Mult: 'multiply'}
        if type(node.op) in ops:
            return {'kind': ops[type(node.op)], 'left': _term(node.left, names, aliases, element_args),
                    'right': _term(node.right, names, aliases, element_args)}
    raise ValueError('unsupported_numeric_term')


def _numeric(line, names):
    # ^ has mathematical power meaning only for explicit integer literals.
    text = re.sub(r'(\b\d+)\s*\^\s*(\d+\b)', r'\1**\2', line)
    text = re.sub(r'\b([A-Za-z_]\w*)\.length\b', r'len(\1)', text)
    expression = ast.parse(text, mode='eval').body
    if not isinstance(expression, ast.Compare) or sum(1 for _ in ast.walk(expression)) > 128:
        raise ValueError('numeric_comparison_required')
    operands = [expression.left, *expression.comparators]
    aliases = {}
    # Only aliases explicitly asserted by equality in this same constraint line.
    for left, op, right in zip(operands, expression.ops, operands[1:]):
        if isinstance(op, ast.Eq):
            for a, b in ((left, right), (right, left)):
                if isinstance(a, ast.Name) and a.id not in names:
                    bound = _term(b, names, {}, set())
                    if bound['kind'] == 'length':
                        aliases[a.id] = bound
    comparisons = []
    elements = set()
    mapping = {ast.Lt: 'lt', ast.LtE: 'le', ast.Eq: 'eq', ast.Gt: 'gt', ast.GtE: 'ge'}
    for left, op, right in zip(operands, expression.ops, operands[1:]):
        if type(op) not in mapping:
            raise ValueError('numeric_comparison_operator')
        comparisons.append({'operator': mapping[type(op)], 'left': _term(left, names, aliases, elements),
                            'right': _term(right, names, aliases, elements)})
    if len(elements) > 1:
        raise ValueError('multiple_element_quantifiers')
    return {'kind': 'numeric', 'comparisons': comparisons,
            'each_arg': next(iter(elements)) if elements else None}


def compile_domain(request):
    from .semantic_contract import specification
    source = request['source']
    fn = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == request['entry'])
    names = {a.arg: i for i, a in enumerate(fn.args.posonlyargs+fn.args.args)}
    spec = specification(request)
    start = re.search(r'(?m)^\s*Constraints:\s*$', spec)
    binding = digest({'source': source, 'entry': request['entry'], 'spec': spec})
    result = {'binding_sha256': binding, 'rules': [], 'unsupported': [], 'status': 'no_explicit_constraints',
              'coverage': 'no_constraints_section','argument_count':len(names),'private_data_used': False}
    if not start:
        return result
    first_line = spec[:start.end()].count('\n')
    rows = spec[start.end():].splitlines()
    for offset, raw in enumerate(rows):
        text = raw.strip()
        if not text:
            continue
        receipt = {'quote': raw, 'line': first_line+offset, 'binding_sha256': binding}
        try:
            if text == 'The input is generated such that:':
                rule = {'kind': 'header'}
            else:
                rule = None
                alphabet = re.fullmatch(r'(.+?) (?:consist|consists) (?:only of lowercase English letters|of digits only)\.', text)
                if alphabet:
                    targets = alphabet.group(1).split(' and ')
                    if any(name not in names for name in targets):
                        raise ValueError('unknown_alphabet_argument')
                    allowed = list(range(97, 123)) if 'lowercase' in text else list(range(48, 58))
                    rule = {'kind': 'alphabet', 'args': [names[name] for name in targets], 'codepoints': allowed}
                shape = re.fullmatch(r'(\w+)\[i\] == \[xi, yi\]', text)
                unique = re.fullmatch(r'All (\w+)\[i\] are unique\.', text)
                boundary = re.fullmatch(r'(\w+)\[i\] lies on the boundary of the square\.', text)
                if shape and shape[1] in names:
                    rule = {'kind': 'point_shape', 'arg': names[shape[1]], 'width': 2}
                if unique and unique[1] in names:
                    rule = {'kind': 'unique', 'arg': names[unique[1]]}
                if boundary and boundary[1] in names:
                    # This exact form requires the explicit square side argument.
                    if 'side' not in names:
                        raise ValueError('unbound_square_side')
                    geometry = 'corners at (0, 0), (0, side), (side, 0), and (side, side)'
                    if geometry not in spec:
                        raise ValueError('unbound_square_geometry')
                    receipt['supporting_quote'] = geometry
                    rule = {'kind': 'square_boundary', 'arg': names[boundary[1]], 'side_arg': names['side']}
                if rule is None:
                    rule = _numeric(text, names)
            result['rules'].append(dict(receipt, rule=rule))
        except (ValueError, SyntaxError, TypeError) as exc:
            result['unsupported'].append(dict(receipt, reason=type(exc).__name__+':'+str(exc)[:100]))
    result['status'] = 'complete' if result['rules'] and not result['unsupported'] else 'incomplete'
    result['coverage'] = 'closed_explicit_grammar' if result['status'] == 'complete' else 'unsupported_or_empty_section'
    result['semantic_scope'] = 'declared_input_constraints_only_not_output_correctness'
    return result


def _value(term, args, elements, symbolic):
    kind = term['kind']
    if kind == 'constant':
        return term['value']
    if kind == 'argument':
        value = args[term['arg']]
        if type(value) is not int and not (symbolic and isinstance(value, z3.ArithRef)):
            raise ValueError('numeric_argument_type')
        return value
    if kind == 'length':
        return len(args[term['arg']])
    if kind == 'element':
        value = elements[term['arg']]
        if type(value) is not int and not (symbolic and isinstance(value, z3.ArithRef)):
            raise ValueError('numeric_element_type')
        return value
    if kind in ('min', 'max'):
        items = [_value(x, args, elements, symbolic) for x in term['items']]
        choose = (lambda a, b: z3.If(a <= b, a, b)) if kind == 'min' else (lambda a, b: z3.If(a >= b, a, b))
        return functools.reduce(choose, items) if symbolic else (min(items) if kind == 'min' else max(items))
    a = _value(term['left'], args, elements, symbolic)
    b = _value(term['right'], args, elements, symbolic)
    return {'add': lambda: a+b, 'subtract': lambda: a-b, 'multiply': lambda: a*b}[kind]()


def constraints(domain, args, *, symbolic=False):
    if len(args)!=domain['argument_count']:
        raise ValueError('domain_argument_count')
    if domain['status'] == 'incomplete':
        raise ValueError('incomplete_input_domain')
    conditions = []
    for row in domain['rules']:
        rule = row['rule'];kind = rule['kind']
        if kind == 'header':
            continue
        if kind == 'numeric':
            index = rule['each_arg']
            contexts = [{}] if index is None else [{index: x} for x in args[index]]
            for elements in contexts:
                for comparison in rule['comparisons']:
                    a = _value(comparison['left'], args, elements, symbolic)
                    b = _value(comparison['right'], args, elements, symbolic)
                    conditions.append({'lt': lambda: a < b, 'le': lambda: a <= b, 'eq': lambda: a == b,
                                       'gt': lambda: a > b, 'ge': lambda: a >= b}[comparison['operator']]())
        elif kind == 'alphabet':
            for index in rule['args']:
                value = args[index]
                if symbolic:
                    if not isinstance(value, SymbolicString):raise ValueError('alphabet_argument_type')
                    conditions.extend(z3.Or(*[x == c for c in rule['codepoints']]) for x in value)
                else:
                    conditions.append(type(value) is str and all(ord(c) in rule['codepoints'] for c in value))
        elif kind == 'point_shape':
            conditions.extend(isinstance(point, (list, tuple)) and len(point) == rule['width'] for point in args[rule['arg']])
        elif kind == 'unique':
            xs = args[rule['arg']]
            conditions.extend(z3.Not(symbolic_equal(xs[i], xs[j])) if symbolic else xs[i] != xs[j]
                              for i in range(len(xs)) for j in range(i))
        elif kind == 'square_boundary':
            side = args[rule['side_arg']]
            for point in args[rule['arg']]:
                if not isinstance(point, (list, tuple)) or len(point) != 2:
                    conditions.append(False);continue
                x, y = point
                bounds = [0 <= x, x <= side, 0 <= y, y <= side]
                edge = [x == 0, y == 0, x == side, y == side]
                conditions.append(z3.And(*bounds, z3.Or(*edge)) if symbolic else all(bounds) and any(edge))
        else:
            raise ValueError('unknown_domain_rule')
    return conditions


def check_domain(domain, args):
    try:
        conditions = constraints(domain, args)
        passed = all(type(value) is bool and value for value in conditions)
        return {'passed': passed, 'status': 'passed_explicit_constraints' if passed else 'violates_explicit_constraints',
                'binding_sha256': domain['binding_sha256'], 'coverage': domain['status']}
    except (ValueError, TypeError, IndexError, KeyError) as exc:
        return {'passed': False, 'status': 'domain_unknown', 'reason': type(exc).__name__+':'+str(exc)[:100],
                'binding_sha256': domain['binding_sha256'], 'coverage': domain['status']}


def public_domain(request):
    domain = compile_domain(request)
    checks = [check_domain(domain, ast.literal_eval(row['arguments'])) for row in request['public_examples']]
    if domain['status'] == 'incomplete' or not all(row['passed'] for row in checks):
        raise ValueError('unsupported_or_inconsistent_public_domain')
    return domain
