"""Unit and offline integration tests for VF3 Hybrid arms (lean Round 1 + free V2 Round 2)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from final.src.models.core_model import ModelResponse
from final.src.modular.arm_names import (
    CATALOGUE_ARM_NAMES,
    VF3_HYBRID_ARM_NAMES,
    generation_call_cap,
    retained_input_budget,
)
from final.src.modular import available_arms, selected_arms
from final.src.modular.black_box import DecisionTableArm, EpBvaArm
from final.src.runtime.contracts import bound_call_key
from final.src.modular.artifacts import ArtifactStore
from final.src.modular.black_box.catalogue import validate_catalogue
from final.src.modular.context import PipelineSettings, TaskContext
from final.src.modular.input_prompts import input_prompt_blocks, structured_input_prompt
from final.src.modular.pipeline import BenchmarkPipeline
from final.src.modular.references import TaskReferencePrograms
from final.src.modular.tests.test_testing_arms_integration import META, TASK, make_pipeline
from final.src.modular.black_box.vf3_hybrid_schema import membership_errors
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


def _str_task():
    return {
        "task_id": "HumanEval/125",
        "entry_point": "split_words",
        "prompt": 'def split_words(txt: str):\n    """Split on whitespace or comma."""\n',
        "test": 'def check(candidate):\n    assert candidate("a b") == ["a", "b"]\n',
    }


def test_all_164_humaneval_tasks_compile_valid_vf3_hybrid_schemas_with_xgrammar_key_order():
    from final.src.benchmarks.datasets import DatasetLoader

    tasks = DatasetLoader("HE-py").load_tasks()
    assert len(tasks) == 164
    for item in tasks:
        ep_schema = EpBvaArm().response_type(item).model_json_schema()
        dt_schema = DecisionTableArm().response_type(item).model_json_schema()
        for schema in (ep_schema, dt_schema):
            defs = schema.get("$defs", {})
            for branch in schema["properties"]["catalogue"]["anyOf"]:
                ref = branch["$ref"].split("/")[-1]
                assert list(defs[ref]["properties"].keys())[0] == "status"
        # Check every EP+BVA boundary anyOf branch aligns leading keys id -> parameter -> transform -> numeric_kind.
        ep_defs = ep_schema.get("$defs", {})
        app_cat = ep_defs["ApplicableHybridCatalogue"]
        b_items = app_cat["properties"]["boundaries"]["items"]
        b_branches = b_items.get("anyOf") or [b_items]
        for b_branch in b_branches:
            b_ref = b_branch["$ref"].split("/")[-1]
            keys = list(ep_defs[b_ref]["properties"].keys())
            assert keys[:4] == ["id", "parameter", "transform", "numeric_kind"]


def test_lean_ep_bva_schema_forbids_null_count_value_and_merges_shared_nominal():
    model = EpBvaArm().response_type(_str_task())

    # transform="count" WITHOUT count_value or with count_value=None is rejected at JSON Schema level.
    for bad_boundary in (
        {
            "id": "B1",
            "parameter": "txt",
            "transform": "count",
            "numeric_kind": "integer",
            "lower": 0,
            "upper": None,
            "context": {},
        },
        {
            "id": "B1",
            "parameter": "txt",
            "transform": "count",
            "numeric_kind": "integer",
            "count_value": None,
            "lower": 0,
            "upper": None,
            "context": {},
        },
    ):
        with pytest.raises(ValidationError):
            model.model_validate({
                "catalogue": {
                    "status": "applicable",
                    "nominal": {"txt": "abc"},
                    "classes": [{"id": "E1", "predicate": "len(txt) > 0"}],
                    "boundaries": [bad_boundary],
                },
                "inputs": [],
            })

    # Valid lean count + length + discrete boundaries canonicalize cleanly with shared nominal.
    two_param = _two_param_task()
    two_model = EpBvaArm().response_type(two_param)
    raw = {
        "catalogue": {
            "status": "applicable",
            "nominal": {"numbers": [1.0, 2.0], "threshold": 0.5},
            "classes": [{"id": "E1", "predicate": "len(numbers) < 2", "fault_hypothesis": "misses short list"}],
            "boundaries": [
                {
                    "id": "B1",
                    "parameter": "numbers",
                    "transform": "length",
                    "numeric_kind": "integer",
                    "lower": 0,
                    "upper": None,
                    "context": {"threshold": 0.25},
                },
                {
                    "id": "B2",
                    "parameter": "numbers",
                    "transform": "count",
                    "numeric_kind": "integer",
                    "count_value": 0.0,
                    "lower": 0,
                    "upper": None,
                    "context": {"threshold": None},
                },
                {
                    "id": "B3",
                    "parameter": "threshold",
                    "transform": "identity",
                    "numeric_kind": "float",
                    "lower": 0.0,
                    "upper": None,
                    "step": 0.1,
                    "context": {},
                },
            ],
        },
        "inputs": [{"arguments": {"numbers": [1.0], "threshold": 0.5}, "covers": ["E1"]}],
    }
    validated = two_model.model_validate(raw)
    normalized = EpBvaArm().normalize_catalogue(validated.model_dump(mode="json")["catalogue"], task=two_param)
    catalogue, errors = validate_catalogue(normalized, ("classes", "boundaries"))
    assert errors == [] and catalogue.status == "applicable"
    assert membership_errors(catalogue, two_param) == []
    # B1 nominal automatically merges B1's context threshold=0.25 so nominal never violates context.
    assert normalized["boundaries"][0]["nominal"] == {"numbers": [1.0, 2.0], "threshold": 0.25}
    assert normalized["boundaries"][1]["context"] == {}
    assert normalized["boundaries"][2]["values"] == [0.0, 0.1]
    assert normalized["classes"][0]["description"] == "misses short list"


def test_lean_dt_schema_drops_infeasible_prose_and_normalizes_cleanly():
    dt_model = DecisionTableArm().response_type(_two_param_task())

    # Extra prose fields like reason on infeasible row are forbidden in lean DT schema.
    with pytest.raises(ValidationError):
        dt_model.model_validate({
            "catalogue": {
                "status": "applicable",
                "condition_predicates": {"C1": "len(numbers) == 0"},
                "rules": {
                    "R0": {"status": "feasible"},
                    "R1": {"status": "infeasible", "reason": "verbose prose"},
                },
            },
            "inputs": [],
        })

    raw = {
        "catalogue": {
            "status": "applicable",
            "condition_predicates": {"C1": "len(numbers) >= 2", "C2": "threshold > 0"},
            "rules": {
                "R00": {"status": "infeasible"},
                "R01": {"status": "feasible", "fault_hypothesis": "short list not False"},
                "R10": {"status": "infeasible"},
                "R11": {"status": "feasible", "fault_hypothesis": "uses <= instead of <"},
            },
        },
        "inputs": [{"arguments": {"numbers": [1.0, 1.05], "threshold": 0.1}, "covers": ["R11"]}],
    }
    validated = dt_model.model_validate(raw)
    normalized = DecisionTableArm().normalize_catalogue(validated.model_dump(mode="json")["catalogue"], task=_two_param_task())
    catalogue, errors = validate_catalogue(normalized, ("rules",))
    assert errors == [] and catalogue.status == "applicable"
    assert membership_errors(catalogue, _two_param_task()) == []
    assert [r["id"] for r in normalized["rules"]] == ["R01", "R11"]
    assert normalized["rules"][1]["fault_hypothesis"] == "uses <= instead of <"


@pytest.mark.parametrize("configured_budget", [4, 20])
def test_hybrid_round2_uses_free_json_and_the_fixed_budget(tmp_path, configured_budget):
    task_data = _str_task()
    contract = 'assert isinstance(txt, str)'
    base_key = bound_call_key({"txt": "a b"})

    r1_response = {
        "catalogue": {
            "status": "applicable",
            "nominal": {"txt": "hello"},
            "classes": [
                {"id": "E1", "predicate": "' ' in txt", "fault_hypothesis": "space split"},
                {"id": "E2", "predicate": "',' in txt", "fault_hypothesis": "comma split"},
            ],
            "boundaries": [{
                "id": "B1",
                "parameter": "txt",
                "transform": "length",
                "numeric_kind": "integer",
                "lower": 0,
                "upper": None,
                "context": {},
            }],
        },
        "inputs": [
            {"arguments": {"txt": "a b"}, "covers": ["E1"]},  # base duplicate -> dropped
            {"arguments": {"txt": "hello world"}, "covers": ["E1"]},  # hits E1
        ],
    }
    # Round 2 is free V2-style JSON (even wrapped in markdown fences with free-form reasoning catalogue!)
    # discovering tab blind spot + hitting missed E2 and B1.
    r2_free_payload = {
        "catalogue": {
            "blind_spots": [
                {"id": "GAP1", "note": "Spec says whitespace, not just space; test tab and newline", "fault_hypothesis": "checks ' ' in txt instead of any whitespace"}
            ]
        },
        "inputs": [
            {"arguments": {"txt": "hello world"}, "covers": ["E1"]},  # duplicate of R1 -> dropped
            {"arguments": {"txt": "a,b"}, "covers": ["E2"]},  # hits missed E2
            {"arguments": {"txt": ""}, "covers": ["B1"]},  # hits B1=0
            {"arguments": {"txt": "a\tb"}, "covers": ["GAP1"]},  # new blind-spot edge case!
        ] + [{"arguments": {"txt": f"edge_{i}"}, "covers": []} for i in range(18)],  # 22 total -> capped at 20 by decoder!
    }

    class FakeCalls:
        def __init__(self):
            self.requests = []

        def token_count(self, messages):
            return 500

        def complete(self, task_number, call_name, messages, **kwargs):
            self.requests.append((call_name, messages, kwargs))
            if len(self.requests) == 1:
                return ModelResponse(json.dumps(r1_response), {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}, "stop")
            return ModelResponse("```json\n" + json.dumps(r2_free_payload) + "\n```", {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}, "stop")

    calls = FakeCalls()
    ctx = TaskContext(
        task_data,
        {"contract": contract},
        ArtifactStore(tmp_path),
        PipelineSettings(input_budget=configured_budget, input_tokens=4096, context_tokens=12288),
        calls=calls,
    )
    ctx.cohort_task = {"base_input_keys": [base_key], "programs": []}
    ctx.packet = {"prompt_blocks": input_prompt_blocks(task_data, [], contract, configured_budget)}

    batch = EpBvaArm().run(ctx)
    assert {"input_budget", "model_calls", "oracle_feedback"}.isdisjoint(batch)

    # Round 1 used strict json_schema; Round 2 used free JSON (response_format=None)!
    assert len(calls.requests) == len(batch["rounds"]) == 2
    response_format = calls.requests[0][2]["response_format"]
    assert response_format["type"] == "json_schema"
    assert "Generate up to 20 small, distinct new calls" in calls.requests[0][1][-1]["content"]
    assert response_format["json_schema"]["schema"]["properties"]["inputs"]["maxItems"] == 20
    assert calls.requests[1][2]["response_format"] is None

    # Round 2 payload sent existing_classes + ONLY unhit targets (E1 was hit -> NOT in missed/unknown!).
    r2_payload = json.loads(calls.requests[1][1][-1]["content"])
    assert "Generate up to 20 new distinct concrete inputs" in r2_payload["instruction"]
    assert "new_input_budget" not in r2_payload
    assert [c["id"] for c in r2_payload["existing_classes"]] == ["E1", "E2"]
    missed_ids = {row["id"] for row in r2_payload["feedback"]["missed_targets"]}
    unknown_ids = {row["id"] for row in r2_payload["feedback"]["unknown_targets"]}
    assert "E1" not in missed_ids and "E1" not in unknown_ids
    assert "E2" in missed_ids and "B1" in missed_ids

    # Round 1 strict catalogue stayed intact; Round 2 free reasoning catalogue preserved separately.
    assert batch["catalogue_status"] == "applicable"
    assert batch["membership_ready"] is True
    assert batch["round_2_reasoning_catalogue"]["blind_spots"][0]["id"] == "GAP1"
    assert batch['rounds'] == [
        {'call_name': f'{EpBvaArm.name}_initial'},
        {'call_name': f'{EpBvaArm.name}_feedback'},
    ]
    # Base and cross-round duplicates were dropped after decoding each capped batch.
    args_list = [row["args"] for row in batch["inputs"]]
    assert "('hello world',)" in args_list
    assert "('a\\tb',)" in args_list
    assert "('a,b',)" in args_list
    assert "('',)" in args_list
    assert "('a b',)" not in args_list
    assert len(args_list) == 20  # One retained from R1 and one duplicate removed from R2.
    # Round 1 feedback re-measured Round 1 strict catalogue over all retained inputs -> E2 is now HIT!
    feedback = ctx.artifacts.read(f'{ctx.task_directory}/{EpBvaArm.name}/round_1_feedback.json')
    r1_targets = {row['id']: row['status'] for row in feedback['targets']}
    assert r1_targets["E1"] == "hit" and r1_targets["E2"] == "hit"


def test_registry_orchestration_preview_preset_and_pipeline_replay_for_vf3_hybrid(tmp_path, monkeypatch):
    # Existing registries intact.
    assert set(CATALOGUE_ARM_NAMES) == {"ep_bva_vf3_hybrid", "decision_table_vf3_hybrid"}
    assert set(VF3_HYBRID_ARM_NAMES) == {"ep_bva_vf3_hybrid", "decision_table_vf3_hybrid"}
    assert set(VF3_HYBRID_ARM_NAMES) <= {arm.name for arm in available_arms()}
    assert len(selected_arms(VF3_HYBRID_ARM_NAMES)) == 2
    for name in VF3_HYBRID_ARM_NAMES:
        assert generation_call_cap(name) == 2
        assert retained_input_budget(name, 20) == 40

    with pytest.raises(ValueError, match="always enabled"):
        config.preview({"arms": ["ep_bva_vf3_hybrid"], "catalogue": False})
    with pytest.raises(ValueError, match="qwen or openrouter backend"):
        config.preview({"arms": ["ep_bva_vf3_hybrid"], "model_backend": "vertex"})

    presets = json.loads(Path("final/presets/run_console.json").read_text())
    preset = next(item for item in presets if item["name"] == "Full164 · EP+BVA VF3 Hybrid vs DT VF3 Hybrid · batch")
    assert preset["preview_only"] is True
    preview = config.preview(preset["parameters"])
    assert preview["logical_call_cap"] == 636
    assert preview["max_input_slots_by_arm"] == {
        "ep_bva_vf3_hybrid": 6360,
        "decision_table_vf3_hybrid": 6360,
    }
    small_preview = config.preview({"arms": ["plain", *VF3_HYBRID_ARM_NAMES], "task_numbers": [0], "inputs_per_task": 4})
    assert small_preview["max_input_slots_by_arm"] == {
        "plain": 4, "ep_bva_vf3_hybrid": 40, "decision_table_vf3_hybrid": 40,
    }
    run_title = names.benchmark_run_name(preview["config"], preview_only=True)
    assert "EP + BVA VF3 Hybrid" in run_title and "DT VF3 Hybrid" in run_title

    monkeypatch.setattr(worker, "private_endpoint", lambda *args: tmp_path / "private.env")
    prepared = tmp_path / "prepared"
    worker.prepare({"arms": list(VF3_HYBRID_ARM_NAMES), "task_numbers": [0], "context_tokens": 12288}, prepared)
    assert (prepared / "runtime/final/src/modular/black_box/vf3_hybrid_schema.py").is_file()
    assert (prepared / "runtime/final/src/modular/black_box/vf3_hybrid.py").is_file()
    assert (prepared / "runtime/final/src/modular/black_box/ep_bva.py").is_file()
    assert (prepared / "runtime/final/src/modular/black_box/decision_table.py").is_file()

    # Full end-to-end pipeline + read-only replay.
    original, model, events, tasks = make_pipeline(tmp_path / "pipe", monkeypatch)
    ep_r1 = json.dumps({
        "catalogue": {
            "status": "applicable",
            "nominal": {"x": 8},
            "classes": [{"id": "E1", "predicate": "x > 5", "fault_hypothesis": "off by one"}],
            "boundaries": [{
                "id": "B1",
                "parameter": "x",
                "transform": "identity",
                "numeric_kind": "integer",
                "lower": 5,
                "upper": None,
                "context": {},
            }],
        },
        "inputs": [{"arguments": {"x": 6}, "covers": ["E1", "B1"]}],
    })
    dt_r1 = json.dumps({
        "catalogue": {
            "status": "applicable",
            "condition_predicates": {"C1": "x > 5"},
            "rules": {
                "R0": {"status": "feasible", "fault_hypothesis": "boundary <= 5"},
                "R1": {"status": "feasible"},
            },
        },
        "inputs": [{"arguments": {"x": 7}, "covers": ["R1"]}],
    })
    r2_free = json.dumps({
        "catalogue": {"notes": "cover x=5 boundary and R0 (and ignore base duplicate x=0)"},
        "inputs": [
            {"arguments": {"x": 0}, "covers": ["R0"]},
            {"arguments": {"x": 5}, "covers": ["B1", "R0"]},
        ],
    })

    def fake_generate(messages, *, temperature, max_tokens, seed, response_format=None):
        model.messages.append((messages, response_format))
        if response_format is None:
            text = r2_free
        elif "HybridOriginalTable1" in json.dumps(response_format):
            text = dt_r1
        else:
            text = ep_r1
        return ModelResponse(text, {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10}, "stop")

    model.generate = fake_generate
    model.generate_prepared = lambda prepared, **kwargs: fake_generate(prepared.messages, max_tokens=prepared.output_tokens, **kwargs)
    methods = (EpBvaArm(), DecisionTableArm())
    settings = PipelineSettings(
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

        reference_programs=TaskReferencePrograms(),
    )
    result = pipeline.run(tasks, {TASK["task_id"]: META})
    assert len(model.messages) == 4  # 2 arms x (R1 strict + R2 free)
    assert sum(rf is None for _, rf in model.messages) == 2
    task_cat = pipeline.artifacts.read('tasks/7/catalogue_measurements.json')
    assert task_cat["ep_bva_vf3_hybrid"]["status"] == "applicable"
    assert task_cat["decision_table_vf3_hybrid"]["status"] == "applicable"
    # Round 2 input x=0 hit B1=0 (and R0 in DT) on Round 1's strict catalogue!
    assert task_cat["ep_bva_vf3_hybrid"]["observed"]["boundaries"][0]["status"] == "hit"
    assert task_cat["decision_table_vf3_hybrid"]["observed"]["summary"]["original_rules"]["hit"] == 2

    replay = BenchmarkPipeline(
        original.cohort_path,
        ArtifactStore(original.artifacts.directory, read_only=True),
        arms=methods,
        settings=settings,

        reference_programs=TaskReferencePrograms(),
    )
    assert replay.run(tasks, {TASK["task_id"]: META}) == result


def test_vf3_hybrid_review_edge_cases_json_safe_r2_40_inputs_14_classes_and_schema_tightening(tmp_path):
    # 1. Schema tightening: list/int lock numeric_kind to integer; bool skips numeric branch.
    typed_task = {
        "task_id": "HumanEval/997",
        "entry_point": "typed_fn",
        "prompt": "def typed_fn(xs: list[int], n: int, flag: bool, sep: str = ','):\n    pass\n",
        "test": "",
    }
    schema = EpBvaArm().response_type(typed_task).model_json_schema()
    defs = schema["$defs"]
    assert {"HybridNumericBoundary", "HybridCountBoundary", "HybridDiscreteBoundary"} <= set(defs)
    assert set(defs["HybridNumericBoundary"]["properties"]["parameter"]["enum"]) == {"xs", "n", "flag", "sep"}

    # 2. Full 20 + 20 = 40 retained inputs, 14 EP classes (>512 checks), default param in nominal,
    #    and Round 2 Python-literal set inside free reasoning catalogue (must stay strict JSON-serializable).
    r1_classes = [
        {"id": f"E{i}", "predicate": f"n == {i}", "fault_hypothesis": f"case {i}"}
        for i in range(14)
    ]
    r1_payload = {
        "catalogue": {
            "status": "applicable",
            "nominal": {"xs": [1, 2], "n": 5, "flag": True},  # omits default sep=','
            "classes": r1_classes,
            "boundaries": [{
                "id": "B1",
                "parameter": "n",
                "transform": "identity",
                "numeric_kind": "integer",
                "lower": 0,
                "upper": None,
                "context": {},
            }],
        },
        "inputs": [{"arguments": {"xs": [1], "n": i, "flag": True}, "covers": []} for i in range(20)],
    }
    # Python literal (single quotes + set inside catalogue) triggers python_literal_fallback.
    r2_inputs_py = ", ".join(
        f"{{'arguments': {{'xs': [1], 'n': {20 + i}, 'flag': False}}, 'covers': []}}"
        for i in range(20)
    )
    r2_python_literal = f"{{'catalogue': {{'chars': {{'\\t', '\\n'}}, 'note': 'whitespace'}}, 'inputs': [{r2_inputs_py}]}}"

    class FakeCalls:
        def __init__(self):
            self.calls = 0

        def token_count(self, messages):
            return 400

        def complete(self, task_number, call_name, messages, **kwargs):
            self.calls += 1
            text = json.dumps(r1_payload) if self.calls == 1 else r2_python_literal
            return ModelResponse(text, {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}, "stop")

    ctx = TaskContext(
        typed_task,
        {"contract": "\n    assert isinstance(xs, list) and isinstance(n, int) and isinstance(flag, bool)\n"},
        ArtifactStore(tmp_path),
        PipelineSettings(input_budget=20, input_tokens=4096, context_tokens=12288),
        calls=FakeCalls(),
    )
    ctx.cohort_task = {"base_input_keys": [], "programs": []}
    ctx.packet = {"common": structured_input_prompt(typed_task, [], "", 20)}

    batch = EpBvaArm().run(ctx)
    assert len(batch["inputs"]) == 40
    first_feedback = ctx.artifacts.read(f'{ctx.task_directory}/{EpBvaArm.name}/round_0_feedback.json')
    assert len(batch['inputs']) - len(first_feedback['admission']) == 20
    assert "r2:python_literal_fallback" in batch.get("response_repairs", [])
    # Strict JSON serializability (no set/NaN crash) and default param populated into nominal.
    json.dumps(batch, allow_nan=False)
    assert "_non_json_repr" in batch["round_2_reasoning_catalogue"]
    assert batch["catalogue"]["boundaries"][0]["nominal"]["sep"] == ","
    assert batch["membership_ready"] is True
    # All 14 classes x 40 inputs = 560 checks -> all 14 hit (zero membership_budget_exhausted unknowns!).
    feedback = ctx.artifacts.read(f'{ctx.task_directory}/{EpBvaArm.name}/round_1_feedback.json')
    r1_targets = {row['id']: row['status'] for row in feedback['targets'] if row['kind'] == 'classes'}
    assert len(r1_targets) == 14
    assert all(status == "hit" for status in r1_targets.values())


def test_vf3_hybrid_separate_id_patterns_and_round2_per_item_recovery(tmp_path):
    from final.src.modular.black_box.vf3_hybrid import _extract_input_items

    # 1. Schema forbids overlapping class/boundary IDs at token level (E<n> vs B<n>).
    model = EpBvaArm().response_type(_str_task())
    with pytest.raises(ValidationError):
        model.model_validate({
            "catalogue": {
                "status": "applicable",
                "nominal": {"txt": "abc"},
                "classes": [{"id": "B1", "predicate": "len(txt) > 0"}],
                "boundaries": [{
                    "id": "B1",
                    "parameter": "txt",
                    "transform": "length",
                    "numeric_kind": "integer",
                    "lower": 0,
                    "upper": None,
                    "context": {},
                }],
            },
            "inputs": [{"arguments": {"txt": "a"}, "covers": []}],
        })
    with pytest.raises(ValidationError):
        model.model_validate({
            "catalogue": {
                "status": "applicable",
                "nominal": {"txt": "abc"},
                "classes": [{"id": "E1", "predicate": "len(txt) > 0"}],
                "boundaries": [{
                    "id": "E1",
                    "parameter": "txt",
                    "transform": "length",
                    "numeric_kind": "integer",
                    "lower": 0,
                    "upper": None,
                    "context": {},
                }],
            },
            "inputs": [{"arguments": {"txt": "a"}, "covers": []}],
        })

    # 2. Unescaped quote in Round 2 free catalogue prose must NEVER drop the 20 valid inputs after it.
    broken_prose_r2 = (
        '{"catalogue": {"gap_classes_or_rules": [{"id": "G1", "note": "prints as "2.0"."}]}, '
        '"inputs": ['
        + ", ".join(f'{{"arguments": {{"txt": "s_{i}"}}, "covers": ["G1"]}}' for i in range(20))
        + "]}"
    )
    recovered_prose = _extract_input_items(broken_prose_r2)
    assert len(recovered_prose) == 20

    # 3. One arithmetic expression inside an input element must skip ONLY that 1 element, keeping all 19 others.
    one_bad_elem_r2 = (
        '{"catalogue": {"notes": "ok"}, "inputs": ['
        '{"arguments": {"txt": "first"}, "covers": ["G1"]}, '
        '{"arguments": {"txt": "bad" + "expr"}, "covers": ["G2"]}, '
        + ", ".join(f'{{"arguments": {{"txt": "after_{i}"}}, "covers": ["G3"]}}' for i in range(18))
        + "]}"
    )
    recovered_elem = _extract_input_items(one_bad_elem_r2)
    assert len(recovered_elem) == 19
    assert recovered_elem[0]["arguments"]["txt"] == "first"
    assert recovered_elem[-1]["arguments"]["txt"] == "after_17"

    # 4. Python set/tuple literal inside ast.literal_eval-recovered input must stay strict JSON-serializable.
    set_elem_r2 = (
        '{"catalogue": {"note": "bad "quote""}, "inputs": ['
        "{'arguments': {'values': [{1, 2}, (3, 4), 5]}, 'covers': ['G1']}, "
        '{"arguments": {"values": [10]}, "covers": ["G2"]}'
        "]}"
    )
    recovered_set = _extract_input_items(set_elem_r2)
    assert len(recovered_set) == 2
    json.dumps({"inputs": recovered_set}, allow_nan=False)
    assert recovered_set[0]["arguments"]["values"][0] == {"__python_type__": "set", "items": [1, 2]}
    assert recovered_set[0]["arguments"]["values"][1] == {"__python_type__": "tuple", "items": [3, 4]}


def test_truncated_response_recovers_only_complete_input_records():
    from final.src.modular.black_box.catalogue_response import read_catalogue_response
    raw, repairs = read_catalogue_response('{"inputs":[{"arguments":{"xs":[4,4]}},{"arguments":{"xs":[5,')
    assert raw['inputs'] == [{'arguments': {'xs': [4, 4]}}]
    assert 'complete_input_records_recovered' in repairs
