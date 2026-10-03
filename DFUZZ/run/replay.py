"""Replay DFUZZ's 37 reproducers (bugs/*/*/bug.py) plus their seed programs (ori.py / original.py), CPU only.

Run inside the dfuzz:arm64 image (see run/replay.sh). Each script runs in its own process, in a scratch cwd
(some scripts write output.tfrecord into cwd; the vendored tree stays untouched). Writes run/replay_results.jsonl.
"""
import csv, json, os, platform, re, signal, subprocess, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = {"torch": "/opt/py38/bin/python", "tf": "/opt/tf215/bin/python"}
TIMEOUT = int(os.environ.get("TIMEOUT", "60"))
REPS = int(os.environ.get("REPS", "3"))  # bug.py repeats: some inputs are random, TensorListConcat is flaky per its issue
EXC = re.compile(r"^([A-Za-z_][\w.]*(?:Error|Exception|Exit|Interrupt))\b")


def tail(s, n=600):
    s = s.strip()
    return s[-n:]


def run(py, script):
    with tempfile.TemporaryDirectory() as cwd:
        t = time.time()
        try:
            p = subprocess.run([py, str(script)], cwd=cwd, capture_output=True, text=True, errors="replace",
                               timeout=TIMEOUT, env={**os.environ, "CUDA_VISIBLE_DEVICES": ""})
        except subprocess.TimeoutExpired as e:
            return {"outcome": "timeout", "rc": None, "secs": TIMEOUT, "exc": None, "fatal_line": None,
                    "stderr_tail": tail((e.stderr or b"").decode(errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or "")),
                    "stdout_tail": ""}
    rc, err = p.returncode, p.stderr
    exc = None
    if rc < 0:
        outcome = signal.Signals(-rc).name  # SIGKILL here usually means the OOM killer
    elif rc == 137:
        outcome = "OOM/137"
    elif rc == 0:
        outcome = "clean"
    else:
        lines = [l for l in err.splitlines() if EXC.match(l)]
        exc = EXC.match(lines[-1]).group(1) if lines else None
        outcome = "exception" if exc else f"exit{rc}"
    fatal = [l for l in err.splitlines() if re.search(r"\] Check failed|^F\d{4}| F tensorflow|malloc|double free|corrupt", l)]
    return {"outcome": outcome, "rc": rc, "secs": round(time.time() - t, 1), "exc": exc,
            "fatal_line": fatal[-1][-300:] if fatal else None,
            "stderr_tail": tail(err), "stdout_tail": tail(p.stdout, 300)}


def reproduces(exp, r):
    if exp["needs_cuda"] == "1":
        return "n/a-needs-cuda"
    want = {"abort": "SIGABRT", "segfault": "SIGSEGV"}.get(exp["expected"])
    if want:
        return "yes" if r["outcome"] == want else "no"
    # runtime_error: Python exception whose text contains the issue's message
    return "yes" if r["outcome"] == "exception" and exp["expected_detail"] in r["stderr_tail"] else "no"


def main():
    rows = list(csv.DictReader(open(ROOT / "run/expected.tsv"), delimiter="\t"))
    probe = "import importlib,sys,platform;print(importlib.import_module(sys.argv[1]).__version__,sys.version.split()[0],platform.machine())"
    versions = {k: subprocess.run([v, "-c", probe, "torch" if k == "torch" else "tensorflow"],
                                  capture_output=True, text=True).stdout.split() for k, v in PY.items()}
    out = open(ROOT / "run/replay_results.jsonl", "w")
    for i, exp in enumerate(rows, 1):
        d = ROOT / "bugs" / exp["dir"]
        py = PY[exp["library"]]
        reps = [run(py, d / "bug.py") for _ in range(REPS)]
        verdicts = [reproduces(exp, r) for r in reps]
        seed = next((d / n for n in ("ori.py", "original.py") if (d / n).exists()), None)
        seed_r = run(py, seed) if seed else None
        rec = {**exp, "lib_version": versions[exp["library"]][0], "python": versions[exp["library"]][1],
               "arch": versions[exp["library"]][2],
               "observed": reps[0]["outcome"], "observed_all": [r["outcome"] for r in reps],
               "reproduces": "yes" if "yes" in verdicts else verdicts[0], "hits": f"{verdicts.count('yes')}/{REPS}",
               "bug_run": reps[0], "seed_file": seed.name if seed else None,
               "seed_outcome": seed_r["outcome"] if seed_r else None, "seed_run": seed_r}
        out.write(json.dumps(rec) + "\n")
        out.flush()
        print(f"[{i}/{len(rows)}] {exp['dir']}: expected={exp['expected']} observed={rec['observed_all']} "
              f"exc={reps[0]['exc']} reproduces={rec['reproduces']} ({rec['hits']}) seed={rec['seed_outcome']}", flush=True)


if __name__ == "__main__":
    main()
