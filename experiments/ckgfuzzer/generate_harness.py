#!/usr/bin/env python3
"""Generate a state-valid C harness from a small API knowledge graph."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def choose_call_sequence(graph: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate the graph-provided path against API state preconditions."""

    api_by_name = {api["name"]: api for api in graph["apis"]}
    state: set[str] = set()
    sequence: list[dict[str, Any]] = []
    for step in graph["target"]["sequence"]:
        api_name = step["api"]
        api = api_by_name.get(api_name)
        if api is None:
            raise ValueError(f"graph refers to unknown API: {api_name}")
        missing = set(api.get("requires", [])) - state
        if missing:
            raise ValueError(f"{api_name} requires unavailable state: {sorted(missing)}")
        sequence.append({"api": api_name, "arguments": list(step.get("arguments", []))})
        state.update(api.get("establishes", []))
        state.difference_update(api.get("clears", []))
    if not sequence or sequence[-1]["api"] != graph["target"]["sink"]:
        raise ValueError("target sequence must end at the declared sink")
    return sequence


def render_harness(graph: dict[str, Any], sequence: list[dict[str, Any]]) -> str:
    """Render a contract-level harness without source or mutant knowledge."""

    expected = graph["target"]["expected"]
    lines = [
        "#include <assert.h>",
        "#include \"ledger.h\"",
        "",
        "int main(void) {",
        "    Ledger *ledger = ledger_create();",
        "    assert(ledger != 0);",
    ]
    for step in sequence[1:]:
        call = f"{step['api']}(ledger"
        if step["arguments"]:
            call += ", " + ", ".join(str(argument) for argument in step["arguments"])
        call += ")"
        if step["api"] in expected:
            lines.append(f"    assert({call} == {expected[step['api']]});")
        else:
            lines.append(f"    (void){call};")
    lines.extend(["    ledger_destroy(ledger);", "    return 0;", "}", ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", type=Path, default=Path(__file__).with_name("graph.json"))
    parser.add_argument("--out", type=Path, default=Path("build/harness.c"))
    args = parser.parse_args()

    graph = json.loads(args.graph.read_text())
    source = render_harness(graph, choose_call_sequence(graph))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(source)
    print(args.out)


if __name__ == "__main__":
    main()
