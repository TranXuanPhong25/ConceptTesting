"""Authored engineering fixtures, not benchmark effectiveness measurements."""
import ast
import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest
import z3

from .construction import construct, replay, certify
from .deep_run import validate_request, prepare, manifest, prompts
from .hypotheses import catalog, import_proposals, patch_tree
from .symbolic import Evaluator, State, input_shapes, equal, materialize, symbolic_inputs

CONFIG = dict(max_seq_len=4, max_shapes=16, max_paths=64, max_hypotheses=16,
              models_per_hypothesis=1, solver_timeout_ms=300, case_timeout_seconds=12,
              int_bound=30, max_queries=64)


def hypothesis(source, family, before=None, after=None):
    rows, _ = catalog(source, 'f')
    return next(r for r in rows if r['family'] == family and (before is None or r['before'] == before)
                and (after is None or r['after'] == after))


def solved(source, seeds, family, before=None, after=None):
    h = hypothesis(source, family, before, after)
    report = construct(source, 'f', seeds, h, CONFIG)
    assert report['inputs'], json.dumps(report, indent=2)
    row = report['inputs'][0]
    assert row['verification'] == 'exact_site_path_and_output_verified'
    assert row['observations']['put']['output'] != row['observations']['alternative']['output']
    return row


def test_joint_assignment_guard_and_multiplicity():
    source = '''def f(xs, k):
    if k > 0:
        required = k + 2
        if len(xs) == required:
            return sum(xs)
    return 0
'''
    row = solved(source, [([1, 2], 5)], 'MULTIPLICITY', 'sum(xs)')
    xs, k = ast.literal_eval(row['arguments'])
    assert k > 0 and len(xs) == k + 2
    assert len(set(xs)) < len(xs)
    assert row['put_path'] and row['path_predicates'] and row['local_infection_predicates']


def test_order_tie_is_an_executable_obligation():
    source = 'def f(x, y):\n    if x > 0 and x <= y:\n        return 1\n    return 0\n'
    row = solved(source, [(2, 5)], 'BOUNDARY', 'x <= y')
    x, y = ast.literal_eval(row['arguments'])
    assert x == y and x > 0


def test_local_infection_without_propagation_is_rejected():
    source = 'def f(x):\n    lost = x + 1\n    return 0\n'
    r = construct(source, 'f', [(2,)], hypothesis(source, 'OPERATOR'), CONFIG)
    assert r['status'] == 'bounded_no_difference' and not r['inputs']


def test_repeated_accumulator_update():
    source = 'def f(xs):\n    total = 0\n    for x in xs:\n        total += x\n    return total\n'
    row = solved(source, [([1, 2],)], 'STATE_ACCUMULATION')
    xs, = ast.literal_eval(row['arguments'])
    assert len(xs) >= 2
    assert len(row['observations']['put']['site_events']) >= 2


def test_loop_cardinality_range_endpoint():
    source = 'def f(n):\n    total = 0\n    for i in range(n):\n        total += i\n    return total\n'
    row = solved(source, [(3,)], 'LOOP_CARDINALITY', 'range(n)', 'range(n + 1)')
    assert row['observations']['put']['site_events'][0]['value']['type'] == 'range'


def test_index_construction_respects_both_bounds_and_negative_indices():
    source = 'def f(xs, i):\n    return xs[i]\n'
    row = solved(source, [([3, 4], 0)], 'INDEX_SELECTION', 'xs[i]', 'xs[i + 1]')
    xs, i = ast.literal_eval(row['arguments'])
    assert -len(xs) <= i < len(xs) and -len(xs) <= i + 1 < len(xs)
    assert xs[i] != xs[i + 1]


def test_short_circuit_site_must_really_execute():
    source = 'def f(xs, n):\n    if n == 0 or xs[n - 1] > 0:\n        return 1\n    return 0\n'
    row = solved(source, [([1, -1], 0)], 'INDEX_SELECTION', 'xs[n - 1]', 'xs[n - 1 + 1]')
    assert ast.literal_eval(row['arguments'])[1] != 0
    assert row['observations']['put']['site_events']


