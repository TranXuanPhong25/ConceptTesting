"""Check context preservation on synthetic inputs without executing a PUT/model."""
import ast
import json

import pytest

from final.src.modular.artifacts import ArtifactStore
from final.src.modular.arms.boundary import BoundaryArm
from final.src.modular.boundary_value_analysis import BoundarySettings, BoundaryValueAnalysis
from final.src.modular.boundary_value_analysis.construction import instantiate_value
from final.src.modular.boundary_value_analysis.context_requirements import validate_context_requirements
from final.src.modular.tests.test_boundary_value_analysis import ScriptedCalls


SPECIFICATION = '''def f(xs: list[int], limit: int):
    """Accept when xs is symmetric and its total is at most limit."""
'''
SOURCE = '''def f(xs, limit):
    if xs != xs[::-1]:
        return False
    return sum(xs) <= limit
'''
REQUIREMENTS = [{"parameter": "xs", "property": "palindrome"},
                {"parameter": "xs", "property": "all_negative"}]


def selected_sum():
    return {"status": "selected", "reason": "Inspect the PUT comparison on valid integer sequences.",
            "boundaries": [{"id": "b1", "template_id": "xs:sum",
                "characteristic": {"parameter": "xs", "operation": "sum"},
                "threshold": {"kind": "expression", "parameter": "limit", "operation": "value"},
                "comparison": "<=", "boundary_kind": "behavior", "neighborhood": {"mode": "step", "step": 1},
                "target_sides": ["below", "at", "above"], "constraints": [],
                "source_quote": "xs is symmetric and its total is at most limit",
                "explanation": "Use a symmetric sequence so the comparison is reached.",
                "origin": "code", "alignment": "match", "code_quote": "sum(xs) <= limit",
                "reach": "xs is symmetric", "infect": "at the limit",
                "side_rules": {"below": "apply acceptance rule", "at": "apply acceptance rule",
                               "above": "apply acceptance rule"}}]}


def run_contexts(path, records, *, selected=None, source=SOURCE, specification=SPECIFICATION, mode="compiled"):
    calls = ScriptedCalls(selected or selected_sum(), {"inputs": records})
    analysis = BoundaryValueAnalysis(BoundarySettings(construction_mode=mode))
    arguments = dict(task_number=0, program_id=0, specification=specification, entry_point="f",
                     program_source=source, base_inputs=[])
    result = analysis.run(**arguments, artifacts=ArtifactStore(path), calls=calls)
    replay = analysis.run(**arguments, artifacts=ArtifactStore(path, read_only=True))
    assert replay == result
    return result


def test_sum_sides_keep_negative_palindrome_and_non_target_limit(tmp_path):
    records = [{"obligation_id": "b1:" + side, "arguments": {"xs": [-2, -1, -2], "limit": -6},
                "context_requirements": REQUIREMENTS} for side in ("below", "at", "above")]
    result = run_contexts(tmp_path, records)
    assert result["rejected"] == []
    assert len(result["inputs"]) == 3
    for record, expected_total in zip(result["inputs"], [-7, -6, -5]):
        values, limit = ast.literal_eval(record["args"])
        assert sum(values) == expected_total and values == values[::-1]
        assert all(value < 0 for value in values) and limit == -6
        assert record["context_requirements"] == REQUIREMENTS
        assert record["validation"]["context_requirements"] == "passed"
        assert record["validation"]["reach_propagation"] == "unverified"
    identity = json.loads((tmp_path / "tasks/0/boundary/0/identity.json").read_text())
    assert identity["schema"] == "boundary-value-analysis-5"


def test_sum_checks_sign_after_construction_and_does_not_poison_duplicate_state(tmp_path):
    seed = {"obligation_id": "b1:at", "arguments": {"xs": [-2, -1, -2], "limit": 1}}
    result = run_contexts(tmp_path, [{**seed, "context_requirements": REQUIREMENTS},
                                      {**seed, "context_requirements": REQUIREMENTS[:1]}])
    assert result["rejected"] == [{"index": 0, "reason": "context_requirement_not_met"}]
    assert len(result["inputs"]) == 1
    assert ast.literal_eval(result["inputs"][0]["args"])[0] == [-2, 5, -2]


@pytest.mark.parametrize("mode", ["compiled", "literal"])
def test_literal_records_cannot_bypass_declared_context_requirements(tmp_path, mode):
    record = {"args": "([-2, -1, -3], -6)", "kwargs": "{}", "boundary_id": "b1", "side": "at"}
    result = run_contexts(tmp_path, [{**record, "context_requirements": REQUIREMENTS}, record], mode=mode)
    assert result["rejected"] == [{"index": 0, "reason": "context_requirement_not_met"}]
    assert len(result["inputs"]) == 1


@pytest.mark.parametrize("requirements, reason", [
    (None, "invalid_context_requirements"),
    ([{"parameter": "xs", "property": "execute(xs)"}], "unsupported_context_property"),
    ([{"parameter": "wrong", "property": "palindrome"}], "unknown_context_parameter"),
    ([{"parameter": "xs", "property": "token_only", "token": "ab"}], "invalid_context_token"),
    ([{"parameter": "xs", "property": "palindrome", "code": "xs[::-1]"}], "invalid_context_requirement"),
])
def test_unsupported_requirements_are_explicit_rejections(tmp_path, requirements, reason):
    record = {"obligation_id": "b1:at", "arguments": {"xs": [-2, -1, -2], "limit": -6},
              "context_requirements": requirements}
    result = run_contexts(tmp_path, [record])
    assert result["inputs"] == []
    assert result["rejected"] == [{"index": 0, "reason": reason}]


