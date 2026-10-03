"""Phase 0b sample frame (PILOT_PLAN.md 'Phase 0b amendment'): seeded APIs with >=1 mapped gap whose released seed runs
clean on arm64 and calls the target, excluding the 37 known-bug APIs, their aliases and sibling families.
Computed for 4 variants to split vocabulary vs reach: extractor {p0, x0b} x vocabulary {released, v0b}.
Writes run/out/frame_0b.jsonl. usage (container, NOCREDS=1): /opt/pilot/bin/python run/frame_0b.py"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from oracle import evaluate_many

ROOT = os.path.dirname(HERE)
IX = {"p0": json.load(open(f"{HERE}/out/gap_index_p0v0b.json")), "x0b": json.load(open(f"{HERE}/out/gap_index_0b.json"))}
VOC = {"released": "n_gaps_mapped_released", "v0b": "n_gaps_mapped"}
progs = {**json.load(open(f"{ROOT}/gen_program/results/tf/api_programs.json")),
         **json.load(open(f"{ROOT}/gen_program/results/torch/api_programs.json"))}


def cand(ix, key):
    return {a for a, v in ix.items() if v["seeded"] and v[key] and not v["excluded"]}


variants = {f"{e}+{w}": cand(IX[e], k) for e in IX for w, k in VOC.items()}
union = sorted(set().union(*variants.values()))
runs = evaluate_many([(a, a, progs[a]) for a in union])
ok = {a for a in union if runs[a]["cls"] == "clean" and runs[a]["has_target_call"]}
with open(f"{HERE}/out/frame_0b.jsonl", "w") as out:
    for a in union:
        r, v = runs[a], IX["x0b"].get(a) or IX["p0"][a]
        rec = {"api": a, "lib": v["lib"], "seed_cls": r["cls"], "seed_exc": r["exc"], "seed_msg": (r["msg"] or "")[:200],
               "has_target_call": r["has_target_call"], "in_frame_ok": a in ok,
               "stratum": "torch" if v["lib"] == "torch" else "tf_tfsa" if v["tfsa"] else "tf_other",
               **{f"cand_{n}": a in s for n, s in variants.items()}}
        out.write(json.dumps(rec) + "\n")
        print(f"{a:48} seed={r['cls']:10} target_call={r['has_target_call']} "
              + " ".join(n for n, s in variants.items() if a in s), flush=True)
print()
for n, s in variants.items():
    print(f"{n:14} candidates={len(s):3} frame={len(s & ok):3}")
unseeded = {a for a, v in IX["x0b"].items() if not v["seeded"] and v["n_gaps_mapped"] and not v["excluded"]}
f = len(variants["x0b+v0b"] & ok)
print(f"go rule: frame(x0b+v0b)={f} >= 40 ? {f >= 40}; unseeded candidates={len(unseeded)}; "
      f"regenerate seeds only if {f} < 40 <= {f + len(unseeded)}: {f < 40 <= f + len(unseeded)}")
