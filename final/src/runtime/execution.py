"""Fresh bwrap sandboxes: hidden host filesystem, no network, bounded resources."""
from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import sysconfig
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


class ExecutionError(RuntimeError):
    pass


def _prepare_workdir(directory: Path, job: dict) -> Path:
    progress = directory / "progress"
    progress.mkdir()
    for name in ("worker.py", "contracts.py"):
        shutil.copyfile(HERE / name, directory / name)
    (directory / "job.json").write_text(json.dumps(job))
    (directory / "program.py").write_text(job.get("source", ""))
    return progress


def _build_bwrap_command(python: Path, temp: str, progress: Path) -> list[str]:
    command = [
        "bwrap", "--unshare-all", "--die-with-parent", "--new-session",
        "--cap-drop", "ALL",
    ]
    for name in ("/usr", "/lib", "/lib64"):
        if Path(name).exists():
            command += ["--ro-bind", name, name]
    prefix = str(Path(sys.base_prefix).resolve())
    if not prefix.startswith("/usr/") and prefix != "/usr":
        command += ["--ro-bind", prefix, prefix]
    command += ["--ro-bind", sysconfig.get_paths()["purelib"], "/deps"]
    command += [
        "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
        "--bind", str(progress), "/execution-progress",
        "--ro-bind", temp, "/work", "--chdir", "/work",
        str(python), "-S", "-B", "/work/worker.py", "/work/job.json",
    ]
    return command


def _timeout_fallback(job: dict, progress: Path) -> dict:
    # A C-level call can delay Python's SIGALRM handler indefinitely.
    # Attribute a hard timeout only after the worker entered this
    # single input's user call, never during sandbox startup/import.
    try:
        active = json.loads((progress / "active.json").read_text())
    except (OSError, ValueError):
        active = None
    if (
        job.get("mode") in ("oracle", "evaluate", "control_flow")
        and len(job.get("tests", [])) == 1
        and active == {"mode": job["mode"], "input_index": 0}
    ):
        observation = {"status": "timeout", "timeout_source": "sandbox_wall_guard"}
        if job["mode"] == "control_flow":
            observation["domain"] = "unknown"
        return {"tests": [observation]}
    raise ExecutionError("Sandbox exceeded overall wall timeout") from None


def execute(job: dict) -> dict:
    if not shutil.which("bwrap"):
        raise ExecutionError("bubblewrap is required; refusing unsandboxed execution")
    python = Path(sys.executable).resolve()
    with tempfile.TemporaryDirectory(prefix="final-eval-") as temp:
        directory = Path(temp)
        progress = _prepare_workdir(directory, job)
        command = _build_bwrap_command(python, temp, progress)
        # -S disables host site-packages and /work is read-only. Unlike -I, this honors
        # the single Python environment setting we provide: PYTHONHASHSEED.
        env = {
            "PATH": os.defpath, "LANG": "C.UTF-8", "HOME": "/tmp", "PYTHONHASHSEED": "0",
            "FINAL_EXECUTION_PROGRESS": "/execution-progress/active.json",
            "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
        }
        wall = 10 + job["timeout"] * max(1, len(job.get("tests", [])))
        with (directory / "stdout").open("wb") as stdout, (directory / "stderr").open("wb") as stderr:
            proc = subprocess.Popen(command, env=env, stdout=stdout, stderr=stderr, start_new_session=True)
            try:
                proc.wait(timeout=wall)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
                return _timeout_fallback(job, progress)
        if proc.returncode != 0:
            details = (directory / "stderr").read_text(errors="replace").strip().splitlines()
            reason = details[-1][:400] if details else "no sandbox stderr"
            raise ExecutionError(f"Sandbox infrastructure exited {proc.returncode}: {reason}")
        try:
            result = json.loads((directory / "stdout").read_bytes())
            if not isinstance(result, dict):
                raise ValueError()
            return result
        except (ValueError, OSError):
            raise ExecutionError("Sandbox returned no valid result") from None


def execute_isolated_inputs(job):
    """Give each input a fresh sandbox so trials cannot share process state."""
    statuses = {'ok', 'invalid_domain', 'error', 'timeout'} if job['mode'] == 'oracle' else {
        'pass', 'fail', 'error', 'timeout',
    }
    observations = []
    for record in job['tests']:
        outcome = execute({**job, 'tests': [record]})
        tests = outcome.get('tests')
        if not isinstance(tests, list) or len(tests) != 1 or not isinstance(tests[0], dict):
            raise ExecutionError('Sandbox result does not match the single input')
        observation = tests[0]
        if observation.get('status') not in statuses:
            raise ExecutionError('Sandbox returned an invalid input outcome')
        if observation['status'] == 'ok' and not all(
            isinstance(observation.get(name), str) for name in ('input_key', 'expected')
        ):
            raise ExecutionError('Oracle outcome is missing its input key or expected output')
        observations.append(observation)
    return {'tests': observations}
