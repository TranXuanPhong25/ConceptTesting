"""Frozen original cards plus a separately sourced semantic extension."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ..base import enriched_cards, load_jsonl, template_slots, validate
from ..ingest import ROOT

HERE = Path(__file__).resolve().parent


def digest() -> str:
    h = hashlib.sha256(b"retrieval-v2-corpus-1")
    for p in [*(ROOT / "data" / n for n in ("concepts.json", "patterns.jsonl", "sources.json", "exclusions.json")),
              *(HERE / "data" / n for n in ("extra_concepts.json", "extra_patterns.jsonl", "extra_sources.json"))]:
        h.update(p.read_bytes())
    return h.hexdigest()


def cards() -> list[dict]:
    result = enriched_cards()
    patterns = {p["id"]: p for p in load_jsonl(ROOT / "data/patterns.jsonl") + load_jsonl(HERE / "data/extra_patterns.jsonl")}
    for card in json.loads((HERE / "data/extra_concepts.json").read_text()):
        card["sources"] = [{"pattern_id": ref, "rule_code": patterns[ref].get("rule_code"),
                            "kind": patterns[ref]["kind"], "status": patterns[ref]["status"],
                            **patterns[ref]["provenance"]} for ref in card["pattern_ids"]]
        result.append(card)
    return result


def verify() -> dict:
    original = validate()
    manifest = json.loads((HERE / "data/extra_sources.json").read_text())
    inventory = {r["path"]: r["sha256"] for r in manifest["files"]}
    for relative, sha in inventory.items():
        p = (ROOT / relative).resolve()
        if not p.is_relative_to(ROOT) or hashlib.sha256(p.read_bytes()).hexdigest() != sha:
            raise ValueError(f"Extension source mismatch: {relative}")
    extra_patterns = load_jsonl(HERE / "data/extra_patterns.jsonl")
    if len({p["id"] for p in extra_patterns}) != len(extra_patterns):
        raise ValueError("Duplicate extension pattern")
    for p in extra_patterns:
        ref = p["provenance"]
        if inventory.get(ref["path"]) != ref["sha256"] or ref["revision"] != manifest["revision"]:
            raise ValueError(f"Invalid extension provenance: {p['id']}")
        if not 1 <= ref["start_line"] <= ref["end_line"] <= len((ROOT / ref["path"]).read_text().splitlines()):
            raise ValueError(f"Invalid extension line span: {p['id']}")
    all_cards = cards()
    if len({c["id"] for c in all_cards}) != len(all_cards):
        raise ValueError("Duplicate concept ID")
    for card in all_cards:
        if template_slots(card) != card["required_bindings"] or not card["sources"]:
            raise ValueError(f"Invalid card template/evidence: {card['id']}")
    return {"original_cards": original["concepts"], "extended_cards": len(all_cards),
            "new_semantic_cards": len(all_cards) - original["concepts"], "extra_source_sections": len(extra_patterns),
            "corpus_sha256": digest()}
