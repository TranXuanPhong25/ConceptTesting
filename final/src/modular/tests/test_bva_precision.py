"""Exact float neighbors, preserved joint context and fixed-budget allocation."""
import ast
import math
import sys

import pytest

from final.src.modular.boundary_value_analysis.precision import (
    expand_seeds, fixed_twenty, call_identity, construction_receipt,
)


def expand(inputs, source="def f(value):\n    return float(value)\n", specification="def f(value):\n    pass\n"):
    return expand_seeds(specification=specification, entry_point="f", program_source=source, contract="", inputs=inputs)


def call(value):
    return {"args": repr((value,)), "kwargs": "{}"}


def test_numeric_string_half_neighbor_is_exact_and_round_trips():
    result = expand([call("0.5")])
    values = [ast.literal_eval(item["input"]["args"])[0] for item in result["expansions"]]
    assert values == ["0.49999999999999994", "0.5000000000000001"]
    assert all(item["receipt"]["adjacent_verified"] for item in result["expansions"])
    assert float(values[0]) + 0.5 == 1.0


def test_signed_zero_and_minimum_subnormal_neighbors_preserve_bits():
    result = expand([call(-0.0)])
    neighbors = [ast.literal_eval(item["input"]["args"])[0] for item in result["expansions"]]
    assert neighbors == [-5e-324, 5e-324]
    assert all(item["receipt"]["anchor_hex"] == "-0x0.0p+0" for item in result["expansions"])


def test_infinite_neighbors_are_rejected_without_constructing_nonfinite_input():
    result = expand([call(sys.float_info.max)])
    assert len(result["expansions"]) == 1
    assert result["rejected"] == [{"seed_index": 0, "parameter": "value", "direction": "above", "reason": "nonfinite_neighbor"}]


def test_integers_and_strings_without_conversion_evidence_are_not_widened():
    assert expand([call(1)])["expansions"] == []
    assert expand([call("0.5")], source="def f(value):\n    return len(value)\n")["expansions"] == []
    assert expand([call("2020")], source="def f(value):\n    return int(value)\n")["expansions"] == []


def test_contract_conversion_supports_strings_without_executing_source():
    result = expand_seeds(specification="def f(value):\n    pass\n", entry_point="f",
        program_source="raise RuntimeError('must not execute')", contract="    value = float(value)\n",
        inputs=[call("0.5")])
    assert result["numeric_string_parameters"] == ["value"]
    assert len(result["expansions"]) == 2


def test_non_numeric_conversion_strings_are_recorded_as_unsupported():
    result = expand([call("not-a-number"), call("inf")])
    assert result["expansions"] == []
    assert len(result["unsupported"]) == 2


def test_float_parameter_expansion_preserves_other_arguments_and_list_shape():
    spec = "def f(q, w):\n    pass\n"
    result = expand_seeds(specification=spec, entry_point="f", program_source="", contract="",
        inputs=[{"args": "([-1, -2, -1], -4.0)", "kwargs": "{}"}])
    assert len(result["expansions"]) == 2
    for item in result["expansions"]:
        q, w = ast.literal_eval(item["input"]["args"])
        assert q == [-1, -2, -1] and type(w) is float
        assert item["receipt"]["parameter"] == "w"


def test_round_robin_uses_declared_parameter_order_before_next_direction():
    spec = "def f(x, y):\n    pass\n"
    result = expand_seeds(specification=spec, entry_point="f", program_source="", contract="",
        inputs=[{"args": "(1.0, 2.0)", "kwargs": "{}"}, {"args": "(3.0, 4.0)", "kwargs": "{}"}])
    order = [(item["receipt"]["seed_index"], item["receipt"]["parameter"], item["receipt"]["direction"])
             for item in result["expansions"]]
    assert order[:4] == [(0, "x", "below"), (0, "y", "below"), (1, "x", "below"), (1, "y", "below")]
    assert all(direction == "above" for _, _, direction in order[4:])


def test_seed_or_expansion_duplicates_are_not_spent_twice():
    result = expand([call(1.0), call(math.nextafter(1.0, -math.inf)), call(1.0)])
    assert len(result["seeds"]) == 2
    assert len(result["expansions"]) == 2
    assert len(result["rejected"]) == 2
    identities = [call_identity(item) for item in result["seeds"]] + [call_identity(item["input"]) for item in result["expansions"]]
    assert len(identities) == len(set(identities))


def test_no_expansion_preserves_full_seed_batch_in_original_order():
    result = expand([call(i) for i in range(20)])
    selected = fixed_twenty(result)
    assert [item["input"] for item in selected] == result["seeds"]


def test_fixed_policy_keeps_ten_seeds_and_exactly_ten_expansions():
    result = expand([call(float(i)) for i in range(20)])
    selected = fixed_twenty(result)
    assert len(selected) == 20
    assert [item["input"] for item in selected[:10]] == result["seeds"][:10]
    assert all(item["kind"] == "expansion" for item in selected[10:])
    assert [item["input"] for item in selected[10:]] == [item["input"] for item in result["expansions"][:10]]


def test_receipt_rejects_wrong_anchor_neighbor_or_changed_context():
    with pytest.raises(ValueError, match="anchor_does_not_match_seed"):
        construction_receipt({"x": 1.0}, {"x": 2.0}, "x", 2.0, 2.0, "below", "float")
    with pytest.raises(ValueError, match="adjacent_neighbor"):
        construction_receipt({"x": 1.0}, {"x": 0.9}, "x", 1.0, 0.9, "below", "float")
    neighbor = math.nextafter(1.0, -math.inf)
    with pytest.raises(ValueError, match="non_target_argument_changed"):
        construction_receipt({"x": 1.0, "q": [1, 2]}, {"x": neighbor, "q": [1]},
                             "x", 1.0, neighbor, "below", "float")
