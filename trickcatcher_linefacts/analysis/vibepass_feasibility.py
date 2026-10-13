"""VibePass (Salesforce/vibepass) feasibility check as a TrickCatcher held-out set. CPU only, no LLM.

Inputs (downloaded, untrusted, never imported):
  out/heldout_vibepass/data/vibepass/test.jsonl         HF Salesforce/vibepass @ 36892367 (173 rows)
  out/heldout_vibepass/data/lcb/test*.filtered.jsonl    HF livecodebench/code_generation_lite @ 0fe84c39,
                                                        only the 76 question_ids used by VibePass
Every piece of dataset code (solutions, test_checker, private-test unpickling) runs only in a child
`unshare -rn python3 -I -B <this file> _<mode> ...` with cwd = an empty temp dir, RLIMIT_AS and a
wall-clock timeout per test. Comparison follows LiveCodeBench (functional: json value ==, tuple->list;
stdin: stripped lines, then Decimal token compare).

  python3 -I -B analysis/vibepass_feasibility.py decode   # private tests -> scratch/tests/<qid>.json
  python3 -I -B analysis/vibepass_feasibility.py run      # execute silver/buggy/checker + fuzz
  python3 -I -B analysis/vibepass_feasibility.py report   # counts + usable.json
"""
import base64, collections, hashlib, io, json, os, pickle, random, re, resource, subprocess, sys, tempfile, zlib
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal, InvalidOperation

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out", "heldout_vibepass")
DATA = os.path.join(OUT, "data")
SCR = os.path.join(OUT, "scratch")
ME = os.path.abspath(__file__)
MARK = "@@VIBEPASS_RESULT@@"
TIMEOUT = 10          # seconds per test (LiveCodeBench uses 6); a TLE is retried once with RETRY_TIMEOUT
RETRY_TIMEOUT = 60
HARNESS = 4           # cache version (1: 10 s, no retry, system python, default stack; 2: 2 GB, OOM could pass as empty ok;
                      # 3: program threads killed at exit -> 4: joined, threaded code re-keyed)
# sandbox interpreter: scratch venv (Python 3.12 + sortedcontainers 2.4.0, as in the LiveCodeBench eval env), else ours
PY = os.path.join(OUT, "scratch", "venv", "bin", "python")
PY = PY if os.path.exists(PY) else sys.executable
MEM = 4 << 30
WORKERS = 12
# LiveCodeBench testing_util import_string; `from builtins import *` restores pow etc. after `from math import *`
PREFIX = ("".join(f"from {m} import *\n" for m in "string re datetime collections heapq bisect copy math random statistics itertools functools operator io sys json builtins typing".split())
          + "".join(f"import {m}\n" for m in "string re datetime collections heapq bisect copy math random statistics itertools functools operator io sys json".split()) + "sys.setrecursionlimit(50000)\n")


# ---------------------------------------------------------------- sandbox side (child process)
class _NoGlobals(pickle.Unpickler):
    def find_class(self, module, name):
        raise pickle.UnpicklingError(f"blocked global {module}.{name}")


def _child_decode(path):
    """Decode one filtered LCB row (private tests may be base64+zlib+pickle of a JSON string)."""
    row = json.loads(open(path).read())
    priv = row["private_test_cases"]
    try:
        priv = json.loads(priv)
    except Exception:
        priv = json.loads(_NoGlobals(io.BytesIO(zlib.decompress(base64.b64decode(priv.encode("utf-8"))))).load())
    meta = json.loads(row.get("metadata") or "{}")
    out = dict(question_id=row["question_id"], platform=row["platform"], difficulty=row["difficulty"],
               contest_date=row.get("contest_date"), func_name=meta.get("func_name"),
               public=json.loads(row["public_test_cases"]), private=priv)
    sys.stdout.write(MARK + json.dumps(out))


def _child_fexec(job_path):
    """Functional (LeetCode) call: exec PREFIX+code, call Solution().func(*args)."""
    import threading
    job = json.load(open(job_path))
    res = {}

    def go():
        try:
            ns = {"__name__": "__vibepass__"}
            exec(compile(PREFIX + job["code"], "<solution>", "exec"), ns)
            sys.setrecursionlimit(10 ** 6)
            args = [json.loads(line) for line in job["input"].split("\n")]
            val = getattr(ns["Solution"](), job["func"])(*args)
            res["out"] = json.loads(json.dumps(val))
        except BaseException as e:  # noqa
            res["err"] = f"{type(e).__name__}: {str(e)[:200]}"
    threading.stack_size(512 << 20)
    t = threading.Thread(target=go); t.start(); t.join()
    sys.stdout.flush()
    os.write(1, ("\n" + MARK + json.dumps(res)).encode())


