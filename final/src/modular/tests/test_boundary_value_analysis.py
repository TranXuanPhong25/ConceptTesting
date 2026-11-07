"""Legacy selection/context behavior with scripted responses; no endpoint/PUT execution."""
import json
from dataclasses import replace

import pytest

from final.src.core_model import ModelResponse
from final.src.modular.artifacts import ArtifactStore
from final.src.modular.boundary_value_analysis.legacy import BoundarySettings, BoundaryValueAnalysis


SPECIFICATION = 'def choose(xs: list[int]):\n    """Return the sum. xs has at least two elements."""\n'
SOURCE = 'def choose(xs):\n    return sum(xs)\n'
QUOTE = 'xs has at least two elements.'


def selection():
    return {"status": "selected", "reason": "The specification supplies a minimum length.", "boundaries": [{
        "id": "b1", "template_id": "xs:length", "characteristic": {"parameter": "xs", "operation": "length"},
        "threshold": {"kind": "constant", "value": 2}, "comparison": ">=", "boundary_kind": "domain_lower",
        "neighborhood": {"mode": "step", "step": 1}, "target_sides": ["at", "above"],
        "constraints": [{"description": "Use a list with at least two integers.", "source_quote": QUOTE}],
        "source_quote": QUOTE, "explanation": "Length two is the lower valid boundary.",
    }]}


def generated(arguments="([5, 6],)", side="at", **extra):
    return {"args": arguments, "kwargs": "{}", "boundary_id": "b1", "side": side, **extra}


class ScriptedCalls:
    model_id = "boundary-fixture"

    def __init__(self, *responses, prompt_tokens=100):
        self.responses = list(responses)
        self.requests = []
        self.prompt_tokens = prompt_tokens

    def token_count(self, messages):
        return self.prompt_tokens

    def complete(self, task_number, call_name, messages, **settings):
        self.requests.append({"task_number": task_number, "call_name": call_name,
                              "messages": messages, "settings": settings})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        if isinstance(response, ModelResponse):
            return response
        return ModelResponse(json.dumps(response), finish_reason="stop")


def run(tmp_path, calls=None, **overrides):
    arguments = {
        "task_number": 7, "program_id": 2, "specification": SPECIFICATION,
        "entry_point": "choose", "program_source": SOURCE,
        "base_inputs": [{"args": "([1, 2, 3],)", "kwargs": "{}"}],
        "contract": "All elements are integers.", "calls": calls,
        "artifacts": ArtifactStore(tmp_path),
    }
    arguments.update(overrides)
    return BoundaryValueAnalysis(BoundarySettings(construction_mode="literal")).run(**arguments)


def test_types_come_from_observations_and_annotations_without_running_source(tmp_path):
    marker = tmp_path / "must_not_exist"
    source = f'raise RuntimeError("must not run")\ndef f(xs, flag: bool):\n    return open({str(marker)!r}, "w")\n'
    report = BoundaryValueAnalysis().extract(
        specification='def f(xs: list[int], flag: bool):\n    pass\n', entry_point="f", program_source=source,
        base_inputs=[{"args": "([], True)", "kwargs": "{}"}])
    candidates = report["templates"]["candidates"]
    assert {item["id"] for item in candidates} == {
        "xs:length", "xs:elements", "xs:sum", "xs:range", "xs:minimum", "xs:maximum"}
    assert not marker.exists()
    assert {record["source"] for record in report["input_types"]["parameters"][0]["evidence"]} == {
        "observed_input", "spec_annotation"}


@pytest.mark.parametrize("source,base", [
    ("def choose(flag: bool):\n    return flag\n", [{"args": "(True,)", "kwargs": "{}"}]),
    ("def choose(value):\n    return value\n", []),
    ("def choose(color: Color):\n    return color\n", []),
])
def test_no_templates_skips_both_model_calls(tmp_path, source, base):
    calls = ScriptedCalls()
    result = run(tmp_path, calls, specification="No numeric domain is specified.", program_source=source,
                 base_inputs=base)
    assert result["status"] == "no_templates"
    assert result["inputs"] == []
    assert calls.requests == []
    assert not (tmp_path / "tasks/7/boundary/2/selection.json").exists()


