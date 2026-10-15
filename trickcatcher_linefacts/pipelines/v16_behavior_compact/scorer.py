"""Shared output scoring for execution, oracles and offline analyses.

Successful outcomes carry Python values. Non-success outcomes carry an exception
type or timeout status; they never compare equal to successful outputs.
"""
import ast
import math
import json
from pathlib import Path
from numbers import Real

REL_TOL = 1e-6


def task_atols(path=None):
    """Read task tolerance from the same trusted dataset used by the oracle.

    Historical evaluation bundles omit atol; defaulting those bundles to zero
    would silently disagree with the oracle on tasks with absolute tolerance.
    """
    if path is None:
        from .paths import dataset_paths
        path = dataset_paths()['oracle_hep']
    return {int(row['task_id'].split('/')[-1]):row.get('atol',0.0)
            for row in map(json.loads,Path(path).read_text().splitlines())}


def output_equal(left, right, atol=0.0):
    """EvalPlus-style float tolerance, recursively through Python containers."""
    if isinstance(left, Real) and isinstance(right, Real) and (
            isinstance(left, float) or isinstance(right, float)):
        try:
            return left == right or math.isclose(left, right, rel_tol=REL_TOL, abs_tol=atol)
        except (TypeError, ValueError, OverflowError):
            return False
    if isinstance(left, (list, tuple)) or isinstance(right, (list, tuple)):
        return (type(left) is type(right) and len(left) == len(right)
                and all(output_equal(a, b, atol) for a, b in zip(left, right)))
    if isinstance(left, dict) or isinstance(right, dict):
        return (isinstance(left, dict) and isinstance(right, dict)
                and left.keys() == right.keys()
                and all(output_equal(left[k], right[k], atol) for k in left))
    try:
        return bool(left == right)
    except Exception:
        return False


def outcome_equal(left, right, atol=0.0):
    def status(value):
        return 'timeout' if value in ('timeout', 'Timeout', 'TO') else value
    a, b = status(left[0]), status(right[0])
    return a == b and (a != 'ok' or output_equal(left[1], right[1], atol))


def contains_float(value):
    if isinstance(value, float):
        return True
    if isinstance(value, dict):
        return any(contains_float(x) for x in value.values())
    return isinstance(value, (list, tuple)) and any(contains_float(x) for x in value)


def assertion_code(source):
    """Route equality inside an assertion through the shared comparator.

    Other predicates retain Python semantics. Chained comparisons preserve
    short-circuiting and evaluate intermediate operands only once.
    """
    class Equality(ast.NodeTransformer):
        counter = 0
        in_assertion = False

        def visit_Assert(self, node):
            previous = self.in_assertion
            self.in_assertion = True
            node.test = self.visit(node.test)
            self.in_assertion = previous
            return node

        def visit_Compare(self, node):
            if not self.in_assertion:
                return node
            # Arguments and expected-value expressions retain their own Python
            # semantics. Tolerance must never change the constructed input.
            if len(node.ops) > 1 and any(isinstance(op, (ast.Eq, ast.NotEq)) for op in node.ops):
                parts = []
                left = node.left
                for index, (op, right) in enumerate(zip(node.ops, node.comparators)):
                    if index < len(node.ops)-1:
                        name = '__fair_comparison_' + str(self.counter)
                        self.counter += 1
                        operand = ast.NamedExpr(target=ast.Name(id=name, ctx=ast.Store()), value=right)
                        next_left = ast.Name(id=name, ctx=ast.Load())
                    else:
                        operand = right
                        next_left = right
                    part = ast.Compare(left=left, ops=[op], comparators=[operand])
                    parts.append(self.visit_Compare(part))
                    left = next_left
                return ast.copy_location(ast.BoolOp(op=ast.And(), values=parts), node)
            if len(node.ops) == 1 and isinstance(node.ops[0], (ast.Eq, ast.NotEq)):
                call = ast.Call(func=ast.Name(id='__fair_equal__', ctx=ast.Load()),
                                args=[node.left, node.comparators[0]], keywords=[])
                return ast.copy_location(ast.UnaryOp(op=ast.Not(), operand=call)
                                         if isinstance(node.ops[0], ast.NotEq) else call, node)
            return node
    return compile(ast.fix_missing_locations(Equality().visit(ast.parse(source))), '<assertion>', 'exec')


def arm_metrics(rows):
    """Own-expected-value metrics; counts and sample detection are both explicit."""
    result = {}
    for arm in sorted({r['arm'] for r in rows}):
        group = [r for r in rows if r['arm'] == arm]
        assertions = [a for r in group for a in r['asserts']]
        failing = [a for a in assertions if a['put'] != 'ok']
        correct = sum(a.get('contract_valid', False) and a['canon'] == 'ok' for a in failing)
        di = sum(i.get('d_i', False) for r in group for i in r.get('input_metrics', []))
        dio = sum(a.get('d_io', False) for a in assertions)
        result[arm] = dict(D_I=di, D_IO=dio,
                           D_I_samples=sum(any(i.get('d_i', False) for i in r.get('input_metrics', [])) for r in group),
                           D_IO_samples=sum(any(a.get('d_io', False) for a in r['asserts']) for r in group),
                           correct_failing=correct, failing=len(failing),
                           precision=correct / len(failing) if failing else None,
                           false_alarms=len(failing)-correct,
                           false_alarm_rate=(len(failing)-correct) / len(failing) if failing else None)
    return result