def _child_sexec(prog_path):
    """Stdin (AtCoder) program run as __main__ in a 512 MB-stack thread (deep recursion), exit() honoured."""
    import runpy, threading
    rc = [0]

    def go():
        try:
            orig = sys.setrecursionlimit
            sys.setrecursionlimit = lambda n: orig(max(n, 10 ** 6))  # PREFIX/solution limits never go below 1e6
            sys.setrecursionlimit(0)
            runpy.run_path(prog_path, run_name="__main__")
        except SystemExit as e:
            rc[0] = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
        except BaseException:  # noqa (rc first: printing may itself fail on MemoryError)
            rc[0] = 1
            import traceback; traceback.print_exc()
    threading.stack_size(512 << 20)
    t = threading.Thread(target=go); t.start(); t.join()
    # like a normal interpreter exit: wait for non-daemon threads the program started
    # (`threading.Thread(target=main).start()` without join is common in AtCoder code)
    for th in threading.enumerate():
        if th is not threading.main_thread() and not th.daemon:
            th.join()
    sys.stdout.flush()
    os._exit(rc[0])


def _child_check(job_path):
    """Batch test_checker over many inputs. job: {checker, platform, inputs:[str]}."""
    import signal
    job = json.load(open(job_path))
    ns = {"__name__": "__checker__"}
    exec(compile(PREFIX + job["checker"], "<checker>", "exec"), ns)
    fn = ns["is_valid_test"]
    out = []

    def alarm(*_):
        raise TimeoutError()
    signal.signal(signal.SIGALRM, alarm)
    for s in job["inputs"]:
        signal.alarm(5)
        try:
            if job["platform"] == "leetcode":
                v = fn(*[json.loads(line) for line in s.split("\n")])
            else:
                v = fn(s)
            out.append(v is True)
        except BaseException:  # noqa
            out.append(None)
        finally:
            signal.alarm(0)
    os.write(1, ("\n" + MARK + json.dumps(out)).encode())


