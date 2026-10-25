import ast

from .capability_inventory import inventory


CONFIG = {
    "max_recipes_per_case": 3, "max_candidates_per_case": 64,
    "max_native_executions_per_case": 256, "max_case_seconds": 120,
    "worker_seconds": 2, "repeat_seeds": [20261024, 20261025],
    "repeats_per_program_seed": 2, "max_symbolic_summaries": 3,
}


def request(source, arguments="([1, 2],)"):
    return {"case_id": "fixture", "source": source, "entry": "f",
            "public_examples": [{"arguments": arguments, "expected": "0"}]}


def test_inventory_is_source_only_and_routes_complex_code_to_native():
    source = '''def f(xs):
    def score(v):
        return sum([x for x in v])
    memo = {x: i for i, x in enumerate(xs)}
    while xs:
        xs.pop()
    return score(list(memo))
'''
    row = inventory(request(source), CONFIG)
    assert row["route"] == "native_first"
    assert {"nested_function", "list_comprehension", "dict_comprehension", "while_loop", "mutating_method"} <= set(row["native_reasons"])
    assert row["private_data_used"] is False


def test_inventory_detects_nested_input_topology_without_rejecting_it():
    source = "def f(points, k):\n    return len(points) + k\n"
    row = inventory(request(source, "([[1, 2], [3, 4]], 2)"), CONFIG)
    shape = row["public_input_topologies"][0][0]
    assert shape["kind"] == "list"
    assert "native_first" == row["route"]


def test_inventory_marks_randomness_for_repeatability_policy():
    source = "def f(xs):\n    import random\n    random.shuffle(xs)\n    return xs[0]\n"
    row = inventory(request(source), CONFIG)
    assert row["repeatability_required"] is True
    assert "possible_nondeterminism" in row["native_reasons"]


def test_inventory_does_not_execute_source():
    source = "def f(xs):\n    raise RuntimeError('must not execute')\n"
    row = inventory(request(source), CONFIG)
    assert row["case_id"] == "fixture"
    assert row["capability_status"] == "source_inventory_only"
