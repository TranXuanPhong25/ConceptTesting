"""Spec-derived string boundaries; engineering fixtures, no live LLM calls."""
import ast
import copy
import json
import math
from pathlib import Path

import pytest

from final.src.modular.artifacts import ArtifactStore
from final.src.modular.arms.boundary import BoundaryArm
from final.src.modular.boundary_value_analysis import BoundarySettings, BoundaryValueAnalysis
from final.src.modular.boundary_value_analysis.binding import BoundaryGuidance
from final.src.modular.boundary_value_analysis.characteristics import characteristic_values, parsed_float
from final.src.modular.boundary_value_analysis.construction import instantiate_value, TargetCompiler
from final.src.modular.boundary_value_analysis.pipeline import BoundaryContext
from final.src.modular.boundary_value_analysis.prompts import selection_messages
from final.src.modular.boundary_value_analysis.stages import BoundarySelection
from final.src.modular.boundary_value_analysis.templates import BoundaryTemplates
from final.src.modular.boundary_value_analysis.types import InputTypeExtraction
from final.src.modular.context import PipelineSettings
from final.src.modular.pipeline import BenchmarkPipeline
from final.src.modular.tests.test_boundary_value_analysis import ScriptedCalls
from final.src.runtime.artifacts import digest, save
from final.src.modular.dataset import DATA_SHA256, load_tasks


def inspect_spec(specification, entry="f", source=None, base_inputs=None):
    ctx = BoundaryContext(200, "0", entry, specification, "", source or specification + "    pass\n",
                          base_inputs or [], BoundarySettings(), None, None)
    ctx.input_types = InputTypeExtraction().run(ctx)
    ctx.templates = BoundaryTemplates().run(ctx)
    ctx.guidance = BoundaryGuidance().run(ctx)
    return ctx


def from_guard(guard, *, identifier="b1"):
    return {"id": identifier, "template_id": guard["template_id"],
            "characteristic": guard["characteristic"], "threshold": guard["threshold"],
            "comparison": guard["comparison"], "boundary_kind": "behavior",
            "neighborhood": {"mode": "float_adjacent"} if guard["characteristic"]["operation"] == "parsed_float"
                            else {"mode": "step", "step": 1},
            "target_sides": ["below", "at", "above"], "constraints": [],
            "source_quote": guard["source_quote"], "explanation": "Apply the recorded public-spec derivation."}


def numeric_spec(parameter="raw"):
    return f'def f({parameter}: str):\n    """Given a numeric string, return the nearest integer."""\n'


@pytest.mark.parametrize("value", [-0.0, 5e-324, -5e-324, math.nextafter(-0.5, -math.inf),
                                  -0.5, math.nextafter(-0.5, math.inf), 1e300])
def test_numeric_string_constructor_preserves_exact_float_bits(value):
    feature = {"parameter": "raw", "operation": "parsed_float"}
    text = instantiate_value(feature, value, "unused context")
    actual = characteristic_values(feature, {"raw": text})[0]
    assert isinstance(text, str)
    assert actual.hex() == value.hex()


@pytest.mark.parametrize("text,reason", [("nan", "nonfinite_numeric_string"), ("inf", "nonfinite_numeric_string"),
    ("-inf", "nonfinite_numeric_string"), ("1e99999", "nonfinite_numeric_string"),
    ("", "invalid_numeric_string"), ("1 + 1", "invalid_numeric_string"),
    ("1" * 1001, "numeric_string_resource_limit"), (3, "numeric_string_required")])
def test_invalid_numeric_strings_have_specific_failure_reasons(text, reason):
    with pytest.raises(ValueError, match=reason):
        parsed_float(text)


def test_numeric_string_content_is_never_executed(tmp_path):
    marker = tmp_path / "forbidden"
    text = f"__import__('pathlib').Path({str(marker)!r}).touch()"
    with pytest.raises(ValueError, match="invalid_numeric_string"):
        parsed_float(text)
    assert not marker.exists()


@pytest.mark.parametrize("threshold", [2**53 + 1, 10**400])
def test_unrepresentable_integer_threshold_is_not_silently_rounded_to_a_float(threshold):
    ctx = inspect_spec(numeric_spec())
    selected = from_guard(ctx.guidance["candidate_guards"][0])
    selected["threshold"]["value"] = threshold
    selected["target_sides"] = ["at"]
    ctx.selection = {"boundaries": [BoundarySelection.validate(selected, ctx)]}
    compiled = TargetCompiler().run(ctx)
    assert compiled["obligations"] == []
    assert compiled["blocked"][0]["reason"] == "threshold_not_on_float_grid"


def test_numeric_string_inverse_does_not_silently_move_an_integer_target():
    with pytest.raises(ValueError, match="unrepresentable_float_target"):
        instantiate_value({"operation": "parsed_float"}, 2**53 + 1, "0.0")


