"""Patched vendor copy of the official TestCase-Eval sandbox executor.

This is FlowRays/TestCase-Eval@45275c6's `sandbox.py` (see
vendor/upstream_sandbox.py for the exact, hash-pinned original), trimmed to
just the reusable execution classes (the paper's own `main()`/CLI/file-layout
code, which assumes their own experiment's data shape, is dropped -- it is
not a library entry point) and patched in exactly 3 places, each marked
inline with a `# PATCH` comment and diffable against vendor/upstream_sandbox.py:

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
   regex to find the class immediately preceding `main` -- this passes when
   that's the only class in the file, but still fails
   (`error: class Other is public, should be declared in a file named
   Other.java`) whenever the file also has an actual public class other than
   the one holding `main`, because Java requires the filename to match the
   public class, and renaming only the main-holding class leaves that
   requirement broken. Fixed properly instead: since every call already runs
   in its own fresh `tempfile.TemporaryDirectory()`, there is no collision to
   avoid renaming for in the first place. The submission is now compiled
   completely unmodified, under whatever filename Java actually requires
   (`_java_file_stem`), and the class that actually declares
   `public static void main` is found post-compile via `javap`
   (`_find_java_main_class`) and run directly -- verified against both the
   simple non-public-main case and the harder competing-public-class case
   above, plus a normal single-public-class submission, with no known
   remaining gap.

Everything else -- language table, other compile flags, time limit (3.0s x
per-language factor), memory limit (512MB via RLIMIT_AS / -Xmx for Java),
psutil RSS monitoring, and verdict mapping (-9/137 or allocation-failure text
-> memory_limit_exceeded, other non-zero -> runtime_error, timeout ->
time_limit_exceeded) -- is unchanged from upstream.

Status: not yet wired into generate.py/validator.py (which still use
sandbox.py's independent Executor); this file demonstrates that patching the
vendored original in place is both possible and preferable to an independent
reimplementation for auditability.
"""

