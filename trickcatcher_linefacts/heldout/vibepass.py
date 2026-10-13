"""Offline VibePass LeetCode adapter; downloaded Python executes only in namespaces.

From trickcatcher_linefacts/: python3 -I -B heldout/vibepass.py build
    --out out/heldout_vibepass_real/he
Task integers are zero-based row offsets in the pinned VibePass release, not
question ids (several buggy programs belong to each question).
"""
from __future__ import annotations

import argparse
import ast
import copy
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))
from trickcatcher_linefacts.heldout.dataset import COMPARE, base_check, digest, plus_check
from trickcatcher_linefacts.analysis.vibepass_feasibility import PREFIX, fuzz_inputs

DATA = ROOT / "out/heldout_vibepass"
OUT = ROOT / "out/heldout_vibepass_real/he"
PYTHON = DATA / "scratch/venv/bin/python3"


def arguments(text):
    """LCB functional input is one JSON value per positional argument."""
    return [json.loads(line) for line in text.strip().splitlines()]


def signature(starter, entry):
    # The starter's last method intentionally has no body.
    tree = ast.parse(starter.rstrip() + "\n        pass\n")
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Solution")
    fn = copy.deepcopy(next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == entry))
    positional = fn.args.posonlyargs + fn.args.args
    if not positional or positional[0].arg != "self":
        raise ValueError("starter method must take self")
    if fn.args.posonlyargs:
        fn.args.posonlyargs.pop(0)
    else:
        fn.args.args.pop(0)
    if fn.args.vararg or fn.args.kwarg or fn.args.kwonlyargs:
        raise ValueError("LCB functional tests require a positional signature")
    params = [a.arg for a in fn.args.posonlyargs + fn.args.args]
    args = "(" + ", ".join(params) + ("," if len(params) == 1 else "") + ")"
    returns = " -> " + ast.unparse(fn.returns) if fn.returns else ""
    return f"def {entry}({ast.unparse(fn.args)}){returns}:\n", args


def normalize(row, task, entry, base, private):
    header, args = signature(row["starter_code"], entry)
    prompt = "from typing import *\n" + header + f"    {row['question_content']!r}\n"
    wrapper = header + f"    {row['question_content']!r}\n    return Solution().{entry}(*copy.deepcopy({args}))\n"
    # Keep source bytes intact, including imports, helper functions and classes.
    def program(src):
        return PREFIX + src + "\n\nimport copy\n\n" + wrapper
    put = program(row["buggy_solution"])
    canonical = "    pass\n\n" + program(row["silver_solution"])
    # Checker helpers live in module scope; the last definition replaces the stub.
    contract = ("    pass\n\n" + PREFIX + row["test_checker"] + "\n\n" + header
                + f"    assert is_valid_test(*{args})\n")
    he = dict(task_id=f"HumanEval/{task}", prompt=prompt, canonical_solution=canonical, entry_point=entry)
    plus = dict(he, base_input=base, plus_input=private, contract=contract, atol=0.0,
                question_id=row["question_id"], vibepass_row=task)
    for src in (put, prompt + canonical, prompt + contract):
        ast.parse(src)
    return he, plus, put


def generated_candidates(data, rows, instances):
    """Replay the feasibility RNG, including unselected rows that advanced it.

    Its cache stores hashed inputs and its examples truncate at 300 characters;
    neither can safely supply complete inputs. Replay uses the original trusted
    generator and seed, then the sandbox rechecks every candidate. No new fuzz
    algorithm or downloaded module is executed here.
    """
    rng = random.Random(20261013)
    out = {}
    selected = {x["row"] for x in instances if x["usable_strict"] and x["platform"] == "leetcode"}
    for item in sorted(instances, key=lambda x: x["row"]):
        if not item["buggy_pass_public"]:
            continue
        row = rows[item["row"]]
        tests = json.loads((data / "scratch/tests" / (row["question_id"] + ".json")).read_text())
        seeds = [t["input"] for split in ("public", "private") for t in tests[split]]
        candidates = fuzz_inputs(row["platform"], seeds, rng)
        if item["row"] in selected:
            if len(candidates) != item["fuzz_candidates"]:
                raise ValueError(f"feasibility replay mismatch for row {item['row']}")
            out[item["row"]] = [arguments(s) for s in candidates]
    return out


