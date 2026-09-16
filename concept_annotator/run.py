#!/usr/bin/env python3
"""Annotate JSONL benchmark items with TEstEval-shaped concept targets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .annotator import annotate_item


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in", dest="input_path", required=True, help="Input JSONL file")
    parser.add_argument("--out", dest="output_path", required=True, help="Output JSONL file")
    parser.add_argument("--func-field", default=None, help="Function source field to annotate")
    parser.add_argument("--limit", type=int, default=0, help="Optional max rows")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print each JSON record")
    args = parser.parse_args()

    input_path = Path(args.input_path)
    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    n = 0
    with input_path.open() as fi, output_path.open("w") as fo:
        for line in fi:
            if args.limit and n >= args.limit:
                break
            line = line.strip()
            if not line:
                continue
            row = annotate_item(json.loads(line), args.func_field)
            if args.pretty:
                fo.write(json.dumps(row, indent=2, sort_keys=True) + "\n")
            else:
                fo.write(json.dumps(row, sort_keys=True) + "\n")
            n += 1
    print("annotated %d item(s) -> %s" % (n, output_path))


if __name__ == "__main__":
    main()
