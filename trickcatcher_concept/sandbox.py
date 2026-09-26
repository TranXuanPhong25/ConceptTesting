"""Compile and run C++/Python programs on stdin with resource limits.

Outputs are whitespace-normalized as in TrickyBugs' judge (``oj t`` ignores
spaces/newlines). Decimal tokens are rounded to 6 places so that formatting
differences in floating-point answers are not reported as bugs; the same
normalization is used by every arm and by the evaluator.
"""

from __future__ import annotations

import hashlib
import os
import re
import resource
import subprocess
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path

DATA_ROOT = Path(os.environ.get("TCC_DATA", "/home/phong/dev/trickcatcher-concept-data"))
PYTHON = os.environ.get("TCC_PYTHON", str(DATA_ROOT / "runvenv" / "bin" / "python"))
CXX_FLAGS = ["-std=gnu++17", "-O2", "-DONLINE_JUDGE", "-fno-stack-protector", "-U_FORTIFY_SOURCE",
             "-U_GLIBCXX_ASSERTIONS", "-include", "cassert", "-w"]
OK, RUN_ERROR, TIME_OUT, COMPILE_ERROR = "OK", "RUN_ERROR", "TIME_OUT", "COMPILE_ERROR"
MAX_KEY_CHARS = 4096
_FLOAT = re.compile(r"^[-+]?(\d+\.\d*|\.\d+|\d+(\.\d*)?[eE][-+]?\d+)$")
_compile_locks: dict[str, threading.Lock] = {}
_compile_guard = threading.Lock()
_process_slots = threading.BoundedSemaphore(int(os.environ.get("TCC_PROCS", "12")))


def set_parallelism(n: int) -> None:
    """Bound the number of concurrently running child processes."""
    global _process_slots
    _process_slots = threading.BoundedSemaphore(n)


def process_slot():
    return _process_slots


@dataclass(frozen=True)
class Program:
    kind: str  # "cpp" binary or "py" script
    path: str
    name: str = ""


@dataclass(frozen=True)
class RunResult:
    status: str
    output: str  # normalized key ("" unless OK)


def normalize_output(text: str) -> str:
    tokens = []
    for token in text.split():
        if _FLOAT.match(token):
            try:
                value = round(float(token), 6)
                token = repr(value + 0.0)
            except (ValueError, OverflowError):
                pass
        tokens.append(token)
    key = " ".join(tokens)
    if len(key) > MAX_KEY_CHARS:
        key = "sha1:" + hashlib.sha1(key.encode()).hexdigest()
    return key


ADDR_NO_RANDOMIZE = 0x0040000


def _disable_aslr() -> None:
    """Best-effort: many TrickyBugs PUTs read out-of-bounds/uninitialized memory
    (that is often the tricky bug itself). Fixing the address layout makes a
    given (binary, input) pair deterministic across repeated runs in *our*
    environment, even though it cannot reproduce the original online judge's
    memory layout. See the report's limitations section."""
    try:
        import ctypes
        libc = ctypes.CDLL(None, use_errno=True)
        libc.personality(ADDR_NO_RANDOMIZE)
    except (OSError, AttributeError):
        pass


def _limits(memory_mb: int):
    def apply() -> None:
        resource.setrlimit(resource.RLIMIT_AS, (memory_mb * 2**20, memory_mb * 2**20))
        resource.setrlimit(resource.RLIMIT_FSIZE, (256 * 2**20, 256 * 2**20))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(resource.RLIMIT_STACK, (1024 * 2**20, 1024 * 2**20))
        _disable_aslr()
        os.setsid()
    return apply


def compile_cpp(source: str, cache_dir: Path) -> tuple[Program | None, str]:
    """Compile once per source hash; return (program, error text)."""
    digest = hashlib.sha256((source + " ".join(CXX_FLAGS)).encode()).hexdigest()[:24]
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    binary = cache_dir / f"{digest}.bin"
    failure = cache_dir / f"{digest}.err"
    with _compile_guard:
        lock = _compile_locks.setdefault(digest, threading.Lock())
    with lock:
        if binary.is_file():
            return Program("cpp", str(binary)), ""
        if failure.is_file():
            return None, failure.read_text()
        src = cache_dir / f"{digest}.cpp"
        src.write_text(source)
        try:
            proc = subprocess.run(["g++", *CXX_FLAGS, str(src), "-o", str(binary) + ".tmp"],
                                  capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            failure.write_text("compile timeout")
            return None, "compile timeout"
        if proc.returncode != 0:
            failure.write_text(proc.stderr[-4000:])
            return None, proc.stderr[-4000:]
        os.replace(str(binary) + ".tmp", binary)
        return Program("cpp", str(binary)), ""


def python_program(source: str, cache_dir: Path) -> Program:
    digest = hashlib.sha256(source.encode()).hexdigest()[:24]
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{digest}.py"
    if not path.is_file():
        path.write_text(source)
    return Program("py", str(path))


def run_program(program: Program, stdin_text: str, timeout: float = 5.0, memory_mb: int = 4096) -> RunResult:
    with _process_slots:
        return _run_program(program, stdin_text, timeout, memory_mb)


def _run_program(program: Program, stdin_text: str, timeout: float, memory_mb: int) -> RunResult:
    cmd = [program.path] if program.kind == "cpp" else [PYTHON, program.path]
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as inp, tempfile.TemporaryDirectory() as cwd:
        inp.write(stdin_text.encode())
        inp.seek(0)
        try:
            proc = subprocess.Popen(cmd, stdin=inp, stdout=out, stderr=subprocess.DEVNULL, cwd=cwd,
                                    preexec_fn=_limits(memory_mb if program.kind == "cpp" else max(memory_mb, 4096)))
        except OSError:
            return RunResult(RUN_ERROR, "")
        try:
            code = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, 9)
            except ProcessLookupError:
                pass
            proc.wait()
            return RunResult(TIME_OUT, "")
        if code != 0:
            return RunResult(RUN_ERROR, "")
        out.seek(0)
        data = out.read(64 * 2**20).decode("utf-8", errors="replace")
    key = normalize_output(data)
    if not key:
        return RunResult(RUN_ERROR, "")  # the paper drops empty outputs
    return RunResult(OK, key)


def run_script(script: Path, cwd: Path, timeout: float = 120.0, memory_mb: int = 4096) -> tuple[int | str, str]:
    """Run an LLM-written Python input generator inside ``cwd``."""
    try:
        with _process_slots:
            proc = subprocess.run([PYTHON, str(script)], cwd=cwd, capture_output=True, text=True,
                                  timeout=timeout, preexec_fn=_limits(memory_mb))
    except subprocess.TimeoutExpired:
        return TIME_OUT, ""
    return proc.returncode, (proc.stderr or "")[-2000:]