def worker(job_path, result_path):
    """Called ONLY through sandbox(); no downloaded module is imported."""
    import contextlib
    import io
    import resource
    import signal
    resource.setrlimit(resource.RLIMIT_AS, (4 << 30, 4 << 30))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    job = json.loads(Path(job_path).read_text())
    compare = {}; exec(COMPARE, compare)

    class Timeout(BaseException):
        pass

    def alarm(*_):
        raise Timeout()
    signal.signal(signal.SIGALRM, alarm)

    def timed(fn, seconds=10):
        signal.setitimer(signal.ITIMER_REAL, seconds)
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                return "ok", fn()
        except BaseException as exc:
            return type(exc).__name__, None
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)

    def load(src):
        ns = {"__name__": "__vibepass__"}
        status, _ = timed(lambda: exec(src, ns))
        if status != "ok":
            raise ValueError("load: " + status)
        return ns[job["entry"]]

    result = dict(ok=False, canonical_check=False, put_check=False, base_rejected=[],
                  base_canonical_errors=[], n_base=0, plus_tested=0, plus_rejected=0,
                  plus_canonical_errors=[], plus_failure=None, generated_valid_indices=[])
    try:
        can, put, con = (load(job[key]) for key in ("canon", "put", "contract"))
        run = lambda fn, a: timed(lambda: fn(*copy.deepcopy(a)))
        pairs = []
        for i, args in enumerate(job["base"]):
            if run(con, args)[0] != "ok":
                result["base_rejected"].append(i)
            status, expected = run(can, args)
            if status != "ok":
                result["base_canonical_errors"].append(dict(index=i, status=status))
            else:
                pairs.append((args, repr(expected)))
        result["n_base"] = len(pairs)
        result["test"] = base_check(pairs, job["atol"])
        def check(fn):
            ns = {}; exec(result["test"], ns); ns["check"](fn)
        for key, fn in (("canonical_check", can), ("put_check", put)):
            status, _ = timed(lambda: check(fn), 120)
            result[key] = status == "ok"
            result[key + "_status"] = status
        valid = [i for i, a in enumerate(job.get("generated", [])) if run(con, a)[0] == "ok"]
        result["generated_checker_valid"] = len(valid)
        result["generated_valid_indices"] = valid[:80]
        plus = job["plus"] + [job["generated"][i] for i in valid[:80]]
        for i, args in enumerate(plus):
            if run(con, args)[0] != "ok":
                result["plus_rejected"] += 1
                continue
            cs, cv = run(can, args)
            if cs != "ok":
                result["plus_canonical_errors"].append(dict(index=i, status=cs))
                continue
            result["plus_tested"] += 1
            ps, pv = run(put, args)
            if ps != "ok" or not compare["_heldout_same"](cv, pv, job["atol"]):
                result["plus_failure"] = dict(index=i, source="private" if i < len(job["plus"]) else "generated",
                                              input_sha256=digest(json.dumps(args)), put_status=ps)
                break
        result["ok"] = bool(pairs) and not result["base_rejected"] and not result["base_canonical_errors"] \
            and result["canonical_check"] and result["put_check"] and result["plus_failure"] is not None
    except BaseException as exc:
        result.update(error=f"{type(exc).__name__}: {exc}")
    Path(result_path).write_text(json.dumps(result))


def sandbox(argv, python, timeout=600):
    """Empty cwd, scrubbed environment, isolated Python and network namespace."""
    with tempfile.TemporaryDirectory(prefix="vibepass_") as cwd:
        return subprocess.run(["unshare", "-rn", str(python), "-I", "-B", *map(str, argv)],
                              cwd=cwd, env={"PATH": os.defpath, "LANG": "C.UTF-8"},
                              capture_output=True, timeout=timeout)


def verify(job, directory, python=PYTHON, timeout=600):
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    jp, rp = directory / "job.json", directory / "result.json"
    jp.write_text(json.dumps(job)); rp.unlink(missing_ok=True)
    try:
        proc = sandbox([Path(__file__).resolve(), "_worker", jp, rp], python, timeout)
        if proc.returncode or not rp.exists():
            result = dict(ok=False, error=f"sandbox rc={proc.returncode}")
        else:
            return json.loads(rp.read_text())
    except subprocess.TimeoutExpired:
        result = dict(ok=False, error="sandbox timed out")
    rp.write_text(json.dumps(result))
    return result


