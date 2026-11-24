"""Unit and offline integration tests for VF3 measured catalogue arms."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from final.src.models.core_model import ModelResponse
from final.src.modular.arm_names import (
    CATALOGUE_ARM_NAMES,
    VF3_MEASURED_ARM_NAMES,
    generation_call_cap,
    retained_input_budget,
)
from final.src.modular.arms import available_arms, selected_arms
from final.src.modular.arms.classical import CatalogueSettings
from final.src.modular.arms.vf3_measured import (
    DecisionTableVf3MeasuredArm,
    EpBvaVf3MeasuredArm,
    VF3_MEASURED_ARMS,
    _frozen_base_value,
)
from final.src.modular.artifacts import ArtifactStore
from final.src.modular.catalogue import measure_catalogue
from final.src.modular.context import PipelineSettings, TaskContext
from final.src.modular.input_prompts import structured_input_prompt
from final.src.modular.pipeline import BenchmarkPipeline
from final.src.modular.references import TaskReferencePrograms
from final.src.modular.tests.test_testing_arms import task as sample_task
from final.src.modular.tests.test_testing_arms_integration import META, TASK, make_pipeline
from final.src.modular.tool_sampling.membership import expression
from final.src.modular.vf3_measured_schema import canonical_response, membership_errors, response_type
from final.src.orchestration import config, names, worker


def _two_param_task():
    return {
        "task_id": "HumanEval/0",
        "entry_point": "has_close_elements",
        "prompt": (
            "from typing import List\n\n"
            "def has_close_elements(numbers: List[float], threshold: float) -> bool:\n"
            '    """Check if two numbers are closer than threshold."""\n'
        ),
        "test": "def check(candidate):\n    assert candidate([1.0, 2.0], 0.5) == False\n",
    }


def _one_param_list_task():
    return {
        "task_id": "HumanEval/3",
        "entry_point": "below_zero",
        "prompt": (
            "from typing import List\n\n"
            "def below_zero(operations: List[int]) -> bool:\n"
            '    """Detect negative running balance."""\n'
        ),
        "test": "def check(candidate):\n    assert candidate([1, 2, 3]) == False\n",
    }


def test_ep_bva_schema_enforces_reason_only_when_not_applicable_or_unresolved():
    model = response_type(_two_param_task(), ("classes", "boundaries"), 20)

    # Missing reason on unresolved or not_applicable is rejected at schema level.
    for bad_status in ("unresolved", "not_applicable"):
        with pytest.raises(ValidationError):
            model.model_validate({
                "catalogue": {"status": bad_status},
                "inputs": [],
            })

    # Mixing classes/boundaries into not_applicable/unresolved is rejected (disjoint schema branches).
    with pytest.raises(ValidationError):
        model.model_validate({
            "catalogue": {
                "status": "not_applicable",
                "reason": "Summary of applied tests",
                "classes": [{"id": "E1", "description": "pos", "predicate": "threshold > 0"}],
                "boundaries": [],
            },
            "inputs": [],
        })

    # Supplying a nonempty reason without classes/boundaries passes for unresolved/not_applicable.
    valid_unresolved = model.model_validate({
        "catalogue": {
            "status": "unresolved",
            "reason": "Specification does not state behavior on empty input.",
        },
        "inputs": [],
    })
    assert valid_unresolved.catalogue.status == "unresolved"

    # Applicable requires nonempty classes and boundaries (and forbids null nominal).
    with pytest.raises(ValidationError):
        model.model_validate({
            "catalogue": {"status": "applicable", "classes": [], "boundaries": []},
            "inputs": [],
        })


def test_boundary_schema_excludes_tested_parameter_from_context_and_blocks_list_identity():
    one_param_model = response_type(_one_param_list_task(), ("classes", "boundaries"), 20)
    # Putting tested parameter inside context is rejected on 1-param tasks.
    with pytest.raises(ValidationError):
        one_param_model.model_validate({
            "catalogue": {
                "status": "applicable",
                "classes": [{"id": "C1", "description": "empty", "predicate": "len(operations) == 0"}],
                "boundaries": [{
                    "id": "B1",
                    "dimension": "list length",
                    "values": [0, 1],
                    "parameter": "operations",
                    "transform": "length",
                    "numeric_kind": "integer",
                    "lower": 0,
                    "upper": None,
                    "context": {"operations": []},
                    "nominal": {"operations": [1]},
                }],
            },
            "inputs": [],
        })

    # List parameter cannot use transform="identity".
    with pytest.raises(ValidationError):
        one_param_model.model_validate({
            "catalogue": {
                "status": "applicable",
                "classes": [{"id": "C1", "description": "empty", "predicate": "len(operations) == 0"}],
                "boundaries": [{
                    "id": "B1",
                    "dimension": "bad list identity",
                    "values": [0, 1],
                    "parameter": "operations",
                    "transform": "identity",
                    "numeric_kind": "integer",
                    "lower": 0,
                    "upper": 10,
                    "context": {},
                    "nominal": {"operations": [1]},
                }],
            },
            "inputs": [],
        })

    # Two-param task allows ONLY the OTHER parameter inside context and strips null context entries.
    two_param_model = response_type(_two_param_task(), ("classes", "boundaries"), 20)
    raw = {
        "catalogue": {
            "status": "applicable",
            "classes": [{
                "id": "C1",
                "description": "short list",
                "predicate": "len(numbers) < 2",
                "fault_hypothesis": "forgets length < 2 check",
            }],
            "boundaries": [{
                "id": "B1",
                "dimension": "threshold near zero",
                "values": [0.0, 0.1],
                "parameter": "threshold",
                "transform": "identity",
                "numeric_kind": "float",
                "lower": 0.0,
                "upper": None,
                "step": 0.1,
                "context": {"numbers": None},
                "nominal": {"numbers": [1.0, 2.0], "threshold": 0.5},
            }],
        },
        "inputs": [{"arguments": {"numbers": [1.0, 1.05], "threshold": 0.1}, "covers": ["B1"]}],
    }
    two_param_model.model_validate(raw)
    canonical = canonical_response(raw, ("classes", "boundaries"), task=_two_param_task())
    assert canonical["catalogue"]["boundaries"][0]["context"] == {}


def test_dt_schema_locks_fixed_1_to_4_bitstrings_and_preserves_fault_hypothesis():
    dt_model = response_type(_two_param_task(), ("rules",), 20)

    # Sequential R01..R04 keys are rejected by OriginalTable2 schema.
    with pytest.raises(ValidationError):
        dt_model.model_validate({
            "catalogue": {
                "status": "applicable",
                "condition_predicates": {"C1": "len(numbers) >= 2", "C2": "threshold > 0"},
                "rules": {
                    "R01": {"status": "feasible", "actions": ["return False"]},
                    "R02": {"status": "feasible", "actions": ["return False"]},
                    "R03": {"status": "feasible", "actions": ["return False"]},
                    "R04": {"status": "feasible", "actions": ["return True"]},
                },
            },
            "inputs": [],
        })

    valid_raw = {
        "catalogue": {
            "status": "applicable",
            "condition_predicates": {"C1": "len(numbers) >= 2", "C2": "threshold > 0"},
            "rules": {
                "R00": {"status": "feasible", "actions": ["return False"], "fault_hypothesis": "threshold <= 0"},
                "R01": {"status": "feasible", "actions": ["return False"]},
                "R10": {"status": "infeasible", "actions": [], "reason": "contract requires threshold > 0"},
                "R11": {"status": "feasible", "actions": ["return check_pairs"], "fault_hypothesis": "uses <= instead of <"},
            },
        },
        "inputs": [{"arguments": {"numbers": [1.0, 1.05], "threshold": 0.1}, "covers": ["R11"]}],
    }
    dt_model.model_validate(valid_raw)
    canonical = canonical_response(valid_raw, ("rules",), task=_two_param_task())
    assert len(canonical["catalogue"]["original_rules"]) == 4
    assert [row["id"] for row in canonical["catalogue"]["rules"]] == ["R00", "R01", "R11"]
    assert canonical["catalogue"]["rules"][-1]["fault_hypothesis"] == "uses <= instead of <"


def test_guidance_keeps_v2_soft_example_clean_prompt_and_status_instructions():
    common = structured_input_prompt(_two_param_task(), [], "assert threshold > 0", 20)
    assert "4294967296" not in common and "PUT timeouts count too" not in common
    for factory in VF3_MEASURED_ARMS:
        arm = factory()
        prompt = arm.build_messages({"common": common})[1]["content"]
        assert "SOFT EXAMPLE" in prompt
        assert "fault_hypothesis" in prompt
        assert 'catalogue.status must be "applicable"' in prompt
        assert "Return one JSON object matching the supplied JSON Schema" in prompt
        assert arm.preserve_prompt_context is True


def test_partial_measurement_still_computes_observed_when_catalogue_validates():
    # Reversed boundary marks catalogue_invalid, yet the valid class must still be observed.
    raw_batch = {
        "catalogue_status": "catalogue_invalid",
        "catalogue_errors": ["reversed_boundary:B1"],
        "catalogue": {
            "status": "applicable",
            "classes": [{"id": "C1", "description": "positive", "predicate": "x > 0"}],
            "boundaries": [{
                "id": "B1",
                "dimension": "bad bounds",
                "values": [1, 5],
                "parameter": "x",
                "lower": 5,
                "upper": 1,
                "numeric_kind": "integer",
            }],
        },
        "inputs": [{"args": "(2,)", "kwargs": "{}", "covers": ["C1"]}],
    }
    measured = measure_catalogue(raw_batch, sample_task(), [0], arm_name="ep_bva_vf3_measured", input_budget=30)
    assert measured["status"] == "catalogue_invalid"
    assert measured["partial_measurement"] is True
    assert measured["observed"]["classes"][0]["status"] == "hit"


def test_membership_ast_accepts_bitwise_and_larger_node_budget():
    expression("set(s) & set(c) == set()", {"s", "c"})
    expression("all((x & (x - 1)) == 0 for x in xs if x > 0)", {"xs"})
    # Expression with > 256 AST nodes and <= 512 nodes is now accepted.
    long_expr = " and ".join(f"(x != {i})" for i in range(60))
    expression(long_expr, {"x"})


def test_vf3_measured_two_round_feedback_dedup_unsupported_contract_and_relaxed_guard(tmp_path):
    task_data = {
        "task_id": "HumanEval/125",
        "entry_point": "split_words",
        "prompt": 'def split_words(txt: str):\n    """Split on whitespace or comma."""\n',
        "test": 'def check(candidate):\n    assert candidate("a b") == ["a", "b"]\n',
    }
    # Contract using .startswith() triggers compile_domain() -> unsupported.
    contract = 'assert isinstance(txt, str) and not txt.startswith("\\0")'
    base_key = repr(_frozen_base_value({"txt": "a b"}))

    r0_response = {
        "catalogue": {
            "status": "applicable",
            "classes": [
                {"id": "C1", "description": "contains space", "predicate": "' ' in txt"},
                {"id": "C2", "description": "bad helper", "predicate": "custom_tab(txt)"},
            ],
            "boundaries": [{
                "id": "B1",
                "dimension": "empty string",
                "values": [0, 1],
                "parameter": "txt",
                "transform": "length",
                "numeric_kind": "integer",
                "lower": 0,
                "upper": None,
                "context": {},
                "nominal": {"txt": "abc"},
            }],
        },
        "inputs": [
            {"arguments": {"txt": "a b"}, "covers": ["C1"]},  # base duplicate -> dropped
            {"arguments": {"txt": "hello world"}, "covers": ["C1"]},  # hits C1
        ],
    }
    # Round 1 repairs C2 (previously unknown), refines C1 description without changing predicate, adds tab input.
    r1_response = {
        "catalogue": {
            "status": "applicable",
            "classes": [
                {"id": "C1", "description": "space separated (refined)", "predicate": "' ' in txt"},
                {"id": "C2", "description": "contains tab", "predicate": "'\\t' in txt", "fault_hypothesis": "space-only check"},
            ],
            "boundaries": [{
                "id": "B1",
                "dimension": "empty string",
                "values": [0, 1],
                "parameter": "txt",
                "transform": "length",
                "numeric_kind": "integer",
                "lower": 0,
                "upper": None,
                "context": {},
                "nominal": {"txt": "abc"},
            }],
        },
        "inputs": [
            {"arguments": {"txt": "hello world"}, "covers": ["C1"]},  # cross-round duplicate -> dropped
            {"arguments": {"txt": "a\tb"}, "covers": ["C2"]},
            {"arguments": {"txt": ""}, "covers": ["B1"]},
        ],
    }

    class FakeCalls:
        def __init__(self):
            self.requests = []
            self.responses = [r0_response, r1_response]

        def token_count(self, messages):
            return 500

        def complete(self, task_number, call_name, messages, **kwargs):
            self.requests.append((call_name, messages, kwargs))
            payload = self.responses[len(self.requests) - 1]
            return ModelResponse(json.dumps(payload), {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}, "stop")

    calls = FakeCalls()
    ctx = TaskContext(
        task_data,
        {"contract": contract},
        ArtifactStore(tmp_path),
        PipelineSettings(input_budget=20, input_tokens=4096, context_tokens=12288),
        calls=calls,
    )
    ctx.cohort_task = {"base_input_keys": [base_key], "programs": []}
    ctx.packet = {"common": structured_input_prompt(task_data, [], contract, 20)}

    arm = EpBvaVf3MeasuredArm()
    batch = arm.run(ctx)

    # Both rounds ran with strict JSON Schema.
    assert len(calls.requests) == 2
    assert calls.requests[0][0] == "ep_bva_vf3_measured_initial"
    assert calls.requests[1][0] == "ep_bva_vf3_measured_feedback"
    assert calls.requests[0][2]["response_format"]["type"] == "json_schema"
    # Base duplicate and cross-round duplicate were discarded before retention.
    assert [row["args"] for row in batch["inputs"]] == ["('hello world',)", "('a\\tb',)", "('',)"]
    assert any(item["reason"] == "base_duplicate" for item in batch["rejected"])
    assert any(item["reason"] == "duplicate" for item in batch["rejected"])
    # Round 0 measured provisionally despite unsupported contract (.startswith), so C1 hit!
    r0_fb = batch["rounds"][0]["feedback"]
    assert r0_fb["admission_basis"] == "provisional_contract_unsupported"
    c1_r0 = next(row for row in r0_fb["targets"] if row["id"] == "C1")
    assert c1_r0["status"] == "hit"
    # Round 1 repaired catalogue was ACCEPTED (relaxed consistency guard allowed description refinement & C2 repair).
    assert batch["catalogue_status"] == "applicable"
    assert batch["membership_ready"] is True
    assert batch["input_budget"] == 30
    assert "feedback_catalogue_errors" not in batch


def test_dt_does_not_early_stop_when_initial_table_is_already_hit(tmp_path):
    task_data = sample_task()
    contract = "assert type(x) == int"
    dt_payload = {
        "catalogue": {
            "status": "applicable",
            "condition_predicates": {"C1": "x > 0"},
            "rules": {
                "R0": {"status": "feasible", "actions": ["non_positive"]},
                "R1": {"status": "feasible", "actions": ["positive"]},
            },
        },
        "inputs": [
            {"arguments": {"x": 0}, "covers": ["R0"]},
            {"arguments": {"x": 5}, "covers": ["R1"]},
        ],
    }
    dt_round1 = {
        **dt_payload,
        "inputs": [{"arguments": {"x": -1}, "covers": ["R0"]}],
    }

    class FakeCalls:
        def __init__(self):
            self.calls = []

        def token_count(self, messages):
            return 200

        def complete(self, task_number, call_name, messages, **kwargs):
            self.calls.append((call_name, messages))
            data = dt_payload if len(self.calls) == 1 else dt_round1
            return ModelResponse(json.dumps(data), finish_reason="stop")

    calls = FakeCalls()
    ctx = TaskContext(
        task_data,
        {"contract": contract},
        ArtifactStore(tmp_path),
        PipelineSettings(input_budget=20, input_tokens=4096, context_tokens=12288),
        calls=calls,
    )
    ctx.cohort_task = {"base_input_keys": [], "programs": []}
    ctx.packet = {"common": structured_input_prompt(task_data, [], contract, 20)}

    batch = DecisionTableVf3MeasuredArm().run(ctx)
    assert len(calls.calls) == 2
    fb_msg = json.loads(calls.calls[1][1][-1]["content"])
    assert fb_msg["feedback"]["repair_reasons"] == ["supplement_fault_hypotheses"]
    assert [row["args"] for row in batch["inputs"]] == ["(0,)", "(5,)", "(-1,)"]


def test_consistency_guard_blocks_dropping_already_hit_target(tmp_path):
    task_data = sample_task()
    contract = "assert type(x) == int"
    r0 = {
        "catalogue": {
            "status": "applicable",
            "classes": [
                {"id": "C1", "description": "positive", "predicate": "x > 0"},
                {"id": "C2", "description": "negative", "predicate": "x < 0"},
            ],
            "boundaries": [{
                "id": "B1",
                "dimension": "zero",
                "values": [0, 1],
                "parameter": "x",
                "transform": "identity",
                "numeric_kind": "integer",
                "lower": 0,
                "upper": None,
                "context": {},
                "nominal": {"x": 5},
            }],
        },
        "inputs": [{"arguments": {"x": 3}, "covers": ["C1"]}],
    }
    # Round 1 drops hit target C1 -> must be rejected while still appending valid new input.
    r1 = {
        "catalogue": {
            "status": "applicable",
            "classes": [{"id": "C2", "description": "negative", "predicate": "x < 0"}],
            "boundaries": r0["catalogue"]["boundaries"],
        },
        "inputs": [{"arguments": {"x": -2}, "covers": ["C2"]}],
    }

    class FakeCalls:
        def __init__(self):
            self.n = 0

        def token_count(self, messages):
            return 200

        def complete(self, *args, **kwargs):
            self.n += 1
            return ModelResponse(json.dumps(r0 if self.n == 1 else r1), finish_reason="stop")

    ctx = TaskContext(
        task_data,
        {"contract": contract},
        ArtifactStore(tmp_path),
        PipelineSettings(input_budget=20, input_tokens=4096, context_tokens=12288),
        calls=FakeCalls(),
    )
    ctx.cohort_task = {"base_input_keys": [], "programs": []}
    ctx.packet = {"common": structured_input_prompt(task_data, [], contract, 20)}

    batch = EpBvaVf3MeasuredArm().run(ctx)
    assert any("dropped_hit_target:classes:C1" in err for err in batch.get("feedback_catalogue_errors", []))
    assert [row["id"] for row in batch["catalogue"]["classes"]] == ["C1", "C2"]
    assert [row["args"] for row in batch["inputs"]] == ["(3,)", "(-2,)"]


def test_registry_orchestration_preview_and_preset_wiring(tmp_path, monkeypatch):
    # Existing default V2 registry stays intact.
    assert set(CATALOGUE_ARM_NAMES) == {"ep_bva_v2", "decision_table_v2"}
    assert set(VF3_MEASURED_ARM_NAMES) == {"ep_bva_vf3_measured", "decision_table_vf3_measured"}
    assert set(VF3_MEASURED_ARM_NAMES) <= {arm.name for arm in available_arms()}
    assert len(selected_arms(VF3_MEASURED_ARM_NAMES)) == 2
    for name in VF3_MEASURED_ARM_NAMES:
        assert generation_call_cap(name) == 2
        assert retained_input_budget(name, 20) == 30

    # catalogue=False and vertex backend are rejected for VF3 measured arms; openrouter is allowed.
    with pytest.raises(ValueError, match="catalogue enabled"):
        config.preview({"arms": ["ep_bva_vf3_measured"], "catalogue": False})
    with pytest.raises(ValueError, match="qwen or openrouter backend"):
        config.preview({"arms": ["ep_bva_vf3_measured"], "model_backend": "vertex"})
    assert config.preview({
        "arms": ["ep_bva_vf3_measured"],
        "task_numbers": [0],
        "model_backend": "openrouter",
        "model_name": "openai/gpt-oss-120b",
    })["logical_call_cap"] == 2

    # Preset preview matches expected caps (2 calls/task/arm, 30 retained inputs/task/arm).
    presets = json.loads(Path("final/presets/run_console.json").read_text())
    preset = next(item for item in presets if item["name"] == "Full164 · EP+BVA VF3 Measured vs DT VF3 Measured · batch")
    assert preset["preview_only"] is True
    preview = config.preview(preset["parameters"])
    assert preview["logical_call_cap"] == 628
    assert preview["max_input_slots_by_arm"] == {
        "ep_bva_vf3_measured": 4710,
        "decision_table_vf3_measured": 4710,
    }
    run_title = names.benchmark_run_name(preview["config"], preview_only=True)
    assert "EP + BVA VF3 Measured" in run_title and "DT VF3 Measured" in run_title

    # Worker prepare snapshots vf3_measured modules cleanly.
    monkeypatch.setattr(worker, "private_endpoint", lambda *args: tmp_path / "private.env")
    prepared = tmp_path / "prepared"
    worker.prepare({"arms": list(VF3_MEASURED_ARM_NAMES), "task_numbers": [0], "context_tokens": 12288}, prepared)
    assert (prepared / "runtime/final/src/modular/vf3_measured_schema.py").is_file()
    assert (prepared / "runtime/final/src/modular/arms/vf3_measured.py").is_file()


def test_all_164_humaneval_tasks_compile_valid_vf3_measured_json_schemas():
    """Offline check over all 164 HumanEval signatures: zero LLM calls."""
    from final.src.benchmarks.datasets import DatasetLoader

    tasks = DatasetLoader("HE-py").load_tasks()
    assert len(tasks) == 164
    for item in tasks:
        ep_schema = response_type(item, ("classes", "boundaries"), 20).model_json_schema()
        dt_schema = response_type(item, ("rules",), 20).model_json_schema()
        assert "properties" in ep_schema and "catalogue" in ep_schema["properties"]
        assert "properties" in dt_schema and "catalogue" in dt_schema["properties"]


def test_pipeline_end_to_end_and_replay_with_vf3_measured_arms(tmp_path, monkeypatch):
    original, model, events, tasks = make_pipeline(tmp_path, monkeypatch)
    ep_payload = json.dumps({
        "catalogue": {
            "status": "applicable",
            "classes": [{"id": "C1", "description": "positive", "predicate": "x > 0"}],
            "boundaries": [{
                "id": "B1",
                "dimension": "lower bound",
                "values": [0, 1],
                "parameter": "x",
                "transform": "identity",
                "numeric_kind": "integer",
                "lower": 0,
                "upper": None,
                "context": {},
                "nominal": {"x": 2},
            }],
        },
        "inputs": [{"arguments": {"x": 1}, "covers": ["C1", "B1"]}],
    })
    dt_payload = json.dumps({
        "catalogue": {
            "status": "applicable",
            "condition_predicates": {"C1": "x > 0"},
            "rules": {
                "R0": {"status": "feasible", "actions": ["non_positive"]},
                "R1": {"status": "feasible", "actions": ["positive"]},
            },
        },
        "inputs": [{"arguments": {"x": 2}, "covers": ["R1"]}],
    })

    def fake_generate(messages, *, temperature, max_tokens, seed, response_format=None):
        model.messages.append(messages)
        text = dt_payload if "OriginalTable1" in json.dumps(response_format or {}) else ep_payload
        return ModelResponse(text, {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10}, "stop")

    model.generate = fake_generate
    model.generate_prepared = lambda prepared, **kwargs: fake_generate(prepared.messages, max_tokens=prepared.output_tokens, **kwargs)
    methods = (EpBvaVf3MeasuredArm(), DecisionTableVf3MeasuredArm())
    settings = PipelineSettings(
        target_programs=original.settings.target_programs,
        input_budget=20,
        input_tokens=4096,
        context_tokens=12288,
    )
    pipeline = BenchmarkPipeline(
        original.cohort_path,
        original.artifacts,
        arms=methods,
        settings=settings,
        calls=original.calls,
        execution_cache=False,
        reference_programs=TaskReferencePrograms(),
    )
    result = pipeline.run(tasks, {TASK["task_id"]: META})
    assert len(model.messages) == 4  # 2 arms x 2 rounds
    task_cat = result["catalogues"][TASK["task_id"]]
    assert task_cat["ep_bva_vf3_measured"]["status"] == "applicable"
    assert task_cat["decision_table_vf3_measured"]["status"] == "applicable"
    assert task_cat["ep_bva_vf3_measured"]["observed"]["classes"][0]["status"] == "hit"
    assert task_cat["decision_table_vf3_measured"]["observed"]["summary"]["original_rules"]["hit"] == 1

    replay = BenchmarkPipeline(
        original.cohort_path,
        ArtifactStore(original.artifacts.directory, read_only=True),
        arms=methods,
        settings=settings,
        execution_cache=False,
        reference_programs=TaskReferencePrograms(),
    )
    assert replay.run(tasks, {TASK["task_id"]: META}) == result


def test_not_applicable_omitting_optional_sections_canonicalizes_without_error():
    for sections in (("classes", "boundaries"), ("rules",)):
        model = response_type(_two_param_task(), sections, 20)
        raw = {"catalogue": {"status": "not_applicable", "reason": "No applicable partition."}, "inputs": []}
        model.model_validate(raw)
        canonical = canonical_response(raw, sections, task=_two_param_task())
        from final.src.modular.catalogue import validate_catalogue

        catalogue, errors = validate_catalogue(canonical["catalogue"], sections)
        assert errors == [] and catalogue.status == "not_applicable"


def test_unannotated_multi_param_strips_null_context_and_step_uses_exclusive_minimum():
    unannotated_task = {
        "task_id": "HumanEval/45",
        "entry_point": "triangle_area",
        "prompt": 'def triangle_area(a, h):\n    """Area of a triangle."""\n',
        "test": "def check(candidate):\n    assert candidate(5, 3) == 7.5\n",
    }
    model = response_type(unannotated_task, ("classes", "boundaries"), 20)
    schema_text = json.dumps(model.model_json_schema())
    assert '"exclusiveMinimum": 0' in schema_text
    assert '"gt": 0' not in schema_text
    assert '"discriminator"' not in schema_text

    raw = {
        "catalogue": {
            "status": "applicable",
            "classes": [{"id": "C1", "description": "pos", "predicate": "a > 0 and h > 0"}],
            "boundaries": [{
                "id": "B1",
                "dimension": "base",
                "values": [0.0, 0.1],
                "parameter": "a",
                "transform": "identity",
                "numeric_kind": "float",
                "lower": 0.0,
                "upper": None,
                "step": 0.1,
                "context": {"h": None},
                "nominal": {"a": 2.0, "h": 3.0},
            }],
        },
        "inputs": [],
    }
    model.model_validate(raw)
    canonical = canonical_response(raw, ("classes", "boundaries"), task=unannotated_task)
    assert canonical["catalogue"]["boundaries"][0]["context"] == {}


def test_typed_numeric_arguments_reject_bool_in_schema():
    model = response_type(_one_param_list_task(), ("rules",), 20)
    with pytest.raises(ValidationError):
        model.model_validate({
            "catalogue": {
                "status": "applicable",
                "condition_predicates": {"C1": "len(operations) == 0"},
                "rules": {
                    "R0": {"status": "feasible", "actions": ["check"]},
                    "R1": {"status": "feasible", "actions": ["return False"]},
                },
            },
            "inputs": [{"arguments": {"operations": [True]}, "covers": ["R0"]}],
        })


def test_feedback_rejects_regressive_round1_and_accepts_valid_non_applicable_repair(tmp_path):
    task_data = sample_task()
    contract = "assert type(x) == int"
    good_r0 = {
        "catalogue": {
            "status": "applicable",
            "classes": [
                {"id": "C1", "description": "positive", "predicate": "x > 0"},
                {"id": "C2", "description": "negative", "predicate": "x < 0"},
            ],
            "boundaries": [{
                "id": "B1",
                "dimension": "zero",
                "values": [0, 1],
                "parameter": "x",
                "transform": "identity",
                "numeric_kind": "integer",
                "lower": 0,
                "upper": None,
                "context": {},
                "nominal": {"x": 5},
            }],
        },
        "inputs": [{"arguments": {"x": 1}, "covers": ["C1"]}],
    }
    # Round 1 preserves hit C1 unchanged (consistency=[]) but breaks C2 -> regresses membership_ready.
    bad_r1 = {
        "catalogue": {
            "status": "applicable",
            "classes": [
                {"id": "C1", "description": "positive", "predicate": "x > 0"},
                {"id": "C2", "description": "negative", "predicate": "unknown_helper(x)"},
            ],
            "boundaries": good_r0["catalogue"]["boundaries"],
        },
        "inputs": [{"arguments": {"x": -1}, "covers": ["C2"]}],
    }

    class RegressiveCalls:
        def __init__(self):
            self.n = 0

        def token_count(self, messages):
            return 200

        def complete(self, *args, **kwargs):
            self.n += 1
            return ModelResponse(json.dumps(good_r0 if self.n == 1 else bad_r1), finish_reason="stop")

    ctx = TaskContext(
        task_data,
        {"contract": contract},
        ArtifactStore(tmp_path / "reg"),
        PipelineSettings(input_budget=20, input_tokens=4096, context_tokens=12288),
        calls=RegressiveCalls(),
    )
    ctx.cohort_task = {"base_input_keys": [], "programs": []}
    ctx.packet = {"common": structured_input_prompt(task_data, [], contract, 20)}
    batch = EpBvaVf3MeasuredArm().run(ctx)
    assert batch["membership_ready"] is True
    assert batch["feedback_catalogue_errors"] == ["regressive_membership_errors"]

    # Now test invalid Round 0 repaired into valid not_applicable Round 1.
    class RepairToNotApplicableCalls:
        def __init__(self):
            self.n = 0

        def token_count(self, messages):
            return 200

        def complete(self, *args, **kwargs):
            self.n += 1
            if self.n == 1:
                return ModelResponse("{truncated", finish_reason="length")
            return ModelResponse(
                json.dumps({
                    "catalogue": {"status": "not_applicable", "reason": "No interacting conditions."},
                    "inputs": [{"arguments": {"x": 2}, "covers": []}],
                }),
                finish_reason="stop",
            )

    ctx2 = TaskContext(
        task_data,
        {"contract": contract},
        ArtifactStore(tmp_path / "repair_na"),
        PipelineSettings(input_budget=20, input_tokens=4096, context_tokens=12288),
        calls=RepairToNotApplicableCalls(),
    )
    ctx2.cohort_task = {"base_input_keys": [], "programs": []}
    ctx2.packet = {"common": structured_input_prompt(task_data, [], contract, 20)}
    batch2 = DecisionTableVf3MeasuredArm().run(ctx2)
    assert batch2["catalogue_status"] == "not_applicable"
    assert batch2["catalogue"]["reason"] == "No interacting conditions."
    assert [row["args"] for row in batch2["inputs"]] == ["(2,)"]


def test_pilot_optimizations_builtins_nominal_count_value_and_errored_condition_unlock(tmp_path):
    from final.src.modular.tool_sampling.membership import evaluate
    from final.src.orchestration.task_log import generation_text

    # 1. Pure scalar builtins (ord/chr/hex/bin/oct) are supported in static + sandbox evaluation.
    expression("any(ord(ch) > 127 for ch in s) and bin(len(s)).startswith('0b')", {"s"})
    assert evaluate("any(ord(ch) > 127 for ch in s)", {"s": "café"}) is True
    assert evaluate("any(ord(ch) > 127 for ch in s)", {"s": "abc"}) is False

    # 2. DT guidance strips contradictory V2 merged-"-" advice.
    common = structured_input_prompt(_two_param_task(), [], "assert threshold > 0", 20)
    dt_prompt = DecisionTableVf3MeasuredArm().build_messages({"common": common})[1]["content"]
    assert 'merged "-"' not in dt_prompt

    # 3. Required non-null nominal + count_value + nominal context checks.
    str_task = {
        "task_id": "HumanEval/6",
        "entry_point": "parse_nested_parens",
        "prompt": 'def parse_nested_parens(paren_string: str):\n    """Parse parens."""\n',
        "test": 'def check(candidate):\n    assert candidate("()") == [1]\n',
    }
    ep_model = response_type(str_task, ("classes", "boundaries"), 20)
    with pytest.raises(ValidationError):
        ep_model.model_validate({
            "catalogue": {
                "status": "applicable",
                "classes": [{"id": "E1", "description": "nonempty", "predicate": "len(paren_string) > 0"}],
                "boundaries": [{
                    "id": "B1",
                    "dimension": "length",
                    "values": [0, 1],
                    "parameter": "paren_string",
                    "transform": "length",
                    "numeric_kind": "integer",
                    "lower": 0,
                    "upper": None,
                    "context": {},
                    "nominal": None,
                }],
            },
            "inputs": [],
        })
    from final.src.modular.catalogue import Catalogue
    bad_count_cat = Catalogue.model_validate({
        "status": "applicable",
        "classes": [{"id": "E1", "description": "nonempty", "predicate": "len(paren_string) > 0"}],
        "boundaries": [{
            "id": "B1",
            "dimension": "spaces",
            "values": [0, 1],
            "parameter": "paren_string",
            "transform": "count",
            "count_value": None,
            "numeric_kind": "integer",
            "lower": 0,
            "upper": None,
            "context": {},
            "nominal": {"paren_string": "()"},
        }],
    })
    errs = membership_errors(bad_count_cat, str_task)
    assert "B1:missing_count_value" in errs

    # 4. Runtime-erroring DT condition (IndexError on empty string) is unlocked for Round 1 repair.
    s_task = {
        "task_id": "HumanEval/64",
        "entry_point": "vowels_count",
        "prompt": 'def vowels_count(s: str) -> int:\n    """Count vowels."""\n',
        "test": 'def check(candidate):\n    assert candidate("abcde") == 2\n',
    }
    r0_dt = {
        "catalogue": {
            "status": "applicable",
            "condition_predicates": {"C1": "len(s) == 0", "C2": "s[-1].lower() == 'y'"},
            "rules": {
                "R00": {"status": "feasible", "actions": ["count"]},
                "R01": {"status": "feasible", "actions": ["count_y"]},
                "R10": {"status": "feasible", "actions": ["return 0"]},
                "R11": {"status": "infeasible", "actions": [], "reason": "empty string has no last char"},
            },
        },
        "inputs": [
            {"arguments": {"s": ""}, "covers": ["R10"]},
            {"arguments": {"s": "sky"}, "covers": ["R01"]},
        ],
    }
    r1_dt = {
        "catalogue": {
            "status": "applicable",
            "condition_predicates": {"C1": "len(s) == 0", "C2": "len(s) > 0 and s[-1].lower() == 'y'"},
            "rules": r0_dt["catalogue"]["rules"],
        },
        "inputs": [{"arguments": {"s": "abc"}, "covers": ["R00"]}],
    }

    class RepairErrCondCalls:
        def __init__(self):
            self.n = 0

        def token_count(self, messages):
            return 200

        def complete(self, *args, **kwargs):
            self.n += 1
            return ModelResponse(json.dumps(r0_dt if self.n == 1 else r1_dt), finish_reason="stop")

    ctx = TaskContext(
        s_task,
        {"contract": "assert isinstance(s, str)"},
        ArtifactStore(tmp_path / "err_cond"),
        PipelineSettings(input_budget=20, input_tokens=4096, context_tokens=12288),
        calls=RepairErrCondCalls(),
    )
    ctx.cohort_task = {"base_input_keys": [], "programs": []}
    ctx.packet = {"common": structured_input_prompt(s_task, [], "assert isinstance(s, str)", 20)}
    batch = DecisionTableVf3MeasuredArm().run(ctx)
    assert "feedback_catalogue_errors" not in batch
    assert batch["catalogue"]["condition_predicates"]["C2"] == "len(s) > 0 and s[-1].lower() == 'y'"
    assert "C2" in batch["rounds"][0]["feedback"]["errored_conditions"]

    # 5. Unresolved Round 0 runs Round 1 and upgrades to applicable.
    r0_unres = {
        "catalogue": {"status": "unresolved", "reason": "Need another pass."},
        "inputs": [{"arguments": {"s": "a"}, "covers": []}],
    }

    class UpgradeUnresolvedCalls:
        def __init__(self):
            self.n = 0

        def token_count(self, messages):
            return 200

        def complete(self, *args, **kwargs):
            self.n += 1
            return ModelResponse(json.dumps(r0_unres if self.n == 1 else r1_dt), finish_reason="stop")

    ctx_u = TaskContext(
        s_task,
        {"contract": "assert isinstance(s, str)"},
        ArtifactStore(tmp_path / "unres"),
        PipelineSettings(input_budget=20, input_tokens=4096, context_tokens=12288),
        calls=UpgradeUnresolvedCalls(),
    )
    ctx_u.cohort_task = {"base_input_keys": [], "programs": []}
    ctx_u.packet = {"common": structured_input_prompt(s_task, [], "assert isinstance(s, str)", 20)}
    batch_u = DecisionTableVf3MeasuredArm().run(ctx_u)
    assert batch_u["model_calls"] == 2
    assert batch_u["catalogue_status"] == "applicable"

    # 6. task_log reports truncation on _initial and _feedback call directories.
    calls_dir = tmp_path / "calls"
    (calls_dir / "ep_bva_vf3_measured_feedback").mkdir(parents=True)
    (calls_dir / "ep_bva_vf3_measured_feedback" / "response.json").write_text(json.dumps({"finish_reason": "length"}))
    log_text = generation_text({"arms": {"ep_bva_vf3_measured": {"inputs": [], "rejected": []}}}, calls_dir)
    assert "truncated (ep_bva_vf3_measured_feedback)" in log_text


def test_review_must_fix_regressions_encoded_nominal_dt_status_duplicate_id_and_float_step():
    from final.src.modular.arms.vf3_measured import (
        _check_feedback_consistency,
        _should_accept_feedback_catalogue,
    )
    from final.src.modular.catalogue import Catalogue

    # 1. Encoded tuple nominal (HumanEval/127) decodes cleanly before matches_context & selected_value.
    tuple_task = {
        "task_id": "HumanEval/127",
        "entry_point": "intersection",
        "prompt": 'def intersection(interval1, interval2):\n    """Interval overlap."""\n',
        "test": 'def check(candidate):\n    assert candidate((1, 2), (2, 3)) == "NO"\n',
    }
    cat = Catalogue.model_validate({
        "status": "applicable",
        "classes": [{"id": "E1", "description": "nonempty", "predicate": "len(interval1) == 2"}],
        "boundaries": [{
            "id": "B1",
            "dimension": "interval1 length",
            "values": [2],
            "parameter": "interval1",
            "transform": "length",
            "numeric_kind": "discrete",
            "context": {"interval2": {"__python_type__": "tuple", "items": [2, 3]}},
            "nominal": {
                "interval1": {"__python_type__": "tuple", "items": [1, 2]},
                "interval2": {"__python_type__": "tuple", "items": [2, 3]},
            },
        }],
    })
    assert membership_errors(cat, tuple_task) == []

    # 2. Hit DT original_rule locks status against flipping feasible -> infeasible.
    old_dt = {
        "condition_predicates": {"C1": "x > 0"},
        "original_rules": [
            {"id": "R0", "conditions": {"C1": False}, "status": "feasible", "actions": ["a"]},
            {"id": "R1", "conditions": {"C1": True}, "status": "feasible", "actions": ["b"]},
        ],
    }
    flipped_dt = {
        "condition_predicates": {"C1": "x > 0"},
        "original_rules": [
            {"id": "R0", "conditions": {"C1": False}, "status": "feasible", "actions": ["a"]},
            {"id": "R1", "conditions": {"C1": True}, "status": "infeasible", "reason": "flipped"},
        ],
    }
    r0_fb = {"targets": [{"kind": "original_rules", "id": "R1", "status": "hit", "errors": []}], "errored_conditions": []}
    errs = _check_feedback_consistency(old_dt, flipped_dt, r0_fb, {"x": "int"})
    assert "changed_hit_target_definition:original_rules:R1" in errs

    # 3. duplicate_id colliding IDs are exempted from locking so Round 1 can rename them.
    dup_old = {
        "classes": [{"id": "X1", "predicate": "x > 0"}],
        "boundaries": [{
            "id": "X1", "parameter": "x", "transform": "identity", "count_value": None,
            "numeric_kind": "integer", "lower": 0, "upper": None, "step": None, "context": {},
        }],
    }
    dup_new = {
        "classes": [{"id": "E1", "predicate": "x > 0"}],
        "boundaries": [{
            "id": "B1", "parameter": "x", "transform": "identity", "count_value": None,
            "numeric_kind": "integer", "lower": 0, "upper": None, "step": None, "context": {},
        }],
    }
    dup_fb = {
        "targets": [
            {"kind": "classes", "id": "X1", "status": "hit", "errors": []},
            {"kind": "boundaries", "id": "X1", "status": "hit", "errors": []},
        ],
        "errored_conditions": [],
    }
    assert _check_feedback_consistency(dup_old, dup_new, dup_fb, {"x": "int"}) == []

    # 4. Hit float boundary with missing step=None unlocks step for Round 1 repair.
    float_old = {
        "boundaries": [{
            "id": "B1", "parameter": "x", "transform": "identity", "count_value": None,
            "numeric_kind": "float", "lower": 0.0, "upper": 0.0, "step": None, "context": {},
        }],
    }
    float_new = {
        "boundaries": [{
            "id": "B1", "parameter": "x", "transform": "identity", "count_value": None,
            "numeric_kind": "float", "lower": 0.0, "upper": 0.0, "step": 0.1, "context": {},
        }],
    }
    float_fb = {"targets": [{"kind": "boundaries", "id": "B1", "status": "hit", "errors": []}], "errored_conditions": []}
    assert _check_feedback_consistency(float_old, float_new, float_fb, {"x": "float"}) == []

    # 5. not_applicable can cleanly upgrade to applicable or remain not_applicable.
    na = {"catalogue_status": "not_applicable", "membership_ready": True, "membership_errors": []}
    app_with_minor = {"catalogue_status": "applicable", "membership_ready": False, "membership_errors": ["B1:missing_float_step"]}
    assert _should_accept_feedback_catalogue(na, app_with_minor, []) is True
    assert _should_accept_feedback_catalogue(na, na, []) is True

    # 6. Every anyOf branch of catalogue places 'status' FIRST for xgrammar guided decoding.
    for sections in (("classes", "boundaries"), ("rules",)):
        schema = response_type(_two_param_task(), sections, 20).model_json_schema()
        defs = schema.get("$defs", {})
        for branch in schema["properties"]["catalogue"]["anyOf"]:
            ref = branch["$ref"].split("/")[-1]
            assert list(defs[ref]["properties"].keys())[0] == "status"
