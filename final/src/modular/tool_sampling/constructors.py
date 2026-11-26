"""Hypothesis and allpairspy constructors without PUT or reference access."""
import ast
import time

from ..common.predicates import expression
from .membership import evaluate


def bound_value(value, arguments):
    if value is None or type(value) in (int, float):
        return value
    tree = expression(value, arguments)
    allowed = (ast.Expression, ast.Constant, ast.Name, ast.Load, ast.BinOp, ast.Add, ast.Sub,
               ast.UnaryOp, ast.USub, ast.UAdd, ast.Call)
    if any(not isinstance(node, allowed) for node in ast.walk(tree)):
        raise ValueError('unsupported_strategy_bound')
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and (not isinstance(node.func, ast.Name) or node.func.id != 'len'
                or len(node.args) != 1 or not isinstance(node.args[0], ast.Name)
                or node.args[0].id not in arguments or node.keywords):
            raise ValueError('unsupported_strategy_bound')
    return eval(compile(tree, '<strategy-bound>', 'eval'), {'__builtins__': {}, 'len': len}, arguments)


def strategy(descriptor, arguments, depth=0):
    from hypothesis import strategies as st
    if not isinstance(descriptor, dict) or depth > 8:
        raise ValueError('strategy_descriptor_required')
    kind = descriptor.get('kind')
    allowed = {'kind', 'min', 'max'} if kind in {'int', 'float'} else {'kind'}
    if kind == 'sampled':
        allowed |= {'values'}
    if kind in {'str', 'list'}:
        allowed |= {'min_size', 'max_size'}
    if kind == 'str':
        allowed |= {'alphabet'}
    if kind == 'list':
        allowed |= {'elements'}
    if set(descriptor) - allowed:
        raise ValueError('unsupported_strategy_fields')
    if kind in {'int', 'float'}:
        low = bound_value(descriptor.get('min'), arguments)
        high = bound_value(descriptor.get('max'), arguments)
        if kind == 'int' and any(value is not None and type(value) is not int for value in (low, high)):
            raise ValueError('integer_bounds_required')
        if kind == 'int':
            return st.integers(min_value=low, max_value=high)
        return st.floats(min_value=low, max_value=high, allow_nan=False, allow_infinity=False)
    if kind == 'bool':
        return st.booleans()
    if kind == 'sampled':
        if not isinstance(descriptor.get('values'), list) or not 1 <= len(descriptor['values']) <= 1000:
            raise ValueError('bounded_nonempty_values_required')
        return st.sampled_from(descriptor['values'])
    if kind in {'str', 'list'}:
        low = bound_value(descriptor.get('min_size', 0), arguments)
        high = bound_value(descriptor.get('max_size'), arguments)
        if type(low) is not int or type(high) is not int or not 0 <= low <= high <= 1000:
            raise ValueError('explicit_bounded_sizes_required')
        if kind == 'str':
            alphabet = descriptor.get('alphabet')
            return st.text(min_size=low, max_size=high, **({'alphabet': alphabet} if alphabet is not None else {}))
        return st.lists(strategy(descriptor['elements'], arguments, depth + 1), min_size=low, max_size=high)
    raise ValueError('unsupported_strategy_kind:' + str(kind))


class SamplingStopped(Exception):
    pass


def sample_hypothesis(ledger, *, draws, seed, seconds, predicate=None, source=None):
    from hypothesis import given, seed as hypothesis_seed, settings, Phase, HealthCheck, strategies as st
    from hypothesis.errors import InvalidArgument, Unsatisfiable, FailedHealthCheck
    start = time.monotonic()
    receipt = {'tool': 'hypothesis', 'seed': seed, 'draw_budget': draws, 'draws': 0, 'status': 'complete'}

    @st.composite
    def arguments(draw):
        values = {}
        for name in ledger.builder.signature.parameters:
            values[name] = draw(strategy(ledger.model['strategies'][name], values))
        return values

    @hypothesis_seed(seed)
    @settings(max_examples=draws, database=None, deadline=None, phases=(Phase.generate,),
              suppress_health_check=list(HealthCheck))
    @given(arguments())
    def collect(values):
        if time.monotonic() - start >= seconds:
            raise SamplingStopped()
        provenance = {'tool': 'hypothesis', 'seed': seed, 'draw_index': receipt['draws'], **(source or {})}
        receipt['draws'] += 1
        row = ledger.add({'arguments': values}, provenance)
        if predicate and row.get('domain') == 'true':
            try:
                if evaluate(predicate, values):
                    receipt['witness'] = row['dedup_group']
            except Exception:
                pass
    try:
        collect()
    except SamplingStopped:
        receipt['status'] = 'budget_exhausted'
    except (ValueError, TypeError, KeyError, NameError, SyntaxError,
            InvalidArgument, Unsatisfiable, FailedHealthCheck) as exc:
        receipt.update(status='unsupported', detail=type(exc).__name__ + ':' + str(exc))
    receipt['seconds'] = time.monotonic() - start
    return receipt


def plan_combinations(ledger, *, rows, draws_per_row, seed, seconds):
    from allpairspy import AllPairs
    start = time.monotonic()
    factors = ledger.model['factors']
    names = list(factors)
    results = []
    if not names:
        return {'tool': 'allpairspy', 'status': 'no_factors', 'results': [], 'seconds': time.monotonic() - start}
    # No feasibility filter: partial rows cannot prove numerical impossibility.
    # Native realization below verifies each full row; failures remain visible.
    levels = [list(factors[name]) for name in names]
    combinations = ([level] for level in levels[0]) if len(names) == 1 else AllPairs(levels)
    for index, values in enumerate(combinations):
        if index >= rows or time.monotonic() - start >= seconds:
            break
        coordinates = dict(zip(names, values))
        predicates = [factors[name][level] for name, level in coordinates.items()]
        query = ' and '.join(f'({item})' for item in [ledger.model['domain'], *predicates])
        row_id = 'row_' + str(index)
        receipt = sample_hypothesis(ledger, draws=draws_per_row, seed=seed + index,
                                    seconds=max(.001, seconds - (time.monotonic() - start)), predicate=query,
                                    source={'planner_row_id': row_id, 'planner_levels': coordinates})
        result = {'planner_row_id': row_id, 'levels': coordinates, 'sampling': receipt,
                  'status': 'realized' if receipt.get('witness') else 'unknown'}
        results.append(result)
    return {'tool': 'allpairspy', 'status': 'complete' if len(results) < rows else 'budget_limited',
            'results': results, 'seconds': time.monotonic() - start}