import os
import re
import tempfile
import subprocess
import time
import threading
import psutil
from pathlib import Path
from typing import Dict, Any, Optional
from enum import Enum

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
    
    def __init__(self):
        self.languages = self._init_languages()
    
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
                execute_cmd="python3",
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
                execute_cmd="pypy3",
                execute_flags="-u",
                file_ext=".py",
                is_compiled=False,
                timeout_factor=2.0
            ),
            "PyPy 3-64": LanguageConfig(
                name="PyPy 3-64",
                compile_cmd="pypy3",
                compile_flags="-m py_compile",
                execute_cmd="pypy3",
                execute_flags="-u",
                file_ext=".py", 
                is_compiled=False,
                timeout_factor=2.0
            ),
  
            "C++14 (GCC 6-32)": LanguageConfig(
                name="C++14 (GCC 6-32)",
                compile_cmd="g++",
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
            )
        }
    
    def _java_file_stem(self, java_code: str) -> str:
        """Filename to compile the submission's OWN, unmodified source under.

        PATCH (vs vendor/upstream_sandbox.py): the original renamed every
        class to a random collision-free name via `_replace_java_class_name`,
        which is unfixable by a better regex: Java requires the *filename* to
        match the public top-level class, so renaming only the class that
        contains `main` breaks compilation the moment a file has main in a
        non-public class alongside an actual public class with a different
        name (`error: class Other is public, should be declared in a file
        named Other.java` -- reproduced with a two-class test file; a naive
        regex fix that only renames the main-holding class still fails this
        case). Since each call already runs in its own fresh
        `tempfile.TemporaryDirectory()`, there is no collision to avoid in
        the first place -- renaming was never necessary here. Compile the
        source completely unmodified, under the name Java actually requires.
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
    
    def execute(self, language: str, code: str, input_data: str = "", 
                time_limit: float = 3.0, memory_limit: int = 512) -> Dict[str, Any]:

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
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir_path = Path(tmpdir)
                
                if language.startswith("Java"):
                    file_stem = self._java_file_stem(code)
                    source_file = tmpdir_path / f"{file_stem}{lang_config.file_ext}"
                else:
                    source_file = tmpdir_path / f"main{lang_config.file_ext}"
                
                with open(source_file, 'w', encoding='utf-8') as f:
                    f.write(code)
                
                if lang_config.is_compiled and lang_config.compile_cmd:
                    if language.startswith("Java"):
                        compile_cmd = [lang_config.compile_cmd] + lang_config.compile_flags.split() + [str(source_file)]
                    elif language.startswith("C++"):
                        executable = tmpdir_path / "main"
                        compile_cmd = [lang_config.compile_cmd] + lang_config.compile_flags.split() + [str(source_file), "-o", str(executable)]
                    elif language.startswith("Python") or language.startswith("PyPy"):
                        compile_cmd = [lang_config.compile_cmd] + lang_config.compile_flags.split() + [str(source_file)]
                    
                    try:
                        compile_result = subprocess.run(
                            compile_cmd,
                            cwd=tmpdir,
                            capture_output=True,
                            text=True,
                            timeout=30
                        )
                        
                        if compile_result.returncode != 0:
                            return {
                                "result": ExecutionResult.COMPILATION_ERROR.value,
                                "output": "",
                                "error": compile_result.stderr,
                                "time": 0.0,
                                "memory": 0
                            }
                    except subprocess.TimeoutExpired:
                        return {
                            "result": ExecutionResult.COMPILATION_ERROR.value,
                            "output": "",
                            "error": "Compilation timeout",
                            "time": 0.0,
                            "memory": 0
                        }

                if language.startswith("Java"):
                    class_name = self._find_java_main_class(tmpdir_path, file_stem)
                    if class_name is None:
                        return {
                            "result": ExecutionResult.COMPILATION_ERROR.value,
                            "output": "",
                            "error": "no class declaring public static void main(String[]) found",
                            "time": 0.0,
                            "memory": 0
                        }
                    java_flags = lang_config.execute_flags.split()
                    java_flags.append(f"-Xmx{memory_limit}M")
                    execute_cmd = [lang_config.execute_cmd] + java_flags + [class_name]
                elif language.startswith("C++"):
                    execute_cmd = [str(executable)]
                elif language.startswith("Python") or language.startswith("PyPy"):
                    execute_cmd = [lang_config.execute_cmd] + lang_config.execute_flags.split() + [str(source_file)]

                try:
                    # PATCH (vs vendor/upstream_sandbox.py): the original used
                    # `preexec_fn=preexec_fn`, which forces fork(). This process
                    # also holds live gRPC channels to Vertex AI (LLM calls run
                    # interleaved with sandbox execution in the same worker
                    # threads -- see generate.py), and gRPC is not fork-safe:
                    # background gRPC threads vanish in the forked child while
                    # their mutexes stay locked, which can hang or crash (the
                    # same bug class was hit and fixed for real in
                    # trickcatcher_concept, commit 4b5cdde). `prlimit` (an
                    # external command, no fork) sets the same RLIMIT_AS instead.
                    if os.name == 'posix' and not language.startswith("Java") and memory_limit > 0:
                        memory_limit_bytes = memory_limit * 1024 * 1024
                        execute_cmd = ["prlimit", f"--as={memory_limit_bytes}", "--"] + execute_cmd

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
                                "memory": max_memory
                            }
                        elif (stderr and any(keyword in stderr.lower() for keyword in 
                                            ['bad_alloc', 'out of memory', 'memory allocation', 'cannot allocate'])) or \
                            (max_memory > memory_limit * 1024 * 0.9):
                            return {
                                "result": ExecutionResult.MEMORY_LIMIT_EXCEEDED.value,
                                "output": stdout,
                                "error": stderr,
                                "time": execution_time,
                                "memory": max_memory
                            }
                        else:
                            return {
                                "result": ExecutionResult.RUNTIME_ERROR.value,
                                "output": stdout,
                                "error": stderr,
                                "time": execution_time,
                                "memory": max_memory
                            }

                    return {
                        "result": ExecutionResult.SUCCESS_RUN.value,
                        "output": stdout,
                        "error": stderr,
                        "time": execution_time,
                        "memory": max_memory
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


