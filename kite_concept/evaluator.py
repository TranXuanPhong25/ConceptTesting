from __future__ import annotations

import hashlib
import os
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class Execution:
    version: str
    attempt: int
    returncode: int
    timed_out: bool
    duration_seconds: float
    stdout_sha256: str
    stderr_tail: str

    @property
    def passed(self) -> bool:
        return self.returncode == 0 and not self.timed_out


@dataclass(frozen=True)
class Detection:
    detected: bool
    stable: bool
    fixed_runs: tuple[Execution, ...]
    buggy_runs: tuple[Execution, ...]
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


def run_command(command: list[str], cwd: Path, version: str, attempt: int, timeout: float, env: dict[str, str] | None = None) -> Execution:
    started = time.monotonic()
    try:
        process = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, timeout=timeout, check=False)
        code, timed_out, out, err = process.returncode, False, process.stdout, process.stderr
    except subprocess.TimeoutExpired as exc:
        code, timed_out = 124, True
        out = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        err = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
    return Execution(version, attempt, code, timed_out, time.monotonic() - started, hashlib.sha256(out.encode()).hexdigest(), err[-2000:])


def independent_reexecution(
    fixed: Callable[[int], Execution], buggy: Callable[[int], Execution], reruns: int = 2
) -> Detection:
    """AnyPoC-style fresh re-execution. At least two runs are always required."""
    if reruns < 2:
        raise ValueError("reruns must be at least two")
    fixed_runs = tuple(fixed(i) for i in range(1, reruns + 1))
    buggy_runs = tuple(buggy(i) for i in range(1, reruns + 1))
    fixed_pass = all(run.passed for run in fixed_runs)
    buggy_fail = all(not run.passed for run in buggy_runs)
    fixed_consistent = len({(r.returncode, r.timed_out, r.stdout_sha256) for r in fixed_runs}) == 1
    buggy_consistent = len({(r.returncode, r.timed_out, r.stdout_sha256) for r in buggy_runs}) == 1
    stable = fixed_consistent and buggy_consistent
    if not fixed_pass:
        reason = "test does not pass on every fixed-version execution"
    elif not buggy_fail:
        reason = "test does not fail on every buggy-version execution"
    elif not stable:
        reason = "independent executions are inconsistent"
    else:
        reason = "stable fixed-pass/buggy-fail witness"
    return Detection(fixed_pass and buggy_fail and stable, stable, fixed_runs, buggy_runs, reason)


def defects4j_test_runner(checkout: Path, test_name: str, java_home: Path, timeout: float = 300) -> Callable[[int], Execution]:
    env = dict(os.environ, JAVA_HOME=str(java_home), PATH=f"{java_home / 'bin'}:{os.environ.get('PATH', '')}")
    return lambda attempt: run_command(
        ["defects4j", "test", "-t", test_name], checkout, checkout.name, attempt, timeout, env
    )

