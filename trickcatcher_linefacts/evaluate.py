"""Score generated assertions: detection, false alarms, delivery (did the test reach the concept facts?).

  python3 trickcatcher_linefacts/evaluate.py            # all rows of out/gen.jsonl -> out/eval.jsonl, then report
  python3 trickcatcher_linefacts/evaluate.py report     # report only

Per assertion (sandboxed: one `unshare -rn python3 -I` process per task):
  canon_ok  passes with the HumanEval+ canonical solution in place of the PUT (oracle + input valid)
  put_ok    passes on the PUT
  detects   canon_ok and not put_ok          false alarm: not canon_ok
  hits      for each of the task's concept facts, whether some call in the assertion reaches it
            (OUTCOME: the missing cell is hit; STMT: one of its lines runs; MUTANT: PUT and mutant outputs differ)
Delivery is measured against the concept facts in every arm, so arms can be compared on it.
"""
import argparse, ast, json, os, re, subprocess, sys
from math import comb
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
HEP = REPO / "PBT_EdgeCases/run/data/humaneval_plus.jsonl"
OUT = HERE / "out"
sys.path.insert(0, str(REPO))
from trickcatcher_linefacts.prompts import ARMS
MAX_ASSERTS = 10


def extract_asserts(text):
    m = re.findall(r"```(?:python)?\n(.*?)```", text, re.S)
    code = "\n".join(m) if m else text
    try:
        nodes = [n for n in ast.walk(ast.parse(code)) if isinstance(n, ast.Assert)]
        out = [ast.unparse(n) for n in nodes]
    except SyntaxError:
        out = []
        for ln in code.splitlines():
            ln = ln.strip()
            if ln.startswith("assert"):
                try:
                    ast.parse(ln)
                    out.append(ln)
                except SyntaxError:
                    pass
    return out[:MAX_ASSERTS]


# ---------------------------------------------------------------- sandboxed worker
def worker(job_path, out_path):
    sys.path.insert(0, str(HERE))
    import contextlib, io
    from tracer import HOOKS, alarm, call, dcopy, instrument, load_module, same, trace, fact_hit
    from trickcatcher_linefacts import spec_facts
    from facts import make_mutant

    job = json.load(open(job_path))
    entry, put_src = job["entry"], job["put"]
    pg = load_module(put_src)
    put = pg[entry]
    cg = load_module(job["canon"], filename="<canon>")
    canon = cg[entry]
    code, _ = instrument(put_src)
    iput = load_module(code, HOOKS)[entry]
    facts = job["facts"]
    mutants = {}
    for i, f in enumerate(facts):
        if f["kind"] == "MUTANT":
            try:
                mutants[i] = load_module(f['mutant_src'] if 'mutant_src' in f else make_mutant(put_src, f["k"])[0])[entry]
            except BaseException:
                pass

    def run_assert(src, fn, g, record):
        calls = []

        def wrapped(*a, **k):
            if record:
                calls.append((dcopy(a), dcopy(k)))
            return fn(*a, **k)

        ns = dict(g)
        ns[entry] = wrapped
        try:
            with contextlib.redirect_stdout(io.StringIO()), alarm(5.0):
                exec("import math\n" + src, ns)
            return "ok", calls
        except AssertionError:
            return "fail", calls
        except BaseException as e:
            return type(e).__name__, calls

    rows = []
    for r in job["rows"]:
        res = []
        assertion_calls = []
        for src in r["asserts"]:
            cst, _ = run_assert(src, canon, cg, False)
            pst, calls = run_assert(src, put, pg, True)
            assertion_calls.extend(calls)
            hits = [False] * len(facts)
            for a in calls[:20]:
                cells, lines, pst_, pval_ = trace(iput, a)
                pout = (pst_, pval_)
                for i, f in enumerate(facts):
                    if hits[i]:
                        continue
                    pout = call(put, a) if f["kind"] == "MUTANT" else None
                    mout = call(mutants[i], a) if i in mutants else None
                    hits[i] = (spec_facts.in_class(f["input_class"]["cls"], a[0][f["input_class"]["param"]])  # v7 spec facts
                               if "input_class" in f else fact_hit(f, (cells, lines, pst_, pval_), pout, mout))
            res.append({"src": src, "canon": cst, "put": pst, "hits": hits})
        result = {k: r[k] for k in ("task", "arm", "sample")} | {"asserts": res}
        if job.get("gen2"):
            from trickcatcher_linefacts.gen_evaluation import input_metrics
            result.update({key: r[key] for key in r if key not in ("text", "asserts", "task", "arm", "sample")})
            result["input_metrics"] = input_metrics(job, r, put, canon, iput, mutants, assertion_calls)
        rows.append(result)
    json.dump(rows, open(out_path, "w"))


