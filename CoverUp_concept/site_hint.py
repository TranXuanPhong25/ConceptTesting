#!/usr/bin/env python3
"""Site-specific test hints: a test-strengthening round after CoverUp, on the mutants its tests left alive.

Seed-1 CoverUp tests (arm `coverup`) execute many lines without checking them: mutants there survive. This round
prompts once per function with surviving mutants (CoverUp's own excerpt format, lines of interest = the mutated
lines) and asks for tests that would fail if those lines changed. Arms differ only in an appended block:

  control   no block (the prompt already names the weak lines)
  hint      per-line hints from RULES: what can go wrong with the construct on that line and concrete inputs to try,
            filled with the real variable names and constants of the line
  placebo   the same kind of hints, taken from other functions of the package (seeded rotation), moved onto
            this function's lines

Tests must pass on the current code (CoverUp's regression oracle); a failing file gets up to 2 repairs with
CoverUp's error prompt, then its failing test functions are removed and the passing ones kept (every arm alike).
There is no rule for `raise` lines: it only targets message mutants and led the model to wrong assertions. Metric: target mutants killed by seed-1 tests + the arm's new tests (mutmut, same settings
as evaluate.py). Message-only mutants (string literals, raise arguments) are reported apart from semantic ones.

usage: python site_hint.py targets <pkg>...          list target functions and their hints (no LLM)
       python site_hint.py run <arm> <pkg>... [--seed K]
       python site_hint.py report <pkg>...
env:   CU_RUN (default smoke_sitehint); Vertex as in cu_concept.py
"""

from __future__ import annotations

import argparse
import ast
import asyncio
import json
import os
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("CU_RUN", "smoke_sitehint")
import cu_concept as cc  # noqa: E402
import evaluate as ev  # noqa: E402

ARMS = ("control", "hint", "placebo")
BASE = cc.HERE / "work" / "main" / "coverup" / "s1"  # seed-1 stock CoverUp workspaces
MAX_HINTS = 8

PROMPT = """
You are an expert Python test-driven developer.
The code below, extracted from {filename}, is executed by the existing tests, but those tests would not notice
if {lines} were wrong: mutation testing shows that changes to them go undetected.
Create new pytest test functions that would FAIL if the logic on those lines were changed, while passing on the
code as it is now. Assert exact results (return values, raised exception types and messages, state changes)
instead of just running the code.
Be sure each test is correct for the current code.
Please also make VERY SURE to clean up after the test, so as to avoid state pollution;
use 'monkeypatch' or 'pytest-mock' if appropriate.
Write as little top-level code as possible, and in particular do not include any top-level code
calling into pytest.main or the test itself.
Respond ONLY with the Python code enclosed in backticks, without any explanation.
```python
{excerpt}
```
"""
ERROR_PROMPT = """\
Executing the test yields an error, shown below.
Modify or rewrite the test to correct it; respond only with the complete Python code in backticks.

{error}"""


# ---------------------------------------------------------------- rules: construct on a line -> hint + inputs
def _src(n: ast.AST) -> str:
    s = ast.unparse(n)
    return s if len(s) <= 60 else s[:57] + "..."


def _num(n: ast.AST):
    if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool):
        return n.value
    if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub) and isinstance(n.operand, ast.Constant):
        return -n.operand.value if isinstance(n.operand.value, (int, float)) else None
    return None


