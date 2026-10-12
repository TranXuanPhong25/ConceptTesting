"""Input-validity filters F1/F2/F3 (PREREG "Input-validity filters"), applied post hoc to an oracle_b01 run.

F1  the task's v3m2 mined validator (lane A) must accept the input; F1b the B5 validator; F4 the concept-guided validator
F2  at least half of the surviving ref programs raise or time out -> invalid
F3  spec-only Qwen judge, 3 samples, majority INVALID -> invalid
Each filter drops an assertion before scoring; filters are reported separately, never combined.
The EvalPlus contract (oracle_b01 rec["valid"]) only measures the filters.

  python3 -B trickcatcher_linefacts/validity_filters.py signals --run out/gen2_qwen7b_v3m2 --oracle out/oracle_b01
  python3 -B trickcatcher_linefacts/validity_filters.py llm     --run ... --oracle ...     # F3 (QWEN_BASE_URL)
  python3 -B trickcatcher_linefacts/validity_filters.py score   --run ... --oracle ...
"""
from __future__ import annotations

import argparse, ast, collections, json, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from trickcatcher_linefacts import oracle_b01 as ob, preconditions
from trickcatcher_linefacts.llm_client import Client, atomic_json

PRECOND = HERE / "out/precond_qwen7b_v2"
# mined validators used as filters: F1 = v3m2 (evidence filter on), F1b = B5 (same prompts, filter off), F4 = concept-guided
VALIDATORS = {"F1": PRECOND, "F1b": HERE / "out/precond_qwen7b_v4", "F4": HERE / "out/precond_qwen7b_f4", "F4b": HERE / "out/precond_qwen7b_f4b",
              # RBCTest step ablation of B5 (rbc_ablation.py): no verifier / no confirmation / neither
              "Rnv": HERE / "out/precond_qwen7b_abl_nover", "Rnc": HERE / "out/precond_qwen7b_abl_noconf",
              "Rnn": HERE / "out/precond_qwen7b_abl_noconf_nover"}
SEED = 20261212 + 900000
FILTERS = ("none", "F1", "F1b", "Rnv", "Rnc", "Rnn", "F4", "F4b", "F2", "F3")
F3_PROMPT = """Below is the specification of a Python function (its signature and docstring). The implementation is not shown.

```python
{spec}
```

For each call below, decide whether its arguments satisfy every input requirement that the specification states or \
clearly implies (types, value ranges, formats, non-empty inputs, and so on). Do not judge the expected output. \
Reply with one line per call, in the same order, exactly `<call> -> VALID` or `<call> -> INVALID`, and nothing else.

{calls}"""


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
        ns = {"__name__": "__ref__"}
        st, _ = timed(lambda: exec("from typing import *\nimport math\n" + src, ns), 5)
        f = ns.get(job["entry"]) if st == "ok" else None
        return f if callable(f) else None

    def passes_base(fn):
        ns = {"__name__": "__base__"}
        st, _ = timed(lambda: (exec(job["base"], ns), ns["check"](fn)), 20)
        return st == "ok"

    valids = {}
    for name, src in job["validators"].items():
        st, fn = timed(lambda: preconditions.load_predicate(src, "valid"), 5) if src else ("missing", None)
        valids[name] = fn if st == "ok" else None
    refs = [f for f in (load(s) for s in job["refs"]) if f is not None and passes_base(f)]
    out = dict(n_refs=len(refs), calls={})
    for call in job["calls"]:
        node = ast.parse(call, mode="eval").body
        st, args = timed(lambda: [eval(compile(ast.Expression(a), "<a>", "eval"), dict(env)) for a in node.args], 3)
        if st != "ok" or node.keywords:
            out["calls"][call] = dict(error="args"); continue
        mined = {}
        for name, fn in valids.items():
            m = timed(lambda: fn(*copy.deepcopy(args)), 1) if fn else ("missing", None)
            mined[name] = m[0] == "ok" and m[1] is True if fn else None   # None: no validator for this task
        crashed = sum(timed(lambda: f(*copy.deepcopy(args)), 3)[0] != "ok" for f in refs)
        out["calls"][call] = dict(mined=mined, ref_crash=crashed)
    Path(out_path).write_text(json.dumps(out))


