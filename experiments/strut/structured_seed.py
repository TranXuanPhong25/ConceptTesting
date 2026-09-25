"""A small, deterministic STRUT-style structured seed prototype for C."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


FUNCTION_RE = re.compile(
    r"\bint\s+(?P<name>[A-Za-z_]\w*)\s*\((?P<params>[^)]*)\)\s*\{",
    re.MULTILINE,
)
COMPARISON_RE = re.compile(
    r"if\s*\(\s*(?P<left>[A-Za-z_]\w*)\s*(?P<op><=|>=|<|>)\s*(?P<right>[A-Za-z_]\w*)\s*\)"
)


def derive_seed(source: str, concept_hints: dict[str, Any]) -> dict[str, Any]:
    """Derive a compact test specification from C source plus static hints."""

    signature = FUNCTION_RE.search(source)
    if not signature:
        raise ValueError("expected one int-returning C function")
    parameters = [part.strip().split()[-1] for part in signature.group("params").split(",")]
    guards = [match.groupdict() for match in COMPARISON_RE.finditer(source)]
    cases = concept_hints.get("boundary_cases", [])
    if not cases:
        raise ValueError("concept_hints.boundary_cases is required")
    return {
        "schema": "strut-mvp.v1",
        "function": signature.group("name"),
        "parameters": parameters,
        "static_concepts": {
            "types": concept_hints.get("types", {}),
            "guards": guards,
            "branches": concept_hints.get("branches", []),
            "expected_oracle": concept_hints.get("expected_oracle", "integer return value"),
        },
        "cases": cases,
    }


def render_harness(seed: dict[str, Any]) -> str:
    """Render a self-contained assertion harness from the structured seed."""

    function = seed["function"]
    params = seed["parameters"]
    declaration = ", ".join(f"int {name}" for name in params)
    lines = ["#include <assert.h>", "", f"int {function}({declaration});", "", "int main(void) {"]
    for case in seed["cases"]:
        args = case["inputs"]
        if len(args) != len(params):
            raise ValueError("case input count does not match function parameters")
        lines.append(f"    assert({function}({', '.join(str(arg) for arg in args)}) == {case['expected']});")
    lines.extend(["    return 0;", "}", ""])
    return "\n".join(lines)


def write_artifacts(target: Path, hints: Path, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    seed = derive_seed(target.read_text(), json.loads(hints.read_text()))
    seed_path = output_dir / "seed.json"
    harness_path = output_dir / "generated_test.c"
    seed_path.write_text(json.dumps(seed, indent=2) + "\n")
    harness_path.write_text(render_harness(seed))
    return {"seed": seed_path, "harness": harness_path}
