from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from .models import ConceptRecord, MechanismRecord, UnitStructure
from .structure import multiset_jaccard

BENCHMARK_PROJECTS = frozenset({"cli", "compress", "csv", "jacksondatabind", "jsoup"})


def build_knowledge_base(records: Iterable[dict], output: Path) -> dict[str, int]:
    """Validate, de-leak and persist already-normalized historical bug records."""
    output.parent.mkdir(parents=True, exist_ok=True)
    accepted = skipped_leakage = skipped_invalid = 0
    with output.open("w", encoding="utf-8") as handle:
        for row in records:
            project = str(row.get("source_project", "")).lower()
            if project in BENCHMARK_PROJECTS:
                skipped_leakage += 1
                continue
            required = ("id", "what", "where", "how", "expected_buggy_behavior", "expected_failure_signal")
            if not all(str(row.get(k, "")).strip() for k in required):
                skipped_invalid += 1
                continue
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            accepted += 1
    return {"accepted": accepted, "skipped_leakage": skipped_leakage, "skipped_invalid": skipped_invalid}


def _terms(text: str) -> Counter[str]:
    return Counter(t for t in re.findall(r"[a-z][a-z0-9_]+", text.lower()) if len(t) > 2)


def semantic_similarity(query: str, mechanism: MechanismRecord) -> float:
    a = _terms(query)
    b = _terms(" ".join((mechanism.what, mechanism.where, mechanism.how)))
    dot = sum(a[t] * b[t] for t in a.keys() & b.keys())
    denom = math.sqrt(sum(v * v for v in a.values()) * sum(v * v for v in b.values()))
    return dot / denom if denom else 0.0


def retrieve(
    mechanisms: Iterable[MechanismRecord], semantic_profile: str, structures: Iterable[UnitStructure], limit: int = 5
) -> list[tuple[MechanismRecord, dict[str, float]]]:
    queries = list(structures)
    scored = []
    for mechanism in mechanisms:
        semantic = semantic_similarity(semantic_profile, mechanism)
        structural = max(
            (
                1.0 if q.fingerprint == s.fingerprint else multiset_jaccard(q, s)
                for q in queries for s in mechanism.structures
                if q.coarse_key == s.coarse_key
            ),
            default=0.0,
        )
        fused = 0.55 * semantic + 0.45 * structural + (0.05 if semantic > 0 and structural > 0 else 0)
        scored.append((mechanism, {"semantic": semantic, "structural": structural, "fused": fused}))
    return sorted(scored, key=lambda item: (-item[1]["fused"], item[0].id))[:limit]


def concept_from_mechanism(mechanism: MechanismRecord, trigger_input_relation: str, expected_oracle: str) -> ConceptRecord:
    concept = ConceptRecord(
        mechanism_id=mechanism.id,
        violated_constraint=mechanism.what,
        applicability_condition=mechanism.where,
        trigger_input_relation=trigger_input_relation,
        expected_oracle=expected_oracle,
        provenance=mechanism.evidence_ids,
    )
    concept.validate()
    return concept

