"""Judging: validator, checker, and CodeHacker's three hack conditions.

A *successful hack* (CodeHacker Sec. 3.1) requires
  1. Validity -- the input passes the (refined) validator;
  2. Oracle confirmation -- the standard solution is AC on it;
  3. Target failure -- the target submission is not AC.

``confirm`` adds an AnyPoC-style independent re-execution: recompile both
programs in a fresh workspace, re-run, re-check, and ask independent correct
submissions (CodeContests+) whether the reference answer is trustworthy.
"""

from __future__ import annotations

import hashlib
import shutil
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from codehacker_concept.sandbox import CompileResult, RunResult, compile_cpp, run_binary

CHECKER_TL_MS = 10000
VALIDATOR_TL_MS = 10000


@dataclass
class Verdict:
    valid: bool
    oracle_ok: bool
    target_verdict: str  # AC | WA | RE | TLE | MLE | OLE | INVALID | ORACLE_FAIL | CE | JUDGE_ERROR
    detail: str = ""
    validator_message: str = ""
    std_cpu_ms: int = 0
    target_cpu_ms: int = 0
    target_output_head: str = ""
    expected_output_head: str = ""

    @property
    def hacked(self) -> bool:
        return self.valid and self.oracle_ok and self.target_verdict in {"WA", "RE", "TLE", "MLE", "OLE"}

    def to_json(self) -> dict[str, Any]:
        data = asdict(self)
        data["hacked"] = self.hacked
        return data


def checker_verdict(checker_bin: Path, stdin: str, output: str, answer: str) -> tuple[str, str]:
    """Run a testlib checker: ``checker <in> <out> <ans>``. Returns (AC|WA|FAIL, message)."""
    with tempfile.TemporaryDirectory(prefix="chk_") as tmp:
        paths = []
        for name, content in (("in", stdin), ("out", output), ("ans", answer)):
            path = Path(tmp) / name
            path.write_text(content)
            paths.append(str(path))
        result = run_binary(checker_bin, "", CHECKER_TL_MS, 1024, args=paths, cwd=tmp)
    code = result.exit_code
    message = (result.stderr or result.stdout)[:500]
    if result.status == "TLE":
        return "FAIL", "checker timeout"
    if code == 0:
        return "AC", message
    if code in (1, 2):
        return "WA", message
    if code == 7:  # points: treat full points only as AC
        return ("AC" if "100" in message else "WA"), message
    return "FAIL", message


