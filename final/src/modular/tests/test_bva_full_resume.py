"""Frozen-runtime continuation preserves old artifacts and rejects ambiguous calls."""
import hashlib
import json
from pathlib import Path

import pytest

from final.src.audits import resume_bva_full as resume
from final.src.runtime.artifacts import digest, save


@pytest.fixture
def stopped_run(tmp_path, monkeypatch):
    monkeypatch.setattr(resume, "ROOT", tmp_path)
    source = tmp_path / "old"
    source.mkdir()
    (source / ".worker.lock").touch()
    cohort = tmp_path / "final/out/cohort.json"
    request = {"messages": [{"role": "user", "content": "fixture"}], "temperature": 0.7, "max_tokens": 2048, "seed": 1}
    plan = {"cohort": str(cohort), "logical_call_cap": 3,
            "requests": {"0/bva_0_soft_inputs": {"request_sha256": digest(request)}}}
    save(source / "launch_plan.json", plan)
    archived = source / "source_archive/final/out/cohort.json"
    archived.parent.mkdir(parents=True)
    archived.write_text("frozen cohort")
    save(source / "source_snapshot.json", {"sources": {str(source / "launch_plan.json"): resume.sha256(source / "launch_plan.json")},
        "archive": {str(archived): resume.sha256(archived)}})
    save(source / "status.json", {"state": "interrupted"})
    call = source / "tasks/0/calls/bva_0_soft_inputs"
    save(call / "request.json", request)
    save(call / "attempt.json", {"state": "received", "request_id": digest(request), "attempt_number": 2})
    save(call / "response.json", {"text": '{"inputs":[]}', "usage": {"total_tokens": 10}})
    history = source / "tasks/0/calls/bva_0_soft_inputs_unknown_attempt_0000"
    save(history / "request.json", request)
    save(history / "attempt.json", {"state": "unknown", "request_id": digest(request), "attempt_number": 1})
    save(source / "tasks/0/inputs.json", {"task_id": "HumanEval/0", "arms": {"boundary": {"inputs": [], "programs": [
        {"program_id": 0, "logical_calls": {"generation": True}}]}}})
    return source, call


def test_received_calls_and_unknown_history_are_preserved_in_new_output(stopped_run, tmp_path):
    source, call = stopped_run
    before = {str(path): resume.sha256(path) for path in source.rglob("*") if path.is_file()}
    output = tmp_path / "new"
    plan = resume.prepare(source, output)
    assert plan["imported_received_calls"] == 1
    assert plan["remaining_new_logical_call_cap"] == 2
    assert plan["imported_completed_tasks"] == ["HumanEval/0"]
    assert plan["imported_historical_usage"]["total_tokens"] == 10
    assert Path(plan["cohort"]).read_text() == "frozen cohort"
    copied = output / call.relative_to(source)
    assert (copied / "response.json").read_bytes() == (call / "response.json").read_bytes()
    assert json.loads((copied / "attempt.json").read_text())["attempt_number"] == 2
    assert (copied.with_name(copied.name + "_unknown_attempt_0000") / "attempt.json").is_file()
    assert before == {str(path): resume.sha256(path) for path in source.rglob("*") if path.is_file()}


def test_unresolved_canonical_call_is_never_reset_or_regenerated(stopped_run, tmp_path):
    source, call = stopped_run
    attempt = json.loads((call / "attempt.json").read_text())
    attempt["state"] = "unknown"
    save(call / "attempt.json", attempt)
    with pytest.raises(ValueError, match="refusing automatic regeneration"):
        resume.prepare(source, tmp_path / "new")


def test_request_mismatch_is_rejected_before_creating_output(stopped_run, tmp_path):
    source, call = stopped_run
    request = json.loads((call / "request.json").read_text())
    request["seed"] = 2
    save(call / "request.json", request)
    output = tmp_path / "new"
    with pytest.raises(ValueError, match="mismatched checkpoint"):
        resume.prepare(source, output)
    assert not output.exists()


def test_corrupt_original_archive_is_rejected(stopped_run, tmp_path):
    source, _ = stopped_run
    (source / "source_archive/final/out/cohort.json").write_text("changed")
    with pytest.raises(ValueError, match="archive changed"):
        resume.prepare(source, tmp_path / "new")
