"""Compile a safe subset of trusted admission clauses, never model code."""
import ast
import hashlib
import textwrap

from ..common.predicates import expression, FUNCTIONS

TYPE_HELPERS = {'int':'is_int', 'float':'is_float', 'bool':'is_bool', 'str':'is_str', 'list':'is_list'}


def call(name, *arguments):
    return ast.Call(func=ast.Name(id=name, ctx=ast.Load()), args=list(arguments), keywords=[])


def numeric_projection(node, names):
    """Recognize only float(str(parameter).replace(',', '.')), exactly."""
    if (not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != 'float'
            or len(node.args) != 1 or node.keywords):
        return None
    replace = node.args[0]
    if (not isinstance(replace, ast.Call) or not isinstance(replace.func, ast.Attribute)
            or replace.func.attr != 'replace' or replace.keywords or len(replace.args) != 2
            or any(not isinstance(item, ast.Constant) for item in replace.args)
            or [item.value for item in replace.args] != [',', '.']):
        return None
    convert = replace.func.value
    if (isinstance(convert, ast.Call) and isinstance(convert.func, ast.Name) and convert.func.id == 'str'
            and len(convert.args) == 1 and not convert.keywords
            and isinstance(convert.args[0], ast.Name) and convert.args[0].id in names):
        return convert.args[0]
    return None


class TrustedExpressions(ast.NodeTransformer):
    def __init__(self, known_types):
        self.known_types = known_types

    def visit_Compare(self, node):
        if (len(node.ops) > 1 and all(isinstance(op, ast.Eq) for op in node.ops)
                and isinstance(node.comparators[-1], ast.Name) and node.comparators[-1].id in TYPE_HELPERS):
            operands = [node.left, *node.comparators[:-1]]
            if all(isinstance(item, ast.Call) and isinstance(item.func, ast.Name) and item.func.id == 'type'
                   and len(item.args) == 1 and not item.keywords for item in operands):
                helper = TYPE_HELPERS[node.comparators[-1].id]
                return ast.BoolOp(op=ast.And(), values=[call(helper, item.args[0]) for item in operands])
        if (isinstance(node.left, ast.Call) and isinstance(node.left.func, ast.Name)
                and node.left.func.id == 'type' and len(node.left.args) == 1 and not node.left.keywords
                and len(node.ops) == 1 and isinstance(node.ops[0], (ast.Eq, ast.NotEq))
                and isinstance(node.comparators[0], ast.Name) and node.comparators[0].id in TYPE_HELPERS):
            value = call(TYPE_HELPERS[node.comparators[0].id], node.left.args[0])
            return ast.UnaryOp(op=ast.Not(), operand=value) if isinstance(node.ops[0], ast.NotEq) else value
        return self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id == 'isinstance' and len(node.args) == 2 and not node.keywords:
            tags = node.args[1].elts if isinstance(node.args[1], ast.Tuple) else [node.args[1]]
            if not tags or any(not isinstance(tag, ast.Name) or tag.id not in TYPE_HELPERS for tag in tags):
                raise ValueError('unsupported_trusted_instance_types')
            values = [call('is_instance', node.args[0], ast.Constant(value=tag.id)) for tag in tags]
            return values[0] if len(values) == 1 else ast.BoolOp(op=ast.Or(), values=values)
        if (isinstance(node.func, ast.Attribute) and node.func.attr == 'issubset' and len(node.args) == 1
                and not node.keywords and isinstance(node.func.value, ast.Call)
                and isinstance(node.func.value.func, ast.Name) and node.func.value.func.id == 'set'
                and len(node.func.value.args) == 1 and not node.func.value.keywords):
            alphabet = ast.literal_eval(node.args[0])
            value = node.func.value.args[0]
            if not isinstance(value, ast.Name) or self.known_types.get(value.id) != {'str'}:
                raise ValueError('trusted_alphabet_requires_string_guard')
            if not isinstance(alphabet, (set, tuple, list)) or any(type(item) is not str or len(item) != 1 for item in alphabet):
                raise ValueError('unsupported_trusted_alphabet')
            return call('chars_in', value, ast.Constant(value=''.join(sorted(alphabet))))
        if isinstance(node.func, ast.Name) and node.func.id == 'all' and len(node.args) == 1 and not node.keywords:
            generator = node.args[0]
            if isinstance(generator, (ast.GeneratorExp, ast.ListComp)) and len(generator.generators) == 1:
                loop = generator.generators[0]
                if (isinstance(loop.target, ast.Name) and isinstance(loop.iter, ast.Name)
                        and not loop.ifs and not loop.is_async):
                    if loop.target.id in set(TYPE_HELPERS) | set(FUNCTIONS) | {'type', 'isinstance'}:
                        raise ValueError('trusted_quantifier_overwrites_builtin')
                    item = generator.elt
                    if (isinstance(item, ast.Call) and isinstance(item.func, ast.Name) and item.func.id == 'isinstance'
                            and len(item.args) == 2 and not item.keywords and isinstance(item.args[0], ast.Name)
                            and item.args[0].id == loop.target.id):
                        tags = item.args[1].elts if isinstance(item.args[1], ast.Tuple) else [item.args[1]]
                        if tags and all(isinstance(tag, ast.Name) and tag.id in TYPE_HELPERS for tag in tags):
                            return call('all_instance', loop.iter, ast.Constant(value=','.join(tag.id for tag in tags)))
                    transformed = TrustedExpressions({}).visit(item)
                    if (isinstance(transformed, ast.Call) and isinstance(transformed.func, ast.Name)
                            and transformed.func.id in TYPE_HELPERS.values() and len(transformed.args) == 1
                            and isinstance(transformed.args[0], ast.Name) and transformed.args[0].id == loop.target.id):
                        tag = next(name for name, helper in TYPE_HELPERS.items() if helper == transformed.func.id)
                        return call('all_type', loop.iter, ast.Constant(value=tag))
            if (isinstance(generator, ast.GeneratorExp) and len(generator.generators) == 1
                    and isinstance(generator.elt, ast.Compare) and len(generator.elt.ops) == 2
                    and all(isinstance(op, ast.LtE) for op in generator.elt.ops)):
                loop = generator.generators[0]
                predicate = generator.elt
                if (isinstance(loop.target, ast.Name) and isinstance(loop.iter, ast.Name)
                        and not loop.ifs and not loop.is_async and isinstance(predicate.comparators[0], ast.Name)
                        and predicate.comparators[0].id == loop.target.id):
                    lower, upper = ast.literal_eval(predicate.left), ast.literal_eval(predicate.comparators[1])
                    if type(lower) not in (int, float) or type(upper) not in (int, float):
                        raise ValueError('trusted_range_requires_numeric_constants')
                    return call('all_in_range', loop.iter, ast.Constant(value=lower), ast.Constant(value=upper))
        return self.generic_visit(node)


