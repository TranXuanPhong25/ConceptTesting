"""VibePass (arXiv 2603.15921, RQ1) metrics on existing dev runs. CPU only, no LLM calls.

Per unique call of a sample (deduplicated by call, first assertion kept, as in oracle_b01.score):
  V_I   input satisfies the EvalPlus contract (oracle exec `valid`; arg-parse errors count as invalid)
  D_I   V_I and PUT(x) != canonical(x)   (analysis/worker.py, sandboxed: tolerant float compare with the task's atol,
        PUT exception/timeout = different; canonical error on a valid input = not D_I)
  V_IO  V_I and the oracle emits an expected value equal to canonical(x)   (oracle_b01.decide canon_ok)
  D_IO  D_I and the oracle's expected value equals canonical(x)
Oracles: o0 (the LLM's own expected value: its assertion passes on canonical), b1one, ref, full (ref+judge+post;
ref+post where no judge responses exist). An oracle that abstains gives no expected value.
Per sample: the sample has at least one such call; reported as samples/K (= tasks per run, out of n tasks).

  python3 -B trickcatcher_linefacts/analysis/vibepass_metrics.py          (from the repo root; cached sandbox results)
"""
import collections, hashlib, json, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

H = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(H.parent))
from trickcatcher_linefacts import oracle_b01 as ob

OUT = H / "out/vibepass_metrics"
WORKER = H / "analysis/worker.py"
K = 3
ORACLES = ("o0", "b1one", "ref", "full")
RUNS = {  # name: (run dir, oracle dir, tasks dropped, arms whose o0 is not meaningful)
    "v7": ("gen2_qwen7b_v7hyb_v4_r2", "oracle_v7hyb", (), ()),
    "v8-strict": ("gen2_qwen7b_v8strict_est", "oracle_v8strict_est", (),
                  ("concept-hybrid", "plain-hybrid", "placebo-hybrid")),
    "evalmitigate": ("gen2_qwen7b_evalmitigate", "oracle_evalmitigate", (), ()),
    "advhyb-partial": ("gen2_qwen7b_advhyb_v4_partial", "oracle_advhyb_partial", (160,), ()),
}
PAIRS = {"v7": [("concept-hybrid", "plain-hybrid"), ("concept-hybrid", "toolinput"), ("concept-hybrid", "placebo-hybrid"),
                ("plain-hybrid", "toolinput")],
         "v8-strict": [("concept-hybrid", "plain-hybrid"), ("concept-hybrid", "toolinput"),
                       ("concept-hybrid", "placebo-hybrid"), ("plain-hybrid", "toolinput")],
         "advhyb-partial": [("advdoc-hybrid", "advdoc-plainhybrid")],
         "evalmitigate": [("advdoc", "onlydoc")]}


def load(name):
    run, ora, drop, _ = RUNS[name]
    run, ora = H / "out" / run, H / "out" / ora
    tasks, rows = ob.load_run(run)
    calls = json.loads((ora / "calls.json").read_text())
    if all((ora / "exec" / f"{t}.json").exists() for t in calls):
        ex = {t: json.loads((ora / "exec" / f"{t}.json").read_text()) for t in calls}
    else:
        ex = ob.execute(run, ora, 12)
    jd = ob.judges(ex, run, ora, use_llm=False)
    rows = [r for r in rows if r["split"] == "dev" and r["task"] not in drop and str(r["task"]) in ex]
    has_b1 = (ora / "b1_responses.json").exists()
    return tasks, rows, ex, jd, dict(b1=has_b1, judge=bool(jd))


def unique_calls(r, entry):
    seen, out = set(), []
    for a in r["asserts"]:
        c = ob.call_of(a["src"], entry)
        if c is None or c in seen:
            continue
        seen.add(c); out.append((c, a))
    return out


