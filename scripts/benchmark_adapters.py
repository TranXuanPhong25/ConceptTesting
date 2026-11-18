#!/usr/bin/env python3
"""Inspect pinned datasets without an LLM, tokenizer, compiler or native execution."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from final.src.benchmarks.datasets import load_mbpp, dataset_sha256, MBPP_PATH


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mbpp', type=Path)
    args = parser.parse_args(arguments)
    rows = load_mbpp(args.mbpp)
    result = {'mbpp':{'count':len(rows), 'sha256':dataset_sha256(args.mbpp or MBPP_PATH)}}
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
