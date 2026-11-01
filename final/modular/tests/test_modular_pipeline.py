"""Meaningful parity/safety fixtures. No endpoint requests or new benchmark scoring."""
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from final.pipeline import Pipeline, Settings, digest, save
from final.run import DATA_SHA256
from final.experiments.concept_reference_v1.cohort import build_task
from final.experiments.concept_reference_v1.prompts import messages as historical_messages
from final.experiments.concept_reference_v1.benchmark import generate_inputs
from final.experiments.concept_reference_v1_recovery.benchmark import score_task, report
from final.experiments.concept_reference_v1.tests.test_concept_benchmark import FixtureModel, TASK, META
from final.modular.arms import default_arms
from final.modular.artifacts import ArtifactStore
from final.modular.calls import CachedModelCalls, RecoveryModelCalls
from final.modular.context import TaskContext, PipelineSettings
from final.modular.pipeline import BenchmarkPipeline
from final.modular.stages.base import PipelineStage
from final.modular.stages.program_generation import ProgramGenerationStage
from final.modular.stages.base_tests import BaseTestFilterStage
from final.modular.stages.reference_oracle import ReferenceOracleStage
from final.modular.stages.witness_sampling import WitnessSamplingStage
from final.modular.stages.concept_analysis import ConceptAnalysisStage
from final.modular.arms.toolinput import ToolInputArm
from final.modular.arms.witness_only import WitnessOnlyArm


class FixtureCalls:
    def __init__(self, model, directory):
        self.model = model
        self.directory = directory
        self.client = Pipeline(model, directory, Settings())

    @property
    def model_id(self):
        return self.model.model_id

    def token_count(self, messages):
        return self.model.tokens(messages)

    def complete(self, task_number, call_name, messages, **parameters):
        return self.client.query(self.directory / f"tasks/{task_number}", call_name, messages, **parameters)


@pytest.fixture
def cached_run(tmp_path):
    cohort_directory = tmp_path / "cohort"
    model = FixtureModel()
    cohort_task = build_task(TASK, Pipeline(model, cohort_directory, Settings()), cohort_directory / "tasks/0")
    cohort = {"tasks": [cohort_task], "cohort_sha256": digest([cohort_task]), "dataset_sha256": DATA_SHA256}
    cohort_path = cohort_directory / "cohort.json"
    save(cohort_path, cohort)
    output_directory = tmp_path / "historical"
    generate_inputs(TASK, cohort_task, META, model, output_directory)
    score_task(TASK, cohort_task, META, output_directory)
    historical_summary = report(output_directory, cohort, 1)
    input_record = json.loads((output_directory / "tasks/0/inputs.json").read_text())
    input_hashes = {TASK["task_id"]: digest(input_record)}
    save(output_directory / "generation_frozen.json", {
        "cohort_sha256": cohort["cohort_sha256"], "inputs": input_hashes, "inputs_sha256": digest(input_hashes),
    })
    (output_directory / ".run.lock").touch()
    return cohort_path, cohort_task, output_directory, historical_summary


def test_all_arm_prompts_match_frozen_implementation(cached_run):
    cohort_path, cohort_task, output_directory, summary = cached_run
    packet = json.loads((output_directory / "tasks/0/packet.json").read_text())
    for arm in default_arms():
        if arm.uses_model:
            assert arm.build_messages(packet) == historical_messages(packet["common"], arm.name, packet["analysis"], packet["witnesses"])


def test_full_stage_replay_reconstructs_inputs_outcomes_and_entire_summary(cached_run, monkeypatch):
    cohort_path, cohort_task, output_directory, expected_summary = cached_run

    def forbidden_execution(*arguments, **keywords):
        raise AssertionError("Read-only replay must not execute native code or call a model")

    for module_name in ("reference_oracle", "put_evaluation", "witness_sampling"):
        monkeypatch.setattr(f"final.modular.stages.{module_name}.execute", forbidden_execution)
    pipeline = BenchmarkPipeline(cohort_path, ArtifactStore(output_directory, read_only=True))
    actual_summary = pipeline.run([TASK], {TASK["task_id"]: META})
    assert actual_summary == expected_summary
    assert actual_summary["arms"]["classical"]["detected"] == 8
    assert len(pipeline.stage_events) == 14
    assert not (output_directory / "stage_events.jsonl").exists()