# ---------------------------------------------------------------- PUT vs canonical (sandbox, cached per chunk)
def reveal_status(all_calls, tasks, workers=12, chunk=80):
    hep = {int(r["task_id"].split("/")[1]): r for r in map(json.loads, ob.HEP.open())}
    jobs = []
    for t, cs in sorted(all_calls.items()):
        cs = sorted(cs)
        for i in range(0, len(cs), chunk):
            part = cs[i:i + chunk]; h = hep[t]
            job = dict(entry=tasks[t]["entry"], put=tasks[t]["put"], canon=h["prompt"] + h["canonical_solution"],
                       contract=h["prompt"] + h["contract"] + "\n    pass\n", atol=h["atol"], calls=part)
            key = hashlib.sha256(json.dumps(job, sort_keys=True).encode()).hexdigest()[:16]
            jobs.append((t, key, job))
    (OUT / "jobs").mkdir(parents=True, exist_ok=True); (OUT / "res").mkdir(parents=True, exist_ok=True)

    def run(item):
        t, key, job = item
        res = OUT / "res" / f"{t}_{key}.json"
        if res.exists():
            return
        jp = OUT / "jobs" / f"{t}_{key}.job.json"; jp.write_text(json.dumps(job))
        subprocess.run(["timeout", "-k", "5", "900", "unshare", "-rn", sys.executable, "-I", "-B", str(WORKER),
                        str(jp), str(res)], check=False, capture_output=True, cwd=OUT / "jobs")

    with ThreadPoolExecutor(workers) as pool:
        list(pool.map(run, jobs))
    status, missing = collections.defaultdict(dict), []
    for t, key, job in jobs:
        res = OUT / "res" / f"{t}_{key}.json"
        if res.exists():
            status[t].update(json.loads(res.read_text()))
        else:
            missing.append((t, key, len(job["calls"])))
    return status, missing