def rules(func: ast.AST, params: set[str]) -> list[tuple[int, str, str, list[str]]]:
    """(line, rule id, hint text, suggested literal inputs) for every matching construct in the function."""
    out = []
    loops = {id(m) for n in ast.walk(func) if isinstance(n, (ast.For, ast.While)) for m in ast.walk(n)}
    for n in ast.walk(func):
        ln = getattr(n, "lineno", None)
        if isinstance(n, ast.Compare):
            for left, op, right in zip([n.left] + n.comparators, n.ops, n.comparators):
                if isinstance(op, (ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq)):
                    k, other = (_num(right), left) if _num(right) is not None else (_num(left), right)
                    if k is not None and isinstance(k, int):
                        out.append((ln, "bound", f"`{_src(n)}` has a boundary at {k}: use {_src(other)} = {k - 1}, "
                                    f"{k} and {k + 1}, and assert the exact outcome of each.", [str(k - 1), str(k), str(k + 1)]))
                    elif k is None and not isinstance(op, (ast.Eq, ast.NotEq)):
                        out.append((ln, "bound2", f"`{_src(n)}` compares two values: make {_src(left)} equal to "
                                    f"{_src(right)}, then one less and one more, and assert each outcome.", []))
                elif isinstance(op, (ast.In, ast.NotIn)) and isinstance(right, (ast.Tuple, ast.List, ast.Set)):
                    lits = [e.value for e in right.elts if isinstance(e, ast.Constant)]
                    if lits:
                        near = [repr(str(lits[0]) + "x"), repr(str(lits[0]).upper()) if isinstance(lits[0], str) else None]
                        out.append((ln, "member", f"`{_src(n)}`: test every member {', '.join(map(repr, lits))} and "
                                    f"near-misses such as {', '.join(x for x in near if x)}, asserting each result.",
                                    [repr(x) for x in lits]))
        elif isinstance(n, ast.BoolOp) and len(n.values) >= 2:
            kind = "true" if isinstance(n.op, ast.Or) else "false"
            out.append((ln, "boolop", f"`{_src(n)}` combines {len(n.values)} conditions: write one test per condition "
                        f"where only that condition is {kind}, so swapping and/or or dropping a condition changes "
                        f"the result.", []))
        elif isinstance(n, ast.AugAssign) and id(n) in loops:
            out.append((ln, "accum", f"`{_src(n)}` accumulates in a loop: use a real-world valid input whose exact "
                        f"result you know (e.g. a valid checksum/total), and the same input with one element changed; "
                        f"assert the exact result for both.", []))
        elif isinstance(n, ast.Call):
            f = n.func
            name = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else ""
            full = _src(f)
            if full == "re.escape" and n.args:
                out.append((ln, "escape", f"`{_src(n.args[0])}` is escaped before going into a regex: use values "
                            f"containing regex metacharacters ('.', '*', '+', '|', '\\\\') and a multi-character "
                            f"value, and assert the exact result.", ["'.'", "'*'", "'+'"]))
            elif full in ("re.sub", "re.match", "re.search", "re.fullmatch", "re.findall", "re.split") or \
                    (name in ("sub", "match", "search", "fullmatch", "findall", "split") and full.endswith("_RE." + name)):
                out.append((ln, "regex", f"regex `{_src(n)}`: use inputs with zero, one and several consecutive "
                            f"matches, matches at the start/end, and the empty string; assert exact outputs.", ["''"]))
            elif name in ("lower", "upper", "casefold", "title", "capitalize", "swapcase"):
                out.append((ln, "case", f"`{_src(n)}` changes case: use UPPER, Mixed and lower case inputs "
                            f"(e.g. 'ABC', 'AbC') and non-ASCII letters ('ß', 'İ'); assert they give the expected "
                            f"(case-insensitive) result.", ["'ß'"]))
            elif name in ("int", "float") and isinstance(f, ast.Name) and n.args:
                out.append((ln, "parse", f"`{_src(n)}` parses a number: try ' 7 ', '+7', '-0', '1_000', '٣' "
                            f"(non-ASCII digit) and '7.0', asserting result or exception.", ["'+7'", "'1_000'", "'٣'"]))
            elif name in ("encode", "decode"):
                out.append((ln, "codec", f"`{_src(n)}`: use non-ASCII text ('é', '日本') and, for decode, bytes "
                            f"invalid in that encoding; assert exact output or exception.", ["'é'", "'日本'"]))
            elif name == "isinstance" and len(n.args) == 2:
                out.append((ln, "isinstance", f"`{_src(n)}`: also pass True/False (bool is an int), 1.0 and a "
                            f"numeric string '1', asserting accept/reject.", ["True", "1.0"]))
            fwd = [a.id for a in list(n.args) + [k.value for k in n.keywords] if isinstance(a, ast.Name) and a.id in params]
            for p in fwd:
                out.append((ln, "forward", f"`{_src(n)}` passes parameter `{p}` on: call with two different values "
                            f"of `{p}` and assert the results differ as they should.", []))
        elif isinstance(n, ast.Subscript) and isinstance(n.slice, (ast.Constant, ast.UnaryOp, ast.Slice)):
            out.append((ln, "index", f"`{_src(n)}`: use the shortest valid input (length 0 or 1) and check the "
                        f"first and last elements exactly.", []))
    seen, uniq = set(), []
    for h in sorted(out, key=lambda h: (h[0], h[1])):
        if (h[0], h[1], h[2]) not in seen:
            seen.add((h[0], h[1], h[2]))
            uniq.append(h)
    return uniq


