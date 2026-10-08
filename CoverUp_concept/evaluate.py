#!/usr/bin/env python3
"""Benchmark check, mutation testing and analysis for the CoverUp + concepts experiment (no LLM calls).

  bench                                 import every subset module in the shared venv -> out/bench.json
  mutate <arm[,arm]> [--seed K] [--pkgs a,b]
                                        mutmut on each finished workspace's generated tests -> <ws>/mut/result.json
  analyze                               coverage, mutation score, concept-site metrics, cost, Wilcoxon -> out/<run>/

Mutation (primary metric): mutmut 3 mutates the pristine benchmark source of the subset modules only (identical mutants
for every arm and seed), and runs the generated tests (coverup-tests/) against each mutant. Before that, test files
that fail on the unmutated code when run together (CoverUp checks them in isolation) are moved aside, up to 3 rounds;
their number is reported. Files that still fail inside mutmut's own clean run (test order, tracing,
patched builtins) are dropped the same way from its log, up to 8 rounds. Score = killed / all mutants of the module (survived, no tests, timeout and suspicious count
as not killed; timeouts are reported separately).
Concept sites: lines carrying a C1-C8 fact (concept_annotator_py.functions, same as the prompts). We report coverage of
those lines and the kill rate of mutants on them.
"""

from __future__ import annotations

import argparse
import ast
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

import cu_concept as cc

HERE = cc.HERE
PY = sys.executable
MUTMUT = str(Path(PY).with_name("mutmut"))
PAIRS = [("concept_reason", "placebo_reason"),  # primary
         ("concept", "coverup"), ("concept_reason", "coverup"), ("placebo_reason", "coverup"), ("ide", "coverup"),
         ("concept_reason", "concept")]
PYTEST_CFG = ["-p", "no:cacheprovider", "-c", "/dev/null", "--rootdir", "."]


def modules() -> dict[str, dict]:
    """module -> {pkg, app, file}"""
    return {f[:-3].replace("/", "."): {"pkg": p, "app": m["app"], "file": f}
            for p, m in cc.subset().items() for f in m["files"]}


def sandbox_env(home: Path) -> dict:
    env = {k: v for k, v in os.environ.items() if not cc.SECRET_ENV.search(k)}
    home.mkdir(parents=True, exist_ok=True)
    return {**env, "HOME": str(home), "PYTHONPATH": ".", "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"}


# ---------------------------------------------------------------- bench
def bench() -> None:
    res = {}
    for mod, m in modules().items():
        p = subprocess.run([PY, "-c", f"import {mod}"], cwd=cc.APPS / m["app"], capture_output=True, text=True,
                           env={**os.environ, "PYTHONPATH": "."}, timeout=120)
        res[mod] = "ok" if p.returncode == 0 else p.stderr.strip().splitlines()[-1]
    bad = {k: v for k, v in res.items() if v != "ok"}
    versions = subprocess.run([PY, "-m", "pip", "freeze"], capture_output=True, text=True).stdout.split()
    cc.OUT.parent.mkdir(parents=True, exist_ok=True)
    json.dump({"python": sys.version.split()[0], "machine": os.uname().machine, "modules": res,
               "packages": versions}, open(HERE / "out" / "bench.json", "w"), indent=1)
    print(f"[bench] {len(res) - len(bad)}/{len(res)} modules import" + "".join(f"\n  {k}: {v}" for k, v in bad.items()))


# ---------------------------------------------------------------- mutation
def failing_tests(mdir: Path, env: dict) -> set[str]:
    """Test files with a failing/erroring test when the whole suite runs on unmutated code (empty set = all pass)."""
    xml = mdir / ".junit.xml"
    subprocess.run([PY, "-m", "pytest", "-q", *PYTEST_CFG, f"--junitxml={xml}",
                    "coverup-tests"], cwd=mdir, env=env, capture_output=True, timeout=3600)
    bad = set()
    if not xml.exists():
        return {"<collection>"}
    for tc in ET.parse(xml).getroot().iter("testcase"):
        if tc.find("failure") is not None or tc.find("error") is not None:
            f = tc.get("file") or tc.get("classname", "").replace(".", "/").rsplit("/", 1)[0] + ".py"
            bad.add(Path(f).name)
    xml.unlink()
    return bad


