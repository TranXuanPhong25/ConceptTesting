"""m8 Phase 0 (offline, no LLM): compile every mutant candidate against the buggy checkout and run the bug's trigger
tests plus a smoke set (the developer tests that invoke the focal method) on it.

Runs in the m8 sandbox (dock8.sh: no credentials, no network, d4jproj checkouts read-only). Mutated sources and classes
live only in /scratch (named volume m8scratch): /scratch/mut/<mid>/cls holds each compiled mutant (reused by probe.py).
Classpaths come from `defects4j export -p cp.test` run on a scratch copy of each checkout (export writes into the
checkout and may compile, so it never runs on the shared one).

usage (container, via dock8.sh):
  python3 m8_concept_mutants/phase0.py env    -> out/env.json  (classpaths, trigger tests, smoke tests per method)
  python3 m8_concept_mutants/phase0.py base   -> out/phase0_base.json (target/classes, recompiled original x2, fixed)
  python3 m8_concept_mutants/phase0.py run    -> out/phase0_runs.jsonl (resumable; M8_WORKERS processes, default 6)
"""
import glob, hashlib, json, os, re, shutil, subprocess, sys, time
from multiprocessing import Pool

REPO = "/repo"
D = f"{REPO}/m8_concept_mutants"
OUT = os.environ.get("M8_OUT") or f"{D}/out"  # dock8.sh: /m8out (top-level mount)
CK = f"{REPO}/d4j_proj_base"  # used by env only; everything else reads the same volume at CK2
CK2 = "/d4j"
SCR = "/scratch"
RUNNER = f"{SCR}/runner"
MAX_SMOKE = 40
TEST_TIMEOUT_MS = 10000
JVM = ["java", "-Xmx384m", "-XX:+UseSerialGC", "-XX:TieredStopAtLevel=1", f"-Dm8.timeout={TEST_TIMEOUT_MS}"]


def sh(cmd, cwd=None, timeout=None):
    try:
        for k in range(5):  # transient ENOENT on the checkout volume
            try:
                return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, errors="replace", timeout=timeout)
            except FileNotFoundError:
                if k == 4:
                    raise
                time.sleep(3)
    except subprocess.TimeoutExpired as e:
        return subprocess.CompletedProcess(cmd, 124, (e.stdout or b"").decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or ""), "TIMEOUT")


def load_mutants():
    return [json.loads(l) for l in open(f"{OUT}/mutants.jsonl")]


def load_env():
    """env.json with the checkout paths moved to /d4j (same volume, not nested in the /repo bind mount)."""
    return json.loads(open(f"{OUT}/env.json").read().replace(f"{CK}/", f"{CK2}/"))


# ------------------------------------------------------------------ env
def export_cp(bug, v):
    """(cp.test, root). root = the shared checkout; if it has no compiled classes (Gson_14), a scratch copy compiled by
    `defects4j compile` under /scratch/ck is used instead."""
    tmp = f"{SCR}/env/{bug}_{v}"
    shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
    for _ in range(3):  # the Docker Desktop volume occasionally reports transient errors
        r = subprocess.run(f"tar --exclude=./.git -C {CK}/{bug}/{v} -cf - . | tar -C {tmp} -xf -", shell=True, capture_output=True, text=True)
        if r.returncode == 0:
            break
        print("tar retry", bug, v, r.stderr[-300:], flush=True); time.sleep(20)
    assert r.returncode == 0, (bug, v)
    out = sh(["defects4j", "export", "-p", "cp.test"], cwd=tmp).stdout.strip()
    cp = [p.replace(tmp, f"{CK}/{bug}/{v}") for p in out.split(":") if p]
    inside = [p for p in cp if p.startswith(f"{CK}/{bug}/{v}/") and not p.endswith(".jar")]  # the class and test-class dirs
    root = f"{CK}/{bug}/{v}"
    if not all(os.path.isdir(p) for p in inside):
        root = f"{SCR}/ck/{bug}_{v}"
        shutil.rmtree(root, ignore_errors=True); os.makedirs(os.path.dirname(root), exist_ok=True)
        shutil.move(tmp, root)
        c = sh(["defects4j", "compile"], cwd=root)
        assert c.returncode == 0, (bug, v, c.stderr[-500:])
        cp = [p for p in sh(["defects4j", "export", "-p", "cp.test"], cwd=root).stdout.strip().split(":") if p]
        inside = [p for p in cp if p.startswith(root + "/") and not p.endswith(".jar")]
        print(bug, v, "no compiled classes in the shared checkout: compiled a scratch copy", root, flush=True)
    shutil.rmtree(tmp, ignore_errors=True)
    assert len(inside) >= 2 and all(os.path.isdir(p) for p in inside), (bug, v, inside)
    return [p for p in cp if os.path.exists(p)], root  # D4J also lists optional jars that do not exist


