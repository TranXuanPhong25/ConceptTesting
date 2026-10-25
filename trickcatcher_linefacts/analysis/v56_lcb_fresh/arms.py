"""v56 pipeline arms on the fresh LCB cohort (PREREG Amendment 4): certified references, Qwen oracle families
(defn / brute / plain, k = 3), input pool (public + vf.fuzz_inputs tool + Qwen plain generator, Qwen `open` filter),
v49 primary quorum, cap 20, scoring against the certified reference.

  python3 -I -B analysis/v56_lcb_fresh/arms.py ref        # Codex reference + is_valid writer, certified on all tests
  python3 -I -B analysis/v56_lcb_fresh/arms.py generate   # 121 Qwen calls (cached, 1 worker, journaled)
  python3 -I -B analysis/v56_lcb_fresh/arms.py score      # pool -> sandbox execution -> metrics.json

Qwen arms never see the PUT, the reference, the validator or any hidden test. Hidden tests are used only to certify
the reference/validator (scoring instruments). All generated code runs in the vibepass_feasibility sandbox
(unshare -rn, empty cwd, RLIMIT_AS) through this file's `_batch` child mode.
"""
import ast, collections, hashlib, itertools, json, math, os, random, re, subprocess, sys, tempfile, threading, time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import vibepass_feasibility as vf  # noqa: E402
import mine  # noqa: E402

ME = os.path.abspath(__file__)
OUT = os.path.join(mine.OUT, "arms")
ARMS = ("defn", "brute", "plain")
K = 3
CAP_TESTS = 20
CAP_GEN = 300
FUZZ_N = 400
REF_ATTEMPTS = 3
T_PROGRAM, T_PUBLIC, T_PUT, T_REF = 1, 2, 2, 10      # per-call seconds (oracle input / program validity / PUT / ref)
GEN_ORACLE = dict(temperature=0.8, top_p=0.95, max_tokens=1024)
GEN_INPUTS = dict(temperature=0.8, top_p=0.95, max_tokens=2048)
CHUNKS = (200, 25, 1)

# ---- v49 gen.py (verbatim)
SYSTEM = 'You are an expert Python programmer. Reply with exactly one ```python code block and nothing else.'
INSTR = {
    'defn': ('First write the definition concept of the task as comments: `# ENUMERATE:` the candidate objects the '
             'statement quantifies over (all subsets, subarrays, pairs, splits, orders, values, ...), `# CHECK:` the '
             'condition the statement imposes on each candidate, `# AGGREGATE:` how the answer is formed from the '
             'candidates that pass. Then write a brute-force implementation that follows this definition literally. '
             'It only has to be correct on small inputs: do not optimise, no shortcuts or clever formulas.'),
    'brute': ('Write a brute-force implementation that follows the problem statement literally. It only has to be '
              'correct on small inputs: do not optimise, no shortcuts or clever formulas.'),
    'plain': 'Write a correct implementation of the function.',
}
# ---- v53 smallscope.py `plain` generator and validity.py `open` checker (verbatim)
GEN_SHARED = ('Each input is a tuple of the arguments in signature order (a 1-tuple when there is one parameter). Use '
              'only builtins and itertools; deterministic; no I/O, randomness or global state. Only the function '
              'inputs() and helpers; do not solve the problem.')
GEN_INSTR = ('Define inputs() returning between 100 and 300 distinct small valid inputs most likely to reveal a bug in a '
             'plausible but incorrect solution. ' + GEN_SHARED)
CHK_SHARED = ('Only conditions the caller must guarantee about the inputs; never conditions on the answer. Write each '
              'check as a separate module-level function check_1, check_2, ... (unique names) with exactly the '
              'parameters of the signature, returning a bool that is True exactly when its condition holds. Use only '
              'builtins; no imports, global state, I/O or parameter mutation; guard types and operations so a check '
              'never raises.')
CHK_INSTR = ('List every condition the specification places on the inputs: types, ranges, lengths, allowed characters '
             'or elements, and relations between parameters. Use one atomic condition per check. Include only what the '
             'statement states or necessarily implies (for example, a length cannot be negative; an index must lie '
             'within its sequence); reject guesses and merely plausible restrictions. Precede each check with a '
             'comment `# <condition>`. ' + CHK_SHARED)

# ---- Codex scoring instruments (never shown to Qwen arms)
REF_PROMPT = ("Solve this LeetCode problem in Python 3. Do not run any commands, read any files or use any tools; "
              "answer from the text below only. Reply with exactly one ```python code block containing the complete "
              "class Solution from the starter code, correct for every input allowed by the constraints and efficient "
              "enough for the largest ones.\n\n### Question:\n{q}\n\n### Starter code:\n```python\n{s}\n```\n")
