#!/usr/bin/env python3
"""A bounded, local HGFuzzer-inspired directed fuzzing demonstration.

This deliberately does not implement HGFuzzer's LLM, static-analysis, or
coverage-guided scheduler. It makes the key experimental interface explicit:
a target-specific concept plan is turned into valid seeds, then mutations keep
the path predicates valid while aiming at a local target branch.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
from typing import Any


def load_plan(path: pathlib.Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def xor_checksum(data: bytes) -> int:
    value = 0
    for byte in data:
        value ^= byte
    return value


def seed_from_plan(plan: dict[str, Any]) -> bytes:
    """Create the smallest valid input on the target side of the length guard."""
    fmt = plan["input_format"]
    payload_length = 9  # nearest integer satisfying `declared_len > 8`
    prefix = fmt["header"].encode("ascii") + bytes([fmt["version"], payload_length])
    payload = b"CONCEPT!!"  # exactly nine bytes; content is otherwise unconstrained
    candidate = prefix + payload
    return candidate + bytes([xor_checksum(candidate)])


def satisfies_plan(candidate: bytes, plan: dict[str, Any]) -> bool:
    fmt = plan["input_format"]
    if len(candidate) < 5:
        return False
    if candidate[:2] != fmt["header"].encode("ascii") or candidate[2] != fmt["version"]:
        return False
    declared_len = candidate[fmt["length_offset"]]
    return (
        declared_len > 8
        and len(candidate) == declared_len + 5
        and candidate[-1] == xor_checksum(candidate[:-1])
    )


def mutate_toward_target(seed: bytes, plan: dict[str, Any], case_index: int) -> bytes:
    """Deterministically vary payload bytes while preserving all path predicates."""
    if not satisfies_plan(seed, plan):
        raise ValueError("seed must satisfy the concept plan before directed mutation")
    payload_start = plan["input_format"]["payload_offset"]
    payload_length = seed[plan["input_format"]["length_offset"]]
    out = bytearray(seed[:-1])
    position = payload_start + (case_index % payload_length)
    out[position] ^= ((case_index * 29) | 1) & 0x7F
    return bytes(out) + bytes([xor_checksum(out)])


def _compile(root: pathlib.Path, fixed: bool) -> pathlib.Path:
    compiler = shutil.which("clang")
    if not compiler:
        raise RuntimeError("clang is required for this local C fixture")
    build_dir = root / ".build"
    build_dir.mkdir(exist_ok=True)
    output = build_dir / ("packet_parser_fixed" if fixed else "packet_parser_vulnerable")
    command = [
        compiler,
        "-std=c11",
        "-O0",
        "-g",
        "-Wall",
        "-Wextra",
        "-fsanitize=address",
        str(root / "fixture" / "packet_parser.c"),
        "-o",
        str(output),
    ]
    if fixed:
        command.insert(-2, "-DFIXED")
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode:
        raise RuntimeError("fixture compilation failed:\n" + completed.stderr)
    return output


def _execute(binary: pathlib.Path, candidate: bytes, timeout_seconds: float) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            [str(binary)], input=candidate, capture_output=True, timeout=timeout_seconds, check=False
        )
    except subprocess.TimeoutExpired:
        return {"target_hit": False, "sanitizer_detected": False, "timed_out": True, "returncode": None}
    output = (completed.stdout + completed.stderr).decode("utf-8", errors="replace")
    return {
        "target_hit": "TARGET_HIT" in output,
        "sanitizer_detected": "AddressSanitizer" in output,
        "timed_out": False,
        "returncode": completed.returncode,
        "output": output,
    }


def _campaign(binary: pathlib.Path, plan: dict[str, Any], cases: int, timeout_seconds: float) -> dict[str, Any]:
    seed = seed_from_plan(plan)
    results = [_execute(binary, mutate_toward_target(seed, plan, index), timeout_seconds) for index in range(cases)]
    return {
        "cases": cases,
        "target_hit": any(result["target_hit"] for result in results),
        "sanitizer_detected": any(result["sanitizer_detected"] for result in results),
        "timeouts": sum(bool(result["timed_out"]) for result in results),
        "first_case": results[0],
    }


def run_smoke(root: pathlib.Path, cases: int = 4, timeout_seconds: float = 2.0) -> dict[str, Any]:
    """Run a bounded red/green local experiment against only the toy fixture."""
    if not 1 <= cases <= 64:
        raise ValueError("cases must be between 1 and 64")
    plan = load_plan(root / "concept_plan.json")
    vulnerable = _campaign(_compile(root, fixed=False), plan, cases, timeout_seconds)
    fixed = _campaign(_compile(root, fixed=True), plan, cases, timeout_seconds)
    return {"plan_schema": plan["schema"], "vulnerable": vulnerable, "fixed": fixed}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true", help="compile and run the bounded local red/green smoke")
    parser.add_argument("--cases", type=int, default=4, help="directed cases per binary (1-64; default: 4)")
    parser.add_argument("--timeout", type=float, default=2.0, help="per-case timeout seconds")
    args = parser.parse_args()
    if not args.smoke:
        parser.error("only --smoke is currently implemented")
    if not 1 <= args.cases <= 64:
        parser.error("--cases must be between 1 and 64")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    result = run_smoke(pathlib.Path(__file__).resolve().parent, args.cases, args.timeout)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
