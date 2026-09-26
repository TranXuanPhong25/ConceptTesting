"""C++ compilation and resource-limited execution (the paper's C++ sandbox).

CodeHacker replicates the Codeforces Windows/MinGW toolchain (Appendix C,
``-static -DONLINE_JUDGE -Wl,--stack=268435456 -O2``). We run on Linux with
g++, emulate the 256 MB stack with ``RLIMIT_STACK``, and default to 64-bit
(``CH_BITS=32`` switches to ``-m32``, which mimics GNU G++14/17 on
Codeforces). Verdicts come from CPU time, peak RSS, exit status, and signals.
"""

from __future__ import annotations

import hashlib
import os
import resource
import shutil
import signal
import subprocess
import tempfile
import threading
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from codehacker_concept.data import data_dir

TESTLIB_URL = "https://raw.githubusercontent.com/MikeMirzayanov/testlib/master/testlib.h"
OUTPUT_CAP = 64 << 20
STACK_BYTES = 256 << 20
_compile_locks: dict[str, threading.Lock] = {}
_compile_guard = threading.Lock()


def include_dir() -> Path:
    path = data_dir() / "include"
    path.mkdir(parents=True, exist_ok=True)
    header = path / "testlib.h"
    if not header.exists():
        with urllib.request.urlopen(TESTLIB_URL, timeout=60) as response:
            header.write_bytes(response.read())
    return path


def bin_dir() -> Path:
    path = data_dir() / "bin"
    path.mkdir(parents=True, exist_ok=True)
    return path


def bits() -> int:
    return 32 if os.environ.get("CH_BITS") == "32" else 64


@dataclass
class CompileResult:
    ok: bool
    binary: Path | None
    error: str = ""


def _base_flags(std: str, opt: str = "-O2") -> list[str]:
    flags = [opt, f"-std={std}", "-DONLINE_JUDGE", "-w"]
    if bits() == 32:
        flags.insert(0, "-m32")
    return flags


_pch_lock = threading.Lock()


def pch_dir(opt: str = "-O2") -> Path | None:
    """Precompiled testlib.h and bits/stdc++.h for the primary standard (gnu++17).

    gcc silently falls back to the plain header when a PCH does not match
    the flags, so this only affects compile time, never semantics.
    """
    root = data_dir() / f"pch{bits()}{opt}"
    marker = root / ".ok"
    if marker.exists():
        return root
    with _pch_lock:
        if marker.exists():
            return root
        try:
            (root / "bits").mkdir(parents=True, exist_ok=True)
            probe = subprocess.run(["g++", "-print-file-name=include"], capture_output=True, text=True)
            system = subprocess.run(
                ["bash", "-c", "echo '#include <bits/stdc++.h>' | g++ -std=gnu++17 -x c++ -H -fsyntax-only - 2>&1 | head -1"],
                capture_output=True, text=True,
            ).stdout.strip().lstrip(". ")
            del probe
            if not system or not Path(system).exists():
                return None
            shutil.copy(system, root / "bits" / "stdc++.h")
            shutil.copy(include_dir() / "testlib.h", root / "testlib.h")
            for header in (root / "bits" / "stdc++.h", root / "testlib.h"):
                subprocess.run(["g++", *_base_flags("gnu++17", opt), "-x", "c++-header", str(header), "-o", str(header) + ".gch"],
                               check=True, capture_output=True, timeout=300)
            marker.write_text("ok")
            return root
        except Exception:  # noqa: BLE001 - PCH is an optimisation only
            return None


def uses_testlib(source: str) -> bool:
    return "testlib.h" in source


def _flags(std: str, opt: str = "-O2") -> list[str]:
    flags = _base_flags(std, opt)
    pch = pch_dir(opt) if std == "gnu++17" else None
    if pch is not None:
        flags += ["-I", str(pch)]
    return flags + ["-I", str(include_dir())]


def compile_key(source: str) -> str:
    return hashlib.sha256((source + f"|bits={bits()}|v3").encode()).hexdigest()[:24]


def compile_cpp(source: str, timeout: float = 120.0) -> CompileResult:
    """Compile once per (source, flags); cached on disk and thread-safe."""
    key = compile_key(source)
    binary = bin_dir() / f"{key}.bin"
    failure = bin_dir() / f"{key}.err"
    if binary.exists():
        return CompileResult(True, binary)
    if failure.exists():
        return CompileResult(False, None, failure.read_text()[:4000])
    with _compile_guard:
        lock = _compile_locks.setdefault(key, threading.Lock())
    with lock:
        if binary.exists():
            return CompileResult(True, binary)
        with tempfile.TemporaryDirectory(prefix="chc_") as tmp:
            src = Path(tmp) / "main.cpp"
            src.write_text(source)
            errors = []
            # testlib tools (validators/checkers/generators) are compiled at -O0:
            # testlib's -O2 codegen costs ~17s per program; I/O-bound tools barely slow down.
            opt = "-O0" if uses_testlib(source) else "-O2"
            for std in ("gnu++17", "gnu++20", "gnu++14"):
                out = Path(tmp) / "a.out"
                try:
                    proc = subprocess.run(
                        ["g++", *_flags(std, opt), str(src), "-o", str(out)],
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                    )
                except subprocess.TimeoutExpired:
                    errors.append(f"{std}: compile timeout")
                    continue
                if proc.returncode == 0:
                    tmp_bin = binary.with_suffix(f".tmp{os.getpid()}_{threading.get_ident()}")
                    shutil.move(str(out), tmp_bin)
                    os.replace(tmp_bin, binary)
                    return CompileResult(True, binary)
                errors.append(f"{std}: {proc.stderr[-3000:]}")
        message = "\n".join(errors)[-4000:]
        failure.write_text(message)
        return CompileResult(False, None, message)