VAL_PROMPT = ("Do not run any commands, read any files or use any tools; answer from the text below only. Write a "
              "Python 3 module-level function `is_valid({params})` that returns True exactly when the arguments "
              "satisfy every condition the problem statement (including its Constraints section) places on the "
              "inputs, and False otherwise. Never raise; no imports beyond the standard library; no I/O. Reply with "
              "exactly one ```python code block.\n\n### Question:\n{q}\n\n### Starter code:\n```python\n{s}\n```\n")


def sha(s):
    return mine.sha(s)


def code_block(text):
    """v7 oracle_b01.code_block (v49/v53 rule): first fenced block, else the whole text."""
    m = re.search(r"```(?:python|py)?\s*\n(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip()


def canon(inp):
    return "\n".join(json.dumps(json.loads(line), separators=(",", ":")) for line in inp.split("\n"))


def signature(starter, func):
    """`func(a: T, ...) -> R` from the starter's Solution method (self removed)."""
    tree = ast.parse(starter.rstrip() + "\n        pass\n")
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Solution")
    fn = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == func)
    args = [a for a in fn.args.args if a.arg != "self"]
    params = ", ".join(a.arg + (": " + ast.unparse(a.annotation) if a.annotation else "") for a in args)
    ret = " -> " + ast.unparse(fn.returns) if fn.returns else ""
    return f"{func}({params}){ret}", [a.arg for a in args]


def task_view(p):
    t = p["_t"]
    sig, names = signature(t["starter_code"], t["func_name"])
    base = "\n".join(f"assert {t['func_name']}({', '.join(repr(json.loads(l)) for l in tc['input'].split(chr(10)))}) "
                     f"== {json.loads(tc['output'])!r}" for tc in t["public"])
    return dict(spec=t["question_content"], base=base, signature=sig, params=names)


def oracle_messages(task, arm):
    user = (f"Problem statement:\n{task['spec']}\n\nPublic tests (the function must pass them):\n{task['base']}\n\n"
            f"Write a module-level Python function with exactly this signature (plus any imports it needs):\n"
            f"def {task['signature']}:\n\n{INSTR[arm]}")
    return [dict(role="system", content=SYSTEM), dict(role="user", content=user)]


def input_messages(task, kind):
    user = (f"Problem statement:\n{task['spec']}\n\nPublic tests (valid inputs):\n{task['base']}\n\n"
            f"Function signature:\ndef {task['signature']}:\n\n{GEN_INSTR if kind == 'inputs' else CHK_INSTR}")
    return [dict(role="system", content=SYSTEM), dict(role="user", content=user)]


def jobs(p):
    """(kind, index, request body) for one problem; problem-major, arms interleaved per sample index."""
    task, qid = task_view(p), p["question_id"]
    out = []
    for i in range(K):
        for arm in ARMS:
            seed = int(sha(f"v56/{qid}/{arm}/{i}")[:8], 16)
            out.append((arm, i, dict(model=mine.MODEL, messages=oracle_messages(task, arm), seed=seed, **GEN_ORACLE)))
    for kind in ("inputs", "checks"):
        seed = int(sha(f"v56/{qid}/{kind}/0")[:8], 16)
        out.append((kind, 0, dict(model=mine.MODEL, messages=input_messages(task, kind), seed=seed, **GEN_INPUTS)))
    return [(k, i, json.dumps(b, sort_keys=True)) for k, i, b in out]


def cohort():
    man = mine.load_manifest()
    by = {p["question_id"]: p for p in man["problems"]}
    rows = json.load(open(os.path.join(mine.OUT, "cohort.json")))
    for r in rows:
        if sha(r["buggy_solution"]) != r["code_sha256"]:
            raise SystemExit("cohort PUT hash mismatch " + r["question_id"])
        by[r["question_id"]]["put"] = r["buggy_solution"]
    return [by[r["question_id"]] for r in rows]


# ---------------------------------------------------------------- sandbox child
class _Timeout(BaseException):
    pass