def test_numeric_string_midpoints_have_public_projection_and_derivation_evidence():
    ctx = inspect_spec(numeric_spec())
    guards = ctx.guidance["candidate_guards"]
    assert {guard["threshold"]["value"] for guard in guards} == {-0.5, 0.5}
    assert ctx.guidance["domain_guards"] == []
    for guard in guards:
        checked = BoundarySelection.validate(from_guard(guard), ctx)
        assert checked["binding_evidence"]["derivation"]["rule"] == "nearest_integer_midpoint"
        assert checked["projection_evidence"][0]["source_quote"] == "numeric string"
    prompt = selection_messages(ctx)[1]["content"]
    assert '"projection_evidence"' in prompt and '"derivation"' in prompt


def test_parsed_float_remains_float_for_mixed_observed_input_types():
    ctx = inspect_spec(numeric_spec(), source="def f(raw):\n    pass\n",
                       base_inputs=[{"args": "(1,)", "kwargs": "{}"}, {"args": "('1',)", "kwargs": "{}"}])
    template = next(item for item in ctx.templates["candidates"] if item["id"] == "raw:parsed_float")
    assert template["numeric_kind"] == "float" and "float_adjacent" in template["neighborhood_modes"]


def test_put_conversion_and_numeric_observations_alone_do_not_define_spec_boundaries():
    ctx = inspect_spec('def f(raw: str):\n    """Return the length of raw."""\n',
                       source="def f(raw):\n    return float(raw)\n",
                       base_inputs=[{"args": "('123.5',)", "kwargs": "{}"}])
    assert ctx.guidance["projection_evidence"] == []
    guard = {"template_id": "raw:parsed_float", "characteristic": {"parameter": "raw", "operation": "parsed_float"},
             "threshold": {"kind": "constant", "value": 0.5}, "comparison": "==", "source_quote": "Return the length of raw."}
    with pytest.raises(ValueError, match="unverified_numeric_string_binding"):
        BoundarySelection.validate(from_guard(guard), ctx)


@pytest.mark.parametrize("declaration", ["not a numeric string", "a non-numeric string",
                                       "a numeric string. Do not return the nearest integer"])
def test_negated_numeric_or_rounding_declarations_do_not_create_midpoint_guards(declaration):
    ctx = inspect_spec(f'def f(raw: str):\n    """raw is {declaration}. Return its length."""\n')
    assert ctx.guidance["candidate_guards"] == []


@pytest.mark.parametrize("mask,length", [("mm-dd-yyyy", 10), ("yyyy/mm/dd", 10), ("HH:mm:ss", 8),
                                        ("YYYY-MM-DDTHH:mm:ss", 19)])
def test_fixed_format_length_is_derived_without_becoming_a_domain_precondition(mask, length):
    ctx = inspect_spec(f'def f(payload: str):\n    """Return True for valid data. It should be in the format: {mask}."""\n')
    guard = ctx.guidance["candidate_guards"][0]
    assert guard["threshold"] == {"kind": "constant", "value": length}
    assert guard["derivation"]["format_mask"] == mask
    assert ctx.guidance["domain_guards"] == []
    checked = BoundarySelection.validate(from_guard(guard), ctx)
    assert checked["binding_status"] == "matched_public_guard"
    wrong_role = {**from_guard(guard), "boundary_kind": "domain_lower", "comparison": ">=", "target_sides": ["at", "above"]}
    with pytest.raises(ValueError, match="unverified_domain_role"):
        BoundarySelection.validate(wrong_role, ctx)


@pytest.mark.parametrize("description", ["Example: mm-dd-yyyy.", "It should not be in the format: mm-dd-yyyy.",
    "It should be in the optional format: mm-dd-yyyy.", "It should be in the format: yyyy-mm-dd...",
    "It should be in the format: yyyy-mm-dd[timezone].", "It should be in the format: yyyy-mm-dd or yyyy/mm."])
def test_examples_negation_and_variable_formats_do_not_claim_fixed_width(description):
    ctx = inspect_spec(f'def f(payload: str):\n    """{description}"""\n')
    assert ctx.guidance["candidate_guards"] == []


def test_ambiguous_string_parameter_does_not_receive_an_unrelated_format_guard():
    ctx = inspect_spec('def f(first: str, second: str):\n    """It should be in the format: mm-dd-yyyy."""\n')
    assert ctx.guidance["candidate_guards"] == []


def test_spec_parameter_name_binds_format_guard_to_renamed_put_argument():
    ctx = inspect_spec('def f(date: str, label: str):\n    """date should be in the format: mm-dd-yyyy."""\n',
                       source="def f(renamed, label):\n    pass\n")
    assert len(ctx.guidance["candidate_guards"]) == 1
    assert ctx.guidance["candidate_guards"][0]["characteristic"]["parameter"] == "renamed"


