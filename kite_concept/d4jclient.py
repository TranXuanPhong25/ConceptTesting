"""Thin wrapper around the ``defects4j`` CLI and its checked-out project repos.

Every function here shells out to the ``defects4j`` binary that must already be on
``PATH`` (source ``~/.local/kite/env.sh`` first, which also selects JDK 11). Checkouts
are cached under ``$KITE_HOME/work/<project>-<bug>/{fixed,buggy}`` and reused across
runs and across cooperating processes that share the same ``KITE_HOME``.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

BENCH_PROJECTS = ("Cli", "Compress", "Csv", "JacksonDatabind", "Jsoup")


def kite_home() -> Path:
    return Path(os.environ.get("KITE_HOME", str(Path.home() / ".local" / "kite")))


def work_dir(project: str, bug: int) -> Path:
    return kite_home() / "work" / f"{project}-{bug}"


def _run(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(args, text=True, capture_output=True, check=False, **kwargs)


def active_bugs(project: str) -> list[int]:
    result = _run(["defects4j", "bids", "-p", project])
    if result.returncode != 0:
        raise RuntimeError(f"defects4j bids -p {project} failed: {result.stderr}")
    return sorted(int(line) for line in result.stdout.splitlines() if line.strip())


_MODIFIED_CLASSES_CACHE: dict[str, dict[int, list[str]]] = {}


def modified_classes(project: str, bug: int) -> list[str]:
    cache = _MODIFIED_CLASSES_CACHE.get(project)
    if cache is None:
        result = _run(["defects4j", "query", "-p", project, "-q", "classes.modified"])
        if result.returncode != 0:
            raise RuntimeError(f"defects4j query classes.modified -p {project} failed: {result.stderr}")
        cache = {}
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            bug_str, rest = line.split(",", 1)
            classes = rest.strip().strip('"')
            cache[int(bug_str)] = [c for c in classes.split(";") if c]
        _MODIFIED_CLASSES_CACHE[project] = cache
    return cache.get(bug, [])


def trigger_tests(project: str, bug: int) -> list[str]:
    result = _run(["defects4j", "query", "-p", project, "-q", "tests.trigger"])
    if result.returncode != 0:
        return []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        bug_str, rest = line.split(",", 1)
        if int(bug_str) == bug:
            return [t for t in rest.strip().strip('"').split(";") if t]
    return []


def src_patch_path(project: str, bug: int) -> Path:
    return kite_home() / "defects4j" / "framework" / "projects" / project / "patches" / f"{bug}.src.patch"


def read_src_patch(project: str, bug: int) -> str:
    return src_patch_path(project, bug).read_text(encoding="utf-8", errors="replace")


@dataclass(frozen=True)
class Hunk:
    fixed_start: int
    lines: tuple[str, ...]  # each line keeps its leading +/-/' ' tag

    def changed_fixed_lines(self) -> list[int]:
        """Fixed-side line numbers touched by this hunk (additions and deletion anchors)."""
        changed: list[int] = []
        fixed_ln = self.fixed_start
        for raw in self.lines:
            if raw.startswith("\\"):
                continue
            tag = raw[:1]
            if tag == " ":
                fixed_ln += 1
            elif tag == "+":
                changed.append(fixed_ln)
                fixed_ln += 1
            elif tag == "-":
                changed.append(fixed_ln)
        return changed


@dataclass(frozen=True)
class FilePatch:
    path: str
    hunks: tuple[Hunk, ...]


def parse_unified_diff(diff: str) -> list[FilePatch]:
    """Parse a ``diff --git`` unified patch into per-file hunks (buggy -> fixed direction)."""
    files: list[FilePatch] = []
    current_path: str | None = None
    current_hunks: list[Hunk] = []
    lines_buffer: list[str] = []
    fixed_start = 0

    def flush_hunk():
        nonlocal lines_buffer, fixed_start
        if lines_buffer:
            current_hunks.append(Hunk(fixed_start, tuple(lines_buffer)))
            lines_buffer = []

    def flush_file():
        flush_hunk()
        if current_path is not None:
            files.append(FilePatch(current_path, tuple(current_hunks)))

    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            flush_file()
            current_path = line[len("+++ b/") :]
            current_hunks = []
        elif line.startswith("@@"):
            flush_hunk()
            # @@ -a,b +c,d @@
            rhs = line.split("+", 1)[1].split("@@")[0].strip()
            fixed_start = int(rhs.split(",")[0])
        elif current_path is not None and line[:1] in "+- \\":
            if line.startswith("+++") or line.startswith("---"):
                continue
            lines_buffer.append(line)
    flush_file()
    return [f for f in files if f.path.endswith(".java") and f.hunks]


def checkout(project: str, bug: int, version: str) -> Path:
    """``version`` is ``fixed`` or ``buggy``; reuses an existing checkout if present."""
    suffix = "f" if version == "fixed" else "b"
    target = work_dir(project, bug) / version
    if target.exists() and any(target.iterdir()):
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    result = _run(["defects4j", "checkout", "-p", project, "-v", f"{bug}{suffix}", "-w", str(target)])
    if result.returncode != 0:
        raise RuntimeError(f"defects4j checkout {project}-{bug}{suffix} failed: {result.stderr[-2000:]}")
    return target
