"""Regression cases from the saved BVA failures; no real LLM/PUT execution."""
import ast
import copy
import json
import math
from pathlib import Path

import pytest

from final.src.modular.dataset import load_tasks
from final.src.modular.call_builder import CallBuilder
from final.src.modular.boundary_value_analysis import BoundarySettings, BoundaryValueAnalysis
from final.src.modular.boundary_value_analysis.pipeline import BoundaryContext
from final.src.modular.boundary_value_analysis.types import InputTypeExtraction
from final.src.modular.boundary_value_analysis.templates import BoundaryTemplates
from final.src.modular.boundary_value_analysis.binding import BoundaryGuidance
from final.src.modular.boundary_value_analysis.characteristics import characteristic_values
from final.src.modular.boundary_value_analysis.construction import TargetCompiler
from final.src.modular.boundary_value_analysis.stages import BoundarySelection
from final.src.modular.tests.test_boundary_value_analysis import ScriptedCalls
from final.src.modular.artifacts import ArtifactStore
from final.src.modular.context import TaskContext, PipelineSettings
from final.src.modular.arms.plain import PlainArm
from final.src.runtime.execution import execute


TASKS = {task["task_id"]: task for task in load_tasks()}
METADATA = json.loads(Path("final/data/contracts.json").read_text())
VALUES = {0: {"numbers": [0.0, 1.0], "threshold": 0.5}, 21: {"numbers": [1.0, 2.0]},
          30: {"l": [-1, 1]}, 52: {"l": [1, 2], "t": 3}, 81: {"grades": [1.0, 2.0]},
          96: {"n": 0}, 138: {"n": 4}, 140: {"text": "a b"},
          146: {"nums": [11, 12]}, 115: {"grid": [[0]], "capacity": 1}}


def context(number, base_values=None):
    task = TASKS[f"HumanEval/{number}"]
    source = task["prompt"] + "    pass\n"
    builder = CallBuilder.for_source(source, task["entry_point"])
    values = [VALUES[number]] if base_values is None else base_values
    result = BoundaryContext(number, "0", task["entry_point"], task["prompt"], METADATA[task["task_id"]]["contract"],
        source, [builder.build_values(item) for item in values], BoundarySettings(), None, None)
    result.input_types = InputTypeExtraction().run(result)
    result.templates = BoundaryTemplates().run(result)
    result.guidance = BoundaryGuidance().run(result)
    return result


def boundary(parameter, operation, threshold, quote, *, comparison=">", kind="behavior", sides=None, mode="step", token=None):
    characteristic = {"parameter": parameter, "operation": operation}
    if token is not None:
        characteristic["token"] = token
    return {"id": "b1", "template_id": f"{parameter}:{operation}", "characteristic": characteristic,
            "threshold": {"kind": "constant", "value": threshold}, "comparison": comparison,
            "boundary_kind": kind, "neighborhood": {"mode": mode, **({"step": 1} if mode == "step" else {})},
            "target_sides": sides or ["below", "at", "above"], "constraints": [],
            "source_quote": quote, "explanation": "Boundary obligation derived from public specification."}


def compile_boundary(ctx, selected):
    validated = BoundarySelection.validate(selected, ctx)
    ctx.selection = {"status": "selected", "boundaries": [validated]}
    ctx.construction = TargetCompiler().run(ctx)
    return ctx.construction


def instantiate(ctx, side, values):
    obligation = next(item for item in ctx.construction["obligations"] if item["side"] == side)
    return TargetCompiler.build_input(ctx, obligation, values, set())


def assert_contract_valid(number, record):
    task = TASKS[f"HumanEval/{number}"]
    result = execute({"mode": "validate", "context": task["prompt"], "source": "",
                      "entry": task["entry_point"], "contract": METADATA[task["task_id"]]["contract"],
                      "tests": [record], "timeout": 3})
    assert result["tests"][0]["status"] == "valid"


def test_shared_builder_handles_singleton_string_and_keyword_only_defaults():
    builder = CallBuilder.for_source("def f(text, /, *, flag=True):\n    pass\n", "f")
    record = builder.build({"text": "  "})
    assert ast.literal_eval(record["args"]) == ("  ",)
    assert record["kwargs"] == "{'flag': True}"
    assert record["args"] == "('  ',)"


def test_shared_builder_preserves_tagged_tuple_set_and_nested_arrays():
    builder = CallBuilder.for_source("def f(data, coordinates, items):\n    pass\n", "f")
    record = builder.build({"data": [[0], [1]], "coordinates": {"__python_type__": "tuple", "items": [1, 2]},
                            "items": {"__python_type__": "set", "items": [1, 2]}})
    assert ast.literal_eval(record["args"]) == ([[0], [1]], (1, 2), {1, 2})


