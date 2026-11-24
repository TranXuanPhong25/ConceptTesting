"""Conditional confirmation preserves detection, input indices and replay."""
import ast
from collections import Counter

import pytest

from final.src.modular.artifacts import ArtifactStore
from final.src.modular.context import PipelineSettings, TaskContext
from final.src.modular.execution_cache import InputExecutionCache
from final.src.modular.put_evaluation import evaluate_programs, evaluate_puts


def evaluation_context(directory, input_count):
    task = {"task_id": "HumanEval/7", "entry_point": "choose",
            "prompt": "def choose(xs: list):\n    pass\n"}
    context = TaskContext(task, {"atol": 0}, ArtifactStore(directory), PipelineSettings())
    context.cohort_task = {"programs": [
        {"id": 4, "code": "def choose(xs):\n    return 0\n", "base": {"status": "pass"}},
        {"id": 9, "code": "raise AssertionError('base failure must be skipped')", "base": {"status": "fail"}},
    ]}
    context.inputs = {"arms": {"plain": {}}}
    context.oracle = {"tests": [], "arm_indices": {"plain": list(range(input_count))}, "rejected": []}
    for index in range(input_count):
        context.oracle["tests"].append({"args": f"([{index}],)", "kwargs": "{}", "expected": "0"})
    return context


@pytest.mark.parametrize("use_cache", [False, True])
@pytest.mark.parametrize("input_count", [0, 3])
def test_first_pass_and_empty_batches_never_run_confirmation(tmp_path, monkeypatch, use_cache, input_count):
    observed_inputs = []

    def executor(job):
        observed_inputs.extend(job["tests"])
        return {"tests": [{"status": "pass"} for record in job["tests"]]}

    monkeypatch.setattr("final.src.modular.put_evaluation.execute", executor)
    cache = InputExecutionCache(tmp_path / "cache") if use_cache else None
    context = evaluation_context(tmp_path / "run", input_count)
    evaluate_puts(context, execution_cache=cache)
    assert len(observed_inputs) == input_count
    assert context.result["base_pass"] == 1
    assert context.result["outcomes"] == {"4": {"failing": [], "unstable": [], "retested": []}}
    assert context.result["arms"]["plain"]["detected"] == 0
    assert not context.artifacts.exists("tasks/7/evaluation/4_retry_1.json")

    expected = context.result
    context.artifacts = ArtifactStore(context.artifacts.directory, read_only=True)
    evaluate_puts(context, execution_cache=cache)
    assert context.result == expected
    assert len(observed_inputs) == input_count
    if use_cache:
        next_run = evaluation_context(tmp_path / "next_run", input_count)
        evaluate_puts(next_run, execution_cache=cache)
        assert next_run.result == expected
        assert len(observed_inputs) == input_count


@pytest.mark.parametrize("use_cache", [False, True])
def test_only_failures_are_retested_with_original_indices_and_separate_checkpoints(tmp_path, monkeypatch, use_cache):
    statuses = {
        0: ["pass"], 1: ["fail", "fail"], 2: ["pass"],
        3: ["timeout", "pass"], 4: ["error", "timeout"], 5: ["fail", "pass"],
    }
    attempts = Counter()
    observed_seeds = []

    def executor(job):
        results = []
        assert job["source"] == "def choose(xs):\n    return 0\n"
        for record in job["tests"]:
            input_index = ast.literal_eval(record["args"])[0][0]
            status = statuses[input_index][attempts[input_index]]
            attempts[input_index] += 1
            observed_seeds.append(job["seed"])
            results.append({"status": status})
        return {"tests": results}

    monkeypatch.setattr("final.src.modular.put_evaluation.execute", executor)
    cache = InputExecutionCache(tmp_path / "cache") if use_cache else None
    context = evaluation_context(tmp_path / "run", 6)
    context.inputs["arms"]["flaky_only"] = {}
    context.oracle["arm_indices"]["flaky_only"] = [3, 5]
    old_second_run = {"tests": [{"status": "fail"}] * 6}
    context.artifacts.write("tasks/7/evaluation/4_1.json", old_second_run)
    evaluate_puts(context, execution_cache=cache)

    assert attempts == {0: 1, 1: 2, 2: 1, 3: 2, 4: 2, 5: 2}
    assert set(observed_seeds) == {context.settings.reference_seed + context.task_number}
    assert context.result["outcomes"] == {
        "4": {"failing": [1, 4], "unstable": [3, 4, 5], "retested": [1, 3, 4, 5]},
    }
    assert context.result["arms"]["plain"]["detected_put_ids"] == ["4"]
    assert context.result["arms"]["flaky_only"]["detected"] == 0
    assert context.artifacts.read("tasks/7/evaluation/4_1.json") == old_second_run
    assert context.artifacts.read("tasks/7/evaluation/4_retry_1.json") == {
        "tests": [{"status": "fail"}, {"status": "pass"}, {"status": "timeout"}, {"status": "pass"}],
    }
    if use_cache:
        receipts = context.extensions["input_execution_cache"]
        assert receipts["tasks/7/evaluation/4_0.json"]["executed_inputs"] == 6
        assert receipts["tasks/7/evaluation/4_retry_1.json"]["executed_inputs"] == 4
        assert receipts["tasks/7/evaluation/4_retry_1.json"]["repeat_index"] == 1

    def unexpected_execution(job):
        pytest.fail("Read-only replay executed a program")

    monkeypatch.setattr("final.src.modular.put_evaluation.execute", unexpected_execution)
    expected = context.result
    context.artifacts = ArtifactStore(context.artifacts.directory, read_only=True)
    evaluate_puts(context, execution_cache=cache)
    assert context.result == expected


