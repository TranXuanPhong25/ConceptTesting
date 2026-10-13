"""Hint ranking from method-visible features (offline, CPU only, no LLM). Plan rank 2 of CONCEPT_WEAKNESS.md (A2).

Pool per dev task = every fuzz-reached v6 code fact of every kind (out/facts_v6, nothing excluded a priori) plus every
v7 specification input-class fact (out/spec_facts_v7). A ranking rule scores each hint from method-visible features
only and shows the top 3. Rules are fitted on EVEN dev task ids and evaluated on ODD ids.

Method-visible features (worker `feat`, sandboxed): PUT source, HumanEval base tests, fuzz inputs regenerated exactly
as facts.py did (same seed, same B5 mined validator), mutants, PUT crashes on fuzz inputs, and the spec-only B2 "ref"
programs Qwen wrote (out/oracle_v7hyb/ref_responses.json, code block extracted as oracle_b01.code_block, kept only if
they pass the base tests, as oracle_b01 does).
Labels (evaluation only, worker `label`, sandboxed): PF = P(PUT fails | HumanEval+ input hits hint) under the official
HumanEval+ assertion. Code-fact labels are read from out/offline_v6_report (offline.py worker); spec-fact labels are
computed here with the same capture as offline.py. A hint is good if PF >= .5. Labels never enter the features.

  python3 -B trickcatcher_linefacts/analysis/hint_rank.py all          # feat + label + analyze
  python3 -B trickcatcher_linefacts/analysis/hint_rank.py analyze      # reuse out/hint_rank/{feat,label}
Outputs: out/hint_rank/feat/<n>.json, out/hint_rank/label/<n>.json, out/hint_rank/results.json, out/hint_rank/tables.md
"""
import ast, json, math, os, random, re, subprocess, sys, time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]          # trickcatcher_linefacts/
REPO = HERE.parent
OUT = HERE / "out/hint_rank"
FACTS = HERE / "out/facts_v6"
LABELS_V6 = HERE / "out/offline_v6_report"
SPEC = HERE / "out/spec_facts_v7"
PRECOND = HERE / "out/precond_qwen7b_v4"
BUNDLE = HERE / "out/tasks_v7_all.json"
REFS = HERE / "out/oracle_v7hyb/ref_responses.json"
HE = REPO / "PBT_EdgeCases/run/data/humaneval.jsonl"
HEP = REPO / "PBT_EdgeCases/run/data/humaneval_plus.jsonl"
PUTS = REPO / "vendor/TrickCatcher/Datasets/EvalPlus/PUTs"
SEED = 20261010
K = 3


