"""Score ULT generations: Pass@k, LCov@k, BCov@k, and (optional) Mut@k.

The vendored `Ray/main.py` has no code that builds the `data/*_mods/` trees its
pytest step expects, and its __main__ is hard-wired to the authors' own files,
so this module lays out each task itself and reuses the authors' helpers where
they exist (`code_import` header, `rename_test_functions`, the cosmic-ray toml).

Choices made here, stated so they can be checked against the paper:
  * Every generated test is written to its own file, so one syntax error does
    not take the other tests down with it.
  * Test files add `from mod import <func_name>` after the authors'
    `from mod import *`, which silently skips `_private` functions.
  * Generated tests all start `def test_<func>()` (the prompt demands it), so
    they are renamed with the authors' `rename_test_functions` before running.
  * Pass@k = passing tests among the first k / (N * k).
  * Coverage counts only *passing* tests among the first k (TestEval
    convention), restricted to the lines/branches of the function under test
    (the shared import header is excluded).
  * Mut@k (only for --mutation-ks, default 5) runs cosmic-ray (authors' toml) with the passing tests among the
    first k; a task with no passing test scores 0.

  python -m ULT_concept.evaluate --gen ULT_concept/out/ULT_Lite_baseline.jsonl
  python -m ULT_concept.evaluate --ground-truth   # sanity check on test_list
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENDOR = ROOT / "vendor_ULT"
EXEC_PY = ROOT / ".venv_exec" / "bin" / "python"
KS = (1, 2, 5)

_spec = importlib.util.spec_from_file_location("ult_main", VENDOR / "Ray" / "main.py")
ult_main = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ult_main)
CODE_IMPORT = ult_main.code_import
HEADER = CODE_IMPORT + "\n\n"

FENCE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.S)


def extract_code(text: str) -> str:
    blocks = FENCE.findall(text or "")
    return "\n\n".join(blocks) if blocks else (text or "")


def run(cmd: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None


def pass_results(work: Path, files: list[str]) -> dict[str, bool]:
    """file -> every test in it passed (and at least one test was collected)."""
    res = run([str(EXEC_PY), "-m", "pytest", "-q", "-p", "no:cacheprovider", "--timeout=10",
               "--junitxml=junit.xml", *files], work, timeout=60 + 15 * len(files))
    status = {f: False for f in files}
    junit = work / "junit.xml"
    if res is None or not junit.exists():
        return status
    per_file: dict[str, list[bool]] = {}
    for case in ET.parse(junit).iter("testcase"):
        mod = (case.get("classname") or "").rsplit(".", 1)[-1] + ".py"
        ok = not any(child.tag in ("failure", "error", "skipped") for child in case)
        per_file.setdefault(mod, []).append(ok)
    for f in files:
        status[f] = bool(per_file.get(f)) and all(per_file[f])
    return status


def coverage(work: Path, files: list[str], fut_start: int, fut_end: int) -> tuple[float, float]:
    """Line and branch coverage of mod.py lines [fut_start, fut_end] by `files`."""
    if not files:
        return 0.0, 0.0
    for stale in (".coverage", "cov.json"):
        (work / stale).unlink(missing_ok=True)
    run([str(EXEC_PY), "-m", "coverage", "run", "--branch", "--include=mod.py", "-m", "pytest", "-q",
         "-p", "no:cacheprovider", "--timeout=10", *files], work, timeout=60 + 15 * len(files))
    run([str(EXEC_PY), "-m", "coverage", "json", "-o", "cov.json", "--include=mod.py"], work, timeout=60)
    if not (work / "cov.json").exists():
        return 0.0, 0.0
    lines_all = json.loads((work / "cov.json").read_text())["files"].get("mod.py")
    if not lines_all:
        return 0.0, 0.0

    def inside(line: int) -> bool:
        return fut_start <= line <= fut_end

    hit = [l for l in lines_all.get("executed_lines", []) if inside(l)]
    miss = [l for l in lines_all.get("missing_lines", []) if inside(l)]
    bhit = [b for b in lines_all.get("executed_branches", []) if inside(b[0])]
    bmiss = [b for b in lines_all.get("missing_branches", []) if inside(b[0])]
    lcov = len(hit) / (len(hit) + len(miss)) if hit or miss else 1.0
    bcov = len(bhit) / (len(bhit) + len(bmiss)) if bhit or bmiss else 1.0
    return lcov, bcov


def mutation(work: Path, files: list[str], timeout: int) -> dict:
    """cosmic-ray with the authors' toml; test-command runs only the given (passing) files."""
    if not files:
        return {"total": 0, "killed": 0, "score": 0.0}
    mdir = work / f"mut_{len(files)}_{'_'.join(f[5:-3] for f in files)}"
    if mdir.exists():
        shutil.rmtree(mdir)
    mdir.mkdir()
    shutil.copy(work / "mod.py", mdir / "mod.py")
    for f in files:
        shutil.copy(work / f, mdir / f)
    toml = ult_main.toml_template.format(timeout=timeout).replace(
        'test-command = "pytest test.py"', f'test-command = "{EXEC_PY} -m pytest -x -q -p no:cacheprovider {" ".join(files)}"')
    (mdir / "cosmic-ray.toml").write_text(toml)
    cr = str(EXEC_PY.parent / "cosmic-ray")
    run([cr, "init", "cosmic-ray.toml", "cr.sqlite"], mdir, 120)
    run([cr, "exec", "cosmic-ray.toml", "cr.sqlite"], mdir, 3600)
    rep = run([str(EXEC_PY.parent / "cr-report"), "cr.sqlite", "--show-pending"], mdir, 120)
    out = rep.stdout if rep else ""
    total = int(m.group(1)) if (m := re.search(r"total jobs:\s*(\d+)", out)) else 0
    surv = int(m.group(1)) if (m := re.search(r"surviving mutants:\s*(\d+)", out)) else 0
    done = int(m.group(1)) if (m := re.search(r"complete:\s*(\d+)", out)) else 0
    killed = done - surv
    return {"total": total, "complete": done, "killed": killed, "score": killed / total if total else 0.0}


