"""Real Hypothesis/Z3/allpairspy constructors; no PUT or reference access."""
import ast
import operator
import time

from ..input_buckets.predicates import expression
from .membership import evaluate
from .ledger import error
from .selection import hits


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


def translate(text, types):
    import z3
    if any(kind not in {'int', 'bool'} for kind in types.values()):
        raise ValueError('z3_integer_bool_only')
    variables = {name: z3.Int(name) if kind == 'int' else z3.Bool(name) for name, kind in types.items()}
    tree = expression(text, types)

    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) in (bool, int):
            return z3.BoolVal(node.value) if type(node.value) is bool else z3.IntVal(node.value)
        if isinstance(node, ast.Name) and node.id in variables:
            return variables[node.id]
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in {'is_int', 'is_bool'} and len(node.args) == 1
                and isinstance(node.args[0], ast.Name) and node.args[0].id in variables):
            expected = 'int' if node.func.id == 'is_int' else 'bool'
            return z3.BoolVal(types[node.args[0].id] == expected)
        if isinstance(node, ast.BoolOp):
            values = [visit(item) for item in node.values]
            if not all(z3.is_bool(value) for value in values):
                raise ValueError('boolean_operands_required')
            return (z3.And if isinstance(node.op, ast.And) else z3.Or)(*values)
        if isinstance(node, ast.UnaryOp):
            value = visit(node.operand)
            if isinstance(node.op, ast.Not) and z3.is_bool(value):
                return z3.Not(value)
            if z3.is_int(value) and isinstance(node.op, (ast.USub, ast.UAdd)):
                return -value if isinstance(node.op, ast.USub) else value
            raise ValueError('unsupported_unary_semantics')
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub)):
            left, right = visit(node.left), visit(node.right)
            if not (z3.is_int(left) and z3.is_int(right)):
                raise ValueError('integer_operands_required')
            return left + right if isinstance(node.op, ast.Add) else left - right
        if isinstance(node, ast.Compare):
            parts = []
            left = visit(node.left)
            for op, comparator in zip(node.ops, node.comparators):
                right = visit(comparator)
                if left.sort() != right.sort():
                    raise ValueError('comparison_sort_mismatch')
                operations = {ast.Eq: operator.eq, ast.NotEq: operator.ne,
                              ast.Lt: operator.lt, ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge}
                if type(op) not in operations or (z3.is_bool(left) and not isinstance(op, (ast.Eq, ast.NotEq))):
                    raise ValueError('unsupported_comparison')
                parts.append(operations[type(op)](left, right))
                left = right
            return z3.And(*parts)
        raise ValueError('unsupported_z3_node:' + type(node).__name__)
    formula = visit(tree.body)
    if not z3.is_bool(formula):
        raise ValueError('z3_predicate_must_be_boolean')
    return formula, variables


def solve(ledger, predicate, *, timeout_ms, query_id, source=None):
    import z3
    start = time.monotonic()
    try:
        formula, variables = translate(predicate, ledger.model['types'])
    except (ValueError, SyntaxError, z3.Z3Exception) as exc:
        return {'status': 'unsupported', 'detail': str(exc), 'seconds': time.monotonic() - start}
    solver = z3.Solver()
    solver.set(timeout=timeout_ms, random_seed=0)
    solver.add(formula)
    outcome = solver.check()
    if outcome != z3.sat:
        return {'status': 'unsat' if outcome == z3.unsat else 'unknown',
                'detail': solver.reason_unknown() if outcome == z3.unknown else '',
                'seconds': time.monotonic() - start}
    model = solver.model()
    raw_model = str(model)
    completed = [name for name, variable in variables.items() if model.get_interp(variable.decl()) is None]
    values = {}
    conversion_errors = []
    for name, variable in variables.items():
        # Complete unconstrained inputs explicitly; replay checks the complete call.
        value = model.eval(variable, model_completion=True)
        if ledger.model['types'][name] == 'int' and z3.is_int_value(value):
            values[name] = value.as_long()
        elif ledger.model['types'][name] == 'bool' and (z3.is_true(value) or z3.is_false(value)):
            values[name] = z3.is_true(value)
        else:
            conversion_errors.append(error('P4', 'z3_value_unrepresentable', name + ':' + str(value)))
    provenance = {'tool': 'z3', 'query_id': query_id, 'model_completed_variables': completed, **(source or {})}
    row = ledger.add({'arguments': values, 'model': str(model)} if conversion_errors else {'arguments': values},
                     provenance, errors=conversion_errors, tool_raw=raw_model)
    if not conversion_errors:
        try:
            native_hit = evaluate(predicate, values)
        except Exception:
            native_hit = False
        if row.get('domain') != 'true' or not native_hit:
            mismatch = error('V2', 'z3_semantics_mismatch', predicate)
            row['errors'].append(mismatch)
            row['primary_error'] = row['primary_error'] or mismatch
            row['solver_rejected'] = True
    return {'status': 'rejected' if conversion_errors or row.get('solver_rejected') else 'sat', 'candidate_id': row['candidate_id'],
            'dedup_group': row['dedup_group'], 'seconds': time.monotonic() - start}


