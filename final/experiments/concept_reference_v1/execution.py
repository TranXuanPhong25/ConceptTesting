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


def execute(job: dict) -> dict:
    if not shutil.which("bwrap"):
        raise ExecutionError("bubblewrap is required; refusing unsandboxed execution")
    python = Path(sys.executable).resolve()
    with tempfile.TemporaryDirectory(prefix="final-eval-") as temp:
        directory = Path(temp)
        for name in ("worker.py", "contracts.py"):
            shutil.copyfile(HERE / name, directory / name)
        (directory / "job.json").write_text(json.dumps(job))
        (directory / "program.py").write_text(job.get('source', ''))
        command = ["bwrap", "--unshare-all", "--die-with-parent", "--new-session",
                   "--cap-drop", "ALL"]
        for name in ("/usr", "/lib", "/lib64"):
            if Path(name).exists():
                command += ["--ro-bind", name, name]
        prefix = str(Path(sys.base_prefix).resolve())
        if not prefix.startswith("/usr/") and prefix != "/usr":
            command += ["--ro-bind", prefix, prefix]
        command += ['--ro-bind', sysconfig.get_paths()['purelib'], '/deps']
        command += ["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
                    "--ro-bind", temp, "/work", "--chdir", "/work",
                    str(python), "-S", "-B", "-P", "-c",
                        "import sys,runpy;sys.path[:0]=['/work','/deps'];"
                        "sys.argv=['/work/worker.py','/work/job.json'];"
                        "runpy.run_path('/work/worker.py',run_name='__main__')"]
        # No site packages or implicit cwd on sys.path. Unlike -I, this honors
        # the single Python environment setting we provide: PYTHONHASHSEED.
        env = {"PATH": os.defpath, "LANG": "C.UTF-8", "HOME": "/tmp", "PYTHONHASHSEED": "0",
               'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1'}
        wall = 10 + job["timeout"] * max(1, len(job.get("tests", [])))
        with (directory / "stdout").open("wb") as stdout, (directory / "stderr").open("wb") as stderr:
            proc = subprocess.Popen(command, env=env, stdout=stdout, stderr=stderr, start_new_session=True)
            try:
                proc.wait(timeout=wall)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
                raise ExecutionError("Sandbox exceeded overall wall timeout") from None
        if proc.returncode != 0:
            raise ExecutionError(f"Sandbox infrastructure exited {proc.returncode}")
        try:
            result = json.loads((directory / "stdout").read_bytes())
            if not isinstance(result, dict):
                raise ValueError()
            return result
        except (ValueError, OSError):
            raise ExecutionError("Sandbox returned no valid result") from None
