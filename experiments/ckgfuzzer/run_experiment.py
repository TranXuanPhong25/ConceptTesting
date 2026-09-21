#!/usr/bin/env python3
"""Compile and run the generated CKGFuzzer-style harness locally."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from generate_harness import choose_call_sequence, render_harness

ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures"
BUILD = ROOT / "build"


def run_variant(variant: str) -> dict[str, object]:
    graph = json.loads((ROOT / "graph.json").read_text())
    harness = BUILD / "ledger_harness.c"
    binary = BUILD / f"ledger_{variant}"
    BUILD.mkdir(exist_ok=True)
    harness.write_text(render_harness(graph, choose_call_sequence(graph)))
    fixture = FIXTURES / ("ledger.c" if variant == "original" else "ledger_mutant.c")
    compile_cmd = [
        "clang", "-std=c11", "-Wall", "-Wextra", "-Werror", "-I", str(FIXTURES),
        str(fixture), str(harness), "-o", str(binary),
    ]
    compiled = subprocess.run(compile_cmd, text=True, capture_output=True, check=False)
    if compiled.returncode:
        return {"variant": variant, "compiled": False, "returncode": compiled.returncode, "stderr": compiled.stderr}
    try:
        executed = subprocess.run([str(binary)], text=True, capture_output=True, timeout=3, check=False)
        return {
            "variant": variant,
            "compiled": True,
            "returncode": executed.returncode,
            "stdout": executed.stdout,
            "stderr": executed.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"variant": variant, "compiled": True, "timeout": True}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=("original", "mutant", "both"), default="both")
    args = parser.parse_args()
    variants = ("original", "mutant") if args.variant == "both" else (args.variant,)
    results = [run_variant(variant) for variant in variants]
    print(json.dumps(results, indent=2))

    correct = all(result.get("compiled") for result in results)
    if args.variant == "both":
        correct = correct and results[0].get("returncode") == 0 and results[1].get("returncode") != 0
    elif args.variant == "original":
        correct = correct and results[0].get("returncode") == 0
    else:
        correct = correct and results[0].get("returncode") != 0
    raise SystemExit(0 if correct else 1)


if __name__ == "__main__":
    main()
