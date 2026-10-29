"""Unblind completed source-only judgments; no inference, target execution or tuning."""
from __future__ import annotations
from collections import Counter
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUN = HERE / "run01"


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    keys = read(RUN / "REVIEW_KEY.json")
    master = {r["review_id"]: r for r in read(RUN / "SEMANTIC_REVIEW.json")}
    if any(len({x["query_sha256"] for x in refs}) != 1 for refs in keys.values()):
        raise ValueError("Review key crosses independent source queries")
    grades = {}
    inputs = []
    for i in (1, 2):
        queue = read(RUN / f"REVIEW_QUEUE_{i}.json")
        path = RUN / f"GRADES_{i}.json"
        values = read(path)
        if isinstance(values, dict):
            values = values["grades"]
        expected = {q["review_id"] for q in queue}
        if any(master.get(q["review_id"]) != q for q in queue):
            raise ValueError("Assigned queue differs from sealed master")
        if {g["review_id"] for g in values} != expected or len(values) != len(expected):
            raise ValueError("Incomplete or duplicate independent review")
        for g in values:
            if g["review_id"] in grades or g["status"] not in {"supported_fault", "contradicted", "unknown_or_conditional"}:
                raise ValueError("Invalid grade")
            if not g.get("source_quotes") or not g.get("reason"):
                raise ValueError("Missing review evidence")
            if g["status"] == "supported_fault" and not g.get("distinguishing_input_class"):
                raise ValueError("Supported fault needs distinguishing class")
            if g["status"] == "supported_fault" and not g.get("mechanism_family"):
                raise ValueError("Supported fault needs a mechanism family")
            if not all(q in master[g["review_id"]]["code"] for q in g["source_quotes"]):
                raise ValueError("Review quote absent from source")
            grades[g["review_id"]] = g
        inputs += [path, RUN/f"REVIEW_QUEUE_{i}.json"]
    summary = {}
    for kind in ("buggy", "canonical", "preinspected_engineering_fixture"):
        summary[kind] = {}
        for arm in ("V6", "A", "B", "C", "D"):
            rows = [g for rid, g in grades.items() if any(x["kind"] == kind and x["arm"] == arm for x in keys[rid])]
            counts = Counter(g["status"] for g in rows)
            summary[kind][arm] = {"reviewed_bindings": len(rows), **{k: counts[k] for k in
                ("supported_fault", "contradicted", "unknown_or_conditional")}}
    contrasts = {}
    for sparse, dense in (("A", "B"), ("C", "D")):
        added, removed = [], []
        for rid, grade in grades.items():
            refs = keys[rid]
            for kind in ("buggy", "canonical", "preinspected_engineering_fixture"):
                members = {r["arm"] for r in refs if r["kind"] == kind}
                row = {"review_id": rid, "kind": kind, "status": grade["status"],
                       "mechanism_family": grade.get("mechanism_family"),
                       "task_ids": sorted({r["task_id"] for r in refs if r["kind"] == kind})}
                if dense in members and sparse not in members:
                    added.append(row)
                if sparse in members and dense not in members:
                    removed.append(row)
        supported = [r for r in added if r["kind"] == "buggy" and r["status"] == "supported_fault"]
        families = sorted({r["mechanism_family"] for r in supported})
        control_kinds = {"canonical", "preinspected_engineering_fixture"}
        added_bad_controls = [r for r in added if r["kind"] in control_kinds and r["status"] == "contradicted"]
        removed_bad_controls = [r for r in removed if r["kind"] in control_kinds and r["status"] == "contradicted"]
        contrasts[dense+"-"+sparse] = {"added": added, "removed": removed,
            "new_supported_buggy_bindings": len(supported), "new_supported_mechanisms": families,
            "added_contradicted_paired_control_bindings": len(added_bad_controls),
            "removed_contradicted_paired_control_bindings": len(removed_bad_controls),
            "control_kinds": sorted(control_kinds),
            "preregistered_gate": "GO" if len(supported) >= 2 and len(families) >= 2
                and len(added_bad_controls) <= len(removed_bad_controls) else "NO_GO"}
    result = {"coverage": {"judged": len(grades), "total_union": len(keys),
                            "selection": "entire query union for every query with incremental dense top3 plus old four fixtures"},
              "reviewed_proposal_quality": summary, "contrasts": contrasts,
              "review_sha256": {p.name: sha(p) for p in inputs},
              "limits": ["Codex source reasoning, not independent human ground truth or formal proof.",
                         "Different source-based reviewers grade disjoint bindings; no inter-rater estimate.",
                         "Unmatched frozen label is unknown. Review status measures proposal quality, not bug-report FP.",
                         "No new test-generation or bug-detection efficacy measurement."]}
    out = RUN / "REVIEW_SUMMARY.json"
    with out.open("x") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({"coverage": result["coverage"], "reviewed_proposal_quality": summary,
                      "contrasts": {k:{a:b for a,b in v.items() if a not in ("added","removed")} for k,v in contrasts.items()}}, indent=2))


if __name__ == "__main__":
    main()