def test_bool_is_not_treated_as_int_and_observed_ranges_are_not_bounds():
    report = BoundaryValueAnalysis().extract(specification="", entry_point="f",
        program_source="def f(x, flag):\n    return 0\n",
        base_inputs=[{"bound": {"x": "100", "flag": "True"}}, {"bound": {"x": "500", "flag": "False"}}])
    assert [template["id"] for template in report["templates"]["candidates"]] == ["x:value"]
    assert "100" not in json.dumps(report["templates"])
    assert "500" not in json.dumps(report["templates"])


def test_saved_calls_bind_positional_arguments_to_actual_put_parameter_names():
    report = BoundaryValueAnalysis().extract(specification="", entry_point="f",
        program_source="def f(renamed):\n    return 0\n",
        base_inputs=[{"args": "([2],)", "kwargs": "{}", "bound": {"spec_name": "[2]"}}])
    assert "renamed:length" in [item["id"] for item in report["templates"]["candidates"]]
    assert not report["input_types"]["rejected"]


def test_no_boundary_skips_generation_and_preserves_reason(tmp_path):
    calls = ScriptedCalls({"status": "no_boundary", "reason": "No supported threshold.", "boundaries": []})
    result = run(tmp_path, calls)
    assert result["status"] == "no_boundary"
    assert result["reason"] == "No supported threshold."
    assert [item["call_name"] for item in calls.requests] == ["bva_2_select"]
    assert result["logical_calls"] == {"selection": True, "generation": False}


def test_two_calls_feed_selected_domains_to_input_generation(tmp_path):
    calls = ScriptedCalls(selection(), {"inputs": [generated(), generated("([7, 8, 9],)", "above")]})
    result = run(tmp_path, calls)
    assert result["status"] == "generated"
    assert len(result["inputs"]) == 2
    assert [item["call_name"] for item in calls.requests] == ["bva_2_select", "bva_2_inputs"]
    assert calls.requests[0]["settings"]["temperature"] == 0
    assert calls.requests[1]["settings"]["temperature"] == .7
    assert QUOTE in calls.requests[1]["messages"][1]["content"]
    assert '"threshold": {"kind": "constant", "value": 2}' in calls.requests[1]["messages"][1]["content"]
    assert result["inputs"][0]["validation"]["domain_constraints"] == "unverified"
    assert all(item["validation"]["boundary_target"] == "passed" for item in result["inputs"])


@pytest.mark.parametrize("mutation", [
    {"source_quote": "Invented requirement."},
    {"template_id": "unknown:length"},
    {"characteristic": {"parameter": "xs", "operation": "eval"}},
    {"threshold": {"kind": "constant", "value": True}},
    {"target_sides": ["below", "at"]},
    {"neighborhood": {"mode": "step", "step": 0}},
    {"neighborhood": {"mode": "float_adjacent"}},
    {"constraints": [{"description": "must be sorted", "source_quote": "sorted"}]},
])
def test_unsupported_or_ungrounded_selection_never_calls_generator(tmp_path, mutation):
    selected = selection()
    selected["boundaries"][0].update(mutation)
    calls = ScriptedCalls(selected)
    result = run(tmp_path, calls)
    assert result["status"] == "invalid_selection"
    assert len(calls.requests) == 1


@pytest.mark.parametrize("response", [
    ModelResponse("not JSON"),
    {"status": "selected", "reason": "empty", "boundaries": []},
    {"status": "no_boundary", "reason": "contradiction", "boundaries": selection()["boundaries"]},
])
def test_parse_failures_are_distinct_from_legitimate_no_boundary(tmp_path, response):
    calls = ScriptedCalls(response)
    assert run(tmp_path, calls)["status"] == "invalid_selection"
    assert len(calls.requests) == 1


@pytest.mark.parametrize("text", ['{"status":"selected",', json.dumps(selection())])
def test_truncated_selection_is_an_output_failure_not_no_boundary(tmp_path, text):
    calls = ScriptedCalls(ModelResponse(text, finish_reason="length"))
    result = run(tmp_path, calls)
    assert result["status"] == "selection_truncated"
    assert result["rejected"] == [{"reason": "truncated_response"}]
    assert result["logical_calls"] == {"selection": True, "generation": False}
    assert calls.requests[0]["settings"]["max_tokens"] == 4096