@dataclass
class RunResult:
    status: str  # OK | RE | TLE | MLE | OLE
    exit_code: int
    stdout: str
    stderr: str
    cpu_ms: int
    wall_ms: int
    max_rss_mb: float

    @property
    def ok(self) -> bool:
        return self.status == "OK"


def _limits(cpu_seconds: int, address_mb: int | None):
    def apply() -> None:
        os.setsid()
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 1))
        try:
            resource.setrlimit(resource.RLIMIT_STACK, (STACK_BYTES, STACK_BYTES))
        except (ValueError, OSError):
            pass
        if address_mb:
            limit = address_mb << 20
            resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
        resource.setrlimit(resource.RLIMIT_FSIZE, (OUTPUT_CAP, OUTPUT_CAP))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    return apply


def run_binary(
    binary: Path,
    stdin: str | bytes,
    time_limit_ms: int = 2000,
    memory_limit_mb: int = 256,
    args: list[str] | None = None,
    wall_factor: float = 3.0,
    cwd: str | None = None,
) -> RunResult:
    """Run with CPU/memory limits; stdin/stdout go through temp files."""
    data = stdin.encode() if isinstance(stdin, str) else stdin
    cpu_seconds = max(1, int(time_limit_ms * 1.5 / 1000) + 1)
    wall_limit = time_limit_ms / 1000 * wall_factor + 2.0
    # address-space cap is generous; MLE is decided from peak RSS below
    address_mb = memory_limit_mb * 2 + 512 if bits() == 64 else min(3900, memory_limit_mb * 2 + 512)
    with tempfile.TemporaryDirectory(prefix="chr_") as tmp:
        in_path = Path(tmp) / "in.txt"
        out_path = Path(tmp) / "out.txt"
        err_path = Path(tmp) / "err.txt"
        in_path.write_bytes(data)
        start = time.monotonic()
        with in_path.open("rb") as fin, out_path.open("wb") as fout, err_path.open("wb") as ferr:
            proc = subprocess.Popen(
                [str(binary), *(args or [])],
                stdin=fin,
                stdout=fout,
                stderr=ferr,
                preexec_fn=_limits(cpu_seconds, address_mb),
                cwd=cwd or tmp,
            )
            killed = threading.Event()

            def kill() -> None:
                killed.set()
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

            timer = threading.Timer(wall_limit, kill)
            timer.start()
            try:
                _, status, usage = os.wait4(proc.pid, 0)
            finally:
                timer.cancel()
            proc.returncode = status
        wall_ms = int((time.monotonic() - start) * 1000)
        cpu_ms = int((usage.ru_utime + usage.ru_stime) * 1000)
        max_rss_mb = usage.ru_maxrss / 1024
        raw = out_path.read_bytes()[:OUTPUT_CAP]
        stderr = err_path.read_bytes()[:20000].decode(errors="replace")
    stdout = raw.decode(errors="replace")
    exit_code = os.waitstatus_to_exitcode(status)
    if killed.is_set() or cpu_ms > time_limit_ms or (os.WIFSIGNALED(status) and os.WTERMSIG(status) == signal.SIGXCPU):
        verdict = "TLE"
    elif max_rss_mb > memory_limit_mb:
        verdict = "MLE"
    elif os.WIFSIGNALED(status) and os.WTERMSIG(status) == signal.SIGXFSZ:
        verdict = "OLE"
    elif exit_code != 0:
        verdict = "RE"
    else:
        verdict = "OK"
    return RunResult(verdict, exit_code, stdout, stderr, cpu_ms, wall_ms, round(max_rss_mb, 1))


def run_cpp_source(source: str, stdin: str, time_limit_ms: int = 2000, memory_limit_mb: int = 256) -> RunResult:
    compiled = compile_cpp(source)
    if not compiled.ok or compiled.binary is None:
        return RunResult("CE", -1, "", compiled.error, 0, 0, 0.0)
    return run_binary(compiled.binary, stdin, time_limit_ms, memory_limit_mb)


def run_python(script: str, timeout_s: float = 20.0, memory_mb: int = 1024) -> RunResult:
    """The analyst's Python calculator (isolated interpreter, resource capped)."""
    import sys

    with tempfile.TemporaryDirectory(prefix="chp_") as tmp:
        path = Path(tmp) / "script.py"
        path.write_text(script)
        start = time.monotonic()
        try:
            proc = subprocess.run(
                [sys.executable, "-I", str(path)],
                capture_output=True,
                timeout=timeout_s,
                preexec_fn=_limits(int(timeout_s) + 1, memory_mb),
                cwd=tmp,
            )
        except subprocess.TimeoutExpired as exc:
            out = (exc.stdout or b"")[:20000].decode(errors="replace")
            return RunResult("TLE", -1, out, "timeout", int(timeout_s * 1000), int(timeout_s * 1000), 0.0)
        wall_ms = int((time.monotonic() - start) * 1000)
    status = "OK" if proc.returncode == 0 else "RE"
    return RunResult(status, proc.returncode, proc.stdout[:20000].decode(errors="replace"),
                     proc.stderr[-6000:].decode(errors="replace"), wall_ms, wall_ms, 0.0)
