"""Offline quality of the fact generator against HumanEval+ ($0, no LLM). Evaluation-only: reads HumanEval+.

  python3 trickcatcher_linefacts/offline.py [facts_dir]          # all tasks -> out/offline/<n>.json, then report
  python3 trickcatcher_linefacts/offline.py report [facts_dir]

For every fact (concept and placebo) and every HumanEval+ input of the task:
  hit   the input reaches the fact (OUTCOME: cell; STMT: a line runs; MUTANT: PUT and mutant outputs differ;
        placebo OUTCOME: either outcome of the cell)
  fail  the PUT fails that input under the official HumanEval+ assertion
Coverage  = does the tool say anything, and does some failing input reach one of its facts.
Precision = are facts reachable by spec-valid inputs, and P(fail | input hits fact) vs the task's base rate.
"""
import ast, contextlib, io, json, os, statistics as st, subprocess, sys, time
from math import comb
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
HE = REPO / "PBT_EdgeCases/run/data/humaneval.jsonl"
HEP = REPO / "PBT_EdgeCases/run/data/humaneval_plus.jsonl"
PUTS = REPO / "vendor/TrickCatcher/Datasets/EvalPlus/PUTs"
OUT = Path(os.environ.get("OFFLINE_OUT", HERE / "out/offline"))
DESIGN = {22, 33, 111, 122, 123, 139}


def excluded():
    return DESIGN | set(json.load(open(HERE / "out/pilot_tasks.json"))["pilot"])


def skip_pilot():
    return os.environ.get("OFFLINE_SKIP_PILOT", "1") == "1"


def plus_check_src(test):
    tree = ast.parse(test)
    chk = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "check"][0]
    loop = [n for n in chk.body if isinstance(n, ast.For)][0]
    pre = ast.parse("__cur[0] = i").body
    handler = ast.ExceptHandler(type=ast.Name("BaseException", ast.Load()), name="__e",
                                body=ast.parse("__fail(i, __e)").body)
    loop.body = pre + [ast.Try(body=loop.body, handlers=[handler], orelse=[], finalbody=[])]
    ast.fix_missing_locations(tree)
    return compile(tree, "<plus>", "exec")


def worker(n, facts_path, out_path):
    if skip_pilot() and n in excluded():
        raise ValueError(f"task {n}: pilot/design offline evaluation disabled")
    sys.path.insert(0, str(HERE))
    from tracer import HOOKS, call, dcopy, instrument, load_module, same, trace, fact_hit
    from facts import make_mutant

    hep = [r for r in map(json.loads, open(HEP)) if r["task_id"] == f"HumanEval/{n}"][0]
    entry = hep["entry_point"]
    src = (PUTS / f"HumanEval_{n}/put0.py").read_text()
    pg = load_module(src)
    put = pg[entry]
    # per-input labels under the official assertion; `candidate` records the args and runs the PUT under the
    # same deterministic step budget as facts.py
    cur, REC, FAIL, POUT = [None], {}, {}, {}

    def cand(*a, **k):
        REC[cur[0]] = (dcopy(a), dcopy(k))
        stt, val = call(put, (a, k))
        POUT[cur[0]] = (stt, val)
        if stt != "ok":
            raise RuntimeError(stt)
        return val

    g = dict(pg)
    g.update({"__cur": cur, "__fail": lambda i, e: FAIL.__setitem__(i, type(e).__name__), "__name__": "__plus__"})
    with contextlib.redirect_stdout(io.StringIO()):
        exec(plus_check_src(hep["test"]), g)
        g["check"](cand)
    idx = sorted(REC)
    fr = json.load(open(facts_path))
    code, _ = instrument(src)
    iput = load_module(code, HOOKS)[entry]
    groups = {"concept": fr["facts"], "placebo": fr.get("placebo_all", [])}
    mut = {}
    for f in groups["concept"] + groups["placebo"]:
        if f["kind"] == "MUTANT" and f["k"] not in mut:
            try:
                mut[f["k"]] = load_module(f['mutant_src'] if 'mutant_src' in f else make_mutant(src, f["k"])[0])[entry]
            except BaseException:
                mut[f["k"]] = None
    tr = {i: trace(iput, REC[i]) for i in idx}
    mout = {}
    for k, fn in mut.items():
        if fn is not None:
            mout[k] = {i: call(fn, REC[i]) for i in idx}

    def hit(f, i):
        return fact_hit(f, tr[i], POUT[i], mout.get(f.get("k"), {}).get(i))

    res = {"task": n, "n_plus": len(idx), "n_fail": sum(i in FAIL for i in idx)}
    for gname, fs in groups.items():
        res[gname] = [{"fail_hits": sum(hit(f, i) for i in idx if i in FAIL),
                       "pass_hits": sum(hit(f, i) for i in idx if i not in FAIL)} for f in fs]
    json.dump(res, open(out_path, "w"))


