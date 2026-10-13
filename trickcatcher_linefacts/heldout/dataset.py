"""Normalize the selected MBPP+ PUTs; execute verification only in namespaces."""
from __future__ import annotations

import argparse
import ast
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "out/heldout_mbpp"
PASSES = {"pass1": "blind", "pass2_only": "blind_luna", "pass3_only": "blind_haiku"}

# Same recursive numeric comparison as the read-only selection worker. For zero
# atol, EvalPlus' numeric fallback is 1e-6 (including an int versus a float).
COMPARE = '''def _heldout_same(x, y, atol):
    import math
    num = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)
    if num(x) and num(y) and (isinstance(x, float) or isinstance(y, float)):
        return math.isclose(x, y, rel_tol=1e-6, abs_tol=atol or 1e-6)
    if isinstance(x, (list, tuple)) and isinstance(y, (list, tuple)) and len(x) == len(y):
        return type(x) == type(y) and all(_heldout_same(a, b, atol) for a, b in zip(x, y))
    return x == y
'''


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def selected(data=DATA):
    chosen = json.loads((Path(data) / "puts.json").read_text())
    pairs = [(int(n), key) for key in PASSES for n in chosen[key]]
    if len({n for n, _ in pairs}) != len(pairs):
        raise ValueError("a selected task occurs in multiple passes")
    return sorted(pairs)


def spec_text(prompt):
    tree = ast.parse(prompt)
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.Expr) or not isinstance(tree.body[0].value, ast.Constant):
        raise ValueError("expected MBPP's specification string")
    return tree.body[0].value.value


def entry_node(source, entry):
    return next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == entry)


def normalize_put(source, entry, spec):
    """Splice only the entry docstring; retain every other source byte."""
    fn = entry_node(source, entry)
    node = fn.body[0]
    lines = source.encode().splitlines(keepends=True)
    start = sum(map(len, lines[:node.lineno - 1])) + node.col_offset
    old_doc = isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
    end = sum(map(len, lines[:node.end_lineno - 1])) + node.end_col_offset if old_doc else start
    replacement = repr(spec).encode()
    if not old_doc:
        replacement += b"\n" + b" " * node.col_offset
    result = (source.encode()[:start] + replacement + source.encode()[end:]).decode()
    # The executable AST must be identical once entry docstrings are removed.
    def without_doc(src):
        tree = ast.parse(src)
        f = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == entry)
        if ast.get_docstring(f, clean=False) is not None:
            f.body = f.body[1:]
        return ast.dump(tree, include_attributes=False)
    if without_doc(source) != without_doc(result):
        raise ValueError("docstring normalization changed executable code")
    return result


def normalize(row, put):
    n = int(row["task_id"].split("/")[1])
    spec = spec_text(row["prompt"])
    args = ast.unparse(entry_node(row["canonical_solution"], row["entry_point"]).args)
    prompt = f"def {row['entry_point']}({args}):\n    {spec!r}\n"
    # Close the stub, then retain the author's complete program, including imports
    # and helpers. Consumers concatenate prompt + canonical_solution unchanged.
    canonical = "    pass\n\n" + row["canonical_solution"]
    contract = textwrap.indent(textwrap.dedent(row["contract"]).strip(), "    ") + "\n    pass\n"
    he = dict(task_id=f"HumanEval/{n}", entry_point=row["entry_point"], prompt=prompt,
              canonical_solution=canonical)
    plus = dict(he, base_input=row["base_input"], plus_input=row["plus_input"],
                atol=row["atol"], contract=contract, mbpp_task_id=row["task_id"])
    return he, plus, normalize_put(put, row["entry_point"], spec)


def base_check(pairs, atol):
    lines = [COMPARE, "def check(candidate):"]
    for args, expected in pairs:
        call = "candidate(" + ", ".join(repr(a) for a in args) + ")"
        lines.append(f"    assert _heldout_same({call}, {expected}, {atol!r})")
    if not pairs:
        lines.append("    pass")
    return "\n".join(lines) + "\n"