@pytest.mark.parametrize("values", [{"wrong": 1}, {}, {"value": float("inf")},
                                   {"value": {"__python_type__": "expression", "items": ["danger()"]}}])
def test_builder_rejects_invalid_named_calls(values):
    builder = CallBuilder.for_source("def f(value):\n    pass\n", "f")
    with pytest.raises(ValueError):
        builder.build(values)


def test_builder_never_executes_default_expressions_or_string_content(tmp_path):
    marker = tmp_path / "forbidden"
    text = f"__import__('pathlib').Path({str(marker)!r}).touch()"
    builder = CallBuilder.for_source("def f(text):\n    pass\n", "f")
    assert ast.literal_eval(builder.build({"text": text})["args"]) == (text,)
    with pytest.raises(ValueError):
        CallBuilder.for_source("def f(text=evil()):\n    pass\n", "f")
    assert not marker.exists()


def test_threshold_zero_float_neighbor_is_computed_not_guessed():
    ctx = context(0)
    selected = boundary("threshold", "value", 0, "threshold > 0", kind="domain_lower",
                        comparison=">", sides=["above"], mode="float_adjacent")
    compile_boundary(ctx, selected)
    record = instantiate(ctx, "above", {"numbers": [0.0, 0.0]})
    args = ast.literal_eval(record["args"])
    assert args[1] == math.nextafter(0.0, math.inf) == 5e-324
    assert_contract_valid(0, record)


def test_grade_float_target_round_trips_as_literal_and_respects_domain():
    ctx = context(81)
    selected = boundary("grades", "elements", 3.7, "3.7", sides=["above"], mode="float_adjacent")
    compile_boundary(ctx, selected)
    record = instantiate(ctx, "above", {"grades": [2.0, 1.0]})
    grades = ast.literal_eval(record["args"])[0]
    assert grades[0] == math.nextafter(3.7, math.inf) and grades[0] > 3.7
    assert_contract_valid(81, record)


def test_run_length_changes_the_run_not_the_whole_string():
    ctx = context(140)
    selected = boundary("text", "run_length", 2, "more than 2 consecutive spaces", token=" ", sides=["at", "above"])
    compile_boundary(ctx, selected)
    record = instantiate(ctx, "at", {"text": "prefix suffix"})
    text = ast.literal_eval(record["args"])[0]
    assert text == "prefix  suffix" and len(text) != 2
    assert characteristic_values(selected["characteristic"], {"text": text}) == [2]
    assert_contract_valid(140, record)
    wrong = boundary("text", "length", 2, "more than 2 consecutive spaces")
    with pytest.raises(ValueError, match="consecutive_run_requires_run_length"):
        BoundarySelection.validate(wrong, ctx)


def test_behavior_threshold_is_not_an_input_precondition():
    ctx = context(138)
    quote = "sum of exactly 4 positive even numbers"
    wrong = boundary("n", "value", 8, quote, kind="domain_lower", comparison=">=", sides=["at", "above"])
    with pytest.raises(ValueError, match="unverified_domain_role"):
        BoundarySelection.validate(wrong, ctx)
    selected = boundary("n", "value", 8, quote)
    compiled = compile_boundary(ctx, selected)
    below = next(item for item in compiled["closed_inputs"] if item["side"] == "below")
    assert ast.literal_eval(below["args"]) == (7,)
    assert_contract_valid(138, below)


def test_extrema_difference_binds_range_and_constructs_nonzero_spread():
    ctx = context(21)
    guard = next(item for item in ctx.guidance["domain_guards"] if item["characteristic"]["operation"] == "range")
    selected = boundary("numbers", "range", 0, guard["source_quote"], kind="domain_lower", sides=["above"], mode="float_adjacent")
    compile_boundary(ctx, selected)
    record = instantiate(ctx, "above", {"numbers": [0.0, 1.0]})
    numbers = ast.literal_eval(record["args"])[0]
    assert max(numbers) - min(numbers) == math.nextafter(0.0, math.inf)
    assert_contract_valid(21, record)
    wrong = boundary("numbers", "elements", 0, guard["source_quote"])
    with pytest.raises(ValueError, match="extrema_difference_requires_range"):
        BoundarySelection.validate(wrong, ctx)


@pytest.mark.parametrize("number,operation,threshold", [(30, "elements", 0), (52, "maximum", "t"), (146, "elements", 10)])
def test_obvious_filter_and_relational_guards_are_presented_to_selection(number, operation, threshold):
    guards = context(number).guidance["candidate_guards"]
    assert any(item["characteristic"]["operation"] == operation and
               (item["threshold"].get("value") == threshold or item["threshold"].get("parameter") == threshold)
               for item in guards)


