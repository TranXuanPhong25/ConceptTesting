#!/usr/bin/env python3
"""A bounded, deterministic structured-mutation loop inspired by LLAMAFUZZ.

The module learns a field-level delta from local seed pairs.  It is deliberately
small: no model calls and no open-ended fuzzing campaign are involved.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixture"
SEED_PAIRS = HERE / "seed_pairs.json"
CONCEPT = HERE / "concept.json"


@dataclass(frozen=True)
class Packet:
    kind: str
    declared_len: int
    payload: str

    @classmethod
    def parse(cls, raw: str) -> "Packet":
        parts = raw.rstrip("\n").split("|", 2)
        if len(parts) != 3:
            raise ValueError("packet must have KIND|DECLARED_LEN|PAYLOAD shape")
        kind, length_text, payload = parts
        if not length_text.isdecimal():
            raise ValueError("DECLARED_LEN must be a non-negative decimal")
        return cls(kind=kind, declared_len=int(length_text), payload=payload)

    def render(self) -> str:
        return f"{self.kind}|{self.declared_len}|{self.payload}"

    def is_well_formed(self) -> bool:
        return self.kind == "MSG" and self.declared_len == len(self.payload)


def derive_delta(source: Packet, target: Packet) -> dict[str, Any]:
    """Return the semantic field changes observed in one mutation seed pair."""

    changes: dict[str, Any] = {}
    for field in ("kind", "declared_len", "payload"):
        old, new = getattr(source, field), getattr(target, field)
        if old != new:
            changes[field] = new
    return {"changes": changes, "preserve": ["declared_len == len(payload)"]}


def apply_delta(seed: Packet, delta: dict[str, Any]) -> Packet:
    """Apply a seed-pair delta, then repair declared_len as the concept requires."""

    changes = delta.get("changes", {})
    candidate = Packet(
        kind=str(changes.get("kind", seed.kind)),
        declared_len=int(changes.get("declared_len", seed.declared_len)),
        payload=str(changes.get("payload", seed.payload)),
    )
    if "declared_len == len(payload)" in delta.get("preserve", []):
        candidate = Packet(candidate.kind, len(candidate.payload), candidate.payload)
    return candidate


def synthesize_candidate(seed: Packet, pairs: list[dict[str, str]], concept: dict[str, Any]) -> Packet:
    """Choose a labeled seed pair and transfer its structured delta to ``seed``."""

    required_label = concept["required_label"]
    for pair in pairs:
        if pair.get("label") != required_label:
            continue
        source = Packet.parse(pair["source"])
        target = Packet.parse(pair["target"])
        delta = derive_delta(source, target)
        delta["preserve"] = list(concept.get("relations", []))
        candidate = apply_delta(seed, delta)
        if candidate.is_well_formed():
            return candidate
    raise ValueError(f"no well-formed seed pair has label {required_label!r}")


def compile_fixture(source_name: str, output_dir: Path) -> Path:
    clang = shutil.which("clang")
    if not clang:
        raise RuntimeError("clang is required to run the local C fixture")
    source = FIXTURE / source_name
    binary = output_dir / source_name.removesuffix(".c")
    subprocess.run([clang, "-std=c11", "-Wall", "-Wextra", "-Werror", str(source), "-o", str(binary)], check=True)
    return binary


def run_harness(binary: Path, packet: Packet) -> dict[str, Any]:
    completed = subprocess.run(
        [str(binary)], input=packet.render() + "\n", text=True, capture_output=True, timeout=2, check=False
    )
    return {"exit_code": completed.returncode, "outcome": completed.stdout.strip(), "stderr": completed.stderr.strip()}


def run_smoke() -> dict[str, Any]:
    pairs = json.loads(SEED_PAIRS.read_text())
    concept = json.loads(CONCEPT.read_text())
    seed = Packet.parse(concept["base_seed"])
    candidate = synthesize_candidate(seed, pairs, concept)

    with tempfile.TemporaryDirectory(prefix="llamafuzz-smoke-") as temp:
        build_dir = Path(temp)
        original = run_harness(compile_fixture("packet_original.c", build_dir), candidate)
        mutant = run_harness(compile_fixture("packet_mutant.c", build_dir), candidate)

    result = {
        "method": "seed-pair structured mutation",
        "campaign_budget": {"candidates": 1, "timeout_seconds": 2},
        "concept": concept,
        "candidate": candidate.render(),
        "well_formed": candidate.is_well_formed(),
        "original": original,
        "controlled_mutant": mutant,
        "guard_hit": original["outcome"] == "GUARD_HIT",
        "distinguishes_mutant": original["outcome"] != mutant["outcome"],
    }
    result["success"] = bool(result["well_formed"] and result["guard_hit"] and result["distinguishes_mutant"])
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "results" / "smoke.json")
    args = parser.parse_args()
    result = run_smoke()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["success"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
