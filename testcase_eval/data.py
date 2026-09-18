#!/usr/bin/env python3
"""Download official TestCase-Eval datasets through the Hugging Face rows API."""

from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
from pathlib import Path


DATASETS = {
    "task2": "Raywithyou/TestCase-Eval-Task2",
    "submission_lite": "TestCase-Eval/submission_lite",
    "problem": "TestCase-Eval/problem",
}


def is_python3_language(language: str) -> bool:
    return language.startswith("Python 3") or language.startswith("PyPy 3")


def download_dataset(dataset: str, output: str, limit: int = 0, page_size: int = 100) -> int:
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from datasets import load_dataset

        rows = load_dataset(dataset, split="train")
        if limit:
            rows = rows.select(range(min(limit, len(rows))))
        with output_path.open("w") as handle:
            for row in rows:
                handle.write(json.dumps(dict(row), ensure_ascii=False) + "\n")
        print(f"downloaded {len(rows)} row(s) from {dataset} -> {output_path}")
        return len(rows)
    except ImportError:
        pass

    offset = 0
    written = 0
    with output_path.open("w") as handle:
        while True:
            length = min(page_size, limit - written) if limit else page_size
            if length <= 0:
                break
            params = urllib.parse.urlencode(
                {"dataset": dataset, "config": "default", "split": "train", "offset": offset, "length": length}
            )
            url = "https://datasets-server.huggingface.co/rows?" + params
            with urllib.request.urlopen(url, timeout=60) as response:
                payload = json.load(response)
            rows = [item["row"] for item in payload.get("rows", [])]
            if not rows:
                break
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                written += 1
            offset += len(rows)
            if len(rows) < length or (limit and written >= limit):
                break
    print(f"downloaded {written} row(s) from {dataset} -> {output_path}")
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=tuple(DATASETS), required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    download_dataset(DATASETS[args.dataset], args.out, args.limit)


if __name__ == "__main__":
    main()
