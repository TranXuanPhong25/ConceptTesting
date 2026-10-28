"""Contract-only validity, frozen fact hits, sandbox orchestration and selection."""
from __future__ import annotations

# Direct-script workers run with -I: establish this copy's package explicitly.
import sys as _package_sys
from pathlib import Path as _PackagePath
if not __package__:
    _package_here = _PackagePath(__file__).resolve().parent
    _package_sys.path.insert(0, str(_package_here.parents[2]))
    __package__ = "trickcatcher_linefacts.pipelines." + _package_here.name
from .paths import REPO as _REPO, DATA_OUT, CONFIG, dataset_paths

import ast
import json
import os
import random
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = _REPO
N = 100
CONTRACTS = dataset_paths()["contracts"]


MAX_INPUT_CHARS = 1000  # longest input repr an oracle prompt can carry (fits the 16k context)


def load_contracts(path=CONTRACTS):
    # Discard canonical_solution/base_input/plus_input immediately; never send them to workers.
    records = {}
    with Path(path).open() as stream:
        for line in stream:
            row = json.loads(line)
            records[int(row["task_id"].split("/")[1])] = {
                "contract_src": row["prompt"] + row["contract"], "entry": row["entry_point"]}
    return records


def arity(task):
    fn = next(n for n in ast.parse(task["put"]).body if isinstance(n, ast.FunctionDef) and n.name == task["entry"])
    if fn.args.vararg or fn.args.kwarg or fn.args.kwonlyargs:
        raise ValueError("variable/keyword-only arity is unsupported")
    return len(fn.args.posonlyargs) + len(fn.args.args)


def extract_generator(text):
    blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", text, re.S)
    code = "\n".join(blocks) if blocks else text.strip()
    tree = ast.parse(code)
    if not any(isinstance(n, ast.FunctionDef) and n.name == "sample_one" for n in tree.body):
        raise ValueError("response has no sample_one() function")
    return code


def sandbox_prefix():
    if sys.platform != 'darwin':
        return ['unshare', '-rn']
    return [] if os.environ.get('LINEFACTS_NETWORK_SANDBOXED') == '1' else [
        '/usr/bin/sandbox-exec', '-p', '(version 1)(allow default)(deny network*)']


def sandbox(python, script, job, output, timeout):
    # No endpoint, token or API credentials enter a generated-code process.
    from .paths import worker_env
    env = worker_env()
    env['LINEFACTS_NETWORK_SANDBOXED'] = '1'
    prefix = sandbox_prefix()
    process = subprocess.Popen(prefix + [str(python), "-I", "-B", str(script), str(job), str(output)],
                               env=env, cwd=job.parent, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               start_new_session=True)
    try:
        deadline = time.monotonic() + timeout
        while process.poll() is None:
            if time.monotonic() >= deadline:
                raise subprocess.TimeoutExpired(process.args, timeout)
            if sys.platform == 'darwin':
                rss = subprocess.run(['/bin/ps', '-axo', 'pgid=,rss='], capture_output=True, timeout=1)
                memory = sum(int(line.split()[1]) for line in rss.stdout.splitlines() if int(line.split()[0]) == process.pid)
                if memory > 3 * 1024 * 1024:
                    raise RuntimeError('sandbox memory limit')
            time.sleep(0.1)
        status = process.returncode
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()
        raise RuntimeError("sandbox total timeout") from None
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
    if status != 0 or not output.exists() or output.stat().st_size > 8 << 20:
        raise RuntimeError(f"sandbox failed (exit {status})")
    return json.loads(output.read_text())


def generate_candidates(code, task, python, directory, sample_seed, *, n=N, per_call_timeout=1, total_timeout=120):
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    jp, op = directory / "generator_job.json", directory / "generated.json"
    jp.write_text(json.dumps(dict(code=code, arity=arity(task), n=n, sample_seed=sample_seed,
                                  per_call_timeout=per_call_timeout)))
    op.unlink(missing_ok=True)
    try:
        return sandbox(python, HERE / "generator_worker.py", jp, op, total_timeout)
    except RuntimeError as exc:
        return dict(attempted=0, returned=0, duplicates=0, rejected=0, candidates=[], errors=[str(exc)])


def witness_candidates(task):
    result, seen = [], set()
    for source in task["tool_inputs"]:
        node = ast.parse(source, mode="eval").body
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != task["entry"] or node.keywords:
            raise ValueError("witness must be a literal positional PUT call")
        args = [ast.literal_eval(n) for n in node.args]
        if len(args) != arity(task):
            raise ValueError("witness arity mismatch")
        literal = repr(args)
        json.dumps(args, allow_nan=False)
        if literal not in seen:
            result.append(dict(input_repr=literal, args=args))
            seen.add(literal)
    return result


def classify(task, contract, candidates, shown, directory, *, requested_draws=None):
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    jp, op = directory / "input_job.json", directory / "inputs.json"
    jp.write_text(json.dumps(dict(entry=task["entry"], put=task["put"], contract_src=contract.get("contract_src"),
                                  mined_src=contract.get("mined_src"),
                                  concept=task["concept_meta"], shown=shown, candidates=candidates,
                                  requested_draws=requested_draws)))
    op.unlink(missing_ok=True)
    try:
        return sandbox(sys.executable, HERE / "gen_inputs.py", jp, op, 900)
    except RuntimeError as exc:
        # Whole classification failed: no input is usable; recorded, the arm proceeds like an empty pool.
        n = len(candidates)
        return dict(records=[], summary=dict(
            candidates=n, valid=0, removed=n, oversize=0, trace_errors=0, raw_candidates=n, raw_valid=0,
            first_contract_message=f"classification failed: {exc}", classification_error=str(exc),
            concept_hit_counts=[0] * len(task["concept_meta"]), shown_hit_counts=[0] * len(shown),
            concept_hit_rates=[0.0] * len(task["concept_meta"]),
            requested_draws=requested_draws if requested_draws is not None else n, raw_valid_rate=0.0))


