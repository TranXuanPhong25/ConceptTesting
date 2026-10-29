"""Reuse unchanged native outcomes; correct one invalid input-shape proposal."""

import hashlib
import json
from pathlib import Path
from .evaluate import HERE, BASE, fingerprint
from ..retrieval_v2.grade_witnesses import isolated
from ..retrieval_v3.grade_utility import equal


def run():
    out = HERE / "evaluation_v6/iter05"
    old = HERE / "evaluation_v6/iter03"
    dest = out / "NATIVE_AUDIT_FINAL.json"
    if dest.exists():
        raise ValueError("Preserve final native evidence")
    assert json.loads((out / "FREEZE.json").read_text())["implementation"] == fingerprint()
    assert (
        json.loads((out / "FREEZE.json").read_text())["inputs"]["inputs.json"]
        == json.loads((old / "FREEZE.json").read_text())["inputs"]["inputs.json"]
    )
    cache = Path.home() / ".cache/evalplus/HumanEvalPlus-v0.1.10.jsonl"
    sha = hashlib.sha256(cache.read_bytes()).hexdigest()
    assert sha == json.loads((BASE / "witness_grading.json").read_text())["reference_sha256"]
    refs = {
        r["task_id"]: {
            k: r[k] for k in ["entry_point", "prompt", "canonical_solution", "contract", "atol"]
        }
        for r in map(json.loads, cache.read_text().splitlines())
    }
    tasks = {r["task_id"]: r for r in json.loads((BASE / "inputs.json").read_text())}
    predictions = {
        r["task_id"]: r for r in json.loads((out / "RESULTS.json").read_text())["records"]
    }
    prior = json.loads((old / "NATIVE_AUDIT.json").read_text())
    rows = [
        {k: v for k, v in r.items() if k != "selected"}
        for r in prior["records"]
        if r["confirmed_bug_input"]
    ]
    tid = "HumanEval/23"
    ref = refs[tid]
    args = ["é"]
    code = ref["prompt"] + ref["canonical_solution"]
    (out / "NATIVE_CORRECTION_PLAN.json").write_text(
        json.dumps(
            {
                "task_id": tid,
                "args": args,
                "reason": "Initial proposal incorrectly passed a list to a string parameter; original invalid row preserved in iter03.",
                "new_native_calls": 3,
            },
            indent=2,
        )
        + "\n"
    )
    job = {"entry": ref["entry_point"], "args": args}
    validity = isolated({**job, "mode": "validity", "source": code, "contract": ref["contract"]})
    expected = isolated({**job, "mode": "value", "source": code})
    actual = isolated({**job, "mode": "value", "source": tasks[tid]["code"]})
    differs = expected.get("status") == "ok" and (
        actual.get("status") == "error"
        or actual.get("status") == "ok"
        and not equal(expected["value"], actual["value"], ref["atol"])
    )
    rows.append(
        {
            "task_id": tid,
            "concept_id": "py.unicode-text-byte-domain",
            "args": args,
            "validity": validity,
            "reference": expected,
            "put": actual,
            "confirmed_bug_input": validity.get("value") is True and differs,
            "correction": True,
        }
    )
    for row in rows:
        row["selected"] = {
            p: next((s for s in system["selected"] if s["concept_id"] == row["concept_id"]), None)
            for p, system in predictions[row["task_id"]]["systems"].items()
        }
    result = {
        "summary": {
            "distinct_mechanism_cases": len(rows),
            "official_valid": sum(r["validity"].get("value") is True for r in rows),
            "confirmed_bug_inputs": sum(r["confirmed_bug_input"] for r in rows),
            "returned_matching_concept": {
                p: sum(r["selected"][p] is not None for r in rows)
                for p in ["coverage", "balanced", "precise"]
            },
        },
        "records": rows,
        "provenance": {
            "reused_artifact": str(old / "NATIVE_AUDIT.json"),
            "reused_sha256": hashlib.sha256((old / "NATIVE_AUDIT.json").read_bytes()).hexdigest(),
            "reused_valid_outcomes": 20,
            "initial_invalid_proposals": 1,
            "corrected_input_proposals": 1,
            "new_native_workers": 3,
            "reference_sha256": sha,
        },
        "limits": prior["limits"],
        "hidden_tests_used": False,
    }
    dest.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    run()
