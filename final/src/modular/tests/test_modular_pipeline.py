"""Current pipeline ordering, manifest and replay invariants."""
from dataclasses import replace
import pytest
from final.src.modular.artifacts import ArtifactStore
from final.src.modular.calls import CachedModelCalls, RecordedModelCalls
from final.src.modular.context import PipelineSettings
from final.src.modular.pipeline import BenchmarkPipeline
from final.src.modular.references import TaskReferencePrograms
from final.src.modular.reference_oracle import run_reference_oracle
from final.src.modular.tests.helpers import TASK, META, write_cohort, make_context
from final.src.modular.tests.test_input_generator import SavedInputsGenerator


def pipeline_at(tmp_path):
    cohort = write_cohort(tmp_path / "cohort.json")
    return BenchmarkPipeline(cohort, ArtifactStore(tmp_path / "run"),
        input_generator=SavedInputsGenerator(), settings=PipelineSettings(target_programs=1),
        reference_programs=TaskReferencePrograms())


def test_reference_requires_inputs(tmp_path):
    context = make_context(tmp_path, None)
    with pytest.raises(RuntimeError, match="requires generated or saved inputs"):
        run_reference_oracle(context)


def test_live_calls_rejected_for_read_only_store(tmp_path):
    with pytest.raises(ValueError, match="read-only"):
        RecordedModelCalls(object(), ArtifactStore(tmp_path, read_only=True))


@pytest.mark.parametrize("read_only", [False, True])
def test_pipeline_selects_calls_for_artifact_mode(tmp_path, read_only):
    cohort = write_cohort(tmp_path / "cohort.json")
    artifacts = ArtifactStore(tmp_path / "run", read_only=read_only)
    calls = object()
    pipeline = BenchmarkPipeline(cohort, artifacts, calls=calls)
    if read_only:
        assert isinstance(pipeline.calls, CachedModelCalls)
        assert pipeline.calls.artifacts is artifacts
    else:
        assert pipeline.calls is calls


def test_read_only_store_never_computes_missing_artifacts(tmp_path):
    artifacts = ArtifactStore(tmp_path, read_only=True)
    with pytest.raises(FileNotFoundError):
        artifacts.load_or_compute("missing.json", lambda: pytest.fail("Computed during replay"))


@pytest.mark.parametrize("read_only", [False, True])
def test_saved_artifact_loads_without_computing(tmp_path, read_only):
    ArtifactStore(tmp_path).write("saved.json", {"inputs": [1, 2]})
    artifacts = ArtifactStore(tmp_path, read_only=read_only)
    assert artifacts.load_or_compute("saved.json", lambda: pytest.fail("Recomputed saved artifact")) == {"inputs": [1, 2]}


def test_manifest_records_current_settings_without_hash_guards(tmp_path):
    pipeline = pipeline_at(tmp_path)
    pipeline.run([TASK], {TASK["task_id"]: META})
    pipeline.settings = replace(pipeline.settings, input_seed=7)
    pipeline.write_manifest([TASK], {TASK["task_id"]: {**META, "atol": 1}})
    manifest = pipeline.artifacts.read("modular_manifest.json")
    assert manifest["settings"]["input_seed"] == 7
    assert "protocol" not in manifest
    assert "sources" not in manifest and "task_data_sha256" not in manifest


def test_unchanged_run_replays_without_execution(tmp_path, monkeypatch):
    pipeline = pipeline_at(tmp_path)
    expected = pipeline.run([TASK], {TASK["task_id"]: META})
    pipeline.artifacts.write("summary.json", {"legacy_summary": True})
    for name in ("reference_oracle", "put_evaluation"):
        monkeypatch.setattr(f"final.src.modular.{name}.execute", lambda job: pytest.fail("Executed during replay"))
    replay = BenchmarkPipeline(pipeline.cohort_path, ArtifactStore(tmp_path / "run", read_only=True),
        input_generator=SavedInputsGenerator(), settings=pipeline.settings,
        reference_programs=TaskReferencePrograms())
    assert replay.run([TASK], {TASK["task_id"]: META}) == expected


def test_old_cohort_hash_stage_config_replays_without_mismatch(tmp_path):
    import json
    pipeline = pipeline_at(tmp_path)
    expected = pipeline.run([TASK], {TASK["task_id"]: META})
    manifest_path = pipeline.artifacts.path("modular_manifest.json")
    manifest = json.loads(manifest_path.read_text())
    for stage in manifest["stages"]:
        if stage["name"] == "cohort_loader":
            stage["configuration"] = {"cohort_sha256": "legacy"}
    manifest["cohort_sha256"] = "legacy"
    manifest_path.write_text(json.dumps(manifest))
    replay = BenchmarkPipeline(pipeline.cohort_path,
        ArtifactStore(tmp_path / "run", read_only=True), input_generator=SavedInputsGenerator(),
        settings=pipeline.settings, reference_programs=TaskReferencePrograms())
    assert replay.run([TASK], {TASK["task_id"]: META}) == expected


def test_read_only_summary_does_not_require_manifest(tmp_path, monkeypatch):
    pipeline = pipeline_at(tmp_path)
    pipeline.run([TASK], {TASK["task_id"]: META})
    manifest_path = pipeline.artifacts.path("modular_manifest.json")
    manifest_path.unlink()
    for name in ("reference_oracle", "put_evaluation"):
        monkeypatch.setattr(f"final.src.modular.{name}.execute", lambda job: pytest.fail("Executed during replay"))
    replay = BenchmarkPipeline(pipeline.cohort_path,
        ArtifactStore(pipeline.artifacts.directory, read_only=True),
        input_generator=SavedInputsGenerator(), settings=pipeline.settings,
        reference_programs=TaskReferencePrograms())
    assert replay.run([TASK], {TASK["task_id"]: META})["arms"] == pipeline.artifacts.read("modular_summary.json")["arms"]


def test_read_only_summary_can_be_rebuilt_from_results(tmp_path, monkeypatch):
    pipeline = pipeline_at(tmp_path)
    expected = pipeline.run([TASK], {TASK["task_id"]: META})
    pipeline.artifacts.write("summary.json", expected)
    pipeline.artifacts.path("modular_summary.json").unlink()
    for name in ("reference_oracle", "put_evaluation"):
        monkeypatch.setattr(f"final.src.modular.{name}.execute", lambda job: pytest.fail("Executed during replay"))
    replay = BenchmarkPipeline(pipeline.cohort_path,
        ArtifactStore(pipeline.artifacts.directory, read_only=True),
        input_generator=SavedInputsGenerator(), settings=pipeline.settings,
        reference_programs=TaskReferencePrograms())
    assert replay.run([TASK], {TASK["task_id"]: META})["arms"] == expected["arms"]


@pytest.mark.parametrize("read_only", [False, True])
def test_legacy_run_directory_is_rejected_without_modifying_it(tmp_path, read_only):
    pipeline = pipeline_at(tmp_path)
    pipeline.artifacts.write("manifest.json", {"model": "legacy-model"})
    path = pipeline.artifacts.path("manifest.json")
    original = path.read_bytes()
    pipeline.artifacts = ArtifactStore(pipeline.artifacts.directory, read_only=read_only)
    with pytest.raises(ValueError, match="new modular run directory"):
        pipeline.write_manifest([TASK], {TASK["task_id"]: META})
    assert path.read_bytes() == original
    assert not pipeline.artifacts.exists("modular_manifest.json")