def run_all(facts_dir, jobs=12):
    OUT.mkdir(parents=True, exist_ok=True)
    ids = [int(x) for x in (HERE / "tasks.txt").read_text().split()]
    if os.environ.get("OFFLINE_TASKS"):
        selected = {int(n) for n in os.environ["OFFLINE_TASKS"].replace(",", " ").split()}
        ids = [n for n in ids if n in selected]
    if skip_pilot():
        ids = [n for n in ids if n not in excluded()]
    procs = []
    for n in ids:
        o = OUT / f"{n}.json"
        if o.exists():
            continue
        cmd = ["timeout", "-k", "5", "3600", "unshare", "-rn", sys.executable, "-I", __file__, "worker", str(n),
               str(Path(facts_dir) / f"{n}.json"), str(o)]
        procs.append((n, subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)))
        while sum(p.poll() is None for _, p in procs) >= jobs:
            time.sleep(.1)
    for n, p in procs:
        if p.wait() != 0:
            print(f"task {n}: rc={p.returncode} {p.stderr.read()[-200:]}")


def sign_p(b, c):
    m, k = b + c, min(b, c)
    return 1.0 if m == 0 else min(1.0, 2 * sum(comb(m, i) for i in range(k + 1)) / 2 ** m)


def report(facts_dir, exclude):
    sys.path.insert(0, str(HERE))
    from facts import SLOTS, slot

    rows = []
    for o in sorted(OUT.glob("*.json")):
        if int(o.stem) in exclude:
            continue
        r = json.load(open(o))
        if r["task"] in exclude or r["n_fail"] == 0:
            continue
        fr = json.load(open(Path(facts_dir) / f"{r['task']}.json"))
        rows.append((r, fr))
    N = len(rows)
    print(f"tasks: {N} (excluded {len(exclude)}: design + pilot; tasks with 0 failing plus inputs dropped)\n")
    if not N:
        return

    def pf(h):
        t = h["fail_hits"] + h["pass_hits"]
        return h["fail_hits"] / t if t else None

    def sets(r, fr):
        conc = [dict(f, **h) for f, h in zip(fr["facts"], r["concept"])]
        plc = [dict(f, **h) for f, h in zip(fr.get("placebo_all", []), r["placebo"])]
        reached = [f for f in conc if f["reached"]]
        top = [conc[i] for i in fr["top3"]]
        p3 = [p for p in plc if any(p["text"] == q["text"] for q in fr["placebo3"])]
        return {"all concept facts": conc, "fuzz-confirmed facts": reached, "top-3 shown": top,
                "placebo (all covered)": plc, "placebo-3 shown": p3}

    print("COVERAGE")
    have = sum(bool(fr["top3"]) for r, fr in rows)
    print(f"  tasks with >=1 shown fact:                      {have}/{N} ({have / N:.0%})")
    for name in ("fuzz-confirmed facts", "top-3 shown"):
        k = sum(any(f["fail_hits"] > 0 for f in sets(r, fr)[name]) for r, fr in rows)
        ks = sum(any(f["fail_hits"] > 0 and pf(f) >= .5 for f in sets(r, fr)[name]) for r, fr in rows)
        print(f"  bug reached via {name:22s} weak {k}/{N} ({k / N:.0%}), strong (PF>=.5) {ks}/{N} ({ks / N:.0%})")

    print("\nPRECISION (fact level; PF = P(PUT fails | HumanEval+ input hits fact))")
    print(f"  {'set':24s} {'facts':>6s} {'valid-reach':>11s} {'mean PF':>8s} {'base':>6s} {'strong':>7s} "
          f"{'tasks PF>base / <base':>22s}")
    for name in ("all concept facts", "fuzz-confirmed facts", "top-3 shown", "placebo (all covered)",
                 "placebo-3 shown"):
        fs_all, pfs, brs, strong, up, down = 0, [], [], 0, 0, 0
        reach = 0
        for r, fr in rows:
            fs = sets(r, fr)[name]
            br = r["n_fail"] / r["n_plus"]
            fs_all += len(fs)
            hitf = [f for f in fs if pf(f) is not None]
            reach += len(hitf)
            strong += sum(pf(f) >= .5 for f in hitf)
            for f in hitf:
                pfs.append(pf(f))
                brs.append(br)
            if hitf:
                m = st.mean(pf(f) for f in hitf)
                up += m > br
                down += m < br
        print(f"  {name:24s} {fs_all:6d} {reach / max(1, fs_all):11.0%} {st.mean(pfs) if pfs else 0:8.2f} "
              f"{st.mean(brs) if brs else 0:6.2f} {strong / max(1, reach):7.0%} {up:>12d} / {down:<3d} "
              f"p={sign_p(up, down):.2g}")

    print("\nBY KIND (fuzz-confirmed facts)")
    for kind in SLOTS:
        fs = [(f, r) for r, fr in rows for f in sets(r, fr)["fuzz-confirmed facts"]
              if slot(f) == kind]
        hitf = [(f, r) for f, r in fs if pf(f) is not None]
        if not fs:
            continue
        print(f"  {kind:10s} facts {len(fs):4d}  valid-reach {len(hitf) / len(fs):4.0%}  "
              f"mean PF {st.mean(pf(f) for f, _ in hitf) if hitf else 0:.2f}  "
              f"vs base {st.mean(r['n_fail'] / r['n_plus'] for _, r in hitf) if hitf else 0:.2f}  "
              f"strong {sum(pf(f) >= .5 for f, _ in hitf)}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "worker":
        worker(int(a[1]), a[2], a[3])
        sys.exit()
    facts_dir = HERE / "out/facts"
    if a and a[0] == "report":
        facts_dir = Path(a[1]) if len(a) > 1 else facts_dir
    else:
        facts_dir = Path(a[0]) if a else facts_dir
        run_all(facts_dir)
    report(facts_dir, excluded())