# ---------------------------------------------------------------- driver
def evaluate(tasks_path=OUT / "pilot_tasks.json", gen_path=OUT / "gen.jsonl", eval_path=OUT / "eval.jsonl", python=None):
    if json.load(open(tasks_path)).get("facts_version") == "v4":
        from trickcatcher_linefacts.v4_evaluation import evaluate as v4_evaluate
        return v4_evaluate(tasks_path, gen_path, eval_path, python)
    tasks = {t["task"]: t for t in json.load(open(tasks_path))["tasks"]}
    hep = {int(r["task_id"].split("/")[1]): r for r in map(json.loads, open(HEP))}
    gen = [json.loads(l) for l in open(gen_path)]
    gen2 = any("run_id" in row for row in gen)
    contracts = None
    mined = gen2 and all(t.get("facts_version") == "v3m" for t in tasks.values())
    if gen2 and not mined:
        from trickcatcher_linefacts.gen_inputs import load_contracts
        contracts = load_contracts()
    eval_path.parent.mkdir(parents=True, exist_ok=True)
    jobs = eval_path.parent / (eval_path.stem + "_jobs")
    jobs.mkdir(exist_ok=True)
    allrows = []
    for n, t in sorted(tasks.items()):
        rows = [{"task": g["task"], "arm": g["arm"], "sample": g["sample"], "asserts": extract_asserts(g["text"])}
                for g in gen if g["task"] == n]
        if not rows:
            continue
        job = {"entry": t["entry"], "put": t["put"], "canon": hep[n]["prompt"] + hep[n]["canonical_solution"],
               "facts": t["concept_meta"], "rows": rows}
        if gen2:
            if mined:
                import hashlib
                code = t["mined_valid_src"]
                if hashlib.sha256(code.encode()).hexdigest() != t["valid_sha256"]:
                    raise ValueError("mined validator hash mismatch")
                job["mined_src"] = code
            else:
                job["contract_src"] = contracts[n]["contract_src"]
            job.update(gen2=True, rows=[dict(g, asserts=extract_asserts(g["text"])) for g in gen if g["task"] == n])
        jp, op = jobs / f"{n}.json", jobs / f"{n}.out.json"
        json.dump(job, open(jp, "w"))
        p = subprocess.run(["timeout", "-k", "5", "1800", "unshare", "-rn", sys.executable, "-I", "-B", __file__,
                            "worker", str(jp), str(op)], capture_output=True, text=True)
        if p.returncode != 0:
            print(f"task {n}: worker rc={p.returncode} {p.stderr[-300:]}")
            raise RuntimeError(f"task {n}: evaluation worker failed; output not written")
        allrows += json.load(open(op))
    with open(eval_path, "w") as fh:
        for r in allrows:
            fh.write(json.dumps(r) + "\n")


def sign_p(b, c):
    n, k = b + c, min(b, c)
    return 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


def report(tasks_path=OUT / "pilot_tasks.json", eval_path=OUT / "eval.jsonl", compare_paths=()):
    rows = [json.loads(l) for l in open(eval_path)]
    if compare_paths or any("run_id" in row for row in rows):
        from trickcatcher_linefacts.gen_evaluation import report as gen_report
        return gen_report(tasks_path, eval_path, compare_paths)
    bundles = {t["task"]: t for t in json.load(open(tasks_path))["tasks"]}
    tasks = sorted(bundles)
    if not rows:
        print("No evaluated rows.")
        return
    K = max(r["sample"] for r in rows) + 1
    det = {}  # (task, arm) -> number of samples that detect
    print(f"{len(tasks)} tasks, K={K}\n")
    print(f"{'arm':10s} {'detect/sample':>13s} {'any-of-K':>8s} {'asserts':>7s} {'false-alarm':>11s} {'delivery':>8s}")
    for arm in ARMS:
        rs = [r for r in rows if r["arm"] == arm]
        n_as = sum(len(r["asserts"]) for r in rs)
        fa = sum(a["canon"] != "ok" for r in rs for a in r["asserts"])
        nf = sum(len(bundles[r["task"]]["concept_meta"]) for r in rs)
        hit = sum(any(a["hits"][i] for a in r["asserts"]) for r in rs if r["asserts"]
                  for i in range(len(r["asserts"][0]["hits"])))
        for t in tasks:
            det[t, arm] = sum(any(a["canon"] == "ok" and a["put"] != "ok" for a in r["asserts"])
                              for r in rs if r["task"] == t)
        per_sample = sum(det[t, arm] for t in tasks) / K
        anyk = sum(det[t, arm] > 0 for t in tasks)
        print(f"{arm:10s} {per_sample:13.1f} {anyk:8d} {n_as / max(1, len(rs)):7.1f} "
              f"{fa / max(1, n_as):11.0%} {hit / max(1, nf):8.0%}")
    print("\npaired per task (samples detecting, concept vs other): wins/losses, sign-test p")
    for arm in (a for a in ARMS if a != "concept"):
        w = sum(det[t, "concept"] > det[t, arm] for t in tasks)
        l = sum(det[t, "concept"] < det[t, arm] for t in tasks)
        print(f"  concept vs {arm:9s} {w}/{l}  p={sign_p(w, l):.2f}")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "worker":
        worker(sys.argv[2], sys.argv[3])
    else:
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd", nargs="?", choices=["evaluate", "report"], default="evaluate")
        ap.add_argument("--tasks", type=Path, default=OUT / "pilot_tasks.json")
        ap.add_argument("--gen", type=Path, default=OUT / "gen.jsonl")
        ap.add_argument("--eval", type=Path, default=OUT / "eval.jsonl")
        ap.add_argument("--compare-eval", type=Path, action="append", default=[], help="merge scored rows for paired reports only")
        ap.add_argument("--python", type=Path, help="v4 dedicated venv interpreter (or V4_PYTHON)")
        a = ap.parse_args()
        if a.cmd == "evaluate":
            evaluate(a.tasks, a.gen, a.eval, a.python)
        report(a.tasks, a.eval, a.compare_eval)


if __name__ == "__main__":
    main()
