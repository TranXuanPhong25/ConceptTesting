"""Offline end-to-end contracts with fixture transport and synthetic native results."""
from __future__ import annotations

import json

import pytest

from final.src.models.core_model import ModelResponse
from final.src.modular.black_box import DecisionTableArm, EpBvaArm
from final.src.modular.plain import PlainArm
from final.src.modular.artifacts import ArtifactStore
from final.src.modular.context import PipelineSettings
from final.src.modular.pipeline import BenchmarkPipeline
from final.src.modular.references import TaskReferencePrograms
from final.src.modular.tests.helpers import FixtureCalls
from final.src.runtime.artifacts import digest, save


TASK = {
    "task_id": "HumanEval/7", "entry_point": "fixture_function",
    "prompt": "def fixture_function(x: int):\n    \"\"\"Return x unchanged for x in [0, 10].\"\"\"\n",
    "test": "def check(candidate):\n    assert candidate(0) == 0\n",
    "canonical_solution": "    return x\n",
}
META = {"contract": "\n    assert type(x) is int and 0 <= x <= 10\n", "atol": 0}


class CatalogueFixtureModel:
    model_id = "catalogue-offline-fixture"

    def __init__(self, *, malformed=False):
        self.malformed = malformed
        self.messages = []

    def tokens(self, messages):
        return 1

    def generate(self, messages, **settings):
        self.messages.append(messages)
        is_round2 = len(messages) > 2
        if is_round2:
            payload = {"catalogue": {"gap_classes_or_rules": []}, "inputs": []}
        elif "supplied JSON Schema" in messages[1]["content"]:
            if "condition_predicates" in messages[1]["content"] or "C1..Cn" in messages[1]["content"]:
                payload = {
                    "catalogue": {
                        "status": "applicable",
                        "condition_predicates": {"C1": "x >= 0"},
                        "rules": {"R0": {"status": "infeasible"}, "R1": {"status": "feasible"}},
                    },
                    "inputs": [{"arguments": {"x": 2}, "covers": ["R1"]}],
                }
            elif self.malformed:
                payload = {"catalogue": {"classes": "invalid"}, "inputs": [{"arguments": {"x": 2}}]}
            else:
                payload = {
                    "catalogue": {
                        "status": "applicable",
                        "nominal": {"x": 5},
                        "classes": [{"id": "E1", "predicate": "0 <= x <= 10"}],
                        "boundaries": [{
                            "id": "B1", "parameter": "x", "transform": "identity",
                            "numeric_kind": "integer", "lower": 0, "upper": 10, "context": {},
                        }],
                    },
                    "inputs": [{"arguments": {"x": 2}, "covers": ["E1", "B1"]}],
                }
        else:
            payload = {"inputs": [{"arguments": {"x": 2}}]}
        return ModelResponse(
            json.dumps(payload),
            {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18},
            "stop",
        )


def write_fixture_cohort(path, tasks):
    rows = []
    for task in tasks:
        rows.append({
            "task_id": task["task_id"], "generated": 1, "base_pass": 1,
            "programs": [{
                "id": 0, "code": "def fixture_function(x):\n    return x\n",
                "base": {"status": "pass", "calls": [{"args": "(0,)", "kwargs": "{}"}]},
            }],
            "base_input_keys": [],
        })
    save(path, {"tasks": rows, "cohort_sha256": digest(rows), "dataset_sha256": "fixture-dataset"})
    return path


def make_pipeline(tmp_path, monkeypatch, *, malformed=False, tasks=None, fail=False):
    tasks = tasks or [TASK]
    directory = tmp_path / "run"
    cohort = write_fixture_cohort(tmp_path / "cohort.json", tasks)
    model = CatalogueFixtureModel(malformed=malformed)
    native_events = []

    def fixture_oracle(job):
        assert all((directory / "tasks" / task["task_id"].split("/")[-1] / "inputs.json").exists() for task in tasks)
        native_events.append("reference")
        return {"tests": [{"status": "ok", "expected": "fixture_value",
                           "input_key": "fixture:" + record["args"]} for record in job["tests"]]}

    def fixture_evaluate(job):
        assert all((directory / "tasks" / task["task_id"].split("/")[-1] /
                    "catalogue_measurements.json").exists() for task in tasks if
                   (directory / "tasks" / task["task_id"].split("/")[-1] / "oracle_valid.json").exists())
        native_events.append("put")
        return {"tests": [{"status": "fail" if fail else "pass"} for record in job["tests"]]}

    monkeypatch.setattr("final.src.modular.reference_oracle.execute", fixture_oracle)
    monkeypatch.setattr("final.src.modular.put_evaluation.execute", fixture_evaluate)
    pipeline = BenchmarkPipeline(
        cohort, ArtifactStore(directory),
        arms=(PlainArm(), EpBvaArm()), settings=PipelineSettings(input_tokens=4096),
        calls=FixtureCalls(model, directory), reference_programs=TaskReferencePrograms(),
    )
    return pipeline, model, native_events, tasks