def _child_batch(path):
    """Sandbox supervisor: every input (and the generator call) runs in its own forked process (fresh module
    namespace, sys.modules, builtins), stdout/stderr -> /dev/null, own process group killed afterwards. The only
    result channel is the supervisor's original stdout, written once at the end."""
    import resource, select, signal
    if os.environ.get("V56_STACK") != "1":   # re-exec once so the main thread gets a large C stack
        soft, hard = resource.getrlimit(resource.RLIMIT_STACK)
        want = 512 << 20 if hard == resource.RLIM_INFINITY else min(512 << 20, hard)
        resource.setrlimit(resource.RLIMIT_STACK, (want, hard))
        os.environ["V56_STACK"] = "1"
        os.execv(sys.executable, [sys.executable, "-I", "-B", ME, "_batch", path])
    job = json.load(open(path))
    out_fd = os.dup(1)
    null = os.open(os.devnull, os.O_RDWR)
    for fd in (0, 1, 2):
        os.dup2(null, fd)
    exec(compile(vf.PREFIX, "<prefix>", "exec"), {"__name__": "__prefix__"})   # warm stdlib imports before forking

    def alarm(*_):
        raise _Timeout()
    signal.signal(signal.SIGALRM, alarm)

    def timed(fn, seconds):
        signal.setitimer(signal.ITIMER_REAL, seconds)
        try:
            return fn()
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)

    def forked(task, limit):
        r, w = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(r)
            os.close(out_fd)   # the supervisor's result channel is never reachable from program code
            os.setpgid(0, 0)
            try:
                data = json.dumps(task()).encode()
            except BaseException as e:  # noqa
                data = json.dumps(["crash", type(e).__name__]).encode()
            view = memoryview(data)
            while view:
                view = view[os.write(w, view):]
            os._exit(0)
        os.close(w)
        chunks, deadline, timed_out = [], time.monotonic() + limit, False
        while True:
            left = deadline - time.monotonic()
            if left <= 0 or not select.select([r], [], [], left)[0]:
                timed_out = True
                break
            b = os.read(r, 1 << 20)
            if not b:
                break
            chunks.append(b)
        os.close(r)
        for kill in (lambda: os.killpg(pid, 9), lambda: os.kill(pid, 9)):
            try:
                kill()
            except (ProcessLookupError, PermissionError):
                pass
        os.waitpid(pid, 0)
        if timed_out:
            return ["timeout"]
        try:
            return json.loads(b"".join(chunks))
        except ValueError:
            return ["crash"]

    mode, func = job["mode"], job.get("func")
    try:
        code = compile(vf.PREFIX + job["code"], "<program>", "exec")
    except BaseException as e:  # noqa
        code, load_error = None, type(e).__name__

    def load():
        ns = {"__name__": "__v56__"}
        timed(lambda: exec(code, ns), 10)
        sys.setrecursionlimit(10 ** 6)
        return ns

    def gen_task():
        try:
            ns = load()
        except BaseException as e:  # noqa
            return dict(status="load:" + type(e).__name__)
        try:
            vals = timed(lambda: list(itertools.islice(ns["inputs"](), 2000)), 20)
        except BaseException as e:  # noqa
            return dict(status="timeout" if isinstance(e, _Timeout) else "exception:" + type(e).__name__)
        items = []
        for v in vals:
            try:
                items.append([json.dumps(a, separators=(",", ":")) for a in v] if isinstance(v, tuple) else None)
            except (TypeError, ValueError, RecursionError):
                items.append(None)
        return dict(status="ok", items=items)

    def input_task(s):
        def task():
            try:
                ns = load()
            except BaseException as e:  # noqa
                return ["load", type(e).__name__]
            args = [json.loads(line) for line in s.split("\n")]
            try:
                if mode == "check":
                    fns = ([ns["is_valid"]] if callable(ns.get("is_valid")) else []) if job["check"] == "is_valid" \
                        else [ns[n] for n in sorted((n for n in ns if re.fullmatch(r"check_\d+", n) and callable(ns[n])),
                                                    key=lambda n: int(n[6:]))]
                    if not fns:
                        return ["load", "no_checks"]
                    return ["ok", timed(lambda: all(f(*args) is True for f in fns), 1)]
                fn = ns.get(func)
                if not callable(fn) and "Solution" in ns:
                    fn = getattr(ns["Solution"](), func, None)
                val = timed(lambda: fn(*args), job["per_call"])
                return ["ok", json.loads(json.dumps(val))]
            except _Timeout:
                return ["timeout"]
            except BaseException as e:  # noqa
                return ["exception", type(e).__name__]
        return task

    if code is None:
        res = dict(status="load:" + load_error) if mode == "gen" else [["load", load_error]] * len(job["inputs"])
    elif mode == "gen":
        res = forked(gen_task, 10 + 20 + 5)
    else:
        res = [forked(input_task(s), 10 + job["per_call"] + 5) for s in job["inputs"]]
    data = memoryview(json.dumps(res).encode())
    while data:
        data = data[os.write(out_fd, data):]


# ---------------------------------------------------------------- parent execution
EXEC = os.path.join(OUT, "exec")
SLOTS = threading.BoundedSemaphore(vf.WORKERS)   # at most 12 sandboxes at once (16 cores): wall-clock limits stay fair
HARNESS = "v56-arms-4"   # cache-key fingerprint: bump on any change of child/sandbox semantics
_LOCKS, _LOCKS_GUARD = collections.defaultdict(threading.Lock), threading.Lock()
MAX_RESULT = 256 << 20


def _symlink_roots(path):
    """Install roots (two levels up) of every hop of an interpreter symlink chain."""
    roots, p = set(), path
    for _ in range(16):
        roots.add(os.path.dirname(os.path.dirname(os.path.abspath(p))))
        if not os.path.islink(p):
            break
        t = os.readlink(p)
        p = t if os.path.isabs(t) else os.path.join(os.path.dirname(p), t)
    roots.add(os.path.dirname(os.path.dirname(os.path.realpath(path))))
    return roots


UV_PY = os.path.realpath(vf.PY)
RO = sorted({"/usr", ME, os.path.abspath(mine.__file__), os.path.abspath(vf.__file__)} | _symlink_roots(vf.PY))


