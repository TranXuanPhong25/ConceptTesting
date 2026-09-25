"""Deterministically permute concept cards within matching function signatures."""

from __future__ import annotations

import argparse
import ast
import json
from collections import defaultdict
from pathlib import Path


def _signature(source: str) -> tuple[str, ...]:
    functions = [node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)]
    args = functions[-1].args.args
    return tuple(ast.unparse(arg.annotation).split("[")[0] if arg.annotation else "?" for arg in args)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pred", required=True, help="Saved concept-arm generation JSONL")
    parser.add_argument("--out", required=True)
    parser.add_argument("--artifact", default="/tmp/TrickCatcher-upstream")
    args = parser.parse_args()
    rows = {row["task_num"]: row for row in (
        json.loads(line) for line in Path(args.pred).read_text().splitlines() if line.strip()
    )}
    groups: dict[tuple[str, ...], list[int]] = defaultdict(list)
    source_root = Path(args.artifact) / "Datasets" / "EvalPlus" / "PUTs"
    for task_num, row in rows.items():
        if row.get("plan"):
            source = (source_root / f"HumanEval_{task_num}" / "put0.py").read_text()
            groups[_signature(source)].append(task_num)
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output.open("w") as handle:
        for group in groups.values():
            group.sort()
            if len(group) < 2:
                continue
            for index, target in enumerate(group):
                donor = group[(index + 1) % len(group)]
                handle.write(json.dumps({
                    "task_num": target, "donor_task_num": donor, "plan": rows[donor]["plan"],
                }, ensure_ascii=False) + "\n")
                count += 1
    print(f"wrote {count} shuffled cards -> {output}")


if __name__ == "__main__":
    main()
