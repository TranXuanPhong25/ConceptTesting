#!/usr/bin/env python3
"""Bounded local G2FUZZ-style experiment with a controlled C mutant."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from generator import Concept, mutate_valid, synthesize_seed


ROOT = Path(__file__).resolve().parent
FIXTURE = ROOT / "fixture_parser.c"


def compile_parser(output: Path, *, mutant: bool) -> None:
    compiler = shutil.which("clang") or shutil.which("cc")
    if compiler is None:
        raise RuntimeError("clang or cc is required")
    command = [compiler, "-std=c11", "-Wall", "-Wextra", "-O2", str(FIXTURE), "-o", str(output)]
    if mutant:
        command.insert(1, "-DCONTROLLED_MUTANT")
    subprocess.run(command, check=True, capture_output=True, text=True)


def run_binary(binary: Path, sample: Path) -> int:
    return subprocess.run([str(binary), str(sample)], check=False, timeout=2).returncode


def build_corpus(mutations: int) -> list[tuple[str, bytes]]:
    target = synthesize_seed(Concept(target_flag=True, require_target_prefix=True))
    counterexample = synthesize_seed(Concept(target_flag=False, require_target_prefix=True))
    neutral = synthesize_seed(Concept())
    generated = mutate_valid(target, count=mutations, seed=17)
    return [("target", target), ("counterexample", counterexample), ("neutral", neutral)] + [
        (f"mutated-{index}", value) for index, value in enumerate(generated)
    ]


def run(mutations: int) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="g2fuzz-") as directory:
        workdir = Path(directory)
        reference = workdir / "parser-ref"
        mutant = workdir / "parser-mutant"
        compile_parser(reference, mutant=False)
        compile_parser(mutant, mutant=True)
        rows = []
        for name, data in build_corpus(mutations):
            sample = workdir / f"{name}.g2fz"
            sample.write_bytes(data)
            ref_exit = run_binary(reference, sample)
            mutant_exit = run_binary(mutant, sample)
            rows.append({"name": name, "bytes": len(data), "reference_exit": ref_exit,
                         "mutant_exit": mutant_exit, "target_hit": ref_exit == 42,
                         "distinguishes_mutant": ref_exit != mutant_exit})
    return {
        "format": "G2FZ/v1",
        "mutations": mutations,
        "valid_inputs": len(rows),
        "target_hits": sum(row["target_hit"] for row in rows),
        "mutant_distinguished": sum(row["distinguishes_mutant"] for row in rows),
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mutations", type=int, default=16)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    if args.mutations < 0:
        parser.error("--mutations must be non-negative")
    result = run(args.mutations)
    rendered = json.dumps(result, indent=2)
    if args.json:
        args.json.write_text(rendered + "\n")
    print(rendered)


if __name__ == "__main__":
    main()
