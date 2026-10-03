"""Oracle validation on DFUZZ's 37 reproducers: strict crash must fire on the ones REPLAY.md says reproduce (crash-type)
and never on their ori.py/original.py seeds. Writes run/out/oracle_validation.jsonl and prints a confusion summary.
usage (container): /opt/pilot/bin/python run/validate_oracle.py"""
import json, os, sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from oracle import evaluate_many

ROOT = Path(__file__).resolve().parent.parent
replay = {r["dir"]: r for r in map(json.loads, open(ROOT / "run/replay_results.jsonl"))}
items = []
for d, r in replay.items():
    p = ROOT / "bugs" / d
    items.append((f"{d}|bug", r["api"], (p / "bug.py").read_text()))
    seed = next((p / n for n in ("ori.py", "original.py") if (p / n).exists()), None)
    if seed:
        items.append((f"{d}|seed", r["api"], seed.read_text()))
res = evaluate_many(items)
out = open(ROOT / "run/out/oracle_validation.jsonl", "w")
tally = {}
for key, v in res.items():
    d, kind = key.split("|")
    exp = replay[d]
    rec = {"dir": d, "kind": kind, "expected": exp["expected"], "replay_reproduces": exp["reproduces"],
           **{k: v[k] for k in ("cls", "strict_crash", "crash_classes", "crash_hits", "sig", "disagree", "exc",
                                "at_target", "own_check")}, "msg": (v["msg"] or "")[:200]}
    out.write(json.dumps(rec) + "\n")
    t = (kind, exp["reproduces"] if kind == "bug" else "seed", exp["expected"] if kind == "bug" else "-", v["strict_crash"])
    tally[t] = tally.get(t, 0) + 1
    print(f"{kind:4} {d:70} replay={exp['reproduces']:14} -> cls={v['cls']:14} strict={v['strict_crash']} "
          f"hits={v['crash_hits']} at_target={v['at_target']} sig={v['sig']} disagree={v['disagree']}", flush=True)
print("\n(kind, replay_reproduces, expected, strict_crash): count")
for k in sorted(tally, key=str):
    print(k, tally[k])
