"""Finite observed-pool tools. Candidate relations are fallible, never spec oracles."""
import ast
from collections import Counter
import itertools

from .flow_common import digest

RELATIONS = {
    'preserve_occurrences': 'Counter(output) == Counter(argument0); order separate',
    'ascending': 'output is an ascending list; content separate',
    'required_subset_container': 'output == (set(argument1) <= set(argument0))',
    'equal_sets': 'output == (set(argument1) == set(argument0))',
    'count_ge': 'output == count(x >= argument1 in argument0)',
    'count_gt': 'output == count(x > argument1 in argument0)',
    'sum_positive': 'output == sum(each x > 0 in argument0)',
    'sum_gt_one': 'output == sum(each x > 1 in argument0)',
    'sum_distinct_positive': 'output == sum(distinct x > 0 in argument0)',
    'sum_distinct_gt_one': 'output == sum(distinct x > 1 in argument0)',
    'sum_le_limit': 'output == (sum(argument0) <= argument1), no length condition',
    'first': 'output == first item of argument0, None if empty; eligibility not inferred',
    'min_positive_none': 'output == min(positive items), None if none',
    'min_positive_raise': 'output == min(positive items), ValueError if none',
    'all_even': 'output == all(x even in argument0), True if empty',
    'any_even': 'output == any(x even in argument0), False if empty',
    'unknown': 'No executable relation justified; no pass/fail value',
}
CONCEPTS = ['occurrence_conservation', 'membership_inclusion', 'quantified_decision',
            'eligible_contribution', 'order_policy', 'eligible_selection', 'defined_outcome']
RELATION_CONCEPTS = {
    'preserve_occurrences': ['occurrence_conservation'],
    'ascending': ['order_policy'],
    'required_subset_container': ['membership_inclusion'],
    'equal_sets': ['membership_inclusion'],
    **{name: ['eligible_contribution'] for name in (
        'count_ge', 'count_gt', 'sum_positive', 'sum_gt_one',
        'sum_distinct_positive', 'sum_distinct_gt_one', 'sum_le_limit')},
    'first': ['eligible_selection'],
    'min_positive_none': ['eligible_selection', 'defined_outcome'],
    'min_positive_raise': ['eligible_selection', 'defined_outcome'],
    'all_even': ['quantified_decision'], 'any_even': ['quantified_decision'],
    'unknown': CONCEPTS,
}


def arity(relation):
    return 2 if relation in ('required_subset_container', 'equal_sets', 'count_ge', 'count_gt', 'sum_le_limit') else 1


def binding_checks(binding, parameters, spec):
    """Mechanical checks shared with BOTH arms; no normative entailment verdict."""
    quote = binding['spec_quote']
    return {'argument_names_known': all(x in parameters for x in binding['arguments']),
            'arity_matches': binding['relation'] == 'unknown' or len(binding['arguments']) == arity(binding['relation']),
            'quote_is_nonempty_exact_spec_substring': bool(quote) and quote in spec,
            'concept_relation_vocabulary_compatible': binding['concept'] in RELATION_CONCEPTS[binding['relation']],
            'spec_entailment': 'unverified; exact quote and executable relation do NOT prove correct binding'}