def signals(run, oracle, out, workers=12):
    tasks, _ = ob.load_run(run)
    calls = json.loads((oracle / "calls.json").read_text())
    refs = ob.by_task(oracle, "ref", ob.code_block)
    work = out / "sig2"; work.mkdir(parents=True, exist_ok=True)

    def one(t):
        res = work / f"{t}.json"
        if res.exists():
            return
        vs = {name: (d / t / "valid.py").read_text() if (d / t / "valid.py").exists() else "" for name, d in VALIDATORS.items()}
        job = dict(entry=tasks[int(t)]["entry"], base=tasks[int(t)]["base"], calls=calls[t], refs=refs.get(t, []), validators=vs)
        jp = work / f"{t}.job.json"; jp.write_text(json.dumps(job))
        subprocess.run(["timeout", "-k", "5", "3000", "unshare", "-rn", sys.executable, "-I", "-B", str(Path(__file__)),
                        "worker", str(jp), str(res)], check=False, capture_output=True)

    with ThreadPoolExecutor(workers) as pool:
        list(pool.map(one, list(calls)))
    print(f"signals: {sum((work / f'{t}.json').exists() for t in calls)}/{len(calls)} tasks")


def llm(run, oracle, out, workers=16):
    tasks, _ = ob.load_run(run)
    calls = json.loads((oracle / "calls.json").read_text())
    client = Client(out / "cache", workers=workers)
    jobs = []
    for t, cs in calls.items():
        spec = preconditions.specification(tasks[int(t)])[0]
        for i, group in enumerate(ob.chunks(cs)):
            for s in range(3):
                jobs.append(dict(task=t, chunk=i, sample=s, calls=group, seed=SEED + int(t) * 1000 + i * 10 + s,
                                 messages=ob.msgs(F3_PROMPT.format(spec=spec, calls="\n".join(group)))))

    def one(j):
        r = client.chat(j["messages"], j["seed"], temperature=0.7, top_p=0.95, max_tokens=2048)
        return dict({k: v for k, v in j.items() if k != "messages"}, text=r["text"])

    with ThreadPoolExecutor(workers) as pool:
        res = list(pool.map(one, jobs))
    atomic_json(out / "f3_responses.json", res)
    print(f"F3 requests: {len(res)}")


def f3_verdicts(out):
    """call -> True if judged invalid by the majority of the 3 samples (missing answer = VALID)."""
    votes = collections.defaultdict(lambda: [0, 0])
    path = out / "f3_responses.json"
    if not path.exists():
        return None
    for r in json.loads(path.read_text()):
        lines = [l.strip().strip("`") for l in r["text"].splitlines() if "->" in l]
        found = {}
        for l in lines:
            c, _, v = l.rpartition("->")
            found[c.strip().strip("`").strip()] = v.strip().upper().startswith("INVALID")
        for i, c in enumerate(r["calls"]):
            bad = found.get(c, None)
            if bad is None and len(lines) == len(r["calls"]):   # same order, call text slightly rewritten
                bad = lines[i].upper().endswith("INVALID")
            votes[(r["task"], c)][0] += bool(bad); votes[(r["task"], c)][1] += 1
    return {k: bad * 2 > n for k, (bad, n) in votes.items()}