@pytest.mark.parametrize("use_cache", [False, True])
def test_real_worker_confirms_mismatches_and_exceptions_but_skips_passes(tmp_path, use_cache):
    context = evaluation_context(tmp_path / "run", 4)
    context.cohort_task["programs"][0]["code"] = (
        "def choose(xs):\n"
        "    if xs[0] == 3:\n"
        "        raise ValueError('fixture failure')\n"
        "    return 0\n"
    )
    context.oracle["tests"][1]["expected"] = "1"
    cache = InputExecutionCache(tmp_path / "cache") if use_cache else None
    evaluate_puts(context, execution_cache=cache)
    assert context.result["outcomes"] == {
        "4": {"failing": [1, 3], "unstable": [], "retested": [1, 3]},
    }
    if use_cache:
        receipts = context.extensions["input_execution_cache"]
        assert sum(receipt["executed_inputs"] for receipt in receipts.values()) == 6


@pytest.mark.parametrize("checkpoint", ["4_0.json", "4_retry_1.json"])
def test_incomplete_checkpoint_results_cannot_silently_drop_test_inputs(tmp_path, checkpoint):
    context = evaluation_context(tmp_path / "run", 2)
    context.artifacts.write("tasks/7/evaluation/4_0.json", {"tests": [{"status": "fail"}] * 2}
                            if checkpoint != "4_0.json" else {"tests": []})
    if checkpoint == "4_retry_1.json":
        context.artifacts.write("tasks/7/evaluation/" + checkpoint, {"tests": [{"status": "fail"}]})
    with pytest.raises(ValueError, match="result count"):
        evaluate_puts(context)
    assert not context.artifacts.exists("tasks/7/result.json")


def test_full_two_repeats_scorer_runs_both_full_passes(tmp_path, monkeypatch):
    calls = []

    def executor(job):
        calls.append(len(job["tests"]))
        if len(calls) == 1:
            return {"tests": [{"status": "pass"}, {"status": "fail"}, {"status": "timeout"}]}
        return {"tests": [{"status": "fail"}, {"status": "fail"}, {"status": "pass"}]}

    monkeypatch.setattr("final.src.modular.put_evaluation.execute", executor)
    context = evaluation_context(tmp_path / "run", 3)
    context.settings = PipelineSettings(scorer="full_two_repeats")
    evaluate_puts(context)
    assert calls == [3, 3]
    assert context.artifacts.exists("tasks/7/evaluation/4_0.json")
    assert context.artifacts.exists("tasks/7/evaluation/4_1.json")
    assert not context.artifacts.exists("tasks/7/evaluation/4_retry_1.json")
    assert context.result["outcomes"] == {"4": {"failing": [1], "unstable": [0, 2]}}
    assert context.result["arms"]["plain"]["detected"] == 1
