"""Run the unchanged v7 stages against normalized held-out MBPP+ data."""
from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import patch

from .bindings import Paths, bound


def code_bundle(paths):
    """run_v6.bundle's recipe, with all tasks heldout and no design exclusions."""
    from trickcatcher_linefacts import generate, preconditions, run_v4
    tasks, he, _ = run_v4.task_sources(paths.ids())
    out = []
    for raw in tasks:
        n = raw["task"]
        mining = run_v4.mined_task(raw, paths.precond, paths.strategy)
        r = json.loads((paths.facts / f"{n}.json").read_text())
        if r.get("facts_version") != "v3m" or r.get("valid_sha256") != mining["valid_sha256"]:
            raise ValueError(f"task {n}: expected v6 facts under this B5 validator")
        if r.get("base_ok") is not True:
            raise ValueError(f"task {n}: facts base check failed")
        b = generate.bundle(n, he[n], paths.facts)
        b.update(placebo_meta=r["placebo3"], split="heldout", facts_version="v3m",
                 valid_sha256=preconditions.sha(mining["mined_valid_src"]), mined_valid_src=mining["mined_valid_src"])
        b["tool_inputs"] = [c for c in b["tool_inputs"] if c]
        out.append(b)
    return dict(facts_version="v3m", pilot=[], design_excluded=[], tasks=out,
                note="v6 code facts with B5 mined validity; v7 specification facts only when code facts are empty")


def facts(paths, python, workers=12):
    from trickcatcher_linefacts import run_v6
    # run_v6 facts already passes HE/PUT/PRECOND explicitly into facts.py and
    # --validity mined. Rebind its interpreter without changing global sys.
    with patch.object(run_v6, "sys", SimpleNamespace(executable=str(python))):
        run_v6.facts(workers)
    code_bundle(paths)  # fail clearly on missing, stale or invalid fact files


def specfacts(paths, python, workers=12):
    from trickcatcher_linefacts import preconditions, spec_facts as sf
    paths.specfacts.mkdir(parents=True, exist_ok=True)
    tasks = [t for t in code_bundle(paths)["tasks"] if not t["concept_facts"]]
    def one(t):
        _, _, params = preconditions.specification(t)
        job = dict(entry=t["entry"], base=sf.base_args(t["base"]),
                   params=[a.arg for a in params.posonlyargs + params.args], valid_src=t["mined_valid_src"])
        jp, rp = paths.specfacts / f"{t['task']}.job.json", paths.specfacts / f"{t['task']}.json"
        if rp.exists():
            if not jp.exists() or json.loads(jp.read_text()) != job:
                raise ValueError("spec-fact cache changed; use a fresh directory")
            return
        jp.write_text(json.dumps(job, default=repr))
        env = {"PATH": os.defpath, "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1"}
        result = subprocess.run(["timeout", "600", "unshare", "-rn", str(python), "-I", "-B", sf.__file__,
                                 "worker", str(jp), str(rp)], env=env, capture_output=True)
        if result.returncode or not rp.exists():
            raise RuntimeError(f"task {t['task']}: spec-facts worker failed (rc={result.returncode})")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(one, tasks))
    print(f"v7 spec facts: {len(tasks)} tasks with empty code facts")


def bundle(paths):
    from trickcatcher_linefacts import oracle_b01 as ob, run_v4
    out = code_bundle(paths)
    for t in out["tasks"]:
        if t["concept_facts"]:
            continue
        r = json.loads((paths.specfacts / f"{t['task']}.json").read_text())
        if r["facts"]:
            top = r["facts"][:3]
            t.update(concept_meta=top, concept_facts=[f["text"] for f in top],
                     placebo_meta=r["placebo"][:3], placebo_facts=[f["text"] for f in r["placebo"][:3]],
                     tool_inputs=[f["witness_call"] for f in top if f["witness_call"]], spec_facts=True)
    hybrid = copy.deepcopy(out)
    for t in hybrid["tasks"]:
        c = run_v4.mined_task(t, paths.precond, paths.strategy)
        for key in ("strategy_src", "strategy_sha256", "strategy_fallback", "mining_summary"):
            t[key] = c[key]
        t["facts_version"] = "v4"
        for key in ("concept_meta", "placebo_meta"):
            for f in t[key]:
                if f["kind"] == "MUTANT" and "mutant_src" not in f:
                    f["mutant_src"] = ob.mutant_source(t["put"], f["k"])
    hybrid["facts_version"] = "v4"
    from trickcatcher_linefacts.v4_runtime import immutable
    immutable(paths.all, out); immutable(paths.hybrid, hybrid)
    print(f"v7 bundle: {len(hybrid['tasks'])} held-out tasks; "
          f"with facts: {sum(bool(t['concept_facts']) for t in hybrid['tasks'])}; "
          f"with spec facts: {sum(bool(t.get('spec_facts')) for t in hybrid['tasks'])}")
    return hybrid


