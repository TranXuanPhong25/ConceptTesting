"""Patched vendor copy of the official TestCase-Eval sandbox executor.

This is FlowRays/TestCase-Eval@45275c6's `sandbox.py` (see
vendor/upstream_sandbox.py for the exact, hash-pinned original), trimmed to
just the reusable execution classes (the paper's own `main()`/CLI/file-layout
code, which assumes their own experiment's data shape, is dropped -- it is
not a library entry point) and patched, each change marked inline with a
`# PATCH` comment and diffable against vendor/upstream_sandbox.py:

1. `execute()` used `preexec_fn=preexec_fn` (forces fork()) to apply
   RLIMIT_AS. This process also holds live gRPC channels to Vertex AI (LLM
   calls run interleaved with sandbox execution in the same worker threads --
   see generate.py), and gRPC is not fork-safe: background gRPC threads
   vanish in the forked child while their mutexes stay locked, which can hang
   or crash (the same bug class was hit and fixed for real in
   trickcatcher_concept, commit 4b5cdde). Patched to use `prlimit` (an
   external command, no fork) instead.
2. C++ compile flags lacked `-include cassert`; GCC 16's `<bits/stdc++.h>`
   (this host) no longer pulls that in the way the judge's GCC 7-14 did, so
   ~15/12,775 accepted submissions failed to compile verbatim. Patched to add
   the include.
3. `_replace_java_class_name` renamed every class to a random collision-free
   name, assuming `main` lives in the class matched by the outer `public
   class ... public static void main` span. A first attempt just fixed the
   regex to find the class immediately preceding `main` -- that passes when
   it's the only class in the file, but still fails
   (`error: class Other is public, should be declared in a file named
   Other.java`) whenever the file also has an actual public class other than
   the one holding `main`, because Java requires the filename to match the
   public class, and renaming only the main-holding class leaves that
   requirement broken. Fixed properly instead: since every call already runs
   in its own fresh directory, there is no collision to avoid renaming for in
   the first place. The submission is compiled completely unmodified, under
   whatever filename Java actually requires (`_java_file_stem`), and the
   class that actually declares `public static void main` is found
   post-compile via `javap` (`_find_java_main_class`) -- verified against the
   simple non-public-main case, the harder competing-public-class case, and a
   normal single-public-class submission.
4. Python 3 / PyPy 3 / PyPy 3-64 used whatever `python3`/`pypy3` resolve to on
   PATH. Patched to the interpreters Codeforces actually used for these
   submissions (CPython 3.8, PyPy 3.10 v7.3.17), env-overridable via
   `TESTCASE_EVAL_PYTHON3` / `TESTCASE_EVAL_PYPY3` -- otherwise programs that
   are valid on 3.8 but not on the host's default python3 (or vice versa)
   would be mis-verdicted.
5. `execute()` always compiled into a fresh, ephemeral
   `tempfile.TemporaryDirectory()`. The paper's own harness runs each
   (input, submission) pair once against static, already-generated data, so
   recompiling every time is free for them. This pipeline recompiles the SAME
   submission across up to 5 conditions x many LLM-generated inputs
   (thousands of executions per submission across a 12,775-submission
   benchmark); recompiling every call would make a full run intractable.
   Compiled artifacts are now cached in a persistent directory keyed by
   `sha256(language, source)` (`_compile`), reused across calls, with the
   actual run still happening in a fresh per-call directory for stdin/stdout
   isolation.
6. The `prlimit` wrapper from patch 1 now also sets `--fsize` (cap stdout; a
   looping wrong program fed an adversarial LLM-generated input, which this
   pipeline does on purpose to try to expose bugs, can otherwise produce
   unbounded output and exhaust host memory even under the `--as` cap, which
   Java is exempt from) and `--stack` (raised to the memory limit; this
   host's low default 8MB stack crashes legitimate deep-recursion accepted
   submissions) and `--core=0` (skip core dumps). Applied to every language,
   matching the scope of `--fsize`/`--stack`/`--core` (only `--as` stays
   Java-exempt, as in patch 1).
7. Result dicts never included the actual exit code. This repo's callers
   (validator.py, generate.py, evaluate.py) distinguish an LLM-written
   validator/generator deliberately signalling invalid input (specific small
   exit codes) from a genuine crash, which needs the raw `returncode`.
   Patched to include it whenever the process actually ran.

Everything else -- language table, other compile flags, time limit (3.0s x
per-language factor), memory limit (512MB via RLIMIT_AS / -Xmx for Java),
psutil RSS monitoring, and verdict mapping (-9/137 or allocation-failure text
-> memory_limit_exceeded, other non-zero -> runtime_error, timeout ->
time_limit_exceeded) -- is unchanged from upstream.

Addition, not a patch to existing paper logic (the paper never ran anything
like this): a "Helper Python 3" language entry using this repo's own Python
3.12 venv interpreter (`sys.executable`), plus a `run_python_program()`
convenience wrapper, for running this extension's own LLM-written
validator/generator code, which isn't a Codeforces submission and so has no
reason to match Codeforces' Python 3.8. `language_family()` and the
`Executor` alias exist only so callers written against the previous
independent implementation need no changes.
"""

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

