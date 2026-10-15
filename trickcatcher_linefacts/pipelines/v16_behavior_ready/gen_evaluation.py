"""Evaluation-only canonical comparisons and stratified post-pilot reports."""
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
import collections
import contextlib
import io
import json

from .gen_prompts import ARMS, INPUT_ARMS

# Report-only additions: generation prompts, seeds and existing arm order stay frozen.
ARMS = ARMS + ("onlydoc", "advdoc")


def input_metrics(job, row, put, canon, iput, mutants, assertion_calls):
    # Called only inside evaluate.py's existing isolated worker, after selection.
    from .tracer import alarm, call, dcopy, fact_hit, load_module, same, trace
    from . import spec_facts
    if job.get("mined_src") is not None:
        from .preconditions import load_predicate
        checker = load_predicate(job["mined_src"], "valid")
    else:
        checker = load_module(job["contract_src"], filename="<contract>")[job["entry"]]
    if row["arm"] in INPUT_ARMS:
        calls = [(ast.literal_eval(r["input_repr"]), {}) for r in row["selected_inputs"]]
    else:
        calls = assertion_calls
    from . import scorer
    if CONFIG.get('shared_scorer'):
        same = lambda a,b: scorer.output_equal(a,b,job.get('atol',0.0))
    records, seen = [], set()
    for args, kwargs in calls:
        identity = repr((args, kwargs))
        if identity in seen:
            continue
        seen.add(identity)
        valid, error = True, None
        try:
            with contextlib.redirect_stdout(io.StringIO()), alarm(1):
                accepted = checker(*dcopy(args), **dcopy(kwargs))
                if job.get("mined_src") is not None and accepted is not True:
                    valid, error = False, "mined precondition rejected input"
        except BaseException as exc:
            valid, error = False, type(exc).__name__
        literal = repr(args)  # v7: very large inputs (e.g. 'a' * 10**6) are stored truncated; scoring uses the assertion source
        literal = literal if len(literal) <= 2000 else literal[:2000] + f"...[{len(literal)} chars]"
        result = dict(input_repr=literal, valid=valid, contract_error=error,
                      hits=[False] * len(job["facts"]), bug_revealing=False)
        if valid:
            tr = trace(iput, (args, kwargs))
            pout, cout = call(put, (args, kwargs)), call(canon, (args, kwargs))
            result.update(put_status=pout[0], canon_status=cout[0], canonical_scored=cout[0] == "ok",
                          bug_revealing=(pout[0] != "ok" or not same(pout[1], cout[1])) if cout[0] == "ok" else None,
                          hits=[spec_facts.in_class(f["input_class"]["cls"], args[f["input_class"]["param"]]) if "input_class" in f else  # v7
                                fact_hit(f, tr, pout, call(mutants[i], (args, kwargs)) if i in mutants else None)
                                for i, f in enumerate(job["facts"])])
        records.append(result)
    return records