def test_relational_universal_boundary_uses_maximum_and_preserves_limit():
    ctx = context(52)
    selected = boundary("l", "maximum", 0, "below threshold t", comparison="<", sides=["at", "above", "below"])
    selected["threshold"] = {"kind": "expression", "parameter": "t", "operation": "value"}
    compile_boundary(ctx, selected)
    record = instantiate(ctx, "below", {"l": [100, 0, -1], "t": 5})
    values, limit = ast.literal_eval(record["args"])
    assert limit == 5 and max(values) == 4 and all(value < limit for value in values)


def test_large_list_is_materialized_by_code_without_literal_expressions():
    ctx = context(21)
    # A behavior boundary here is only a constructor fixture, not a spec claim.
    selected = boundary("numbers", "length", 1000, "at least two elements", sides=["at"])
    compile_boundary(ctx, selected)
    record = instantiate(ctx, "at", {"numbers": [0.0, 1.0]})
    values = ast.literal_eval(record["args"])[0]
    assert len(values) == 1000 and len(record["args"]) < 16000


def test_grid_arguments_are_encoded_and_outer_length_constructed_safely():
    ctx = context(115)
    guard = next(item for item in ctx.guidance["domain_guards"] if item["characteristic"]["parameter"] == "grid"
                 and item["comparison"] == "<=")
    selected = boundary("grid", "length", 100, guard["source_quote"], kind="domain_upper", comparison="<=", sides=["at"])
    compile_boundary(ctx, selected)
    record = instantiate(ctx, "at", {"grid": [[0]], "capacity": 1})
    grid, capacity = ast.literal_eval(record["args"])
    assert len(grid) == 100 and all(row == [0] for row in grid) and capacity == 1
    assert_contract_valid(115, record)


def test_known_domain_checks_filter_joint_constraint_violations():
    ctx = context(81)
    selected = boundary("grades", "elements", 3.7, "3.7", sides=["at"])
    compile_boundary(ctx, selected)
    with pytest.raises(ValueError, match="recognized_domain_constraint_failed"):
        instantiate(ctx, "at", {"grades": [2.0, 99.0]})


def test_or_precondition_does_not_turn_into_two_required_clauses():
    ctx = context(138)
    ctx.contract = "\n    assert n == 0 or n >= 10\n"
    assert BoundaryGuidance().run(ctx)["domain_guards"] == []


def test_exact_scalar_base_inputs_skip_context_call(tmp_path):
    ctx = context(96, [{"n": 0}, {"n": 1}])
    guard = ctx.guidance["domain_guards"][0]
    selected = boundary("n", "value", 0, guard["source_quote"], kind="domain_lower", comparison=">=", sides=["at", "above"])
    calls = ScriptedCalls({"status": "selected", "reason": "Public lower input bound.", "boundaries": [selected]})
    result = BoundaryValueAnalysis().run(task_number=96, program_id=0, specification=ctx.specification,
        entry_point=ctx.entry_point, program_source=ctx.program_source, base_inputs=ctx.base_inputs,
        artifacts=ArtifactStore(tmp_path), calls=calls, contract=ctx.contract)
    assert result["status"] == "already_covered_inputs" and result["inputs"] == []
    assert result["logical_calls"] == {"selection": True, "generation": False}
    assert len(calls.requests) == 1


def test_new_context_protocol_compiles_targets_and_replays_without_model(tmp_path):
    ctx = context(140)
    selected = boundary("text", "run_length", 2, "more than 2 consecutive spaces", token=" ", sides=["at", "above"])
    calls = ScriptedCalls({"status": "selected", "reason": "Explicit consecutive-space threshold.", "boundaries": [selected]},
        {"inputs": [{"obligation_id": "b1:at", "arguments": {"text": "left right"}},
                    {"obligation_id": "b1:above", "arguments": {"text": "prefix suffix"}}]})
    arguments = dict(task_number=140, program_id=0, specification=ctx.specification, entry_point=ctx.entry_point,
                     program_source=ctx.program_source, base_inputs=ctx.base_inputs, contract=ctx.contract)
    expected = BoundaryValueAnalysis().run(**arguments, artifacts=ArtifactStore(tmp_path), calls=calls)
    assert expected["status"] == "generated"
    assert [ast.literal_eval(item["args"])[0] for item in expected["inputs"]] == ["left  right", "prefix   suffix"]
    assert expected["logical_calls"] == {"selection": True, "generation": True}
    assert "compiled_obligations" in calls.requests[1]["messages"][1]["content"]
    actual = BoundaryValueAnalysis().run(**arguments, artifacts=ArtifactStore(tmp_path, read_only=True))
    assert actual == expected


def test_plain_uses_the_same_named_argument_builder(tmp_path):
    task = TASKS["HumanEval/140"]
    calls = ScriptedCalls({"inputs": [{"arguments": {"text": "  "}}]})
    ctx = TaskContext(task, METADATA[task["task_id"]], ArtifactStore(tmp_path), PipelineSettings(), calls)
    ctx.packet = {"common": "Generate named arguments."}
    result = PlainArm().run(ctx)
    assert ast.literal_eval(result["inputs"][0]["args"]) == ("  ",)


