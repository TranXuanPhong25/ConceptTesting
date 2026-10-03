"""Sample frame (PILOT_PLAN 'Sample'): seeded APIs with >=1 gap mapped to a DFUZZ parameter role + released edge case,
whose released seed runs cleanly on arm64 and calls the target; known-bug APIs and aliases excluded.
Strata: tf_tfsa (raw op with a pre-2.15 TFSA advisory) / tf_other / torch.
Also reports the frame restricted to gaps confirmed by the manual review (run/out/gap_review.jsonl).
Writes run/out/frame.jsonl. usage (container, NOCREDS=1): /opt/pilot/bin/python run/frame.py"""
import json, os, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from oracle import evaluate_many

ROOT = os.path.dirname(HERE)
idx = json.load(open(f"{HERE}/out/gap_index.json"))
gaps = [json.loads(l) for l in open(f"{HERE}/out/gaps.jsonl")]
review = {(r["api"], r["kind"], r["param"]): r["verdict"] for r in map(json.loads, open(f"{HERE}/out/gap_review.jsonl"))}
progs = {**json.load(open(f"{ROOT}/gen_program/results/tf/api_programs.json")),
         **json.load(open(f"{ROOT}/gen_program/results/torch/api_programs.json"))}

cands = sorted(a for a, v in idx.items() if v["seeded"] and v["n_gaps_mapped"] and not v["known_bug_or_alias"])
runs = evaluate_many([(a, a, progs[a]) for a in cands])
out = open(f"{HERE}/out/frame.jsonl", "w")
counts = Counter()
for a in cands:
    v, r = idx[a], runs[a]
    stratum = "torch" if v["lib"] == "torch" else "tf_tfsa" if v["tfsa"] else "tf_other"
    mine = [g for g in gaps if g["api"] == a and g["role_in_dfuzz"] and g["edge_case"]]
    tw = a.replace("torch.Tensor.", "torch.")
    verdicts = [review.get((g["api"], g["kind"], g["param"])) or review.get((tw, g["kind"], g["param"])) for g in mine]
    ok = r["cls"] == "clean" and r["has_target_call"]
    rec = {"api": a, "stratum": stratum, "in_frame": ok, "seed_cls": r["cls"], "seed_exc": r["exc"],
           "has_target_call": r["has_target_call"], "n_gaps": len(mine), "kinds": sorted({g["kind"] for g in mine}),
           "review": verdicts, "verified": any((x or "").startswith("TP") for x in verdicts),
           "verified_crash_capable": any(x == "TP-crash" for x in verdicts), "tfsa": v["tfsa"][:3],
           "bug_family": v["bug_family"]}
    out.write(json.dumps(rec) + "\n")
    counts[(stratum, "candidates")] += 1
    counts[(stratum, "in_frame")] += ok
    counts[(stratum, "in_frame_verified")] += ok and rec["verified"]
    counts[(stratum, "in_frame_crash_capable")] += ok and rec["verified_crash_capable"]
    print(f"{a:50} {stratum:8} seed={r['cls']:10} target_call={r['has_target_call']} gaps={len(mine)} review={verdicts}")
print()
for s in ("tf_tfsa", "tf_other", "torch"):
    print(s, {k: counts[(s, k)] for k in ("candidates", "in_frame", "in_frame_verified", "in_frame_crash_capable")})
