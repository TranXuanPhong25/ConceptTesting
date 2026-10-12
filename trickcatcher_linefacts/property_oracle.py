"""Property concepts, step A (PREREG): B3 postconditions used as the oracle on the pooled v3m2 inputs.

A kept postcondition (holds on every base-test pair) detects on input x when PUT(x) violates it and canonical(x)
satisfies it; it is a false alarm when canonical(x) violates it. Canonical and the EvalPlus contract only score.

  python3 -B trickcatcher_linefacts/property_oracle.py [--run out/gen2_qwen7b_v3m2 --oracle out/oracle_b01]
"""
from __future__ import annotations

import argparse, ast, collections, json, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from trickcatcher_linefacts import oracle_b01 as ob, preconditions


def worker(job_path, out_path):
    import copy, signal

    class TO(Exception):
        pass

    def alarm(*_):
        raise TO()

    signal.signal(signal.SIGALRM, alarm)
    job = json.loads(Path(job_path).read_text())

    def timed(f, secs):
        signal.alarm(secs)
        try:
            return "ok", f()
        except TO:
            return "Timeout", None
        except BaseException as e:
            return type(e).__name__, None
        finally:
            signal.alarm(0)

    env = {}
    exec("from typing import *\nimport math", env)

    def load(src):
        ns = {"__name__": "__x__"}
        st, _ = timed(lambda: exec("from typing import *\nimport math\n" + src, ns), 5)
        f = ns.get(job["entry"]) if st == "ok" else None
        return f if callable(f) else None

    put, canon, contract = load(job["put"]), load(job["canon"]), load(job["contract"])
    params = [a.arg for a in ast.parse(job["spec"]).body[0].args.args]
    pairs = []
    for node in ast.walk(ast.parse(job["base"])):
        if isinstance(node, ast.Assert) and isinstance(node.test, ast.Compare) and len(node.test.ops) == 1 \
                and isinstance(node.test.ops[0], ast.Eq) and isinstance(node.test.left, ast.Call) \
                and isinstance(node.test.left.func, ast.Name) and node.test.left.func.id == "candidate" and not node.test.left.keywords:
            st, v = timed(lambda: ([eval(compile(ast.Expression(a), "<a>", "eval"), dict(env)) for a in node.test.left.args],
                                   eval(compile(ast.Expression(node.test.comparators[0]), "<e>", "eval"), dict(env))), 3)
            if st == "ok":
                pairs.append(v)

    def holds(post, args, ret):
        ns = dict(env); ns.update(dict(zip(params, copy.deepcopy(args)))); ns["return_val"] = copy.deepcopy(ret)
        st, _ = timed(lambda: exec(post, ns), 2)
        return st != "AssertionError"

    posts = [p for p in job["posts"] if pairs and all(holds(p, a, e) for a, e in pairs)]
    out = dict(n_posts=len(job["posts"]), kept=posts, n_pairs=len(pairs), calls={})
    for call in job["calls"]:
        node = ast.parse(call, mode="eval").body
        st, args = timed(lambda: [eval(compile(ast.Expression(a), "<a>", "eval"), dict(env)) for a in node.args], 3)
        if st != "ok" or node.keywords:
            continue
        run = lambda f: timed(lambda: f(*copy.deepcopy(args)), 3)
        ps, pv = run(put); cs, cv = run(canon)
        rec = dict(valid=run(contract)[0] == "ok", put=ps, canon=cs)
        if ps == "ok" and cs == "ok":
            rec["viol_put"] = [i for i, p in enumerate(posts) if not holds(p, args, pv)]
            rec["viol_canon"] = [i for i, p in enumerate(posts) if not holds(p, args, cv)]
        out["calls"][call] = rec
    Path(out_path).write_text(json.dumps(out))


def main(run, oracle, out, workers=12):
    tasks, rows = ob.load_run(run)
    calls = json.loads((oracle / "calls.json").read_text())
    posts = ob.by_task(oracle, "post", ob.post_of)
    hep = {int(r["task_id"].split("/")[1]): r for r in map(json.loads, ob.HEP.open())}
    work = out / "exec"; work.mkdir(parents=True, exist_ok=True)

    def one(t):
        res = work / f"{t}.json"
        if res.exists():
            return
        task, h = tasks[int(t)], hep[int(t)]
        job = dict(entry=task["entry"], put=task["put"], canon=h["prompt"] + h["canonical_solution"], base=task["base"],
                   contract=h["prompt"] + h["contract"] + "\n    pass\n", spec=preconditions.specification(task)[0],
                   posts=posts.get(t, []), calls=calls[t])
        jp = work / f"{t}.job.json"; jp.write_text(json.dumps(job))
        subprocess.run(["timeout", "-k", "5", "3000", "unshare", "-rn", sys.executable, "-I", "-B", str(Path(__file__)),
                        "worker", str(jp), str(res)], check=False, capture_output=True)

    with ThreadPoolExecutor(workers) as pool:
        list(pool.map(one, list(calls)))
    res = {t: json.loads((work / f"{t}.json").read_text()) for t in calls if (work / f"{t}.json").exists()}
    ex = {p.stem: json.loads(p.read_text()) for p in (oracle / "exec").glob("*.json") if not p.name.endswith(".job.json")}
    lines = []
    for split in ("dev", "pilot"):
        tids = sorted(str(t) for t, v in tasks.items() if v.get("split") == split and str(t) in res)
        c = collections.Counter()
        for t in tids:
            r = res[t]; kept = len(r["kept"]); c["tasks"] += 1; c["with_props"] += kept > 0; c["props"] += kept
            valid = {k: v for k, v in r["calls"].items() if v["valid"]}
            det = any(set(v.get("viol_put", [])) - set(v.get("viol_canon", [])) for v in valid.values())
            crash = any(v["put"] != "ok" and v["canon"] == "ok" for v in valid.values())
            fa = any(v.get("viol_canon") for v in valid.values())
            bad_props = {i for v in valid.values() for i in v.get("viol_canon", [])}
            c["det_prop"] += det; c["det_crash_only"] += crash and not det; c["fa_tasks"] += fa
            c["bad_props"] += len(bad_props)
            refdet = any(rec.get("valid", True) and rec.get("ref", {}).get("emit") and rec["ref"]["canon_ok"] and not rec["ref"]["put_ok"]
                         for rec in ex.get(t, {}).get("calls", {}).values())
            c["det_ref"] += refdet; c["prop_not_ref"] += det and not refdet; c["ref_not_prop"] += refdet and not det
        lines.append(f"## {split}: {c['tasks']} tasks; tasks with >=1 kept property {c['with_props']}; kept properties {c['props']}, "
                     f"of which violated by canonical on some valid input {c['bad_props']}")
        lines.append(f"  tasks detected by properties alone (valid inputs, PUT violates, canonical satisfies): {c['det_prop']}")
        lines.append(f"  tasks where a property also flags the CORRECT program (canonical violates): {c['fa_tasks']}")
        lines.append(f"  tasks where only a PUT crash would detect (no property): {c['det_crash_only']}")
        lines.append(f"  same input pool, ref oracle: {c['det_ref']} tasks; property-only {c['prop_not_ref']}, ref-only {c['ref_not_prop']}")
    text = "\n".join(lines)
    (out / "report.txt").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    if sys.argv[1:2] == ["worker"]:
        worker(*sys.argv[2:4]); sys.exit()
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=Path, default=ob.RUN)
    ap.add_argument("--oracle", type=Path, default=ob.OUT)
    ap.add_argument("--out", type=Path, default=HERE / "out/property_oracle")
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    main(a.run, a.oracle, a.out, a.workers)
