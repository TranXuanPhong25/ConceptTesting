"""Analysis for the PBT_EdgeCases pilot (reads JSON/log results only; executes nothing).
usage: python3 run/analyze.py [r1|r0]   (r1 = arm-blind repair on, primary; r0 = strict) -> stdout + results/analysis_<m>.json
"""
import json, math, random, re, sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE / "results"
M = sys.argv[1] if len(sys.argv) > 1 else "r1"
TASKS = [22, 44, 49, 55, 63, 64, 76, 95, 97, 122, 123, 124, 127, 132, 140, 150]
PAPER = {"pbt": {22, 44, 55, 63, 64, 76, 95, 97, 122, 124, 132}, "ebt": {22, 44, 63, 64, 76, 97, 122, 124, 132, 140, 150}}
ARMS = ["ebt", "pbt", "pbt_concept", "pbt_placebo"]


def load(kind):
    out = defaultdict(lambda: defaultdict(dict))  # arm -> task -> k -> rec
    f = R / f"eval_gemini_{kind}_{M}.jsonl"
    for r in map(json.loads, f.open()) if f.exists() else []:
        _, arm, k, name = r["path"].split("/")[-4:]
        out[arm][int(name.split("_")[1].split(".")[0])][int(k[1:])] = r
    return out


def vendored():
    out = defaultdict(lambda: defaultdict(dict))
    for log in (R / "vendored").glob("*.log"):
        arm, k = log.stem.rsplit("_k", 1)
        for m in re.finditer(r"^(?:pbt|ebt) for task HumanEval/(\d+)\s+(passed|failed)", log.read_text(), re.M):
            out[arm][int(m.group(1))][int(k)] = m.group(2) == "failed"
    return out


def binom_two_sided(b, n):
    if n == 0: return 1.0
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, n - b) + 1)) / 2 ** n)


def signflip(d):
    nz = [x for x in d if x != 0]
    obs = abs(sum(d))
    if not nz: return 1.0
    hits = 0
    for mask in range(2 ** len(nz)):
        s = sum(x if mask >> i & 1 else -x for i, x in enumerate(nz))
        hits += abs(s) >= obs - 1e-12
    return hits / 2 ** len(nz)


def boot_ci(d, n=20000, seed=0):
    rng = random.Random(seed)
    ms = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(n))
    return ms[int(0.025 * n)], ms[int(0.975 * n)]


def compare(a, b, ra, rb):
    d = [ra[t] - rb[t] for t in TASKS]
    ma, mb = {t: ra[t] > 0.5 for t in TASKS}, {t: rb[t] > 0.5 for t in TASKS}
    b_, c_ = sum(ma[t] and not mb[t] for t in TASKS), sum(mb[t] and not ma[t] for t in TASKS)
    pos, neg = sum(x > 0 for x in d), sum(x < 0 for x in d)
    lo, hi = boot_ci(d)
    return {"a": a, "b": b, "mean_rate_a": round(sum(ra.values()) / 16, 3), "mean_rate_b": round(sum(rb.values()) / 16, 3),
            "mean_diff": round(sum(d) / 16, 3), "boot95": [round(lo, 3), round(hi, 3)],
            "majority_a": sum(ma.values()), "majority_b": sum(mb.values()), "mcnemar_b_c": [b_, c_],
            "mcnemar_exact_p": round(binom_two_sided(b_, b_ + c_), 4), "sign_pos_neg": [pos, neg],
            "sign_p": round(binom_two_sided(pos, pos + neg), 4), "perm_p": round(signflip(d), 4)}


