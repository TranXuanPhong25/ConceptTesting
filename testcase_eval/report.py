#!/usr/bin/env python3
"""Paired comparison tables for scored Task 2 runs (official + strict metrics).

For every condition: Fault Exposure (official denominator = all targets),
strict Fault Exposure (only validator-accepted inputs on which all accepted
submissions succeed and agree), validity rates, per language family.  For
every pair against a reference condition: exact McNemar on the paired
targets and a problem-clustered bootstrap 95% CI of the difference.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

from testcase_eval.llm import estimate_cost
from testcase_eval.stats import mcnemar
from testcase_eval.store import read_jsonl

FAMILIES = ("all", "cpp", "java", "python")


def load_scored(path: str) -> dict[int, dict[str, Any]]:
    rows = {}
    for r in read_jsonl(path):
        rows[int(r["submission_id"])] = r
    return rows


def cluster_bootstrap(diffs: dict[str, list[int]], reps: int = 2000, seed: int = 7) -> tuple[float, float]:
    clusters = list(diffs.values())
    if not clusters:
        return 0.0, 0.0
    rng = random.Random(seed)
    stats = []
    for _ in range(reps):
        sample = [clusters[rng.randrange(len(clusters))] for _ in clusters]
        n = sum(len(c) for c in sample)
        stats.append(sum(sum(c) for c in sample) / max(1, n))
    stats.sort()
    return stats[int(0.025 * reps)], stats[int(0.975 * reps) - 1]


def rate(items: list[dict], key: str) -> float:
    return sum(bool(r[key]) for r in items) / max(1, len(items))


def condition_table(runs: dict[str, dict[int, dict]], ids: list[int]) -> list[dict[str, Any]]:
    table = []
    for name, rows in runs.items():
        for fam in FAMILIES:
            items = [rows[i] for i in ids if i in rows and (fam == "all" or rows[i].get("family") == fam)]
            if not items:
                continue
            table.append({
                "condition": name, "family": fam, "n": len(items),
                "FE_official": rate(items, "exposed_official"),
                "FE_strict": rate(items, "exposed_strict"),
                "input_present": rate(items, "input_present"),
                "validator_accept": sum(r["validator"] == "accepted" for r in items) / len(items),
                "official_consensus": rate(items, "official_consensus"),
                "strict_valid": rate(items, "strict_valid"),
                "FE_strict_given_valid": sum(r["exposed_strict"] for r in items) / max(1, sum(r["strict_valid"] for r in items)),
            })
    return table


def paired(runs: dict[str, dict[int, dict]], ids: list[int], reference: str, metric: str) -> list[dict[str, Any]]:
    out = []
    ref = runs[reference]
    for name, rows in runs.items():
        if name == reference:
            continue
        for fam in FAMILIES:
            common = [i for i in ids if i in rows and i in ref and (fam == "all" or ref[i].get("family") == fam)]
            if not common:
                continue
            a = {i: int(bool(rows[i][metric])) for i in common}
            b = {i: int(bool(ref[i][metric])) for i in common}
            only_a, only_b, p = mcnemar(a, b)
            diffs: dict[str, list[int]] = defaultdict(list)
            for i in common:
                diffs[ref[i]["problem_id"]].append(a[i] - b[i])
            lo, hi = cluster_bootstrap(diffs)
            out.append({
                "condition": name, "reference": reference, "metric": metric, "family": fam, "n": len(common),
                "cond_rate": sum(a.values()) / len(common), "ref_rate": sum(b.values()) / len(common),
                "diff": (sum(a.values()) - sum(b.values())) / len(common), "ci95": [lo, hi],
                "cond_only": only_a, "ref_only": only_b, "mcnemar_p": p,
            })
    return out


def cost_table(gen_paths: dict[str, str]) -> dict[str, Any]:
    out = {}
    for name, path in gen_paths.items():
        rows = read_jsonl(path)
        inp = sum(r.get("usage", {}).get("input_tokens", 0) for r in rows)
        outp = sum(r.get("usage", {}).get("output_tokens", 0) for r in rows)
        calls = sum(r.get("usage", {}).get("calls", 0) for r in rows)
        out[name] = {"targets": len(rows), "calls": calls, "input_tokens": inp, "output_tokens": outp,
                     "usd": round(estimate_cost(inp, outp), 2), "usd_per_target": round(estimate_cost(inp, outp) / max(1, len(rows)), 5)}
    return out


def pct(x: float) -> str:
    return f"{100 * x:.1f}"


def markdown(table: list[dict], pairs: list[dict]) -> str:
    lines = ["| condition | family | n | FE official | FE strict | validator accept | official consensus | strict valid | FE strict given valid |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in table:
        lines.append(f"| {r['condition']} | {r['family']} | {r['n']} | {pct(r['FE_official'])} | {pct(r['FE_strict'])} | {pct(r['validator_accept'])} | "
                     f"{pct(r['official_consensus'])} | {pct(r['strict_valid'])} | {pct(r['FE_strict_given_valid'])} |")
    lines += ["", "| condition vs ref | metric | family | n | cond | ref | diff (95% cluster CI) | cond-only | ref-only | McNemar p |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for p in pairs:
        lines.append(f"| {p['condition']} vs {p['reference']} | {p['metric']} | {p['family']} | {p['n']} | {pct(p['cond_rate'])} | {pct(p['ref_rate'])} | "
                     f"{100 * p['diff']:+.1f} [{100 * p['ci95'][0]:+.1f}, {100 * p['ci95'][1]:+.1f}] | {p['cond_only']} | {p['ref_only']} | {p['mcnemar_p']:.3g} |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scored", nargs="+", required=True, help="name=path of evaluate.py output")
    parser.add_argument("--gen", nargs="*", default=[], help="name=path of generate.py output (costs)")
    parser.add_argument("--reference", default="cot")
    parser.add_argument("--targets", default="", help="restrict to these submission ids")
    parser.add_argument("--exclude", default="", help="drop these submission ids (e.g. the tuning subset)")
    parser.add_argument("--json-out", default="")
    args = parser.parse_args()
    runs = {k: load_scored(v) for k, v in (s.split("=", 1) for s in args.scored)}
    ids = sorted(set.intersection(*(set(r) for r in runs.values())))
    if args.targets:
        keep = {int(x) for x in Path(args.targets).read_text().split()}
        ids = [i for i in ids if i in keep]
    if args.exclude:
        drop = {int(x) for x in Path(args.exclude).read_text().split()}
        ids = [i for i in ids if i not in drop]
    table = condition_table(runs, ids)
    pairs = []
    if args.reference in runs:
        for metric in ("exposed_official", "exposed_strict"):
            pairs += paired(runs, ids, args.reference, metric)
    costs = cost_table(dict(s.split("=", 1) for s in args.gen)) if args.gen else {}
    print(markdown(table, pairs))
    if costs:
        print("\n" + json.dumps(costs, indent=2))
    if args.json_out:
        Path(args.json_out).write_text(json.dumps({"n_paired": len(ids), "table": table, "pairs": pairs, "costs": costs}, indent=2))


if __name__ == "__main__":
    main()
