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
    "task2_do": "Raywithyou/TestCase-Eval-Task2-DO",
    "task1": "Raywithyou/TestCase-Eval-Task1",
    "task1_do": "Raywithyou/TestCase-Eval-Task1-DO",
    "submission_lite": "TestCase-Eval/submission_lite",
    "submission_all": "TestCase-Eval/submission_all",
    "problem": "TestCase-Eval/problem",
}

# Hugging Face dataset commits used for every number in the extension report
# (resolved 2026-09-26 via https://huggingface.co/api/datasets/<name>).
REVISIONS = {
    "task2": "ad6c3af216b088652b6f05d7df331b3858bf916d",
    "task2_do": "32433626e9704fa70fafc70f0234afb1c9cb73b7",
    "task1": "bd8b0e2e26e1e52225ca41537eaff592142cbc85",
    "task1_do": "294e91a4b1cbc3a93428e663afc112a017e1d5c2",
    "submission_lite": "96affb6b416002ed36bab881834e38a8c07b0647",
    "submission_all": "7de1bb5d7b3143418147a84d34594be162ef7821",
    "problem": "b5cc0cc4589f5e38c1b010c24a4c5f513009278e",
}

# Official code: https://github.com/FlowRays/TestCase-Eval
UPSTREAM_COMMIT = "45275c6f838566e6e148a9eca18edc00be08a305"

RAW_DIR = Path(__file__).resolve().parent / "data" / "raw"


def parquet_url(name: str) -> str:
    return (
        f"https://huggingface.co/datasets/{DATASETS[name]}/resolve/{REVISIONS[name]}"
        "/data/train-00000-of-00001.parquet"
    )


def fetch_parquet(name: str, raw_dir: Path = RAW_DIR) -> Path:
    """Download the pinned parquet shard for `name` once and return its path."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / f"{name}.parquet"
    if not path.exists():
        tmp = path.with_suffix(".part")
        urllib.request.urlretrieve(parquet_url(name), tmp)
        tmp.replace(path)
    return path


def load_rows(name: str, raw_dir: Path = RAW_DIR) -> list[dict]:
    import pyarrow.parquet as pq

    return pq.read_table(fetch_parquet(name, raw_dir)).to_pylist()


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
    parser.add_argument("--out", default="")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--pinned", action="store_true", help="fetch the pinned parquet revision into data/raw/")
    args = parser.parse_args()
    if args.pinned:
        print(fetch_parquet(args.dataset))
        return
    download_dataset(DATASETS[args.dataset], args.out, args.limit)


if __name__ == "__main__":
    main()