def check_run(paths):
    from trickcatcher_linefacts import v4_prompts
    tasks = json.loads((paths.generation / "tasks.json").read_text())["tasks"]
    if {t["task"] for t in tasks} != set(paths.ids()) or any(t["split"] != "heldout" for t in tasks):
        raise ValueError("run must contain every selected task, split heldout")
    rows = [json.loads(l) for l in (paths.generation / "eval.jsonl").read_text().splitlines()]
    expected = {(n, arm, s) for n in paths.ids() for arm in v4_prompts.ARMS for s in range(3)}
    keys = [(r["task"], r["arm"], r["sample"]) for r in rows]
    if len(set(keys)) != len(keys) or set(keys) != expected:
        raise ValueError("expected complete heldout x seven arms x K=3 evaluation")


def oracle(paths, action, python=None, workers=16, no_llm=False):
    from trickcatcher_linefacts import oracle_b01 as ob
    from . import reporting
    check_run(paths)
    paths.oracle.mkdir(parents=True, exist_ok=True)
    if action == "collect":
        ob.collect(paths.generation, paths.oracle)
        # Retain all tasks even if a task's completions contain no callable test.
        cp = paths.oracle / "calls.json"; calls = json.loads(cp.read_text())
        for n in paths.ids(): calls.setdefault(str(n), [])
        cp.write_text(json.dumps(calls))
        return
    if action == "llm":
        ob.llm(paths.generation, paths.oracle, workers=workers, stages=("b1", "ref", "post"))
        return
    # execute/worker/decide/judges are unchanged. Only the worker entry handles
    # the normalized tolerant base-check AST for postcondition trusted pairs.
    with patch.object(ob, "__file__", str(Path(__file__).with_name("worker.py"))), \
         patch.object(ob, "sys", SimpleNamespace(executable=str(python))):
        ex = ob.execute(paths.generation, paths.oracle, workers=min(workers, 12))
    missing = set(map(str, paths.ids())) - set(ex)
    if missing:
        raise RuntimeError(f"oracle workers missing: {sorted(missing)}")
    jd = ob.judges(ex, paths.generation, paths.oracle, workers=16, use_llm=not no_llm)
    reporting.oracle_report(paths, ex, jd)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    for name in ("mine", "facts", "specfacts", "bundle", "arms", "evaluate", "oracle"):
        s = sub.add_parser(name)
        if name == "oracle":
            s.add_argument("action", choices=("collect", "llm", "score"))
            s.add_argument("--no-llm", action="store_true", help="score only; skip uncached B4 judge requests")
        s.add_argument("--python", type=Path, default=os.environ.get("V4_PYTHON"))
        s.add_argument("--workers", type=int, default=12 if name in ("facts", "specfacts") else 16)
        s.add_argument("--root", type=Path, help="held-out data root (default out/heldout_mbpp)")
    a = p.parse_args()
    if a.workers < 1: p.error("workers must be positive")
    if a.command == "oracle" and a.no_llm and a.action != "score":
        p.error("--no-llm is only available for oracle score")
    paths = Paths(a.root.resolve()) if a.root else Paths()
    paths.ids()
    from trickcatcher_linefacts import evaluate, run_v4, v4_runtime
    requires_python = a.command not in ("bundle", "oracle") or getattr(a, "action", None) == "score"
    python = v4_runtime.interpreter(a.python) if requires_python else None
    with bound(paths):
        if a.command == "mine":
            from trickcatcher_linefacts.llm_client import Client
            tasks, _, _ = run_v4.task_sources(paths.ids())
            run_v4.mine(tasks, Client(paths.strategy / "cache", workers=a.workers), paths.precond,
                        paths.strategy, python, a.workers)
        elif a.command == "facts": facts(paths, python, a.workers)
        elif a.command == "specfacts": specfacts(paths, python, a.workers)
        elif a.command == "bundle": bundle(paths)
        elif a.command == "arms":
            tasks = json.loads(paths.hybrid.read_text())["tasks"]
            if [t["task"] for t in tasks] != paths.ids():
                raise ValueError("bundle must contain every selected held-out task")
            run_v4.run(tasks, paths.generation, python, k=3, workers=a.workers)
        elif a.command == "evaluate":
            evaluate.evaluate(paths.generation / "tasks.json", paths.generation / "gen.jsonl",
                              paths.generation / "eval.jsonl", python)
            check_run(paths)
            from .reporting import evaluation_report
            evaluation_report(paths)
        else: oracle(paths, a.action, python, a.workers, a.no_llm)


if __name__ == "__main__":
    main()
