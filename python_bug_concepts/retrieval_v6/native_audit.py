"""Purposive native counterexamples; never imported by the retriever."""

from __future__ import annotations
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from .evaluate import HERE, BASE, fingerprint
from ..retrieval_v2.grade_witnesses import isolated
from ..retrieval_v3.grade_utility import equal

CASES = [
    (2, "py.branch-boundary-contract", [1.0]),
    (16, "py.unicode-text-byte-domain", ["café"]),
    (19, "py.presence-frequency-confusion", ["one one"]),
    (20, "py.negative-index-sentinel", [[1.0, 2.0]]),
    (23, "py.unicode-text-byte-domain", ["é"]),
    (27, "py.ascii-unicode-classification", ["É"]),
    (35, "py.extremum-initial-sentinel", [[-5, -2]]),
    (56, "py.empty-singleton-shortcut", [""]),
    (62, "py.index-origin-domain", [[1, 2]]),
    (67, "py.branch-boundary-contract", ["0 apples and 0 oranges", 0]),
    (68, "py.first-match-vs-optimum", [[1, 4, 2]]),
    (73, "py.presence-frequency-confusion", [[1, 1, 1, 2, 2, 2]]),
    (74, "py.aggregation-scope", [["aaa"], ["b", "c"]]),
    (114, "py.empty-singleton-shortcut", [[-1, -2]]),
    (118, "py.literal-classification-domain", ["FULL"]),
    (124, "py.branch-boundary-contract", ["01-01-1800"]),
    (126, "py.index-out-of-bounds", [[1, 1]]),
    (128, "py.branch-boundary-contract", [[-1, -2, -3]]),
    (136, "py.empty-reduction-domain", [[0, 0]]),
    (142, "py.empty-singleton-shortcut", [[2]]),
    (163, "py.index-origin-domain", [1, 4]),
]


def run(tag):
    out = HERE / "evaluation_v6" / tag
    if (out / "NATIVE_AUDIT.json").exists():
        raise ValueError("Preserve the existing native audit")
    frozen = json.loads((out / "FREEZE.json").read_text())
    assert frozen["implementation"] == fingerprint()
    refs = {
        r["task_id"]: {
            k: r[k] for k in ["entry_point", "prompt", "canonical_solution", "contract", "atol"]
        }
        for r in map(
            json.loads,
            (Path.home() / ".cache/evalplus/HumanEvalPlus-v0.1.10.jsonl").read_text().splitlines(),
        )
    }
    tasks = {r["task_id"]: r for r in json.loads((BASE / "inputs.json").read_text())}
    predictions = {
        r["task_id"]: r for r in json.loads((out / "RESULTS.json").read_text())["records"]
    }
    plan = {
        "sampling": "purposive source/implementation audit cases; not a precision estimate",
        "cases": [
            {"task_id": f"HumanEval/{n}", "concept_id": cid, "args": args} for n, cid, args in CASES
        ],
    }
    (out / "NATIVE_PLAN.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n")

    def one(case):
        n, cid, args = case
        tid = f"HumanEval/{n}"
        ref = refs[tid]
        source = ref["prompt"] + ref["canonical_solution"]
        job = {"entry": ref["entry_point"], "args": args}
        validity = isolated(
            {**job, "mode": "validity", "source": source, "contract": ref["contract"]}
        )
        expected = isolated({**job, "mode": "value", "source": source})
        actual = isolated({**job, "mode": "value", "source": tasks[tid]["code"]})
        valid = validity.get("status") == "ok" and validity.get("value") is True
        differs = expected.get("status") == "ok" and (
            actual.get("status") == "error"
            or actual.get("status") == "ok"
            and not equal(actual["value"], expected["value"], ref["atol"])
        )
        selected = {
            p: next((s for s in row["selected"] if s["concept_id"] == cid), None)
            for p, row in predictions[tid]["systems"].items()
        }
        return {
            "task_id": tid,
            "concept_id": cid,
            "args": args,
            "validity": validity,
            "reference": expected,
            "put": actual,
            "confirmed_bug_input": valid and differs,
            "selected": selected,
        }

    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(one, CASES))
    result = {
        "summary": {
            "cases": len(rows),
            "official_valid": sum(r["validity"].get("value") is True for r in rows),
            "confirmed_bug_inputs": sum(r["confirmed_bug_input"] for r in rows),
            "matching_concept_returned": {
                p: sum(r["selected"][p] is not None for r in rows)
                for p in ["coverage", "balanced", "precise"]
            },
        },
        "records": rows,
        "reference_fields_used": [
            "entry_point",
            "prompt",
            "canonical_solution",
            "contract",
            "atol",
        ],
        "hidden_tests_used": False,
        "limits": [
            "Native replay confirms input validity/outcome difference, not causal attribution to every selected concept.",
            "Selected inputs intentionally exercise mechanisms; not random evaluation or global precision.",
            "No expected/reference values enter retrieval.",
        ],
    }
    (out / "NATIVE_AUDIT.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--tag", required=True)
    args = p.parse_args()
    run(args.tag)