def test_unverified_parsed_threshold_expression_is_also_rejected():
    spec = 'def f(raw: str, limit: str):\n    """raw is a numeric string. Compare it to limit."""\n'
    ctx = inspect_spec(spec)
    raw_template = next(item for item in ctx.templates["candidates"] if item["id"] == "raw:parsed_float")
    guard = {"template_id": raw_template["id"], "characteristic": raw_template["characteristic"],
             "threshold": {"kind": "expression", "parameter": "limit", "operation": "parsed_float"},
             "comparison": "<", "source_quote": "Compare it to limit."}
    with pytest.raises(ValueError, match="unverified_numeric_string_binding"):
        BoundarySelection.validate(from_guard(guard), ctx)


def test_declining_derived_format_guard_is_uncertain_and_does_not_force_inputs(tmp_path):
    spec = 'def f(raw: str):\n    """It should be in the format: yyyy/mm/dd."""\n'
    calls = ScriptedCalls({"status": "no_applicable_boundary", "reason": "No numeric length is quoted.", "boundaries": []})
    result = BoundaryValueAnalysis().run(task_number=200, program_id=0, specification=spec, entry_point="f",
        program_source=spec + "    pass\n", base_inputs=[], artifacts=ArtifactStore(tmp_path), calls=calls)
    assert result["status"] == "uncertain_binding" and result["inputs"] == [] and len(calls.requests) == 1


def test_string_boundaries_flow_through_injected_generator_freeze_and_corrected_oracle(tmp_path, monkeypatch):
    tasks_by_id = {task["task_id"]: task for task in load_tasks()}
    tasks = [{**tasks_by_id[task_id], "canonical_solution": "    raise RuntimeError('FORBIDDEN_ORACLE_CONTEXT')\n"}
             for task_id in ["HumanEval/99", "HumanEval/124"]]
    fixture_path = Path("final/data/fixtures/bva_string_puts.json")
    cohort = json.loads(fixture_path.read_text())
    records = [copy.deepcopy(row) for row in cohort["tasks"] if row["task_id"] in {task["task_id"] for task in tasks}]
    path = tmp_path / "cohort.json"
    save(path, {"tasks": records, "cohort_sha256": digest(records), "dataset_sha256": DATA_SHA256})
    metadata = json.loads(Path("final/data/contracts.json").read_text())
    inspections = [inspect_spec(task["prompt"], task["entry_point"], record["programs"][0]["code"],
                               record["programs"][0]["base"]["calls"]) for task, record in zip(tasks, records)]
    rounding = next(guard for guard in inspections[0].guidance["candidate_guards"] if guard["threshold"]["value"] == -0.5)
    formatting = inspections[1].guidance["candidate_guards"][0]
    def selected(guard):
        return {"status": "selected", "reason": "Use the supplied public-spec guard.", "boundaries": [from_guard(guard)]}
    calls = ScriptedCalls(selected(rounding), selected(formatting), {"inputs": [
        {"obligation_id": f"b1:{side}", "arguments": {"date": "01-01-2042"}} for side in ["below", "at", "above"]]})
    from final.src.modular.generators.methods import MethodInputGenerator
    generator = MethodInputGenerator([BoundaryArm()])
    artifacts = ArtifactStore(tmp_path / "run")
    pipeline = BenchmarkPipeline(path, artifacts, input_generator=generator, calls=calls,
        settings=PipelineSettings(target_programs=1, input_budget=6))
    original_run = pipeline.evaluation_stages[0].run
    def verify_freeze(context):
        freeze = artifacts.read("generation_frozen.json")
        assert len(freeze["inputs"]) == 2 and context.inputs_frozen
        return original_run(context)
    monkeypatch.setattr(pipeline.evaluation_stages[0], "run", verify_freeze)
    summary = pipeline.run(tasks, metadata)
    assert summary["arms"]["boundary"]["valid_inputs"] == 6
    assert summary["arms"]["boundary"]["detected"] == 2
    assert [request["call_name"] for request in calls.requests] == ["bva_0_select", "bva_0_select", "bva_0_inputs"]
    assert "FORBIDDEN_ORACLE_CONTEXT" not in json.dumps(calls.requests)
    inputs = artifacts.read("tasks/99/inputs.json")["arms"]["boundary"]["inputs"]
    assert [float(ast.literal_eval(item["args"])[0]) for item in inputs] == [
        math.nextafter(-0.5, -math.inf), -0.5, math.nextafter(-0.5, math.inf)]
    assert artifacts.read("tasks/99/reference_program.json")["version"] == "v0.1.10"