def test_wrong_side_wrong_target_and_base_duplicates_are_rejected(tmp_path):
    records = [generated("([1],)", "below"), generated("([1],)"),
               generated("([1, 2, 3],)", "above"), generated(),
               {**generated(), "args": "()", "kwargs": "{'xs': [5, 6]}"}]
    result = run(tmp_path, ScriptedCalls(selection(), {"inputs": records}))
    assert len(result["inputs"]) == 1
    assert [item["reason"] for item in result["rejected"]] == [
        "undeclared_side", "boundary_not_hit", "duplicate_input", "duplicate_input"]


def test_generation_never_executes_model_literals(tmp_path):
    marker = tmp_path / "forbidden"
    malicious = generated(f"(__import__('pathlib').Path({str(marker)!r}).touch(),)")
    result = run(tmp_path, ScriptedCalls(selection(), {"inputs": [malicious]}))
    assert result["status"] == "no_inputs"
    assert not marker.exists()


def test_relational_aggregate_boundary_uses_each_inputs_threshold(tmp_path):
    specification = 'def choose(xs: list[int], limit: int):\n    """Return whether sum(xs) <= limit."""\n'
    selected = selection()
    selected["boundaries"][0].update({
        "template_id": "xs:sum", "characteristic": {"parameter": "xs", "operation": "sum"},
        "threshold": {"kind": "expression", "parameter": "limit", "operation": "value"},
        "boundary_kind": "behavior", "comparison": "<=", "target_sides": ["below", "at", "above"],
        "source_quote": "sum(xs) <= limit", "constraints": [],
    })
    calls = ScriptedCalls(selected, {"inputs": [generated("([2, 3], 5)"),
                                               generated("([2, 3], 6)", "below"),
                                               generated("([2, 3], 7)", "below")]})
    result = run(tmp_path, calls, specification=specification,
                 program_source="def choose(xs, limit):\n    return sum(xs) <= limit\n", base_inputs=[])
    assert len(result["inputs"]) == 2
    assert result["rejected"] == [{"index": 2, "reason": "boundary_not_hit"}]


def test_float_adjacent_uses_representable_neighbor(tmp_path):
    import math

    selected = selection()
    selected["boundaries"][0].update({
        "template_id": "value:value", "characteristic": {"parameter": "value", "operation": "value"},
        "threshold": {"kind": "constant", "value": 1.0}, "boundary_kind": "behavior",
        "neighborhood": {"mode": "float_adjacent"}, "source_quote": "value < 1.0", "constraints": [],
        "comparison": "<", "target_sides": ["below", "at", "above"],
    })
    calls = ScriptedCalls(selected, {"inputs": [generated(repr((math.nextafter(1.0, -math.inf),)), "below"),
                                               generated("(0.99,)", "below")]})
    result = run(tmp_path, calls, specification="Return whether value < 1.0.",
                 program_source="def choose(value: float):\n    return value < 1.0\n", base_inputs=[])
    assert len(result["inputs"]) == 1
    assert result["rejected"][0]["reason"] == "boundary_not_hit"


def test_transport_error_propagates_and_resume_reuses_selection(tmp_path):
    calls = ScriptedCalls(selection(), RuntimeError("transport unavailable"))
    with pytest.raises(RuntimeError, match="transport unavailable"):
        run(tmp_path, calls)
    assert (tmp_path / "tasks/7/boundary/2/selection.json").exists()
    assert not (tmp_path / "tasks/7/boundary/2/result.json").exists()
    resumed = ScriptedCalls({"inputs": [generated()]})
    assert run(tmp_path, resumed)["status"] == "generated"
    assert [request["call_name"] for request in resumed.requests] == ["bva_2_inputs"]


def test_cache_replay_uses_no_model_and_changes_no_artifact(tmp_path):
    expected = run(tmp_path, ScriptedCalls(selection(), {"inputs": [generated()]}))
    before = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    actual = run(tmp_path, artifacts=ArtifactStore(tmp_path, read_only=True))
    assert actual == expected
    assert before == {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}


@pytest.mark.parametrize("field,value", [("program_source", SOURCE + "# changed\n"),
                                         ("contract", "different contract"),
                                         ("base_inputs", [])])
def test_cache_rejects_source_contract_or_input_drift(tmp_path, field, value):
    run(tmp_path, ScriptedCalls(selection(), {"inputs": [generated()]}))
    calls = ScriptedCalls()
    with pytest.raises(ValueError, match="Artifact changed"):
        run(tmp_path, calls, **{field: value})
    assert calls.requests == []


