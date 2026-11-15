"""Legacy BVA integration and shared fixtures; explicit archived imports only."""
import json
from dataclasses import replace

import pytest

from final.src.models.core_model import ModelResponse
from final.src.runtime.artifacts import digest, save
from final.src.modular.dataset import DATA_SHA256
from final.src.modular.arms import available_arms, default_arms, selected_arms
from final.src.modular.boundary_value_analysis.legacy.arm import BoundaryArm
from final.src.modular.arms.plain import PlainArm
from final.src.modular.artifacts import ArtifactStore
from final.src.modular.context import PipelineSettings, TaskContext
from final.src.modular.pipeline import BenchmarkPipeline
from final.src.modular.references import TaskReferencePrograms
from final.src.modular.tests.test_boundary_value_analysis import SPECIFICATION, selection, generated, ScriptedCalls
from final.src.modular.tests.helpers import FixtureCalls


TASK = {"task_id": "HumanEval/7", "entry_point": "choose", "prompt": SPECIFICATION,
        "test": "def check(candidate):\n    assert candidate([0, 0]) == 0\n",
        "canonical_solution": "    # REFERENCE_ONLY_MARKER\n    return sum(xs)\n"}
META = {"contract": "\n    assert isinstance(xs, list) and len(xs) >= 2\n    assert all(type(x) is int for x in xs)\n",
        "atol": 0}


def program(identifier):
    return {"id": identifier, "code": "def choose(xs):\n    return 0\n",
            "base": {"status": "pass", "calls": [{"args": "([0, 0],)", "kwargs": "{}"}],
                     "coverage": {"lines": [1, 2], "arcs": []}}}


def make_context(tmp_path, calls, count=2, budget=5):
    context = TaskContext(TASK, META, ArtifactStore(tmp_path),
                          PipelineSettings(target_programs=count, input_budget=budget), calls)
    context.cohort_task = {"task_id": TASK["task_id"], "generated": count, "base_pass": count,
                           "programs": [program(index) for index in range(count)], "base_input_keys": []}
    context.packet = {"visible_put_ids": list(range(count))}
    return context


def write_cohort(path, tasks=None, *, boolean=False):
    records = []
    for task in tasks or [TASK]:
        item = program(0)
        if boolean:
            item["code"] = "def choose(flag: bool):\n    return flag\n"
            item["base"]["calls"] = [{"args": "(True,)", "kwargs": "{}"}]
        records.append({"task_id": task["task_id"], "generated": 1, "base_pass": 1,
                        "programs": [item], "base_input_keys": []})
    save(path, {"tasks": records, "cohort_sha256": digest(records), "dataset_sha256": DATA_SHA256})
    return path