def code_block(text):  # identical to oracle_b01.code_block
    m = re.search(r"```(?:python|py)?\s*\n(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip()


def dev_ids():
    sys.path.insert(0, str(HERE))
    import offline
    ids = [int(x) for x in (HERE / "tasks.txt").read_text().split()]
    exc = offline.excluded()
    return [n for n in ids if n not in exc]


# ================================================================ feature worker (method-visible only)
def feat_worker(n, out_path):
    sys.path.insert(0, str(HERE))
    import difflib
    import facts as F
    import spec_facts as S
    from tracer import HOOKS, call, instrument, load_module, run_base, same, trace, fact_hit
    from fuzz_validity import validator

    he = next(r for r in map(json.loads, open(HE)) if r["task_id"] == f"HumanEval/{n}")
    entry = he["entry_point"]
    src = (PUTS / f"HumanEval_{n}/put0.py").read_text()
    fr = json.loads((FACTS / f"{n}.json").read_text())
    bundle = next(t for t in json.loads(BUNDLE.read_text())["tasks"] if t["task"] == n)
    spec = json.loads((SPEC / f"{n}.json").read_text())

    # --- replay facts.main up to the fuzz inputs (same seed, same validator)
    rng = random.Random(F.SEED + n)
    pg = load_module(src)
    put = pg[entry]
    base_args, ok = run_base(put, he["test"], ns=pg)
    code, sites = instrument(src)
    iput = load_module(code, HOOKS)[entry]
    base_lines, base_out = set(), []
    for a in base_args:
        cs, ls, st, val = trace(iput, a)
        base_lines |= ls
        base_out.append((st, val))
    F.CONSTS[:] = sorted({x.value for x in ast.walk(ast.parse(src)) if isinstance(x, ast.Constant)
                          and isinstance(x.value, (int, float)) and not isinstance(x.value, bool)
                          and abs(x.value) < 10 ** 6} - {0, 1, -1})[:12]
    with validator("mined", n, PRECOND) as valid:
        fz = F.fuzz_inputs(base_args, rng, valid, n, {})
    fzt = [trace(iput, a) for a in fz]
    pout = [(t[2], t[3]) for t in fzt]

    # --- spec-only reference programs (B2), kept if they pass the base tests
    refs_txt = sorted((r for r in json.loads(REFS.read_text()) if r["stage"] == "ref" and r["task"] == str(n)),
                      key=lambda r: r["sample"])
    refs = []
    for r in refs_txt:
        s = code_block(r["text"])
        if not s:
            continue
        try:
            ns = load_module("from typing import *\nimport math\n" + s, filename="<ref>")
            fn = ns.get(entry)
        except BaseException:
            continue
        if callable(fn) and run_base(fn, bundle["base"], T=20, record=False, ns=ns)[1] is True:
            refs.append(fn)

    def majority(args):
        if len(refs) < 3:
            return None
        outs = [call(fn, args, T=3.0) for fn in refs]
        good = [v for s, v in outs if s == "ok"]
        groups = []
        for v in good:
            for g in groups:
                if same(g[0], v):
                    g[1] += 1
                    break
            else:
                groups.append([v, 1])
        if not groups:
            return None
        v, c = max(groups, key=lambda g: g[1])
        return (v,) if c > len(refs) / 2 else None

    maj_cache = {}

    def maj(i, args):
        if i not in maj_cache:
            maj_cache[i] = majority(args)
        return maj_cache[i]

    # --- static helpers
    tree = ast.parse(src)
    cmp_lines = sorted({x.lineno for x in ast.walk(tree) if isinstance(x, ast.Compare)})

    def cmp_dist(line):
        return min((abs(line - l) for l in cmp_lines), default=99)

    def rep(a):
        r = repr(a)
        return r[:400]

    base_reps = [rep(a) for a in base_args]

    def nearest_base(a):
        r = rep(a)
        best = max(range(len(base_args)), key=lambda j: difflib.SequenceMatcher(None, r, base_reps[j]).ratio())
        return best

    def witness_args(call_src):
        node = ast.parse(call_src, mode="eval").body
        return (tuple(ast.literal_eval(x) for x in node.args), {k.arg: ast.literal_eval(k.value) for k in node.keywords})

    def bad(st, v, m):  # PUT disagrees with the ref majority m (None = no majority)
        return m is not None and (st != "ok" or not same(v, m[0]))

    def signals(hits, put_out, mut_out=None):
        """hits: list of (fz index or key, args). ref/crash signals over the hit inputs (capped)."""
        hits = hits[:40]
        crash = sum(put_out(i)[0] not in ("ok",) for i, _ in hits)
        n_maj = n_dis = n_fh = n_mbad = 0
        for i, a in hits:
            m = maj(i, a)
            if m is None:
                continue
            n_maj += 1
            ps, pv = put_out(i)
            pb = bad(ps, pv, m)
            n_dis += pb
            if mut_out is not None:
                ms, mv = mut_out(i)
                mb = bad(ms, mv, m)
                n_fh += pb and not mb
                n_mbad += mb and not pb
        out = dict(n_eval=len(hits), crash=crash, n_maj=n_maj, ref_dis=n_dis)
        if mut_out is not None:
            out.update(mut_fh=n_fh, mut_wrong=n_mbad)
        return out

    rows = []
    witness_mismatch = 0
    for idx, f in enumerate(fr["facts"]):
        if not f["reached"]:
            continue
        mfn, mo = None, {}
        if f["kind"] == "MUTANT":
            try:
                mfn = load_module(F.make_mutant(src, f["k"])[0])[entry]
            except BaseException:
                mfn = None
        hit = []
        for i, a in enumerate(fz):
            mout = None
            if f["kind"] == "MUTANT":
                if mfn is None:
                    break
                mo[i] = mout = call(mfn, a)
            if fact_hit(f, fzt[i], pout[i], mout):
                hit.append(i)
        wa = witness_args(f["witness_call"])
        if f["witness"] >= len(fz) or F.call_src(entry, fz[f["witness"]]) != f["witness_call"]:
            witness_mismatch += 1
        w_i = f["witness"] if f["witness"] < len(fz) and F.call_src(entry, fz[f["witness"]]) == f["witness_call"] else None
        wst, wv = pout[w_i] if w_i is not None else call(put, wa)
        nb = nearest_base(wa)
        out_change = not (wst == base_out[nb][0] and (wst != "ok" or same(wv, base_out[nb][1])))
        hits = [(i, fz[i]) for i in ([w_i] if w_i is not None else []) + [i for i in hit if i != w_i]]
        sig = signals(hits, lambda i: pout[i],
                      (lambda i: mo[i] if i in mo else call(mfn, fz[i])) if mfn is not None else None)
        rows.append(dict(src="code", idx=idx, kind=f["kind"], slot=F.slot(f), line=f["line"], block=f.get("block"),
                         tier=f.get("tier", 0), g_demote=bool(f.get("g_demote")), guard_class=f.get("guard_class"),
                         boundary=bool(f.get("boundary")), family=f.get("family"), extended=bool(f.get("extended")),
                         covered_site=f["kind"] != "STMT" and f["line"] in base_lines, cmp_dist=cmp_dist(f["line"]),
                         n_hit=len(hit), hit_frac=len(hit) / max(1, len(fz)), out_change=out_change,
                         witness_crash=wst != "ok", **sig))
    for j, f in enumerate(spec["facts"]):
        c = f["input_class"]
        wa = (tuple(f["witness_args"]), {})
        hit = [i for i, a in enumerate(fz) if not a[1] and c["param"] < len(a[0]) and S.in_class(c["cls"], a[0][c["param"]])]
        wst, wv = call(put, wa)
        nb = nearest_base(wa)
        out_change = not (wst == base_out[nb][0] and (wst != "ok" or same(wv, base_out[nb][1])))
        hits = [("w", wa)] + [(i, fz[i]) for i in hit]
        sig = signals(hits, lambda i: (wst, wv) if i == "w" else pout[i])
        rows.append(dict(src="spec", idx=j, kind="SPEC", slot="SPEC-" + c["cls"], line=None, block=None, tier=0,
                         g_demote=False, guard_class=None, boundary=False, family=c["cls"], extended=False,
                         covered_site=False, cmp_dist=99, n_hit=len(hit) + 1, hit_frac=(len(hit) + 1) / max(1, len(fz) + 1),
                         out_change=out_change, witness_crash=wst != "ok", **sig))
    json.dump(dict(task=n, n_fuzz=len(fz), n_base=len(base_args), n_refs=len(refs), n_refs_raw=len(refs_txt),
                   witness_mismatch=witness_mismatch, top3=fr["top3"], rows=rows), open(out_path, "w"))


# ================================================================ label worker (evaluation only: HumanEval+)
def label_worker(n, out_path):
    sys.path.insert(0, str(HERE))
    import contextlib, io
    import offline
    import spec_facts as S
    from tracer import call, dcopy, load_module
    if n in offline.excluded():
        raise ValueError("pilot/design labels are forbidden")
    hep = next(r for r in map(json.loads, open(HEP)) if r["task_id"] == f"HumanEval/{n}")
    entry = hep["entry_point"]
    src = (PUTS / f"HumanEval_{n}/put0.py").read_text()
    pg = load_module(src)
    put = pg[entry]
    cur, REC, FAIL = [None], {}, {}

    def cand(*a, **k):
        REC[cur[0]] = (dcopy(a), dcopy(k))
        stt, val = call(put, (a, k))
        if stt != "ok":
            raise RuntimeError(stt)
        return val

    g = dict(pg)
    g.update({"__cur": cur, "__fail": lambda i, e: FAIL.__setitem__(i, type(e).__name__), "__name__": "__plus__"})
    with contextlib.redirect_stdout(io.StringIO()):
        exec(offline.plus_check_src(hep["test"]), g)
        g["check"](cand)
    spec = json.loads((SPEC / f"{n}.json").read_text())
    res = []
    for f in spec["facts"]:
        c = f["input_class"]
        h = [i for i, (a, k) in REC.items() if not k and c["param"] < len(a) and S.in_class(c["cls"], a[c["param"]])]
        res.append(dict(fail_hits=sum(i in FAIL for i in h), pass_hits=sum(i not in FAIL for i in h)))
    json.dump(dict(task=n, n_plus=len(REC), n_fail=len(FAIL), spec=res), open(out_path, "w"))


def run_workers(kind, ids, jobs=12, timeout=3600):
    d = OUT / kind
    d.mkdir(parents=True, exist_ok=True)
    env = {"PATH": os.defpath, "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1"}

    def one(n):
        o = d / f"{n}.json"
        if o.exists():
            return
        t0 = time.time()
        r = subprocess.run(["timeout", "-k", "5", str(timeout), "unshare", "-rn", sys.executable, "-I", "-B",
                            str(Path(__file__).resolve()), kind + "-worker", str(n), str(o)],
                           env=env, capture_output=True, text=True)
        if r.returncode:
            (d / f"{n}.err").write_text(r.stderr[-3000:])
            print(f"{kind} {n}: rc={r.returncode}", flush=True)
        else:
            print(f"{kind} {n}: {time.time() - t0:.0f}s", flush=True)

    with ThreadPoolExecutor(jobs) as pool:
        list(pool.map(one, ids))


# ================================================================ analysis
def pf(h):
    d = h["fail_hits"] + h["pass_hits"]
    return h["fail_hits"] / d if d else None


def load_tasks():
    sys.path.insert(0, str(HERE))
    import facts as F
    tasks = []
    for n in dev_ids():
        lab = json.loads((LABELS_V6 / f"{n}.json").read_text())
        if not lab["n_fail"]:
            continue
        fr = json.loads((FACTS / f"{n}.json").read_text())
        ft = json.loads((OUT / "feat" / f"{n}.json").read_text())
        sl = json.loads((OUT / "label" / f"{n}.json").read_text())
        spec = json.loads((SPEC / f"{n}.json").read_text())
        rows = []
        for r in ft["rows"]:
            h = lab["concept"][r["idx"]] if r["src"] == "code" else sl["spec"][r["idx"]]
            p = pf(h)
            r = dict(r, pf=p, good=p is not None and p >= .5, text=(fr["facts"][r["idx"]] if r["src"] == "code" else spec["facts"][r["idx"]])["text"],
                     allowed=r["src"] == "code" and F.display_slot(fr["facts"][r["idx"]]) in F.RANK_SLOTS)
            rows.append(r)
        key = {("code", i): j for j, r in enumerate(rows) if r["src"] == "code" for i in [r["idx"]]}
        pick6 = [key[("code", i)] for i in fr["top3"]]
        pick7 = pick6 or [j for j, r in enumerate(rows) if r["src"] == "spec"][:K]
        tasks.append(dict(n=n, rows=rows, pick6=pick6, pick7=pick7, n_refs=ft["n_refs"], wm=ft["witness_mismatch"],
                          n_plus=lab["n_plus"], n_fail=lab["n_fail"]))
    return tasks


def good_at(t, sel):
    return any(t["rows"][j]["good"] for j in sel)


def exp_random(t, pool, k=K):
    N = len(pool)
    G = sum(t["rows"][j]["good"] for j in pool)
    if N == 0:
        return 0.0
    k = min(k, N)
    return 1 - math.comb(N - G, k) / math.comb(N, k)


# ---- features for the scoring rules
KIND_GROUPS = ["OUTCOME", "STMT", "MUTANT", "MUTANT-X", "BOUND", "NUM", "REL", "SHAPE", "OUTPUT", "LOOP", "LOOP-MAX",
               "DU", "DECISION", "SPEC"]


def kind_of(r):
    return "SPEC" if r["src"] == "spec" else r["slot"]


FEATURE_NAMES = {
    "kind": ["kind=" + k for k in KIND_GROUPS],
    "struct": ["covered_site", "boundary", "tier1(g_demote)", "on_compare_line", "log10(hit_frac)", "out_change_vs_nearest_base"],
    "crash": ["crash_on_hit_input", "crash_frac"],
    "mutref": ["mutant_agrees_ref_put_not", "only_mutant_disagrees_ref"],
    "refdis": ["has_ref_majority", "put_ref_disagree_frac", "put_ref_disagree_any"],
}
GROUP_ORDER = ["kind", "struct", "crash", "mutref", "refdis"]


def x_of(r, use):
    """Feature vector. use: set of feature groups."""
    x = []
    if "kind" in use:
        x += [float(kind_of(r) == k) for k in KIND_GROUPS]
    if "struct" in use:
        x += [float(r["covered_site"]), float(r["boundary"]), float(r["tier"]), float(r["cmp_dist"] == 0),
              math.log10(max(r["hit_frac"], 1e-3)), float(r["out_change"])]
    if "crash" in use:
        x += [float(r["crash"] > 0), r["crash"] / max(1, r["n_eval"])]
    if "mutref" in use:
        x += [float(r.get("mut_fh", 0) > 0), float(r.get("mut_wrong", 0) > 0 and r.get("mut_fh", 0) == 0)]
    if "refdis" in use:
        x += [float(r["n_maj"] > 0), r["ref_dis"] / max(1, r["n_maj"]), float(r["ref_dis"] > 0)]
    return x


def fit_logistic(X, y, w, l2=1e-2, iters=4000, lr=1.0):
    """Weighted L2-regularised logistic regression by gradient descent (weights normalised to sum 1)."""
    import numpy as np
    X = np.asarray(X, float)
    X = np.hstack([X, np.ones((len(X), 1))])
    y = np.asarray(y, float)
    w = np.asarray(w, float)
    w = w / w.sum()
    b = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-X @ b))
        b -= lr * (X.T @ (w * (p - y)) + l2 * np.r_[b[:-1], 0])
    return b