def smoke_tests(rec, ev, name):
    """Class::method of the developer tests that invoke the focal method (the dataset lists names only)."""
    tdir = f"{CK}/{ev['bug']}/buggy/{ev['test_dir']}"
    files = glob.glob(f"{tdir}/**/*.java", recursive=True)
    out = []
    for t in rec["invoking_test_cases"]:
        pat = re.compile(r"void\s+" + re.escape(t["method_name"]) + r"\s*\(")
        for f in files:
            txt = open(f, encoding="utf-8", errors="replace").read()
            if pat.search(txt) and re.search(r"\b" + re.escape(name) + r"\s*\(", txt):
                out.append(os.path.relpath(f, tdir)[:-5].replace("/", ".") + "::" + t["method_name"])
    return sorted(set(out))[:MAX_SMOKE]


def env():
    recs = [json.loads(l) for l in open(f"{REPO}/data/prompts/buggy_source_data_unified_invoked.jsonl")]
    evs = {e["idx"]: e for e in map(json.loads, open(f"{REPO}/m6_agent_oracle/out/evidence.jsonl"))}
    muts = load_mutants()
    bugs = sorted({m["bug"] for m in muts})
    path = f"{OUT}/env.json"
    res = json.load(open(path)) if os.path.exists(path) else {"bugs": {}, "methods": {}}  # resumable (transient ENOENT)
    for b in bugs:
        if b in res["bugs"]:
            continue
        fi = json.load(open(f"{REPO}/data/d4j2_fix_info/{b}/buggy_fix_info.json"))
        (cpb, rb), (cpf, rf) = export_cp(b, "buggy"), export_cp(b, "fixed")
        res["bugs"][b] = {"cp_buggy": cpb, "root_buggy": rb, "cp_fixed": cpf, "root_fixed": rf,
                          "trigger": [f"{t['test_class']}::{t['test_function']}" for t in fi["trigger_tests"]]}
        print(b, len(res["bugs"][b]["cp_buggy"]), res["bugs"][b]["trigger"], flush=True)
        json.dump(res, open(path, "w"), indent=1)
    for m in muts:
        i = m["idx"]
        res["methods"][str(i)] = {"bug": m["bug"], "file": m["file"], "smoke": smoke_tests(recs[i], evs[i], recs[i]["source:source_method_name"])}
        print(i, m["bug"], "smoke tests", len(res["methods"][str(i)]["smoke"]), flush=True)
    json.dump(res, open(path, "w"), indent=1)


# ------------------------------------------------------------------ compile / run helpers
JUNIT = "/defects4j/framework/projects/lib/junit-4.12-hamcrest-1.3.jar"  # appended: some cp.test lists lack JUnit 4 (Cli)


