"""v6: v3m2 facts re-fuzzed under the B5 (F1b) precondition validator instead of the v3m2 one.

Only change versus v3m2: facts.py --validity mined --precond-dir out/precond_qwen7b_v4 (B5), so fuzz inputs that
violate a mined input requirement never become witnesses and facts that only such inputs reach (e.g. "n was never
zero" when the specification requires n > 0) disappear. Fuzz, tracer, gates, ranking, K=3, placebo rules unchanged.

  python3 -B trickcatcher_linefacts/run_v6.py facts            # out/facts_v6/<n>.json (CPU only)
  V4=... ; $V4 -B trickcatcher_linefacts/run_v6.py bundle      # out/tasks_v6_all.json + out/tasks_v6hyb_v4.json
"""

# Direct-script workers run with -I: establish this copy's package explicitly.
import sys as _package_sys
from pathlib import Path as _PackagePath
if not __package__:
    _package_here = _PackagePath(__file__).resolve().parent
    _package_sys.path.insert(0, str(_package_here.parents[2]))
    __package__ = "trickcatcher_linefacts.pipelines." + _package_here.name
from .paths import REPO as _REPO, DATA_OUT, CONFIG, dataset_paths
import argparse, json, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent

from . import generate

PRECOND = DATA_OUT / 'precond_qwen7b_v4'
FACTS = DATA_OUT / 'facts_v6'
SOURCE = DATA_OUT / 'tasks_v3m2_all.json'


def facts(workers):
    FACTS.mkdir(parents=True, exist_ok=True)
    tasks = json.loads(SOURCE.read_text())["tasks"]

    def one(t):
        n = t["task"]; out = FACTS / f"{n}.json"
        if out.exists():
            return True
        put = generate.PUTS / f"HumanEval_{n}/put0.py"
        r = subprocess.run(["timeout", "3600", "unshare", "-rn", sys.executable, "-B", "facts.py", str(n), str(put),
                            str(generate.HE), str(out), "--validity", "mined", "--precond-dir", str(PRECOND)],
                           cwd=HERE, capture_output=True, text=True)
        if r.returncode:
            (FACTS / f"{n}.err").write_text(r.stderr[-4000:])
        return out.exists()

    with ThreadPoolExecutor(workers) as pool:
        ok = list(pool.map(one, tasks))
    print(f"v6 facts: {sum(ok)}/{len(tasks)}")


def bundle():
    from . import oracle_b01 as ob, preconditions
    src = json.loads(SOURCE.read_text())
    he = {int(r["task_id"].split("/")[1]): r for r in map(json.loads, generate.HE.open())}
    tasks = []
    for t in src["tasks"]:
        n = t["task"]; b = generate.bundle(n, he[n], FACTS)
        r = json.loads((FACTS / f"{n}.json").read_text())
        valid = (PRECOND / str(n) / "valid.py").read_text()
        tasks.append(dict(t, concept_facts=b["concept_facts"], concept_meta=b["concept_meta"],
                          placebo_facts=b["placebo_facts"], placebo_meta=r["placebo3"],
                          tool_inputs=[c for c in b["tool_inputs"] if c], doc_fail=b["doc_fail"],
                          mined_valid_src=valid, valid_sha256=preconditions.sha(valid)))
    out = dict(src, tasks=tasks, note="v6: v3m2 pipeline, fuzz validated by B5 preconditions (out/facts_v6)")
    (DATA_OUT / 'tasks_v6_all.json').write_text(json.dumps(out))
    # v4 format for run_v4 arms (same recipe as out/tasks_v3m2hyb_v4.json): v4c domain strategies, mutant sources
    v4c = {t["task"]: t for t in json.loads((DATA_OUT / 'tasks_v4c_all.json').read_text())["tasks"]}
    hyb = json.loads(json.dumps(out))
    for t in hyb["tasks"]:
        c = v4c[t["task"]]
        t.update(strategy_src=c["strategy_src"], strategy_sha256=c["strategy_sha256"],
                 strategy_fallback=c["strategy_fallback"], mining_summary=c["mining_summary"], facts_version="v4")
        for key in ("concept_meta", "placebo_meta"):
            for f in t[key]:
                if f["kind"] == "MUTANT" and "mutant_src" not in f:
                    f["mutant_src"] = ob.mutant_source(t["put"], f["k"])
    hyb["facts_version"] = "v4"
    (DATA_OUT / 'tasks_v6hyb_v4.json').write_text(json.dumps(hyb))
    dev = [t for t in tasks if t["split"] == "dev"]
    print(f"v6 bundle: {len(tasks)} tasks; dev with facts {sum(bool(t['concept_facts']) for t in dev)}/{len(dev)}")


if __name__ == "__main__":
    raise SystemExit('v30 CPU-only: inherited generation CLI disabled')
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("facts", "bundle"))
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args()
    facts(a.workers) if a.cmd == "facts" else bundle()
