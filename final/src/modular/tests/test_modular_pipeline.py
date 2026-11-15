"""Current pipeline ordering, manifest and replay invariants."""
from dataclasses import replace
import pytest
from final.src.modular.artifacts import ArtifactStore
from final.src.modular.calls import RecordedModelCalls
from final.src.modular.context import PipelineSettings
from final.src.modular.pipeline import BenchmarkPipeline
from final.src.modular.references import TaskReferencePrograms
from final.src.modular.stages.base import PipelineStage
from final.src.modular.stages.reference_oracle import ReferenceOracleStage
from final.src.modular.tests.test_boundary_arm import TASK, META, write_cohort, make_context
from final.src.modular.tests.test_input_generator import SavedInputsGenerator


def pipeline_at(tmp_path):
    cohort = write_cohort(tmp_path / "cohort.json")
    return BenchmarkPipeline(cohort, ArtifactStore(tmp_path / "run"),
        input_generator=SavedInputsGenerator(), settings=PipelineSettings(target_programs=1),
        reference_programs=TaskReferencePrograms())


def test_custom_stage_can_be_inserted_after_input_generation(tmp_path):
    class TraceStage(PipelineStage):
        name = "trace_inputs"
        requires = ("input_generation",)
        def run(self, context):
            context.extensions["input_count"] = len(context.inputs["arms"]["new_method"]["inputs"])
    pipeline = pipeline_at(tmp_path)
    pipeline.insert_stage(TraceStage(), after="input_generation")
    pipeline.run([TASK], {TASK["task_id"]: META})
    stages = [event["stage"] for event in pipeline.stage_events if event["state"] == "complete"]
    assert stages.index("input_generation") < stages.index("trace_inputs") < stages.index("reference_oracle")


def test_invalid_stage_insertion_rolls_back(tmp_path):
    class InvalidStage(PipelineStage):
        name = "invalid"
        requires = ("put_evaluation",)
        def run(self, context):
            pytest.fail("Invalid stage ran")
    pipeline = pipeline_at(tmp_path)
    with pytest.raises(ValueError, match="requires earlier"):
        pipeline.insert_stage(InvalidStage(), after="frozen_cohort")
    assert all(stage.name != "invalid" for stage in pipeline.generation_stages)


def test_reference_refuses_to_run_before_freeze(tmp_path):
    context = make_context(tmp_path, None)
    with pytest.raises(RuntimeError, match="frozen"):
        ReferenceOracleStage().run(context)


def test_live_calls_rejected_for_read_only_store(tmp_path):
    with pytest.raises(ValueError, match="read-only"):
        RecordedModelCalls(object(), ArtifactStore(tmp_path, read_only=True))
    cohort = write_cohort(tmp_path / "cohort.json")
    with pytest.raises(ValueError, match="cached model calls"):
        BenchmarkPipeline(cohort, ArtifactStore(tmp_path / "replay", read_only=True), calls=object())


def test_read_only_store_never_computes_missing_artifacts(tmp_path):
    artifacts = ArtifactStore(tmp_path, read_only=True)
    with pytest.raises(FileNotFoundError):
        artifacts.load_or_compute("missing.json", lambda: pytest.fail("Computed during replay"))


@pytest.mark.parametrize("read_only", [False, True])
def test_saved_artifact_loads_without_computing(tmp_path, read_only):
    ArtifactStore(tmp_path).write("saved.json", {"inputs": [1, 2]})
    artifacts = ArtifactStore(tmp_path, read_only=read_only)
    assert artifacts.load_or_compute("saved.json", lambda: pytest.fail("Recomputed saved artifact")) == {"inputs": [1, 2]}


def test_metadata_and_settings_drift_rejected_before_generation(tmp_path):
    pipeline = pipeline_at(tmp_path)
    pipeline.run([TASK], {TASK["task_id"]: META})
    with pytest.raises(ValueError, match="modular_manifest"):
        pipeline.run([TASK], {TASK["task_id"]: {**META, "atol": 1}})
    pipeline.settings = replace(pipeline.settings, input_seed=7)
    with pytest.raises(ValueError, match="modular_manifest"):
        pipeline.run([TASK], {TASK["task_id"]: META})


def test_unchanged_run_replays_without_execution(tmp_path, monkeypatch):
    pipeline = pipeline_at(tmp_path)
    expected = pipeline.run([TASK], {TASK["task_id"]: META})
    for name in ("reference_oracle", "put_evaluation"):
        monkeypatch.setattr(f"final.src.modular.stages.{name}.execute", lambda job: pytest.fail("Executed during replay"))
    replay = BenchmarkPipeline(pipeline.cohort_stage.cohort_path, ArtifactStore(tmp_path / "run", read_only=True),
        input_generator=SavedInputsGenerator(), settings=pipeline.settings,
        reference_programs=TaskReferencePrograms())
    assert replay.run([TASK], {TASK["task_id"]: META}) == expected


@pytest.mark.parametrize("manifest_change", ["missing", "old_protocol"])
def test_read_only_replay_requires_current_manifest(tmp_path, monkeypatch, manifest_change):
    import json
    pipeline = pipeline_at(tmp_path)
    pipeline.run([TASK], {TASK["task_id"]: META})
    manifest_path = pipeline.artifacts.path("modular_manifest.json")
    if manifest_change == "missing":
        manifest_path.unlink()
        error_type = FileNotFoundError
    else:
        manifest = json.loads(manifest_path.read_text())
        manifest["protocol"] = "injectable-input-generator-v1"
        manifest_path.write_text(json.dumps(manifest))
        error_type = ValueError
    for name in ("reference_oracle", "put_evaluation"):
        monkeypatch.setattr(f"final.src.modular.stages.{name}.execute", lambda job: pytest.fail("Executed during replay"))
    replay = BenchmarkPipeline(pipeline.cohort_stage.cohort_path,
        ArtifactStore(pipeline.artifacts.directory, read_only=True),
        input_generator=SavedInputsGenerator(), settings=pipeline.settings,
        reference_programs=TaskReferencePrograms())
    with pytest.raises(error_type, match="manifest|protocol"):
        replay.run([TASK], {TASK["task_id"]: META})
