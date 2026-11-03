"""V11 kernels with their pinned environment, private writable scratch and no network."""

import json
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

from final.pipeline import digest, save

REPOSITORY = Path(__file__).resolve().parents[2]


class WorkerStalled(Exception):
    """An infrastructure failure, never a method-level empty test suite."""


class V11Sandbox:
    def __init__(
        self, python_path=None, *, coverage_core="pytrace", idle_timeout_seconds=120
    ):
        self.python_path = Path(
            python_path or REPOSITORY / "final/.venv_v11/bin/python"
        ).absolute()
        self.runtime_path = self.python_path.resolve().parent.parent
        self.package_path = (
            self.python_path.parent.parent / "lib/python3.11/site-packages"
        )
        self.coverage_core = coverage_core
        self.idle_timeout_seconds = idle_timeout_seconds

    @staticmethod
    def descendant_cpu_ticks(process_id):
        total_ticks = 0
        pending_process_ids = [process_id]
        while pending_process_ids:
            current_id = pending_process_ids.pop()
            process_directory = Path("/proc") / str(current_id)
            try:
                fields = (process_directory / "stat").read_text().split()
                total_ticks += int(fields[13]) + int(fields[14])
                children = (
                    process_directory / "task" / str(current_id) / "children"
                ).read_text()
                pending_process_ids.extend(int(child) for child in children.split())
            except (FileNotFoundError, ProcessLookupError):
                continue
        return total_ticks

    def wait_for_worker(self, process, timeout, progress_path=None):
        started_at = time.monotonic()
        last_progress_at = started_at
        last_cpu_ticks = -1
        last_recorded_at = started_at
        while process.poll() is None:
            remaining_timeout = timeout - (time.monotonic() - started_at)
            if remaining_timeout <= 0:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                raise RuntimeError("V11 worker exceeded wall timeout")
            try:
                process.wait(timeout=min(1, remaining_timeout))
                break
            except subprocess.TimeoutExpired:
                now = time.monotonic()
                cpu_ticks = self.descendant_cpu_ticks(process.pid)
                if cpu_ticks != last_cpu_ticks:
                    last_cpu_ticks = cpu_ticks
                    last_progress_at = now
                if progress_path is not None and now - last_recorded_at >= 5:
                    save(
                        progress_path,
                        {
                            "state": "running",
                            "pid": process.pid,
                            "process_tree_cpu_ticks": cpu_ticks,
                            "idle_seconds": round(now - last_progress_at, 1),
                            "elapsed_seconds": round(now - started_at, 1),
                            "updated_utc": time.time(),
                        },
                    )
                    last_recorded_at = now
                if now - last_progress_at >= self.idle_timeout_seconds:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                    raise WorkerStalled(
                        "Sandbox made no CPU progress; process tree terminated"
                    )
                if now - started_at >= timeout:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                    raise RuntimeError("V11 worker exceeded wall timeout")

    def execute(self, job, directory, timeout=600):
        directory = Path(directory).resolve()
        directory.mkdir(parents=True, exist_ok=True)
        job_path, result_path = directory / "job.json", directory / "result.json"
        if job_path.exists() and json.loads(job_path.read_text()) != job:
            raise ValueError("Worker job changed; use a fresh directory")
        save(job_path, job)
        if result_path.exists():
            result = json.loads(result_path.read_text())
            if "worker_error" in result:
                raise RuntimeError(f"Stored V11 worker error: {result['worker_error']}")
            return result
        command = [
            "bwrap",
            "--unshare-all",
            "--die-with-parent",
            "--new-session",
            "--cap-drop",
            "ALL",
        ]
        for runtime_directory in ["/usr", "/lib", "/lib64"]:
            if Path(runtime_directory).exists():
                command += ["--ro-bind", runtime_directory, runtime_directory]
        command += [
            "--ro-bind",
            str(self.runtime_path),
            str(self.runtime_path),
            "--ro-bind",
            str(self.package_path),
            "/deps",
            "--ro-bind",
            str(REPOSITORY / "trickcatcher_linefacts/pipelines/v11_fair"),
            "/app/trickcatcher_linefacts/pipelines/v11_fair",
            "--ro-bind",
            str(REPOSITORY / "trickcatcher_linefacts/pipelines/__init__.py"),
            "/app/trickcatcher_linefacts/pipelines/__init__.py",
            "--ro-bind",
            str(Path(__file__).with_name("worker.py")),
            "/worker.py",
            "--bind",
            str(directory),
            "/work",
            "--chdir",
            "/work",
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--tmpfs",
            "/tmp",
            str(self.python_path.resolve()),
            "-S",
            "-B",
            "-P",
            "-c",
            "import sys,runpy;sys.path[:0]=['/app','/deps'];sys.argv=['/worker.py','/work/job.json','/work/result.json'];runpy.run_path('/worker.py',run_name='__main__')",
        ]
        environment = {
            "PATH": os.defpath,
            "HOME": "/tmp",
            "LANG": "C.UTF-8",
            "PYTHONHASHSEED": "0",
            "OPENBLAS_NUM_THREADS": "1",
            "OMP_NUM_THREADS": "1",
            # CTracer can retain collector.data_lock when SIGALRM interrupts a
            # traced generator. Use coverage.py's supported Python tracer core.
            "COVERAGE_CORE": self.coverage_core,
        }
        save(
            directory / "worker_runtime.json",
            {
                "coverage_core": self.coverage_core,
                "idle_timeout_seconds": self.idle_timeout_seconds,
                "max_idle_restarts": 1,
            },
        )
        overall_deadline = time.monotonic() + timeout
        existing_attempt_numbers = []
        for path in directory.glob("native_attempt_*"):
            if path.is_dir() and path.name.rsplit("_", 1)[-1].isdigit():
                existing_attempt_numbers.append(int(path.name.rsplit("_", 1)[-1]))
        next_attempt_number = max(existing_attempt_numbers, default=-1) + 1
        successful_work_directory = None
        for restart_index in range(2):
            remaining_timeout = overall_deadline - time.monotonic()
            if remaining_timeout <= 0:
                if restart_index > 0:
                    raise WorkerStalled(
                        "Overall wall budget exhausted after infrastructure idle restart"
                    )
                raise RuntimeError("V11 worker exceeded overall wall timeout")
            work_directory = (
                directory / f"native_attempt_{next_attempt_number + restart_index:04d}"
            )
            work_directory.mkdir()
            save(work_directory / "job.json", job)
            attempt_command = list(command)
            bind_index = attempt_command.index("--bind")
            attempt_command[bind_index + 1] = str(work_directory)
            try:
                with (
                    (work_directory / "stdout.log").open("wb") as stdout,
                    (work_directory / "stderr.log").open("wb") as stderr,
                ):
                    process = subprocess.Popen(
                        attempt_command,
                        env=environment,
                        stdout=stdout,
                        stderr=stderr,
                        start_new_session=True,
                    )
                    self.wait_for_worker(
                        process, remaining_timeout, directory / "worker_progress.json"
                    )
                successful_work_directory = work_directory
                break
            except WorkerStalled:
                for filename in ("stdout.log", "stderr.log"):
                    shutil.copyfile(
                        work_directory / filename,
                        directory / f"idle_attempt_{restart_index}_{filename}",
                    )
                save(
                    directory / f"idle_attempt_{restart_index}.json",
                    {"state": "worker_stalled", "restart_index": restart_index},
                )
                if restart_index == 1:
                    raise
            except RuntimeError:
                if restart_index > 0:
                    save(
                        directory / f"idle_attempt_{restart_index}.json",
                        {
                            "state": "overall_deadline_after_idle_restart",
                            "restart_index": restart_index,
                        },
                    )
                    raise WorkerStalled(
                        "Overall wall budget exhausted after infrastructure idle restart"
                    ) from None
                raise
        attempt_result_path = successful_work_directory / "result.json"
        if process.returncode or not attempt_result_path.exists():
            raise RuntimeError(f"V11 sandbox failed with exit{process.returncode}")
        for filename in ("stdout.log", "stderr.log"):
            shutil.copyfile(successful_work_directory / filename, directory / filename)
        result = json.loads(attempt_result_path.read_text())
        if "worker_error" in result:
            raise RuntimeError(f"V11 worker error: {result['worker_error']}")
        save(result_path, result)
        save(
            directory / "worker_progress.json",
            {"state": "complete", "updated_utc": time.time()},
        )
        return result