def test_python_floor_division_with_negative_divisor():
    source = 'def f(x, y):\n    return (x // y, x % y, x + 1)\n'
    h = hypothesis(source, 'OPERATOR')
    ev = Evaluator(source, 'f', h)
    args, domain = symbolic_inputs([('int', None), ('int', None)], 30, 4)
    states = ev.run(args)
    s = z3.Solver(); s.add(*domain, *states[0].guards, args[0] == 7, args[1] == -3)
    assert s.check() == z3.sat
    assert materialize(states[0].value, s.model()) == (-3, -2, 8)


def test_partial_support_never_becomes_unsat():
    source = 'def f(x):\n    if x > 0:\n        while x > 1:\n            x -= 1\n    return x + 1\n'
    h = hypothesis(source, 'OPERATOR', 'x + 1')
    r = construct(source, 'f', [(2,)], h, CONFIG)
    assert any('While' in issue for issue in r['issues'])
    assert r['status'] != 'bounded_no_difference'


def test_only_empty_sequence_does_not_invent_element_type():
    with pytest.raises(Exception, match='empty_only_sequence'):
        input_shapes([([],)], 4, 4)


def test_shape_enumeration_does_not_infer_sign_or_minimum_length():
    shapes, _ = input_shapes([([5, 6, 7], 3)], 4, 16)
    assert any(shape[0][1][1] == 0 for shape in shapes)
    args, domain = symbolic_inputs(shapes[0], 30, 4)
    solver = z3.Solver(); solver.add(*domain, args[1] == -3)
    assert solver.check() == z3.sat


def test_imported_semantics_remain_unverified_and_require_exact_binding():
    source = 'def f(x):\n    """Return x plus one."""\n    return x + 1\n'
    h = hypothesis(source, 'OPERATOR')
    proposal = {key: h[key] for key in ('span', 'before', 'after', 'family')}
    proposal.update(rationale='The quoted requirement could distinguish these operations.', spec_quote='Return x plus one.',
                    required_relation='output = x + 1', observed_relation='the code returns x + 1',
                    trigger_reason='This is a behavioral alternative, not evidence of a real bug.')
    rows = import_proposals(source, 'f', [proposal])
    assert rows[0]['spec_binding'] == 'unverified'
    assert rows[0]['origin'] == 'external_proposal'
    assert 'x - 1' in ast.unparse(patch_tree(source, rows[0]))
    proposal['spec_quote'] = 'invented requirement'
    with pytest.raises(ValueError, match='quote'):
        import_proposals(source, 'f', [proposal])


def test_private_fields_rejected_and_evidence_parity():
    request = dict(case_id='engineering', source='def f(x):\n    return x + 1\n', entry='f',
                   public_examples=[dict(arguments='(2,)', expected='3')])
    with pytest.raises(ValueError, match='evaluator'):
        validate_request(dict(request, canonical_solution='secret'))
    data = prepare(request, dict(CONFIG, max_hypotheses=2))
    arms = data['prompts']
    assert arms['concept']['evidence'] == arms['equal_evidence_raw']['evidence']
    assert arms['concept']['instruction'] != arms['equal_evidence_raw']['instruction']
    assert data['hypotheses'][0]['base_status'] == 'already_distinguished_by_public_inputs'


def test_replay_errors_do_not_count_as_propagation():
    candidate = dict(predicted_put={}, predicted_alternative={}, put_path=[], alternative_path=[], predicted_site_values=[])
    assert certify(candidate, dict(status='ok', put={'status': 'timeout'}, alternative={'status': 'ok'}))[0] is False


def test_manifest_includes_domain_proposals_and_solver():
    r = dict(case_id='x', source='def f(x):\n    return x + 1\n', entry='f', public_examples=[dict(arguments='(2,)', expected='3')])
    first = manifest(r, CONFIG)
    assert first != manifest(r, dict(CONFIG, int_bound=31))
    assert first != manifest(dict(r, proposals=[]), CONFIG)
    assert first['solver_version'] and 'construction.py' in first['source_files_sha256']


