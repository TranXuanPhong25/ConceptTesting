import hashlib
import json
from pathlib import Path

from .frozen_score import audit_freeze, label_slots, raw_final_slots, summarize


def write(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def test_raw_final_slots_preserve_malformed_absent_and_failed_denominators(tmp_path):
    root = tmp_path
    for arm in ("plain", "concept", "equal_evidence_raw", "inputs_only"):
        path = root / "x" / arm / "final" / "response.json"
        if arm == "plain":
            write(path, {"error": None, "value": {"tests": [
                {"arguments": "(1,)", "expected": "2"}, {"arguments": "not literal", "expected": "2"},
            ]}})
        elif arm == "concept":
            write(path, {"error": "incomplete_completion", "value": None})
        elif arm == "equal_evidence_raw":
            write(path, {"error": None, "value": {"tests": "wrong"}})
        # inputs_only is intentionally missing
    rows = raw_final_slots(root, ["x"])
    assert len(rows) == 24
    assert sum(r["raw_status"] == "present" for r in rows) == 2
    assert sum(r["raw_status"].startswith("failed_final_slot") for r in rows) == 6
    labeled = label_slots(rows, lambda *_: {"status": "passing_test"})
    report = summarize(labeled)
    assert report["plain"]["raw_slots"] == 6
    assert report["plain"]["parsed_slots"] == 1
    assert report["concept"]["labels"]["unresolved_parse"] == 6


def test_freeze_audit_reports_missing_and_digest_mismatch(tmp_path):
    payload = b"original"
    (tmp_path / "artifact.json").write_bytes(payload)
    manifest = {"artifact.json": hashlib.sha256(payload).hexdigest(), "missing.json": "deadbeef"}
    write(tmp_path / "generation_frozen.json", manifest)
    result = audit_freeze(tmp_path)
    assert result["missing"] == ["missing.json"] and not result["mismatches"]
    (tmp_path / "artifact.json").write_text("changed")
    result = audit_freeze(tmp_path)
    assert result["mismatches"] == ["artifact.json"]