def test_oversized_prompt_skips_before_completion(tmp_path):
    calls = ScriptedCalls(prompt_tokens=8000)
    result = run(tmp_path, calls)
    assert result["status"] == "prompt_too_large"
    assert calls.requests == []
    assert result["logical_calls"] == {"selection": False, "generation": False}


def test_adapter_never_exposes_reference_plus_or_base_outputs(tmp_path):
    task = {"task_id": "HumanEval/7", "entry_point": "choose", "prompt": SPECIFICATION,
            "canonical_solution": "SECRET_REFERENCE", "plus_input": "SECRET_PLUS"}
    program = {"id": 2, "code": SOURCE, "base": {"calls": [
        {"args": "([1, 2, 3],)", "kwargs": "{}", "expected": "SECRET_OUTPUT"}]}}
    calls = ScriptedCalls(selection(), {"inputs": [generated()]})
    result = BoundaryValueAnalysis().run_for_program(task, program, artifacts=ArtifactStore(tmp_path), calls=calls)
    assert result["status"] == "generated"
    assert "SECRET" not in json.dumps(calls.requests)


def test_positional_only_keyword_only_and_literal_defaults(tmp_path):
    source = "def choose(xs, /, *, flag=True):\n    return sum(xs)\n"
    calls = ScriptedCalls(selection(), {"inputs": [generated(),
        {**generated(), "args": "()", "kwargs": "{'xs': [6, 7]}"}]})
    result = run(tmp_path, calls, program_source=source)
    assert len(result["inputs"]) == 1
    assert len(result["rejected"]) == 1


@pytest.mark.parametrize("source", ["def choose(*args):\n    return 0\n",
                                     "def choose(xs=make_list()):\n    return xs\n"])
def test_unsupported_signatures_do_not_call_model(tmp_path, source):
    calls = ScriptedCalls()
    assert run(tmp_path, calls, program_source=source)["status"] == "unsupported_signature"
    assert not calls.requests


def test_malformed_and_empty_generation_are_distinguishable(tmp_path):
    invalid = run(tmp_path / "invalid", ScriptedCalls(selection(), ModelResponse("broken")))
    empty = run(tmp_path / "empty", ScriptedCalls(selection(), {"inputs": [], "reason": "Cannot construct input."}))
    assert invalid["status"] == "invalid_generation"
    assert empty["status"] == "no_inputs"
    assert "Cannot construct" in empty["reason"]


def test_input_budget_caps_generation_without_adding_fallback(tmp_path):
    settings = replace(BoundarySettings(), input_budget=1)
    calls = ScriptedCalls(selection(), {"inputs": [generated(), generated("([7, 8],)")]})
    result = BoundaryValueAnalysis(settings).run(task_number=7, program_id=2, specification=SPECIFICATION,
        entry_point="choose", program_source=SOURCE, base_inputs=[], artifacts=ArtifactStore(tmp_path), calls=calls)
    assert len(result["inputs"]) == 1
    assert result["rejected"] == [{"reason": "input_budget_exceeded", "count": 1}]


def test_repeated_base_types_are_compacted_but_all_duplicates_are_checked(tmp_path):
    base = [{"args": repr(([index, index + 1],)), "kwargs": "{}"} for index in range(50)]
    report = BoundaryValueAnalysis().extract(specification=SPECIFICATION, entry_point="choose",
                                            program_source=SOURCE, base_inputs=base)
    observed = [item for item in report["input_types"]["parameters"][0]["evidence"]
                if item["source"] == "observed_input"]
    assert len(observed) == 1
    assert observed[0]["observation_count"] == 50
    assert len(observed[0]["input_indices"]) == 8
    calls = ScriptedCalls(selection(), {"inputs": [generated("([49, 50],)")]})
    result = run(tmp_path, calls, base_inputs=base)
    assert result["rejected"] == [{"index": 0, "reason": "duplicate_input"}]
    assert '([49, 50],)' not in calls.requests[1]["messages"][1]["content"]


def test_selection_can_reject_one_candidate_and_keep_another(tmp_path):
    selected = selection()
    selected["boundaries"].append({**selected["boundaries"][0], "id": "bad", "source_quote": "invented"})
    result = run(tmp_path, ScriptedCalls(selected, {"inputs": [generated()]}))
    assert result["status"] == "generated"
    assert [boundary["id"] for boundary in result["boundaries"]] == ["b1"]
    saved = json.loads((tmp_path / "tasks/7/boundary/2/selection.json").read_text())
    assert saved["rejected"] == [{"index": 1, "reason": "quote_not_in_spec_or_contract"}]