def compile_file(src_bytes, file_rel, cp, out_dir):
    """writes the (mutated) focal file to out_dir/src, compiles it alone against cp into out_dir/cls."""
    shutil.rmtree(out_dir, ignore_errors=True)
    os.makedirs(f"{out_dir}/src"); os.makedirs(f"{out_dir}/cls")
    path = f"{out_dir}/src/{os.path.basename(file_rel)}"
    open(path, "wb").write(src_bytes)
    for enc in ("UTF-8", "ISO-8859-1"):  # a Latin-1 source file fails as UTF-8 with "unmappable character"
        r = sh(["javac", "-nowarn", "-proc:none", "-g", "-encoding", enc, "-d", f"{out_dir}/cls", "-cp", ":".join(cp), path], timeout=180)
        if "unmappable character" not in r.stderr:
            break
    os.remove(path); os.rmdir(f"{out_dir}/src")
    err = next((l for l in r.stderr.splitlines() if "error:" in l), r.stderr.strip()[:200])
    return r.returncode == 0, err[:300]


def cls_md5(cls_dir):
    h = hashlib.md5()
    for f in sorted(glob.glob(f"{cls_dir}/**/*.class", recursive=True)):
        h.update(os.path.relpath(f, cls_dir).encode()); h.update(open(f, "rb").read())
    return h.hexdigest()


def run_tests(tests, cp, cwd):
    """{test: [status, message]} via M8Runner; a JVM that dies or hangs marks the remaining tests."""
    res, todo = {}, list(tests)
    while todo:
        r = sh(JVM + ["-cp", ":".join(cp + [JUNIT]), "M8Runner"] + todo, cwd=cwd, timeout=30 + len(todo) * (TEST_TIMEOUT_MS / 1000 + 1))
        for l in r.stdout.splitlines():
            p = l.split("\t")
            if len(p) >= 3 and p[0] == "M8T" and p[1] in todo:
                res[p[1]] = [p[2], p[3] if len(p) > 3 else ""]
        rest = [t for t in todo if t not in res]
        if rest:  # the JVM died or hung on rest[0]: record it and continue with the others
            res[rest[0]] = ["TIMEOUT" if r.returncode == 124 else "ERROR", ("jvm " + (r.stderr or "")[-200:]).strip()]
            rest = rest[1:]
        todo = rest
    return res


def tests_of(env_, idx):
    m = env_["methods"][str(idx)]
    return list(dict.fromkeys(env_["bugs"][m["bug"]]["trigger"] + m["smoke"]))


# ------------------------------------------------------------------ base
def base():
    e = load_env()
    os.makedirs(RUNNER, exist_ok=True)
    r = sh(["javac", "-nowarn", "-d", RUNNER, "-cp", JUNIT, f"{D}/M8Runner.java"])
    assert r.returncode == 0, r.stderr
    out = {}
    for m in load_mutants():
        i, bug = m["idx"], m["bug"]
        b = e["bugs"][bug]
        src = open(f"{b['root_buggy']}/{m['file']}", "rb").read()
        assert hashlib.md5(src).hexdigest() == m["src_md5"], f"buggy source of {bug} changed since mutate.py"
        ok, err = compile_file(src, m["file"], b["cp_buggy"], f"{SCR}/orig/{i}")
        tests = tests_of(e, i)
        cwd_b, cwd_f = b["root_buggy"], b["root_fixed"]
        rec = {"idx": i, "bug": bug, "compiled": ok, "err": err, "cls_md5": cls_md5(f"{SCR}/orig/{i}/cls") if ok else None,
               "d4j": run_tests(tests, [RUNNER] + b["cp_buggy"], cwd_b),
               "orig": run_tests(tests, [f"{SCR}/orig/{i}/cls", RUNNER] + b["cp_buggy"], cwd_b) if ok else {},
               "orig2": run_tests(tests, [f"{SCR}/orig/{i}/cls", RUNNER] + b["cp_buggy"], cwd_b) if ok else {},
               "fixed": run_tests(tests, [RUNNER] + b["cp_fixed"], cwd_f)}
        out[str(i)] = rec
        trig = b["trigger"]
        print(i, bug, "compiled", ok, err if not ok else "", "| trigger orig:", [rec["orig"].get(t, ["-"])[0] for t in trig],
              "fixed:", [rec["fixed"][t][0] for t in trig], "| d4j==orig", rec["d4j"] == rec["orig"],
              "| flaky", [t for t in tests if rec["orig"].get(t) != rec["orig2"].get(t)], flush=True)
    json.dump(out, open(f"{OUT}/phase0_base.json", "w"), indent=1)