def scorer_logistic(train, use, weighting):
    X, y, w = [], [], []
    for t in train:
        for r in t["rows"]:
            X.append(x_of(r, use))
            y.append(float(r["good"]))
            w.append(1.0 / len(t["rows"]) if weighting == "task" else 1.0)
    b = fit_logistic(X, y, w)
    return (lambda r: float(sum(c * v for c, v in zip(b[:-1], x_of(r, use))) + b[-1])), b


SALT = [0]  # tie-break salt; 0 = reported run, others only for the robustness column


def select(t, score, mode, k=K):
    rng = random.Random(SEED + t["n"] + 7919 * SALT[0])
    order = list(range(len(t["rows"])))
    rng.shuffle(order)
    order.sort(key=lambda j: -score(t["rows"][j]))
    if mode == "plain":
        return order[:k]
    out, used = [], Counter()
    cap = 1 if mode == "kind1" else 2
    for j in order:
        kd = kind_of(t["rows"][j])
        if used[kd] < cap:
            out.append(j)
            used[kd] += 1
        if len(out) == k:
            break
    return out


def cohort(ts, part):
    return [t for t in ts if part == "all" or (t["n"] % 2 == 0) == (part == "even")]


def evaluate_rule(ts, sel_fn):
    sel = {t["n"]: sel_fn(t) for t in ts}
    return {p: sum(good_at(t, sel[t["n"]]) for t in cohort(ts, p)) for p in ("even", "odd", "all")}, sel