import psutil
from enum import Enum

REPO = Path(__file__).resolve().parent.parent
DEFAULT_BUILD_DIR = REPO / "testcase_eval" / "data" / "build"
PYTHON3 = os.environ.get("TESTCASE_EVAL_PYTHON3", str(Path.home() / ".pyenv/versions/3.8.18/bin/python3.8"))
PYPY3 = os.environ.get("TESTCASE_EVAL_PYPY3", str(REPO / "vendor/pypy3.10-v7.3.17-linux64/bin/pypy3"))
OUTPUT_LIMIT_BYTES = 64 * 1024 * 1024


class ExecutionResult(Enum):
    SUCCESS_RUN = "success_run"
    PASSED = "passed"
    COMPILATION_ERROR = "compilation_error"
    WRONG_ANSWER = "wrong_answer"
    RUNTIME_ERROR = "runtime_error"
    TIME_LIMIT_EXCEEDED = "time_limit_exceeded"
    MEMORY_LIMIT_EXCEEDED = "memory_limit_exceeded"
    SYSTEM_ERROR = "system_error"
    INVALID_INPUT = "invalid_input"


class LanguageConfig:
    def __init__(self, name: str, compile_cmd: Optional[str] = None,
                 compile_flags: str = "", execute_cmd: str = "",
                 execute_flags: str = "", file_ext: str = "",
                 is_compiled: bool = False, timeout_factor: float = 1.0):
        self.name = name
        self.compile_cmd = compile_cmd
        self.compile_flags = compile_flags
        self.execute_cmd = execute_cmd
        self.execute_flags = execute_flags
        self.file_ext = file_ext
        self.is_compiled = is_compiled
        self.timeout_factor = timeout_factor