# ------------------------------------------------------------------ run
_E = None


def work(job):
    m, mu = job
    t0 = time.time()
    b = _E["bugs"][m["bug"]]
    src = open(f"{b['root_buggy']}/{m['file']}", "rb").read()
    data = src[:mu["s"]] + mu["repl"].encode() + src[mu["e"]:]
    d = f"{SCR}/mut/{mu['mid']}"
    ok, err = compile_file(data, m["file"], b["cp_buggy"], d)
    res = {k: mu[k] for k in ("mid", "arm", "concept", "op")}
    res.update({"idx": m["idx"], "compiled": ok, "err": "" if ok else err})
    if ok:
        res["cls_md5"] = cls_md5(f"{d}/cls")
        if res["cls_md5"] != _BASE[str(m["idx"])]["cls_md5"]:
            res["tests"] = run_tests(tests_of(_E, m["idx"]), [f"{d}/cls", RUNNER] + b["cp_buggy"], b["root_buggy"])
    else:
        shutil.rmtree(d, ignore_errors=True)
    res["secs"] = round(time.time() - t0, 1)
    return res


def safe_work(job):
    try:
        return work(job)
    except Exception as e:
        return {"mid": job[1]["mid"], "exception": repr(e)[:300]}


def init():
    global _E, _BASE
    _E, _BASE = load_env(), json.load(open(f"{OUT}/phase0_base.json"))


def run():
    init()
    path = f"{OUT}/phase0_runs.jsonl"
    done = {json.loads(l)["mid"] for l in open(path)} if os.path.exists(path) else set()
    jobs = [(m, mu) for m in load_mutants() for mu in m["mutants"] if mu["mid"] not in done and _BASE[str(m["idx"])]["compiled"]]
    print("jobs", len(jobs), "done", len(done), flush=True)
    t0 = time.time()
    with Pool(int(os.environ.get("M8_WORKERS") or 6), initializer=init) as pool, open(path, "a") as f:
        for k, r in enumerate(pool.imap_unordered(safe_work, jobs, chunksize=1), 1):
            if "exception" in r:
                print("not persisted (rerun retries it):", r, flush=True)
                continue
            f.write(json.dumps(r) + "\n"); f.flush()
            if k % 100 == 0:
                print(k, "/", len(jobs), f"{time.time() - t0:.0f}s", flush=True)
    print("done", time.time() - t0)


def checkouts(tag):
    """state of the shared checkouts: main sources unmodified vs HEAD (git diff --quiet) and hashes of the full diff and
    status. Compare out/checkouts_<before>.json with a later tag; Phase 0 mounts them read-only anyway."""
    e, out = load_env(), {}
    evs = {x["bug"]: x for x in map(json.loads, open(f"{REPO}/m6_agent_oracle/out/evidence.jsonl"))}
    for b in sorted(e["bugs"]):
        for v in ("buggy", "fixed"):
            d = f"{CK2}/{b}/{v}"
            g = lambda *a: sh(["git", "--no-optional-locks", *a], cwd=d)
            out[f"{b}/{v}"] = {"src_clean": g("diff", "--quiet", "HEAD", "--", evs[b]["src_dir"]).returncode == 0,
                               "diff_md5": hashlib.md5(g("diff", "HEAD").stdout.encode()).hexdigest(),
                               "status_md5": hashlib.md5(g("status", "--porcelain").stdout.encode()).hexdigest()}
    json.dump(out, open(f"{OUT}/checkouts_{tag}.json", "w"), indent=1)
    print(tag, "checkouts", len(out), "main sources modified:", [k for k, x in out.items() if not x["src_clean"]])


if __name__ == "__main__":
    {"env": env, "base": base, "run": run, "checkouts": lambda: checkouts(sys.argv[2])}[sys.argv[1]]()
