import hashlib
import ast

from .native_construct import candidates, certify
from .recipe_ir import joint_length_guard, multiplicity, odd_cardinality_unique


def budget():
    return {"max_candidates": 8, "max_executions": 16, "seeds": [1, 2], "repeats": 2}


def binding(source):
    expr=next(n.value for n in ast.walk(ast.parse(source)) if isinstance(n,ast.Return))
    return {"source_sha256": hashlib.sha256(source.encode()).hexdigest(), "span": [expr.lineno,expr.col_offset,expr.end_lineno,expr.end_col_offset], "function": "f"}


def test_joint_recipe_constructs_related_arguments():
    source = "def f(xs, k):\n    return len(xs) + k\n"
    recipe = joint_length_guard(**binding(source), seq_arg=0, int_arg=1, delta=2, positive=True,
                                 budget=budget(), provenance={"origin": "fixture"})
    rows = candidates(recipe, ([9], 99))
    assert rows and all(len(args[0]) == args[1] + 2 and args[1] > 0 for args in rows)


def test_multiplicity_recipe_has_real_duplicates():
    source = "def f(xs):\n    return len(set(xs))\n"
    recipe = multiplicity(**binding(source), seq_arg=0, require_length=3, budget=budget(), provenance={"origin": "fixture"})
    rows = candidates(recipe, ([5],))
    assert rows and all(len(set(args[0])) < len(args[0]) for args in rows)


def test_odd_unique_recipe_runs_in_native_worker_without_reference():
    source = "def f(xs):\n    return len(xs)\n"
    recipe = odd_cardinality_unique(**binding(source), seq_arg=0, budget=budget(), provenance={"origin": "fixture"})
    report = certify(source, "f", recipe, ([1],))
    assert report["runs"]
    assert all(row["status"] == "stable_input_and_site_realized" for row in report["runs"])
    assert all(row['output_sensitivity']=='unknown' for row in report['runs'])


def test_native_replay_reseeds_standard_random_module():
    source = "import random\ndef f(xs):\n    return random.choice(xs)\n"
    recipe = multiplicity(**binding(source), seq_arg=0, require_length=3, budget=budget(), provenance={"origin": "fixture"})
    first = certify(source, "f", recipe, ([1],))
    second = certify(source, "f", recipe, ([1],))
    assert first == second


def test_unreached_site_never_receives_realization_certificate():
    source='def f(xs):\n    if False:\n        return len(xs)\n    return 0\n'
    expr=next(n for n in ast.walk(ast.parse(source)) if isinstance(n,ast.Call))
    b=dict(source_sha256=hashlib.sha256(source.encode()).hexdigest(),span=[expr.lineno,expr.col_offset,expr.end_lineno,expr.end_col_offset],function='f')
    recipe=odd_cardinality_unique(**b,seq_arg=0,budget=budget(),provenance={'origin':'fixture'})
    report=certify(source,'f',recipe,([1],))
    assert report['runs'] and not any(r['obligation_realized'] for r in report['runs'])


def test_alternative_masked_at_output_is_not_certified():
    source='def f(xs):\n    unused = len(set(xs))\n    return 0\n'
    expr=next(n for n in ast.walk(ast.parse(source)) if isinstance(n,ast.Call) and ast.unparse(n)=='len(set(xs))')
    span=[expr.lineno,expr.col_offset,expr.end_lineno,expr.end_col_offset]
    b=dict(source_sha256=hashlib.sha256(source.encode()).hexdigest(),span=span,function='f')
    alt=dict(span=span,node_kind='Call',before='len(set(xs))',after='len(xs)')
    recipe=multiplicity(**b,seq_arg=0,require_length=3,budget=budget(),provenance={'origin':'fixture'},alternative=alt)
    report=certify(source,'f',recipe,([1],))
    assert report['runs'] and all(r['output_sensitivity'] is False for r in report['runs'])
