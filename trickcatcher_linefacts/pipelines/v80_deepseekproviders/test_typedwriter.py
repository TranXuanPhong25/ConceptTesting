import copy
import itertools
import time

import pytest
import z3

from . import joint_constructor
from .predicate_compiler import compile_condition, check_types, normalize_aliases
from .predicates import SymbolicString, SymbolicTuple, symbolic, symbolic_equal, evaluate
from .writer_compiler import compile_and_admit, compile_edit, compile_proposals
from .test_contractfix import REQ, proposal, writer_proposal


def test_symbolic_string_order_matches_python_on_empty_prefix_equal_and_unicode():
    alphabet = ('a', 'é', '😀')
    strings = [''.join(chars) for n in range(3) for chars in itertools.product(alphabet, repeat=n)]
    for a, b in itertools.product(strings, repeat=2):
        args = [SymbolicString(map(ord, a)), SymbolicString(map(ord, b))]
        for operator, expected in [('lt', a < b), ('le', a <= b), ('eq', a == b)]:
            node = {'op': operator, 'left': {'op': 'input', 'arg': 0}, 'right': {'op': 'input', 'arg': 1}}
            actual = z3.is_true(z3.simplify(symbolic(node, args)))
            assert actual == expected, (operator, a, b)
        literal = {'op': 'lt', 'left': {'op': 'input', 'arg': 0}, 'right': {'op': 'literal', 'value': b}}
        assert z3.is_true(z3.simplify(symbolic(literal, args))) == (a < b)


def test_string_solver_materializes_inputs_matching_python_condition():
    condition = 'arg0 < arg1 and len(arg0) == 2 and len(arg1) == 2'
    node, _ = compile_condition(condition, 2)
    solved = joint_constructor.solve_inputs([('ab', 'ac')], node, time.monotonic()+5)
    assert solved['inputs'] and not solved['issues']
    assert all(a < b and len(a) == len(b) == 2 for a, b in solved['inputs'])
    assert all(evaluate(node, args) is True for args in solved['inputs'])


def test_symbolic_equality_preserves_string_list_and_tuple_distinctions():
    assert z3.is_false(z3.simplify(symbolic_equal(SymbolicString([97]), [97])))
    assert z3.is_false(z3.simplify(symbolic_equal(SymbolicTuple([1]), [1])))
    assert z3.is_true(z3.simplify(symbolic_equal(SymbolicString([97]), 'a')))
    assert z3.is_true(z3.simplify(symbolic_equal(SymbolicTuple([1]), SymbolicTuple([1]))))


@pytest.mark.parametrize('text,profiles', [
    ('arg0 < 3', [{'kind': 'str'}]),
    ('arg0 == True', [{'kind': 'int'}]),
    ('len(arg0) > 0', [{'kind': 'int'}]),
    ('arg0 and True', [{'kind': 'str'}]),
    ('arg0 < arg1', [{'kind': 'list', 'element': {'kind': 'int'}}]*2),
    ('arg0 % arg1 == 0', [{'kind': 'int'}]*2),
    ('has_duplicate(arg0)', [{'kind': 'list', 'element': {'kind': 'list', 'element': {'kind': 'int'}}}]),
])
def test_trigger_type_errors_are_explicit_before_solver(text, profiles):
    node, _ = compile_condition(text, len(profiles))
    with pytest.raises(ValueError, match='predicate_type:'):
        check_types(node, profiles)


@pytest.mark.parametrize('text', [
    '__import__("os")', 'arg0.upper()', '[x for x in arg0]', 'lambda: True',
    '(x := 1)', 'arg0[0] == 1', 'local("x") == 1', 'a plausible trigger', 'arg3 > 1',
])
def test_condition_compiler_never_executes_or_guesses_unsupported_text(text):
    with pytest.raises((ValueError, SyntaxError)):
        compile_condition(text, 1)


def test_comparison_aliases_preserve_semantics_and_input_document():
    for op, fn in [('gt', lambda a, b: a > b), ('ge', lambda a, b: a >= b), ('ne', lambda a, b: a != b)]:
        raw = {'op': op, 'left': {'op': 'input', 'arg': 0}, 'right': {'op': 'input', 'arg': 1}}
        before = copy.deepcopy(raw)
        changes = []
        ir = normalize_aliases(raw, changes)
        assert raw == before and changes[0]['rewrite'] == op
        for a, b in itertools.product(range(-3, 4), repeat=2):
            assert evaluate(ir, (a, b)) == fn(a, b)


def test_operator_edit_keeps_operands_and_native_admission_is_stable():
    raw = writer_proposal()
    accepted, rejected, compilation = compile_and_admit(REQ, [raw])
    assert not rejected and len(accepted) == 1
    assert accepted[0]['alternative'] == 'x + 1'
    assert compilation['receipts'][0]['hypothesis_id'] == accepted[0]['id']
    evidence = joint_constructor.verify_input(REQ, accepted[0], (2,),
        {'repeat_seeds': [1, 2], 'repeats_per_program_seed': 2}, time.monotonic()+5)
    assert evidence['output_sensitivity'] is True
    assert raw == writer_proposal()


def test_compilation_receipts_keep_original_positions_after_rejection():
    bad = dict(writer_proposal(), trigger='arg0[0] > 1')
    first = writer_proposal()
    second = dict(first, family='different claim')
    accepted, rejected, compilation = compile_and_admit(REQ, [bad, first, second])
    assert len(accepted) == 2 and rejected[0]['index'] == 0
    assert compilation['receipts'][1]['hypothesis_id'] != compilation['receipts'][2]['hypothesis_id']
    assert {row['hypothesis_id'] for row in compilation['receipts'][1:]} == {h['id'] for h in accepted}


def test_writer_surface_and_legacy_replay_are_explicitly_separate():
    accepted, rejected, _ = compile_and_admit(REQ, [proposal()])
    assert not accepted and rejected[0]['reason'] == 'ValueError:writer_fields'
    accepted, rejected, _ = compile_and_admit(REQ, [proposal()], mode='legacy')
    assert accepted and not rejected


def test_legacy_none_and_assignment_are_not_silently_repaired():
    for replacement in ('None', 'x = x + 1'):
        raw = dict(proposal(), alternative=replacement)
        compiled, receipts = compile_proposals(REQ, [raw], mode='legacy')
        assert compiled[0]['alternative'] == replacement
        assert not receipts[0]['rewrites']
        accepted, rejected, _ = compile_and_admit(REQ, [raw], mode='legacy')
        assert not accepted and rejected


def test_local_condition_is_concrete_only_and_not_assumed_proven():
    ir, _ = compile_condition('local("n") == len(arg0)', 1, event=True)
    check_types(ir, [{'kind': 'str'}], event=True)
    assert evaluate(ir, ('abc',), {'n': 3}) is True
    assert evaluate(ir, ('abc',), {'n': 2}) is False
    with pytest.raises(ValueError, match='unobserved_local'):
        evaluate(ir, ('abc',), {})
