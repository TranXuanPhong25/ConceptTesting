"""Executor + crash oracle (pre-registered in PILOT_PLAN.md). Runs inside dfuzz-pilot:arm64.

Every program runs in a fresh process (run/launch.py: faulthandler, seeded RNGs), own scratch cwd, timeout, address-space
limit (prlimit), env without cloud credentials. Run 1 always; run 2 if run 1 is clean (uninitialised-memory check: the
two fresh runs disagree) or a crash; runs 2-3 if any crash. Classes:
  crash classes : check_abort | memory_safety | fpe | ill | trap | abort_other | signal_other | internal_assert
  not crashes   : exception (type, msg, at_target, own_check) | clean | resource (137/SIGKILL/OOM) | timeout | exit
strict crash = crash class in 3/3 runs with the innermost program frame on the target API call.
Dedup signature = CHECK/assert file:line, else the top native frame (one extra run under gdb).
"""
import ast, json, os, re, signal, subprocess, tempfile, time
from concurrent.futures import ThreadPoolExecutor

PY = {"torch": "/opt/py38/bin/python", "tf": "/opt/tf215/bin/python"}
LAUNCH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "launch.py")
TIMEOUT = int(os.environ.get("ORACLE_TIMEOUT", "30"))
MEM = os.environ.get("ORACLE_MEM", str(6 << 30))  # bytes of address space; TF alone reserves ~3 GB
CRASH = {"check_abort", "memory_safety", "fpe", "ill", "trap", "abort_other", "signal_other", "internal_assert"}
NOT_A_CHECK = ("NameError", "SyntaxError", "IndentationError", "ImportError", "ModuleNotFoundError",
               "UnboundLocalError", "AttributeError", "KeyboardInterrupt")
SIGNATURE_ERR = re.compile(r"unexpected keyword argument|missing \d+ required|positional argument|takes \d+ positional")
FATAL = re.compile(r"\bF(?:\d{4}[^\]\n]*?\s| )([\w/.+-]+\.(?:cc|cpp|h|c)):(\d+)\]\s*(.*)")
THROWN_AT = re.compile(r'(?:Exception raised from \S+ at |INTERNAL ASSERT FAILED at )"?([^":\s]+\.(?:cpp|cc|h|c))"?:(\d+)')
HEAP = re.compile(r"free\(\)|double free|corrupted|munmap_chunk|malloc\(\)|malloc_consolidate|realloc\(\)|stack smashing")
OOM = re.compile(r"std::bad_alloc|Cannot allocate memory|MemoryError|out of memory|OOM when allocating", re.I)
HEX = re.compile(r"0x[0-9a-fA-F]+")
SAFE_ENV = {k: v for k, v in os.environ.items()
            if not k.startswith(("GOOGLE", "VERTEX", "CLOUDSDK", "OPENAI", "LLM_"))}
SAFE_ENV.update(CUDA_VISIBLE_DEVICES="", PYTHONHASHSEED="0", PYTHONFAULTHANDLER="1", OMP_NUM_THREADS="2")


def lib_of(api):
    return "torch" if api.startswith("torch") else "tf"


def _fname(f):
    return f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else None


def target_lines(code, api):
    """Line numbers spanned by calls to the target (by last name component), to instances bound from it, or taking
    such an instance as an argument (config objects like tf.io.TFRecordOptions act where they are consumed)."""
    name = api.split(".")[-1]
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return set()
    bound = {t.id for n in ast.walk(tree) if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call)
             and _fname(n.value.func) == name for t in n.targets if isinstance(t, ast.Name)}
    lines = set()
    for n in ast.walk(tree):
        uses = [a for a in list(n.args) + [k.value for k in n.keywords] if isinstance(a, ast.Name) and a.id in bound] \
            if isinstance(n, ast.Call) else []
        if isinstance(n, ast.Call) and (_fname(n.func) == name or uses or
                                        (isinstance(n.func, ast.Name) and n.func.id in bound)):
            lines |= set(range(n.lineno, (n.end_lineno or n.lineno) + 1))
    return lines


