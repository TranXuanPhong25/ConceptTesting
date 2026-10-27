"""Use the quality-evaluated Qwen selection flow for a new code query.

This is an explicit model-backed API. It requires the authorized endpoint in the
environment and never reads benchmark labels, references or evaluation witnesses.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from .client import Client
from .prompts import BY_ID, parse_retrieval, retrieval


def retrieve(code: str, *, out: Path, client: Client | None = None) -> dict:
    client = client or Client(out)
    client.preflight()
    messages = retrieval({"code": code})
    seed = int(hashlib.sha256(code.encode()).hexdigest()[:7], 16)
    response = client.complete(messages, stage="retrieve", max_tokens=1200, seed=seed)
    rows, error = parse_retrieval(response, code)
    results = []
    for rank, row in enumerate(rows, 1):
        results.append({"rank": rank, "concept": BY_ID[row["concept_id"]],
                        "instantiated": {k: row[k] for k in ("line", "where", "how", "what")},
                        "status": "unverified_fault_hypothesis"})
    return {"results": results, "schema_error": error, "model": "qwen3.5-27b-awq",
            "request_sha256": response["request_sha256"], "usage": response.get("usage", {}),
            "retrieval": "Qwen global-catalog selection plus concrete where/how/what; requires separate validation"}


if __name__ == "__main__":
    import argparse
    import json
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(retrieve(args.code.read_text(), out=args.out), indent=2, ensure_ascii=False))