def plus_check(row):
    """Evaluation-only loop format also understood by offline.plus_check_src."""
    canon = "from typing import *\nimport math\n" + row["prompt"] + row["canonical_solution"]
    contract = "from typing import *\nimport math\n" + row["prompt"] + row["contract"]
    return COMPARE + f'''\ndef check(candidate):
    import copy
    _can, _con = {{}}, {{}}
    exec({canon!r}, _can)
    exec({contract!r}, _con)
    for i, args in enumerate({row['plus_input']!r}):
        try:
            _con[{row['entry_point']!r}](*copy.deepcopy(args))
            expected = _can[{row['entry_point']!r}](*copy.deepcopy(args))
        except Exception:
            continue
        assert _heldout_same(candidate(*copy.deepcopy(args)), expected, {row['atol']!r})
'''


def worker(job_path, result_path):
    """Trusted selection/check adapter, always launched with unshare -rn -I -B."""
    import contextlib
    import copy
    import io
    import signal
    job = json.loads(Path(job_path).read_text())
    exec(COMPARE, globals())

    class Timeout(BaseException):
        pass

    def alarm(*_):
        raise Timeout()
    signal.signal(signal.SIGALRM, alarm)

    def timed(fn, secs=3):
        signal.alarm(secs)
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                return "ok", fn()
        except BaseException as exc:
            return type(exc).__name__, None
        finally:
            signal.alarm(0)

    def load(src):
        ns = {}
        status, _ = timed(lambda: exec("from typing import *\nimport math\n" + src, ns), 5)
        if status != "ok":
            raise ValueError("load: " + status)
        return ns[job["entry"]]

    result = dict(base_rejected=0, base_canonical_errors=[], n_base=0,
                  plus_tested=0, plus_rejected=0, plus_canonical_errors=0,
                  plus_failure=None, canonical_check=False, put_check=False)
    try:
        can, put, con = load(job["canon"]), load(job["put"]), load(job["contract"])
        run = lambda f, a: timed(lambda: f(*copy.deepcopy(a)))
        pairs = []
        for args in job["base"]:
            if run(con, args)[0] != "ok":
                result["base_rejected"] += 1
                continue
            status, expected = run(can, args)
            if status != "ok":
                result["base_canonical_errors"].append(dict(input_repr=repr(args), status=status))
                continue
            pairs.append((args, repr(expected)))
        result["n_base"] = len(pairs)
        result["test"] = base_check(pairs, job["atol"])
        def check(fn):
            ns = {}; exec(result["test"], ns); ns["check"](fn)
        for key, fn in (("canonical_check", can), ("put_check", put)):
            status, _ = timed(lambda: check(fn), 20)
            result[key] = status == "ok"
            result[key + "_status"] = status
        for args in job["plus"]:
            if run(con, args)[0] != "ok":
                result["plus_rejected"] += 1
                continue
            cs, cv = run(can, args)
            if cs != "ok":
                result["plus_canonical_errors"] += 1
                continue
            result["plus_tested"] += 1
            ps, pv = run(put, args)
            if ps != "ok" or not _heldout_same(cv, pv, job["atol"]):
                result["plus_failure"] = dict(input_repr=repr(args), put_status=ps)
                break  # Selection requires at least one; do not rescore all plus labels.
        result["ok"] = bool(pairs) and not result["base_canonical_errors"] and result["canonical_check"] and result["put_check"] and result["plus_failure"] is not None
    except BaseException as exc:
        result.update(ok=False, error=f"{type(exc).__name__}: {exc}")
    Path(result_path).write_text(json.dumps(result))


def verify(job, directory, python=sys.executable):
    directory.mkdir(parents=True, exist_ok=True)
    jp, rp = directory / "job.json", directory / "result.json"
    jp.write_text(json.dumps(job))
    rp.unlink(missing_ok=True)
    env = {"PATH": os.defpath, "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        p = subprocess.run(["unshare", "-rn", str(python), "-I", "-B", str(Path(__file__)),
                            "worker", str(jp), str(rp)], env=env, capture_output=True, timeout=600)
        if p.returncode or not rp.exists():
            return dict(ok=False, error=f"verification sandbox rc={p.returncode}")
        return json.loads(rp.read_text())
    except subprocess.TimeoutExpired:
        return dict(ok=False, error="verification sandbox timed out")