def mutant_lines(mdir: Path, rel: str) -> dict[str, int]:
    """mutant key -> line in the original file (first line where the mutated function differs from the original)."""
    mfile = mdir / "mutants" / rel
    spans = json.load(open(str(mfile) + ".spans"))["spans"]
    mlines = mfile.read_text(encoding="utf-8").splitlines()
    tree = ast.parse((mdir / rel).read_text(encoding="utf-8"))
    starts = {}  # mutmut function name -> def line
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            starts[f"x_{n.name}"] = n.lineno
        elif isinstance(n, ast.ClassDef):
            for m in n.body:
                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    starts[f"xǁ{n.name}ǁ{m.name}"] = m.lineno
    prefix = rel[:-3].replace("/", ".") + "."
    out = {}
    for name, (a, b) in spans.items():
        func, _, num = name.rpartition("__mutmut_")
        if num == "orig" or func not in starts or f"{func}__mutmut_orig" not in spans:
            continue
        oa, ob = spans[f"{func}__mutmut_orig"]
        orig, mut = mlines[oa:ob], mlines[a:b]  # spans are 0-based, end-exclusive
        k = next((i for i in range(1, min(len(orig), len(mut))) if orig[i] != mut[i]), min(len(orig), len(mut)) - 1)
        out[prefix + name] = starts[func] + k
    return out