def test_catalogue_pipeline_freezes_all_tasks_before_measurement_and_put(tmp_path, monkeypatch):
    tasks = [TASK, {**TASK, "task_id": "HumanEval/8"}]
    pipeline, model, events, tasks = make_pipeline(tmp_path, monkeypatch, tasks=tasks, fail=True)
    result = pipeline.run(tasks, {task["task_id"]: META for task in tasks})
    assert len(model.messages) == 6  # 2 tasks * (1 plain + 2 vf3_hybrid rounds)
    assert events.count("reference") == 4
    assert events.count("put") == 4
    for task in tasks:
        names = [event["stage"] for event in pipeline.stage_events
                 if event["task_id"] == task["task_id"] and event["state"] == "complete"]
        assert names.index("input_generation") < names.index("reference_oracle")
        assert names.index("reference_oracle") < names.index("catalogue_measurement") < names.index("put_evaluation")
        path = f"tasks/{task['task_id'].split('/')[-1]}/catalogue_measurements.json"
        catalogue = pipeline.artifacts.read(path)["ep_bva_vf3_hybrid"]
        assert catalogue["valid_input_records"] == 1
        assert catalogue["declared"]["covered_ids"] == ["B1", "E1"]
        assert catalogue["semantic_audit"] == "pending"
        observed = catalogue["observed"]
        assert observed["classes"][0]["status"] == "hit"
        assert observed["boundaries"][0]["status"] == "miss"
    assert 'catalogues' not in result
    assert result["arms"]["ep_bva_vf3_hybrid"]["detected"] == 2
    assert result["detection_kinds"]["ep_bva_vf3_hybrid"]["wrong_value"] == 2
    assert len(result["comparisons"]) == 1
    report = (tmp_path / "run" / "REPORT.md").read_text()
    assert "Kết quả testing arms" in report and "4096 tokens/call" in report


def test_malformed_catalogue_preserves_valid_call_through_evaluation(tmp_path, monkeypatch):
    pipeline, model, events, tasks = make_pipeline(tmp_path, monkeypatch, malformed=True)
    result = pipeline.run(tasks, {TASK["task_id"]: META})
    batch = pipeline.artifacts.read("tasks/7/inputs.json")["arms"]["ep_bva_vf3_hybrid"]
    assert batch["catalogue_status"] == "catalogue_invalid"
    assert batch["inputs"][0]["args"] == "(2,)"
    assert result["arms"]["ep_bva_vf3_hybrid"]["valid_inputs"] == 1
    measured = pipeline.artifacts.read('tasks/7/catalogue_measurements.json')
    assert measured['ep_bva_vf3_hybrid']['status'] == 'catalogue_invalid'
    assert events.count("put") == 1


def test_catalogue_run_replays_identically_without_fixture_generation_or_execution(tmp_path, monkeypatch):
    pipeline, model, events, tasks = make_pipeline(tmp_path, monkeypatch, fail=True)
    expected = pipeline.run(tasks, {TASK["task_id"]: META})
    snapshot = {str(path.relative_to(tmp_path / "run")): path.read_bytes()
                for path in (tmp_path / "run").rglob("*") if path.is_file()}

    def forbidden(*args, **kwargs):
        pytest.fail("Read-only replay attempted generation, tokenization or native execution")

    monkeypatch.setattr(CatalogueFixtureModel, "generate", forbidden)
    monkeypatch.setattr(CatalogueFixtureModel, "tokens", forbidden)
    monkeypatch.setattr("final.src.modular.reference_oracle.execute", forbidden)
    monkeypatch.setattr("final.src.modular.put_evaluation.execute", forbidden)
    replay = BenchmarkPipeline(
        pipeline.cohort_path, ArtifactStore(tmp_path / "run", read_only=True),
        arms=(PlainArm(), EpBvaArm()), settings=pipeline.settings, reference_programs=TaskReferencePrograms(),
    )
    assert replay.run(tasks, {TASK["task_id"]: META}) == expected
    assert {str(path.relative_to(tmp_path / "run")): path.read_bytes()
            for path in (tmp_path / "run").rglob("*") if path.is_file()} == snapshot


def test_catalogue_manifest_tracks_schema_and_read_only_classifier_sources(tmp_path, monkeypatch):
    pipeline, model, events, tasks = make_pipeline(tmp_path, monkeypatch)
    pipeline.run(tasks, {TASK["task_id"]: META})
    manifest = pipeline.artifacts.read("modular_manifest.json")
    assert "pydantic" in manifest["packages"]
    assert "sources" not in manifest
    assert "settings" in manifest
    assert manifest["settings"]["input_tokens"] == 4096
    stage = next(stage for stage in manifest["stages"] if stage["name"] == "catalogue_measurement")
    assert stage["configuration"]["arms"] == [EpBvaArm.name]
    assert [stage["name"] for stage in manifest["stages"]].index("catalogue_measurement") < [
        stage["name"] for stage in manifest["stages"]].index("put_evaluation")