class MultiLanguageExecutor:

    def __init__(self, build_dir: str | Path | None = None):
        self.languages = self._init_languages()
        # PATCH 5 setup: persistent, content-addressed compile cache.
        self.build_dir = Path(build_dir or DEFAULT_BUILD_DIR)
        self.build_dir.mkdir(parents=True, exist_ok=True)
        self._build_locks: Dict[str, threading.Lock] = {}
        self._build_locks_guard = threading.Lock()

    def _init_languages(self) -> Dict[str, LanguageConfig]:
        return {
            "Python 2": LanguageConfig(
                name="Python 2",
                compile_cmd="python2",
                compile_flags="-m py_compile",
                execute_cmd="python2",
                execute_flags="-u",
                file_ext=".py",
                is_compiled=False,
                timeout_factor=2.0
            ),
            "Python 3": LanguageConfig(
                name="Python 3",
                compile_cmd="python3",
                compile_flags="-m py_compile",
                execute_cmd=PYTHON3,  # PATCH 4: pinned to the interpreter Codeforces used
                execute_flags="-u",
                file_ext=".py",
                is_compiled=False,
                timeout_factor=2.0
            ),
            "PyPy 2": LanguageConfig(
                name="PyPy 2",
                compile_cmd="pypy2",
                compile_flags="-m py_compile",
                execute_cmd="pypy2",
                execute_flags="-u",
                file_ext=".py",
                is_compiled=False,
                timeout_factor=2.0
            ),
            "PyPy 3": LanguageConfig(
                name="PyPy 3",
                compile_cmd="pypy3",
                compile_flags="-m py_compile",
                execute_cmd=PYPY3,  # PATCH 4
                execute_flags="-u",
                file_ext=".py",
                is_compiled=False,
                timeout_factor=2.0
            ),
            "PyPy 3-64": LanguageConfig(
                name="PyPy 3-64",
                compile_cmd="pypy3",
                compile_flags="-m py_compile",
                execute_cmd=PYPY3,  # PATCH 4
                execute_flags="-u",
                file_ext=".py",
                is_compiled=False,
                timeout_factor=2.0
            ),

            "C++14 (GCC 6-32)": LanguageConfig(
                name="C++14 (GCC 6-32)",
                compile_cmd="g++",
                # PATCH 2: -include cassert added
                compile_flags="-include cassert -std=c++14 -O2 -static -DONLINE_JUDGE -static-libstdc++ -static-libgcc -lstdc++exp",
                file_ext=".cpp",
                is_compiled=True
            ),
            "C++17 (GCC 7-32)": LanguageConfig(
                name="C++17 (GCC 7-32)",
                compile_cmd="g++",
                compile_flags="-include cassert -std=c++17 -O2 -static -DONLINE_JUDGE -static-libstdc++ -static-libgcc -lstdc++exp",
                file_ext=".cpp",
                is_compiled=True
            ),
            "C++20 (GCC 13-64)": LanguageConfig(
                name="C++20 (GCC 13-64)",
                compile_cmd="g++",
                compile_flags="-include cassert -std=c++20 -O2 -static -DONLINE_JUDGE -static-libstdc++ -static-libgcc -lstdc++exp",
                file_ext=".cpp",
                is_compiled=True
            ),
            "C++23 (GCC 14-64, winlibs)": LanguageConfig(
                name="C++23 (GCC 14-64, winlibs)",
                compile_cmd="g++",
                compile_flags="-include cassert -std=c++23 -O2 -static -DONLINE_JUDGE -static-libstdc++ -static-libgcc -lstdc++exp",
                file_ext=".cpp",
                is_compiled=True
            ),
            "C++23 (GCC 14-64, msys2)": LanguageConfig(
                name="C++23 (GCC 14-64, msys2)",
                compile_cmd="g++",
                compile_flags="-include cassert -std=c++23 -O2 -static -DONLINE_JUDGE -static-libstdc++ -static-libgcc -lstdc++exp",
                file_ext=".cpp",
                is_compiled=True
            ),

            "Java 8": LanguageConfig(
                name="Java 8",
                compile_cmd="javac",
                compile_flags="",
                execute_cmd="java",
                execute_flags="-XX:+UseSerialGC -XX:TieredStopAtLevel=1 -XX:NewRatio=5 -Xms8M -Xss64M -DONLINE_JUDGE=true",
                file_ext=".java",
                is_compiled=True,
                timeout_factor=1.5
            ),
            "Java 21": LanguageConfig(
                name="Java 21",
                compile_cmd="javac",
                compile_flags="",
                execute_cmd="java",
                execute_flags="-XX:+UseSerialGC -XX:TieredStopAtLevel=1 -XX:NewRatio=5 -Xms8M -Xss64M -DONLINE_JUDGE=true",
                file_ext=".java",
                is_compiled=True,
                timeout_factor=1.5
            ),

            # ADDITION (see module docstring): not a Codeforces submission
            # language, used only for this repo's own LLM-written helper code.
            "Helper Python 3": LanguageConfig(
                name="Helper Python 3",
                compile_cmd=None,
                execute_cmd=sys.executable,
                execute_flags="-I -u",
                file_ext=".py",
                is_compiled=False,
                timeout_factor=1.0
            ),
        }

    def _java_file_stem(self, java_code: str) -> str:
        """Filename to compile the submission's OWN, unmodified source under.

        PATCH 3 (vs vendor/upstream_sandbox.py): see module docstring.
        """
        public = re.search(r'public\s+(?:final\s+|abstract\s+)*class\s+(\w+)', java_code)
        return public.group(1) if public else "Main"

    def _find_java_main_class(self, class_dir: Path, preferred: str) -> str | None:
        """The top-level compiled class that actually declares `public static void main`."""
        names = [preferred] + sorted(p.stem for p in class_dir.glob("*.class") if "$" not in p.stem and p.stem != preferred)
        for name in names:
            if not (class_dir / f"{name}.class").exists():
                continue
            out = subprocess.run(["javap", "-public", "-cp", str(class_dir), name],
                                capture_output=True, text=True, timeout=60).stdout
            if re.search(r"public static void main\(java\.lang\.String(\[\]|\.\.\.)", out):
                return name
        return None

    def _build_lock(self, key: str) -> threading.Lock:
        with self._build_locks_guard:
            return self._build_locks.setdefault(key, threading.Lock())

    def _compile(self, language: str, lang_config: LanguageConfig, code: str) -> Dict[str, Any]:
        """PATCH 5 (vs vendor/upstream_sandbox.py): compile into a persistent,
        content-addressed directory instead of a fresh one per call, reusing
        an existing compiled artifact when the (language, source) pair has
        already been built. See module docstring for why."""
        key = hashlib.sha256((language + "\0" + code).encode("utf-8", "surrogatepass")).hexdigest()[:24]
        final = self.build_dir / key
        with self._build_lock(key):
            if not (final / "status").exists():
                tmp = Path(tempfile.mkdtemp(prefix="build-", dir=self.build_dir))
                try:
                    if language.startswith("Java"):
                        file_stem = self._java_file_stem(code)
                        source_file = tmp / f"{file_stem}{lang_config.file_ext}"
                    else:
                        source_file = tmp / f"main{lang_config.file_ext}"
                    source_file.write_text(code, encoding="utf-8")

                    if language.startswith("C++"):
                        executable = tmp / "main"
                        compile_cmd = [lang_config.compile_cmd] + lang_config.compile_flags.split() + [str(source_file), "-o", str(executable)]
                    else:
                        compile_cmd = [lang_config.compile_cmd] + lang_config.compile_flags.split() + [str(source_file)]

                    try:
                        compile_result = subprocess.run(compile_cmd, cwd=tmp, capture_output=True, text=True, timeout=30)
                        ok, error = compile_result.returncode == 0, compile_result.stderr
                    except subprocess.TimeoutExpired:
                        ok, error = False, "Compilation timeout"

                    main_class = ""
                    if ok and language.startswith("Java"):
                        found = self._find_java_main_class(tmp, file_stem)
                        if found is None:
                            ok, error = False, "no class declaring public static void main(String[]) found"
                        else:
                            main_class = found

                    if language.startswith("C++"):
                        source_file.unlink(missing_ok=True)

                    (tmp / "error.txt").write_text(error or "")
                    (tmp / "main_class.txt").write_text(main_class)
                    (tmp / "status").write_text("ok" if ok else "compilation_error")

                    if final.exists():
                        shutil.rmtree(tmp, ignore_errors=True)
                    else:
                        os.replace(tmp, final)
                finally:
                    if tmp.exists() and tmp != final:
                        shutil.rmtree(tmp, ignore_errors=True)

            status = (final / "status").read_text()

        if status != "ok":
            return {"ok": False, "error": (final / "error.txt").read_text()[-2000:]}
        return {"ok": True, "dir": final, "main_class": (final / "main_class.txt").read_text()}

    def execute(self, language: str, code: str, input_data: str = "",
                time_limit: float = 3.0, memory_limit: int = 512,
                output_limit: int = OUTPUT_LIMIT_BYTES) -> Dict[str, Any]:

        if language not in self.languages:
            return {
                "result": ExecutionResult.COMPILATION_ERROR.value,
                "output": "",
                "error": f"Unsupported language: {language}",
                "time": 0.0,
                "memory": 0
            }

        lang_config = self.languages[language]
        actual_timeout = time_limit * lang_config.timeout_factor

        try:
            artifact_dir: Path | None = None
            if lang_config.is_compiled and lang_config.compile_cmd:
                compiled = self._compile(language, lang_config, code)
                if not compiled["ok"]:
                    return {
                        "result": ExecutionResult.COMPILATION_ERROR.value,
                        "output": "",
                        "error": compiled["error"],
                        "time": 0.0,
                        "memory": 0
                    }
                artifact_dir = compiled["dir"]

            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir_path = Path(tmpdir)

                if language.startswith("Java"):
                    java_flags = lang_config.execute_flags.split()
                    java_flags.append(f"-Xmx{memory_limit}M")
                    execute_cmd = [lang_config.execute_cmd, "-cp", str(artifact_dir)] + java_flags + [compiled["main_class"]]
                elif language.startswith("C++"):
                    execute_cmd = [str(artifact_dir / "main")]
                else:
                    source_file = tmpdir_path / f"main{lang_config.file_ext}"
                    source_file.write_text(code, encoding="utf-8")
                    execute_cmd = [lang_config.execute_cmd] + lang_config.execute_flags.split() + [str(source_file)]

                try:
                    # PATCH 1 + PATCH 6 (vs vendor/upstream_sandbox.py): the
                    # original used `preexec_fn=preexec_fn` (forces fork(),
                    # unsafe alongside this pipeline's concurrent gRPC/Vertex
                    # calls -- see module docstring) to apply only RLIMIT_AS.
                    # `prlimit` (external command, no fork) applies that plus
                    # --fsize/--stack/--core, all needed for this pipeline's
                    # adversarial-input usage (see module docstring).
                    memory_limit_bytes = memory_limit * 1024 * 1024
                    limits = [f"--stack={memory_limit_bytes}", f"--fsize={output_limit}", "--core=0"]
                    if not language.startswith("Java") and memory_limit > 0:
                        limits.append(f"--as={memory_limit_bytes}")
                    if os.name == 'posix':
                        execute_cmd = ["prlimit", *limits, "--"] + execute_cmd

                    process = subprocess.Popen(
                        execute_cmd,
                        cwd=tmpdir,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                    )

                    try:
                        processed_input = input_data
                        if processed_input and not processed_input.endswith('\n'):
                            processed_input += '\n'

                        start_time = time.time()

                        max_memory = 0
                        stop_monitoring = threading.Event()

                        def monitor_memory():
                            nonlocal max_memory
                            try:
                                p = psutil.Process(process.pid)
                                while not stop_monitoring.is_set() and p.is_running():
                                    try:
                                        memory_info = p.memory_info()
                                        current_memory = memory_info.rss // 1024
                                        max_memory = max(max_memory, current_memory)
                                        time.sleep(0.01)
                                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                                        break
                            except Exception:
                                pass

                        monitor_thread = threading.Thread(target=monitor_memory, daemon=False)
                        monitor_thread.start()

                        try:
                            stdout, stderr = process.communicate(input=processed_input, timeout=actual_timeout)
                            execution_time = time.time() - start_time
                        finally:
                            stop_monitoring.set()
                            monitor_thread.join(timeout=1.0)

                    except subprocess.TimeoutExpired:
                        process.kill()
                        execution_time = actual_timeout
                        return {
                            "result": ExecutionResult.TIME_LIMIT_EXCEEDED.value,
                            "output": "",
                            "error": "Execution timeout",
                            "time": execution_time,
                            "memory": 0
                        }

                    if process.returncode != 0:
                        if process.returncode in (-9, 137):
                            return {
                                "result": ExecutionResult.MEMORY_LIMIT_EXCEEDED.value,
                                "output": stdout,
                                "error": stderr,
                                "time": execution_time,
                                "memory": max_memory,
                                "returncode": process.returncode,  # PATCH 7
                            }
                        elif (stderr and any(keyword in stderr.lower() for keyword in
                                            ['bad_alloc', 'out of memory', 'memory allocation', 'cannot allocate'])) or \
                            (max_memory > memory_limit * 1024 * 0.9):
                            return {
                                "result": ExecutionResult.MEMORY_LIMIT_EXCEEDED.value,
                                "output": stdout,
                                "error": stderr,
                                "time": execution_time,
                                "memory": max_memory,
                                "returncode": process.returncode,  # PATCH 7
                            }
                        else:
                            return {
                                "result": ExecutionResult.RUNTIME_ERROR.value,
                                "output": stdout,
                                "error": stderr,
                                "time": execution_time,
                                "memory": max_memory,
                                "returncode": process.returncode,  # PATCH 7
                            }

                    return {
                        "result": ExecutionResult.SUCCESS_RUN.value,
                        "output": stdout,
                        "error": stderr,
                        "time": execution_time,
                        "memory": max_memory,
                        "returncode": 0,  # PATCH 7
                    }

                except Exception as e:
                    return {
                        "result": ExecutionResult.RUNTIME_ERROR.value,
                        "output": "",
                        "error": str(e),
                        "time": 0.0,
                        "memory": 0
                    }

        except Exception as e:
            return {
                "result": ExecutionResult.SYSTEM_ERROR.value,
                "output": "",
                "error": f"System error: {str(e)}",
                "time": 0.0,
                "memory": 0
            }


# Compatibility alias: callers written against the previous independent
# implementation import `Executor`.
Executor = MultiLanguageExecutor

_FAMILY_PREFIXES = {"Python 3": "python", "PyPy 3": "python", "PyPy 3-64": "python"}


def language_family(language: str) -> str | None:
    """'cpp' | 'java' | 'python' (CPython and PyPy 3) | None for unsupported
    (Python 2 / PyPy 2, or anything not in the language table)."""
    if language in _FAMILY_PREFIXES:
        return _FAMILY_PREFIXES[language]
    if language.startswith("C++"):
        return "cpp"
    if language.startswith("Java"):
        return "java"
    return None


_helper_executor = MultiLanguageExecutor()


def run_python_program(source: str, input_data: str = "", timeout: float = 10.0,
                       output_limit: int = 16 * 1024 * 1024) -> Dict[str, Any]:
    """Run this repo's own LLM-written helper code (validators, generators)
    on the repo's own Python 3.12 venv (see module docstring)."""
    return _helper_executor.execute("Helper Python 3", source, input_data,
                                    time_limit=timeout, memory_limit=2048, output_limit=output_limit)
