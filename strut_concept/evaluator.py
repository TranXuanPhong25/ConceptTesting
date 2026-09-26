"""Compile, execute, and obtain focal-function gcov metrics."""

from __future__ import annotations

import gzip
import json
import os
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from .benchmark import Subject


@dataclass
class Evaluation:
    status: str
    compile_returncode: int
    run_returncode: int | None
    line_covered: int
    line_total: int
    branch_covered: int
    branch_total: int
    error: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _run(command: list[str], cwd: Path, timeout: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=timeout, env={**os.environ, "LC_ALL": "C"})


def evaluate(subject: Subject, source: str, harness: str, directory: Path, timeout: float = 10.0) -> Evaluation:
    directory.mkdir(parents=True, exist_ok=True)
    source_path, harness_path = directory / "target.c", directory / "test.c"
    source_path.write_text(source)
    harness_path.write_text(harness)
    common = ["gcc", "-std=gnu11", "-O0", "-g", "--coverage", "-fno-builtin", "-D_DEFAULT_SOURCE", "-D_GNU_SOURCE", "-DPREFER_SIZE_OVER_SPEED"]
    try:
        target_compile = _run(common + ["-c", "target.c", "-o", "target.o"], directory, timeout)
        harness_compile = _run(common + ["-c", "test.c", "-o", "test.o"], directory, timeout)
        if target_compile.returncode or harness_compile.returncode:
            message = (target_compile.stderr + harness_compile.stderr)[-4000:]
            return Evaluation("compile_error", target_compile.returncode or harness_compile.returncode, None, 0, 0, 0, 0, message)
        link = _run(["gcc", "--coverage", "target.o", "test.o", "-o", "test"], directory, timeout)
        if link.returncode:
            return Evaluation("compile_error", link.returncode, None, 0, 0, 0, 0, link.stderr[-4000:])
        try:
            executed = _run(["./test"], directory, timeout)
            run_code = executed.returncode
            status = "passed" if run_code == 0 else "runtime_failure"
            error = (executed.stderr + executed.stdout)[-4000:]
        except subprocess.TimeoutExpired:
            run_code, status, error = 124, "timeout", "test execution timed out"
        coverage = _coverage(subject.name, directory, _function_region(source, subject.name))
        return Evaluation(status, 0, run_code, *coverage, error)
    except subprocess.TimeoutExpired as exc:
        return Evaluation("timeout", 124, None, 0, 0, 0, 0, str(exc))


def _function_region(source: str, function: str) -> tuple[int, int] | None:
    clean = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), source, flags=re.S)
    clean = re.sub(r"//[^\n]*", "", clean)
    pattern = re.compile(r"\b" + re.escape(function) + r"\s*\([^;{}]*\)\s*\{")
    match = pattern.search(clean)
    if not match:
        return None
    brace = clean.find("{", match.start())
    depth, end = 0, brace
    for end in range(brace, len(clean)):
        if clean[end] == "{":
            depth += 1
        elif clean[end] == "}":
            depth -= 1
            if depth == 0:
                break
    return clean.count("\n", 0, match.start()) + 1, clean.count("\n", 0, end) + 1


def _coverage(function: str, directory: Path, region: tuple[int, int] | None = None) -> tuple[int, int, int, int]:
    result = _run(["gcov", "-j", "-b", "-c", "target.o"], directory, 10.0)
    if result.returncode:
        return 0, 0, 0, 0
    archives = list(directory.glob("*.gcov.json.gz"))
    if not archives:
        return 0, 0, 0, 0
    with gzip.open(archives[0], "rt") as handle:
        payload = json.load(handle)
    files = payload.get("files", [])
    # GCC can attribute an inline/header declaration with the same symbol name;
    # prefer the prepared focal translation unit rather than returning header
    # coverage for e.g. strcmp.
    files = sorted(files, key=lambda item: not str(item.get("file", "")).endswith("target.c"))
    for file_info in files:
        is_target = str(file_info.get("file", "")).endswith("target.c")
        if is_target and region:
            start, end = region
            relevant = [line for line in file_info.get("lines", []) if start <= int(line["line_number"]) <= end]
            if relevant:
                executable = [line for line in relevant if "count" in line]
                line_covered = sum(int(line.get("count", 0)) > 0 for line in executable)
                branches = [branch for line in relevant for branch in line.get("branches", [])]
                branch_covered = sum(int(branch.get("count", 0)) > 0 for branch in branches)
                return line_covered, len(executable), branch_covered, len(branches)
        functions = [f for f in file_info.get("functions", []) if f.get("name") == function]
        if not functions:
            continue
        start = min(int(f["start_line"]) for f in functions)
        end = max(int(f["end_line"]) for f in functions)
        relevant = [line for line in file_info.get("lines", []) if start <= int(line["line_number"]) <= end]
        executable = [line for line in relevant if "count" in line]
        line_covered = sum(int(line.get("count", 0)) > 0 for line in executable)
        branches = [branch for line in relevant for branch in line.get("branches", [])]
        branch_covered = sum(int(branch.get("count", 0)) > 0 for branch in branches)
        return line_covered, len(executable), branch_covered, len(branches)
    return 0, 0, 0, 0