def _bwrap(job_dir, timeout):
    """bubblewrap: no network, own user/pid/ipc/uts/cgroup namespaces, read-only root (tmpfs with read-only binds of
    /usr, the interpreter and the 3 runner files, the job dir read-only at /job); no writable path at all, no out/.
    The whole process tree is killed on timeout. Returns (tle, parsed stdout or None)."""
    argv = ["bwrap", "--unshare-all", "--die-with-parent", "--new-session", "--proc", "/proc", "--dev", "/dev",
            "--symlink", "usr/lib", "/lib", "--symlink", "usr/lib", "/lib64", "--symlink", "usr/bin", "/bin"]
    for path in RO:
        argv += ["--ro-bind", path, path]
    argv += ["--ro-bind", job_dir, "/job", "--remount-ro", "/dev", "--remount-ro", "/", "--chdir", "/job", "--clearenv",
             "--setenv", "PATH", "/usr/bin", "--setenv", "LANG", "C.UTF-8",
             vf.PY, "-I", "-B", ME, "_batch", "/job/job.json"]
    p = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                         preexec_fn=vf._limits, start_new_session=True)
    box = []
    reader = threading.Thread(target=lambda: box.append(p.stdout.read(MAX_RESULT + 1)), daemon=True)
    reader.start()
    try:
        p.wait(timeout=timeout)
        tle = False
    except subprocess.TimeoutExpired:
        tle = True
    try:
        os.killpg(p.pid, 9)
    except ProcessLookupError:
        pass
    p.wait()
    reader.join(5)
    out = box[0] if box else b""
    p.stdout.close()
    if tle or p.returncode != 0 or len(out) > MAX_RESULT:   # abnormal supervisor exit: never accept its output
        return tle, None
    try:
        return False, json.loads(out)
    except ValueError:
        return False, None


def _valid_outputs(m, n, mode):
    if not isinstance(m, list) or len(m) != n:
        return False
    for o in m:
        if not isinstance(o, list) or not o or o[0] not in ("ok", "timeout", "exception", "load", "crash"):
            return False
        if o[0] == "ok" and (len(o) != 2 or mode == "check" and not isinstance(o[1], bool)):
            return False
        if o[0] in ("exception", "load") and (len(o) != 2 or not isinstance(o[1], str)):
            return False
        if o[0] in ("timeout", "crash") and len(o) > 2:
            return False
    return True


def _valid_gen(m):
    return isinstance(m, dict) and isinstance(m.get("status"), str) and (
        m["status"] != "ok" or isinstance(m.get("items"), list) and all(
            it is None or isinstance(it, list) and all(isinstance(a, str) for a in it) for it in m["items"]))


def _sandbox(job):
    key = sha(json.dumps(dict(job, harness=HARNESS, py=UV_PY), sort_keys=True))
    path = os.path.join(EXEC, key[:2], key + ".json")
    with _LOCKS_GUARD:
        lock = _LOCKS[key]
    with lock:
        if os.path.exists(path):
            return json.load(open(path))
        n = len(job.get("inputs", [])) or 1
        with SLOTS, tempfile.TemporaryDirectory(prefix="v56job_") as d:
            with open(os.path.join(d, "job.json"), "w") as f:
                json.dump(job, f)
            tle, m = _bwrap(d, 60 + n * (job.get("per_call", 1) + 15))
        ok = _valid_gen(m) if job["mode"] == "gen" else _valid_outputs(m, n, job["mode"])
        res = dict(tle=tle, marked=m if ok else None)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = f"{path}.{os.getpid()}.{threading.get_ident()}.tmp"
        with open(tmp, "w") as f:
            json.dump(res, f)
        os.replace(tmp, path)
        return res


def run(code, func, inputs, per_call, mode="call", check=None):
    """Outputs per input: ['ok', v] | ['timeout'] | ['exception', name] | ['load', name] | ['crash'].
    Chunks of 200; a chunk whose process dies/hangs is rerun in chunks of 25, then singly."""
    def go(part, level):
        job = dict(code=code, func=func, inputs=part, per_call=per_call, mode=mode, check=check)
        r = _sandbox(job)
        m = r["marked"]
        if m is not None:
            return m
        if level + 1 < len(CHUNKS):
            size = CHUNKS[level + 1]
            return [o for s in range(0, len(part), size) for o in go(part[s:s + size], level + 1)]
        return [["timeout"] if r["tle"] else ["crash"]] * len(part)
    parts = [inputs[s:s + CHUNKS[0]] for s in range(0, len(inputs), CHUNKS[0])]
    with ThreadPoolExecutor(vf.WORKERS) as ex:
        return [o for chunk in ex.map(lambda part: go(part, 0), parts) for o in chunk]


