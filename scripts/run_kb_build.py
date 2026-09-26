#!/usr/bin/env python3
"""Run bounded, real, LLM-reviewed mechanism extraction over cached Bears diffs.

Resume-safe: writes each accepted/error row to --out as it completes and skips ids already present
on restart. Concurrency is capped (default 2) to be conservative with shared Vertex quota.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kite_concept.kb_builder import bears_candidates, extract_mechanism
from kite_concept.llm import configured_llm, response_text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bears", default=str(Path.home() / ".local/kite/kbsrc/bears/bears-bugs.json"))
    parser.add_argument("--out", required=True)
    parser.add_argument("--limit", type=int, default=120)
    parser.add_argument("--concurrency", type=int, default=2)
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done_ids: set[str] = set()
    if out_path.exists():
        for line in out_path.read_text().splitlines():
            if line.strip():
                row = json.loads(line)
                done_ids.add(row.get("_mechanism_id", ""))

    candidates = list(bears_candidates(Path(args.bears)))[: args.limit]
    llm = configured_llm(temperature=0.1, timeout=90, max_tokens=1024)

    def work(index: int, candidate: dict) -> tuple[str, dict]:
        mid = f"bears-{candidate['bug_id']}-{index}"
        row = extract_mechanism(llm, response_text, candidate, mid)
        return mid, (row or {"error": "empty_response"})

    todo = [(i, c) for i, c in enumerate(candidates) if f"bears-{c['bug_id']}-{i}" not in done_ids]
    print(f"total candidates={len(candidates)} already_done={len(done_ids)} todo={len(todo)}", flush=True)

    accepted = errors = 0
    with out_path.open("a", encoding="utf-8") as handle, ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = {pool.submit(work, i, c): (i, c) for i, c in todo}
        for future in as_completed(futures):
            mid, row = future.result()
            row["_mechanism_id"] = mid
            handle.write(json.dumps(row, sort_keys=True) + "\n")
            handle.flush()
            if "error" in row:
                errors += 1
            else:
                accepted += 1
            print(f"{mid} {'ERROR:' + row['error'] if 'error' in row else 'OK'}", flush=True)

    print(f"done accepted={accepted} errors={errors}", flush=True)


if __name__ == "__main__":
    main()
