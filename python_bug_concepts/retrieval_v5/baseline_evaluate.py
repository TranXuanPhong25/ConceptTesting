"""Strict bug-mechanism retrieval scoring. Gold is never passed to the engine."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path

from . import corpus
from .engine import search

HERE = Path(__file__).resolve().parent
EVAL = HERE / "evaluation"


def check_gold_freeze() -> None:
    freeze = json.loads((EVAL / "GOLD_FREEZE.json").read_text())
    for relative, sha in freeze["files"].items():
        if hashlib.sha256((HERE / relative).read_bytes()).hexdigest() != sha:
            raise ValueError("Frozen ground truth/corpus changed: " + relative)
    provenance = json.loads((EVAL / "INPUTS.json").read_text())
    for relative, sha in provenance["files"].items():
        if hashlib.sha256((EVAL / relative).read_bytes()).hexdigest() != sha:
            raise ValueError("Baseline snapshot changed: " + relative)
    for name in ("concepts.json", "patterns.jsonl", "sources.json", "exclusions.json"):
        if (corpus.ROOT / "data" / name).read_bytes() != (EVAL / "baseline_snapshot" / name).read_bytes():
            raise ValueError("Original corpus no longer matches frozen lexical baseline: " + name)
    sites_freeze = json.loads((EVAL / "MECHANISM_SITES_FREEZE.json").read_text())
    if hashlib.sha256((EVAL / "mechanism_sites.json").read_bytes()).hexdigest() != sites_freeze["sha256"]:
        raise ValueError("Frozen bug mechanism site labels changed")


def source_manifest() -> dict:
    paths = [HERE / n for n in ("engine.py", "corpus.py", "evaluate.py", "grade_witnesses.py", "grader_worker.py")]
    paths += [corpus.ROOT / n for n in ("base.py", "ingest.py")]
    return {str(p.relative_to(corpus.ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def score(predictions: list[str], accepted: list[str]) -> dict:
    ranks = [i + 1 for i, key in enumerate(predictions[:3]) if key in accepted]
    rank = min(ranks) if ranks else None
    return {"hit_at_1": rank == 1, "hit_at_3": rank is not None, "rank": rank}


def metrics(rows: list[dict], system: str) -> dict:
    n = len(rows)
    result = {"tasks": n, "hit_at_1": sum(x["systems"][system]["hit_at_1"] for x in rows),
            "hit_at_3": sum(x["systems"][system]["hit_at_3"] for x in rows),
            "fraction_at_3": sum(x["systems"][system]["hit_at_3"] for x in rows) / n,
            "labeled_ceiling": sum(bool(x["accepted_concepts"]) for x in rows)}
    if system == "structural_v2":
        result["correct_family_and_first_site_at_3"] = sum(x["systems"][system]["first_site_hit_at_3"] for x in rows)
        result["correct_family_and_any3_sites_at_3"] = sum(x["systems"][system]["any_site_hit_at_3"] for x in rows)
    return result


def binding_score(hits: list[dict], accepted_sites: dict) -> dict:
    first, any_site = False, False
    for hit in hits[:3]:
        valid_lines = {site["line"] for site in accepted_sites.get(hit["concept"]["id"], [])}
        returned = hit.get("evidence", [])[:3]
        first |= bool(returned) and returned[0]["line"] in valid_lines
        any_site |= any(r["line"] in valid_lines for r in returned)
    return {"first_site_hit_at_3": first, "any_site_hit_at_3": any_site}


def run(split: str) -> dict:
    check_gold_freeze()
    if split == "audit":
        frozen = json.loads((EVAL / "ENGINE_FREEZE.json").read_text())
        if frozen["files"] != source_manifest() or frozen["corpus_sha256"] != corpus.digest():
            raise ValueError("Freeze the final implementation before audit scoring")
        if (EVAL / "audit.json").exists():
            raise ValueError("Audit results already exist; use the saved artifact rather than rerunning")
    spec = importlib.util.spec_from_file_location("python_bug_concepts._frozen_v1_base", EVAL / "baseline_snapshot/base.py")
    baseline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(baseline)
    inputs = json.loads((EVAL / "inputs.json").read_text())
    gold = json.loads((EVAL / "gold.json").read_text())["tasks"]
    site_gold = json.loads((EVAL / "mechanism_sites.json").read_text())["tasks"]
    # This supervised constant baseline is derived only from development labels.
    frequencies = Counter(c for r in inputs if r["split"] == "development" for c in gold[r["task_id"]]["concept_ids"])
    frequent3 = [c for c, _ in frequencies.most_common(3)]
    output = []
    for task in inputs:
        if task["split"] != split:
            continue
        # Retrieval receives the code string only. Gold joins happen afterwards.
        packets = {
            "original_bm25": baseline.search(code=task["code"], top_k=3),
            "extended_bm25": search(code=task["code"], top_k=3, mode="lexical"),
            "structural_v2": search(code=task["code"], top_k=3),
        }
        accepted = gold[task["task_id"]]["concept_ids"]
        systems = {}
        for name, packet in packets.items():
            predictions = [h["concept"]["id"] for h in packet["results"]]
            systems[name] = {"predictions": predictions, **score(predictions, accepted)}
            if name == "structural_v2":
                systems[name]["evidence"] = [{"id": h["concept"]["id"], "sites": h.get("evidence", [])} for h in packet["results"]]
                systems[name].update(binding_score(packet["results"], site_gold.get(task["task_id"], {})))
        systems["frequent3_development"] = {"predictions": frequent3, **score(frequent3, accepted)}
        output.append({"task_id": task["task_id"], "split": split, "accepted_concepts": accepted,
                       "gold_witness_ids": gold[task["task_id"]]["witness_ids"], "rationale": gold[task["task_id"]]["rationale"], "systems": systems})
    report = {"split": split, "metric": "strict bug-family hit@3 against manually attributed, contract-valid native witness labels",
              "engine_files": source_manifest(), "corpus_sha256": corpus.digest(),
              "gold_sha256": hashlib.sha256((EVAL / "gold.json").read_bytes()).hexdigest(),
              "constant_baseline_concepts": frequent3,
              "summary": {s: metrics(output, s) for s in ("original_bm25", "extended_bm25", "structural_v2", "frequent3_development")},
              "tasks": output}
    (EVAL / f"{split}.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", required=True, choices=["development", "audit"])
    args = parser.parse_args()
    print(json.dumps(run(args.split)["summary"], indent=2))