def run_many(specs):
    """specs: {name: (code, func, inputs, per_call, mode, check)} -> {name: outputs}, programs in parallel."""
    with ThreadPoolExecutor(max(1, len(specs))) as ex:
        futs = {n: ex.submit(run, *s) for n, s in specs.items()}
        return {n: f.result() for n, f in futs.items()}


def generated_inputs(code, arity):
    job = dict(code=code, func=None, inputs=[], per_call=20, mode="gen", check=None)
    r = _sandbox(job)
    m = r["marked"]
    info = dict(status="ok", yielded=0, dropped=0, duplicates=0, kept=0)
    if not isinstance(m, dict):
        return [], dict(info, status="timeout" if r["tle"] else "crash")
    if m["status"] != "ok":
        return [], dict(info, status=m["status"])
    out = []
    for it in m["items"]:
        info["yielded"] += 1
        if it is None or len(it) != arity:
            info["dropped"] += 1
            continue
        try:
            lit = canon("\n".join(it))
        except (ValueError, RecursionError):
            info["dropped"] += 1
            continue
        if lit in out:
            info["duplicates"] += 1
        elif len(out) < CAP_GEN:
            out.append(lit)
    info["kept"] = len(out)
    return out, info


# ---------------------------------------------------------------- references (Codex)
CODEX_MODEL, CODEX_EFFORT = "gpt-6-astra", "high"


def codex(prompt, outdir):
    """One isolated Codex attempt in an empty directory -> (answer text or None, audit). An attempt is consumed as
    soon as its `sent.json` marker exists: a sent attempt without audit (crash/interruption) is final `unknown` and
    is never resent; a saved audit is reused on resume."""
    os.makedirs(outdir, exist_ok=True)
    last, apath, spath = (os.path.join(outdir, n) for n in ("answer.txt", "audit.json", "sent.json"))
    if os.path.exists(apath):
        audit = json.load(open(apath))
        if audit.get("prompt_sha256") != sha(prompt):
            raise SystemExit(outdir + ": saved attempt was made with a different prompt")
        ok = audit["rc"] == 0 and not audit["tool_events"] and os.path.exists(last)
        return (open(last).read() if ok else None), audit
    if os.path.exists(spath):
        audit = dict(rc=None, unknown="sent_without_record", tool_events=0, prompt_sha256=sha(prompt))
        mine.dump(audit, apath)
        return None, audit
    with open(spath, "w") as f:
        json.dump(dict(prompt_sha256=sha(prompt), ts=time.time()), f)
        f.flush(); os.fsync(f.fileno())
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="v56ref_") as d:
        try:
            p = subprocess.run(["codex", "exec", "--ephemeral", "--skip-git-repo-check", "-s", "read-only", "-C", d,
                                "-m", CODEX_MODEL, "-c", f'model_reasoning_effort="{CODEX_EFFORT}"',
                                "--json", "-o", last, prompt], stdin=subprocess.DEVNULL, capture_output=True,
                               text=True, timeout=1800)
            rc, stdout = p.returncode, p.stdout
        except subprocess.TimeoutExpired:
            rc, stdout = None, ""
    events = []
    for l in stdout.splitlines():
        try:
            events.append(json.loads(l))
        except ValueError:
            pass
    kinds = collections.Counter((e.get("item") or {}).get("type") or e.get("type") for e in events)
    tools = sum(v for k, v in kinds.items() if k and any(w in k for w in ("command", "tool", "file", "mcp", "web")))
    audit = dict(rc=rc, seconds=round(time.time() - t0, 1), events=dict(kinds), tool_events=tools,
                 model=CODEX_MODEL, effort=CODEX_EFFORT, prompt_sha256=sha(prompt))
    mine.dump(audit, apath)
    ok = rc == 0 and not tools and os.path.exists(last)
    return (open(last).read() if ok else None), audit


def certify(code, func, tests):
    """Hardened-harness version of mine.py's policy: 10 s per test, a timeout retried once at 60 s.
    -> per test pass | wrong | exc | tle | load | crash."""
    inputs = [tc["input"] for tc in tests]
    outs = run(code, func, inputs, 10)
    slow = [i for i, o in enumerate(outs) if o[0] == "timeout"]
    for i, o in zip(slow, run(code, func, [inputs[i] for i in slow], 60) if slow else []):
        outs[i] = o
    res = []
    for o, tc in zip(outs, tests):
        if o[0] == "ok":
            res.append("pass" if same(o[1], json.loads(tc["output"])) else "wrong")
        else:
            res.append(dict(exception="exc", timeout="tle").get(o[0], o[0]))
    return res


