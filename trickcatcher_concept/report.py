"""Aggregate a results.jsonl into paper-style metrics, paired stats and costs.

Usage:
  .venv/bin/python -m trickcatcher_concept.report --results <run-dir>/results.jsonl
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from trickcatcher_concept.evaluate import KS, summarize

BEST_K = {"cpp": 10, "python": 10}  # matches TrickCatcher Table 1's reported k for TC (best F1 at k=10)


def load_rows(path: Path) -> list[dict]:
    rows = []
    with Path(path).open() as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return [r for r in rows if "error" not in r]


def mcnemar(a_only: int, b_only: int) -> float:
    n = a_only + b_only
    if not n:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, k) for k in range(min(a_only, b_only) + 1)) / 2**n)


def paired_exposure(rows: list[dict], a_key: str, b_key: str) -> dict[str, Any]:
    tasks = [r for r in rows if r.get(a_key) and r.get(b_key)]
    a_only = [r["task_num"] for r in tasks if r[a_key]["task_exposed"] and not r[b_key]["task_exposed"]]
    b_only = [r["task_num"] for r in tasks if r[b_key]["task_exposed"] and not r[a_key]["task_exposed"]]
    both = sum(r[a_key]["task_exposed"] and r[b_key]["task_exposed"] for r in tasks)
    return {"n_paired": len(tasks), "a_exposed": sum(r[a_key]["task_exposed"] for r in tasks),
            "b_exposed": sum(r[b_key]["task_exposed"] for r in tasks), "both_exposed": both,
            "a_only": a_only, "b_only": b_only, "mcnemar_exact_two_sided": mcnemar(len(a_only), len(b_only))}


def validity_rates(rows: list[dict], arm: str) -> dict[str, Any]:
    key = f"{arm}_inputs"
    entries = [r[key] for r in rows if r.get(key)]
    generated = sum(e["generated"] for e in entries)
    usable = sum(e["usable"] for e in entries)
    eval_invalid_usable = sum(e["eval_invalid_usable"] for e in entries)
    byref_invalid_usable = sum(e["byref_invalid_usable"] for e in entries)
    return {"tasks": len(entries), "generated": generated, "usable": usable,
            "eval_invalid_rate_of_usable": eval_invalid_usable / usable if usable else None,
            "byref_invalid_rate_of_usable": byref_invalid_usable / usable if usable else None}


def per_lang_metrics(rows: list[dict], validity: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for lang in ("cpp", "python"):
        lang_rows = [r for r in rows if r["lang"] == lang]
        if not lang_rows:
            continue
        n = len(lang_rows)
        entry: dict[str, Any] = {"n_tasks": n, "by_k": {}}
        for k in KS:
            entry["by_k"][k] = {
                "baseline": summarize(lang_rows, f"baseline_{validity}", n, k),
                "concept": summarize(lang_rows, f"concept_{validity}", n, k),
            }
        best_k = BEST_K[lang]
        entry["best_k"] = best_k
        entry["best"] = entry["by_k"][best_k]
        entry["paired_task_exposure"] = paired_exposure(lang_rows, f"baseline_{validity}", f"concept_{validity}")
        entry["baseline_validity"] = validity_rates(lang_rows, "baseline")
        entry["concept_validity"] = validity_rates(lang_rows, "concept")
        out[lang] = entry
    return out


def llm_cost(run_dir: Path) -> dict[str, Any]:
    calls = input_tokens = output_tokens = 0
    by_model: dict[str, dict[str, int]] = {}
    for path in (run_dir / "llm_cache").rglob("*.json"):
        try:
            record = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        calls += 1
        input_tokens += record.get("input_tokens", 0)
        output_tokens += record.get("output_tokens", 0)
        model = record.get("model", "unknown")
        slot = by_model.setdefault(model, {"calls": 0, "input_tokens": 0, "output_tokens": 0})
        slot["calls"] += 1
        slot["input_tokens"] += record.get("input_tokens", 0)
        slot["output_tokens"] += record.get("output_tokens", 0)
    return {"calls": calls, "input_tokens": input_tokens, "output_tokens": output_tokens, "by_model": by_model}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", required=True)
    parser.add_argument("--validity", default="strict", choices=("strict", "refs"))
    args = parser.parse_args()
    results_path = Path(args.results)
    rows = load_rows(results_path)
    report = {
        "results_path": str(results_path), "n_rows": len(rows),
        "n_errors": sum(1 for line in results_path.open() if line.strip() and "error" in json.loads(line)),
        "metrics": per_lang_metrics(rows, args.validity),
        "cost": llm_cost(results_path.parent),
    }
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
