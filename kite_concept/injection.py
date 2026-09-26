from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class InjectionPlan:
    mechanism_id: str
    before: str
    after: str
    anchor_start: int
    anchor_end: int
    expected_change: str
    trigger_recipe: str


@dataclass(frozen=True)
class GateResult:
    accepted: bool
    locality: bool
    syntax_compilation: bool
    repository_compatibility: bool
    behavioral_nontriviality: bool
    reason: str
    injected_source: str = ""


def apply_local_plan(method_source: str, plan: InjectionPlan) -> str:
    occurrences = [m for m in re.finditer(re.escape(plan.before), method_source)]
    eligible = [m for m in occurrences if m.start() >= plan.anchor_start and m.end() <= plan.anchor_end]
    if len(eligible) != 1:
        raise ValueError(f"anchor must identify exactly one before fragment; found {len(eligible)}")
    match = eligible[0]
    return method_source[: match.start()] + plan.after + method_source[match.end() :]


def validate_injection(
    method_source: str,
    plan: InjectionPlan,
    compile_check: Callable[[str], bool],
    compatibility_check: Callable[[str], bool],
    behavior_check: Callable[[str, str], bool],
) -> GateResult:
    try:
        injected = apply_local_plan(method_source, plan)
        locality = injected != method_source and len(injected) - len(method_source) == len(plan.after) - len(plan.before)
    except ValueError as exc:
        return GateResult(False, False, False, False, False, str(exc))
    syntax = compile_check(injected)
    compatible = syntax and compatibility_check(injected)
    nontrivial = compatible and behavior_check(method_source, injected)
    flags = (locality, syntax, compatible, nontrivial)
    labels = ("locality", "syntax/compilation", "repository compatibility", "behavioral non-triviality")
    reason = "accepted" if all(flags) else "failed " + labels[flags.index(False)]
    return GateResult(all(flags), *flags, reason, injected)


def javac_check(source_file: Path, java_home: Path, classpath: str = "") -> bool:
    command = [str(java_home / "bin" / "javac")]
    if classpath:
        command.extend(["-cp", classpath])
    command.append(str(source_file))
    return subprocess.run(command, cwd=source_file.parent, capture_output=True, check=False).returncode == 0


def promotion_gate(correct_passes: bool, current_killed: bool, previous_results: dict[str, bool]) -> bool:
    return correct_passes and current_killed and all(previous_results.values())