def test_custom_stage_is_inserted_and_tracks_its_dependency(cached_run):
    cohort_path, cohort_task, output_directory, expected_summary = cached_run

    class TraceStage(PipelineStage):
        name = "trace_concept_quality"
        requires = ("concept_analysis",)

        def run(self, context):
            context.extensions["card_count"] = len(context.packet["analysis"]["classical"])

    pipeline = BenchmarkPipeline(cohort_path, ArtifactStore(output_directory, read_only=True))
    pipeline.insert_stage(TraceStage(), after="concept_analysis")
    assert pipeline.run([TASK], {TASK["task_id"]: META}) == expected_summary
    stage_names = [event["stage"] for event in pipeline.stage_events if event["state"] == "complete"]
    assert stage_names.index("trace_concept_quality") == stage_names.index("concept_analysis") + 1


def test_invalid_stage_insertion_rolls_back(cached_run):
    cohort_path, cohort_task, output_directory, expected_summary = cached_run

    class InvalidStage(PipelineStage):
        name = "invalid"
        requires = ("put_evaluation",)

        def run(self, context):
            raise AssertionError("Invalidly ordered stage must not run")

    pipeline = BenchmarkPipeline(cohort_path, ArtifactStore(output_directory, read_only=True))
    with pytest.raises(ValueError, match="requires earlier"):
        pipeline.insert_stage(InvalidStage(), after="concept_analysis")
    assert all(stage.name != "invalid" for stage in pipeline.generation_stages)


def test_oracle_barrier_rejects_unfrozen_inputs(tmp_path):
    context = TaskContext(TASK, META, ArtifactStore(tmp_path), PipelineSettings())
    context.inputs = {"skip": "fixture"}
    with pytest.raises(RuntimeError, match="must be frozen"):
        ReferenceOracleStage().run(context)


def test_missing_witness_cache_cannot_run_sampler_or_sandbox(tmp_path, monkeypatch):
    context = TaskContext(TASK, META, ArtifactStore(tmp_path, read_only=True), PipelineSettings())
    context.packet = {"task_id": TASK["task_id"]}
    monkeypatch.setattr("final.modular.stages.witness_sampling.candidate_pool", lambda *args: pytest.fail("Sampler invoked"))
    with pytest.raises(FileNotFoundError, match="saved witnesses"):
        WitnessSamplingStage(ToolInputArm()).run(context)


def test_read_only_rejects_live_adapter_and_live_pipeline_calls(cached_run):
    cohort_path, cohort_task, output_directory, expected_summary = cached_run
    artifacts = ArtifactStore(output_directory, read_only=True)
    with pytest.raises(ValueError, match="read-only"):
        RecoveryModelCalls(object(), artifacts)
    with pytest.raises(ValueError, match="cached model calls"):
        BenchmarkPipeline(cohort_path, artifacts, calls=object())


def test_read_only_store_never_computes_missing_artifacts(tmp_path):
    artifacts = ArtifactStore(tmp_path, read_only=True)
    with pytest.raises(FileNotFoundError):
        artifacts.load_or_compute("missing.json", lambda: pytest.fail("Unexpected execution"))
    with pytest.raises(ValueError, match="inside"):
        artifacts.path("../escape.json")


def test_standalone_writer_and_base_filter_classes_match_existing_cohort(cached_run):
    cohort_path, expected_task, output_directory, expected_summary = cached_run
    cohort_store = ArtifactStore(cohort_path.parent, read_only=True)
    context = TaskContext(TASK, META, cohort_store, PipelineSettings(), CachedModelCalls(cohort_store))
    ProgramGenerationStage().run(context)
    BaseTestFilterStage().run(context)
    assert context.cohort_task == expected_task


def test_new_run_config_changes_cannot_reuse_previous_inputs(cached_run, tmp_path):
    cohort_path, cohort_task, output_directory, expected_summary = cached_run
    new_directory = tmp_path / "modular"
    artifacts = ArtifactStore(new_directory)
    model = FixtureModel()
    # The writer already happened in the frozen cohort; use tester fixture behavior.
    model.writer_calls = 2
    calls = FixtureCalls(model, new_directory)
    pipeline = BenchmarkPipeline(cohort_path, artifacts, calls=calls)
    result = pipeline.run([TASK], {TASK["task_id"]: META})
    assert result["arms"] == expected_summary["arms"]
    assert model.writer_calls == 2
    assert model.tester_calls == 5
    events = [json.loads(line) for line in (new_directory / "stage_events.jsonl").read_text().splitlines()]
    assert events[0]["state"] == "started"
    assert events[-1] == {"task_id": TASK["task_id"], "stage": "reporting", "state": "complete"}
    assert pipeline.run([TASK], {TASK["task_id"]: META}) == result
    assert model.tester_calls == 5
    changed_metadata = {TASK["task_id"]: dict(META, atol=.1)}
    with pytest.raises(ValueError, match="modular_manifest"):
        pipeline.run([TASK], changed_metadata)
    with pytest.raises(ValueError, match="modular_manifest"):
        changed = BenchmarkPipeline(cohort_path, artifacts, calls=calls, settings=replace(PipelineSettings(), input_seed=7))
        changed.run([TASK], {TASK["task_id"]: META})
    with pytest.raises(ValueError, match="modular_manifest"):
        pipeline.run([dict(TASK, canonical_solution="    return 999\n")], {TASK["task_id"]: META})


