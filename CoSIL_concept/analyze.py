#!/usr/bin/env python3
"""Evaluation (the authors' FLEvalNew metrics) and paired statistics for the stock / concept / placebo arms.

usage: python analyze.py eval <dataset> [--ids FILE|ID,ID]   -> out/<ds>/metrics.json, per_instance.jsonl
       python analyze.py stats <dataset>                     -> out/<ds>/stats.json (+ printed tables)

Ground truth: swebench_lite = the authors' evaluation/gt.json; locbench = LocBench edit_functions + patched files;
swebench_live = derived from the gold patch over the base-commit structure (prepare.py). Missing outputs count as
misses (the authors' convention: denominators are the ground-truth size).
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import sys
from collections import defaultdict
from pathlib import Path

from prepare import DATA, STRUCT, VENDOR, load_rows

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
ARMS = ("stock", "concept", "placebo")
PAIRS = (("concept", "placebo"), ("concept", "stock"), ("placebo", "stock"))  # first = primary
GT_FILE = {"swebench_lite": "swebench_lite_gt.json", "locbench": "locbench_gt.json",
           "swebench_live": "swebench_live_gt_patch.json"}
CONCEPTS = [f"C{i}" for i in range(1, 9)]


def authors_eval():
    spec = importlib.util.spec_from_file_location("FLEvalNew", VENDOR / "evaluation" / "FLEvalNew.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in open(p)] if p.exists() else []


def gold_concepts(ds: str, iid: str, entries: list[str]) -> list[str] | None:
    """Union of C1-C8 tags (as shown in the concept arm) over the gold functions/methods; None without a structure."""
    p = STRUCT / ds / f"{iid}.json"
    if not p.exists():
        return None
    from check_tags import function_texts
    from concept_annotator_py.functions import annotate_function

    texts = function_texts(json.load(open(p))["structure"])
    out = set()
    for e in entries:
        if "::" in e and (hit := texts.get(tuple(e.split("::", 1)))):
            out |= set(annotate_function("\n".join(hit[1]), hit[0] - 1)["concepts"])
    return sorted(out)


def evaluate(ds: str, ids: str | None) -> None:
    ev = authors_eval()
    gt_all = json.load(open(DATA / GT_FILE[ds]))
    (OUT / ds).mkdir(parents=True, exist_ok=True)
    rows = load_rows(ds, ids)
    gt = {r["instance_id"]: gt_all[r["instance_id"]] for r in rows if r["instance_id"] in gt_all}
    print(f"[eval] {ds}: {len(gt)} instances with ground truth ({len(rows) - len(gt)} selected without: "
          f"structure not built); {sum(not any('::' in e for e in v) for v in gt.values())} have no function-level gt")
    metrics, per = {}, defaultdict(dict)
    for arm in ARMS:
        preds = {r["instance_id"]: r for r in load_jsonl(OUT / ds / f"{arm}.jsonl") if r["instance_id"] in gt}
        with contextlib.redirect_stdout(io.StringIO()):
            metrics[arm] = ev.evaluate_accuracy(list(preds.values()), gt)
        metrics[arm]["n_outputs"] = len(preds)
        for iid, entries in gt.items():  # the same computation as evaluate_accuracy, kept per instance
            gt_files, gt_methods = ev.parse_gt_methods(entries)
            p = preds.get(iid, {})
            files = p.get("found_files", [])[:5]
            methods = ev.extract_predicted_methods(ev.construct_pred_func(files, p.get("found_related_locs", {}))[:5]) if files else []
            rec = {f"file@{k}": int(ev.top_k_accuracy(gt_files, files, k)) for k in (1, 3, 5)}
            rec |= {f"func@{k}": int(ev.top_k_accuracy(gt_methods, methods, k)) for k in (1, 3, 5)}
            rec |= {"file_rr": ev.reciprocal_rank(gt_files, files), "func_rr": ev.reciprocal_rank(gt_methods, methods),
                    "has_output": iid in preds, "pred_methods": methods[:5]}
            per[iid][arm] = rec
        n = len(gt)
        assert abs(sum(per[i][arm]["func@5"] for i in gt) / n * 100 - metrics[arm]["function_level"]["TOP 5"]) < 1e-9
    with open(OUT / ds / "per_instance.jsonl", "w") as f:
        for iid in sorted(per):
            f.write(json.dumps({"instance_id": iid, "gt": gt[iid], "gold_concepts": gold_concepts(ds, iid, gt[iid]),
                                **per[iid]}) + "\n")
    json.dump({"dataset": ds, "n": len(gt), "metrics": metrics}, open(OUT / ds / "metrics.json", "w"), indent=1)
    print(f"{'arm':8} {'n_out':>5} | file@1 file@3 file@5  MAP   MRR | func@1 func@3 func@5  MAP   MRR")
    for arm, m in metrics.items():
        fl, fn = m["file_level"], m["function_level"]
        print(f"{arm:8} {m['n_outputs']:5} | " + " ".join(f"{fl[k]:6.1f}" for k in ("TOP 1", "TOP 3", "TOP 5", "MAP", "MRR"))
              + " | " + " ".join(f"{fn[k]:6.1f}" for k in ("TOP 1", "TOP 3", "TOP 5", "MAP", "MRR")))


def mcnemar(a: list[int], b: list[int]) -> tuple[int, int, float]:
    """Exact (binomial) McNemar: (#a-only, #b-only, two-sided p)."""
    from scipy.stats import binomtest
    x = sum(1 for i, j in zip(a, b) if i and not j)
    y = sum(1 for i, j in zip(a, b) if j and not i)
    return x, y, (binomtest(x, x + y, 0.5).pvalue if x + y else 1.0)


def wilcoxon(a: list[float], b: list[float]) -> tuple[int, float]:
    from scipy.stats import wilcoxon as w
    d = [i - j for i, j in zip(a, b) if i != j]
    return len(d), (float(w(d).pvalue) if d else 1.0)


def stats(ds: str) -> None:
    per = load_jsonl(OUT / ds / "per_instance.jsonl")
    ok = [r for r in per if all(r[a]["has_output"] for a in ARMS)]
    print(f"[stats] {ds}: {len(per)} instances, {len(ok)} with output in all three arms (paired tests use all {len(per)}; "
          f"missing = miss)")
    res = {"n": len(per), "n_all_arms": len(ok), "pairs": {}, "per_concept": {}}
    same_files = all(r[a]["file@5"] == r["stock"]["file@5"] for r in per for a in ARMS)
    print(f"[stats] file-level identical across arms (shared file stage): {same_files}")
    for x, y in PAIRS:
        row = {}
        for m in ("func@5", "func@1", "func@3"):
            b, c, p = mcnemar([r[x][m] for r in per], [r[y][m] for r in per])
            row[m] = {x: sum(r[x][m] for r in per), y: sum(r[y][m] for r in per), f"{x}_only": b, f"{y}_only": c, "p": p}
        k, p = wilcoxon([r[x]["func_rr"] for r in per], [r[y]["func_rr"] for r in per])
        row["func_rr"] = {f"mean_{x}": _mean(r[x]["func_rr"] for r in per), f"mean_{y}": _mean(r[y]["func_rr"] for r in per),
                          "n_nonzero_diff": k, "p": p}
        res["pairs"][f"{x}_vs_{y}"] = row
        print(f"[stats] {x} vs {y}: " + "; ".join(
            f"{m} {v[x]}/{v[y]} (only {v[f'{x}_only']}/{v[f'{y}_only']}, McNemar p={v['p']:.3g})" for m, v in row.items()
            if m != "func_rr") + f"; RR {row['func_rr'][f'mean_{x}']:.3f}/{row['func_rr'][f'mean_{y}']:.3f} "
            f"(Wilcoxon n={k}, p={p:.3g})")
    print(f"[stats] per concept of the gold function(s) (func@5, concept/placebo/stock; McNemar concept vs placebo):")
    for c in CONCEPTS + ["untagged"]:
        sub = [r for r in per if r["gold_concepts"] is not None and
               ((c in r["gold_concepts"]) if c != "untagged" else not r["gold_concepts"])]
        if not sub:
            continue
        b, d, p = mcnemar([r["concept"]["func@5"] for r in sub], [r["placebo"]["func@5"] for r in sub])
        acc = {a: sum(r[a]["func@5"] for r in sub) for a in ARMS}
        res["per_concept"][c] = {"n": len(sub), **acc, "concept_only": b, "placebo_only": d, "p": p}
        print(f"  {c:9} n={len(sub):4}  {acc['concept']:4}/{acc['placebo']:4}/{acc['stock']:4}  only {b}/{d}  p={p:.3g}")
    res["cost"] = ledger(ds)
    json.dump(res, open(OUT / ds / "stats.json", "w"), indent=1)


def _mean(xs) -> float:
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


def ledger(ds: str) -> dict:
    by = defaultdict(lambda: {"calls": 0, "in": 0, "out": 0, "think": 0, "usd": 0.0, "instances": set()})
    for r in load_jsonl(OUT / ds / "ledger.jsonl"):
        k = by[r["arm"] if r["stage"] == "funcs" else r["stage"]]
        k["calls"] += 1
        k["in"] += r["in"]
        k["out"] += r["out"]
        k["think"] += r["think"]
        k["usd"] += r["usd"]
        k["instances"].add(r["iid"])
    out = {}
    for k, v in by.items():
        n = len(v.pop("instances"))
        out[k] = {**v, "usd": round(v["usd"], 4), "usd_per_instance": round(v["usd"] / max(n, 1), 5), "instances": n}
        print(f"[cost] {k:8} {v['calls']:6} calls  in={v['in']:>10,} out={v['out']:>9,} think={v['think']}  "
              f"${v['usd']:.3f}  (${out[k]['usd_per_instance']:.4f}/instance over {n})")
    return out


if __name__ == "__main__":
    sys.path.append(str(HERE.parent))
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["eval", "stats"])
    ap.add_argument("dataset", choices=list(GT_FILE))
    ap.add_argument("--ids")
    a = ap.parse_args()
    evaluate(a.dataset, a.ids) if a.cmd == "eval" else stats(a.dataset)