def test_public_adapter_uses_only_explicit_asserts_and_records_unsupported():
    from .public_adapter import adapt
    src = 'def f(xs, k):\n    return len(xs) + k\n'
    req, skipped = adapt(src, 'f', 'assert candidate([1, 2], 3) == 5\nassert f([], 2) > 0\n', 'example', spec='Add length to k.')
    assert req['public_examples'] == [dict(arguments='([1, 2], 3)', expected='5')]
    assert req['spec'] == 'Add length to k.' and len(skipped) == 1
    validate_request(req)


def test_short_circuit_division_and_ternary_targets():
    source = 'def f(x, y):\n    return x + 1 if y != 0 and x // y > 0 else x - 1\n'
    solved(source, [(5, 2)], 'OPERATOR', 'x + 1')


def test_replay_rejects_exact_site_mismatch_even_when_line_executes():
    src = 'def f(x):\n    return (x + 1) if x > 0 else 0\n'
    h = hypothesis(src, 'OPERATOR')
    observed = replay(src, 'f', (-1,), h)
    assert observed['status'] == 'ok'
    assert not observed['put']['site_events']


def test_mutating_alias_calls_fail_closed():
    src = 'def f(xs):\n    ys = xs\n    ys.append(1)\n    return len(xs)\n'
    h = hypothesis(src, 'MULTIPLICITY')
    r = construct(src, 'f', [([1, 2],)], h, CONFIG)
    assert not r['inputs'] and r['status'] == 'unsupported_or_incomplete'


def test_imported_hypothesis_is_not_starved_by_catalog_cap():
    src = 'def f(x):\n    """Return x plus one."""\n    return x + 1\n'
    h = hypothesis(src, 'OPERATOR')
    p = {key: h[key] for key in ('span', 'before', 'after', 'family')}
    p.update(after='x + 2', rationale='Alternate value behavior to investigate.', spec_quote='Return x plus one.',
             required_relation='x + 1', observed_relation='x + 1', trigger_reason='Check output distinction.')
    request = dict(case_id='priority', source=src, entry='f', proposals=[p], public_examples=[dict(arguments='(2,)', expected='3')])
    result = prepare(request, dict(CONFIG, max_hypotheses=1))
    assert result['hypotheses'][0]['hypothesis']['origin'] == 'external_proposal'


def test_string_profile_supported_for_length_and_value_queries():
    src = 'def f(s):\n    if len(s) <= 2:\n        return 1\n    return 0\n'
    row = solved(src, [('abc',)], 'BOUNDARY', 'len(s) <= 2')
    assert len(ast.literal_eval(row['arguments'])[0]) == 2


def test_type_only_local_infection_is_preserved():
    source = 'def f(x):\n    return abs(x)\n'
    row = solved(source, [(True,)], 'VALUE')
    assert row['predicted_put']['type'] == 'int'
    assert row['predicted_alternative']['type'] == 'bool'


def test_query_cap_is_enforced_before_each_check():
    source = 'def f(x):\n    return x + 1\n'
    report = construct(source, 'f', [(2,)], hypothesis(source, 'OPERATOR'), dict(CONFIG, max_queries=1, models_per_hypothesis=2))
    assert report['queries'] == 1 and len(report['inputs']) == 1
    assert 'query_cap' in report['issues']


def test_sequence_augassign_is_not_silently_treated_as_fresh_assignment():
    source = 'def f(xs):\n    ys = xs\n    xs += [1]\n    return len(ys)\n'
    report = construct(source, 'f', [([2],)], hypothesis(source, 'STATE_ACCUMULATION'), CONFIG)
    assert not report['inputs'] and 'inplace_sequence_mutation' in report['issues']


def test_shadowed_builtin_is_unsupported():
    source = 'def f(abs, x):\n    return abs(x)\n'
    report = construct(source, 'f', [(2, 3)], hypothesis(source, 'VALUE'), CONFIG)
    assert not report['inputs'] and any('shadowed_callable' in i for i in report['issues'])


def test_intermediate_length_is_explored_within_domain():
    source = 'def f(xs):\n    if len(xs) == 4:\n        return sum(xs)\n    return 0\n'
    h = hypothesis(source, 'MULTIPLICITY', 'sum(xs)')
    report = construct(source, 'f', [([1, 2],)], h, dict(CONFIG, max_seq_len=6, max_queries=100))
    assert report['inputs'], json.dumps(report)
    assert len(ast.literal_eval(report['inputs'][0]['arguments'])[0]) == 4


