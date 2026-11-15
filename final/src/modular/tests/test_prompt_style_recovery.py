"""Recovery preserves received responses and rejects ambiguous/tampered imports."""
import hashlib
from argparse import Namespace
from pathlib import Path

import pytest

from final.src.audits import run_prompt_style as runner


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def checkpoint(tmp_path):
    source = tmp_path / "old"
    request = {"task": 16, "put_id": "PUT4", "arm": "direct", "model": runner.MODEL,
               "messages": [{"role": "user", "content": "generate inputs"}],
               "temperature": 0.7, "max_tokens": 2048, "seed": 314175,
               "context_tokens": 8192, "input_budget": 20}
    plan = source / "requests/16/direct.json"
    call = source / "tasks/16/calls/style_direct"
    runner.save(plan, request)
    runner.save(call / "request.json", runner.request_identity(request))
    runner.save(call / "attempt.json", {"state": "received", "request_id": runner.digest(runner.request_identity(request))})
    runner.save(call / "response.json", {"text": '{"inputs": []}', "usage": {"total_tokens": 20}})
    runner.save(source / "source_snapshot.json", {"sources": {str(plan): checksum(plan)}, "prior_outputs": {}})
    runner.save(source / "status.json", {"state": "interrupted"})
    return source, request, call


def test_received_response_can_be_imported_without_changing_source(checkpoint):
    source, request, call = checkpoint
    before = {path: checksum(path) for path in source.rglob("*.json")}
    response, dependencies = runner.reusable_response(source, 16, "direct", request)
    assert response == call / "response.json"
    assert call / "attempt.json" in dependencies
    assert before == {path: checksum(path) for path in source.rglob("*.json")}


@pytest.mark.parametrize("state", ["started", "unknown", "failed"])
def test_unresolved_attempt_is_not_regenerated(checkpoint, state):
    source, request, call = checkpoint
    attempt = runner.read(call / "attempt.json")
    attempt["state"] = state
    runner.save(call / "attempt.json", attempt)
    with pytest.raises(ValueError, match="unresolved calls cannot be retried"):
        runner.reusable_response(source, 16, "direct", request)


def test_request_checksum_must_match(checkpoint):
    source, request, call = checkpoint
    runner.save(call / "attempt.json", {"state": "received", "request_id": "wrong"})
    with pytest.raises(ValueError, match="received checkpoint"):
        runner.reusable_response(source, 16, "direct", request)


@pytest.mark.parametrize("field,value", [("model", "other"), ("seed", 1), ("put_id", "PUT0")])
def test_entire_request_must_match(checkpoint, field, value):
    source, request, _ = checkpoint
    with pytest.raises(ValueError, match="request mismatch"):
        runner.reusable_response(source, 16, "direct", {**request, field: value})


def test_inherited_response_requires_intact_receipt_and_original(checkpoint, tmp_path):
    source, request, original_call = checkpoint
    inherited_source = tmp_path / "inherited"
    call = inherited_source / "reused_calls/16/direct"
    plan = inherited_source / "requests/16/direct.json"
    runner.save(plan, request)
    runner.save(call / "request.json", runner.request_identity(request))
    original = original_call / "response.json"
    runner.save(call / "response.json", runner.read(original))
    runner.save(call / "receipt.json", {"source_response": str(original), "sha256": checksum(original),
                                         "request_identity_matched": True})
    paths = [plan, *call.glob("*.json")]
    runner.save(inherited_source / "source_snapshot.json",
                {"sources": {str(path): checksum(path) for path in paths}, "prior_outputs": {}})
    response, dependencies = runner.reusable_response(inherited_source, 16, "direct", request)
    assert response == call / "response.json"
    assert original in dependencies
    runner.save(original, {"text": "changed"})
    with pytest.raises(ValueError, match="response checksum mismatch"):
        runner.reusable_response(inherited_source, 16, "direct", request)


def test_frozen_reuse_file_tampering_rejected(checkpoint):
    source, request, _ = checkpoint
    plan = source / "requests/16/direct.json"
    snapshot = runner.read(source / "source_snapshot.json")
    snapshot["sources"][str(plan)] = "wrong"
    runner.save(source / "source_snapshot.json", snapshot)
    with pytest.raises(ValueError, match="frozen checksum mismatch"):
        runner.reusable_response(source, 16, "direct", request)