def render(hints: list[tuple]) -> str:
    return ("How to catch a bug on these lines (inputs and checks the existing tests do not try):\n"
            + "\n".join(f"- line {ln}: {text}" for ln, _, text, _ in hints))


# ---------------------------------------------------------------- targets from seed-1 surviving mutants
def message_only(orig: str, mut: str) -> bool:
    if orig.lstrip().startswith("raise "):
        return True
    strip = lambda s: re.sub(r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"", "S", s)  # noqa: E731
    return strip(orig) == strip(mut)


def targets(pkg: str) -> list[dict]:
    """One target per function with surviving mutants in seed-1 stock tests: lines, mutants, hints."""
    cache = cc.OUT / f"targets_{pkg}.json"
    if cache.exists():
        return json.load(open(cache))
    files = cc.subset()[pkg]["files"]
    ws = cc.WORK / "_base" / pkg
    shutil.rmtree(ws, ignore_errors=True)
    shutil.copytree(BASE / pkg / "coverup-tests", ws / "coverup-tests", ignore=shutil.ignore_patterns("__pycache__"))
    res = ev.mutate_ws(ws, pkg, files, int(os.environ.get("MUTMUT_JOBS", os.cpu_count() or 4)), keep=True)
    diffs = {}
    for f in files:
        diffs.update(ev.mutant_diffs(ws / "mut", f))
    shutil.rmtree(ws / "mut")
    out = []
    for f in files:
        src = cc.APPS / cc.subset()[pkg]["app"] / f
        tree = ast.parse(src.read_text())
        funcs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        prefix = f[:-3].replace("/", ".") + "."
        by_func = {}
        for key, (status, _) in res["mutants"].items():
            if status != "survived" or not key.startswith(prefix) or key not in diffs:
                continue
            ln, o, m = diffs[key]
            fn = min((n for n in funcs if n.lineno <= ln <= n.end_lineno), key=lambda n: n.end_lineno - n.lineno, default=None)
            if fn is None:
                continue
            t = by_func.setdefault((fn.lineno, fn.name), {"file": f, "func": fn.name, "begin": fn.lineno,
                                                           "end": fn.end_lineno, "mutants": {}})
            t["mutants"][key] = {"line": ln, "orig": o.strip(), "mut": m.strip(), "message_only": message_only(o, m)}
        for (b, _), t in sorted(by_func.items()):
            fn = next(n for n in funcs if n.lineno == b)
            pos = fn.args.posonlyargs + fn.args.args  # options = parameters with a default value
            params = {a.arg for a in pos[len(pos) - len(fn.args.defaults):]} | \
                     {a.arg for a, d in zip(fn.args.kwonlyargs, fn.args.kw_defaults) if d is not None}
            lines = sorted({m["line"] for m in t["mutants"].values()})
            t["lines"] = lines
            t["hints"] = [h for h in rules(fn, params) if h[0] in lines][:MAX_HINTS]
            out.append(t)
    cc.OUT.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(cache, "w"), indent=1)
    json.dump({"dropped_tests": res["dropped_tests"]}, open(cc.OUT / f"base_{pkg}.json", "w"))
    return out


def placebo_hints(ts: list[dict], seed: int) -> dict[int, list]:
    """Target index -> hints of another target (seeded derangement among targets with hints), lines remapped."""
    idx = [i for i, t in enumerate(ts) if t["hints"]]
    rot = idx[:]
    random.Random(seed).shuffle(rot)
    if len(rot) > 1:
        rot = rot[1:] + rot[:1]  # every target gets someone else's hints
    out = {}
    for i, j in zip(idx, rot):
        lines = ts[i]["lines"]
        out[i] = [(lines[k % len(lines)], r, txt, inp) for k, (_, r, txt, inp) in enumerate(ts[j]["hints"])]
    return out


