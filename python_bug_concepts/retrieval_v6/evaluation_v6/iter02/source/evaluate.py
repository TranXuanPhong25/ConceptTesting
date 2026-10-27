"""Append-only development iterations; immutable labels enter only after retrieval."""

from __future__ import annotations
import argparse
import hashlib
import json
import time
from pathlib import Path
from .engine import search
from ..retrieval_v2.evaluate import binding_score, check_gold_freeze, score

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "retrieval_v2/evaluation"
FILES = [
    "engine.py",
    "semantic.py",
    "facts.py",
    "applicability.py",
    "corpus.py",
    "baseline_engine.py",
    "requirements.txt",
    "semantic_tests.py",
    "scoped_tests.py",
    "evaluate.py",
]


def fingerprint():
    return {n: hashlib.sha256((HERE / n).read_bytes()).hexdigest() for n in FILES}


def run(name):
    check_gold_freeze()
    out = HERE / "evaluation_v6" / name
    if out.exists():
        raise ValueError("Iteration exists; never overwrite prior outcomes")
    out.mkdir(parents=True)
    snapshot = out / "source"
    snapshot.mkdir()
    for n in FILES:
        (snapshot / n).write_bytes((HERE / n).read_bytes())
    frozen = {
        "implementation": fingerprint(),
        "inputs": {
            n: hashlib.sha256((BASE / n).read_bytes()).hexdigest()
            for n in ["inputs.json", "gold.json", "mechanism_sites.json"]
        },
        "frozen_at": time.time(),
        "kind": "development_iteration_user_authorized; no independent holdout",
    }
    (out / "FREEZE.json").write_text(json.dumps(frozen, indent=2) + "\n")
    tasks = json.loads((BASE / "inputs.json").read_text())
    packets = {
        policy: {
            t["task_id"]: search(code=t["code"], top_k=3, include_facts=False, policy=policy)
            for t in tasks
        }
        for policy in ["coverage", "precise"]
    }
    gold = json.loads((BASE / "gold.json").read_text())["tasks"]
    sites = json.loads((BASE / "mechanism_sites.json").read_text())["tasks"]
    old = {
        r["task_id"]: r
        for s in ["development", "audit"]
        for r in json.loads((BASE / f"{s}.json").read_text())["tasks"]
    }
    records = []
    for task in tasks:
        tid = task["task_id"]
        accepted = gold[tid]["concept_ids"]
        systems = {}
        for policy in packets:
            packet = packets[policy][tid]
            hits = packet["results"]
            ids = [h["concept"]["id"] for h in hits]
            systems[policy] = {
                **score(ids, accepted),
                **binding_score(hits, sites.get(tid, {})),
                "returned": len(hits),
                "matching_cards": sum(cid in accepted for cid in ids),
                "warning": packet["warning"],
                "selected": [
                    {
                        "concept_id": h["concept"]["id"],
                        "line": h["evidence"][0]["line"] if h["evidence"] else None,
                        "label_match": h["concept"]["id"] in accepted,
                        "ranking": h.get("ranking"),
                        "instantiated": h.get("instantiated"),
                        "evidence": h["evidence"],
                    }
                    for h in hits
                ],
                "excluded_bindings": packet.get("excluded_bindings", []),
            }
        records.append(
            {
                "task_id": tid,
                "split": task["split"],
                "labeled": bool(accepted),
                "baseline": old[tid]["systems"]["structural_v2"],
                "systems": systems,
            }
        )

    def summarize(rows, policy):
        vals = [r["systems"][policy] for r in rows]
        n = len(vals)
        returned = sum(r["returned"] for r in vals)
        return {
            "tasks": n,
            "family_hit_at_1": sum(r["hit_at_1"] for r in vals),
            "family_hit_at_3": sum(r["hit_at_3"] for r in vals),
            "first_site_hit_at_3": sum(r["first_site_hit_at_3"] for r in vals),
            "any3_sites_hit_at_3": sum(r["any_site_hit_at_3"] for r in vals),
            "returned_cards": returned,
            "frozen_label_matches": sum(r["matching_cards"] for r in vals),
            "frozen_label_match_rate": sum(r["matching_cards"] for r in vals) / returned
            if returned
            else None,
            "fallbacks": sum(bool(r["warning"]) for r in vals),
            "site_wins": [
                r["task_id"]
                for r in rows
                if r["systems"][policy]["first_site_hit_at_3"]
                and not r["baseline"]["first_site_hit_at_3"]
            ],
            "site_losses": [
                r["task_id"]
                for r in rows
                if not r["systems"][policy]["first_site_hit_at_3"]
                and r["baseline"]["first_site_hit_at_3"]
            ],
            "family_losses": [
                r["task_id"]
                for r in rows
                if not r["systems"][policy]["hit_at_3"] and r["baseline"]["hit_at_3"]
            ],
        }

    result = {
        "summary": {p: summarize(records, p) for p in packets},
        "splits": {
            s: {p: summarize([r for r in records if r["split"] == s], p) for p in packets}
            for s in ["development", "audit"]
        },
        "records": records,
        "freeze": frozen,
        "limits": [
            "Old labels incomplete, single-author; unmatched is not verified incorrect.",
            "Development-adapted iteration, never new heldout.",
            "No target execution, oracle or gold in retrieval. Static support is not bug proof.",
        ],
    }
    assert fingerprint() == frozen["implementation"]
    (out / "RESULTS.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result["summary"], indent=2))
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--name", required=True)
    args = p.parse_args()
    run(args.name)