def classify_worker(job_path, output_path):
    
    from .tracer import HOOKS, alarm, call, dcopy, fact_hit, instrument, load_module, trace
    from .facts import make_mutant
    from . import spec_facts

    job = json.loads(Path(job_path).read_text())
    with alarm(5):
        if job.get("mined_src") is not None:
            from .preconditions import load_predicate
            checker = load_predicate(job["mined_src"], "valid")
        else:
            checker = load_module(job["contract_src"], filename="<contract>")[job["entry"]]
        put = load_module(job["put"])[job["entry"]]
        code, _ = instrument(job["put"])
        iput = load_module(code, HOOKS)[job["entry"]]
    facts = job["concept"] + job["shown"]
    mutants = {}
    for f in facts:
        if f["kind"] == "MUTANT" and f["k"] not in mutants:
            with alarm(5):
                mutants[f["k"]] = load_module(f['mutant_src'] if 'mutant_src' in f else make_mutant(job["put"], f["k"])[0])[job["entry"]]
    records = []
    for candidate in job["candidates"]:
        row = dict(candidate, concept_hits=[False] * len(job["concept"]), shown_hits=[False] * len(job["shown"]))
        if len(candidate["input_repr"]) > MAX_INPUT_CHARS:
            # Cannot be written into the oracle prompt; never traced, never selected.
            row.update(valid=False, oversize=True, call=None,
                       contract_error=f"oversize: input longer than {MAX_INPUT_CHARS} characters")
            records.append(row)
            continue
        args = ast.literal_eval(candidate["input_repr"])
        valid, error = True, None
        try:
            with alarm(1):
                accepted = checker(*dcopy(args))
                if job.get("mined_src") is not None and accepted is not True:
                    valid, error = False, "mined precondition rejected input"
        except BaseException as exc:
            valid, error = False, f"{type(exc).__name__}: {str(exc)[:300]}"
        row.update(valid=valid, contract_error=error)
        if valid:
            try:
                with alarm(10):
                    trace_result = trace(iput, (args, {}))
                    pout = call(put, (args, {})) if mutants else None
                    mouts = {k: call(fn, (args, {})) for k, fn in mutants.items()}
                    hits = [spec_facts.in_class(f["input_class"]["cls"], args[f["input_class"]["param"]]) if "input_class" in f
                            else fact_hit(f, trace_result, pout, mouts.get(f.get("k"))) for f in facts]  # v7 spec facts
                row.update(concept_hits=hits[:len(job["concept"])], shown_hits=hits[len(job["concept"]):])
            except BaseException as exc:
                row["trace_error"] = type(exc).__name__
        row["call"] = job["entry"] + "(" + ", ".join(repr(a) for a in args) + ")"
        records.append(row)
    valid = [r for r in records if r["valid"]]
    count = len(valid)
    summary = dict(candidates=len(records), valid=count, removed=len(records) - count,
                   oversize=sum(bool(r.get("oversize")) for r in records),
                   trace_errors=sum("trace_error" in r for r in valid),
                   raw_candidates=sum(r.get("occurrences", 1) for r in records),
                   raw_valid=sum(r.get("occurrences", 1) for r in valid),
                   first_contract_message=next((r["contract_error"] for r in records if not r["valid"]), None),
                   concept_hit_counts=[sum(r["concept_hits"][i] for r in valid) for i in range(len(job["concept"]))],
                   shown_hit_counts=[sum(r["shown_hits"][i] for r in valid) for i in range(len(job["shown"]))])
    summary["concept_hit_rates"] = [n / count if count else 0.0 for n in summary["concept_hit_counts"]]
    summary["requested_draws"] = job["requested_draws"] if job["requested_draws"] is not None else summary["raw_candidates"]
    summary["raw_valid_rate"] = summary["raw_valid"] / max(1, summary["requested_draws"])
    Path(output_path).write_text(json.dumps(dict(records=records, summary=summary)))


def feedback(generated, classified, shown):
    summary = classified["summary"]
    errors = list(generated.get("errors", []))
    if not summary["valid"]:
        why = summary.get("first_contract_message") or generated.get("first_rejection") or "no usable inputs returned"
        errors.append(f"0 of 100 inputs were valid: {why}")
    else:
        for i, (fact, count) in enumerate(zip(shown, summary["shown_hit_counts"]), 1):
            if not count:
                errors.append(f"None of the 100 inputs exercised fact {i}: {fact['text']}")
    return "\n".join(errors) + "\nPlease write a corrected sample_one() generator. Reply with Python code only." if errors else None


def select(arm, classified, sample_seed, limit=3):
    valid = [r for r in classified["records"] if r["valid"]]
    if arm == "toolinput":
        return valid[:limit]
    rng, chosen = random.Random(sample_seed), []
    if arm in ("gen-concept", "gen-placebo") and valid:
        for i in range(len(valid[0]["shown_hits"])):
            options = [r for r in valid if r["shown_hits"][i] and r not in chosen]
            if options and len(chosen) < limit:
                chosen.append(rng.choice(options))
    remaining = [r for r in valid if r not in chosen]
    chosen += rng.sample(remaining, min(limit - len(chosen), len(remaining)))
    return chosen


if __name__ == "__main__":
    classify_worker(*sys.argv[1:])