def analyze():
    ts = load_tasks()
    even, odd = cohort(ts, "even"), cohort(ts, "odd")
    res = dict(n={p: len(cohort(ts, p)) for p in ("even", "odd", "all")}, rules={}, notes={})
    full = lambda t: list(range(len(t["rows"])))
    code_all = lambda t: [j for j, r in enumerate(t["rows"]) if r["src"] == "code"]
    allowed = lambda t: [j for j, r in enumerate(t["rows"]) if r["allowed"]]
    res["notes"]["witness_mismatch_tasks"] = [t["n"] for t in ts if t["wm"]]
    res["notes"]["refs_ge3_tasks"] = sum(t["n_refs"] >= 3 for t in ts)

    RULE_FNS = {}

    def put(name, sel_fn, desc):
        RULE_FNS[name] = sel_fn
        m, sel = evaluate_rule(ts, sel_fn)
        res["rules"][name] = dict(desc=desc, good=m, sel={str(k): v for k, v in sel.items()})
        return sel

    put("pick_v6", lambda t: t["pick6"], "facts.pick() on v6 code facts (allowed kinds only)")
    put("pick_v7", lambda t: t["pick7"], "pick() + v7 spec facts when no code fact is shown (what v7 prompts used)")
    for nm, pool in (("allowed", allowed), ("code_all", code_all), ("full", full)):
        res["rules"][f"random@3[{nm}]"] = dict(desc=f"expected good@3 of a uniform 3-sample from the {nm} pool",
                                               good={p: round(sum(exp_random(t, pool(t)) for t in cohort(ts, p)), 2)
                                                     for p in ("even", "odd", "all")})
        res["rules"][f"ceiling@3[{nm}]"] = dict(desc=f"some good hint exists in the {nm} pool",
                                                good={p: sum(any(t["rows"][j]["good"] for j in pool(t)) for t in cohort(ts, p))
                                                      for p in ("even", "odd", "all")})

    # ---- per-kind good rates (fact level and task level), all cohorts
    kinds = {}
    for p in ("even", "odd", "all"):
        c = defaultdict(lambda: [0, 0, 0, set(), set()])
        for t in cohort(ts, p):
            for r in t["rows"]:
                k = kind_of(r)
                c[k][0] += 1
                c[k][1] += r["pf"] is not None
                c[k][2] += r["good"]
                c[k][3].add(t["n"])
                if r["good"]:
                    c[k][4].add(t["n"])
        kinds[p] = {k: dict(facts=v[0], scored=v[1], good=v[2], rate=v[2] / v[0], tasks=len(v[3]), good_tasks=len(v[4]))
                    for k, v in sorted(c.items())}
    res["by_kind"] = kinds

    # ---- per-signal good rates (fact level): does the signal separate good from not-good hints?
    def rate(rows, pred):
        s = [r for r in rows if pred(r)]
        return dict(n=len(s), good=sum(r["good"] for r in s), rate=round(sum(r["good"] for r in s) / len(s), 3) if s else None)
    sigs = {
        "crash>0": lambda r: r["crash"] > 0,
        "crash=0": lambda r: r["crash"] == 0,
        "covered_site": lambda r: r["covered_site"],
        "uncovered_site": lambda r: not r["covered_site"],
        "out_change": lambda r: r["out_change"],
        "no_out_change": lambda r: not r["out_change"],
        "hit_frac<=.05": lambda r: r["hit_frac"] <= .05,
        "hit_frac>.05": lambda r: r["hit_frac"] > .05,
        "MUTANT mut_fh>0": lambda r: r["kind"] == "MUTANT" and r.get("mut_fh", 0) > 0,
        "MUTANT mut_fh=0, has majority": lambda r: r["kind"] == "MUTANT" and r.get("mut_fh", 0) == 0 and r["n_maj"] > 0,
        "MUTANT no majority": lambda r: r["kind"] == "MUTANT" and r["n_maj"] == 0,
        "MUTANT mut_wrong only": lambda r: r["kind"] == "MUTANT" and r.get("mut_wrong", 0) > 0 and r.get("mut_fh", 0) == 0,
        "ref_dis>0": lambda r: r["ref_dis"] > 0,
        "ref_dis=0, has majority": lambda r: r["ref_dis"] == 0 and r["n_maj"] > 0,
        "no majority": lambda r: r["n_maj"] == 0,
    }
    res["signals"] = {p: {k: rate([r for t in cohort(ts, p) for r in t["rows"]], f) for k, f in sigs.items()}
                      for p in ("even", "odd", "all")}

    # ---- rules fitted on EVEN tasks only
    configs = {
        "kindrate": ({"kind"},),
        "noref": ({"kind", "struct", "crash"},),
        "noref+mutref": ({"kind", "struct", "crash", "mutref"},),
        "noref+mutref+refdis": ({"kind", "struct", "crash", "mutref", "refdis"},),
    }
    fitted = {}
    for name, (use,) in configs.items():
        best = None
        for weighting in ("task", "fact"):
            score, coef = scorer_logistic(even, use, weighting)
            for mode in ("plain", "kind2", "kind1"):
                g = sum(good_at(t, select(t, score, mode)) for t in even)
                if best is None or g > best[0]:
                    best = (g, weighting, mode, score, coef)
        g, weighting, mode, score, coef = best
        fitted[name] = (use, weighting, mode, coef)
        put(f"LR[{name}]", lambda t, s=score, m=mode: select(t, s, m),
            f"logistic on EVEN facts, features {sorted(use)}, weighting={weighting}, selection={mode} (both chosen on EVEN)")
        names = [nm for g in GROUP_ORDER if g in use for nm in FEATURE_NAMES[g]] + ["intercept"]
        res["rules"][f"LR[{name}]"]["coef"] = {nm: round(float(c), 3) for nm, c in zip(names, coef)}
        res["rules"][f"LR[{name}]"]["feature_groups"] = sorted(use)

    # ---- hand rules (explainable, one decision list, thresholds/ordering chosen from EVEN signal rates)
    rates_even = {k: v["rate"] for k, v in kinds["even"].items()}

    def hand(use_mut, use_dis):
        def score(r):
            s = rates_even.get(kind_of(r), 0)
            s += 1.0 * (r["crash"] > 0)
            if use_mut:
                s += 1.0 * (r.get("mut_fh", 0) > 0) - 0.5 * (r.get("mut_wrong", 0) > 0 and r.get("mut_fh", 0) == 0)
            if use_dis:
                s += 1.0 * (r["ref_dis"] > 0) - 0.5 * (r["ref_dis"] == 0 and r["n_maj"] > 0)
            return s
        return score
    for name, um, ud in (("hand", False, False), ("hand+mutref", True, False), ("hand+mutref+refdis", True, True)):
        best = max(("plain", "kind2", "kind1"), key=lambda m: sum(good_at(t, select(t, hand(um, ud), m)) for t in even))
        put(f"{name}", lambda t, s=hand(um, ud), m=best: select(t, s, m),
            f"score = EVEN per-kind good rate + 1[crash on hit inputs]"
            + (" + 1[mutant agrees with ref majority while PUT does not] - .5[only the mutant disagrees]" if um else "")
            + (" + 1[PUT disagrees with ref majority on a hit input] - .5[majority exists, PUT always agrees]" if ud else "")
            + f"; selection={best} (chosen on EVEN)")

    # ---- tests vs random@3[full] (exact Poisson-binomial tail), win/loss vs pick_v7, tie-break robustness
    def pb_tail(ps, obs):
        dist = [1.0]
        for p in ps:
            nd = [0.0] * (len(dist) + 1)
            for i, q in enumerate(dist):
                nd[i] += q * (1 - p)
                nd[i + 1] += q * p
            dist = nd
        return sum(dist[obs:]) if obs <= len(dist) - 1 else 0.0
    rand_p = {t["n"]: exp_random(t, full(t)) for t in ts}
    for name, body in res["rules"].items():
        if "sel" not in body:
            continue
        body["p_vs_random_full"] = {p: pb_tail([rand_p[t["n"]] for t in cohort(ts, p)], body["good"][p]) for p in ("even", "odd")}
        p7, me = res["rules"]["pick_v7"]["sel"], body["sel"]
        body["vs_pick_v7"] = {p: [sum(good_at(t, me[str(t["n"])]) and not good_at(t, p7[str(t["n"])]) for t in cohort(ts, p)),
                                  sum(not good_at(t, me[str(t["n"])]) and good_at(t, p7[str(t["n"])]) for t in cohort(ts, p))]
                              for p in ("even", "odd")}
    for name, body in list(res["rules"].items()):
        if name in RULE_FNS:
            vals = []
            for salt in range(1, 21):
                SALT[0] = salt
                vals.append({p: sum(good_at(t, RULE_FNS[name](t)) for t in cohort(ts, p)) for p in ("even", "odd")})
            SALT[0] = 0
            body["tiebreak_20"] = {p: dict(mean=sum(v[p] for v in vals) / 20, min=min(v[p] for v in vals), max=max(v[p] for v in vals))
                                   for p in ("even", "odd")}

    # ---- recovery of the 33 weak tasks (CONCEPT_WEAKNESS.md A2)
    weak = json.loads((HERE / "out/analysis_weak/weak_table.json").read_text())
    causes = defaultdict(list)
    for w in weak:
        causes[w["cause"]].append(w["task"])
    res["weak_causes"] = causes
    rec = {}
    for name, body in res["rules"].items():
        if "sel" not in body:
            continue
        rec[name] = {}
        for cause, ids in causes.items():
            got = [n for n in ids if any(t["n"] == n and good_at(t, body["sel"][str(n)]) for t in ts)]
            rec[name][cause] = dict(all=got, odd=[n for n in got if n % 2], odd_total=sum(n % 2 for n in ids))
    res["recovered"] = rec
    # tasks that lose a good hint vs pick_v6
    for name, body in res["rules"].items():
        if "sel" in body:
            p6, me = res["rules"]["pick_v6"]["sel"], body["sel"]
            body["gain_vs_pick_v6"] = {p: dict(
                won=[t["n"] for t in cohort(ts, p) if good_at(t, me[str(t["n"])]) and not good_at(t, p6[str(t["n"])])],
                lost=[t["n"] for t in cohort(ts, p) if not good_at(t, me[str(t["n"])]) and good_at(t, p6[str(t["n"])])])
                for p in ("even", "odd")}
    json.dump(res, open(OUT / "results.json", "w"), indent=1, default=list)
    write_tables(res, ts)