def main():
    ev = {**load("pbt"), **load("ebt")}
    ven = vendored()
    res = {"mode": M, "per_task": {}, "arms": {}, "tests": []}
    rate = {}
    for arm in ARMS:
        recs = ev.get(arm, {})
        rate[arm] = {t: (sum(r["detect"] for r in recs[t].values()) / len(recs[t]) if recs.get(t) else 0.0) for t in TASKS}
        K = {t: len(recs.get(t, {})) for t in TASKS}
        allr = [r for t in TASKS for r in recs.get(t, {}).values()]
        vr = {t: (sum(ven[arm][t].values()) / len(ven[arm][t]) if ven.get(arm, {}).get(t) else None) for t in TASKS}
        res["arms"][arm] = {
            "K_min_max": [min(K.values()), max(K.values())], "files": len(allr),
            "majority_detected": sum(rate[arm][t] > 0.5 for t in TASKS),
            "any_of_K_detected": sum(rate[arm][t] > 0 for t in TASKS),
            "mean_task_rate": round(sum(rate[arm].values()) / 16, 3),
            "vendored_runner_majority": sum((vr[t] or 0) > 0.5 for t in TASKS),
            "vendored_runner_mean_rate": round(sum(v or 0 for v in vr.values()) / 16, 3),
            "raw_any_fail_mean_rate": round(sum(r["raw_detect"] for r in allr) / max(1, len(allr)), 3),
            "files_without_runnable_tests": sum(bool(r["error"]) or r["n_units"] == 0 for r in allr),
            "unit_validity": round(sum(r["n_valid"] for r in allr) / max(1, sum(r["n_units"] for r in allr)), 3),
            "files_repaired": sum(bool(r.get("repaired")) for r in allr),
            "detecting_units_by_buggy_outcome": dict(sorted(_mech(allr).items())),
            "files_using_@example": sum("@example(" in Path(HERE / r["path"]).read_text() for r in allr) if arm != "ebt" else None,
        }
        res["per_task"][arm] = {t: {"rate": round(rate[arm][t], 2), "K": K[t], "vendored_rate": vr[t] and round(vr[t], 2)} for t in TASKS}
    for a, b in [("pbt_concept", "pbt_placebo"), ("pbt_concept", "pbt"), ("pbt_placebo", "pbt"), ("ebt", "pbt")]:
        res["tests"].append(compare(a, b, rate[a], rate[b]))
    # paper agreement (single-shot paper result vs our per-task majority)
    for kind, arm in (("pbt", "pbt"), ("ebt", "ebt")):
        ours = {t for t in TASKS if rate[arm][t] > 0.5}
        res[f"paper_vs_ours_{kind}"] = {"paper": sorted(PAPER[kind]), "ours_majority": sorted(ours),
                                        "agree_tasks": sum((t in ours) == (t in PAPER[kind]) for t in TASKS)}
    for kind in ("pbt", "ebt"):  # authors' hand-filtered Claude files through our differential evaluator
        f = R / f"eval_authors_{kind}_{M}.jsonl"
        if f.exists():
            rs = [json.loads(l) for l in f.open()]
            det = {int(r["task"].split("/")[1]) for r in rs if r["detect"]}
            raw = {int(r["task"].split("/")[1]) for r in rs if r["raw_detect"]}
            res[f"authors_claude_{kind}"] = {"filtered": sorted(det), "raw": sorted(raw),
                                             "paper": sorted(PAPER[kind]), "filtered_minus_paper": sorted(PAPER[kind] - det)}
    (R / f"analysis_{M}.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "per_task"}, indent=1))
    print("\nper-task detection rate (filtered)  |  vendored-runner rate")
    print("task  " + "  ".join(f"{a:>11}" for a in ARMS) + "  | " + "  ".join(f"{a:>11}" for a in ARMS) + "  paper(P/E)")
    for t in TASKS:
        print(f"{t:<5} " + "  ".join(f"{rate[a][t]:>11.2f}" for a in ARMS) + "  | " +
              "  ".join(f"{(res['per_task'][a][t]['vendored_rate'] or 0):>11.2f}" for a in ARMS) +
              f"  {'P' if t in PAPER['pbt'] else '-'}{'E' if t in PAPER['ebt'] else '-'}")


def _mech(recs):
    c = defaultdict(int)
    for r in recs:
        for u in r["units"]:
            if u["fixed"] == "pass" and u["buggy"] != "pass" and u["buggy"] != "not_run":
                c[u["buggy"].split(":")[0]] += 1
    return c


if __name__ == "__main__":
    main()