def _exec(cmd, cwd, timeout):
    p = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="replace",
                         env=SAFE_ENV, start_new_session=True)
    try:
        out, err = p.communicate(timeout=timeout)
        return p.returncode, out, err, False
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        out, err = p.communicate()
        return None, out, err, True


def run_once(lib, code, timeout=TIMEOUT):
    with tempfile.TemporaryDirectory() as cwd:
        os.chmod(cwd, 0o777)
        prog, rec = os.path.join(cwd, "prog.py"), os.path.join(cwd, "rec.json")
        open(prog, "w").write(code)
        t = time.time()
        rc, out, err, to = _exec(["prlimit", f"--as={MEM}", "--core=0", "--", PY[lib], "-X", "faulthandler",
                                  LAUNCH, lib, prog, rec], cwd, timeout)
        r = json.load(open(rec)) if os.path.exists(rec) else None
    return {"rc": rc, "timeout": to, "secs": round(time.time() - t, 1), "out": out, "err": err, "rec": r, "prog": prog}


def _fault_lines(err, prog):
    """Innermost program line per thread from a faulthandler dump; the crashing ('Current') thread first."""
    cur, others, thread, seen = None, [], None, set()
    for line in err.splitlines():
        if line.startswith(("Current thread", "Thread 0x")):
            thread = "cur" if line.startswith("Current") else line
            continue
        m = re.match(r'\s+File "([^"]+)", line (\d+)', line)
        if m and thread and m.group(1) == prog and thread not in seen:
            seen.add(thread)
            if thread == "cur":
                cur = int(m.group(2))
            else:
                others.append(int(m.group(2)))
    return ([cur] if cur else []) + others


def classify(r, tlines):
    err, rec = r["err"] or "", r["rec"] or {}
    c = {"cls": None, "at_target": False, "own_check": False, "exc": None, "msg": None, "fatal": None, "sig": None,
         "rc": r["rc"], "secs": r["secs"]}
    fatal = FATAL.findall(err)
    if fatal:
        c["fatal"] = f"{fatal[-1][0]}:{fatal[-1][1]}] {fatal[-1][2][:200]}"
    if r["timeout"]:
        c["cls"] = "timeout"
    elif r["rc"] in (137, -9):
        c["cls"] = "resource"
    elif r["rc"] < 0:
        sig = signal.Signals(-r["rc"]).name
        c["signal"] = sig
        if sig == "SIGABRT":
            c["cls"] = ("resource" if OOM.search(err) else "memory_safety" if HEAP.search(err) else
                        "check_abort" if fatal or re.search(r"Check failed|Non-OK-status|terminate called", err)
                        else "abort_other")
        else:
            c["cls"] = {"SIGSEGV": "memory_safety", "SIGBUS": "memory_safety", "SIGFPE": "fpe", "SIGILL": "ill",
                        "SIGTRAP": "trap"}.get(sig, "signal_other")
        lines = _fault_lines(err, r["prog"])
        c["at_target"] = bool(lines) and lines[0] in tlines
        c["frame_line"] = lines[0] if lines else None
        if c["cls"] == "check_abort":
            m = THROWN_AT.search(err)
            c["sig"] = f"{fatal[-1][0]}:{fatal[-1][1]}" if fatal else f"{m.group(1)}:{m.group(2)}" if m else None
    elif r["rc"] == 0:
        c["cls"] = "clean"
    elif rec.get("kind") == "exception":
        typ, msg = rec["type"], rec["msg"]
        c.update(exc=typ, msg=msg[:1500], frame_line=rec["prog_line"], raised_in=rec["raised_in"],
                 at_target=rec["prog_line"] in tlines)
        if "INTERNAL ASSERT FAILED" in msg:
            c["cls"] = "internal_assert"
            m = THROWN_AT.search(msg)
            c["sig"] = f"{m.group(1)}:{m.group(2)}" if m else None
        elif OOM.search(typ + msg) or typ.endswith("ResourceExhaustedError"):
            c["cls"] = "resource"
        else:
            c["cls"] = "exception"
            c["own_check"] = (c["at_target"] and rec["raised_in"] != "prog" and
                              not typ.split(".")[-1] in NOT_A_CHECK and not SIGNATURE_ERR.search(msg))
    else:
        c["cls"] = "exit"
    c["err_tail"] = err.strip()[-1200:]
    c["out_tail"] = (r["out"] or "").strip()[-400:]
    c["_out"] = HEX.sub("0x?", r["out"] or "")
    return c