def sign_p(b, c):
    m, k = b + c, min(b, c)
    return 1.0 if m == 0 else min(1.0, 2 * sum(math.comb(m, i) for i in range(k + 1)) / 2 ** m)


def write_tables(res, ts):
    L = [f"# hint_rank tables (generated by analysis/hint_rank.py)", "",
         f"Dev tasks with a failing HumanEval+ input: {res['n']['all']} (even {res['n']['even']}, odd {res['n']['odd']}).",
         f"Tasks with >= 3 surviving ref programs: {res['notes']['refs_ge3_tasks']}. Witness replay mismatches: {res['notes']['witness_mismatch_tasks']}.",
         "", "## good@3", "",
         "p(rand) = exact P(random@3[full] >= observed) (Poisson-binomial over tasks). v6 / v7 = tasks won/lost vs pick_v6 / pick_v7 (sign p). tie20 = mean [min-max] over 20 other tie-break seeds.", "",
         "| Rule | even | odd | all | p(rand) even | p(rand) odd | odd vs v6 | odd vs v7 | tie20 even | tie20 odd | how |", "|---|---:|---:|---:|---:|---:|---|---|---|---|---|"]
    for name, b in res["rules"].items():
        g = b["good"]
        wl = ""
        if "gain_vs_pick_v6" in b:
            w, l = len(b["gain_vs_pick_v6"]["odd"]["won"]), len(b["gain_vs_pick_v6"]["odd"]["lost"])
            wl = f"{w}/{l} (p={sign_p(w, l):.2g})"
        pr = b.get("p_vs_random_full")
        v7 = b.get("vs_pick_v7")
        w7 = f"{v7['odd'][0]}/{v7['odd'][1]} (p={sign_p(*v7['odd']):.2g})" if v7 else ""
        tb = b.get("tiebreak_20")
        tbs = {p: f"{tb[p]['mean']:.1f} [{tb[p]['min']}-{tb[p]['max']}]" if tb else "" for p in ("even", "odd")}
        pre, pro = (f"{pr['even']:.2g}", f"{pr['odd']:.2g}") if pr else ("", "")
        L.append(f"| {name} | {g['even']} | {g['odd']} | {g['all']} | {pre} | {pro} | {wl} | {w7} | {tbs['even']} | {tbs['odd']} | {b['desc']} |")
    L += ["", "## Per-kind good rate (fact level, full pool)", "",
          "| Kind | facts all | good all | rate all | rate even | rate odd | tasks with a good one (all) |", "|---|---:|---:|---:|---:|---:|---:|"]
    for k, v in sorted(res["by_kind"]["all"].items(), key=lambda kv: -kv[1]["rate"]):
        e = res["by_kind"]["even"].get(k, {}).get("rate")
        o = res["by_kind"]["odd"].get(k, {}).get("rate")
        L.append(f"| {k} | {v['facts']} | {v['good']} | {v['rate']:.3f} | {e if e is None else f'{e:.3f}'} | {o if o is None else f'{o:.3f}'} | {v['good_tasks']}/{v['tasks']} |")
    L += ["", "## Signals (fact level good rate)", "", "| Signal | even n | even rate | odd n | odd rate |", "|---|---:|---:|---:|---:|"]
    for k in res["signals"]["all"]:
        e, o = res["signals"]["even"][k], res["signals"]["odd"][k]
        L.append(f"| {k} | {e['n']} | {e['rate']} | {o['n']} | {o['rate']} |")
    L += ["", "## Recovery of the weak tasks (CONCEPT_WEAKNESS.md A2), odd tasks", "",
          "| Rule | " + " | ".join(res["weak_causes"].keys()) + " |", "|---|" + "---|" * len(res["weak_causes"])]
    for name, r in res["recovered"].items():
        L.append(f"| {name} | " + " | ".join(f"{len(v['odd'])}/{v['odd_total']} {v['odd']}" for v in r.values()) + " |")
    L += ["", "## Coefficients (logistic rules)", ""]
    for name, b in res["rules"].items():
        if "coef" in b:
            L.append(f"- {name}: " + ", ".join(f"{k} {v:+.2f}" for k, v in b["coef"].items()))
    (OUT / "tables.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "feat-worker":
        feat_worker(int(a[1]), a[2])
    elif a[0] == "label-worker":
        label_worker(int(a[1]), a[2])
    else:
        OUT.mkdir(parents=True, exist_ok=True)
        if a[0] in ("all", "feat"):
            run_workers("feat", dev_ids())
        if a[0] in ("all", "label"):
            run_workers("label", dev_ids())
        if a[0] in ("all", "analyze"):
            analyze()