def report(tasks_path, eval_path, compare_paths=()):
    if json.load(open(tasks_path)).get("facts_version") == "v4":
        if compare_paths:
            raise ValueError("merged reports require gen2 bundles")
        from .v4_evaluation import report as v4_report
        return v4_report(tasks_path, eval_path)
    from .evaluate import sign_p
    bundles = {t["task"]: t for t in json.load(open(tasks_path))["tasks"]}
    rows = [json.loads(line) for line in open(eval_path)]
    for path in compare_paths:
        rows += [json.loads(line) for line in open(path)]
    if not rows:
        print("No evaluated rows.")
        return
    k = max(r["sample"] for r in rows) + 1
    present = {r["arm"] for r in rows}
    arms = [a for a in ARMS if a in present]
    keys = [(r["task"], r["arm"], r["sample"]) for r in rows]
    expected = {(n, arm, sample) for n in bundles for arm in arms for sample in range(k)}
    if len(set(keys)) != len(keys) or set(keys) != expected:
        raise ValueError("gen2 report requires a complete task x selected-arm x K cohort; use the run's tasks.json")
    for split in ("dev", "pilot"):
        group = {n: t for n, t in bundles.items() if t["split"] == split}
        if not group:
            continue
        for label, cohort in (("all", group), ("without doc_fail", {n: t for n, t in group.items() if not t["doc_fail"]}),
                              ("doc_fail only", {n: t for n, t in group.items() if t["doc_fail"]})):
            if not cohort:
                print(f"\n{split} / {label}: 0 tasks")
                continue
            selected_rows = [r for r in rows if r["task"] in cohort]
            print(f"\n{split} / {label}: {len(cohort)} tasks, K={k}" + (" (primary cohort)" if split == "dev" and label == "all" else ""))
            print("arm          detect/sample any-of-K false-alarm delivery valid-input bug-input calls tokens-in tokens-out")
            detected = {}
            for arm in arms:
                rs = [r for r in selected_rows if r["arm"] == arm]
                asserts = [a for r in rs for a in r["asserts"]]
                for n in cohort:
                    detected[n, arm] = sum(any(a["canon"] == "ok" and a["put"] != "ok" for a in r["asserts"])
                                           for r in rs if r["task"] == n)
                total_facts = sum(len(cohort[r["task"]]["concept_meta"]) for r in rs)
                reached = sum(any(a["hits"][i] for a in r["asserts"]) for r in rs
                              for i in range(len(cohort[r["task"]]["concept_meta"])))
                inputs = [inp for r in rs for inp in r["input_metrics"]]
                valid_inputs = [inp for inp in inputs if inp["valid"]]
                scored_inputs = [inp for inp in valid_inputs if inp.get("canonical_scored")]
                candidate_n = sum(r.get("input_summary", {}).get("candidates", 0) for r in rs)
                valid_n = sum(r.get("input_summary", {}).get("valid", 0) for r in rs)
                if arm not in INPUT_ARMS:
                    candidate_n, valid_n = len(inputs), len(valid_inputs)
                validity = f"{valid_n}/{candidate_n}"
                bug = f"{sum(inp['bug_revealing'] for inp in scored_inputs)}/{len(scored_inputs)}" if arm in INPUT_ARMS else "—"
                print(f"{arm:12s} {sum(detected[n,arm] for n in cohort)/k:13.1f} "
                      f"{sum(detected[n,arm]>0 for n in cohort):8d} "
                      f"{sum(a['canon']!='ok' for a in asserts)/max(1,len(asserts)):11.1%} "
                      f"{reached/max(1,total_facts):8.1%} {validity:11s} {bug:9s} "
                      f"{sum(r['llm_calls'] for r in rs):5d} {sum(r['n_in'] for r in rs):9d} {sum(r['n_out'] for r in rs):10d}")
                kinds = collections.defaultdict(lambda: [0, 0])
                for r in rs:
                    meta = cohort[r["task"]]["concept_meta"]
                    summary = r.get("input_summary")
                    for i, fact in enumerate(meta):
                        kind = "MUTANT-X" if fact.get("extended") else fact["kind"]
                        if summary is not None:
                            hits, denominator = summary["concept_hit_counts"][i], summary["valid"]
                        else:
                            good = [inp for inp in r["input_metrics"] if inp["valid"]]
                            hits, denominator = sum(inp["hits"][i] for inp in good), len(good)
                        kinds[kind][0] += hits
                        kinds[kind][1] += denominator
                print("  valid-input concept fact hits by kind: " + ", ".join(f"{kind}={h}/{n}" for kind,(h,n) in sorted(kinds.items())))
                if arm in INPUT_ARMS:
                    print("  raw validator-valid draws=" +
                          f"{sum(r['input_summary']['raw_valid'] for r in rs)}/{sum(r['input_summary']['requested_draws'] for r in rs)}")
                    print(f"  valid selected inputs without canonical output={len(valid_inputs)-len(scored_inputs)}")
                print(f"  summed request seconds={sum(r['seconds'] for r in rs):.3f}")
                if arm.startswith("gen-"):
                    retry_n = sum(len(r.get("generator_attempts", [])) == 2 for r in rs)
                    empty_n = sum(r.get("empty_inputs", False) for r in rs)
                    print(f"  retries={retry_n}/{len(rs)}, empty-stage2={empty_n}/{len(rs)}")
                if arm in ("toolinput", "concept-toolinput"):
                    print(f"  invalid witnesses removed={sum(r.get('toolinput_removed',0) for r in rs)}")
            for first, second in (("concept-toolinput", "toolinput"), ("concept-toolinput", "concept"),
                                  ("concept-toolinput", "plain"),
                                  ("gen-concept", "gen-plain"), ("gen-concept", "gen-placebo"),
                                  ("gen-concept", "toolinput"), ("gen-concept", "concept"), ("gen-plain", "plain")):
                if first not in arms or second not in arms:
                    continue
                win = sum(detected[n, first] > detected[n, second] for n in cohort)
                loss = sum(detected[n, first] < detected[n, second] for n in cohort)
                print(f"  {first} vs {second}: {win}/{loss}, sign p={sign_p(win,loss):.6g}")