GDB_SKIP = re.compile(r"raise|abort|pthread_kill|__libc_message|malloc_printerr|_int_free|_int_malloc|__restore_rt|"
                      r"gsignal|^free$|^malloc$|faulthandler|__GI_|__kernel|sigreturn|_PyRuntime|^\?\?$|std::terminate|__cxa_|__gnu_cxx|LogMessageFatal")


def native_top_frame(lib, code):
    """Re-run once under gdb; first frame outside libc/abort machinery, as 'func@lib.so' (or 'func at file:line')."""
    with tempfile.TemporaryDirectory() as cwd:
        prog = os.path.join(cwd, "prog.py")
        open(prog, "w").write(code)
        rc, out, err, to = _exec(["gdb", "-q", "-batch", "-ex", "set pagination off", "-ex", "handle SIGPIPE nostop",
                                  "-ex", "run", "-ex", "bt 30", "--args", PY[lib], LAUNCH, lib, prog,
                                  os.path.join(cwd, "rec.json")], cwd, 180)
    for line in out.splitlines():
        m = re.match(r"#\d+\s+(?:0x[0-9a-f]+ in )?(.*?)(?: at (\S+)| from (\S+))?$", line)
        if not m or "(" not in m.group(1):
            continue
        func, src, so = m.group(1).split("(")[0].strip(), m.group(2), m.group(3)
        if GDB_SKIP.search(func) or (so and re.search(r"libc\.so|libpthread", so)):
            continue
        return f"{func} at {src}" if src else f"{func}@{os.path.basename(so or 'python')}"
    return None


def evaluate(api, code, reps=3, gdb=True):
    lib, tl = lib_of(api), target_lines(code, api)
    runs = [classify(run_once(lib, code), tl)]
    if runs[0]["cls"] == "clean" or runs[0]["cls"] in CRASH:
        runs.append(classify(run_once(lib, code), tl))
    if any(r["cls"] in CRASH for r in runs):
        while len(runs) < reps:
            runs.append(classify(run_once(lib, code), tl))
    first = runs[0]
    # a run whose faulthandler dump shows no program frame (heap corruption can garble it) neither confirms nor refutes
    framed = [r for r in runs if r.get("frame_line") is not None]
    strict = (len(runs) == reps and all(r["cls"] in CRASH for r in runs) and bool(framed)
              and all(r["at_target"] for r in framed))
    crash_cls = sorted({r["cls"] for r in runs if r["cls"] in CRASH})
    sig = next((r["sig"] for r in runs if r["sig"]), None)
    if strict and not sig and gdb:
        sig = native_top_frame(lib, code) or f"{crash_cls[0]}@{api}"
    disagree = len(runs) >= 2 and (runs[0]["cls"] != runs[1]["cls"] or runs[0]["_out"] != runs[1]["_out"])
    for r in runs:
        r.pop("_out", None)
    return {"api": api, "lib": lib, "has_target_call": bool(tl), "cls": first["cls"], "strict_crash": strict,
            "crash_classes": crash_cls, "crash_hits": f"{sum(r['cls'] in CRASH for r in runs)}/{len(runs)}",
            "sig": sig if crash_cls else None, "disagree": disagree, "exc": first["exc"], "msg": first["msg"],
            "at_target": first["at_target"], "own_check": first["own_check"], "runs": runs}


def evaluate_many(items, workers=None):
    """items: [(key, api, code)] -> {key: result}. Subprocess-bound, so threads are fine."""
    workers = workers or int(os.environ.get("WORKERS", "4"))
    with ThreadPoolExecutor(workers) as ex:
        futs = {k: ex.submit(evaluate, api, code) for k, api, code in items}
        return {k: f.result() for k, f in futs.items()}


if __name__ == "__main__":
    import sys
    api, path = sys.argv[1], sys.argv[2]
    res = evaluate(api, open(path).read())
    print(json.dumps({k: v for k, v in res.items() if k != "runs"}, indent=1))
