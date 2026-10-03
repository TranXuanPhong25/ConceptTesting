"""Differential executor for LLM-written PBT/EBT files. Runs ONLY in the exec container
(no credentials, --network none): MODE=exec bash run/dock.sh python evaluate.py <kind> <out.jsonl> <dir>...

Each test unit is run twice, against
  buggy = HumanEval canonical solution (what the paper's runner tests, `run pbt|ebt --canonical`), and
  fixed = HumanEval+ canonical solution (passes all HumanEval+ tests for the 16 tasks; see he_plus_canonical_check.log).
A unit is VALID if it passes on fixed; it DETECTS if it is valid and fails on buggy (assertion, exception, or 15 s
timeout = the paper's TEST_EXECUTION_TIMEOUT). This automatic filter replaces the paper's manual removal of wrong tests.
Program assembly reuses the vendored helpers (extract_code_block, entry-point removal, make_canonical_function,
REQUIRED_IMPORTS), i.e. exactly what vendor `_make_generated_pbt_string` builds.
  PBT unit = one pytest node, run alone: `pytest file::node --hypothesis-seed=0` (same seed on buggy and fixed).
  EBT unit = one top-level check statement (assert / call / loop ...), executed in order after the setup statements.
"""
import ast, json, os, re, signal, subprocess, sys, tempfile, textwrap, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pbteval.core.data import REQUIRED_IMPORTS, get_function_pattern, make_canonical_function
from pbteval.utils.utils import extract_code_block

TIMEOUT = 15
ENV = {**os.environ, "HYPOTHESIS_SUPPRESS_HEALTH_CHECK": "filter_too_much,too_slow,data_too_large,function_scoped_fixture"}
WORKERS = int(os.environ.get("WORKERS", "6"))
REPAIR = os.environ.get("REPAIR", "1") == "1"  # uniform, arm-blind repairs (see code_of); REPAIR=0 = strict
PRELUDE = "from hypothesis import given, example, settings, assume, strategies as st"
SETUP = (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Assign, ast.AnnAssign,
         ast.AugAssign)


def load(path):
    return {r["task_id"]: r for r in map(json.loads, open(path))}


HE, HEP = load("/work/data/humaneval.jsonl"), load("/work/data/humaneval_plus.jsonl")


def solutions(task):
    he, hep = HE[task], HEP[task]
    return {"buggy": make_canonical_function(he["prompt"], he["canonical_solution"], he["entry_point"]),
            "fixed": make_canonical_function(hep["prompt"], hep["canonical_solution"], hep["entry_point"])}


def limited(cmd):  # test processes run as nobody, 3 GB address-space cap
    return ["setpriv", "--reuid=65534", "--regid=65534", "--clear-groups",
            "bash", "-c", 'ulimit -v 3000000; exec "$@"', "_", *cmd]


def mktmp():
    d = Path(tempfile.mkdtemp()); d.chmod(0o777)
    return d


def code_of(path, entry):
    """Vendored extraction (extract_code_block + entry-point removal). With REPAIR, if that does not parse, the raw
    fenced blocks are dedented (the model sometimes indents the whole answer as if continuing the function body)."""
    text = path.read_text()
    code = re.sub(get_function_pattern(entry), "", extract_code_block(text), flags=re.DOTALL)
    repaired = False
    if REPAIR:
        try:
            ast.parse(code)
        except SyntaxError:
            raw = "\n".join(textwrap.dedent(b) for b in re.findall(r"```(?:python)?\n(.*?)```", text, flags=re.DOTALL))
            alt = re.sub(get_function_pattern(entry), "", raw, flags=re.DOTALL)
            try:
                ast.parse(alt); code, repaired = alt, True
            except SyntaxError:
                pass
    return code, repaired


def run(cmd, cwd, timeout):
    p = subprocess.Popen(limited(cmd), cwd=cwd, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, start_new_session=True)
    try:
        out, _ = p.communicate(timeout=timeout)
        return p.returncode, out
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        out, _ = p.communicate()
        return "timeout", out


# ---------------------------------------------------------------- PBT
def pbt_file(path, task, entry):
    code, repaired = code_of(path, entry)
    sols = solutions(task)
    tmp = mktmp()
    for s, fn in sols.items():
        (tmp / s).mkdir(); (tmp / s).chmod(0o777)
        parts = (REQUIRED_IMPORTS, PRELUDE if REPAIR else "", fn, code)
        (tmp / s / f"test_{s}.py").write_text("\n".join(x for x in parts if x))
    rc, out = run(["python", "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", "test_fixed.py"],
                  tmp / "fixed", 60)
    nodes = [l.split("::", 1)[1] for l in out.splitlines() if l.startswith("test_fixed.py::")]
    return tmp, nodes, (None if nodes else f"collect rc={rc}: {out[-300:]}"), repaired


def pbt_node(tmp, sol, node):
    t0 = time.time()
    rc, out = run(["python", "-m", "pytest", f"test_{sol}.py::{node}", "-q", "-x", "-p", "no:cacheprovider",
                   "--hypothesis-seed=0"], tmp / sol, TIMEOUT)
    status = "pass" if rc == 0 else ("timeout" if rc == "timeout" else "fail")
    tail = "" if status == "pass" else out[-400:]
    return {"status": status, "secs": round(time.time() - t0, 2), "tail": tail}