def test_recovery_allows_test_drift_but_keeps_runtime_frozen(checkpoint):
    source, _, _ = checkpoint
    test_path = source / "tests/test_fixture.py"
    runtime_path = source / "runtime.py"
    test_path.parent.mkdir()
    test_path.write_text("old test")
    runtime_path.write_text("old runtime")
    snapshot = runner.read(source / "source_snapshot.json")
    snapshot["sources"].update({str(path): checksum(path) for path in [test_path, runtime_path]})
    runner.save(source / "source_snapshot.json", snapshot)
    test_path.write_text("changed test")
    runner.validate_continuation(source)
    runtime_path.write_text("changed runtime")
    with pytest.raises(ValueError, match="Continuation frozen file changed"):
        runner.validate_continuation(source)


def test_production_snapshot_excludes_tests_and_guards_runtime():
    paths = runner.execution_sources()
    assert Path("final/src/models/model.py") in paths
    assert Path("final/src/modular/pipeline.py") in paths
    assert paths and all("tests" not in path.parts for path in paths)


def test_offline_continuation_imports_received_and_inherited_slots(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Recovery preparation must not call model or evaluate")

    monkeypatch.setattr(runner, "QwenModel", forbidden)
    monkeypatch.setattr(runner, "evaluate", forbidden)
    monkeypatch.setattr(runner, "load_tasks", lambda: [{"task_id": "HumanEval/16", "prompt": "fixture spec"}])
    monkeypatch.setattr(runner, "load_cohort", lambda path: {"tasks": [{"task_id": "HumanEval/16",
        "programs": [{"id": 4, "code": "fixture PUT", "base": {"status": "pass", "calls": []}}]}]})
    cohort = tmp_path / "cohort.json"
    runner.save(cohort, {})
    source = tmp_path / "interrupted"
    styles = tmp_path / "styles.json"
    runner.save(styles, {"settings": {"temperature": 0.7, "max_tokens": 2048,
        "context_tokens": 8192, "input_budget": 20, "model": runner.MODEL},
        "system": "fixture system", "common": "fixture common",
        "styles": {arm: "fixture guidance" for arm in runner.ARMS}})
    options = Namespace(artifacts=source, cohort=cohort, styles=styles,
                        reuse=None, no_reuse=False, continue_from=None)
    runner.prepare(options)
    (source / ".worker.lock").touch()
    runner.save(source / "status.json", {"state": "interrupted"})
    response = {"text": '{"inputs": []}', "usage": {"total_tokens": 20}}
    request = runner.read(source / "requests/16/direct.json")
    call = source / "tasks/16/calls/style_direct"
    runner.save(call / "request.json", runner.request_identity(request))
    runner.save(call / "attempt.json", {"state": "received", "request_id": runner.digest(runner.request_identity(request))})
    runner.save(call / "response.json", response)
    original = tmp_path / "original_response.json"
    runner.save(original, response)
    inherited = source / "reused_calls/16/soft_bva"
    request = runner.read(source / "requests/16/soft_bva.json")
    runner.save(inherited / "request.json", runner.request_identity(request))
    runner.save(inherited / "response.json", response)
    runner.save(inherited / "receipt.json", {"source_response": str(original), "sha256": checksum(original),
                                             "request_identity_matched": True})
    snapshot = runner.read(source / "source_snapshot.json")
    snapshot["sources"].update({str(path): checksum(path) for path in inherited.glob("*.json")})
    runner.save(source / "source_snapshot.json", snapshot)
    before = {path: checksum(path) for path in source.rglob("*") if path.is_file()}
    options.artifacts = tmp_path / "continued"
    options.continue_from = source
    plan = runner.prepare(options)
    assert plan["logical_slots"] == 3
    assert plan["reused_slots"] == [[16, "direct"], [16, "soft_bva"]]
    assert plan["new_logical_calls"] == 1
    assert plan["reused_usage"]["total_tokens"] == 40
    runner.verify(options.artifacts)
    assert before == {path: checksum(path) for path in source.rglob("*") if path.is_file()}