# ---------------------------------------------------------------- generation (one function = one conversation)
def excerpt(pkg: str, t: dict) -> str:
    from coverup.segment import get_missing_coverage
    src = cc.APPS / cc.subset()[pkg]["app"] / t["file"]
    cov = {"files": {str(src): {"missing_lines": t["lines"], "executed_lines": [], "missing_branches": []}}}
    segs = [s for s in get_missing_coverage(cov) if s.begin <= t["begin"] <= s.end]
    seg = max(segs, key=lambda s: len(set(t["lines"]) & s.lines_of_interest))
    return seg.get_excerpt()


def lines_text(lines: list[int]) -> str:
    return f"line {lines[0]}" if len(lines) == 1 else "lines " + ", ".join(map(str, lines[:-1])) + f" and {lines[-1]}"


def extract_code(text: str) -> str | None:
    m = re.findall(r"```python\n(.*?)```", text or "", re.S)
    return m[-1] if m else None


def failing_nodes(test: Path, cwd: Path) -> set[tuple[str, ...]] | None:
    """(class?, function) names of failing tests in the file; None if the file does not even collect."""
    xml = cwd / ".prune.xml"
    subprocess.run([sys.executable, "-m", "pytest", "-q", *ev.PYTEST_CFG, "-p", "no:randomly", f"--junitxml={xml}",
                    str(test)], cwd=cwd, env=ev.sandbox_env(cwd / ".home"), capture_output=True, timeout=300)
    if not xml.exists():
        return None
    import xml.etree.ElementTree as ET
    bad = set()
    for tc in ET.parse(xml).getroot().iter("testcase"):
        if tc.find("failure") is not None or tc.find("error") is not None:
            name = tc.get("name", "").split("[")[0]
            cls = tc.get("classname", "").rsplit(".", 1)[-1]
            bad.add((cls, name) if cls and cls[0].isupper() else (name,))
    xml.unlink()
    if any(t == ("",) for t in bad):
        return None
    return bad


def prune(test: Path, cwd: Path) -> int:
    """Remove failing test functions (all arms alike); returns how many were kept, 0 if the file had to go."""
    for _ in range(3):
        bad = failing_nodes(test, cwd)
        if bad is None:
            return 0
        tree = ast.parse(test.read_text())
        if not bad:
            return sum(1 for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                       and n.name.startswith("test"))
        names = {b[-1] for b in bad}
        for holder in [tree] + [n for n in tree.body if isinstance(n, ast.ClassDef)]:
            holder.body = [n for n in holder.body
                           if not (isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names)] or [ast.Pass()]
        test.write_text(ast.unparse(tree) + "\n")
    return 0


def run_pytest(test: Path, cwd: Path) -> tuple[bool, str]:
    env = ev.sandbox_env(cwd / ".home")
    p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", *ev.PYTEST_CFG, "-p", "no:randomly", str(test)],
                       cwd=cwd, env=env, capture_output=True, text=True, timeout=300)
    return p.returncode == 0, (p.stdout + p.stderr)[-4000:]