def test_changed_settings_and_model_are_rejected_before_calls(tmp_path):
    run(tmp_path, ScriptedCalls(selection(), {"inputs": [generated()]}))
    calls = ScriptedCalls()
    calls.model_id = "different-model"
    with pytest.raises(ValueError, match="Artifact changed"):
        run(tmp_path, calls)
    settings = replace(BoundarySettings(), input_budget=5)
    with pytest.raises(ValueError, match="Artifact changed"):
        BoundaryValueAnalysis(settings).run(task_number=7, program_id=2, specification=SPECIFICATION,
            entry_point="choose", program_source=SOURCE, base_inputs=[{"args": "([1, 2, 3],)", "kwargs": "{}"}],
            contract="All elements are integers.", artifacts=ArtifactStore(tmp_path), calls=ScriptedCalls())
    assert not calls.requests


def test_read_only_missing_stage_cannot_call_a_live_model(tmp_path):
    run(tmp_path, ScriptedCalls(selection(), {"inputs": [generated()]}))
    calls = ScriptedCalls()
    with pytest.raises(ValueError, match="Read-only BVA"):
        run(tmp_path, calls, artifacts=ArtifactStore(tmp_path, read_only=True))
    (tmp_path / "tasks/7/boundary/2/generation.json").unlink()
    with pytest.raises(FileNotFoundError, match="Read-only replay requires"):
        run(tmp_path, artifacts=ArtifactStore(tmp_path, read_only=True))
    assert not calls.requests


def test_same_program_lock_prevents_duplicate_controller(tmp_path):
    import fcntl

    path = tmp_path / "tasks/7/boundary/2/.run.lock"
    path.parent.mkdir(parents=True)
    calls = ScriptedCalls()
    with path.open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(BlockingIOError):
            run(tmp_path, calls)
    assert not calls.requests


def selection_with_worksheet(**fields):
    record = selection()
    record["boundaries"][0].update(fields)
    return record


def test_selection_worksheet_reaches_the_input_prompt(tmp_path):
    worksheet = {"origin": "code", "alignment": "code_only", "code_quote": "return sum(xs)", "reach": "any call",
                 "infect": "2", "side_rules": {"at": "sum", "above": "sum"}}
    calls = ScriptedCalls(selection_with_worksheet(**worksheet), {"inputs": [], "reason": "No context."})
    result = run(tmp_path, calls)
    assert result["boundaries"][0]["reach"] == "any call"
    assert '"side_rules"' in calls.requests[1]["messages"][1]["content"]


@pytest.mark.parametrize("fields, reason", [
    ({"origin": "code"}, "code_origin_requires_code_quote"),
    ({"origin": "code", "code_quote": "xs[0] > 2"}, "code_quote_not_in_put"),
    ({"origin": "guess"}, "invalid_boundary_origin"),
    ({"side_rules": {"inside": "sum"}}, "invalid_side_rules"),
])
def test_invalid_worksheet_rejects_the_boundary_and_skips_generation(tmp_path, fields, reason):
    calls = ScriptedCalls(selection_with_worksheet(**fields))
    run(tmp_path, calls)
    saved = json.loads((tmp_path / "tasks/7/boundary/2/selection.json").read_text())
    assert saved["rejected"] == [{"index": 0, "reason": reason}]
    assert len(calls.requests) == 1


def test_no_boundary_keeps_the_suggested_technique(tmp_path):
    response = {"status": "no_applicable_boundary", "reason": "Unordered labels.", "boundaries": [],
                "better_technique": "decision_table"}
    run(tmp_path, ScriptedCalls(response))
    saved = json.loads((tmp_path / "tasks/7/boundary/2/selection.json").read_text())
    assert saved["better_technique"] == "decision_table"


def test_context_prompt_has_no_copyable_parameter_placeholder():
    from final.src.modular.boundary_value_analysis.legacy.prompts import CONTEXT_INSTRUCTIONS
    assert '"parameter":"JSON value"' not in CONTEXT_INSTRUCTIONS.format(input_budget=20)