def cmd_ref():
    for p in cohort():
        t, qid = p["_t"], p["question_id"]
        tests = t["public"] + t["private"]
        _, names = signature(t["starter_code"], t["func_name"])
        rdir = os.path.join(OUT, "ref", qid)
        final = os.path.join(rdir, "reference.json")
        if not os.path.exists(final):
            rec = dict(question_id=qid, certified=None, attempts=[])
            for a in range(REF_ATTEMPTS):
                text, audit = codex(REF_PROMPT.format(q=t["question_content"], s=t["starter_code"]),
                                    os.path.join(rdir, f"ref_{a}"))
                code = code_block(text) if text else None
                res = certify(code, t["func_name"], tests) if code else []
                ok = bool(code) and all(r == "pass" for r in res)
                rec["attempts"].append(dict(attempt=a, audit=audit, has_code=bool(code),
                                            results=dict(collections.Counter(res))))
                if ok:
                    rec.update(certified=a, code=code, code_sha256=sha(code))
                    break
            mine.dump(rec, final)
        vfinal = os.path.join(rdir, "validator.json")
        if not os.path.exists(vfinal):
            rec = dict(question_id=qid, certified=None, attempts=[])
            inputs = [tc["input"] for tc in tests]
            for a in range(REF_ATTEMPTS):
                text, audit = codex(VAL_PROMPT.format(q=t["question_content"], s=t["starter_code"],
                                                      params=", ".join(names)), os.path.join(rdir, f"val_{a}"))
                code = code_block(text) if text else None
                res = run(code, None, inputs, 1, mode="check", check="is_valid") if code else []
                ok = bool(code) and all(o == ["ok", True] for o in res)
                rec["attempts"].append(dict(attempt=a, audit=audit, has_code=bool(code),
                                            accepted=sum(o == ["ok", True] for o in res), of=len(inputs)))
                if ok:
                    rec.update(certified=a, code=code, code_sha256=sha(code))
                    break
            mine.dump(rec, vfinal)
        r, v = json.load(open(final)), json.load(open(vfinal))
        print(qid, "reference", r["certified"], [x["results"] for x in r["attempts"]],
              "validator", v["certified"], flush=True)


# ---------------------------------------------------------------- Qwen generation
def cmd_generate():
    ps = cohort()
    if os.environ.get("QWEN_MODEL") != mine.MODEL:
        raise SystemExit("QWEN_MODEL is not the registered served name")
    served = mine.check_model()
    mine.JOURNAL = os.path.join(OUT, "journal.jsonl")
    os.makedirs(OUT, exist_ok=True)
    sent = {json.loads(l)["key"] for l in open(mine.JOURNAL)} if os.path.exists(mine.JOURNAL) else set()
    for p in ps:
        for kind, i, body in jobs(p):
            key = f"{p['question_id']}/{kind}/{i}"
            path = os.path.join(OUT, "calls", p["question_id"], f"{kind}_{i}.json")
            if os.path.exists(path):
                if json.load(open(path))["request_sha256"] != sha(body):
                    raise SystemExit(key + ": cached record was made with a different request")
                continue
            os.makedirs(os.path.dirname(path), exist_ok=True)
            if key in sent:
                mine.dump(dict(key=key, request_sha256=sha(body), served=None,
                               response=dict(unknown="sent_without_record")), path)
                print(key, "unknown (sent without record)", flush=True)
                continue
            t0 = time.time()
            resp, tries = mine._chat(body.encode(), key)
            mine.dump(dict(key=key, request_sha256=sha(body), model=mine.MODEL, served=served,
                           seconds=round(time.time() - t0, 1), transport_retries=tries, response=resp), path)
            mine.journal(event="saved", key=key)
            print(key, "ok" if "choices" in resp else {k: v for k, v in resp.items() if k != "body"},
                  round(time.time() - t0, 1), flush=True)


def answer(p, kind, i):
    """(text or None, finish_reason or status) of one verified Qwen record."""
    body = dict((f"{k}/{j}", b) for k, j, b in jobs(p))[f"{kind}/{i}"]
    path = os.path.join(OUT, "calls", p["question_id"], f"{kind}_{i}.json")
    if not os.path.exists(path):
        return None, "missing"
    rec = json.load(open(path))
    if rec["request_sha256"] != sha(body):
        raise SystemExit(f"{p['question_id']}/{kind}/{i}: record request differs from the frozen prompt/seed/config")
    resp = rec["response"]
    if "choices" not in resp:
        return None, "no_response"
    if rec.get("model") != mine.MODEL:
        raise SystemExit("record model differs")
    c = resp["choices"][0]
    return c["message"]["content"], c.get("finish_reason")


# ---------------------------------------------------------------- scoring
def same(a, b):
    """Both sides are decoded JSON values (LiveCodeBench functional equality: value ==)."""
    return a == b


NO_QUORUM = object()   # sentinel: an oracle value may itself be None (JSON null)


def quorum(put_out, outs):
    """v49 primary: largest group of valid programs with value != PUT, >= 2 members and > V/2 (V = valid count;
    failures count as not agreeing). Returns the value or None."""
    if put_out[0] != "ok" or not outs:
        return NO_QUORUM
    groups = []   # equality groups in program order (same() is the only equality used anywhere)
    for o in outs:
        if o[0] == "ok" and not same(o[1], put_out[1]):
            for g in groups:
                if same(g[0], o[1]):
                    g.append(o[1])
                    break
            else:
                groups.append([o[1]])
    if not groups:
        return NO_QUORUM
    best = max(groups, key=len)   # ties: first in program order; with K = 3 a quorum group is unique anyway
    return best[0] if len(best) >= 2 and len(best) * 2 > len(outs) else NO_QUORUM