async def gen_one(arm: str, pkg: str, i: int, t: dict, block: str, wdir: Path, seed: int, sem) -> dict:
    import litellm
    out = wdir / f"test_sitehint_{i}.py"
    rec_path = wdir / f"rec_{i}.json"
    if rec_path.exists():
        return json.load(open(rec_path))
    prompt = PROMPT.format(filename=t["file"], lines=lines_text(t["lines"]), excerpt=excerpt(pkg, t))
    if block:
        prompt += "\n" + block + "\n"
    msgs = [{"role": "user", "content": prompt}]
    ok, err, tries = False, "", 0
    async with sem:
        for tries in range(1, 4):
            cc._seg.set(f"{arm}:{t['file']}:{t['func']}")
            r = None
            for attempt in range(60):  # 429s: back off like CoverUp's Chatter (max 64 s), give up after ~1 h
                try:
                    r = await litellm.acreate(model=cc.MODEL, messages=msgs)
                    break
                except (litellm.RateLimitError, litellm.Timeout, litellm.ServiceUnavailableError,
                        litellm.InternalServerError, litellm.APIConnectionError):
                    await asyncio.sleep(random.uniform(0.5, 1) * min(64, 2 ** attempt))
            if r is None:
                return {"i": i, "func": t["func"], "arm": arm, "ok": False, "llm_failed": True}  # not cached: rerun
            text = r.choices[0].message.content or ""
            msgs.append({"role": "assistant", "content": text})
            code = extract_code(text)
            if code is None:
                msgs.append({"role": "user", "content": "Respond only with the complete Python code in backticks."})
                continue
            out.write_text(code)
            ok, err = await asyncio.to_thread(run_pytest, out, wdir.parent)
            if ok:
                break
            msgs.append({"role": "user", "content": ERROR_PROMPT.format(error=err)})
    kept = None
    if not ok and out.exists():  # keep the passing test functions, drop the failing ones
        (wdir / f"test_sitehint_{i}.orig").write_text(out.read_text())
        kept = await asyncio.to_thread(prune, out, wdir.parent)
        if kept:
            ok = (await asyncio.to_thread(run_pytest, out, wdir.parent))[0]
        if not ok:
            out.rename(out.with_suffix(".failed"))
    rec = {"i": i, "func": t["func"], "file": t["file"], "arm": arm, "ok": ok, "tries": tries, "pruned_kept": kept,
           "block": block,
           "prompt": prompt, "error": None if ok else err[-500:]}
    rec_path.write_text(json.dumps(rec))
    return rec


async def run_arm(arm: str, pkg: str, seed: int) -> None:
    ts = targets(pkg)
    plac = placebo_hints(ts, seed) if arm == "placebo" else {}
    root = cc.WORK / arm / f"s{seed}" / pkg
    wdir = root / "coverup-tests"
    if not wdir.exists():
        shutil.copytree(BASE / pkg / "coverup-tests", wdir, ignore=shutil.ignore_patterns("__pycache__"))
    if not (root / pkg).exists():
        shutil.copytree(cc.APPS / cc.subset()[pkg]["app"] / pkg, root / pkg, ignore=shutil.ignore_patterns("__pycache__"))
    sem = asyncio.Semaphore(int(os.environ.get("CU_CONCURRENCY", "4")))
    jobs = []
    for i, t in enumerate(ts):
        hints = t["hints"] if arm == "hint" else plac.get(i, []) if arm == "placebo" else []
        jobs.append(gen_one(arm, pkg, i, t, render(hints) if hints else "", wdir, seed, sem))
    recs = await asyncio.gather(*jobs)
    lost = sum(r.get("llm_failed", False) for r in recs)
    print(f"[run] {arm}/s{seed}/{pkg}: {sum(r['ok'] for r in recs)}/{len(recs)} functions got passing tests"
          + (f"; {lost} lost to LLM errors, rerun to retry them" if lost else ""))
    if not lost and not (root / "mut_result.json").exists():
        res = ev.mutate_ws(root, pkg, cc.subset()[pkg]["files"], int(os.environ.get("MUTMUT_JOBS", os.cpu_count() or 4)))
        (root / "mut_result.json").write_text(json.dumps(res))


def run(arm: str, pkgs: list[str], seed: int) -> None:
    creds = cc.load_adc()
    cc.scrub_env(cc.WORK / ".home")
    cc.patch_llm(cc.Ledger(arm, seed, ",".join(pkgs)), seed, creds)
    for pkg in pkgs:
        asyncio.run(run_arm(arm, pkg, seed))


# ---------------------------------------------------------------- report
def literal_used(lit: str, code: str) -> bool:
    try:
        v = ast.literal_eval(lit)
    except Exception:
        return lit in code
    return repr(v) in code or (isinstance(v, str) and (f'"{v}"' in code or f"'{v}'" in code))


