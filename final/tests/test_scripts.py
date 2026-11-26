"""Unit tests for the CLI scripts under final.src.scripts (offline, 0 LLM calls)."""
from __future__ import annotations

import json
from pathlib import Path

from final.src.models.core_model import ModelResponse
from final.src.runtime.artifacts import digest, save
from final.src.scripts import (
    evaluate_saved,
    generate_puts,
    run_v2_cf,
    test_random_pipeline,
    union_results,
)
from final.src.scripts._formatting import collect_run_results, format_table, render_arm_union_tables


def _write_result(run_dir: Path, task_number: int, task_id: str, base_pass: int, arms: dict) -> None:
    path = run_dir / f"tasks/{task_number}/result.json"
    save(
        path,
        {
            "task_id": task_id,
            "base_pass": base_pass,
            "arms": arms,
        },
    )


class _FakeModel:
    """Minimal fake model injected via monkeypatch in unit tests only."""

    model_id = "unit-test-fake-model"

    def tokens(self, messages) -> int:
        return max(1, len(json.dumps(messages)) // 4)

    def prepare_generation(self, messages, max_tokens):
        return {"messages": messages, "max_tokens": max_tokens}

    def generate_prepared(self, prepared, *, temperature, seed, response_format=None):
        return self.generate(prepared["messages"], temperature=temperature, max_tokens=prepared["max_tokens"], seed=seed)

    def generate(self, messages, **kwargs) -> ModelResponse:
        text = json.dumps(messages)
        if "Implement this specification" in text:
            payload = {
                "programs": [
                    {
                        "approach": "buggy_false",
                        "code": (
                            "from typing import List\n"
                            "def has_close_elements(numbers: List[float], threshold: float) -> bool:\n"
                            "    return False\n"
                        ),
                    }
                ]
            }
        else:
            payload = {
                "inputs": [
                    {"args": "([1.0, 2.0, 3.9, 4.0, 5.0, 2.2], 0.3)", "kwargs": "{}", "guidance_id": None},
                    {"args": "([1.0, 2.0, 3.0], 0.5)", "kwargs": "{}", "guidance_id": None},
                ]
            }
        return ModelResponse(
            text=json.dumps(payload),
            usage={"prompt_tokens": 50, "completion_tokens": 40, "total_tokens": 90},
            finish_reason="stop",
        )


def test_format_table_and_union_across_runs(tmp_path):
    run_a = tmp_path / "run_a"
    run_b = tmp_path / "run_b"

    _write_result(
        run_a,
        0,
        "HumanEval/0",
        3,
        {
            "ep_bva_v2": {"valid_inputs": 5, "detected": 1, "detected_put_ids": ["0"]},
            "decision_table_v2": {"valid_inputs": 4, "detected": 2, "detected_put_ids": ["0", "1"]},
        },
    )
    _write_result(
        run_b,
        0,
        "HumanEval/0",
        3,
        {
            "control_flow": {"valid_inputs": 6, "detected": 2, "detected_put_ids": ["1", "2"]},
        },
    )

    stats = collect_run_results([run_a, run_b])
    assert stats["eligible_tasks"] == 1
    assert stats["eligible_puts"] == 3
    assert stats["union"]["detected"] == 3
    assert stats["arms"]["ep_bva_v2"]["unique_only"] == 0
    assert stats["arms"]["decision_table_v2"]["unique_only"] == 0
    assert stats["arms"]["control_flow"]["unique_only"] == 1

    table = render_arm_union_tables(stats, show_per_task=True, show_gain=True)
    assert "UNION" in table
    assert "3/3" in table
    assert "HumanEval/0" in table
    assert format_table(["A", "B"], [["1", "2"]]).startswith("+")


def test_union_results_cli(tmp_path, capsys):
    run_dir = tmp_path / "run"
    _write_result(
        run_dir,
        7,
        "HumanEval/7",
        2,
        {
            "ep_bva_v2": {"valid_inputs": 3, "detected": 1, "detected_put_ids": ["0"]},
            "control_flow": {"valid_inputs": 2, "detected": 1, "detected_put_ids": ["1"]},
        },
    )
    export_path = tmp_path / "union.json"
    code = union_results.main(["--sources", str(run_dir), "--per-task", "--export-json", str(export_path)])
    assert code == 0
    out = capsys.readouterr().out
    assert "UNION" in out
    assert "2/2" in out
    exported = json.loads(export_path.read_text())
    assert exported["union"]["detected"] == 2


def test_run_v2_cf_replay_cli(tmp_path, capsys):
    run_dir = tmp_path / "v2_cf"
    _write_result(
        run_dir,
        0,
        "HumanEval/0",
        2,
        {
            "ep_bva_v2": {"valid_inputs": 4, "detected": 1, "detected_put_ids": ["0"]},
            "decision_table_v2": {"valid_inputs": 4, "detected": 1, "detected_put_ids": ["0"]},
            "control_flow": {"valid_inputs": 3, "detected": 1, "detected_put_ids": ["1"]},
        },
    )
    code = run_v2_cf.main(["--replay", "--artifacts", str(run_dir), "--per-task"])
    assert code == 0
    out = capsys.readouterr().out
    assert "ep_bva_v2" in out
    assert "control_flow" in out
    assert "UNION" in out
    assert "2/2" in out


def test_generate_puts_dry_run_cli(capsys):
    code = generate_puts.main(
        ["--datatype", "mbpp-py", "--mode", "dry-run", "--puts-per-task", "5", "--num-tasks", "2"]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "PUT Generation Dry-Run" in out
    assert "mbpp-py" in out
    assert "MBPP/" in out


def test_random_pipeline_and_evaluate_saved_end_to_end(tmp_path, monkeypatch, capsys):
    import final.src.models as models_pkg

    monkeypatch.setattr(models_pkg, "create_model", lambda **kwargs: _FakeModel())

    # Build a tiny 2-PUT cohort for HumanEval/0 so test_random_pipeline runs the real pipeline end-to-end.
    cohort_path = tmp_path / "cohort.json"
    records = [
        {
            "task_id": "HumanEval/0",
            "generated": 2,
            "base_pass": 2,
            "base_input_keys": [],
            "programs": [
                {
                    "id": 0,
                    "approach": "buggy_false",
                    "code": (
                        "from typing import List\n"
                        "def has_close_elements(numbers: List[float], threshold: float) -> bool:\n"
                        "    return False\n"
                    ),
                    "base": {"status": "pass", "calls": [], "coverage": {"lines": [1, 2, 3], "arcs": []}},
                },
                {
                    "id": 1,
                    "approach": "correct_sort",
                    "code": (
                        "from typing import List\n"
                        "def has_close_elements(numbers: List[float], threshold: float) -> bool:\n"
                        "    s = sorted(numbers)\n"
                        "    return any(s[i+1] - s[i] < threshold for i in range(len(s) - 1))\n"
                    ),
                    "base": {"status": "pass", "calls": [], "coverage": {"lines": [1, 2, 3, 4], "arcs": []}},
                },
            ],
        }
    ]
    save(cohort_path, {"tasks": records, "cohort_sha256": digest(records), "dataset_sha256": "unit-test"})

    run_dir = tmp_path / "random_run"
    code = test_random_pipeline.main(
        [
            "--dataset", "he-py",
            "--cohort", str(cohort_path),
            "--arms", "plain",
            "--seed", "42",
            "--output", str(run_dir),
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "Stage 0: Random Task & Pipeline Configuration" in out
    assert "Stage 1: PUT Cohort & Base Tests" in out
    assert "Stage [input_generation]" in out
    assert "Stage [reference_oracle]" in out
    assert "Stage [put_evaluation]" in out
    assert "DETECTED" in out
    assert "UNION" in out
    assert (run_dir / "modular_summary.json").exists()

    # Verify pure evaluation script on the saved inputs from that run.
    eval_dir = tmp_path / "eval_only"
    eval_code = evaluate_saved.main(
        [
            "--source", str(run_dir),
            "--cohort", str(cohort_path),
            "--output", str(eval_dir),
            "--dataset", "he-py",
            "--target-programs", "2",

            "--per-task",
        ]
    )
    assert eval_code == 0
    eval_out = capsys.readouterr().out
    assert "Pure Evaluation Summary" in eval_out
    assert "0 LLM calls" in eval_out
    assert "1/2" in eval_out
