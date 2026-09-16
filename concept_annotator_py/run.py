#!/usr/bin/env python3
"""Annotate TestEval Python JSONL records with prompt-ready concepts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .annotator import annotate_record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in", dest="input_path", required=True, help="TestEval leetcode-py JSONL")
    parser.add_argument("--out", dest="output_path", required=True, help="Output annotated JSONL")
    parser.add_argument("--paths", default=None, help="Optional TestEval tgt_paths JSONL")
    parser.add_argument("--limit", type=int, default=0, help="Optional max rows")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print each JSON record")
    args = parser.parse_args()

    path_by_task = _load_paths(args.paths)
    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    n = 0
    with Path(args.input_path).open() as fi, output_path.open("w") as fo:
        for line in fi:
            if args.limit and n >= args.limit:
                break
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            annotated = annotate_record(record, path_by_task.get(record.get("task_num")))
            if args.pretty:
                fo.write(json.dumps(annotated, indent=2, sort_keys=True) + "\n")
            else:
                fo.write(json.dumps(annotated, sort_keys=True) + "\n")
            n += 1
    print("annotated %d TestEval item(s) -> %s" % (n, output_path))


def _load_paths(path: str | None) -> dict[int, dict]:
    if not path:
        return {}
    out: dict[int, dict] = {}
    with Path(path).open() as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            out[row["task_num"]] = row
    return out


if __name__ == "__main__":
    main()