def test_adapter_excludes_dead_and_nested_asserts_preserves_order():
    from .public_adapter import adapt
    source = 'def f(x):\n    return x + 1\n'
    tests = 'if False:\n    assert candidate(1) == 999\nassert candidate(2) == 3\ndef check(candidate):\n    assert candidate(3) == 4\n    if False:\n        assert candidate(4) == 999\n'
    request, unsupported = adapt(source, 'f', tests, 'context')
    assert [e['arguments'] for e in request['public_examples']] == ['(2,)']
    assert len(unsupported) == 3


def test_writer_cannot_import_external_code_or_change_assignment_target():
    source = 'def f(x):\n    """Return x plus one."""\n    return x + 1\n'
    h = hypothesis(source, 'OPERATOR')
    p = {k: h[k] for k in ('span', 'before', 'after', 'family')}
    p.update(after="__import__('math').sqrt(x)", rationale='probe', spec_quote='Return x plus one.',
             required_relation='x + 1', observed_relation='x + 1', trigger_reason='probe')
    with pytest.raises(ValueError, match='unsupported_syntax|external_or_keyword|reserved'):
        import_proposals(source, 'f', [p])
    source2 = 'def f(xs):\n    """Sum all occurrences."""\n    total = 0\n    for x in xs:\n        total += x\n    return total\n'
    h2 = hypothesis(source2, 'STATE_ACCUMULATION')
    p2 = {k: h2[k] for k in ('span', 'before', 'after', 'family')}
    p2.update(after='other = x', rationale='probe', spec_quote='Sum all occurrences.',
              required_relation='sum', observed_relation='sum', trigger_reason='probe')
    with pytest.raises(ValueError, match='preserve_assignment_target'):
        import_proposals(source2, 'f', [p2])


def test_expired_construction_deadline_is_not_unsat():
    source = 'def f(x):\n    return x + 1\n'
    r = construct(source, 'f', [(2,)], hypothesis(source, 'OPERATOR'), dict(CONFIG, case_timeout_seconds=-1))
    assert r['status'] == 'unsupported_or_incomplete'
    assert r['queries'] == 0 and 'construction_deadline' in r['issues']


def test_concrete_replay_preserves_real_inplace_alias_semantics():
    source = 'def f(xs):\n    ys = xs\n    xs += [1]\n    return len(ys)\n'
    h = hypothesis(source, 'STATE_ACCUMULATION')
    observations = replay(source, 'f', ([2],), h)
    assert observations['put']['output'] == {'type': 'int', 'repr': '2'}
    assert observations['alternative']['output'] == {'type': 'int', 'repr': '1'}


@pytest.mark.parametrize('prefix', ['return', 'candidate = lambda x: 999'])
def test_adapter_does_not_skip_return_or_rebinding_in_check(prefix):
    from .public_adapter import adapt
    tests = f'def check(candidate):\n    {prefix}\n    assert candidate(1) == 999\nassert f(2) == 3\n'
    request, unsupported = adapt('def f(x):\n    return x + 1\n', 'f', tests, 'wrapper')
    assert request['public_examples'] == [dict(arguments='(2,)', expected='3')]
    assert len(unsupported) == 1


def test_valid_direct_check_wrapper_is_supported():
    from .public_adapter import adapt
    request, skipped = adapt('def f(x):\n    return x + 1\n', 'f',
                             'def check(candidate):\n    assert candidate(2) == 3\n    assert candidate(4) == 5\ncheck(f)\n', 'wrapper')
    assert len(request['public_examples']) == 2 and not skipped


def test_reverse_multiplicity_recipe_can_remove_deduplication():
    source = 'def f(xs, k):\n    if k > 0:\n        required = k + 2\n        if len(xs) == required:\n            return len(set(xs))\n    return 0\n'
    row = solved(source, [([1, 2], 5)], 'MULTIPLICITY', 'len(set(xs))', 'len(xs)')
    xs, k = ast.literal_eval(row['arguments'])
    assert k > 0 and len(xs) == k + 2 and len(set(xs)) < len(xs)