def test_console_new_arm_worker_uses_shared_completion_cap_and_replays_empty_fixture(tmp_path, monkeypatch, capsys):
    """Exercise console factories/immutable snapshots with no model or native work."""
    from final.src.orchestration import worker
    import final.src.models.model as transport

    requests = []

    class ConsoleFixtureModel:
        model_id = "qwen3.5-27b-awq"

        def __init__(self, **kwargs):
            pass

        def check_endpoint(self):
            return {"model": self.model_id, "context": 12288}

        def tokens(self, messages):
            return 1

        def prepare_generation(self, messages, max_tokens):
            return messages

        def generate_prepared(self, messages, **settings):
            requests.append((messages, settings))
            payload = {"inputs": []}
            if len(messages) == 2 and "supplied JSON Schema" in messages[1]["content"]:
                payload["catalogue"] = {"status": "not_applicable", "reason": "offline transport fixture"}
            return ModelResponse(json.dumps(payload), {"prompt_tokens": 1, "completion_tokens": 1,
                                                       "total_tokens": 2}, "stop")

    monkeypatch.setattr(worker, "private_endpoint", lambda directory, name: tmp_path / "private-fixture.env")
    monkeypatch.setattr(transport, "QwenModel", ConsoleFixtureModel)
    monkeypatch.setattr(worker.signal, "signal", lambda *args: None)
    monkeypatch.setenv("FINAL_ENDPOINT_ENV_FILE", "fixture-before-run")

    def unexpected_native(job):
        pytest.fail("Empty console fixture attempted native execution")

    monkeypatch.setattr("final.src.modular.reference_oracle.execute", unexpected_native)
    monkeypatch.setattr("final.src.modular.put_evaluation.execute", unexpected_native)
    output = tmp_path / "console"
    preview = worker.prepare({"cohort": "humaneval164", "task_numbers": [0],
                              "arms": ["plain", "ep_bva_vf3_hybrid"]}, output)
    assert preview["config"]["completion_tokens"] == 8192
    plan = worker.read(output / "launch_plan.json")
    plan.update(native_lock=str(tmp_path / "native.lock"))
    worker.save(output / "launch_plan.json", plan)
    assert not (output / 'source_snapshot.json').exists()
    worker.run(output)
    assert len(requests) == 3  # plain + ep_bva_vf3_hybrid (2 rounds)
    for name in ("plain", "ep_bva_vf3_hybrid_initial", "ep_bva_vf3_hybrid_feedback"):
        request = worker.read(output / "tasks" / "0" / "calls" / name / "request.json")
        assert request["max_tokens"] == 8192
    result = worker.read(output / "result_digest.json")
    assert result["arms"]["ep_bva_vf3_hybrid"]["valid_inputs"] == 0
    measured = worker.read(output / 'tasks/0/catalogue_measurements.json')
    assert measured['ep_bva_vf3_hybrid']['status'] == 'not_applicable'


def test_three_full_run_arms_share_one_plain_baseline_and_replay(tmp_path, monkeypatch):
    pipeline, model, events, tasks = make_pipeline(tmp_path, monkeypatch)
    methods = (PlainArm(), EpBvaArm(), DecisionTableArm())
    pipeline = BenchmarkPipeline(
        pipeline.cohort_path, pipeline.artifacts,
        arms=methods, settings=pipeline.settings, calls=pipeline.calls, reference_programs=TaskReferencePrograms(),
    )
    summary = pipeline.run(tasks, {TASK["task_id"]: META})
    assert len(model.messages) == 5  # 1 plain + 2 ep_bva + 2 dt
    packet = pipeline.artifacts.read("tasks/7/packet.json")
    assert set(packet["prompt_tokens"]) == {"plain", "ep_bva_vf3_hybrid", "decision_table_vf3_hybrid"}
    assert set(summary["arms"]) == {"plain", "ep_bva_vf3_hybrid", "decision_table_vf3_hybrid"}
    assert {(row["left"], row["right"]) for row in summary["comparisons"]} == {
        ("plain", "ep_bva_vf3_hybrid"),
        ("plain", "decision_table_vf3_hybrid"),
        ("ep_bva_vf3_hybrid", "decision_table_vf3_hybrid"),
    }
    for name in ["reference_oracle", "put_evaluation"]:
        monkeypatch.setattr("final.src.modular." + name + ".execute",
                            lambda job: pytest.fail("Native execution during three-arm replay"))
    replay = BenchmarkPipeline(
        pipeline.cohort_path,
        ArtifactStore(pipeline.artifacts.directory, read_only=True), arms=methods,
        settings=pipeline.settings, reference_programs=TaskReferencePrograms(),
    )
    assert replay.run(tasks, {TASK["task_id"]: META}) == summary
