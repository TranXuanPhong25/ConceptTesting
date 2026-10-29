"""Frozen four-source infrastructure smoke; no target execution or bug-truth scoring."""
from __future__ import annotations
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from .dense import Encoder
from .hybrid_engine import Retriever

HERE = Path(__file__).resolve().parent
SOURCES = {
    "distinct_cardinality": 'def measure(values: list):\n """Return the number of distinct values; duplicates are allowed."""\n return len(set(values))\n',
    "occurrence_cardinality": 'def measure(values: list):\n """Return the number of occurrences including repeated values."""\n return len(set(values))\n',
    "encoded_character_measurement": 'def measure(text: str):\n """Return the number of Unicode characters in the input string."""\n return len(text.encode("utf-8"))\n',
    "filtered_minimum": 'def choose(values: list):\n """Return the smallest positive value, or None if there are no positive values."""\n return min(x for x in values if x > 0)\n',
}


def sources():
    paths = list(HERE.glob("*.py")) + list((HERE / "data").glob("*"))
    paths += [HERE / "MODEL_MANIFEST.json", HERE / "PREREG_V7.md", HERE / "requirements-v7.txt"]
    paths += [HERE.parent / n for n in ("base.py", "ingest.py")]
    paths += [p for p in (HERE.parent / "data").glob("*") if p.is_file()]
    return {str(p.relative_to(HERE.parent)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(paths) if p.is_file()}


def run():
    out = HERE / "engineering_smoke_20261029"
    out.mkdir()  # Single-use; never overwrite or silently resume different source.
    frozen = {"files": sources(), "sources": SOURCES, "arms": ["A", "B", "C", "D"],
              "timestamp": datetime.now(timezone.utc).isoformat(),
              "kind": "authored_engineering_fixture_no_target_execution_no_efficacy_score"}
    (out / "FREEZE.json").write_text(json.dumps(frozen, indent=2) + "\n")
    started = time.monotonic()
    try:
        encoder = Encoder()
        r = Retriever(encoder=encoder)
        records = []
        try:
            for name, code in SOURCES.items():
                arms = {}
                for arm in frozen["arms"]:
                    arms[arm] = r.search(code=code, arm=arm)
                    print(name, arm, "completed", flush=True)
                deltas = {}
                for sparse, dense in (("A", "B"), ("C", "D")):
                    before = {c["concept_id"] for c in arms[sparse]["candidates"]}
                    after = {c["concept_id"] for c in arms[dense]["candidates"]}
                    deltas[dense+"-"+sparse] = {"added_candidates": sorted(after-before),
                                                 "removed_candidates": sorted(before-after)}
                records.append({"fixture": name, "arms": arms, "paired_shortlist_deltas": deltas})
        finally:
            r.close()
        if sources() != frozen["files"]:
            raise ValueError("Source changed during smoke")
        result = {"records": records, "seconds": time.monotonic()-started,
                  "encoder": {"identity": encoder.identity, "new_texts": encoder.calls,
                              "cached_texts": encoder.hits, "truncated_texts": encoder.truncated},
                  "source_integrity": "PASS", "efficacy": "unmeasured",
                  "limits": ["Four fixtures were authored for engineering, not mined bugs.",
                             "Ranks and support status do not prove semantic discrimination or utility."]}
        (out / "RESULTS.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({k:v for k,v in result.items() if k != "records"}, indent=2))
    except Exception as exc:
        (out / "BLOCKED.json").write_text(json.dumps({"error": type(exc).__name__, "reason": str(exc),
                                                     "seconds": time.monotonic()-started}, indent=2) + "\n")
        raise


if __name__ == "__main__":
    run()