def report(pkgs: list[str]) -> None:
    from scipy.stats import binomtest
    rows = []
    for pkg in pkgs:
        ts = targets(pkg)
        for sdir in sorted({p.name for a in ARMS for p in (cc.WORK / a).glob("s*")}):
            killed = {}
            for arm in ARMS:
                f = cc.WORK / arm / sdir / pkg / "mut_result.json"
                if f.exists():
                    killed[arm] = {k for k, (s, _) in json.load(open(f))["mutants"].items() if s == "killed"}
            if len(killed) < len(ARMS):
                continue
            for i, t in enumerate(ts):
                code = {a: "\n".join(p.read_text() for p in (cc.WORK / a / sdir / pkg / "coverup-tests").glob(f"test_sitehint_{i}.py")) for a in ARMS}
                lits = [x for h in t["hints"] for x in h[3]]
                for key, m in t["mutants"].items():
                    rows.append({"pkg": pkg, "seed": sdir, "i": i, "func": t["func"], "key": key, "msg": m["message_only"],
                                 "has_hint": any(h[0] == m["line"] for h in t["hints"]),
                                 **{a: key in killed[a] for a in ARMS}})
                if lits:
                    for a in ARMS:
                        rows.append({"compliance": True, "arm": a, "used": sum(literal_used(x, code[a]) for x in lits),
                                     "n": len(lits)})
    muts = [r for r in rows if "key" in r]
    comp = [r for r in rows if r.get("compliance")]
    lines = [f"# Site-hint smoke ({', '.join(pkgs)})", "", "Target mutants: survived seed-1 stock CoverUp tests. "
             "Killed = by seed-1 tests + the arm's new tests.", "",
             "| subset | n | control | hint | placebo | hint vs placebo (only/only, p) | hint vs control (only/only, p) |",
             "|---|---|---|---|---|---|---|"]
    for name, sub in [("all", muts), ("semantic", [r for r in muts if not r["msg"]]),
                      ("semantic, line has a hint", [r for r in muts if not r["msg"] and r["has_hint"]]),
                      ("semantic, no hint on line", [r for r in muts if not r["msg"] and not r["has_hint"]]),
                      ("message-only", [r for r in muts if r["msg"]])]:
        if not sub:
            continue
        cells = []
        for x, y in (("hint", "placebo"), ("hint", "control")):
            b = sum(r[x] and not r[y] for r in sub)
            c = sum(r[y] and not r[x] for r in sub)
            cells.append(f"{b}/{c}, p={binomtest(b, b + c).pvalue if b + c else 1:.3g}")
        lines.append(f"| {name} | {len(sub)} | " + " | ".join(f"{sum(r[a] for r in sub)}" for a in ARMS) + " | "
                     + " | ".join(cells) + " |")
    lines += ["", "Hint compliance (suggested literal inputs that appear in the new tests; same literals checked in "
              "every arm):", ""]
    for a in ARMS:
        u, n = sum(r["used"] for r in comp if r["arm"] == a), sum(r["n"] for r in comp if r["arm"] == a)
        lines.append(f"- {a}: {u}/{n}")
    gen = []
    for a in ARMS:
        recs = [json.load(open(p)) for p in cc.WORK.glob(f"{a}/s*/*/coverup-tests/rec_*.json")]
        gen.append(f"- {a}: {sum(r['ok'] for r in recs)}/{len(recs)} functions with passing tests")
    lines += ["", "Generation:", ""] + gen + ["", f"Cost: {json.dumps(ev.cost())}"]
    (cc.OUT / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["targets", "run", "report"])
    ap.add_argument("args", nargs="+")
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    if a.cmd == "targets":
        for pkg in a.args:
            ts = targets(pkg)
            n = sum(len(t["mutants"]) for t in ts)
            sem = sum(not m["message_only"] for t in ts for m in t["mutants"].values())
            hinted = sum(any(h[0] == m["line"] for h in t["hints"]) for t in ts for m in t["mutants"].values() if not m["message_only"])
            print(f"[targets] {pkg}: {len(ts)} functions, {n} surviving mutants ({sem} semantic, {hinted} of them on a "
                  f"line with a hint); {sum(bool(t['hints']) for t in ts)} functions have hints")
    elif a.cmd == "run":
        run(a.args[0], a.args[1:], a.seed)
    else:
        report(a.args)
