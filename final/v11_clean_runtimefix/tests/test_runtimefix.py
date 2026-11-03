"""Coverage core parity and timeout/idle regression fixtures. Never call a model."""

import json
import time

import pytest

from final.v11_clean_runtimefix.sandbox import V11Sandbox, WorkerStalled


def test_supported_python_core_preserves_normal_branch_and_generator_observations(
    tmp_path,
):
    source = (
        "def f(values):\n"
        "    total=0\n"
        "    for value in (item for item in values):\n"
        "        if value>0:\n"
        "            total+=value\n"
        "        else:\n"
        "            total-=value\n"
        "    return total\n"
    )
    job = {
        "mode": "coverage_probe",
        "source": source,
        "entry": "f",
        "inputs": [[[]], [[-2, 0, 3]], [[1, 4]]],
    }
    original = V11Sandbox(coverage_core="ctrace").execute(
        job, tmp_path / "c_core", timeout=30
    )
    fixed = V11Sandbox().execute(job, tmp_path / "python_core", timeout=30)
    assert original["core"] == "CTracer"
    assert fixed["core"] == "PyTracer"
    assert original["observations"] == fixed["observations"]


def test_timeout_in_traced_generator_does_not_lock_coverage_collection(tmp_path):
    source = "def f(n):\n    return ' '.join(str(index) for index in range(n))\n"
    job = {
        "mode": "coverage_probe",
        "source": source,
        "entry": "f",
        "inputs": [[10**18], [3], [10**18], [2], [10**18], [0]],
    }
    started_at = time.monotonic()
    result = V11Sandbox().execute(job, tmp_path / "timed_generators", timeout=20)
    assert result["core"] == "PyTracer"
    assert len(result["observations"]) == 6
    assert time.monotonic() - started_at < 20
    assert result["observations"][1]["lines"]
    assert result["observations"][3]["arcs"]


def test_idle_watchdog_restarts_once_then_raises_infrastructure_failure(tmp_path):
    sandbox = V11Sandbox(idle_timeout_seconds=2)
    with pytest.raises(WorkerStalled):
        sandbox.execute({"mode": "inactivity_probe"}, tmp_path / "locked", timeout=20)
    assert (tmp_path / "locked/idle_attempt_0.json").exists()
    assert (tmp_path / "locked/idle_attempt_1.json").exists()
    assert not (tmp_path / "locked/result.json").exists()
    assert not isinstance(WorkerStalled(), RuntimeError)
    metadata = json.loads((tmp_path / "locked/worker_runtime.json").read_text())
    assert metadata["max_idle_restarts"] == 1


def test_deadline_after_idle_restart_remains_infrastructure_failure(tmp_path):
    sandbox = V11Sandbox(idle_timeout_seconds=2)
    with pytest.raises(WorkerStalled):
        sandbox.execute(
            {"mode": "inactivity_probe"}, tmp_path / "short_retry_budget", timeout=4.3
        )
    second_attempt = json.loads(
        (tmp_path / "short_retry_budget/idle_attempt_1.json").read_text()
    )
    assert second_attempt["state"] == "overall_deadline_after_idle_restart"
