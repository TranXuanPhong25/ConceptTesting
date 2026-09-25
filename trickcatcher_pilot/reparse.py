"""Post-hoc format sensitivity check applied identically to saved model outputs.

This is separate from the preregistered strict parser. It repairs only an
unambiguous extra/missing list wrapper inferred from the PUT signature.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path
from typing import Any


def _one_list_parameter(source: str) -> bool:
    functions = [node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)]
    if not functions or len(functions[-1].args.args) != 1:
        return False
    annotation = functions[-1].args.args[0].annotation
    if isinstance(annotation, ast.Subscript):
        annotation = annotation.value
    return isinstance(annotation, ast.Name) and annotation.id in {"List", "list"}


def parse_lenient(raw: str, arity: int, list_parameter: bool) -> list[list[Any]]:
    text = re.sub(r"```(?:python)?|```", "", raw, flags=re.IGNORECASE)
    parsed: list[list[Any]] = []
    seen: set[str] = set()
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("["):
            continue
        try:
            value = ast.literal_eval(line)
        except (SyntaxError, ValueError, TypeError, MemoryError, RecursionError):
            continue
        if not isinstance(value, list):
            continue
        if arity == 1 and list_parameter:
            normalized = value if len(value) == 1 and isinstance(value[0], list) else [value]
        elif len(value) == arity:
            normalized = value
        elif len(value) == 1 and isinstance(value[0], (list, tuple)) and len(value[0]) == arity:
            normalized = list(value[0])
        else:
            continue
        try:
            json.dumps(normalized)
        except (TypeError, ValueError, OverflowError):
            continue
        fingerprint = repr(normalized)
        if fingerprint not in seen:
            seen.add(fingerprint)
            parsed.append(normalized)
    return parsed[:10]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pred", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--artifact", default="/tmp/TrickCatcher-upstream")
    args = parser.parse_args()
    source_root = Path(args.artifact) / "Datasets" / "EvalPlus" / "PUTs"
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    with Path(args.pred).open() as source_rows, output.open("w") as destination:
        for line in source_rows:
            if not line.strip():
                continue
            row = json.loads(line)
            source = (source_root / f"HumanEval_{row['task_num']}" / "put0.py").read_text()
            original_count = len(row.get("inputs", []))
            row["inputs"] = parse_lenient(row.get("raw_response", ""), row["arity"], _one_list_parameter(source))
            row["parser"] = "lenient-wrapper-v1"
            row["strict_input_count"] = original_count
            destination.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(f"task={row['task_num']} arm={row['arm']} strict={original_count} lenient={len(row['inputs'])}", flush=True)


if __name__ == "__main__":
    main()