def score_problem(p):
    t, qid, func = p["_t"], p["question_id"], p["_t"]["func_name"]
    task = task_view(p)
    arity = len(task["params"])
    ref = json.load(open(os.path.join(OUT, "ref", qid, "reference.json")))
    val = json.load(open(os.path.join(OUT, "ref", qid, "validator.json")))
    if ref["certified"] is None:
        return dict(question_id=qid, excluded="no_certified_reference")
    public = [canon(tc["input"]) for tc in t["public"]]
    expected = [json.loads(tc["output"]) for tc in t["public"]]
    # input sources
    rng = random.Random(f"v56/fuzz/{qid}")
    tool = [canon(s) for s in vf.fuzz_inputs("leetcode", [tc["input"] for tc in t["public"]], rng, n=FUZZ_N)]
    text, fin = answer(p, "inputs", 0)
    llm, gen_info = generated_inputs(code_block(text), arity) if text else ([], dict(status=fin))
    gen_info["finish_reason"] = fin
    sources = collections.OrderedDict()
    for name, items in (("public", public), ("tool", tool), ("llm", llm)):
        for x in items:
            sources.setdefault(x, name)
    pool = list(sources)
    # Qwen `open` validity filter (Amendment 4: the whole checker is dropped if it rejects any public input)
    text, cfin = answer(p, "checks", 0)
    filt = dict(finish_reason=cfin, used=False)
    if text:
        chk = run(code_block(text), None, pool, 1, mode="check", check="open")
        ok = {x: o == ["ok", True] for x, o in zip(pool, chk)}
        if all(ok[x] for x in public):
            filt.update(used=True, rejected=sum(not v for v in ok.values()))
            pool = [x for x in pool if ok[x]]
        else:
            filt["dropped"] = "rejects_public"
    decisive = sorted(pool, key=lambda x: (sha(x), x))
    # programs
    programs, info = {}, {}
    for arm in ARMS:
        programs[arm], info[arm] = [], collections.Counter()
        for i in range(K):
            text, f = answer(p, arm, i)
            info[arm]["finish_" + str(f)] += 1
            info[arm]["missing"] += text is None
            if text:
                programs[arm].append(code_block(text))
    specs = {f"{arm}{i}": (c, func, public, T_PUBLIC, "call", None)
             for arm in ARMS for i, c in enumerate(programs[arm])}
    pub = run_many(specs)
    valid = {arm: [c for i, c in enumerate(programs[arm])
                   if all(o[0] == "ok" and same(o[1], e) for o, e in zip(pub[f"{arm}{i}"], expected))]
             for arm in ARMS}
    specs = {"put": (p["put"], func, decisive, T_PUT, "call", None),
             "ref": (ref["code"], func, decisive, T_REF, "call", None)}
    if val["certified"] is not None:
        specs["val"] = (val["code"], None, decisive, 1, "check", "is_valid")
    specs.update({f"{arm}{i}": (c, func, decisive, T_PROGRAM, "call", None)
                  for arm in ARMS for i, c in enumerate(valid[arm])})
    outs = run_many(specs)
    put, rout = dict(zip(decisive, outs["put"])), dict(zip(decisive, outs["ref"]))
    vout = dict(zip(decisive, outs["val"])) if "val" in outs else None

    def input_ok(x):   # True / False / None (unknown)
        if rout[x][0] == "exception":
            return False
        if vout is not None:
            return {True: True, False: False}.get(vout[x][1]) if vout[x][0] == "ok" else None
        return True if rout[x][0] == "ok" else None

    exposing = [x for x in decisive if input_ok(x) is True and rout[x][0] == "ok" and put[x][0] == "ok"
                and not same(put[x][1], rout[x][1])]
    res = dict(question_id=qid, difficulty=p["difficulty"], pool=len(decisive),
               pool_by_source=dict(collections.Counter(sources[x] for x in decisive)), generator=gen_info,
               filter=filt, validator_certified=val["certified"] is not None,
               exposing=len(exposing), exposing_by_source=dict(collections.Counter(sources[x] for x in exposing)),
               ref_status=dict(collections.Counter(rout[x][0] for x in decisive)), arms={})
    for arm in ARMS:
        prog = [dict(zip(decisive, outs[f"{arm}{i}"])) for i in range(len(valid[arm]))]
        emitted = []
        for x in decisive:
            v = quorum(put[x], [pr[x] for pr in prog])
            if v is not NO_QUORUM:
                emitted.append((x, v))
        labels = collections.Counter()
        for x, v in emitted[:CAP_TESTS]:
            ok = input_ok(x)
            if ok is True and rout[x][0] == "ok" and same(v, rout[x][1]) and not same(put[x][1], rout[x][1]):
                labels["confirmed"] += 1
            elif ok is False:
                labels["fa_invalid"] += 1
            elif ok is True and rout[x][0] == "ok":
                labels["fa_wrong_value"] += 1
            else:
                labels["fa_unknown"] += 1
        diag = collections.Counter()
        for x in exposing:
            fin = [pr[x] for pr in prog if pr[x][0] == "ok"]
            if len(fin) < 2:
                diag["abstain"] += 1
            elif all(same(o[1], put[x][1]) for o in fin):
                diag["common_mode_put"] += 1
            elif all(same(o[1], fin[0][1]) for o in fin) and not same(fin[0][1], rout[x][1]):
                diag["common_mode_other"] += 1
            elif quorum(put[x], [pr[x] for pr in prog]) is NO_QUORUM:
                diag["no_quorum"] += 1
        res["arms"][arm] = dict(programs=len(programs[arm]), valid=len(valid[arm]), finish=dict(info[arm]),
                                emitted_uncapped=len(emitted), tests=min(len(emitted), CAP_TESTS), **labels,
                                confirmed_task=labels["confirmed"] > 0, exposing_diag=dict(diag),
                                confirmed_by_source=dict(collections.Counter(
                                    sources[x] for x, v in emitted[:CAP_TESTS]
                                    if input_ok(x) is True and rout[x][0] == "ok" and same(v, rout[x][1])
                                    and not same(put[x][1], rout[x][1]))))
    return res


