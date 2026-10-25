"""Adapt source/spec/public asserts without importing a benchmark/evaluator loader."""
import argparse
import ast
import json
from pathlib import Path

NORMALIZED_COMPARATOR = '''def _heldout_same(x, y, atol):
    import math
    num = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)
    if num(x) and num(y) and (isinstance(x, float) or isinstance(y, float)):
        return math.isclose(x, y, rel_tol=1e-6, abs_tol=atol or 1e-6)
    if isinstance(x, (list, tuple)) and isinstance(y, (list, tuple)) and len(x) == len(y):
        return type(x) == type(y) and all(_heldout_same(a, b, atol) for a, b in zip(x, y))
    return x == y
'''


def adapt(source, entry, public_asserts, case_id, spec=None):
    examples, unsupported = [], []
    tree = ast.parse(public_asserts)
    helpers = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_heldout_same']
    normalized_comparator = bool(helpers) and len(helpers) == 1 and ast.dump(helpers[0]) == ast.dump(ast.parse(NORMALIZED_COMPARATOR).body[0])
    direct = []
    def collect(body):
        for node in body:
            if isinstance(node, ast.Assert): direct.append(node)
            elif normalized_comparator and node is helpers[0]: continue
            elif (isinstance(node, ast.FunctionDef) and node.name == 'check' and not node.decorator_list
                  and len(node.args.args) == 1 and node.args.args[0].arg == 'candidate'
                  and not node.args.defaults and not node.args.vararg and not node.args.kwarg and not node.args.kwonlyargs):
                allowed = lambda child: isinstance(child, (ast.Assert, ast.Pass)) or (isinstance(child, ast.Expr) and isinstance(child.value, ast.Constant) and isinstance(child.value.value, str))
                if all(allowed(child) for child in node.body):
                    direct.extend(child for child in node.body if isinstance(child, ast.Assert))
                else:
                    unsupported.extend(f'L{n.lineno}:unsupported_check_wrapper' for n in ast.walk(node) if isinstance(n, ast.Assert))
            elif isinstance(node, ast.Pass) or (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)):
                continue
            elif isinstance(node, ast.If) and isinstance(node.test, ast.Constant) and node.test.value is False and not node.orelse:
                unsupported.extend(f'L{n.lineno}:controlled_or_nested_assert' for n in ast.walk(node) if isinstance(n, ast.Assert))
            elif (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name)
                  and node.value.func.id == 'check' and len(node.value.args) == 1 and not node.value.keywords
                  and isinstance(node.value.args[0], ast.Name) and node.value.args[0].id in (entry, 'candidate')):
                continue
            else:
                # General module statements can rebind the PUT or alter whether later assertions execute.
                raise ValueError('unsupported_public_test_module_statement:' + type(node).__name__)
    collect(tree.body)
    for n in direct:
        test = n.test
        if (normalized_comparator and isinstance(test, ast.Call) and isinstance(test.func, ast.Name)
                and test.func.id == '_heldout_same' and len(test.args) == 3 and not test.keywords):
            # The original comparator remains the evaluation policy; only literal public examples are extracted.
            try: ast.literal_eval(test.args[2])
            except (TypeError, ValueError): unsupported.append(f'L{n.lineno}:nonliteral_tolerance'); continue
            test = ast.Compare(left=test.args[0], ops=[ast.Eq()], comparators=[test.args[1]])
        if not isinstance(test, ast.Compare) or len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq):
            unsupported.append(f'L{n.lineno}:non_literal_equality'); continue
        call = test.left
        if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name) or call.func.id not in (entry, 'candidate') or call.keywords:
            unsupported.append(f'L{n.lineno}:non_direct_positional_call'); continue
        try:
            args = tuple(ast.literal_eval(a) for a in call.args)
            expected = ast.literal_eval(test.comparators[0])
        except (ValueError, TypeError):
            unsupported.append(f'L{n.lineno}:non_literal_input_or_expected'); continue
        item = dict(arguments=repr(args), expected=repr(expected))
        if item not in examples: examples.append(item)
    if not examples: raise ValueError('no_supported_public_examples:' + repr(unsupported))
    if len(examples) > 6: raise ValueError('public_example_cap:choose_frozen_visible_subset_explicitly')
    request = dict(case_id=str(case_id), source=source, entry=entry, public_examples=examples)
    if spec is not None: request['spec'] = spec
    return request, unsupported


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--public-asserts', type=Path, required=True)
    p.add_argument('--spec', type=Path)
    p.add_argument('--entry', required=True)
    p.add_argument('--case-id', required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    request, unsupported = adapt(a.source.read_text(), a.entry, a.public_asserts.read_text(), a.case_id,
                                 a.spec.read_text() if a.spec else None)
    from .deep_run import validate_request
    validate_request(request)
    with a.out.open('x') as stream: json.dump(request, stream, indent=2)
    print(json.dumps(dict(examples=len(request['public_examples']), unsupported_asserts=unsupported)))


if __name__ == '__main__': main()
