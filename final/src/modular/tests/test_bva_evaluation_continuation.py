"""Evaluation-only recovery validates the input ledger and preserves native checkpoints."""
import json
import os
import platform
from pathlib import Path
from types import SimpleNamespace

import pytest

from final.src.audits import continue_bva_evaluation as continuation


@pytest.fixture
def frozen_source(tmp_path, monkeypatch):
    source = tmp_path / "source"
    runtime = source / "runtime"
    code = runtime / "final/src/runtime/execution.py"
    code.parent.mkdir(parents=True)
    code.write_text("frozen runtime")
    (source / ".worker.lock").touch()
    cohort = runtime / "cohort.json"
    cohort.write_text("fixture cohort")
    batch = {"task_id": "HumanEval/0", "arms": {"boundary": {"inputs": [{"args": "(1,)", "kwargs": "{}"}]}}}
    continuation.save(source / "tasks/0/inputs.json", batch)
    continuation.save(source / "tasks/0/packet.json", {"task_id": "HumanEval/0", "visible_put_ids": [0]})
    inputs = {"HumanEval/0": continuation.digest(batch)}
    continuation.save(source / "generation_frozen.json", {"cohort_sha256": "fixture", "inputs": inputs,
                                                         "inputs_sha256": continuation.digest(inputs)})
    continuation.save(source / "modular_manifest.json", {"tasks": ["HumanEval/0"], "cohort_sha256": "fixture",
        "settings": {"input_budget": 20}, "python": platform.python_version(), "packages": {},
        "stages": [{"name": "put_evaluation", "configuration": {"execution_cache": {"directory": str(tmp_path / "cache")}}}]})
    continuation.save(source / "launch_plan.json", {"cohort": str(cohort)})
    continuation.save(source / "source_snapshot.json", {"sources": {str(code): continuation.checksum(code)}, "archive": {}})
    continuation.save(source / "status.json", {"state": "interrupted"})
    continuation.save(source / "tasks/0/oracle_0.json", {"tests": [{"expected": "1", "status": "ok"}]})
    continuation.save(source / "tasks/0/evaluation/0_0.json", {"tests": [{"actual": "0", "status": "fail"}]})
    continuation.save(source / "tasks/0/result.json", {"task_id": "HumanEval/0", "arms": {"boundary": {"detected": 1}}})
    monkeypatch.setattr(continuation, "sandbox_binary", lambda: {"path": "/bin/bwrap", "sha256": "fixture", "path_policy": os.defpath})
    return source


def test_preparation_copies_native_checkpoints_without_model_calls_or_input_changes(frozen_source, tmp_path):
    source, output = frozen_source, tmp_path / "evaluation"
    before = {str(path): continuation.checksum(path) for path in source.rglob("*") if path.is_file()}
    plan = continuation.prepare(source, output)
    assert plan["new_model_calls"] == 0
    assert plan["imported_task_results"] == 1
    assert plan["runtime"] == str(source / "runtime")
    assert not (output / "tasks/0/calls").exists()
    for name in ["oracle_0.json", "evaluation/0_0.json", "result.json"]:
        assert (output / "tasks/0" / name).read_bytes() == (source / "tasks/0" / name).read_bytes()
    assert before == {str(path): continuation.checksum(path) for path in source.rglob("*") if path.is_file()}


def test_changed_frozen_input_is_rejected_before_preparing_output(frozen_source, tmp_path):
    continuation.save(frozen_source / "tasks/0/inputs.json", {"changed": True})
    output = tmp_path / "evaluation"
    with pytest.raises(ValueError, match="Frozen source inputs changed"):
        continuation.prepare(frozen_source, output)
    assert not output.exists()


def test_missing_global_freeze_cannot_start_evaluation(frozen_source, tmp_path):
    (frozen_source / "generation_frozen.json").unlink()
    with pytest.raises(FileNotFoundError):
        continuation.prepare(frozen_source, tmp_path / "evaluation")


def test_frozen_plain_export_can_use_an_explicit_shared_scoring_runtime(frozen_source, tmp_path):
    runtime = frozen_source / "runtime"
    external = tmp_path / "frozen_scoring"
    runtime.rename(external)
    execution = external / "final/src/runtime/execution.py"
    continuation.save(frozen_source / "source_snapshot.json", {"sources": {str(execution): continuation.checksum(execution)}, "archive": {}})
    continuation.save(frozen_source / "launch_plan.json", {"cohort": str(external / "cohort.json"), "frozen_runtime": str(external)})
    continuation.save(frozen_source / "status.json", {"state": "frozen_export", "new_model_calls": 0})
    plan = continuation.prepare(frozen_source, tmp_path / "evaluation")
    assert plan["runtime"] == str(external)
    assert plan["new_model_calls"] == 0


def test_launch_uses_fixed_runtime_sanitized_path_and_no_model_credentials(frozen_source, tmp_path, monkeypatch):
    output = tmp_path / "evaluation"
    continuation.prepare(frozen_source, output)
    monkeypatch.setenv("FINAL_BASE_URL", "http://fixture.invalid")
    monkeypatch.setenv("FINAL_API_KEY", "fixture-secret")
    captured = {}

    def popen(command, **options):
        captured.update(command=command, **options)
        return SimpleNamespace(pid=123)

    monkeypatch.setattr(continuation.subprocess, "Popen", popen)
    assert continuation.launch(output) == 123
    assert captured["env"]["PATH"] == os.defpath
    assert captured["env"]["PYTHONPATH"] == str(frozen_source / "runtime")
    assert "FINAL_API_KEY" not in captured["env"] and "FINAL_BASE_URL" not in captured["env"]
    assert "-P" in captured["command"] and "-B" in captured["command"]