def finite_numeric_string_contract(body, names):
    """One exact pure conversion idiom; no general assignment/import execution."""
    if len(body) != 3 or not isinstance(body[0], ast.Try) or not isinstance(body[1], ast.Import) or not isinstance(body[2], ast.Assert):
        return None
    branch = body[0]
    if len(branch.body) != 2 or not isinstance(branch.body[0], ast.Assert) or not isinstance(branch.body[1], ast.Assign):
        return None
    assignment = branch.body[1]
    if len(assignment.targets) != 1 or not isinstance(assignment.targets[0], ast.Name):
        return None
    name = assignment.targets[0].id
    if name not in names:
        return None
    template = ast.parse(f'''try:
    assert isinstance({name}, str)
    {name} = float({name})
except:
    raise Exception("invalid inputs")
import math
assert not (math.isinf({name}) or math.isnan({name})), "invalid inputs"
''')
    # Assertion/raise messages do not change admitted inputs; every executable
    # node and exception handler must otherwise match this reviewed idiom.
    import copy
    actual = ast.Module(body=copy.deepcopy(body), type_ignores=[])
    for tree in (actual, template):
        for node in ast.walk(tree):
            if isinstance(node, ast.Assert):
                node.msg = None
            if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
                if any(not isinstance(item, ast.Constant) for item in node.exc.args) or node.exc.keywords:
                    return None
                node.exc.args = []
    return name if ast.dump(actual, include_attributes=False) == ast.dump(template, include_attributes=False) else None


