"""Plain-only export preserves admitted records and source skips without repairing them."""
import platform
from pathlib import Path

import pytest

from final.src.audits import export_cached_plain as exporter
from final.src.audits.continue_bva_evaluation import read, save, digest, checksum


@pytest.fixture
def inputs(tmp_path):
    naive, generation, evaluation = (tmp_path / name for name in ("naive", "generation", "evaluation"))
    plain = {"inputs": [{"args": "(1,)", "kwargs": "{}", "concept_id": None}], "rejected": [], "finish_reason": "stop"}
    batches = {"HumanEval/0": {"task_id": "HumanEval/0", "arms": {"plain": plain, "v11_concept": {"inputs": []}}},
               "HumanEval/160": {"task_id": "HumanEval/160", "skip": "all_base_pass_resource_excluded"}}
    manifest = {"tasks": list(batches), "cohort_sha256": "cohort", "task_data_sha256": "tasks", "metadata_sha256": "metadata",
                "settings": {"input_budget": 20}, "model": "fixture", "python": platform.python_version(), "packages": {},
                "arms": [{"name": "plain", "class": "historical.PlainArm", "configuration": {}}, {"name": "v11_concept"}],
                "stages": [{"name": "put_evaluation", "configuration": {"execution_cache": {"directory": str(tmp_path / "cache")}}}]}
    save(naive / "modular_manifest.json", manifest)
    freeze = {task: digest(batch) for task, batch in batches.items()}
    save(naive / "generation_frozen.json", {"inputs": freeze, "inputs_sha256": digest(freeze)})
    for task, batch in batches.items():
        number = task.split('/')[-1]
        save(naive / "tasks" / number / "inputs.json", batch)
        save(naive / "tasks" / number / "packet.json", {"task_id": task, "visible_put_ids": [0]})
    save(naive / "status.json", {"state": "complete"})
    save(naive / "resource_exclusions.json", {"cohort_sha256": "cohort", "records": []})
    save(evaluation / "modular_manifest.json", manifest)
    save(evaluation / "status.json", {"state": "complete"})
    cohort = tmp_path / "cohort.json"
    save(cohort, {"tasks": [{"task_id": task, "programs": [{"id": 0, "code": "fixture"}]} for task in batches]})
    code = generation / "runtime/code.py"
    code.parent.mkdir(parents=True)
    code.write_text("fixture")
    save(generation / "launch_plan.json", {"cohort": str(cohort), "skips": []})
    save(generation / "source_snapshot.json", {"sources": {str(code): checksum(code)}, "archive": {}})
    return naive, generation, evaluation, plain


def test_plain_records_are_unchanged_and_other_arm_is_not_exported(inputs, tmp_path):
    naive, generation, evaluation, plain = inputs
    before = {str(path): checksum(path) for path in naive.rglob('*') if path.is_file()}
    output = tmp_path / "export"
    result = exporter.export(naive, generation, evaluation, output)
    batch = read(output / "tasks/0/inputs.json")
    assert batch["arms"] == {"plain": plain}
    assert result["inputs"] == 1 and result["new_model_calls"] == 0
    assert read(output / "modular_manifest.json")["protocol"] == "frozen-naive-input-export-1"
    assert before == {str(path): checksum(path) for path in naive.rglob('*') if path.is_file()}


def test_missing_source_batch_stays_empty_on_newly_eligible_targets(inputs, tmp_path):
    naive, generation, evaluation, _ = inputs
    output = tmp_path / "export"
    exporter.export(naive, generation, evaluation, output)
    batch = read(output / "tasks/160/inputs.json")
    assert not batch.get('skip')
    assert batch['arms']['plain']['inputs'] == []
    assert batch['arms']['plain']['skip'] == 'all_base_pass_resource_excluded'


def test_changed_original_input_ledger_is_rejected(inputs, tmp_path):
    naive, generation, evaluation, _ = inputs
    save(naive / "tasks/0/inputs.json", {"changed": True})
    with pytest.raises(ValueError, match="source batch changed"):
        exporter.export(naive, generation, evaluation, tmp_path / "export")


def test_cohort_hash_does_not_block_saved_export(inputs, tmp_path):
    naive, generation, evaluation, _ = inputs
    manifest = read(evaluation / "modular_manifest.json")
    manifest['cohort_sha256'] = 'other'
    save(evaluation / "modular_manifest.json", manifest)
    assert exporter.export(naive, generation, evaluation, tmp_path / 'export')['inputs'] == 1
