#!/usr/bin/env python3
"""Generate and differentially execute the bounded STRUT MVP."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from structured_seed import write_artifacts


ROOT = Path(__file__).resolve().parent


def compile_and_run(implementation: Path, harness: Path, binary: Path) -> int:
    compile_result = subprocess.run(
        ["clang", "-std=c11", "-Wall", "-Wextra", "-Werror", str(implementation), str(harness), "-o", str(binary)],
        text=True,
        capture_output=True,
    )
    if compile_result.returncode:
        raise RuntimeError(f"compile failed for {implementation.name}: {compile_result.stderr}")
    return subprocess.run([str(binary)], text=True, capture_output=True).returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT / "out")
    args = parser.parse_args()
    paths = write_artifacts(ROOT / "fixture" / "target.c", ROOT / "fixture" / "concept_hints.json", args.output_dir)
    original = compile_and_run(ROOT / "fixture" / "target.c", paths["harness"], args.output_dir / "original_test")
    mutant = compile_and_run(ROOT / "fixture" / "mutant.c", paths["harness"], args.output_dir / "mutant_test")
    print(f"seed={paths['seed']}")
    print(f"original_exit={original}")
    print(f"mutant_exit={mutant}")
    if original != 0:
        print("FAIL: generated test does not pass on the original", file=sys.stderr)
        return 1
    if mutant == 0:
        print("FAIL: generated test did not distinguish the mutant", file=sys.stderr)
        return 1
    print("PASS: original green; boundary mutant red")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