def build(data=DATA, out=None, ids=None, workers=8, python=sys.executable):
    data = Path(data); out = Path(out) if out else data / "he"
    choices = selected(data)
    if ids is not None:
        if set(ids) - {n for n, _ in choices}:
            raise ValueError("requested task is not selected")
        choices = [(n, p) for n, p in choices if n in ids]
    with gzip.open(data / "raw/MbppPlus.jsonl.gz", "rt") as stream:
        raw = {int(r["task_id"].split("/")[1]): r for r in map(json.loads, stream)}
    out.mkdir(parents=True, exist_ok=True)
    def one(pair):
        n, source_pass = pair
        path = data / PASSES[source_pass] / str(n) / "solution.py"
        try:
            source = path.read_text()
            he, plus, put = normalize(raw[n], source)
            result = verify(dict(entry=he["entry_point"], put=put, canon=he["prompt"] + he["canonical_solution"],
                                 contract=he["prompt"] + plus["contract"], base=plus["base_input"],
                                 plus=plus["plus_input"], atol=plus["atol"]), out / "verification" / str(n), python)
            he["test"] = result.get("test", "def check(candidate):\n    raise RuntimeError('dataset verification failed')\n")
            plus["test"] = plus_check(plus)
            target = out / "PUTs" / f"HumanEval_{n}" / "put0.py"
            target.parent.mkdir(parents=True, exist_ok=True); target.write_text(put)
            record = dict(task=n, task_id=he["task_id"], mbpp_task_id=raw[n]["task_id"], split="heldout",
                          source_pass=source_pass, source_path=str(path.relative_to(data)),
                          source_sha256=digest(path.read_bytes()), put_sha256=digest(put),
                          verification={k: v for k, v in result.items() if k != "test"})
            return he, plus, record
        except Exception as exc:
            return None, None, dict(task=n, source_pass=source_pass, verification=dict(ok=False, error=str(exc)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(one, choices))
    for name, index in (("humaneval_mbpp.jsonl", 0), ("humaneval_mbpp_plus.jsonl", 1)):
        (out / name).write_text("".join(json.dumps(r[index]) + "\n" for r in results if r[index] is not None))
    task_ids = [n for n, _ in choices]
    (out / "tasks.txt").write_text("\n".join(map(str, task_ids)) + "\n")
    (out / "tasks.json").write_text(json.dumps(dict(pilot=[], design_excluded=[], heldout=task_ids,
                                                   tasks=[dict(task=n, split="heldout") for n in task_ids]), indent=2) + "\n")
    manifest = dict(dataset="EvalPlus MBPP+ v0.2.0", raw_sha256=digest((data / "raw/MbppPlus.jsonl.gz").read_bytes()),
                    tasks_selected=len(choices), tasks_built=sum(r[0] is not None for r in results),
                    failing_checks=[r[2]["task"] for r in results if not r[2]["verification"]["ok"]],
                    puts=[r[2] for r in results])
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"dataset: {manifest['tasks_built']}/{len(choices)} built; failing checks: {manifest['failing_checks']}")
    return manifest


def main():
    if sys.argv[1:2] == ["worker"]:
        worker(*sys.argv[2:4]); return
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=["build"])
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--python", default=sys.executable)
    p.add_argument("--out", type=Path, help="output he/ directory of a subset root (default out/heldout_mbpp/he)")
    p.add_argument("--ids", type=int, nargs="+", help="subset of the selected task ids")
    a = p.parse_args()
    if a.workers < 1:
        p.error("workers must be positive")
    if build(out=a.out, ids=a.ids, workers=a.workers, python=a.python)["failing_checks"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
