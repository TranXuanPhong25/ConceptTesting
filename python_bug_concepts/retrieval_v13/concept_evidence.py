"""Conditional mechanism overlay; provenance validation does not prove applicability.

Only pinned documentation and curated cards are read. There is no target execution,
benchmark label/reference lookup, model call, or inferred expected output here.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

from ..ingest import ROOT

HERE = Path(__file__).resolve().parent
OVERLAY_PATH = HERE / "data" / "mechanism_evidence.json"
_RECORD_KEYS = {
    "concept_id", "family", "realizations", "related_concepts", "scope_note",
    "requirements", "effect", "consumer", "trigger", "exclusions",
    "benign_contrast", "citations", "evidence_status",
}


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Nonempty text required: {label}")
    return value


def _strings(value, label, *, allow_empty=False):
    if not isinstance(value, list) or (not value and not allow_empty):
        raise ValueError(f"Text list required: {label}")
    for item in value:
        _text(item, label)
    if len(value) != len(set(value)):
        raise ValueError(f"Duplicate text: {label}")


def _source_registry():
    """Resolve pattern IDs against independent pinned source manifests."""
    original = json.loads((ROOT / "data/sources.json").read_text())
    extension = json.loads((HERE / "data/extra_sources.json").read_text())
    inventories = []
    original_inventory = {}
    for source in original["sources"]:
        for item in source["files"]:
            original_inventory[item["path"]] = (item["sha256"], source["revision"])
    inventories.append((ROOT / "data/patterns.jsonl", original_inventory))
    inventories.append((HERE / "data/extra_patterns.jsonl", {
        item["path"]: (item["sha256"], extension["revision"])
        for item in extension["files"]
    }))
    result = {}
    for path, inventory in inventories:
        for line in path.read_text().splitlines():
            record = json.loads(line)
            if record["id"] in result:
                raise ValueError(f"Duplicate source pattern: {record['id']}")
            result[record["id"]] = (record, inventory)
    return result


def _resolve_citation(citation, registry, file_cache):
    if not isinstance(citation, dict) or set(citation) != {"pattern_id", "quote", "supports"}:
        raise ValueError("Citation requires exactly pattern_id, quote and supports")
    for key, value in citation.items():
        _text(value, f"citation.{key}")
    pid = citation["pattern_id"]
    if pid not in registry:
        raise ValueError(f"Unknown source pattern: {pid}")
    pattern, inventory = registry[pid]
    ref = pattern["provenance"]
    if inventory.get(ref["path"]) != (ref["sha256"], ref["revision"]):
        raise ValueError(f"Source manifest mismatch: {pid}")
    path = (ROOT / ref["path"]).resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise ValueError(f"Source outside corpus: {pid}")
    if path not in file_cache:
        data = path.read_bytes()
        file_cache[path] = (hashlib.sha256(data).hexdigest(), data.decode("utf-8").splitlines())
    actual_hash, lines = file_cache[path]
    if actual_hash != ref["sha256"]:
        raise ValueError(f"Source hash mismatch: {pid}")
    start, end = ref["start_line"], ref["end_line"]
    if type(start) is not int or type(end) is not int or not 1 <= start <= end <= len(lines):
        raise ValueError(f"Invalid source line span: {pid}")
    snippet = " ".join(" ".join(lines[start - 1:end]).split())
    if " ".join(citation["quote"].split()) not in snippet:
        raise ValueError(f"Quote absent from pinned line span: {pid}")
    return {**deepcopy(citation), "provenance": deepcopy(ref), "kind": pattern["kind"]}


def validate_overlay(payload):
    """Validate structure and local citations, returning records keyed by concept.

    Validation establishes source integrity and exact quoted text only. Every
    requirement is explicitly unbound: target contract, flow and domain evidence
    must be supplied elsewhere, and no condition is marked satisfied here.
    """
    if not isinstance(payload, dict) or set(payload) != {"schema_version", "evidence_scope", "records"}:
        raise ValueError("Invalid overlay envelope")
    if type(payload["schema_version"]) is not int or payload["schema_version"] != 1:
        raise ValueError("Unsupported overlay schema")
    _text(payload["evidence_scope"], "evidence_scope")
    if not isinstance(payload["records"], list) or not payload["records"]:
        raise ValueError("Overlay records must be a nonempty list")
    card_ids = set()
    for path in (ROOT / "data/concepts.json", HERE / "data/extra_concepts.json"):
        card_ids.update(card["id"] for card in json.loads(path.read_text()))
    registry, file_cache, records = _source_registry(), {}, {}
    for raw in payload["records"]:
        if not isinstance(raw, dict) or set(raw) != _RECORD_KEYS:
            raise ValueError("Invalid mechanism record fields")
        for key in ("concept_id", "family", "scope_note", "effect", "consumer", "trigger", "benign_contrast"):
            _text(raw[key], key)
        cid = raw["concept_id"]
        if cid not in card_ids or cid in records:
            raise ValueError(f"Unknown or duplicate concept: {cid}")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", raw["family"]):
            raise ValueError(f"Invalid family: {cid}")
        if raw["evidence_status"] != "curated_conditional_template":
            raise ValueError(f"Overlay cannot promote evidence status: {cid}")
        for key in ("realizations", "exclusions", "related_concepts"):
            _strings(raw[key], key, allow_empty=key == "related_concepts")
        if any(other not in card_ids or other == cid for other in raw["related_concepts"]):
            raise ValueError(f"Invalid related concept: {cid}")
        requirements = raw["requirements"]
        if not isinstance(requirements, list) or not requirements:
            raise ValueError(f"Missing requirements: {cid}")
        requirement_ids, roles = set(), set()
        for requirement in requirements:
            if not isinstance(requirement, dict) or set(requirement) != {"id", "role", "text", "required_evidence"}:
                raise ValueError(f"Invalid requirement fields: {cid}")
            for key, value in requirement.items():
                _text(value, f"requirement.{key}")
            if requirement["id"] in requirement_ids or requirement["role"] not in {"contract", "flow", "domain"}:
                raise ValueError(f"Duplicate requirement or unknown role: {cid}")
            requirement_ids.add(requirement["id"])
            roles.add(requirement["role"])
        if roles != {"contract", "flow", "domain"}:
            raise ValueError(f"Contract, flow and domain requirements are all needed: {cid}")
        if not isinstance(raw["citations"], list) or not raw["citations"]:
            raise ValueError(f"Missing citations: {cid}")
        result = deepcopy(raw)
        result["citations"] = [_resolve_citation(c, registry, file_cache) for c in raw["citations"]]
        for requirement in result["requirements"]:
            requirement["binding_status"] = "unknown_requires_target_evidence"
        result["validation"] = "schema_and_pinned_citations_only_not_target_applicability"
        records[cid] = result
    return records


def load_overlay(path=None):
    """Read and validate an overlay afresh; callers may reuse the returned mapping."""
    return validate_overlay(json.loads(Path(path or OVERLAY_PATH).read_text()))


def family_for(card_or_id, *, overlay=None):
    """Return a grouping key, not a claim that related cards are interchangeable."""
    cid = card_or_id["id"] if isinstance(card_or_id, dict) else card_or_id
    _text(cid, "concept ID")
    records = load_overlay() if overlay is None else overlay
    return records[cid]["family"] if cid in records else cid


def feature_views(card, revised=False, *, overlay=None):
    """Return positive contract/mechanism/trigger texts for lexical or dense search.

    Negative conditions and benign examples remain in the evidence overlay for
    separate applicability review. Similarity to these texts is not bug proof.
    Untouched cards have byte-identical views across original and revised arms.
    """
    original = {
        "contract": " ".join([*card["where"]["preconditions"], card["what"]["oracle_template"]]),
        "mechanism": " ".join([card["title"], card["where"]["summary"], card["how"]["mechanism"], card["what"]["observable_failure"]]),
        "trigger": card["how"]["trigger_template"],
    }
    if not revised:
        return original
    records = load_overlay() if overlay is None else overlay
    evidence = records.get(card["id"])
    if evidence is None:
        return original
    # These are conditional retrieval descriptions, never evaluated predicates.
    return {
        "contract": "Required target conditions: " + " ".join(
            r["text"] for r in evidence["requirements"] if r["role"] in {"contract", "domain"}
        ),
        "mechanism": " ".join([
            card["title"], *evidence["realizations"], evidence["effect"],
            "Affected consumer: " + evidence["consumer"],
            *(r["text"] for r in evidence["requirements"] if r["role"] == "flow"),
        ]),
        "trigger": evidence["trigger"],
    }


def digest():
    """Fingerprint the overlay, card inputs and provenance registries for caches."""
    digest_value = hashlib.sha256(b"v7-mechanism-evidence-1")
    for path in (
        Path(__file__), OVERLAY_PATH, ROOT / "data/concepts.json",
        HERE / "data/extra_concepts.json", ROOT / "data/patterns.jsonl",
        HERE / "data/extra_patterns.jsonl", ROOT / "data/sources.json",
        HERE / "data/extra_sources.json",
    ):
        digest_value.update(path.read_bytes())
    return digest_value.hexdigest()
