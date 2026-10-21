"""Gate A from parent + reviewer label CSVs (stdlib only). Rules: LABEL_GUIDE.md 'Gate A'."""
import csv, json, sys
from collections import Counter

FILES = {"parent": "labels.csv", "reviewer_1": "labels_reviewer_1.csv", "reviewer_2": "labels_reviewer_2.csv"}
UPSTREAM = {"SPEC", "PRED", "OBS", "INTERFACE"}

def load(p):
    with open(p, newline="") as f:
        return {(r["episode"], r["arm"]): r for r in csv.DictReader(f)}

def has_high_role(r):
    labs = {r["first_error_label"].strip().upper(), r["first_unrecovered_label"].strip().upper()}
    return "ROLE" in labs and r["role_confidence"].strip().lower().startswith("high")

def upstream_explained(r):
    first = r["first_error_label"].strip().upper()
    unrec = r["first_unrecovered_label"].strip().upper()
    if first in UPSTREAM or unrec in UPSTREAM:
        return True
    return False

def unknown_row(r):
    return "UNKNOWN" in (r["first_error_label"].strip().upper(), r["first_unrecovered_label"].strip().upper())

ann = {k: load(v) for k, v in FILES.items()}
keys = sorted(ann["parent"])
assert all(sorted(a) == keys for a in ann.values()) and len(keys) == 24, "row coverage mismatch"
out = {"per_annotator": {}, "agreement": {}}
for name, a in ann.items():
    elig = [k for k in keys if a[k]["eligible_target"].strip().lower() == "yes"]
    not_up = [k for k in elig if not upstream_explained(a[k])]
    # guide: UNKNOWN with an unexcluded OBS candidate counts as upstream; adjudicated by reading the text,
    # so report both bounds here
    strict = [k for k in not_up if not unknown_row(a[k])]
    out["per_annotator"][name] = {
        "high_role_rows": [f"{e}/{arm}" for e, arm in keys if has_high_role(a[(e, arm)])],
        "eligible": [f"{e}/{arm}" for e, arm in elig],
        "eligible_not_upstream": [f"{e}/{arm}" for e, arm in not_up],
        "eligible_unknown_rows": [f"{e}/{arm}" for e, arm in not_up if unknown_row(a[(e, arm)])],
        "cond2_strict": f"{len(strict)}/{len(elig)}", "cond2_lenient": f"{len(not_up)}/{len(elig)}",
        "cond2_pass": len(strict) * 2 > len(elig), "cond2_pass_lenient": len(not_up) * 2 > len(elig),
        "first_unrecovered": dict(Counter(a[k]["first_unrecovered_label"].strip().upper() or "NONE" for k in keys)),
    }
# agreed high-ROLE episodes: every annotator has a high-ROLE row in that episode
eps = sorted({e for e, _ in keys})
rel = {e: ann["parent"][(e, "concept_adaptive")]["relation"] for e in eps}
agreed = [e for e in eps if all(any(has_high_role(a[(e, arm)]) for (ee, arm) in keys if ee == e) for a in ann.values())]
cond1 = len(agreed) >= 2 and len({rel[e] for e in agreed}) >= 2
cond2 = all(v["cond2_pass"] for v in out["per_annotator"].values())
for k in keys:
    labs = {n: (a[k]["first_unrecovered_label"], a[k]["role_confidence"]) for n, a in ann.items()}
    if len({(l.upper(), c.lower()[:4]) for l, c in labs.values()}) > 1:
        out["agreement"][f"{k[0]}/{k[1]}"] = labs
out.update(agreed_high_role_episodes=agreed, relations={e: rel[e] for e in agreed},
           cond1_pass=cond1, cond2_pass_all_annotators=cond2, gate_A="GO_B1" if cond1 and cond2 else "STOP")
json.dump(out, open("gate_a.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps(out, indent=1, ensure_ascii=False))