def fill_z3(ledger, *, queries, timeout_ms, seconds):
    start = time.monotonic()
    results = []
    attempted = 0
    def priority(target):
        try:
            nodes = list(ast.walk(ast.parse(target['predicate'], mode='eval')))
            equality = any(isinstance(node, ast.Eq) for node in nodes)
            joint = len({node.id for node in nodes if isinstance(node, ast.Name)} & set(ledger.model['types'])) > 1
            return (not equality, not joint, target['id'])
        except (SyntaxError, TypeError):
            return (True, True, target['id'])
    for target in sorted(ledger.model['targets'], key=priority):
        covered = set().union(*(hits(row) for row in ledger.pool()))
        if target['id'] in covered or target.get('status') == 'infeasible':
            continue
        query = f"({ledger.model['domain']}) and ({target.get('context', 'True')}) and ({target['predicate']})"
        try:
            translate(query, ledger.model['types'])
        except (ValueError, SyntaxError) as exc:
            results.append({'target_id': target['id'], 'status': 'unsupported', 'detail': str(exc)})
            continue
        if attempted >= queries or time.monotonic() - start >= seconds:
            results.append({'target_id': target['id'], 'status': 'budget_exhausted'})
            continue
        remaining_ms = max(1, int((seconds - (time.monotonic() - start)) * 1000))
        result = solve(ledger, query, timeout_ms=min(timeout_ms, remaining_ms), query_id=target['id'])
        attempted += 1
        results.append({'target_id': target['id'], **result})
    return {'tool': 'z3', 'queries': attempted, 'query_budget': queries, 'results': results,
            'seconds': time.monotonic() - start}


def plan_combinations(ledger, *, rows, draws_per_row, seed, seconds, solver_queries, timeout_ms):
    from allpairspy import AllPairs
    start = time.monotonic()
    factors = ledger.model['factors']
    names = list(factors)
    results, queries, dt_rules = [], 0, []
    # Pairwise coverage does not imply DT coverage. Route explicit feasible
    # original rules first, within the same planner solver/time budget.
    for target in ledger.model['targets']:
        if target.get('kind') != 'rule' or target.get('status') != 'feasible':
            continue
        if any(target['id'] in hits(row) for row in ledger.pool()):
            dt_rules.append({'target_id': target['id'], 'status': 'already_covered'})
            continue
        if queries >= solver_queries or time.monotonic() - start >= seconds:
            dt_rules.append({'target_id': target['id'], 'status': 'budget_exhausted'})
            continue
        query = f"({ledger.model['domain']}) and ({target.get('context', 'True')}) and ({target['predicate']})"
        remaining_ms = max(1, int((seconds - (time.monotonic() - start)) * 1000))
        result = solve(ledger, query, timeout_ms=min(timeout_ms, remaining_ms), query_id=target['id'],
                       source={'planner_dt_rule_id': target['id']})
        queries += 1
        dt_rules.append({'target_id': target['id'], **result})
    if not names:
        return {'tool': 'allpairspy', 'status': 'no_factors', 'results': [], 'dt_rules': dt_rules,
                'solver_queries': queries, 'seconds': time.monotonic() - start}
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
        if not receipt.get('witness') and queries < solver_queries and time.monotonic() - start < seconds:
            remaining_ms = max(1, int((seconds - (time.monotonic() - start)) * 1000))
            solver_result = solve(ledger, query, timeout_ms=min(timeout_ms, remaining_ms), query_id=row_id,
                                  source={'planner_row_id': row_id, 'planner_levels': coordinates})
            queries += 1
            result['solver'] = solver_result
            result['status'] = 'realized' if solver_result['status'] == 'sat' else solver_result['status']
        results.append(result)
    return {'tool': 'allpairspy', 'status': 'complete' if len(results) < rows else 'budget_limited',
            'results': results, 'dt_rules': dt_rules, 'solver_queries': queries, 'seconds': time.monotonic() - start}