@dataclass
class ProblemJudge:
    """Judge for one problem. ``validators`` must all accept for validity."""

    validator_sources: list[str]
    checker_source: str
    std_source: str
    time_limit_ms: int
    memory_limit_mb: int
    extra_correct_sources: list[str] = field(default_factory=list)
    _cache: dict[str, Any] = field(default_factory=dict, repr=False)

    def _bin(self, source: str) -> CompileResult:
        key = hashlib.sha1(source.encode()).hexdigest()
        if key not in self._cache:
            self._cache[key] = compile_cpp(source)
        return self._cache[key]

    def validate(self, stdin: str) -> tuple[bool, str]:
        for index, source in enumerate(self.validator_sources):
            compiled = self._bin(source)
            if not compiled.ok or compiled.binary is None:
                return False, f"validator[{index}] compile error"
            result = run_binary(compiled.binary, stdin, VALIDATOR_TL_MS, 2048)
            if result.status != "OK":
                message = (result.stderr or result.stdout).strip()[:400]
                return False, f"validator[{index}]: {message or result.status}"
        return True, ""

    def std_output(self, stdin: str) -> tuple[RunResult | None, str]:
        compiled = self._bin(self.std_source)
        if not compiled.ok or compiled.binary is None:
            return None, "std compile error"
        return run_binary(compiled.binary, stdin, self.time_limit_ms, self.memory_limit_mb), ""

    def check(self, stdin: str, output: str, answer: str) -> tuple[str, str]:
        compiled = self._bin(self.checker_source)
        if not compiled.ok or compiled.binary is None:
            return "FAIL", "checker compile error"
        return checker_verdict(compiled.binary, stdin, output, answer)

    def evaluate(self, stdin: str, target_source: str, skip_validation: bool = False) -> Verdict:
        if not skip_validation:
            ok, message = self.validate(stdin)
            if not ok:
                return Verdict(False, False, "INVALID", "validator rejected input", validator_message=message)
        std, error = self.std_output(stdin)
        if std is None:
            return Verdict(True, False, "JUDGE_ERROR", error)
        if std.status != "OK":
            return Verdict(True, False, "ORACLE_FAIL", f"std {std.status}", std_cpu_ms=std.cpu_ms)
        verdict, message = self.check(stdin, std.stdout, std.stdout)
        if verdict != "AC":
            return Verdict(True, False, "ORACLE_FAIL", f"checker rejects std: {message}", std_cpu_ms=std.cpu_ms)
        compiled = self._bin(target_source)
        if not compiled.ok or compiled.binary is None:
            return Verdict(True, True, "CE", compiled.error[:300], std_cpu_ms=std.cpu_ms)
        target = run_binary(compiled.binary, stdin, self.time_limit_ms, self.memory_limit_mb)
        head = target.stdout[:300]
        expected = std.stdout[:300]
        if target.status != "OK":
            return Verdict(True, True, target.status, f"target {target.status} exit={target.exit_code}",
                           std_cpu_ms=std.cpu_ms, target_cpu_ms=target.cpu_ms,
                           target_output_head=head, expected_output_head=expected)
        verdict, message = self.check(stdin, target.stdout, std.stdout)
        if verdict == "FAIL":
            return Verdict(True, True, "JUDGE_ERROR", f"checker failed: {message}", std_cpu_ms=std.cpu_ms,
                           target_cpu_ms=target.cpu_ms)
        return Verdict(True, True, verdict, message[:300], std_cpu_ms=std.cpu_ms, target_cpu_ms=target.cpu_ms,
                       target_output_head=head, expected_output_head=expected)

    # ------------------------------------------------------------ AnyPoC-style

    def confirm(self, stdin: str, target_source: str, max_correct: int = 5) -> dict[str, Any]:
        """Independent re-execution in a fresh workspace + correct-submission consensus."""
        report: dict[str, Any] = {"reexec": None, "consensus_pass": 0, "consensus_total": 0}
        with tempfile.TemporaryDirectory(prefix="chconfirm_") as tmp:
            fresh = _FreshCompiler(Path(tmp))
            judge = ProblemJudge(
                [fresh.salted(v) for v in self.validator_sources],
                fresh.salted(self.checker_source),
                fresh.salted(self.std_source),
                self.time_limit_ms,
                self.memory_limit_mb,
            )
            second = judge.evaluate(stdin, fresh.salted(target_source))
            report["reexec"] = second.to_json()
            if second.hacked and self.extra_correct_sources:
                std, _ = judge.std_output(stdin)
                answer = std.stdout if std else ""
                for source in self.extra_correct_sources[:max_correct]:
                    compiled = compile_cpp(source)
                    if not compiled.ok or compiled.binary is None:
                        continue
                    run = run_binary(compiled.binary, stdin, self.time_limit_ms, self.memory_limit_mb)
                    report["consensus_total"] += 1
                    if run.status == "OK" and judge.check(stdin, run.stdout, answer)[0] == "AC":
                        report["consensus_pass"] += 1
            fresh.cleanup()
        total = report["consensus_total"]
        report["consensus_ok"] = total == 0 or report["consensus_pass"] * 2 > total
        report["confirmed"] = bool(report["reexec"] and report["reexec"]["hacked"] and report["consensus_ok"])
        return report


class _FreshCompiler:
    """Forces a fresh compile by salting sources with a unique comment."""

    def __init__(self, root: Path):
        self.root = root
        self.salt = hashlib.sha1(str(root).encode()).hexdigest()[:10]
        self.sources: list[str] = []

    def salted(self, source: str) -> str:
        salted = source + f"\n// confirm-salt {self.salt}\n"
        self.sources.append(salted)
        return salted

    def cleanup(self) -> None:
        # salted binaries are single-use; drop them from the compile cache
        from codehacker_concept.sandbox import bin_dir, compile_key

        for source in self.sources:
            key = compile_key(source)
            for suffix in (".bin", ".err"):
                path = bin_dir() / f"{key}{suffix}"
                if path.exists():
                    path.unlink()
        shutil.rmtree(self.root, ignore_errors=True)