def test_declining_a_supported_guard_is_uncertain_not_proven_inapplicable(tmp_path):
    ctx = context(30)
    calls = ScriptedCalls({"status": "no_applicable_boundary", "reason": "No fixed bounds.", "boundaries": []})
    result = BoundaryValueAnalysis().run(task_number=30, program_id=0, specification=ctx.specification,
        entry_point=ctx.entry_point, program_source=ctx.program_source, base_inputs=ctx.base_inputs,
        artifacts=ArtifactStore(tmp_path), calls=calls, contract=ctx.contract)
    assert result["status"] == "uncertain_binding" and len(calls.requests) == 1


@pytest.mark.parametrize("threshold,reason", [(-1, "characteristic_has_no_negative_values"),
                                            (1001, "construction_resource_limit"),
                                            (0.5, "threshold_not_on_integer_grid")])
def test_unavailable_length_targets_are_classified_before_context_generation(threshold, reason):
    ctx = context(140)
    selected = boundary("text", "length", threshold, "Given a string text", sides=["at"])
    compiled = compile_boundary(ctx, selected)
    assert compiled["obligations"] == []
    assert compiled["blocked"][0]["reason"] == reason


def test_unknown_obligation_keeps_a_specific_failure_reason(tmp_path):
    ctx = context(140)
    selected = boundary("text", "run_length", 2, "more than 2 consecutive spaces", token=" ", sides=["at"])
    calls = ScriptedCalls({"status": "selected", "reason": "Consecutive-space cutoff.", "boundaries": [selected]},
                           {"inputs": [{"obligation_id": "invented", "arguments": {"text": "left right"}}]})
    result = BoundaryValueAnalysis().run(task_number=140, program_id=0, specification=ctx.specification,
        entry_point=ctx.entry_point, program_source=ctx.program_source, base_inputs=ctx.base_inputs,
        artifacts=ArtifactStore(tmp_path), calls=calls, contract=ctx.contract)
    assert result["rejected"] == [{"index": 0, "reason": "unknown_obligation_id"}]


def test_context_budget_is_split_before_model_contexts_are_observed():
    ctx = context(140)
    ctx.settings = BoundarySettings(input_budget=5)
    compiled = compile_boundary(ctx, boundary("text", "run_length", 2, "more than 2 consecutive spaces",
                                              token=" ", sides=["at", "above"]))
    assert [item["context_budget"] for item in compiled["obligations"]] == [3, 2]


def test_contexts_cannot_consume_another_obligations_budget(tmp_path):
    ctx = context(140)
    selected = boundary("text", "run_length", 2, "more than 2 consecutive spaces", token=" ", sides=["at", "above"])
    calls = ScriptedCalls({"status": "selected", "reason": "Explicit run cutoff.", "boundaries": [selected]},
                          {"inputs": [{"obligation_id": "b1:at", "arguments": {"text": "left right"}},
                                      {"obligation_id": "b1:at", "arguments": {"text": "another context"}}]})
    result = BoundaryValueAnalysis(BoundarySettings(input_budget=2)).run(task_number=140, program_id=0,
        specification=ctx.specification, entry_point=ctx.entry_point, program_source=ctx.program_source,
        base_inputs=ctx.base_inputs, artifacts=ArtifactStore(tmp_path), calls=calls, contract=ctx.contract)
    assert len(result["inputs"]) == 1
    assert result["rejected"] == [{"index": 1, "reason": "obligation_budget_exceeded"}]


@pytest.mark.parametrize("contract", ["n = abs(n)\nassert n > 0\n", "assert unknown_predicate(n)\nassert n > 0\n"])
def test_mutated_or_unknown_predicate_inputs_do_not_become_necessary_guards(contract):
    ctx = context(138)
    ctx.contract = contract
    assert BoundaryGuidance().run(ctx)["domain_guards"] == []


def test_conditional_length_requirement_is_not_an_input_precondition():
    ctx = context(140)
    ctx.contract = ""
    ctx.specification = 'def f(text: str):\n    """Return True if text has at least two characters."""\n'
    guidance = BoundaryGuidance().run(ctx)
    assert guidance["domain_guards"] == []
    assert any(item["characteristic"]["operation"] == "length" for item in guidance["candidate_guards"])


def test_opaque_grid_preparation_does_not_erase_independent_capacity_bounds():
    guards = context(115).guidance["domain_guards"]
    assert any(item["characteristic"]["parameter"] == "capacity" and item["comparison"] == ">=" for item in guards)
    assert any(item["characteristic"]["parameter"] == "capacity" and item["comparison"] == "<=" for item in guards)
