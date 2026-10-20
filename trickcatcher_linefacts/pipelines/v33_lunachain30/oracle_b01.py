"""Re-oracle the inputs of an existing run (default: the v3m2 arms run) post hoc. Lane C of the v4 plan.

o0     the run's own assertions (the LLM saw the PUT code)
b1     B1: expected written from signature + docstring only (no code), 3 samples, emitted only if all 3 agree
b1one  B1 first sample alone (hiding the code, no agreement filter)
ref    B2: 10 reference programs by Qwen with TrickCatcher's DPP prompt (verbatim); keep those that pass the base
       tests; emit only if >=3 survive and all agree (abstain on disagreement / crash / timeout)
judge  B4: where ref abstains and a shown MUTANT fact distinguishes PUT(x) from mutant(x), a spec-only LLM judge
       picks one of the two values (or neither)
+post  B3: drop an assertion whose (input, expected) violates a surviving postcondition; postconditions are
       written by Qwen from the spec (DeCon-style) and kept only if they hold on every base-test (input, output)
dpp,tc B0 reference: TrickCatcher's released GPT-3.5 variants (spec-only DPP rule / PUT-guided TrickCatcher rule)
Canonical solutions only score (canon_ok); nothing feeds back into a run. Base tests are the trusted oracle.

  python3 -B trickcatcher_linefacts/oracle_b01.py collect
  python3 -B trickcatcher_linefacts/oracle_b01.py llm            # B1 + B2 + B3 requests (QWEN_BASE_URL)
  python3 -B trickcatcher_linefacts/oracle_b01.py score          # sandboxed execution, B4 judge requests, report
"""
from __future__ import annotations

# Direct-script workers run with -I: establish this copy's package explicitly.
import sys as _package_sys
from pathlib import Path as _PackagePath
if not __package__:
    _package_here = _PackagePath(__file__).resolve().parent
    _package_sys.path.insert(0, str(_package_here.parents[2]))
    __package__ = "trickcatcher_linefacts.pipelines." + _package_here.name
from .paths import REPO as _REPO, DATA_OUT, CONFIG, dataset_paths

import argparse, ast, collections, hashlib, json, random, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from math import comb
from pathlib import Path

HERE = Path(__file__).resolve().parent

from . import preconditions
from .llm_client import Client, atomic_json

RUN = DATA_OUT / 'gen2_qwen7b_v3m2'
OUT = DATA_OUT / 'oracle_b01'
VARIANTS = Path(CONFIG["B0_VARIANTS"])
HEP = dataset_paths()["oracle_hep"]
SEED = CONFIG["seeds"]["oracle"]
K1, NREF, NPOST = 3, 10, 5
DPP_SHA = {"genprog_dfp_sys": "bdf6e9c7a61ebd5a3c7c297118543e7ad9fd7a435f51f20e4fb9b15dd3f14615",
           "genprog_dfp_usr": "ba4085d3668dc4eb80a6cce6945ac7f3f96797698840ac228502c129830a9e85"}
SYSTEM = "You are an expert software tester."
B1_PROMPT = """Below is the specification of a Python function (its signature and docstring). The implementation is not shown.

```python
{spec}
```

For each call below, write the assertion `assert <call> == <expected>`, where <expected> is the exact value the \
specification requires for that call. Work it out carefully from the specification. Keep each call exactly as given. \
Reply with a single ```python code block containing one assertion per line and nothing else.

{calls}"""
POST_PROMPT = """Below is the specification of a Python function (its signature and docstring).

```python
{spec}
```

Write a symbolic postcondition for this function: exactly one Python `assert` statement that must be true after any \
correct call. Use only the function's parameters and `return_val` (the value the function returns). It must check \
the meaning of the result, not only its type, and it must not re-implement the function. Reply with only that \
assert statement in a ```python code block."""
JUDGE_PROMPT = """Below is the specification of a Python function (its signature and docstring). The implementation is not shown.

```python
{spec}
```

Consider the call `{call}`. Two candidate return values were observed:
A: {a}
B: {b}

Which one does the specification require for this call? Reason briefly, then end with a final line \
`ANSWER: A`, `ANSWER: B`, or `ANSWER: NEITHER`."""


