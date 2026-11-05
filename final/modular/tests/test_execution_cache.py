"""Input cache reuse, invalidation, isolation and stability without model calls."""
import copy
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from final.modular.execution_cache import InputExecutionCache, cached_execution
from final.modular.artifacts import ArtifactStore
from final.modular.context import TaskContext, PipelineSettings
from final.modular.pipeline import BenchmarkPipeline
from final.modular.tests.test_boundary_arm import TASK, META, write_cohort
from final.modular.tests.test_input_generator import SavedInputsGenerator
from final.experiments.concept_reference_v1.execution import execute


@pytest.fixture
def executor():
    calls = []

    def run(job):
        calls.append(copy.deepcopy(job))
        assert len(job["tests"]) == 1
        record = job["tests"][0]
        if job["mode"] == "oracle":
            return {"tests": [{"status": "ok", "expected": "1", "input_key": record["args"]}]}
        return {"tests": [{"status": "pass", "actual": "1"}]}

    run.calls = calls
    return run


def job():
    return {"mode": "oracle", "context": "def f(x: int):\n    pass\n",
            "source": "def f(x):\n    return x\n", "entry": "f", "contract": "\n    assert type(x) is int\n",
            "timeout": 3, "seed": 7, "tests": [{"args": "(1,)", "kwargs": "{}"}]}


def test_shared_cache_skips_old_inputs_and_executes_only_new_ones(tmp_path, executor):
    cache = InputExecutionCache(tmp_path / "cache")
    first, counters = cache.execute(job(), repeat_index=0, executor=executor)
    expanded = job()
    expanded["tests"].append({"args": "(2,)", "kwargs": "{}"})
    second, reuse = InputExecutionCache(tmp_path / "cache").execute(expanded, repeat_index=0, executor=executor)
    assert second["tests"][0] == first["tests"][0]
    assert counters["executed_inputs"] == 1
    assert reuse["hits"] == 1 and reuse["executed_inputs"] == 1
    assert [call["tests"][0]["args"] for call in executor.calls] == ["(1,)", "(2,)"]


def test_normalized_call_matches_positional_keyword_default_and_whitespace(tmp_path, executor):
    cache = InputExecutionCache(tmp_path / "cache")
    original = job()
    original["context"] = "def f(x: int = 1):\n    pass\n"
    cache.execute(original, repeat_index=0, executor=executor)
    for record in ({"args": "[]", "kwargs": "{'x': 1}"}, {"args": "()", "kwargs": "{}"},
                   {"args": "  (1,) ", "kwargs": "{}"}):
        modified = {**original, "tests": [record]}
        _, stats = cache.execute(modified, repeat_index=0, executor=executor)
        assert stats["hits"] == 1
    assert len(executor.calls) == 1


def test_two_repeats_are_observed_independently_and_then_reused(tmp_path, executor):
    cache = InputExecutionCache(tmp_path / "cache")
    for repeat in (0, 1):
        _, stats = cache.execute(job(), repeat_index=repeat, executor=executor)
        assert stats["misses"] == 1
    assert len(executor.calls) == 2
    for repeat in (0, 1):
        _, stats = cache.execute(job(), repeat_index=repeat, executor=executor)
        assert stats["hits"] == 1
    assert len(executor.calls) == 2


@pytest.mark.parametrize("field,value", [
    ("source", "def f(x):\n    return x + 1\n"),
    ("context", "def f(x: float):\n    pass\n"), ("contract", "\n    assert x > 0\n"),
    ("seed", 8), ("timeout", 5), ("atol", 1e-4),
])
def test_execution_scope_changes_never_reuse_old_result(tmp_path, executor, field, value):
    cache = InputExecutionCache(tmp_path / "cache")
    cache.execute(job(), repeat_index=0, executor=executor)
    _, counters = cache.execute({**job(), field: value}, repeat_index=0, executor=executor)
    assert counters["misses"] == 1
    assert len(executor.calls) == 2


def test_evaluation_cache_includes_expected_output(tmp_path, executor):
    cache = InputExecutionCache(tmp_path / "cache")
    original = {**job(), "mode": "evaluate", "atol": 0,
                "tests": [{"args": "(1,)", "kwargs": "{}", "expected": "1"}]}
    cache.execute(original, repeat_index=0, executor=executor)
    changed = {**original, "tests": [{**original["tests"][0], "expected": "2"}]}
    _, stats = cache.execute(changed, repeat_index=0, executor=executor)
    assert stats["misses"] == 1


def test_type_float_bits_and_dict_order_are_preserved(tmp_path, executor):
    cache = InputExecutionCache(tmp_path / "cache")
    for literal in ("(1,)", "(True,)", "(1.0,)", "(0.0,)", "(-0.0,)",
                    "({'a': 1, 'b': 2},)", "({'b': 2, 'a': 1},)"):
        _, stats = cache.execute({**job(), "tests": [{"args": literal, "kwargs": "{}"}]},
                                repeat_index=0, executor=executor)
        assert stats["misses"] == 1
    assert len(executor.calls) == 7