# ---------------------------------------------------------------- parent side
def _limits():
    resource.setrlimit(resource.RLIMIT_AS, (MEM, MEM))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def sandbox(argv, stdin_bytes=b"", timeout=TIMEOUT, files=None):
    """Run argv (relative names resolved in a fresh empty temp dir) under unshare -rn."""
    with tempfile.TemporaryDirectory(prefix="vp_") as d:
        for name, content in (files or {}).items():
            with open(os.path.join(d, name), "w") as f:
                f.write(content)
        argv = [os.path.join(d, a) if files and a in files else a for a in argv]
        try:
            p = subprocess.run(["unshare", "-rn", PY, "-I", "-B"] + argv, input=stdin_bytes,
                               cwd=d, capture_output=True, timeout=timeout, preexec_fn=_limits,
                               env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"})
            return dict(rc=p.returncode, out=p.stdout.decode("utf-8", "replace"),
                        err=p.stderr.decode("utf-8", "replace")[-300:], tle=False)
        except subprocess.TimeoutExpired:
            return dict(rc=None, out="", err="", tle=True)


def _marked(res):
    if res["tle"] or MARK not in res["out"]:
        return None
    return json.loads(res["out"].rsplit(MARK, 1)[1])


def run_program(code, platform, func, inp):
    """-> dict(status in ok|re|tle, out, slow); a 10 s TLE is retried once at 60 s."""
    o = _run_program(code, platform, func, inp, TIMEOUT)
    if o["status"] == "tle":
        o = _run_program(code, platform, func, inp, RETRY_TIMEOUT)
        o["slow"] = True
    return o


def _run_program(code, platform, func, inp, timeout):
    if platform == "leetcode":
        job = json.dumps(dict(code=code, func=func, input=inp))
        r = sandbox([ME, "_fexec", "job.json"], files={"job.json": job}, timeout=timeout)
        if r["tle"]:
            return dict(status="tle")
        m = _marked(r)
        if m is None:
            return dict(status="re", err=r["err"])
        if "err" in m:
            return dict(status="re", err=m["err"])
        return dict(status="ok", out=m["out"])
    r = sandbox([ME, "_sexec", "prog.py"], stdin_bytes=inp.encode(), files={"prog.py": PREFIX + code}, timeout=timeout)
    if r["tle"]:
        return dict(status="tle")
    if r["rc"] != 0:
        return dict(status="re", err=r["err"], out=r["out"])
    return dict(status="ok", out=r["out"])


def _lines(s):
    return [x.strip() for x in s.strip().split("\n")]


def _decs(line):
    try:
        return [Decimal(t) for t in line.split()]
    except InvalidOperation:
        return None


def same(platform, got, exp):
    """LiveCodeBench-style equality. got: program output, exp: expected (str for stdin, json str/val for functional)."""
    if platform == "leetcode":
        if isinstance(exp, str):
            try:
                exp = json.loads(exp)
            except Exception:
                return False
        return got == exp
    a, b = _lines(got), _lines(exp)
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        if x == y:
            continue
        dx, dy = _decs(x), _decs(y)
        if dx is None or dy is None or dx != dy:
            return False
    return True


def check_inputs(checker, platform, inputs):
    if not inputs:
        return []
    r = sandbox([ME, "_check", "job.json"], files={"job.json": json.dumps(
        dict(checker=checker, platform=platform, inputs=inputs))}, timeout=60 + 5 * len(inputs))
    m = _marked(r)
    return m if m is not None else [None] * len(inputs)


# ---------------------------------------------------------------- decode
def load_vibepass():
    rows = [json.loads(l) for l in open(os.path.join(DATA, "vibepass", "test.jsonl"))]
    for i, r in enumerate(rows):
        r["idx"] = i
        r["uid"] = f"{r['question_id']}#{i}"
    return rows


def cmd_decode():
    tdir = os.path.join(SCR, "tests"); os.makedirs(tdir, exist_ok=True)
    jobs = []
    for f in sorted(os.listdir(os.path.join(DATA, "lcb"))):
        if not f.endswith(".filtered.jsonl"):
            continue
        for line in open(os.path.join(DATA, "lcb", f)):
            qid = json.loads(line)["question_id"]
            jobs.append((f, qid, line))

    def one(job):
        f, qid, line = job
        r = sandbox([ME, "_decode", "row.json"], files={"row.json": line}, timeout=300)
        m = _marked(r)
        if m is None:
            return qid, f"FAIL {r['err']}"
        m["lcb_file"] = f
        json.dump(m, open(os.path.join(tdir, qid + ".json"), "w"))
        return qid, f"{len(m['public'])} public, {len(m['private'])} private"
    with ThreadPoolExecutor(WORKERS) as ex:
        for qid, msg in ex.map(one, jobs):
            print(qid, msg)
    want = set(json.load(open(os.path.join(SCR, "wanted_ids.json"))))
    have = {f[:-5] for f in os.listdir(tdir)}
    print("missing:", sorted(want - have))


# ---------------------------------------------------------------- fuzz (our own generator; dataset code never runs here)
def _mut_val(v, rng, ints, depth=0):
    if isinstance(v, bool):
        return v
    if isinstance(v, int):
        lo, hi = (min(ints), max(ints)) if ints else (-10, 10)
        return rng.choice([v, v - 1, v + 1, 0, 1, 2, lo, hi, rng.randint(lo, min(hi, lo + 20)),
                           rng.randint(lo, hi)])
    if isinstance(v, str):
        if not v:
            return v
        alpha = sorted(set(v))
        n = rng.choice([len(v), 1, 2, 3, min(len(v), rng.randint(1, 8))])
        return "".join(rng.choice(alpha) for _ in range(n)) if rng.random() < .6 else v[:n]
    if isinstance(v, list):
        if not v:
            return v
        n = min(len(v), rng.choice([1, 2, 3, 4, 5, 6, 8]))
        start = rng.randint(0, len(v) - n)
        part = v[start:start + n] if rng.random() < .5 else v[:n]
        return [_mut_val(x, rng, ints, depth + 1) if rng.random() < .5 else x for x in part]
    return v


def _ints_in(v, acc):
    if isinstance(v, bool):
        return
    if isinstance(v, int):
        acc.append(v)
    elif isinstance(v, list):
        for x in v[:2000]:
            _ints_in(x, acc)


def fuzz_inputs(platform, seeds, rng, n=400):
    seeds = [s for s in seeds if len(s) < 4000]
    out = set()
    if not seeds:
        return []
    if platform == "leetcode":
        parsed = [[json.loads(l) for l in s.split("\n")] for s in seeds]
        ints = []
        for p in parsed:
            _ints_in(p, ints)
        for _ in range(n):
            p = rng.choice(parsed)
            q = [_mut_val(a, rng, ints) if rng.random() < .7 else a for a in p]
            out.add("\n".join(json.dumps(a, separators=(",", ":")) for a in q))
    else:
        for _ in range(n):
            s = rng.choice(seeds)
            lines = [l.split() for l in s.strip("\n").split("\n")]
            toks = [(i, j) for i, l in enumerate(lines) for j, t in enumerate(l)]
            ints = [int(t) for l in lines for t in l if re.fullmatch(r"-?\d+", t)]
            lo, hi = (min(ints), max(ints)) if ints else (0, 10)
            for _k in range(rng.randint(1, 3)):
                if not toks:
                    break
                i, j = rng.choice(toks)
                t = lines[i][j]
                if re.fullmatch(r"-?\d+", t):
                    v = int(t)
                    lines[i][j] = str(rng.choice([v - 1, v + 1, lo, hi, 0, 1, rng.randint(lo, hi)]))
                elif t.isalpha() and len(t) > 1:
                    alpha = sorted(set("".join(x for l in lines for x in l if x.isalpha())))
                    c = list(t); c[rng.randrange(len(c))] = rng.choice(alpha); lines[i][j] = "".join(c)
            out.add("\n".join(" ".join(l) for l in lines) + "\n")
    return sorted(out - set(seeds))


# ---------------------------------------------------------------- run
def _cache():
    path = os.path.join(SCR, "exec_cache.jsonl")
    c = {}
    if os.path.exists(path):
        for line in open(path):
            k, v = json.loads(line)
            # keep older results that ran fine with non-empty output (unaffected by later changes); re-run the rest
            if v.get("harness") == HARNESS or (v["status"] == "ok" and str(v.get("out", "")).strip()):
                c[k] = v
    return c, path


def cmd_run():
    rows = load_vibepass()
    tests = {r["question_id"]: json.load(open(os.path.join(SCR, "tests", r["question_id"] + ".json"))) for r in rows}
    cache, cpath = _cache()
    cf = open(cpath, "a")

    def ex(code, plat, func, inp):
        key = [code, plat, func, inp] + (["thread-join"] if "threading" in code else [])  # re-run harness-4 change
        k = hashlib.sha256(json.dumps(key).encode()).hexdigest()
        if k not in cache:
            cache[k] = dict(run_program(code, plat, func, inp), harness=HARNESS)
            cf.write(json.dumps([k, cache[k]]) + "\n"); cf.flush()
        return cache[k]

    pool = ThreadPoolExecutor(WORKERS)
    res = {}
    # 1) checker validity of official inputs, per row (checkers can differ between rows of one question)
    for r in rows:
        t = tests[r["question_id"]]
        ins = [x["input"] for x in t["public"]] + [x["input"] for x in t["private"]]
        res[r["uid"]] = dict(checker_official=check_inputs(r["test_checker"], r["platform"], ins))
    print("checker done", flush=True)
    # 2) silver + buggy on all official tests
    for kind in ("silver_solution", "buggy_solution"):
        jobs = []
        for r in rows:
            t = tests[r["question_id"]]
            for split in ("public", "private"):
                for i, tc in enumerate(t[split]):
                    jobs.append((r["uid"], split, i, r[kind], r["platform"], t["func_name"], tc))
        outs = list(pool.map(lambda j: ex(j[3], j[4], j[5], j[6]["input"]), jobs))
        for j, o in zip(jobs, outs):
            ok = o["status"] == "ok" and same(j[4], o["out"], j[6]["output"])
            st = "pass" if ok else ("wa" if o["status"] == "ok" else o["status"])
            res[j[0]].setdefault(kind, {}).setdefault(j[1], []).append(st)
            res[j[0]].setdefault(kind + "_out", {}).setdefault(j[1], []).append(o)
        print(kind, "done", flush=True)
    # 3) buggy vs silver on private inputs and on fuzz inputs (rows whose buggy passes all public tests)
    for r in rows:
        x = res[r["uid"]]
        x["buggy_pass_public"] = all(s == "pass" for s in x["buggy_solution"]["public"])
    rng = random.Random(20261013)
    fuzz_jobs = {}
    for r in rows:
        if not res[r["uid"]]["buggy_pass_public"]:
            continue
        t = tests[r["question_id"]]
        seeds = [x["input"] for x in t["public"]] + [x["input"] for x in t["private"]]
        cands = fuzz_inputs(r["platform"], seeds, rng)
        valid = check_inputs(r["test_checker"], r["platform"], cands)
        cands = [c for c, v in zip(cands, valid) if v is True][:80]
        fuzz_jobs[r["uid"]] = (r, cands, sum(v is True for v in valid), len(valid))
    print("fuzz candidates done", flush=True)
    for uid, (r, cands, nvalid, ncand) in fuzz_jobs.items():
        func = tests[r["question_id"]]["func_name"]
        so = list(pool.map(lambda c: ex(r["silver_solution"], r["platform"], func, c), cands))
        bo = list(pool.map(lambda c: ex(r["buggy_solution"], r["platform"], func, c), cands))
        diffs = []
        for c, s, b in zip(cands, so, bo):
            if s["status"] != "ok":
                continue
            if b["status"] == "ok" and same(r["platform"], b["out"], s["out"] if r["platform"] == "leetcode" else s["out"]):
                continue
            diffs.append(dict(input=c[:300], buggy=b["status"], silver_out=str(s["out"])[:200],
                              buggy_out=str(b.get("out"))[:200]))
        res[uid]["fuzz"] = dict(candidates=ncand, valid=nvalid, run=len(cands),
                                silver_ok=sum(s["status"] == "ok" for s in so), diffs=len(diffs),
                                diff_wa=sum(d["buggy"] == "ok" for d in diffs), examples=diffs[:3])
    pool.shutdown()
    for x in res.values():
        for kind in ("silver_solution_out", "buggy_solution_out"):
            for split in x.get(kind, {}):
                x[kind][split] = [dict(status=o["status"], out=str(o.get("out"))[:200], err=o.get("err", "")[:200])
                                  for o in x[kind][split]]
    json.dump(res, open(os.path.join(SCR, "run_results.json"), "w"))
    print("run done")


# ---------------------------------------------------------------- report
def cmd_report():
    rows = load_vibepass()
    tests = {r["question_id"]: json.load(open(os.path.join(SCR, "tests", r["question_id"] + ".json"))) for r in rows}
    res = json.load(open(os.path.join(SCR, "run_results.json")))
    C = collections.Counter
    out, usable = [], []
    for r in rows:
        x, t = res[r["uid"]], tests[r["question_id"]]
        npub, npriv = len(t["public"]), len(t["private"])
        chk = x["checker_official"]
        chk_pub, chk_priv = chk[:npub], chk[npub:]
        sp, spr = x["silver_solution"]["public"], x["silver_solution"]["private"]
        bp, bpr = x["buggy_solution"]["public"], x["buggy_solution"]["private"]
        bso = x["buggy_solution_out"]["private"]
        sso = x["silver_solution_out"]["private"]
        priv_fail = [s for s in bpr if s != "pass"]
        # buggy != silver on a checker-valid private input where silver itself is correct
        priv_diff = [i for i in range(npriv) if chk_priv[i] is True and spr[i] == "pass" and bpr[i] != "pass"]
        priv_diff_wa = [i for i in priv_diff if bpr[i] in ("wa", "re")]
        fz = x.get("fuzz") or {}
        rec = dict(uid=r["uid"], question_id=r["question_id"], row=r["idx"], platform=r["platform"],
                   difficulty=r["difficulty"], func_name=t["func_name"], lcb_file=t["lcb_file"],
                   contest_date=t["contest_date"], n_public=npub, n_private=npriv,
                   checker_valid_public=sum(v is True for v in chk_pub),
                   checker_valid_private=sum(v is True for v in chk_priv),
                   silver_pass_public=all(s == "pass" for s in sp), silver_pass_private=all(s == "pass" for s in spr),
                   silver_private_fail_kinds=dict(C(s for s in spr if s != "pass")),
                   buggy_pass_public=all(s == "pass" for s in bp),
                   buggy_public_fail_kinds=dict(C(s for s in bp if s != "pass")),
                   buggy_fail_private=bool(priv_fail), buggy_private_fail_kinds=dict(C(priv_fail)),
                   n_private_fail=len(priv_fail),
                   private_diff_valid=len(priv_diff), private_diff_valid_wa_re=len(priv_diff_wa),
                   fuzz_valid_run=fz.get("run"), fuzz_diff=fz.get("diffs"), fuzz_diff_wa_re=fz.get("diff_wa"),
                   fuzz_examples=fz.get("examples", []))
        rec["fuzz_candidates"], rec["fuzz_checker_valid"] = fz.get("candidates"), fz.get("valid")
        rec["fuzz_silver_not_ok"] = (fz["run"] - fz["silver_ok"]) if fz else None
        rec["private_fail_frac"] = round(len(priv_fail) / npriv, 3) if npriv else None
        b = r["buggy_solution"]
        # LiveCodeBench's stdin mock: sys.stdin.read() returns the WHOLE input even after input() consumed lines,
        # and output printed by a thread that outlives the wrapped function is lost. Such code is judged wrong
        # by LCB/VibePass although it is right under a real interpreter.
        rec["lcb_mock_hazard"] = r["platform"] == "atcoder" and (
            bool(re.search(r"(?<![\w.])input\(", b) and re.search(r"stdin\.read\(\)|stdin\.buffer\.read\(\)|open\(0\)", b))
            or bool(re.search(r"Thread\(target=\w+\)\.start\(\)", b)))
        rec["differs_on_valid"] = bool(priv_diff) or bool(fz.get("diffs"))
        rec["differs_on_valid_wa_re"] = bool(priv_diff_wa) or bool(fz.get("diff_wa"))
        rec["usable"] = rec["buggy_pass_public"] and rec["differs_on_valid"]
        rec["usable_strict"] = (rec["usable"] and rec["differs_on_valid_wa_re"] and rec["silver_pass_public"]
                                and rec["silver_pass_private"])
        out.append(rec)
    json.dump(dict(source=dict(vibepass="Salesforce/vibepass@36892367f341a1205031724d193bbbd045d995d5",
                               lcb="livecodebench/code_generation_lite@0fe84c3912ea0c4d4a78037083943e8f0c4dd505"),
                   definitions=dict(
                       usable="buggy passes all public tests AND differs from silver (silver output = expected) "
                              "on >=1 test_checker-valid input: a private test where silver passes and buggy fails "
                              "(WA/RE/TLE), or a generated input",
                       usable_strict="usable AND the difference is a wrong answer / runtime error (not only TLE) "
                                     "AND silver passes all public+private tests"),
                   instances=out), open(os.path.join(OUT, "usable.json"), "w"), indent=1)
    # summary
    def cnt(pred, rs=out):
        return sum(1 for o in rs if pred(o))
    pp = [o for o in out if o["buggy_pass_public"]]
    U = [o for o in out if o["usable"]]
    S = [o for o in out if o["usable_strict"]]
    print("rows", len(out), "questions", len({o["question_id"] for o in out}))
    print("platform x difficulty", dict(C((o["platform"], o["difficulty"]) for o in out)))
    print("silver pass public", cnt(lambda o: o["silver_pass_public"]), "private", cnt(lambda o: o["silver_pass_private"]),
          "both", cnt(lambda o: o["silver_pass_public"] and o["silver_pass_private"]))
    print("silver private fail kinds", sum((C(o["silver_private_fail_kinds"]) for o in out), C()))
    print("silver fail rows", sorted({(o["question_id"], o["platform"]) for o in out
                                      if not (o["silver_pass_public"] and o["silver_pass_private"])}))
    print("buggy pass public", len(pp), "fail public kinds", sum((C(o["buggy_public_fail_kinds"]) for o in out
                                                                    if not o["buggy_pass_public"]), C()))
    print(" of those fail >=1 private", cnt(lambda o: o["buggy_fail_private"], pp),
          "kinds", sum((C(o["buggy_private_fail_kinds"]) for o in pp), C()))
    print(" of those fail private only by TLE", cnt(lambda o: o["buggy_fail_private"] and set(o["buggy_private_fail_kinds"]) == {"tle"}, pp))
    print(" differ on valid private", cnt(lambda o: o["private_diff_valid"] > 0, pp),
          "(wa/re)", cnt(lambda o: o["private_diff_valid_wa_re"] > 0, pp))
    print(" differ on fuzz", cnt(lambda o: (o["fuzz_diff"] or 0) > 0, pp), "(wa/re)", cnt(lambda o: (o["fuzz_diff_wa_re"] or 0) > 0, pp),
          "fuzz-only", cnt(lambda o: (o["fuzz_diff"] or 0) > 0 and o["private_diff_valid"] == 0, pp))
    print(" fuzz valid run: total", sum(o["fuzz_valid_run"] or 0 for o in pp),
          "rows with 0 valid", cnt(lambda o: not o["fuzz_valid_run"], pp))
    print("usable", len(U), "questions", len({o["question_id"] for o in U}), dict(C((o["platform"], o["difficulty"]) for o in U)))
    print("usable_strict", len(S), "questions", len({o["question_id"] for o in S}), dict(C((o["platform"], o["difficulty"]) for o in S)))
    fr = sorted(o["private_fail_frac"] for o in U)
    if fr:
        print("usable private-fail fraction quartiles", [fr[int(q * (len(fr) - 1))] for q in (0, .25, .5, .75, 1)])
    print("usable rows per question", sorted(C(o["question_id"] for o in U).values(), reverse=True))
    print("buggy passes ALL public+private (not usable):", [o["uid"] for o in pp if not o["buggy_fail_private"]],
          "of which LCB-mock hazard", sum(o["lcb_mock_hazard"] for o in pp if not o["buggy_fail_private"]))
    print("fuzz: candidates", sum(o["fuzz_candidates"] or 0 for o in pp), "checker-valid", sum(o["fuzz_checker_valid"] or 0 for o in pp),
          "rows where checker accepted every candidate", cnt(lambda o: o["fuzz_candidates"] == o["fuzz_checker_valid"], pp),
          "silver not ok on valid fuzz", [(o["uid"], o["fuzz_silver_not_ok"]) for o in pp if o["fuzz_silver_not_ok"]])
    print("usable by contest date", dict(C(o["contest_date"][:7] < "2024-10" and "<2024-10" or ">=2024-10" for o in U)))
    print("usable leetcode", cnt(lambda o: o["platform"] == "leetcode", U), "questions",
          len({o["question_id"] for o in U if o["platform"] == "leetcode"}),
          "strict leetcode", cnt(lambda o: o["platform"] == "leetcode", S))
    print("checker accepts all official inputs:", cnt(lambda o: o["checker_valid_public"] + o["checker_valid_private"] == o["n_public"] + o["n_private"]),
          "rows; rejects some:", [(o["uid"], o["n_public"] + o["n_private"] - o["checker_valid_public"] - o["checker_valid_private"])
                                   for o in out if o["checker_valid_public"] + o["checker_valid_private"] < o["n_public"] + o["n_private"]])
    print("tests per question: public", sorted(C(len(t["public"]) for t in tests.values()).items()),
          "private min/median/max", (lambda L: (min(L), sorted(L)[len(L) // 2], max(L)))([len(t["private"]) for t in tests.values()]))
    print("lcb files", dict(C(t["lcb_file"] for t in tests.values())))
    # AtCoder wrapping hazards
    at = [r for r in rows if r["platform"] == "atcoder"]
    for name, pat in [("global/nonlocal", r"\b(global|nonlocal)\b"), ("exit()", r"\b(sys\.)?exit\("),
                      ("threading", r"threading"), ("stdin.buffer / open(0)", r"stdin\.buffer|open\(0"),
                      ("__main__ guard", r"__name__")]:
        print("atcoder", name, "silver", sum(bool(re.search(pat, r["silver_solution"])) for r in at),
              "buggy", sum(bool(re.search(pat, r["buggy_solution"])) for r in at), "/", len(at))
    lc = [r for r in rows if r["platform"] == "leetcode"]
    print("leetcode helper outside class (buggy)", sum(bool(re.search(r"^(def|class (?!Solution))", r["buggy_solution"], re.M)) for r in lc),
          "silver", sum(bool(re.search(r"^(def|class (?!Solution))", r["silver_solution"], re.M)) for r in lc), "/", len(lc))
    print("loc buggy median", sorted(len(r["buggy_solution"].splitlines()) for r in rows)[len(rows) // 2],
          "silver median", sorted(len(r["silver_solution"].splitlines()) for r in rows)[len(rows) // 2])


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "_decode":
        _child_decode(sys.argv[2])
    elif mode == "_fexec":
        _child_fexec(sys.argv[2])
    elif mode == "_sexec":
        _child_sexec(sys.argv[2])
    elif mode == "_check":
        _child_check(sys.argv[2])
    else:
        {"decode": cmd_decode, "run": cmd_run, "report": cmd_report}[mode]()
