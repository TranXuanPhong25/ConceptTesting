"""Correct-program over-retrieval diagnostic, never part of query construction."""

import argparse
import json
import time
from pathlib import Path
from .engine import search
from .evaluate import HERE, BASE, fingerprint
from ..retrieval_v2.engine import search as baseline


def run(tag):
    out = HERE / "evaluation_v6" / tag
    path = out / "CANONICAL_CONTROLS.json"
    if path.exists():
        raise ValueError("Preserve prior control outcomes")
    frozen = json.loads((out / "FREEZE.json").read_text())
    if frozen["implementation"] != fingerprint():
        raise ValueError("Control evaluation must match iteration source")
    task_ids = {r["task_id"] for r in json.loads((BASE / "inputs.json").read_text())}
    references = {
        r["task_id"]: {k: r[k] for k in ["prompt", "canonical_solution"]}
        for r in map(
            json.loads,
            (Path.home() / ".cache/evalplus/HumanEvalPlus-v0.1.10.jsonl").read_text().splitlines(),
        )
        if r["task_id"] in task_ids
    }
    records = []
    for tid, ref in references.items():
        source = ref["prompt"] + ref["canonical_solution"]
        methods = {
            "v2": baseline(code=source, top_k=3),
            **{
                p: search(code=source, top_k=3, policy=p, include_facts=False)
                for p in ["coverage", "balanced", "precise"]
            },
        }
        systems = {
            name: [
                {
                    "concept_id": h["concept"]["id"],
                    "line": h["evidence"][0]["line"] if h["evidence"] else None,
                    "ranking": h.get("ranking"),
                }
                for h in packet["results"]
            ]
            for name, packet in methods.items()
        }
        records.append({"task_id": tid, "systems": systems})
    (out / "CANONICAL_RECORDS.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n"
    )
    summary = {
        name: {
            "tasks": len(records),
            "tasks_with_candidates": sum(bool(r["systems"][name]) for r in records),
            "returned_cards": sum(len(r["systems"][name]) for r in records),
            "tier_ge2_candidates": sum(
                ((h.get("ranking") or {}).get("semantic_support") or {}).get("tier", 0) >= 2
                for r in records
                for h in r["systems"][name]
            ),
        }
        for name in ["v2", "coverage", "balanced", "precise"]
    }
    result = {
        "summary": summary,
        "records": records,
        "source_role": "canonical implementation used as a standalone correct-program query, not supplied with buggy query",
        "reference_fields_used": ["prompt", "canonical_solution"],
        "hidden_tests_used": False,
        "put_executions": 0,
        "limits": [
            "Over-retrieval is not a bug-report false-positive rate: results are conditional risks, not proven bug assertions.",
            "Canonical implementations are trusted under benchmark contracts; public docs can omit private domain restrictions.",
            "Diagnostic on known cohort, not independent generalization.",
        ],
        "created": time.time(),
        "implementation": fingerprint(),
    }
    assert fingerprint() == frozen["implementation"]
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--tag", required=True)
    args = p.parse_args()
    run(args.tag)