def mutate_ws(ws: Path, pkg: str, files: list[str], jobs: int) -> dict:
    mdir = ws / "mut"
    shutil.rmtree(mdir, ignore_errors=True)
    mdir.mkdir()
    shutil.copytree(cc.APPS / cc.subset()[pkg]["app"] / pkg, mdir / pkg,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copytree(ws / "coverup-tests", mdir / "coverup-tests", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    env = sandbox_env(mdir / ".home")
    dropped = []
    if not list((mdir / "coverup-tests").glob("test_*.py")):  # nothing generated: every mutant is "no tests"
        (mdir / "coverup-tests" / "test_empty.py").write_text("def test_empty():\n    pass\n")
    for _ in range(3):
        bad = failing_tests(mdir, env)
        if not bad:
            break
        (mdir / "dropped").mkdir(exist_ok=True)
        for f in bad:
            src = mdir / "coverup-tests" / f
            if src.exists():
                src.rename(mdir / "dropped" / f)
                dropped.append(f)
        if "<collection>" in bad or not list((mdir / "coverup-tests").glob("test_*.py")):
            (mdir / "coverup-tests" / "test_empty.py").write_text("def test_empty():\n    pass\n")
    (mdir / "setup.cfg").write_text(
        "[mutmut]\n"
        f"source_paths = {pkg}\n"
        "only_mutate =\n" + "".join(f"    {f}\n" for f in files) +
        "also_copy = coverup-tests\n"
        "pytest_add_cli_args_test_selection = coverup-tests\n"
        f"pytest_add_cli_args = {' '.join(PYTEST_CFG)}\n")
    for _ in range(8):  # tests passing under plain pytest can still fail under mutmut (order, tracing, trampolines)
        p = subprocess.run([MUTMUT, "run", "--max-children", str(jobs)], cwd=mdir, env=env, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=4 * 3600)
        log = re.sub(r"[^\n]*\r", "", p.stdout.decode(errors="replace"))
        (ws / "mutmut.log").write_text(log[-20000:])
        if p.returncode == 0:
            break
        bad = set(re.findall(r"FAILED[^ ]* coverup-tests/(test_\w+\.py)", re.sub(r"\x1b\[[0-9;]*m", "", log)))
        if not bad:  # INTERNALERROR from a test that patched a builtin: find the file defining the culprit
            for name in set(re.findall(r"TypeError: (\w+)\(\) takes", log)):
                bad |= {t.name for t in (mdir / "coverup-tests").glob("test_*.py") if f"def {name}(" in t.read_text()}
        bad = {f for f in bad if (mdir / "coverup-tests" / f).exists()}
        if not bad:
            raise RuntimeError(f"mutmut rc={p.returncode} (see {ws / 'mutmut.log'})")
        (mdir / "dropped").mkdir(exist_ok=True)
        for f in bad:
            (mdir / "coverup-tests" / f).rename(mdir / "dropped" / f)
            dropped.append(f)
        if not list((mdir / "coverup-tests").glob("test_*.py")):
            (mdir / "coverup-tests" / "test_empty.py").write_text("def test_empty():\n    pass\n")
        shutil.rmtree(mdir / "mutants", ignore_errors=True)
    else:
        raise RuntimeError(f"mutmut still failing after dropping {len(dropped)} test files (see {ws / 'mutmut.log'})")
    from mutmut.stats import status_by_exit_code
    mutants = {}
    for f in files:
        meta = json.load(open(mdir / "mutants" / (f + ".meta")))
        lines = mutant_lines(mdir, f)
        for key, code in meta["exit_code_by_key"].items():
            mutants[key] = [status_by_exit_code[code], lines.get(key)]
    res = {"dropped_tests": sorted(dropped), "tests": len(list((mdir / "coverup-tests").glob("test_*.py"))),
           "mutants": mutants}
    shutil.rmtree(mdir)  # mutants/ copies are large; result.json keeps every verdict
    return res


def mutate(arms: list[str], seed: int | None, pkgs: list[str] | None) -> None:
    jobs = int(os.environ.get("MUTMUT_JOBS", os.cpu_count() or 4))
    sub = cc.subset()
    for arm in arms:
        for sdir in sorted((cc.WORK / arm).glob("s*")):
            if seed is not None and sdir.name != f"s{seed}":
                continue
            for pkg in pkgs or sub:
                ws = sdir / pkg
                if not (ws / "done.json").exists():
                    continue
                out = ws / "mut_result.json"
                if out.exists():
                    continue
                try:
                    res = mutate_ws(ws, pkg, sub[pkg]["files"], jobs)
                except Exception as e:
                    print(f"[mutate] {arm}/{sdir.name}/{pkg}: FAILED {e}")
                    continue
                out.write_text(json.dumps(res))
                st = [s for s, _ in res["mutants"].values()]
                print(f"[mutate] {arm}/{sdir.name}/{pkg}: {st.count('killed')}/{len(st)} killed, "
                      f"{st.count('timeout')} timeout, {len(res['dropped_tests'])} test files dropped")


# ---------------------------------------------------------------- analysis
def concept_lines(path: Path) -> dict[int, set[str]]:
    funcs, _ = cc.file_units(path)
    out = defaultdict(set)
    for _, _, facts in funcs:
        for f in facts:
            out[f["line"]].add(f["concept"])
    return out


def mean(xs) -> float | None:
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def wilcoxon(a: list[float], b: list[float]) -> tuple[int, float]:
    from scipy.stats import wilcoxon as w
    d = [i - j for i, j in zip(a, b) if i != j]
    return len(d), (float(w(d).pvalue) if d else 1.0)


def ws_metrics(ws: Path, mods: dict) -> dict[str, dict]:
    """module -> metrics for one finished workspace."""
    final = json.load(open(ws / "final.json"))["files"] if (ws / "final.json").exists() else {}
    mut = json.load(open(ws / "mut_result.json")) if (ws / "mut_result.json").exists() else None
    out = {}
    for mod, m in mods.items():
        src = cc.APPS / m["app"] / m["file"]
        cl = concept_lines(src)
        f = final.get(m["file"])
        r = {}
        if f:
            s = f["summary"]
            r["cov"] = 100 * (s["covered_lines"] + s["covered_branches"]) / max(
                1, s["covered_lines"] + s["missing_lines"] + s["covered_branches"] + s["missing_branches"])
            r["line_cov"] = 100 * s["covered_lines"] / max(1, s["covered_lines"] + s["missing_lines"])
            ex, miss = set(f["executed_lines"]), set(f["missing_lines"])
            sites = [ln for ln in cl if ln in ex or ln in miss]
            r["site_cov"] = 100 * sum(ln in ex for ln in sites) / len(sites) if sites else None
        elif final:
            r["cov"] = r["line_cov"] = 0.0  # module never imported by any test
        if mut is not None:
            ms = {k: v for k, v in mut["mutants"].items() if k.startswith(mod + ".")}
            if ms:
                r["mut"] = 100 * sum(s == "killed" for s, _ in ms.values()) / len(ms)
                r["n_mut"] = len(ms)
                r["timeouts"] = sum(s == "timeout" for s, _ in ms.values())
                site = [s for s, ln in ms.values() if ln in cl]
                r["site_mut"] = 100 * sum(s == "killed" for s in site) / len(site) if site else None
                r["killed"] = sorted(k for k, (s, _) in ms.items() if s == "killed")
            r["dropped_tests"] = len(mut["dropped_tests"])
        out[mod] = r
    return out


def analyze() -> None:
    mods = modules()
    by_pkg = defaultdict(dict)
    for mod, m in mods.items():
        by_pkg[m["pkg"]][mod] = m
    rows = {}  # (arm, seed, module) -> metrics
    blocks = defaultdict(lambda: [0, 0])  # arm -> [segments with a block, segments]
    for arm in cc.ARMS:
        for sdir in sorted((cc.WORK / arm).glob("s*")):
            for pkg, pm in by_pkg.items():
                ws = sdir / pkg
                if not (ws / "done.json").exists():
                    continue
                for mod, r in ws_metrics(ws, pm).items():
                    rows[(arm, sdir.name, mod)] = r
                if (ws / "prompts.jsonl").exists():
                    for line in open(ws / "prompts.jsonl"):
                        blocks[arm][0] += bool(json.loads(line)["block"])
                        blocks[arm][1] += 1
    seeds = sorted({s for _, s, _ in rows})
    arms = [a for a in cc.ARMS if any(k[0] == a for k in rows)]
    # per (arm, module): mean over seeds; paired tests use modules finished (with mutation) in every arm and seed
    per = {a: {mod: {k: mean(rows[(a, s, mod)].get(k) for s in seeds if (a, s, mod) in rows)
                     for k in ("cov", "line_cov", "site_cov", "mut", "site_mut")} for mod in mods} for a in arms}
    complete = [mod for mod in mods if all((a, s, mod) in rows and "mut" in rows[(a, s, mod)]
                                           for a in arms for s in seeds)]
    cov_complete = [mod for mod in mods if all((a, s, mod) in rows and "cov" in rows[(a, s, mod)]
                                               for a in arms for s in seeds)]
    res = {"run": cc.RUN, "model": cc.MODEL, "seeds": seeds, "arms": arms, "n_modules_mut": len(complete),
           "n_modules_cov": len(cov_complete), "per_arm": {}, "pairs": {}, "cost": cost(),
           "blocks": {a: {"with_block": v[0], "segments": v[1]} for a, v in blocks.items()}}
    lines = [f"# CoverUp + concepts: {cc.RUN}", "",
             f"Model {cc.MODEL}; seeds {', '.join(seeds)}; {len(complete)} modules with mutation results in every arm "
             f"and seed, {len(cov_complete)} with coverage. Means over modules of the per-module mean over seeds.", "",
             "| arm | coverage % | line cov % | concept-site cov % | mutation score % | concept-site kill % | "
             "dropped test files | segments with block | USD |", "|---|---|---|---|---|---|---|---|---|"]
    for a in arms:
        pa = {k: mean(per[a][mod][k] for mod in (complete if k in ("mut", "site_mut") else cov_complete))
              for k in ("cov", "line_cov", "site_cov", "mut", "site_mut")}
        pa["dropped_tests"] = sum(r.get("dropped_tests", 0) for (x, _, _), r in rows.items() if x == a)
        res["per_arm"][a] = pa
        fmt = lambda v: "-" if v is None else f"{v:.1f}"
        lines.append(f"| {a} | {fmt(pa['cov'])} | {fmt(pa['line_cov'])} | {fmt(pa['site_cov'])} | {fmt(pa['mut'])} | "
                     f"{fmt(pa['site_mut'])} | {pa['dropped_tests']} | {blocks[a][0]}/{blocks[a][1]} | "
                     f"{res['cost'].get(a, {}).get('usd', 0):.2f} |")
    lines += ["", "Paired by module (Wilcoxon signed-rank, two-sided; n = modules with a nonzero difference):", "",
              "| contrast | metric | mean A | mean B | A>B | B>A | n | p |", "|---|---|---|---|---|---|---|---|"]
    for x, y in PAIRS:
        if x not in arms or y not in arms:
            continue
        for k in ("mut", "cov", "site_mut", "site_cov"):
            ms = [m for m in (complete if k in ("mut", "site_mut") else cov_complete)
                  if per[x][m][k] is not None and per[y][m][k] is not None]
            if not ms:
                continue
            a_, b_ = [per[x][m][k] for m in ms], [per[y][m][k] for m in ms]
            n, p = wilcoxon(a_, b_)
            row = {"mean_a": mean(a_), "mean_b": mean(b_), "a_gt_b": sum(i > j for i, j in zip(a_, b_)),
                   "b_gt_a": sum(j > i for i, j in zip(a_, b_)), "n": n, "p": p, "modules": len(ms)}
            res["pairs"][f"{x}_vs_{y}:{k}"] = row
            lines.append(f"| {x} vs {y} | {k} | {row['mean_a']:.1f} | {row['mean_b']:.1f} | {row['a_gt_b']} | "
                         f"{row['b_gt_a']} | {n} | {p:.3g} |")
    ref = json.load(open(HERE / "data" / "paper_ref.json"))["modules"]
    if "coverup" in arms:
        ms = [m for m in cov_complete if m in ref and per["coverup"][m]["cov"] is not None]
        if ms:
            ours, theirs = mean(per["coverup"][m]["cov"] for m in ms), mean(ref[m]["run1"]["percent_covered"] for m in ms)
            res["paper_ref"] = {"modules": len(ms), "coverup_cov": ours, "paper_run1_cov": theirs}
            lines += ["", f"Replication check: stock coverup arm {ours:.1f}% vs the authors' gpt-4o run 1 "
                          f"{theirs:.1f}% (same {len(ms)} modules)."]
    lines += ["", "Cost (ledger):", ""] + [f"- {a}: {v['calls']} calls ({v['errors']} errors), in {v['in']:,} / out "
                                         f"{v['out']:,} tokens, ${v['usd']:.3f}" for a, v in res["cost"].items()]
    cc.OUT.mkdir(parents=True, exist_ok=True)
    json.dump(res, open(cc.OUT / "metrics.json", "w"), indent=1)
    with open(cc.OUT / "per_module.jsonl", "w") as f:
        for (a, s, mod), r in sorted(rows.items()):
            f.write(json.dumps({"arm": a, "seed": s, "module": mod, **{k: v for k, v in r.items() if k != "killed"}})
                    + "\n")
    (cc.OUT / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def cost() -> dict:
    by = defaultdict(lambda: {"calls": 0, "errors": 0, "in": 0, "out": 0, "usd": 0.0})
    p = cc.OUT / "ledger.jsonl"
    for line in (open(p) if p.exists() else []):
        r = json.loads(line)
        b = by[r["arm"]]
        b["calls"] += 1
        b["errors"] += "err" in r
        b["in"] += r["in"]
        b["out"] += r["out"]
        b["usd"] += r["usd"]
    return {a: {**v, "usd": round(v["usd"], 4)} for a, v in by.items()}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["bench", "mutate", "analyze"])
    ap.add_argument("arms", nargs="?")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--pkgs")
    a = ap.parse_args()
    if a.cmd == "bench":
        bench()
    elif a.cmd == "mutate":
        mutate(a.arms.split(","), a.seed, a.pkgs.split(",") if a.pkgs else None)
    else:
        analyze()