def dpp_templates():
    d = HERE / "tc_templates"
    out = []
    for name, sha in DPP_SHA.items():
        raw = (d / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != sha:
            raise ValueError(f"TrickCatcher template {name} failed SHA256 verification")
        out.append(raw.decode())
    return out


def load_run(run=RUN):
    tasks = json.loads((run / "tasks.json").read_text())
    tasks = {t["task"]: t for t in (tasks["tasks"] if isinstance(tasks, dict) else tasks)}
    rows = [json.loads(l) for l in (run / "eval.jsonl").open()]
    return tasks, rows


def call_of(src, entry):
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == entry:
            return ast.unparse(node)
    return None


def expected_of(src):
    try:
        node = ast.parse(src).body[0].test
    except (SyntaxError, IndexError, AttributeError):
        return None
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
        return ast.unparse(node.comparators[0])
    return None


def code_block(text):
    m = re.search(r"```(?:python|py)?\s*\n(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip()


def collect(run=RUN, out=OUT):
    tasks, rows = load_run(run)
    calls = collections.defaultdict(dict)
    for r in rows:
        for a in r["asserts"]:
            c = call_of(a["src"], tasks[r["task"]]["entry"])
            if c is not None:
                calls[r["task"]].setdefault(c, len(calls[r["task"]]))
    data = {str(t): sorted(c, key=c.get) for t, c in sorted(calls.items())}
    atomic_json(out / "calls.json", data)
    print(f"{len(data)} tasks, {sum(map(len, data.values()))} unique calls")


def chunks(calls, max_calls=10, max_chars=1500):
    group, size = [], 0
    for c in calls:
        if group and (len(group) >= max_calls or size + len(c) > max_chars):
            yield group
            group, size = [], 0
        group.append(c); size += len(c)
    if group:
        yield group


def msgs(user, system=SYSTEM):
    return [dict(role="system", content=system), dict(role="user", content=user)]


def llm(run=RUN, out=OUT, workers=16, stages=("b1", "ref", "post")):
    tasks, _ = load_run(run)
    calls = json.loads((out / "calls.json").read_text())
    client = Client(out / "cache", workers=workers)
    dsys, dusr = dpp_templates()
    jobs = []
    for t, cs in calls.items():
        spec = preconditions.specification(tasks[int(t)])[0]
        if "b1" in stages:
            for i, group in enumerate(chunks(cs)):
                for s in range(K1):
                    jobs.append(dict(stage="b1", task=t, chunk=i, sample=s, calls=group, seed=SEED + int(t) * 1000 + i * 10 + s,
                                     messages=msgs(B1_PROMPT.format(spec=spec, calls="\n".join(group))), temperature=0.7, max_tokens=2048))
        if "ref" in stages:
            for s in range(NREF):
                jobs.append(dict(stage="ref", task=t, sample=s, seed=SEED + 500000 + int(t) * 100 + s, temperature=0.8, max_tokens=1024,
                                 messages=msgs(dusr.replace("{signature_and_doctoring}", spec), system=dsys)))
        if "post" in stages:
            for s in range(NPOST):
                jobs.append(dict(stage="post", task=t, sample=s, seed=SEED + 700000 + int(t) * 100 + s, temperature=0.8, max_tokens=512,
                                 messages=msgs(POST_PROMPT.format(spec=spec))))

    def run_job(j):
        r = client.chat(j["messages"], j["seed"], temperature=j["temperature"], top_p=0.95, max_tokens=j["max_tokens"])
        return dict({k: v for k, v in j.items() if k != "messages"}, text=r["text"])

    with ThreadPoolExecutor(workers) as pool:
        res = list(pool.map(run_job, jobs))
    for stage in stages:
        atomic_json(out / f"{stage}_responses.json", [r for r in res if r["stage"] == stage])
    print({s: sum(r["stage"] == s for r in res) for s in stages})


def b1_expected(out, entry_of):
    exp = collections.defaultdict(lambda: collections.defaultdict(lambda: [None] * K1))
    path = out / "b1_responses.json"
    if not path.exists():
        return {}
    for r in json.loads(path.read_text()):
        wanted = set(r["calls"])
        for line in code_block(r["text"]).splitlines():
            line = line.strip()
            if not line.startswith("assert"):
                continue
            e = expected_of(line)
            call = call_of(line, entry_of(int(r["task"])))
            if e is not None and call in wanted:
                exp[r["task"]][call][r["sample"]] = e
    return {t: dict(v) for t, v in exp.items()}


def by_task(out, stage, parse):
    path = out / f"{stage}_responses.json"
    res = collections.defaultdict(list)
    if path.exists():
        for r in sorted(json.loads(path.read_text()), key=lambda r: r["sample"]):
            v = parse(r["text"])
            if v:
                res[r["task"]].append(v)
    return res


def post_of(text):
    for line in code_block(text).splitlines():
        line = line.strip()
        if line.startswith("assert "):
            try:
                ast.parse(line)
                return line
            except SyntaxError:
                return None
    return None


def variants(kind, task):
    from .paths import DATASET
    if DATASET != "humaneval": return []
    d = VARIANTS / f"{kind}_generated_progs" / f"HumanEval_{task}"
    return [p.read_text() for p in sorted(d.glob("*.py"), key=lambda p: int(p.stem))] if d.exists() else []


def mutant_source(put, k):
    """Source of facts.make_mutant's mutant (it returns compiled code): read the tree it would compile."""
    from . import facts
    facts.compile = lambda tree, *a, **kw: ast.unparse(tree)
    try:
        return facts.make_mutant(put, k)[0]
    finally:
        del facts.compile


def mutants(task_bundle, n):
    out = []
    for m in task_bundle.get("concept_meta", []):
        if m.get("kind") == "MUTANT":
            src = m.get("mutant_src") or mutant_source(task_bundle["put"], m["k"])
            out.append(dict(k=m.get("k"), text=m["text"], src=src))
    return out


# ---------------------------------------------------------------- sandbox worker
def worker(job_path, out_path):
    import copy, doctest, signal

    class TO(Exception):
        pass

    def alarm(*_):
        raise TO()

    signal.signal(signal.SIGALRM, alarm)
    job = json.loads(Path(job_path).read_text())
    entry = job["entry"]

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

    def load(src):
        ns = {"__name__": "__variant__"}
        st, _ = timed(lambda: exec("from typing import *\nimport math\n" + src, ns), 5)
        f = ns.get(entry) if st == "ok" else None
        return f if callable(f) else None

    def passes_base(fn):
        ns = {"__name__": "__base__"}
        st, _ = timed(lambda: (exec(job["base"], ns), ns["check"](fn)), 20)
        return st == "ok"

    def same(a, b):
        try:
            return bool(a == b)
        except BaseException:
            return False

    env = {"__builtins__": __builtins__}
    ev = lambda expr: timed(lambda: eval(expr, dict(env)), 3)
    put, canon = load(job["put"]), load(job["canon"])
    contract = load(job["contract"]) if job.get("contract") else None   # EvalPlus contract: labels only
    params = [a.arg for a in ast.parse(job["spec"]).body[0].args.args]

    # base-test (args, expected) pairs: the trusted oracle for postconditions
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
        return st != "AssertionError"   # other errors do not count as a violation (DeCon: violated assertion)

    posts = [p for p in job["post"] if pairs and all(holds(p, a, e) for a, e in pairs)]
    pools = {}
    for kind in ("dpp", "tc", "ref"):
        fns = [load(src) for src in job[kind]]
        pools[kind] = [f for f in fns if f is not None and passes_base(f)]
    muts = [(m, load(m["src"])) for m in job["mutants"]]
    out = dict(n_variants={k: len(job[k]) for k in ("dpp", "tc", "ref")}, n_survivors={k: len(v) for k, v in pools.items()},
               n_post=len(job["post"]), n_post_kept=len(posts), n_pairs=len(pairs), calls={})
    for call in job["calls"]:
        node = ast.parse(call, mode="eval").body
        st, args = timed(lambda: ([eval(compile(ast.Expression(a), "<a>", "eval"), dict(env)) for a in node.args],
                                  {k.arg: eval(compile(ast.Expression(k.value), "<k>", "eval"), dict(env)) for k in node.keywords}), 3)
        if st != "ok" or args[1]:
            out["calls"][call] = dict(error="args")
            continue
        a = args[0]
        run = lambda f: timed(lambda: f(*copy.deepcopy(a)), 3)
        ps, pv = run(put)
        cs, cv = run(canon)

        def judge(value):
            return dict(emit=True, canon_ok=cs == "ok" and same(cv, value), put_ok=ps == "ok" and same(pv, value),
                        post_ok=all(holds(p, a, value) for p in posts))

        def unanimous(pool, label):
            outs = [run(f) for f in pool]
            good = [v for s, v in outs if s == "ok"]
            if len(pool) >= 3 and len(good) == len(outs) and all(same(good[0], v) for v in good[1:]):
                return judge(good[0])
            return dict(emit=False, why="few" if len(pool) < 3 else "disagree")

        rec = dict(put=ps, canon=cs, valid=contract is None or run(contract)[0] == "ok",
                   dpp=unanimous(pools["dpp"], "dpp"), ref=unanimous(pools["ref"], "ref"))
        outs = [v for s, v in (run(f) for f in pools["tc"]) if s == "ok"]
        diff = [v for v in outs if not (ps == "ok" and same(v, pv))]
        rec["tc"] = judge(max(diff, key=lambda v: sum(same(v, w) for w in diff))) if diff else dict(emit=False, why="agree")
        o0 = {}
        for expr in job["o0"].get(call, []):
            s, v = ev(expr)
            o0[expr] = all(holds(p, a, v) for p in posts) if s == "ok" else True
        rec["o0_post_ok"] = o0
        vals = []
        for expr in job["b1"].get(call, [None] * K1):
            if expr is None:
                vals.append(None); continue
            s, v = ev(expr)
            vals.append((v,) if s == "ok" else None)
        rec["b1one"] = judge(vals[0][0]) if vals and vals[0] is not None else dict(emit=False, why="missing")
        if vals and all(v is not None for v in vals) and all(same(vals[0][0], v[0]) for v in vals[1:]):
            rec["b1"] = judge(vals[0][0])
        else:
            rec["b1"] = dict(emit=False, why="missing" if any(v is None for v in vals) else "disagree")
        if not rec["ref"]["emit"] and ps == "ok":
            for m, f in muts:
                if f is None:
                    continue
                ms, mv = run(f)
                if ms == "ok" and not same(mv, pv):
                    rec["judge_cands"] = dict(fact=m["text"], put=dict(judge(pv), repr=repr(pv)[:300]),
                                              mutant=dict(judge(mv), repr=repr(mv)[:300]))
                    break
        out["calls"][call] = rec
    Path(out_path).write_text(json.dumps(out))


# ---------------------------------------------------------------- scoring
def sign_p(w, l):
    n = w + l
    return 1.0 if not n else min(1.0, 2 * sum(comb(n, i) for i in range(min(w, l) + 1)) / 2 ** n)


def execute(run=RUN, out=OUT, workers=12):
    tasks, rows = load_run(run)
    calls = json.loads((out / "calls.json").read_text())
    hep = {int(r["task_id"].split("/")[1]): r for r in map(json.loads, HEP.open())}
    b1x = b1_expected(out, lambda t: tasks[t]["entry"])
    refs = by_task(out, "ref", lambda txt: code_block(txt))
    posts = by_task(out, "post", post_of)
    o0 = collections.defaultdict(lambda: collections.defaultdict(set))
    for r in rows:
        for a in r["asserts"]:
            c, e = call_of(a["src"], tasks[r["task"]]["entry"]), expected_of(a["src"])
            if c is not None and e is not None:
                o0[str(r["task"])][c].add(e)
    work = out / "exec"; work.mkdir(parents=True, exist_ok=True)
    muts = {t: mutants(tasks[int(t)], int(t)) for t in calls}   # main thread: facts/tracer install signal handlers

    def run_task(t):
        res = work / f"{t}.json"
        if res.exists():
            return
        task, h = tasks[int(t)], hep[int(t)]
        job = dict(entry=task["entry"], put=task["put"], canon=h["prompt"] + h["canonical_solution"], base=task["base"],
                   contract=h["prompt"] + h["contract"] + "\n    pass\n",
                   spec=preconditions.specification(task)[0], dpp=variants("dfp", t), tc=variants("tc", t),
                   ref=refs.get(t, []), post=posts.get(t, []), mutants=muts[t], calls=calls[t],
                   b1=b1x.get(t, {}), o0={c: sorted(v) for c, v in o0[t].items()})
        jp = work / f"{t}.job.json"; jp.write_text(json.dumps(job))
        subprocess.run(["timeout", "-k", "5", "3000", "unshare", "-rn", sys.executable, "-I", "-B", str(Path(__file__)),
                        "worker", str(jp), str(res)], check=False, capture_output=True)

    with ThreadPoolExecutor(workers) as pool:
        list(pool.map(run_task, list(calls)))
    return {t: json.loads((work / f"{t}.json").read_text()) for t in calls if (work / f"{t}.json").exists()}


def judges(ex, run=RUN, out=OUT, workers=16, use_llm=True):
    tasks, _ = load_run(run)
    path = out / "judge_responses.json"
    if path.exists():
        return {(r["task"], r["call"]): r for r in json.loads(path.read_text())}
    if not use_llm:
        return {}
    client = Client(out / "cache", workers=workers)
    jobs = []
    for t, v in ex.items():
        spec = preconditions.specification(tasks[int(t)])[0]
        for i, (call, rec) in enumerate(v["calls"].items()):
            jc = rec.get("judge_cands")
            if jc:
                swap = random.Random(SEED + int(t) * 100000 + i).random() < 0.5
                a, b = (jc["mutant"], jc["put"]) if swap else (jc["put"], jc["mutant"])
                jobs.append(dict(task=t, call=call, swap=swap, seed=SEED + 900000 + int(t) * 1000 + i % 1000,
                                 messages=msgs(JUDGE_PROMPT.format(spec=spec, call=call, a=a["repr"], b=b["repr"]))))

    def run_job(j):
        r = client.chat(j["messages"], j["seed"], temperature=0, top_p=1, max_tokens=512)
        m = re.findall(r"ANSWER:\s*(A|B|NEITHER)", r["text"])
        ans = m[-1] if m else None
        pick = None if ans in (None, "NEITHER") else ("mutant" if (ans == "A") == j["swap"] else "put")
        return dict(task=j["task"], call=j["call"], answer=ans, pick=pick, text=r["text"])

    with ThreadPoolExecutor(workers) as pool:
        res = list(pool.map(run_job, jobs))
    atomic_json(path, res)
    return {(r["task"], r["call"]): r for r in res}


ORACLES = ["o0", "o0+post", "b1one", "b1", "b1+post", "ref", "ref+judge", "full", "dpp", "tc"]   # full = ref+judge+post


def decide(o, rec, jd, o0_expr=None, a=None):
    """(emit, canon_ok, put_ok) for one oracle on one call."""
    if o.startswith("o0"):
        emit = o == "o0" or rec.get("o0_post_ok", {}).get(o0_expr, True)
        return emit, a["canon"] == "ok", a["put"] == "ok"
    if o in ("ref+judge", "full"):
        d = rec.get("ref", {})
        if not d.get("emit") and rec.get("judge_cands") and jd and jd.get("pick"):
            d = rec["judge_cands"][jd["pick"]]
        if not d.get("emit"):
            return False, False, False
        return (o != "full" or d.get("post_ok", True)), d["canon_ok"], d["put_ok"]
    d = rec.get(o.replace("+post", ""), {})
    if not d.get("emit"):
        return False, False, False
    return (not o.endswith("+post") or d.get("post_ok", True)), d["canon_ok"], d["put_ok"]


def score(run=RUN, out=OUT, workers=12, use_llm=True):
    tasks, rows = load_run(run)
    ex = execute(run, out, workers)
    jd = judges(ex, run, out, workers=16, use_llm=use_llm)
    report = []
    for split in ("dev", "pilot", "heldout"):
        rs = [r for r in rows if r["split"] == split and str(r["task"]) in ex]
        if not rs: continue
        K = max(r["sample"] for r in rs) + 1
        arms = sorted({r["arm"] for r in rs})
        stats = {}
        for r in rs:
            entry, t = tasks[r["task"]]["entry"], str(r["task"])
            seen, res = set(), {o: dict(emit=0, fa=0, inv=0, det=False, flag=False) for o in ORACLES}
            for a in r["asserts"]:
                c = call_of(a["src"], entry)
                if c is None or c in seen:
                    continue
                seen.add(c)
                rec = ex[t]["calls"].get(c, {})
                valid = rec.get("valid", True)   # an input violating the EvalPlus contract never detects; it is a false alarm
                for o in ORACLES:
                    emit, cok, pok = decide(o, rec, jd.get((t, c)), expected_of(a["src"]), a)
                    if emit:
                        bad = not cok or not valid
                        res[o]["emit"] += 1; res[o]["fa"] += bad; res[o]["inv"] += not valid
                        res[o]["det"] |= cok and not pok and valid
                        res[o]["flag"] |= bad   # the same test would report a bug in the correct program
            stats[r["task"], r["arm"], r["sample"]] = res
        tids = sorted({k[0] for k in stats})
        report.append(f"\n## {split}: {len(tids)} tasks, K={K}   (cells: detecting samples/K, tasks any-of-K, FA% of "
                      f"assertions incl. contract-invalid inputs, assertions/sample, % of samples that would flag the CORRECT program)")
        for group in (ORACLES[:5], ORACLES[5:]):
            report.append(f"{'arm':12s} " + " ".join(f"{o:>28s}" for o in group))
            for arm in arms:
                cells = []
                for o in group:
                    ss = [stats[k][o] for k in stats if k[1] == arm]
                    det = sum(s["det"] for s in ss) / K
                    anyk = sum(any(stats[t, arm, s][o]["det"] for s in range(K) if (t, arm, s) in stats) for t in tids)
                    em = sum(s["emit"] for s in ss); fa = sum(s["fa"] for s in ss)
                    fp = 100 * sum(s["flag"] for s in ss) / len(ss)
                    cells.append(f"{det:5.1f} {anyk:3d} {100*fa/max(1,em):4.1f}% {em/len(ss):4.1f} {fp:4.0f}%")
                report.append(f"{arm:12s} " + " ".join(f"{c:>28s}" for c in cells))
            inv = {o: sum(stats[k][o]["inv"] for k in stats) for o in group}
            report.append(f"{'':12s} contract-invalid assertions counted as false alarms: {inv}")
        report.append("paired per task (samples detecting) wins/losses sign-p:")
        for a, b in (("gen-concept", "gen-plain"), ("gen-concept", "gen-placebo"), ("concept", "plain"),
                     ("gen-concept", "toolinput"), ("concept", "toolinput"), ("gen-plain", "plain")):
            if a not in arms or b not in arms:
                continue
            parts = []
            for o in ("o0", "b1", "ref", "full", "dpp"):
                w = l = 0
                for t in tids:
                    sa = sum(stats[t, a, s][o]["det"] for s in range(K) if (t, a, s) in stats)
                    sb = sum(stats[t, b, s][o]["det"] for s in range(K) if (t, b, s) in stats)
                    w += sa > sb; l += sa < sb
                parts.append(f"{o} {w}/{l} p={sign_p(w, l):.3g}")
            report.append(f"  {a} vs {b}: " + " | ".join(parts))
    n = collections.Counter()
    for v in ex.values():
        for k in ("dpp", "tc", "ref"):
            n[k + "_variants"] += v["n_variants"][k]; n[k + "_survivors"] += v["n_survivors"][k]
        n["post"] += v["n_post"]; n["post_kept"] += v["n_post_kept"]; n["post_tasks_with_kept"] += v["n_post_kept"] > 0
        for rec in v["calls"].values():
            for o in ("ref", "b1", "dpp"):
                d = rec.get(o, {})
                if d and not d.get("emit"):
                    n[f"{o}_abstain_{d.get('why')}"] += 1
            n["judge_cands"] += "judge_cands" in rec
    picks = collections.Counter(r.get("pick") for r in jd.values())
    correct = sum(1 for (t, c), r in jd.items() if r.get("pick") and ex[t]["calls"][c]["judge_cands"][r["pick"]]["canon_ok"])
    report.append(f"\nprograms / postconditions / abstentions: {dict(n)}")
    report.append(f"judge: {sum(picks.values())} asked, picks {dict(picks)}, picked value correct (canonical) {correct}")
    text = "\n".join(report)
    (out / "report.txt").write_text(text + "\n")
    print(text)


if __name__ == '__main__':
    raise SystemExit('v21 P1 is offline-only; use chain_offline checks.')