@pytest.mark.parametrize("seed,target,expected", [
    ([-2, -2], -6, [-3, -3]),
    ((-3, -1, -3), -8, (-3, -2, -3)),
    ([-2.0, -2.0], -5.0, [-2.5, -2.5]),
    ([], -3, [-3]),
])
def test_palindrome_sum_construction_keeps_shape_types_and_integral_values(seed, target, expected):
    value = instantiate_value({"operation": "sum"}, target, seed, preserve_palindrome=True)
    assert value == expected and type(value) is type(expected)
    if type(target) is int:
        assert all(type(item) is int for item in value)


def test_even_integer_palindrome_rejects_odd_total_without_changing_type(tmp_path):
    record = {"obligation_id": "b1:at", "arguments": {"xs": [-2, -2], "limit": -5},
              "context_requirements": REQUIREMENTS}
    result = run_contexts(tmp_path, [record])
    assert result["inputs"] == []
    assert result["rejected"] == [{"index": 0, "reason": "context_shape_cannot_realize_target"}]


@pytest.mark.parametrize("property_name,valid,invalid", [
    ("all_negative", [-3, -1], [-1, 0]),
    ("all_nonpositive", (-3, 0), [-1, 1]),
    ("all_positive", [1, 3], [1, 0]),
    ("all_nonnegative", (0, 3), [-1, 3]),
    ("palindrome", "aba", "ab"),
])
def test_declared_properties_accept_and_reject_expected_values(property_name, valid, invalid):
    requirements = [{"parameter": "value", "property": property_name}]
    validate_context_requirements(requirements, {"value": valid})
    with pytest.raises(ValueError, match="context_requirement_not_met"):
        validate_context_requirements(requirements, {"value": invalid})


@pytest.mark.parametrize("value", [[], [True], [float("nan")], ["-1"]])
def test_sign_requirements_need_a_nonempty_finite_numeric_sequence(value):
    with pytest.raises(ValueError, match="context_requirement_not_met"):
        validate_context_requirements([{"parameter": "value", "property": "all_nonnegative"}], {"value": value})


def test_run_context_can_be_token_only_and_is_checked_after_construction(tmp_path):
    selected = selected_sum()
    selected["boundaries"] = [{"id": "b1", "template_id": "text:run_length",
        "characteristic": {"parameter": "text", "operation": "run_length", "token": " "},
        "threshold": {"kind": "constant", "value": 2}, "comparison": ">", "boundary_kind": "behavior",
        "neighborhood": {"mode": "step", "step": 1}, "target_sides": ["below", "at", "above"],
        "source_quote": "consecutive spaces", "constraints": [], "explanation": "Inspect adjacent run sizes."}]
    requirement = [{"parameter": "text", "property": "token_only", "token": " "}]
    records = [{"obligation_id": "b1:" + side, "arguments": {"text": ""},
                "context_requirements": requirement} for side in ("below", "at", "above")]
    records.append({"obligation_id": "b1:at", "arguments": {"text": "a b"},
                    "context_requirements": requirement})
    result = run_contexts(tmp_path, records, selected=selected,
                          specification='def f(text: str):\n    """Process consecutive spaces."""\n',
                          source='def f(text):\n    return text\n')
    assert [ast.literal_eval(item["args"])[0] for item in result["inputs"]] == [" ", "  ", "   "]
    assert result["rejected"] == [{"index": 3, "reason": "context_requirement_not_met"}]


def test_arm_and_standalone_use_the_same_selection_budget():
    assert BoundarySettings().selection_tokens == BoundaryArm().selection_tokens == 4096


@pytest.mark.parametrize("origin", ["code", "edge"])
def test_valid_code_and_edge_boundaries_need_no_threshold_in_spec(tmp_path, origin):
    quote = "Return the magnitude of integer x."
    selected = {"status": "selected", "reason": "Zero is sensitive to sign handling.", "boundaries": [{
        "id": "b1", "template_id": "x:value", "characteristic": {"parameter": "x", "operation": "value"},
        "threshold": {"kind": "constant", "value": 0}, "comparison": "==", "boundary_kind": "behavior",
        "neighborhood": {"mode": "step", "step": 1}, "target_sides": ["below", "at", "above"],
        "constraints": [], "source_quote": quote, "explanation": "Zero separates negative and positive values.",
        "origin": origin, "alignment": "code_only", "code_quote": "x == 0" if origin == "code" else "",
        "side_rules": {side: "magnitude" for side in ("below", "at", "above")}}]}
    calls = ScriptedCalls(selected)
    result = BoundaryValueAnalysis().run(task_number=0, program_id=0,
        specification='def f(x: int):\n    """' + quote + '"""\n', entry_point="f",
        program_source='def f(x):\n    if x == 0:\n        return 0\n    return abs(x)\n',
        base_inputs=[], artifacts=ArtifactStore(tmp_path), calls=calls)
    assert result["status"] == "generated"
    assert [ast.literal_eval(record["args"])[0] for record in result["inputs"]] == [-1, 0, 1]
    assert result["logical_calls"] == {"selection": True, "generation": False}