def test_duplicates_across_method_records_share_one_execution_per_repeat(tmp_path, executor):
    original = job()
    original["tests"] *= 3
    result, stats = InputExecutionCache(tmp_path / "cache").execute(original, repeat_index=0, executor=executor)
    assert len(result["tests"]) == 3
    assert stats["hits"] == 2 and stats["executed_inputs"] == 1


def test_timeouts_and_infrastructure_failures_are_not_reused(tmp_path):
    calls = []

    def timeout(job):
        calls.append(job)
        return {"tests": [{"status": "timeout"}]}

    cache = InputExecutionCache(tmp_path / "cache")
    for _ in range(2):
        _, stats = cache.execute(job(), repeat_index=0, executor=timeout)
        assert stats["not_cached"] == 1
    assert len(calls) == 2

    def failure(job):
        raise RuntimeError("sandbox infrastructure failed")

    with pytest.raises(RuntimeError, match="sandbox infrastructure failed"):
        cache.execute(job(), repeat_index=0, executor=failure)


def test_corrupt_result_is_reexecuted_and_repaired(tmp_path, executor):
    directory = tmp_path / "cache"
    cache = InputExecutionCache(directory)
    cache.execute(job(), repeat_index=0, executor=executor)
    with sqlite3.connect(directory / "results.sqlite3") as database:
        database.execute("UPDATE results SET payload = ?", ('{"status":"fake"}',))
    _, stats = cache.execute(job(), repeat_index=0, executor=executor)
    assert stats["corrupt_entries"] == 1 and stats["misses"] == 1
    _, stats = cache.execute(job(), repeat_index=0, executor=executor)
    assert stats["hits"] == 1


def test_runtime_change_invalidates_cache(tmp_path, executor, monkeypatch):
    import final.modular.execution_cache as module

    cache = InputExecutionCache(tmp_path / "cache")
    monkeypatch.setattr(module, "runtime_identity", lambda: {"environment": 1})
    cache.execute(job(), repeat_index=0, executor=executor)
    monkeypatch.setattr(module, "runtime_identity", lambda: {"environment": 2})
    _, stats = cache.execute(job(), repeat_index=0, executor=executor)
    assert stats["misses"] == 1


def test_concurrent_controllers_compute_each_missing_input_once(tmp_path, executor):
    directory = tmp_path / "cache"
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(InputExecutionCache(directory).execute, job(), repeat_index=0, executor=executor)
                   for _ in range(2)]
        stats = [future.result()[1] for future in futures]
    assert len(executor.calls) == 1
    assert sum(item["hits"] for item in stats) == 1


def test_read_only_missing_run_artifact_never_executes_shared_cache(tmp_path, executor):
    context = TaskContext(TASK, META, ArtifactStore(tmp_path / "run", read_only=True), PipelineSettings())
    with pytest.raises(FileNotFoundError, match="Read-only replay requires"):
        cached_execution(context, "tasks/7/oracle_0.json", job(), 0, executor,
                         InputExecutionCache(tmp_path / "cache", read_only=True))
    assert not executor.calls
    assert not (tmp_path / "cache").exists()


def test_real_worker_isolated_state_matches_across_runs(tmp_path):
    source = "import math\ndef f(x):\n    original = math.sqrt(9)\n    math.sqrt = lambda x: 99\n    return original\n"
    request = {**job(), "source": source, "tests": [{"args": "(1,)", "kwargs": "{}"},
                                                     {"args": "(2,)", "kwargs": "{}"}]}
    cache = InputExecutionCache(tmp_path / "cache")
    first, stats = cache.execute(request, repeat_index=0, executor=execute)
    assert [item["expected"] for item in first["tests"]] == ["3.0", "3.0"]
    second, reused = cache.execute({**request, "tests": list(reversed(request["tests"]))},
                                   repeat_index=0, executor=execute)
    assert [item["expected"] for item in second["tests"]] == ["3.0", "3.0"]
    assert reused["hits"] == 2 and reused["executed_inputs"] == 0


def test_pipeline_new_run_reuses_reference_and_put_results_after_freeze(tmp_path):
    path = write_cohort(tmp_path / "cohort.json")
    settings = PipelineSettings(target_programs=1)
    first = BenchmarkPipeline(path, ArtifactStore(tmp_path / "run1"), input_generator=SavedInputsGenerator(), settings=settings)
    expected = first.run([TASK], {TASK["task_id"]: META})
    assert expected["input_execution_cache"]["executed_inputs"] == 4
    second = BenchmarkPipeline(path, ArtifactStore(tmp_path / "run2"), input_generator=SavedInputsGenerator(), settings=settings)
    actual = second.run([TASK], {TASK["task_id"]: META})
    assert actual["arms"] == expected["arms"]
    assert actual["input_execution_cache"]["hits"] == 4
    assert actual["input_execution_cache"]["executed_inputs"] == 0
    replay = BenchmarkPipeline(path, ArtifactStore(tmp_path / "run2", read_only=True),
                               input_generator=SavedInputsGenerator(), settings=settings)
    assert replay.run([TASK], {TASK["task_id"]: META}) == actual