def evaluate_task(args: tuple) -> dict:
    task, tests, out_dir, with_mutation = args
    work = Path(out_dir) / f"task_{task['task_id']}"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    (work / "mod.py").write_text(HEADER + task["code"] + "\n")
    fut_start = HEADER.count("\n") + 1
    fut_end = fut_start + task["code"].count("\n")

    files = []
    for i, test in enumerate(tests[: max(KS)]):
        body = ult_main.rename_test_functions(extract_code(test))
        name = f"test_{i}.py"
        # `import *` skips underscore names, so the function under test is imported by name too.
        (work / name).write_text(CODE_IMPORT + f"\n\nfrom mod import *\nfrom mod import {task['func_name']}\n\n"
                                 + body + "\n")
        files.append(name)
    passed = pass_results(work, files)

    row = {"task_id": task["task_id"], "func_name": task["func_name"], "n_tests": len(files),
           "passed": [passed[f] for f in files]}
    for k in KS:
        ok = [f for f in files[:k] if passed[f]]
        row[f"pass@{k}"] = len(ok) / k
        row[f"lcov@{k}"], row[f"bcov@{k}"] = coverage(work, ok, fut_start, fut_end)
        if k in with_mutation:
            row[f"mut@{k}"] = mutation(work, ok, timeout=10)
    return row


def ground_truth_tests(task: dict) -> list[str]:
    return [f"def test_{task['func_name']}():\n    {a}" for a in task["test_list"]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", help="generation jsonl from ULT_concept.generate")
    ap.add_argument("--ground-truth", action="store_true", help="score ULT_Lite's own test_list instead")
    ap.add_argument("--dataset", default="ULT_Lite")
    ap.add_argument("--mutation", action="store_true")
    ap.add_argument("--mutation-ks", default="5", help="comma list of k for Mut@k (each k is a full cosmic-ray run)")
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()

    tasks = {t["task_id"]: t for t in json.loads((VENDOR / "datasets" / f"{args.dataset}.jsonl").read_text())}
    if args.ground_truth:
        name = f"{args.dataset}_ground_truth"
        jobs = [(t, ground_truth_tests(t)) for t in tasks.values()]
    else:
        name = Path(args.gen).stem
        jobs = [(tasks[r["task_id"]], r["tests"]) for r in map(json.loads, Path(args.gen).read_text().splitlines())]
    jobs = jobs[: args.limit]
    out_dir = ROOT / "out" / "eval" / name
    mut_ks = {int(k) for k in args.mutation_ks.split(",")} if args.mutation else set()
    with ProcessPoolExecutor(args.workers) as pool:
        rows = list(pool.map(evaluate_task, [(t, tests, str(out_dir), mut_ks) for t, tests in jobs]))

    rows.sort(key=lambda r: int(r["task_id"]) if str(r["task_id"]).isdigit() else str(r["task_id"]))
    (ROOT / "out" / f"{name}_scores.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    n = len(rows)
    print(f"[ULT eval] {name}: N={n}")
    for k in KS:
        line = (f"  k={k}: Pass@{k}={sum(r[f'pass@{k}'] for r in rows) / n:.2%}  "
                f"LCov@{k}={sum(r[f'lcov@{k}'] for r in rows) / n:.2%}  "
                f"BCov@{k}={sum(r[f'bcov@{k}'] for r in rows) / n:.2%}")
        if k in mut_ks:
            line += f"  Mut@{k}={sum(r[f'mut@{k}']['score'] for r in rows) / n:.2%}"
        print(line)


if __name__ == "__main__":
    main()