def collect_type_guards(node, known, admission_types):
    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And):
        for child in node.values:
            collect_type_guards(child, known, admission_types)
    elif (isinstance(node, ast.Compare) and isinstance(node.left, ast.Call)
          and isinstance(node.left.func, ast.Name) and node.left.func.id == 'type'
          and len(node.left.args) == 1 and isinstance(node.left.args[0], ast.Name)
          and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq)
          and isinstance(node.comparators[0], ast.Name) and node.comparators[0].id in TYPE_HELPERS):
        known[node.left.args[0].id] = {node.comparators[0].id}
        admission_types[node.left.args[0].id] = node.comparators[0].id
    elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'isinstance'
          and len(node.args) == 2 and isinstance(node.args[0], ast.Name)):
        tags = node.args[1].elts if isinstance(node.args[1], ast.Tuple) else [node.args[1]]
        if tags and all(isinstance(tag, ast.Name) and tag.id in TYPE_HELPERS for tag in tags):
            known[node.args[0].id] = {tag.id for tag in tags}


def compile_domain(contract, names):
    names = set(names)
    record = {'source': 'trusted_input_admission', 'source_sha256': hashlib.sha256(contract.encode()).hexdigest(),
              'status': 'supported', 'expression': None, 'unsupported': [],
              'admission_types': {name:'any' for name in sorted(names)}}
    if not contract.strip():
        return {**record, 'status': 'not_provided'}
    if len(contract) > 16000:
        return {**record, 'status': 'unsupported', 'unsupported': ['trusted_contract_size_limit']}
    try:
        reserved = set(FUNCTIONS) | set(TYPE_HELPERS) | {'type','isinstance','set','all','range','str','Exception','ValueError','math'}
        if names & reserved:
            raise ValueError('trusted_parameter_overwrites_builtin_or_helper:' + ','.join(sorted(names & reserved)))
        tree = ast.parse(textwrap.dedent(contract))
        if sum(1 for _ in ast.walk(tree)) > 512:
            raise ValueError('trusted_contract_node_limit')
        body = tree.body
        finite_string = finite_numeric_string_contract(body, names)
        if finite_string is not None:
            record['expression'] = ast.unparse(call('is_finite_numeric_string', ast.Name(id=finite_string, ctx=ast.Load())))
            return record
        clauses, known_types = [], {}
        for statement in body:
            if isinstance(statement, ast.Assert):
                collect_type_guards(statement.test, known_types, record['admission_types'])
                transformed = TrustedExpressions(known_types).visit(statement.test)
                ast.fix_missing_locations(transformed)
                text = ast.unparse(transformed)
                expression(text, names)
                clauses.append(text)
            elif isinstance(statement, ast.Try):
                handler_ok = (len(statement.handlers) == 1 and isinstance(statement.handlers[0].type, ast.Name)
                    and statement.handlers[0].type.id == 'ValueError' and statement.handlers[0].name is None
                    and len(statement.handlers[0].body) == 1 and isinstance(statement.handlers[0].body[0], ast.Raise)
                    and statement.handlers[0].body[0].cause is None and not statement.orelse and not statement.finalbody)
                raised = statement.handlers[0].body[0].exc if handler_ok else None
                handler_ok = (handler_ok and isinstance(raised, ast.Call) and isinstance(raised.func, ast.Name)
                              and raised.func.id in {'Exception', 'ValueError'} and not raised.keywords
                              and len(raised.args) <= 1 and all(isinstance(item, ast.Constant) for item in raised.args))
                projections = [numeric_projection(item.value, names) if isinstance(item, ast.Expr) else None for item in statement.body]
                if not handler_ok or not projections or any(item is None for item in projections):
                    raise ValueError('unsupported_trusted_try')
                clauses.extend(ast.unparse(call('is_numeric', node)) for node in projections)
            else:
                raise ValueError('unsupported_trusted_statement:' + type(statement).__name__)
        if not clauses:
            raise ValueError('empty_trusted_assertions')
        record['expression'] = ' and '.join('(' + text + ')' for text in clauses)
        expression(record['expression'], names)
    except (ValueError, SyntaxError, TypeError, RecursionError) as exc:
        record.update(status='unsupported', expression=None, unsupported=[str(exc)])
    return record
