"""Multi-language executor for TestCase-Eval submissions (C++, Java, Python, PyPy).

Port of the official `sandbox.py` (FlowRays/TestCase-Eval @ 45275c6):
same language table, compile flags, time limit (3.0 s x per-language
factor), 512 MB memory limit (RLIMIT_AS, not applied to Java, which gets
-Xmx512M), and the same verdict mapping (return code -9/137 or allocation
failure text -> memory_limit_exceeded, other non-zero -> runtime_error,
timeout -> time_limit_exceeded).

Differences, all documented in the report:
* Compiled artefacts are cached by sha256(language, source) so each of the
  12,775 submissions is compiled once instead of once per run.
* stdout goes to a file capped by RLIMIT_FSIZE (64 MB) instead of a pipe, so
  a looping wrong program cannot exhaust host memory.
* RLIMIT_STACK is raised to the memory limit (Codeforces runs with a large
  stack; the host default of 8 MB crashes deep-recursion accepted solutions).
* No psutil RSS polling; allocation failures are detected from the exit
  code and stderr only.
* Python 3 runs on CPython 3.8 and PyPy 3 / PyPy 3-64 on PyPy 3.10 v7.3.17
  (the interpreters Codeforces used for these submissions).  Python 2 and
  PyPy 2 are unsupported (14 of 10,000 Task 2 targets, 2 accepted
  submissions).
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import signal
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
DEFAULT_BUILD_DIR = REPO / "testcase_eval" / "data" / "build"
PYTHON3 = os.environ.get("TESTCASE_EVAL_PYTHON3", str(Path.home() / ".pyenv/versions/3.8.18/bin/python3.8"))
PYPY3 = os.environ.get("TESTCASE_EVAL_PYPY3", str(REPO / "vendor/pypy3.10-v7.3.17-linux64/bin/pypy3"))

# `-include cassert`: GCC 16's <bits/stdc++.h> no longer pulls in <cassert>
# (the judge's GCC 7-14 did); without it ~15 accepted submissions fail to compile.
CPP_FLAGS = "-include cassert -O2 -static -DONLINE_JUDGE -static-libstdc++ -static-libgcc -lstdc++exp"
JAVA_FLAGS = "-XX:+UseSerialGC -XX:TieredStopAtLevel=1 -XX:NewRatio=5 -Xms8M -Xss64M -DONLINE_JUDGE=true"
OUTPUT_LIMIT_BYTES = 64 * 1024 * 1024


@dataclass(frozen=True)
class LanguageConfig:
    family: str
    std: str = ""
    timeout_factor: float = 1.0


LANGUAGES: dict[str, LanguageConfig] = {
    "Python 3": LanguageConfig("python", timeout_factor=2.0),
    "PyPy 3": LanguageConfig("pypy", timeout_factor=2.0),
    "PyPy 3-64": LanguageConfig("pypy", timeout_factor=2.0),
    "C++14 (GCC 6-32)": LanguageConfig("cpp", "-std=c++14"),
    "C++17 (GCC 7-32)": LanguageConfig("cpp", "-std=c++17"),
    "C++20 (GCC 13-64)": LanguageConfig("cpp", "-std=c++20"),
    "C++23 (GCC 14-64, winlibs)": LanguageConfig("cpp", "-std=c++23"),
    "C++23 (GCC 14-64, msys2)": LanguageConfig("cpp", "-std=c++23"),
    "Java 8": LanguageConfig("java", timeout_factor=1.5),
    "Java 21": LanguageConfig("java", timeout_factor=1.5),
}


def language_family(language: str) -> str | None:
    """'cpp' | 'java' | 'python' (CPython and PyPy 3) | None for unsupported."""
    config = LANGUAGES.get(language)
    if config is None:
        return None
    return "python" if config.family in {"python", "pypy"} else config.family


def replace_java_class_name(java_code: str, new_class_name: str) -> str:
    """Verbatim port of the official `_replace_java_class_name`."""
    main_match = re.search(r"public\s+class\s+(\w+).*?public\s+static\s+void\s+main", java_code, re.DOTALL)
    if main_match:
        original = main_match.group(1)
        java_code = re.sub(f"public\\s+class\\s+{re.escape(original)}", f"public class {new_class_name}", java_code)
        java_code = re.sub(f"\\b{re.escape(original)}\\s*\\(", f"{new_class_name}(", java_code)
    else:
        java_code = re.sub(r"public\s+class\s+(\w+)", f"public class {new_class_name}", java_code)
        java_code = re.sub(
            r"(?<!public\s)(?<!public\s\s)(?<!public\s\s\s)(?<!public\s\s\s\s)class\s+(\w+)",
            f"class {new_class_name}",
            java_code,
            count=1,
        )
    return java_code


def java_layout(java_code: str) -> tuple[str, str]:
    """(file stem, main class) for compiling the submission unchanged.

    The official renaming breaks when `main` lives in a non-public class
    (5 accepted Java submissions fail the sample self-check that way), so
    the extension compiles the original source under its public class name
    and runs the class that declares `main`.
    """
    public = re.search(r"public\s+(?:final\s+|abstract\s+)*class\s+(\w+)", java_code)
    main_at = re.search(r"static\s+(?:public\s+)?void\s+main\s*\(", java_code)
    main_class = None
    if main_at:
        before = list(re.finditer(r"\bclass\s+(\w+)", java_code[: main_at.start()]))
        main_class = before[-1].group(1) if before else None
    stem = public.group(1) if public else (main_class or "Main")
    return stem, main_class or stem


def find_java_main(class_dir: Path, preferred: str) -> str | None:
    """Top-level compiled class that declares `public static void main(String[])`."""
    names = [preferred] + sorted(p.stem for p in class_dir.glob("*.class") if "$" not in p.stem and p.stem != preferred)
    for name in names:
        if not (class_dir / f"{name}.class").exists():
            continue
        out = subprocess.run(["javap", "-public", "-cp", str(class_dir), name], capture_output=True, text=True, timeout=60).stdout
        if re.search(r"public static void main\(java\.lang\.String(\[\]|\.\.\.)", out):
            return name
    return None


@dataclass
class Prepared:
    language: str
    ok: bool
    command: list[str]
    error: str = ""


class Executor:
    def __init__(self, build_dir: str | Path | None = None) -> None:
        self.build_dir = Path(build_dir or DEFAULT_BUILD_DIR)
        self.build_dir.mkdir(parents=True, exist_ok=True)
        self._locks: dict[str, threading.Lock] = {}
        self._guard = threading.Lock()

    def _lock(self, key: str) -> threading.Lock:
        with self._guard:
            return self._locks.setdefault(key, threading.Lock())

    @staticmethod
    def key(language: str, source: str) -> str:
        return hashlib.sha256((language + "\0" + source).encode("utf-8", "surrogatepass")).hexdigest()[:24]

    def prepare(self, language: str, source: str) -> Prepared:
        config = LANGUAGES.get(language)
        if config is None:
            return Prepared(language, False, [], f"Unsupported language: {language}")
        key = self.key(language, source)
        final = self.build_dir / key
        with self._lock(key):
            marker = final / "status"
            if not marker.exists():
                self._build(config, source, final)
            status = marker.read_text()
        if status != "ok":
            return Prepared(language, False, [], (final / "error.txt").read_text()[-2000:])
        if config.family == "cpp":
            return Prepared(language, True, [str(final / "main")])
        if config.family == "java":
            main_class = (final / "main_class").read_text().strip()
            return Prepared(language, True, ["java", *JAVA_FLAGS.split(), "-Xmx512M", "-cp", str(final), main_class])
        interpreter = PYTHON3 if config.family == "python" else PYPY3
        return Prepared(language, True, [interpreter, "-u", str(final / "main.py")])

    def _build(self, config: LanguageConfig, source: str, final: Path) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="build-", dir=self.build_dir))
        try:
            if config.family == "cpp":
                (tmp / "main.cpp").write_text(source)
                cmd = ["g++", config.std, *CPP_FLAGS.split(), str(tmp / "main.cpp"), "-o", str(tmp / "main")]
            elif config.family == "java":
                stem, main_class = java_layout(source)
                (tmp / f"{stem}.java").write_text(source)
                (tmp / "main_class").write_text(main_class)
                cmd = ["javac", "-encoding", "UTF-8", "-nowarn", str(tmp / f"{stem}.java")]
            else:
                (tmp / "main.py").write_text(source)
                interpreter = PYTHON3 if config.family == "python" else PYPY3
                cmd = [interpreter, "-m", "py_compile", str(tmp / "main.py")]
            try:
                result = subprocess.run(cmd, cwd=tmp, capture_output=True, text=True, timeout=120)
                ok = result.returncode == 0
                error = result.stderr
            except subprocess.TimeoutExpired:
                ok, error = False, "Compilation timeout"
            if ok and config.family == "java":
                found = find_java_main(tmp, (tmp / "main_class").read_text())
                if found:
                    (tmp / "main_class").write_text(found)
            if config.family == "cpp":
                (tmp / "main.cpp").unlink(missing_ok=True)
            (tmp / "error.txt").write_text(error or "")
            (tmp / "status").write_text("ok" if ok else "compilation_error")
            if final.exists():
                shutil.rmtree(tmp, ignore_errors=True)
            else:
                os.replace(tmp, final)
        finally:
            if tmp.exists() and tmp != final:
                shutil.rmtree(tmp, ignore_errors=True)

    def execute(
        self,
        language: str,
        source: str,
        input_data: str,
        time_limit: float = 3.0,
        memory_limit: int = 512,
    ) -> dict[str, Any]:
        prepared = self.prepare(language, source)
        if not prepared.ok:
            return {"result": "compilation_error", "output": "", "error": prepared.error[-500:], "time": 0.0}
        config = LANGUAGES[language]
        return run_command(
            prepared.command,
            input_data,
            time_limit * config.timeout_factor,
            memory_limit,
            limit_address_space=config.family != "java",
        )


def run_command(
    command: list[str],
    input_data: str,
    timeout: float,
    memory_limit: int = 512,
    limit_address_space: bool = True,
    output_limit: int = OUTPUT_LIMIT_BYTES,
) -> dict[str, Any]:
    memory_bytes = memory_limit * 1024 * 1024
    # Limits are applied with util-linux `prlimit` rather than preexec_fn: a
    # Python-level preexec_fn forces fork() and trips gRPC's fork handlers in
    # the threads that talk to Vertex AI.  Without it CPython uses vfork.
    limits = [f"--stack={memory_bytes}", f"--fsize={output_limit}", "--core=0"]
    if limit_address_space and memory_limit > 0:
        limits.append(f"--as={memory_bytes}")
    command = ["prlimit", *limits, "--", *command]

    if input_data and not input_data.endswith("\n"):
        input_data += "\n"
    with tempfile.TemporaryDirectory(prefix="run-") as td:
        in_path, out_path, err_path = Path(td) / "in.txt", Path(td) / "out.txt", Path(td) / "err.txt"
        in_path.write_text(input_data)
        with in_path.open("rb") as fin, out_path.open("wb") as fout, err_path.open("wb") as ferr:
            start = time.monotonic()
            try:
                process = subprocess.Popen(command, cwd=td, stdin=fin, stdout=fout, stderr=ferr, process_group=0)
            except OSError as exc:
                return {"result": "system_error", "output": "", "error": str(exc), "time": 0.0}
            try:
                returncode = process.wait(timeout=timeout)
                elapsed = time.monotonic() - start
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
                return {"result": "time_limit_exceeded", "output": "", "error": "Execution timeout", "time": timeout}
        stdout = out_path.read_bytes().decode("utf-8", "replace")
        stderr = err_path.read_bytes()[-4000:].decode("utf-8", "replace")
    if returncode != 0:
        lowered = stderr.lower()
        if returncode in (-9, 137) or any(
            k in lowered for k in ("bad_alloc", "out of memory", "memory allocation", "cannot allocate", "memoryerror", "outofmemoryerror")
        ):
            verdict = "memory_limit_exceeded"
        else:
            verdict = "runtime_error"
        return {"result": verdict, "output": stdout, "error": stderr[-500:], "time": elapsed, "returncode": returncode}
    return {"result": "success_run", "output": stdout, "error": stderr[-500:], "time": elapsed}


def run_python_program(source: str, input_data: str = "", timeout: float = 10.0, output_limit: int = 16 * 1024 * 1024) -> dict[str, Any]:
    """Run LLM-written helper code (validators, generators) on CPython 3.12 (the repo venv)."""
    import sys

    with tempfile.TemporaryDirectory(prefix="helper-") as td:
        path = Path(td) / "helper.py"
        path.write_text(source)
        return run_command([sys.executable, "-I", "-u", str(path)], input_data, timeout, memory_limit=2048, output_limit=output_limit)