def test_witness_only_requires_neither_model_nor_tokenizer(cached_run, tmp_path):
    cohort_path, cohort_task, output_directory, expected_summary = cached_run
    artifacts = ArtifactStore(tmp_path / "witness-only")
    pipeline = BenchmarkPipeline(cohort_path, artifacts, arms=(WitnessOnlyArm(),))
    summary = pipeline.run([TASK], {TASK["task_id"]: META})
    assert list(summary["arms"]) == ["witness_only"]
    assert summary["tester_calls"]["invocations"] == 0
    assert summary["writer_calls"] == {}
    assert pipeline.calls is None


def test_custom_arm_configuration_invalidates_cache_before_model_calls(cached_run, tmp_path):
    from final.modular.arms.plain import PlainArm

    class ConfiguredPlainArm(PlainArm):
        def __init__(self, parameter):
            self.parameter = parameter

        def configuration(self):
            return {"parameter": self.parameter}

    cohort_path, cohort_task, output_directory, expected_summary = cached_run
    artifacts = ArtifactStore(tmp_path / "configured-arm")
    model = FixtureModel()
    calls = FixtureCalls(model, artifacts.directory)
    pipeline = BenchmarkPipeline(cohort_path, artifacts, calls=calls, arms=(ConfiguredPlainArm(1),))
    pipeline.run([TASK], {TASK["task_id"]: META})
    completed_calls = model.tester_calls
    changed = BenchmarkPipeline(cohort_path, artifacts, calls=calls, arms=(ConfiguredPlainArm(2),))
    with pytest.raises(ValueError, match="modular_manifest"):
        changed.run([TASK], {TASK["task_id"]: META})
    assert model.tester_calls == completed_calls


def test_all_task_generation_precedes_any_reference_execution(cached_run, tmp_path):
    cohort_path, cohort_task, output_directory, expected_summary = cached_run
    second_task = dict(TASK, task_id="HumanEval/1")
    second_cohort_task = dict(cohort_task, task_id=second_task["task_id"])
    cohort_tasks = [cohort_task, second_cohort_task]
    cohort = {"tasks": cohort_tasks, "cohort_sha256": digest(cohort_tasks), "dataset_sha256": DATA_SHA256}
    new_cohort_path = tmp_path / "two_tasks/cohort.json"
    save(new_cohort_path, cohort)
    artifacts = ArtifactStore(tmp_path / "two_task_run")
    calls = FixtureCalls(FixtureModel(), artifacts.directory)
    pipeline = BenchmarkPipeline(new_cohort_path, artifacts, calls=calls)
    pipeline.run([TASK, second_task], {TASK["task_id"]: META, second_task["task_id"]: META})
    generated_positions = []
    reference_positions = []
    for event_index, event in enumerate(pipeline.stage_events):
        if event["stage"] == "input_generation" and event["state"] == "complete":
            generated_positions.append(event_index)
        if event["stage"] == "reference_oracle" and event["state"] == "started":
            reference_positions.append(event_index)
    assert max(generated_positions) < min(reference_positions)


def test_cached_call_rejects_request_drift(cached_run):
    cohort_path, cohort_task, output_directory, expected_summary = cached_run
    calls = CachedModelCalls(ArtifactStore(output_directory, read_only=True))
    with pytest.raises(ValueError, match="request mismatch"):
        calls.complete(0, "plain", [], temperature=.7, max_tokens=2048, seed=314159)


def test_toolinput_only_budgets_common_prompt_before_witnesses(cached_run, tmp_path):
    cohort_path, cohort_task, output_directory, expected_summary = cached_run

    def token_count(request_messages):
        visible_count = request_messages[-1]["content"].count('"id":')
        return 10000 if visible_count > 2 else 400

    context = TaskContext(TASK, META, ArtifactStore(tmp_path / "toolinput"), PipelineSettings(),
                          SimpleNamespace(token_count=token_count), cohort_task=cohort_task)
    ConceptAnalysisStage((ToolInputArm(),)).run(context)
    assert len(context.packet["visible_put_ids"]) <= 2
    assert context.packet["prompt_tokens"] == {"toolinput": 400}