def sign_p(w, l):
    return ob.sign_p(w, l)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    data = {n: load(n) for n in RUNS}
    all_calls, all_tasks = collections.defaultdict(set), {}
    for n, (tasks, rows, ex, jd, avail) in data.items():
        all_tasks.update(tasks)
        for r in rows:
            all_calls[r["task"]].update(c for c, _ in unique_calls(r, tasks[r["task"]]["entry"]))
    status, missing = reveal_status(all_calls, all_tasks)
    if missing:
        print("sandbox chunks without result:", missing)

    metrics, report, checks = {}, [], collections.Counter()
    for n, (tasks, rows, ex, jd, avail) in data.items():
        notmeaningful = RUNS[n][3]
        A = collections.defaultdict(lambda: collections.Counter())        # arm -> assertion counts
        S = collections.defaultdict(lambda: collections.Counter())        # arm -> sample counts
        P = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.Counter()))  # arm -> task -> samples
        for r in rows:
            t, arm = r["task"], r["arm"]; ts = str(t)
            samp = collections.Counter()
            for c, a in unique_calls(r, tasks[t]["entry"]):
                rec = ex[ts]["calls"].get(c, {})
                st = status[t].get(c)
                vi = rec.get("error") is None and rec.get("valid") is True
                if st is None:
                    checks[f"{n}: no sandbox status"] += 1
                elif vi != (st in ("reveal", "same", "canon_err")):
                    checks[f"{n}: validity disagreement exec vs worker"] += 1
                di = vi and st == "reveal"
                checks[f"{n}: canon_err on valid"] += vi and st == "canon_err"
                f = dict(n=1, V_I=vi, D_I=di)
                for o in ORACLES:
                    emit, cok, pok = ob.decide(o, rec, jd.get((ts, c)), ob.expected_of(a["src"]), a)
                    f[f"abst_{o}"] = not emit
                    f[f"abstV_{o}"] = vi and not emit
                    f[f"V_IO_{o}"] = vi and emit and cok
                    f[f"D_IO_{o}"] = di and emit and cok
                    legacy = emit and cok and not pok and rec.get("valid", True)   # oracle_b01 detection
                    f[f"det_{o}"] = legacy
                    if legacy != (di and emit and cok):
                        checks[f"{n}: legacy det != D_IO ({o})"] += 1
                for k, v in f.items():
                    A[arm][k] += v; samp[k] |= bool(v)
            S[arm]["n"] += 1
            for k, v in samp.items():
                if k != "n":
                    S[arm][k] += v; P[arm][t][k] += v
        metrics[n] = dict(assertions={a: dict(v) for a, v in A.items()}, samples={a: dict(v) for a, v in S.items()},
                          per_task={a: {t: dict(c) for t, c in v.items()} for a, v in P.items()}, avail=avail)

        ntask = len({r["task"] for r in rows})
        arms = sorted(A, key=lambda a: -S[a]["D_I"])
        orc = [o for o in ORACLES if not (o == "b1one" and not avail["b1"])]
        full_note = "full = ref+judge+post" if avail["judge"] else "full = ref+post (no judge responses in this oracle dir)"
        report.append(f"\n## {n}  ({RUNS[n][0]} + {RUNS[n][1]}; dev, {ntask} tasks, K={K}; {full_note}"
                      + ("; b1one not available" if not avail["b1"] else "") + ")")
        if notmeaningful:
            report.append(f"o0 marked * for {', '.join(notmeaningful)}: rebuilt arms carry placeholder expected values.")
        # per assertion
        report.append("\nPer assertion (% of unique calls). Columns V_IO/D_IO per oracle; abst = oracle abstains (% of all calls).\n")
        hdr = "| arm | calls/sample | V_I | D_I | " + " | ".join(f"V_IO {o} | D_IO {o} | abst {o}" for o in orc) + " |"
        report.append(hdr); report.append("|" + "---|" * (hdr.count("|") - 1))
        for arm in arms:
            a = A[arm]; pc = lambda k: f"{100 * a[k] / max(1, a['n']):.1f}"
            cells = []
            for o in orc:
                star = "*" if o == "o0" and arm in notmeaningful else ""
                cells += [pc(f"V_IO_{o}") + star, pc(f"D_IO_{o}") + star, pc(f"abst_{o}")]
            report.append(f"| {arm} | {a['n'] / S[arm]['n']:.1f} | {pc('V_I')} | {pc('D_I')} | " + " | ".join(cells) + " |")
        # per sample
        report.append(f"\nPer sample (samples with >=1 such call / K = tasks per run, out of {ntask}).\n")
        hdr = "| arm | V_I | D_I | " + " | ".join(f"V_IO {o} | D_IO {o}" for o in orc) + " |"
        report.append(hdr); report.append("|" + "---|" * (hdr.count("|") - 1))
        for arm in arms:
            s = S[arm]; pk = lambda k: f"{s[k] / K:.1f}"
            cells = []
            for o in orc:
                star = "*" if o == "o0" and arm in notmeaningful else ""
                cells += [pk(f"V_IO_{o}") + star, pk(f"D_IO_{o}") + star]
            report.append(f"| {arm} | {pk('V_I')} | {pk('D_I')} | " + " | ".join(cells) + " |")
        # decomposition
        report.append("\nGaps. fault-hypothesis = V_I - D_I; output-validation = D_I - D_IO(oracle). "
                      "Assertion level in % points of calls; sample level in tasks per run.\n")
        hdr = "| arm | FH (assert) | FH (sample) | " + " | ".join(f"OV {o} (assert) | OV {o} (sample)" for o in orc) + " |"
        report.append(hdr); report.append("|" + "---|" * (hdr.count("|") - 1))
        for arm in arms:
            a, s = A[arm], S[arm]
            pa = lambda x, y: f"{100 * (a[x] - a[y]) / max(1, a['n']):.1f}"
            ps = lambda x, y: f"{(s[x] - s[y]) / K:.1f}"
            cells = []
            for o in orc:
                star = "*" if o == "o0" and arm in notmeaningful else ""
                cells += [pa("D_I", f"D_IO_{o}") + star, ps("D_I", f"D_IO_{o}") + star]
            report.append(f"| {arm} | {pa('V_I', 'D_I')} | {ps('V_I', 'D_I')} | " + " | ".join(cells) + " |")
        # paired
        if n in PAIRS:
            report.append("\nPaired per task (samples with the property, 0..K), wins/losses, two-sided sign test.\n")
            keys = ["D_I", "V_I"] + [f"D_IO_{o}" for o in ("ref", "full")]
            report.append("| pair | " + " | ".join(keys) + " |"); report.append("|" + "---|" * (len(keys) + 1))
            T = sorted({r["task"] for r in rows})
            for x, y in PAIRS[n]:
                if x not in P or y not in P:
                    continue
                cells = []
                for k in keys:
                    w = sum(P[x][t][k] > P[y][t][k] for t in T); l = sum(P[x][t][k] < P[y][t][k] for t in T)
                    cells.append(f"{w}/{l} p={sign_p(w, l):.3g}")
                report.append(f"| {x} vs {y} | " + " | ".join(cells) + " |")
    report.append("\nConsistency checks: " + json.dumps(dict(checks)))
    report.append(f"sandbox chunks without result: {missing}")
    (OUT / "metrics.json").write_text(json.dumps(metrics, default=str))
    (OUT / "tables.md").write_text("\n".join(report) + "\n")
    print("\n".join(report))


if __name__ == "__main__":
    main()