def build(data=DATA, out=OUT, python=PYTHON, workers=8, ids=None):
    data, out = Path(data).resolve(), Path(out).resolve()
    raw_path = data / "data/vibepass/test.jsonl"
    rows = [json.loads(line) for line in raw_path.read_text().splitlines()]
    usable = json.loads((data / "usable.json").read_text())
    instances = usable["instances"]
    choices = sorted((x for x in instances if x["usable_strict"] and x["platform"] == "leetcode"),
                     key=lambda x: x["row"])
    if ids is not None:
        if set(ids) - {x["row"] for x in choices}:
            raise ValueError("requested id is not a strict LeetCode PUT")
        choices = [x for x in choices if x["row"] in ids]
    candidates = generated_candidates(data, rows, instances)
    out.mkdir(parents=True, exist_ok=True)

    def one(item):
        n = item["row"]; row = rows[n]
        record = dict(task=n, task_id=f"HumanEval/{n}", vibepass_row=n, uid=item["uid"],
                      question_id=item["question_id"], split="heldout", difficulty=row["difficulty"])
        try:
            if row["question_id"] != item["question_id"] or item["uid"] != f"{row['question_id']}#{n}":
                raise ValueError("selection/raw identity mismatch")
            tp = data / "scratch/tests" / (row["question_id"] + ".json")
            tests = json.loads(tp.read_text())
            if tests["func_name"] != item["func_name"] or tests["question_id"] != row["question_id"]:
                raise ValueError("decoded tests identity mismatch")
            base, private = ([arguments(t["input"]) for t in tests[split]] for split in ("public", "private"))
            he, plus, put = normalize(row, n, item["func_name"], base, private)
            job = dict(entry=he["entry_point"], canon=he["prompt"] + he["canonical_solution"], put=put,
                       contract=he["prompt"] + plus["contract"], base=base, plus=private,
                       generated=candidates[n], atol=plus["atol"])
            result = verify(job, out / "verification" / str(n), python)
            indices = result.get("generated_valid_indices", [])
            if result.get("generated_checker_valid") != item["fuzz_checker_valid"]:
                result.update(ok=False, replay_error="checker-valid replay count differs from feasibility")
            (out / "verification" / str(n) / "result.json").write_text(json.dumps(result))
            he["test"] = result.get("test", "def check(candidate):\n    raise RuntimeError('verification failed')\n")
            plus["plus_input"] = private + [candidates[n][i] for i in indices]
            plus["test"] = plus_check(plus)
            target = out / "PUTs" / f"HumanEval_{n}" / "put0.py"
            target.parent.mkdir(parents=True, exist_ok=True); target.write_text(put)
            record.update(source_sha256=digest(row["buggy_solution"]), put_sha256=digest(put),
                          silver_sha256=digest(row["silver_solution"]), checker_sha256=digest(row["test_checker"]),
                          tests_sha256=digest(tp.read_bytes()), n_public=len(base), n_private=len(private),
                          n_generated=len(indices), generated_candidates=len(candidates[n]),
                          verification={k: v for k, v in result.items() if k not in ("test", "generated_valid_indices")})
            return he, plus, record
        except Exception as exc:
            record["verification"] = dict(ok=False, error=f"{type(exc).__name__}: {exc}")
            return None, None, record

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(one, choices))
    for name, index in (("humaneval_mbpp.jsonl", 0), ("humaneval_mbpp_plus.jsonl", 1)):
        (out / name).write_text("".join(json.dumps(r[index]) + "\n" for r in results if r[index] is not None))
    task_ids = [x["row"] for x in choices]
    (out / "tasks.txt").write_text("".join(f"{n}\n" for n in task_ids))
    (out / "tasks.json").write_text(json.dumps(dict(pilot=[], design_excluded=[], heldout=task_ids,
        tasks=[dict(task=n, split="heldout") for n in task_ids]), indent=2) + "\n")
    manifest = dict(dataset="VibePass strict LeetCode", source=usable["source"],
                    attribution="VibePass, Bansal et al. (CC-BY-4.0); LiveCodeBench; LeetCode statements/tests",
                    raw_sha256=digest(raw_path.read_bytes()), selection_sha256=digest((data / "usable.json").read_bytes()),
                    id_mapping="task integer = zero-based row in the pinned VibePass test.jsonl",
                    generated_inputs="replay feasibility seed 20261013, sandbox checker, first 80 valid per row",
                    tasks_selected=len(choices), tasks_built=sum(r[0] is not None for r in results),
                    tasks_verified=sum(r[2]["verification"]["ok"] for r in results),
                    questions=len({x["question_id"] for x in choices}),
                    failing_checks=[r[2]["task"] for r in results if not r[2]["verification"]["ok"]],
                    puts=[r[2] for r in results])
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"dataset: {manifest['tasks_built']}/{len(choices)} built; {manifest['tasks_verified']} verified; "
          f"{manifest['questions']} questions; failing checks: {manifest['failing_checks']}", flush=True)
    return manifest


def main():
    if sys.argv[1:2] == ["_worker"]:
        worker(*sys.argv[2:4]); return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build"])
    parser.add_argument("--data", type=Path, default=DATA)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--python", type=Path, default=PYTHON if PYTHON.exists() else Path(sys.executable))
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--ids", type=int, nargs="+")
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("workers must be positive")
    if build(args.data, args.out, args.python.absolute(), args.workers, args.ids)["failing_checks"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