# ---------------------------------------------------------------- EBT
EBT_RUNNER = r'''
import ast, json, signal, sys
def alarm(*_): raise TimeoutError("unit timeout")
signal.signal(signal.SIGALRM, alarm)
prefix, tests, T = open(sys.argv[1]).read(), open(sys.argv[2]).read(), int(sys.argv[3])
g = {"__name__": "__ebt__"}
exec(compile(prefix, "solution", "exec"), g)
SETUP = (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Assign, ast.AnnAssign, ast.AugAssign)
i = 0
for st in ast.parse(tests).body:
    is_check = not isinstance(st, SETUP)
    signal.alarm(T)
    try:
        exec(compile(ast.Module([st], []), "tests", "exec"), g); r = "pass"
    except TimeoutError: r = "timeout"
    except BaseException as e: r = "fail:" + type(e).__name__
    finally: signal.alarm(0)
    if is_check:
        print(json.dumps({"i": i, "line": st.lineno, "status": r}), flush=True); i += 1
'''


def ebt_file(path, task, entry):
    code, repaired = code_of(path, entry)
    try:
        body = ast.parse(code).body
    except SyntaxError as e:
        return [], f"syntax: {e}", repaired
    n_checks = sum(not isinstance(s, SETUP) for s in body)
    tmp = mktmp()
    (tmp / "runner.py").write_text(EBT_RUNNER)
    (tmp / "tests.py").write_text(code)
    res = {}
    for sol, fn in solutions(task).items():
        (tmp / f"{sol}.py").write_text(REQUIRED_IMPORTS + "\n" + fn)
        rc, out = run(["python", "runner.py", f"{sol}.py", "tests.py", str(TIMEOUT)], tmp,
                      min(900, TIMEOUT * (len(body) + 1) + 30))
        got = {r["i"]: r["status"] for r in (json.loads(l) for l in out.splitlines() if l.startswith('{"i"'))}
        killed = rc == "timeout"
        res[sol] = [got.get(i, "killed" if killed and i == len(got) else "not_run") for i in range(n_checks)]
    units = [{"i": i, "fixed": res["fixed"][i], "buggy": res["buggy"][i]} for i in range(n_checks)]
    return units, None, repaired


def norm(s):  # unit outcome -> pass / fail ('not_run' after a hard kill counts as neither)
    return "pass" if s == "pass" else ("na" if s == "not_run" else "fail")


def summarize(rec):
    units = rec["units"]
    valid = [u for u in units if norm(u["fixed"]) == "pass"]
    rec.update(n_units=len(units), n_valid=len(valid),
               n_detect=sum(norm(u["buggy"]) == "fail" for u in valid),
               raw_detect=any(norm(u["buggy"]) == "fail" for u in units))
    rec["detect"] = rec["n_detect"] > 0
    return rec


def main():
    kind, out_path, dirs = sys.argv[1], Path(sys.argv[2]), sys.argv[3:]
    done = {json.loads(l)["path"] for l in out_path.open()} if out_path.exists() else set()
    files = [f for d in dirs for f in sorted(Path(d).glob("HumanEval_*.txt")) if str(f) not in done]
    print(f"{kind}: {len(files)} files to evaluate ({len(done)} done)", flush=True)
    with ThreadPoolExecutor(WORKERS) as pool, out_path.open("a") as fo:
        if kind == "ebt":
            def one(f):
                task = "HumanEval/" + f.stem.split("_")[1]
                units, err, rep = ebt_file(f, task, HE[task]["entry_point"])
                return f, task, units, err, rep
            jobs = [pool.submit(one, f) for f in files]
            for j in jobs:
                f, task, units, err, rep = j.result()
                rec = summarize({"path": str(f), "task": task, "kind": kind, "units": units, "error": err,
                                 "repaired": rep, "repair_mode": REPAIR})
                fo.write(json.dumps(rec) + "\n"); fo.flush()
        else:
            prepared = []
            for f in files:
                task = "HumanEval/" + f.stem.split("_")[1]
                tmp, nodes, err, rep = pbt_file(f, task, HE[task]["entry_point"])
                futs = {(n, s): pool.submit(pbt_node, tmp, s, n) for n in nodes for s in ("fixed", "buggy")}
                prepared.append((f, task, nodes, err, futs, rep))
            for f, task, nodes, err, futs, rep in prepared:
                units = [{"node": n, **{s: futs[(n, s)].result()["status"] for s in ("fixed", "buggy")},
                          "tail_fixed": futs[(n, "fixed")].result()["tail"][-300:],
                          "tail_buggy": futs[(n, "buggy")].result()["tail"][-300:]} for n in nodes]
                rec = summarize({"path": str(f), "task": task, "kind": kind, "units": units, "error": err,
                                 "repaired": rep, "repair_mode": REPAIR})
                fo.write(json.dumps(rec) + "\n"); fo.flush()
    print("done", flush=True)


if __name__ == "__main__":
    main()