def sign_p(wins, losses):
    n = wins + losses
    if not n:
        return 1.0
    k = min(wins, losses)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def compare(rows, a, b, no_verdict=()):
    w = sum(r["arms"][a]["confirmed_task"] and not r["arms"][b]["confirmed_task"] for r in rows)
    l = sum(r["arms"][b]["confirmed_task"] and not r["arms"][a]["confirmed_task"] for r in rows)
    ta = sum(r["arms"][a]["confirmed_task"] for r in rows)
    tb = sum(r["arms"][b]["confirmed_task"] for r in rows)
    fa = lambda arm: sum(r["arms"][arm].get(k, 0) for r in rows for k in ("fa_invalid", "fa_wrong_value", "fa_unknown"))
    go = None if a in no_verdict or b in no_verdict else ta >= tb + 2 and w > l and fa(a) <= fa(b)
    return dict(tasks=[ta, tb], wins=w, losses=l, sign_p=sign_p(w, l), fa=[fa(a), fa(b)], go=go)


def cmd_score():
    ps = cohort()
    rows = [score_problem(p) for p in ps]
    for r in rows:
        print(json.dumps(r, sort_keys=True), flush=True)
    scored = [r for r in rows if "excluded" not in r]
    totals = {}
    for arm in ARMS:
        a = [r["arms"][arm] for r in scored]
        tests = sum(x["tests"] for x in a)
        conf = sum(x.get("confirmed", 0) for x in a)
        totals[arm] = dict(confirmed_tasks=sum(x["confirmed_task"] for x in a), tests=tests, confirmed_tests=conf,
                           precision=round(conf / tests, 3) if tests else None,
                           fa_invalid=sum(x.get("fa_invalid", 0) for x in a),
                           fa_wrong_value=sum(x.get("fa_wrong_value", 0) for x in a),
                           fa_unknown=sum(x.get("fa_unknown", 0) for x in a),
                           valid_programs=sum(x["valid"] for x in a),
                           tasks_with_valid=sum(x["valid"] >= 2 for x in a))
    # > 10 % missing/no-response oracle calls over the whole cohort (before any exclusion): no verdict
    missing = {arm: sum(answer(p, arm, i)[0] is None for p in ps for i in range(K)) for arm in ARMS}
    nv = tuple(arm for arm in ARMS if missing[arm] * 10 > K * len(ps))
    summary = dict(scored=len(scored), excluded=[r["question_id"] for r in rows if "excluded" in r],
                   reach=sum(r["exposing"] > 0 for r in scored), totals=totals, missing_calls=missing,
                   no_verdict_arms=list(nv),
                   concept_defn_vs_brute=compare(scored, "defn", "brute", nv),
                   family_brute_vs_plain=compare(scored, "brute", "plain", nv),
                   defn_vs_plain=compare(scored, "defn", "plain", nv))
    mine.dump(dict(summary=summary, problems=rows), os.path.join(OUT, "metrics.json"))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "_batch":
        _child_batch(sys.argv[2])
    else:
        import fcntl
        os.makedirs(OUT, exist_ok=True)
        lock = open(os.path.join(OUT, f".{sys.argv[1]}.lock"), "w")   # ref / generate touch disjoint files
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)   # one runner at a time (cache, attempt markers)
        except BlockingIOError:
            raise SystemExit(f"another arms.py {sys.argv[1]} runner holds the lock")
        dict(ref=cmd_ref, generate=cmd_generate, score=cmd_score)[sys.argv[1]]()