def equal(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(a, (list, tuple)):
        return len(a) == len(b) and all(equal(x, y) for x, y in zip(a, b))
    return a == b


def compare(binding, row, parameters):
    """Compute only whether the saved observation satisfies the proposed relation."""
    relation = binding['relation']
    if relation == 'unknown':
        return {'status': 'unknown', 'reason': 'binding_unknown'}
    if row.get('execution_status') not in ('ok', 'exception') or (row.get('execution_status') == 'ok' and row.get('output_capture') != 'literal'):
        return {'status': 'unknown', 'reason': 'observation_not_usable'}
    try:
        values = dict(zip(parameters, ast.literal_eval(row['input'])))
        args = [values[name] for name in binding['arguments']]
        expected_arity = arity(relation)
        if len(args) != expected_arity:
            raise ValueError('binding_arity')
        xs = args[0]
        if type(xs) is not list or any(type(x) is not int for x in xs):
            raise ValueError('list_int_argument_required')
        actual_exception = row['exception_type'] if row['execution_status'] == 'exception' else None
        actual = ast.literal_eval(row['output']) if row['execution_status'] == 'ok' else None
        expected_exception = None
        if relation == 'preserve_occurrences':
            holds = actual_exception is None and type(actual) is list and all(type(v) is int for v in actual) and Counter(actual) == Counter(xs)
            return {'status': 'computed', 'holds_on_observation': holds}
        if relation == 'ascending':
            holds = actual_exception is None and type(actual) is list and all(type(v) is int for v in actual) and actual == sorted(actual)
            return {'status': 'computed', 'holds_on_observation': holds}
        if relation in ('required_subset_container', 'equal_sets'):
            ys = args[1]
            if type(ys) is not list or any(type(x) is not int for x in ys):
                raise ValueError('second_list_int_required')
            predicted = set(ys) <= set(xs) if relation == 'required_subset_container' else set(ys) == set(xs)
        elif relation in ('count_ge', 'count_gt', 'sum_le_limit'):
            threshold = args[1]
            if type(threshold) is not int:
                raise ValueError('integer_threshold_required')
            if relation == 'sum_le_limit':
                predicted = sum(xs) <= threshold
            else:
                predicted = sum(x >= threshold if relation == 'count_ge' else x > threshold for x in xs)
        elif relation.startswith('sum_'):
            eligible = [x for x in xs if x > (1 if relation.endswith('gt_one') else 0)]
            predicted = sum(set(eligible) if 'distinct' in relation else eligible)
        elif relation == 'first':
            predicted = xs[0] if xs else None
        elif relation in ('min_positive_none', 'min_positive_raise'):
            eligible = [x for x in xs if x > 0]
            predicted = min(eligible) if eligible else None
            if not eligible and relation == 'min_positive_raise':
                expected_exception = 'ValueError'
        elif relation in ('all_even', 'any_even'):
            predicted = (all if relation == 'all_even' else any)(x % 2 == 0 for x in xs)
        else:
            raise ValueError('unsupported_relation')
        holds = actual_exception == expected_exception
        if expected_exception is None:
            holds = holds and row['execution_status'] == 'ok' and equal(actual, predicted)
        return {'status': 'computed', 'candidate_value': repr(predicted) if expected_exception is None else None,
                'candidate_exception': expected_exception, 'holds_on_observation': holds}
    except (KeyError, IndexError, ValueError, TypeError, SyntaxError):
        return {'status': 'unknown', 'reason': 'binding_arguments_or_observation_unsupported'}


def measure(row):
    args = ast.literal_eval(row['input'])
    result = []
    for value in args:
        if type(value) is list and all(type(x) is int for x in value):
            result.append({'length': len(value), 'distinct': len(set(value)), 'sum': sum(value),
                           'positive': sum(x > 0 for x in value), 'ones': value.count(1),
                           'max_multiplicity': max(Counter(value).values(), default=0)})
        elif type(value) is int:
            result.append({'integer': value})
        else:
            result.append({'unsupported': True})
    return result


def contrast(rows, matrix):
    """Choose simplest observed pairs with different candidate satisfaction vectors.

    Selection uses no spec/gold label. It is bounded finite-pool inspection, not
    generation or proof that no unseen discriminator exists.
    """
    pairs = []
    for a, b in itertools.combinations(rows, 2):
        vector = lambda rid: {key: (value['status'], value.get('holds_on_observation'))
                              for key, value in matrix[rid].items()}
        va, vb = vector(a['id']), vector(b['id'])
        changed = [key for key in va if va[key] != vb[key]]
        aa, bb = ast.literal_eval(a['input']), ast.literal_eval(b['input'])
        differing = [i for i, (x, y) in enumerate(zip(aa, bb)) if not equal(x, y)]
        controlled = len(aa) == len(bb) and len(differing) == 1
        if changed or controlled:
            pairs.append({'rows': [a['id'], b['id']], 'changed_candidates': changed,
                          'only_changed_argument': differing[0] if controlled else None,
                          'measurements': [measure(a), measure(b)],
                          'cost': len(a['input']) + len(b['input'])})
    pairs.sort(key=lambda x: (x['only_changed_argument'] is None, not bool(x['changed_candidates']), x['cost'], x['rows']))
    return {'scope': '4 small observed pairs, prefer one changed argument; possibly multiple dimensions changed',
            'pairs': pairs[:4], 'found': len(pairs), 'no_pair_means': 'none in this finite pool, not infeasibility'}


def return_dependencies(source):
    tree = ast.parse(source)
    function = next(x for x in tree.body if isinstance(x, ast.FunctionDef))
    names = lambda node: sorted({x.id for x in ast.walk(node) if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Load)})
    assignments = {target.id: names(node.value) for node in function.body if isinstance(node, ast.Assign)
                   for target in node.targets if isinstance(target, ast.Name)}
    returns = [names(node.value) for node in ast.walk(function) if isinstance(node, ast.Return) and node.value is not None]
    used = set(itertools.chain.from_iterable(returns))
    for _ in range(len(assignments)):
        used.update(itertools.chain.from_iterable(assignments.get(x, []) for x in list(used)))
    return {'scope': 'partial return-expression/top-level-assignment read inventory; omits guards, aliases, side effects and nested scopes; NOT sound dataflow or causality proof',
            'return_reads': returns, 'top_level_assignments_read': assignments,
            'transitive_names': sorted(used), 'unreferenced_top_level_targets': sorted(set(assignments) - used),
            'control_or_nested_scope_present': any(isinstance(x, (ast.If, ast.For, ast.While, ast.ListComp,
                                                                 ast.GeneratorExp, ast.FunctionDef))
                                                   for node in function.body for x in ast.walk(node))}


def tools(bindings, rows, parameters, source, requested):
    result = {'notice': 'Candidate relations NOT validated against spec. Agreement with PUT is NOT correctness.'}
    matrix = None
    if set(requested) & {'compare_bindings', 'contrast'}:
        try:
            matrix = {row['id']: {b['id']: compare(b, row, parameters) for b in bindings} for row in rows}
        except Exception as exc:
            result['matrix_error'] = {'status': 'error', 'error_type': type(exc).__name__}
    if 'compare_bindings' in requested:
        result['candidate_relations_on_observations'] = {
            'columns': ['observation', 'binding', 'status', 'candidate_value', 'candidate_exception', 'holds_on_observation', 'reason'],
            'rows': [[oid, bid, value['status'], value.get('candidate_value'), value.get('candidate_exception'), value.get('holds_on_observation'), value.get('reason')]
                     for oid, values in matrix.items() for bid, value in values.items()],
        } if matrix is not None else {'status': 'error'}
    if 'contrast' in requested:
        try:
            result['contrasts'] = contrast(rows, matrix) if matrix is not None else {'status': 'error'}
        except Exception as exc:
            result['contrasts'] = {'status': 'error', 'error_type': type(exc).__name__}
    if 'return_dependencies' in requested:
        try:
            result['return_dependencies'] = return_dependencies(source)
        except Exception as exc:
            result['return_dependencies'] = {'status': 'error', 'error_type': type(exc).__name__}
    result['input_pool_hash'] = digest(rows)
    return result