class BoundaryFixtureModel:
    model_id = "boundary-pipeline-fixture"

    def __init__(self):
        self.requests = []

    def tokens(self, messages):
        return max(1, len(json.dumps(messages)) // 4)

    def generate(self, messages, **settings):
        self.requests.append(messages)
        assert "REFERENCE_ONLY_MARKER" not in json.dumps(messages)
        if "applying boundary value analysis" in messages[0]["content"]:
            record = selection()
        elif "boundary" in messages[0]["content"]:
            record = {"inputs": [generated()]}
        else:
            record = {"inputs": [{"args": "([7, 8],)", "kwargs": "{}", "guidance_id": None}]}
        return ModelResponse(json.dumps(record), {"prompt_tokens": 50, "completion_tokens": 50,
                                                  "total_tokens": 100}, "stop")




def test_arm_registration_preserves_plain_boundary_and_exposes_testing_variants():
    from final.src.modular.arms.classical import CATALOGUE_ARM_NAMES
    assert [arm.name for arm in available_arms()] == ["plain", "boundary", *CATALOGUE_ARM_NAMES, "control_flow", "spec_obligation", "control_flow_obligation"]
    assert [arm.name for arm in default_arms()] == ["plain"]
    assert selected_arms(["boundary"])[0].configuration()["pipeline_contract"] == "soft-bva-v1"
    with pytest.raises(ValueError, match="Unknown input-generation method"):
        selected_arms(["v11_concept"])


def test_fixed_task_budget_is_split_and_duplicate_inputs_are_merged(tmp_path):
    calls = ScriptedCalls(selection(), {"inputs": [generated(), generated("([7, 8],)")]},
                          selection(), {"inputs": [generated(), generated("([9, 10, 11],)", "above")]})
    context = make_context(tmp_path, calls)
    result = BoundaryArm().run(context)
    assert [record["input_budget"] for record in result["programs"]] == [3, 2]
    assert len(result["inputs"]) == 3
    assert result["inputs"][0]["guidance_id"] == "bva_0_b1"
    assert result["inputs"][-1]["guidance_id"] == "bva_1_b1"
    assert result["rejected"][-1]["reason"] == "duplicate_across_programs"
    assert len(calls.requests) == 4


def test_no_template_put_receives_no_allocation_or_llm_request(tmp_path):
    calls = ScriptedCalls(selection(), {"inputs": [generated()]})
    context = make_context(tmp_path, calls)
    context.cohort_task["programs"][0] = {"id": 0, "code": "def choose(*, flag: bool):\n    return flag\n",
                                         "base": {"status": "pass", "calls": [{"args": "()", "kwargs": "{'flag': True}"}]}}
    result = BoundaryArm().run(context)
    assert [item["input_budget"] for item in result["programs"]] == [0, 5]
    assert result["programs"][0]["status"] == "no_templates"
    assert [request["call_name"] for request in calls.requests] == ["bva_1_select", "bva_1_inputs"]


def test_unused_no_boundary_budget_is_not_redistributed(tmp_path):
    none = {"status": "no_boundary", "boundaries": [], "reason": "No usable boundary."}
    context = make_context(tmp_path, ScriptedCalls(none, selection(), {"inputs": [generated()]}))
    result = BoundaryArm().run(context)
    assert [item["input_budget"] for item in result["programs"]] == [3, 2]
    assert [item["status"] for item in result["programs"]] == ["no_boundary", "generated"]


def test_fewer_input_slots_than_puts_leaves_explicit_budget_skips(tmp_path):
    calls = ScriptedCalls(selection(), {"inputs": [generated()]})
    result = BoundaryArm().run(make_context(tmp_path, calls, count=3, budget=1))
    assert [item["status"] for item in result["programs"]] == ["generated", "input_budget_exhausted", "input_budget_exhausted"]
    assert len(calls.requests) == 2




def test_full_pipeline_freezes_boundary_inputs_then_runs_reference_and_puts(tmp_path, monkeypatch):
    path = write_cohort(tmp_path / "cohort.json")
    artifacts = ArtifactStore(tmp_path / "run")
    model = BoundaryFixtureModel()
    calls = FixtureCalls(model, artifacts.directory)
    settings = PipelineSettings(target_programs=1, input_budget=4)
    pipeline = BenchmarkPipeline(path, artifacts, arms=(BoundaryArm(),), calls=calls, settings=settings, reference_programs=TaskReferencePrograms())
    summary = pipeline.run([TASK], {TASK["task_id"]: META})
    assert summary["arms"]["boundary"] == {"valid_inputs": 1, "detected": 1, "tasks_detected": 1}
    assert summary["boundary_analysis"]["logical_calls"] == {"selection": 1, "generation": 1}
    assert summary["tester_calls"]["received"] == 2
    assert len(model.requests) == 2
    result = artifacts.read("tasks/7/result.json")
    assert result["arms"]["boundary"]["generation_status"] == "generated"
    names = [(event["stage"], event["state"]) for event in pipeline.stage_events]
    assert names.index(("input_generation", "complete")) < names.index(("reference_oracle", "started"))
    assert artifacts.exists("generation_frozen.json")
    assert "Boundary accounting" in artifacts.path("REPORT.md").read_text()
    # A second run reconstructs the same summary entirely from checkpoints.
    assert pipeline.run([TASK], {TASK["task_id"]: META}) == summary
    assert len(model.requests) == 2
    before = {item: item.read_bytes() for item in artifacts.directory.rglob("*") if item.is_file()}
    replay = BenchmarkPipeline(path, ArtifactStore(artifacts.directory, read_only=True),
                               arms=(BoundaryArm(),), settings=settings, reference_programs=TaskReferencePrograms())
    assert replay.run([TASK], {TASK["task_id"]: META}) == summary
    assert before == {item: item.read_bytes() for item in artifacts.directory.rglob("*") if item.is_file()}


@pytest.mark.parametrize("no_templates", [True, False])
def test_empty_boundary_arm_preserves_skip_and_never_executes_native_code(tmp_path, monkeypatch, no_templates):
    for name in ("reference_oracle", "put_evaluation"):
        monkeypatch.setattr(f"final.src.modular.stages.{name}.execute", lambda job: pytest.fail("Empty suite executed"))
    task = TASK
    if no_templates:
        task = {**TASK, "prompt": 'def choose(flag: bool):\n    """Return flag."""\n'}
    path = write_cohort(tmp_path / "cohort.json", [task], boolean=no_templates)
    calls = None if no_templates else ScriptedCalls({"status": "no_boundary", "boundaries": [], "reason": "None applies."})
    artifacts = ArtifactStore(tmp_path / "run")
    summary = BenchmarkPipeline(path, artifacts, arms=(BoundaryArm(),), calls=calls,
                                settings=PipelineSettings(target_programs=1), reference_programs=TaskReferencePrograms()).run([task], {task["task_id"]: META})
    expected = "no_templates" if no_templates else "no_boundary"
    result = artifacts.read("tasks/7/result.json")
    assert result["arms"]["boundary"]["generation_skip"] == expected
    assert summary["boundary_analysis"]["task_statuses"] == {expected: 1}
    assert summary["arms"]["boundary"]["valid_inputs"] == 0


def test_plain_and_boundary_share_existing_reference_evaluation(tmp_path):
    path = write_cohort(tmp_path / "cohort.json")
    artifacts = ArtifactStore(tmp_path / "run")
    model = BoundaryFixtureModel()
    calls = FixtureCalls(model, artifacts.directory)
    summary = BenchmarkPipeline(path, artifacts, arms=(PlainArm(), BoundaryArm()), calls=calls,
                                settings=PipelineSettings(target_programs=1, input_budget=4), reference_programs=TaskReferencePrograms()).run([TASK], {TASK["task_id"]: META})
    assert set(summary["arms"]) == {"plain", "boundary"}
    assert summary["arms"]["boundary"]["valid_inputs"] == 1
    assert summary["arms"]["plain"]["valid_inputs"] == 1
    assert summary["tester_calls"]["received"] == 3
    assert len(model.requests) == 3
    assert summary["comparisons"] == []  # No claim that 2-call BVA is call-matched to plain.


def test_cli_forwards_explicit_smoke_subset_and_budget(tmp_path, monkeypatch):
    from final.src.modular import run as runner

    captured = {}

    class PipelineFixture:
        def __init__(self, cohort, artifacts, **options):
            captured.update(options)
            self.stage_events = []

        def run(self, tasks, metadata):
            captured["tasks"] = tasks
            return {"scored_tasks": len(tasks), "arms": {}}

    monkeypatch.setattr(runner, "BenchmarkPipeline", PipelineFixture)
    monkeypatch.setattr(runner, "load_tasks", lambda: [TASK, {**TASK, "task_id": "HumanEval/8"}])
    assert runner.main(["--arms", "boundary", "--task-ids", "HumanEval/7", "--target-programs", "1",
                        "--input-budget", "4", "--artifacts", str(tmp_path)]) == 0
    assert captured["tasks"] == [TASK]
    assert captured["settings"].target_programs == 1
    assert captured["settings"].input_budget == 4
    assert captured["arms"][0].name == "boundary"
    assert captured["calls"] is None