def score(run, oracle, out):
    tasks, rows = ob.load_run(run)
    ex = {p.stem: json.loads(p.read_text()) for p in (oracle / "exec").glob("*.json") if not p.name.endswith(".job.json")}
    jpath = oracle / "judge_responses.json"
    jd = {(r["task"], r["call"]): r for r in json.loads(jpath.read_text())} if jpath.exists() else {}
    sig = {p.stem: json.loads(p.read_text()) for p in (out / "sig2").glob("*.json") if not p.name.endswith(".job.json")}
    f3 = f3_verdicts(out)

    def invalid(f, t, c):
        if f == "none":
            return False
        s = sig.get(t, {}); rec = s.get("calls", {}).get(c, {})
        if f in VALIDATORS:
            return rec.get("mined", {}).get(f) is False
        if f == "F2":
            return s.get("n_refs", 0) >= 3 and rec.get("ref_crash", 0) * 2 >= s["n_refs"]
        return bool(f3 and f3.get((t, c)))

    lines = []
    have = {n for s in sig.values() for r in s["calls"].values() for n, v in r.get("mined", {}).items() if v is not None}
    filters = [f for f in FILTERS if (f != "F3" or f3 is not None) and (f not in VALIDATORS or f in have)]
    # filter quality on unique (task, call) inputs, against the EvalPlus contract
    q = {f: collections.Counter() for f in filters}
    revealing = {(str(r["task"]), ob.call_of(a["src"], tasks[r["task"]]["entry"])) for r in rows for a in r["asserts"]
                 if a["canon"] == "ok" and a["put"] != "ok"}
    for t, v in ex.items():
        for c, rec in v["calls"].items():
            if "error" in rec:
                continue
            for f in filters:
                bad = invalid(f, t, c); inv = not rec.get("valid", True)
                q[f]["inputs"] += 1; q[f]["contract_invalid"] += inv
                q[f]["caught"] += bad and inv; q[f]["wrongly_dropped"] += bad and not inv
                q[f]["revealing_dropped"] += bad and not inv and (t, c) in revealing
    lines.append("filter quality on unique inputs (contract = EvalPlus, labels only):")
    for f in filters:
        c = q[f]
        lines.append(f"  {f:4s} dropped invalid {c['caught']}/{c['contract_invalid']}  dropped valid {c['wrongly_dropped']}/"
                     f"{c['inputs'] - c['contract_invalid']}  (valid AND bug-revealing dropped {c['revealing_dropped']})")
    for split in ("dev", "pilot"):
        rs = [r for r in rows if r["split"] == split and str(r["task"]) in ex]
        if not rs:
            continue
        K = max(r["sample"] for r in rs) + 1
        arms = sorted({r["arm"] for r in rs})
        tids = sorted({r["task"] for r in rs})
        lines.append(f"\n## {split}: {len(tids)} tasks, K={K}  cells: detections/sample · FA% · % samples flagging the correct program")
        det = {}
        for f in filters:
            for o in ("o0", "ref", "full"):
                for r in rs:
                    t, e = str(r["task"]), tasks[r["task"]]["entry"]; seen = set(); d = flag = False; em = fa = 0
                    for a in r["asserts"]:
                        c = ob.call_of(a["src"], e)
                        if c is None or c in seen:
                            continue
                        seen.add(c)
                        if invalid(f, t, c):
                            continue
                        rec = ex[t]["calls"].get(c, {}); valid = rec.get("valid", True)
                        emit, cok, pok = ob.decide(o, rec, jd.get((t, c)), ob.expected_of(a["src"]), a)
                        if emit:
                            bad = not cok or not valid
                            em += 1; fa += bad; flag |= bad; d |= cok and not pok and valid
                    det[f, o, r["arm"], r["task"], r["sample"]] = (d, em, fa, flag)
        for o in ("o0", "ref", "full"):
            lines.append(f"oracle {o}:")
            lines.append(f"  {'arm':18s}" + "".join(f"{f:>24s}" for f in filters))
            for arm in arms:
                cells = []
                for f in filters:
                    ss = [det[f, o, arm, t, s] for t in tids for s in range(K) if (f, o, arm, t, s) in det]
                    em = sum(x[1] for x in ss); fa = sum(x[2] for x in ss)
                    cells.append(f"{sum(x[0] for x in ss) / K:5.1f} · {100 * fa / max(1, em):4.1f}% · {100 * sum(x[3] for x in ss) / len(ss):3.0f}%")
                lines.append(f"  {arm:18s}" + "".join(f"{c:>24s}" for c in cells))
            for a, b in (("concept", "plain"), ("concept-toolinput", "toolinput"), ("gen-concept", "gen-plain")):
                if a not in arms or b not in arms:
                    continue
                parts = []
                for f in filters:
                    sa = {t: sum(det[f, o, a, t, s][0] for s in range(K) if (f, o, a, t, s) in det) for t in tids}
                    sb = {t: sum(det[f, o, b, t, s][0] for s in range(K) if (f, o, b, t, s) in det) for t in tids}
                    w = sum(sa[t] > sb[t] for t in tids); l = sum(sa[t] < sb[t] for t in tids)
                    parts.append(f"{f} {w}/{l} p={ob.sign_p(w, l):.3g}")
                lines.append(f"  {a} vs {b}: " + " | ".join(parts))
    text = "\n".join(lines)
    (out / "report.txt").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    if sys.argv[1:2] == ["worker"]:
        worker(*sys.argv[2:4]); sys.exit()
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("signals", "llm", "score"))
    ap.add_argument("--run", type=Path, default=ob.RUN)
    ap.add_argument("--oracle", type=Path, default=ob.OUT)
    ap.add_argument("--out", type=Path, help="default: out/validity_filters/<run dir name>")
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args()
    out = a.out or HERE / "out/validity_filters" / a.run.name
    out.mkdir(parents=True, exist_ok=True)
    {"signals": lambda: signals(a.run, a.oracle, out, a.workers), "llm": lambda: llm(a.run, a.oracle, out, a.workers),
     "score": lambda: score(a.run, a.oracle, out)}[a.cmd]()
