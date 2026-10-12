"""V4 hybrid round two on saved advdoc assertions, with doc-only expectations."""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HARNESS.parent))
from trickcatcher_linefacts import evaluate as evaluator, oracle_b01, run_v4
from trickcatcher_linefacts import v4_evaluation, v4_prompts, v4_runtime, v4_strategies
from trickcatcher_linefacts.evalmitigate import prompts, run as baseline
from trickcatcher_linefacts.llm_client import Client

ARMS = ("advdoc-hybrid", "advdoc-plainhybrid")
TASKS = HARNESS / "out/tasks_v3m2hyb_v4.json"
ADVDOC = HARNESS / "out/gen2_qwen7b_evalmitigate"
OUT = HARNESS / "out/gen2_qwen7b_advhyb_v4"
ORACLE_OUT = HARNESS / "out/oracle_advhyb"
ORACLE_CACHE = HARNESS / "out/oracle_v3m2hyb/cache"
STRATEGY_SETTINGS = dict(temperature=0, top_p=1, max_tokens=4096)
ORACLE_SETTINGS = dict(temperature=0.7, top_p=0.95, max_tokens=1024)
sha, digest, save, immutable, scrub = baseline.sha, baseline.digest, baseline.save, baseline.immutable, baseline.scrub
# Adapt the onlydoc template's last paragraph to the fixed selected inputs.
INJECTED_PROMPT = prompts.TEST_GENERATION_PROMPT[:prompts.TEST_GENERATION_PROMPT.index(
    "Please write some unit tests")] + '''For each selected input below, write exactly one
`assert <entry>(<args>) == <expected>` assertion. Keep each call exactly as given.
Derive the exact expected value from the specification above. Reply with a single
```python code block containing one assertion per input and no explanations.

SELECTED INPUTS:
{calls}
'''


def seed(task, arm, sample, stage=0, request=0, retry=0):
    """Disjoint uint32 range; preserve v4's stage/request/retry seeded selection."""
    if not (0 <= int(task) < 1000 and 0 <= sample < 1000 and stage in range(4)
            and request in range(64) and retry in (0, 1)):
        raise ValueError("seed indices out of range")
    return 3000000000 + (((int(task)*2 + ARMS.index(arm))*1000 + sample)*512
                         + stage*128 + request*2 + retry)


def injected_messages(task, docstring, selected):
    return prompts.messages(INJECTED_PROMPT.format(
        **prompts.metadata(task, docstring), calls="\n".join(r["call"] for r in selected)))


def validate_bundle(bundle):
    tasks = bundle["tasks"]
    if bundle.get("facts_version") != "v4" or not tasks or len({t["task"] for t in tasks}) != len(tasks):
        raise ValueError("expected a nonempty v4 bundle of distinct tasks")
    for t in tasks:
        if (t.get("facts_version") != "v4" or sha(t["strategy_src"]) != t["strategy_sha256"]
                or sha(t["mined_valid_src"]) != t["valid_sha256"]
                or t["mining_summary"].get("preconditions_version") != "B5"
                or t["mining_summary"].get("evidence_filter") is not False):
            raise ValueError("v4/B5 bundle hash/version mismatch")
        if len(t["concept_meta"]) > 3:
            raise ValueError("expected at most three shown facts")
        if any("mutant_src" not in f for key in ("concept_meta", "placebo_meta")
               for f in t[key] if f["kind"] == "MUTANT"):
            raise ValueError("shown mutants require full sources")


def load_bundle(path=TASKS, ids=None):
    bundle = json.loads(Path(path).read_text())
    if ids is not None:
        if len(set(ids)) != len(ids):
            raise ValueError("task ids must be distinct")
        tasks = [t for t in bundle["tasks"] if t["task"] in ids]
        if {t["task"] for t in tasks} != set(ids):
            raise ValueError("unknown task id")
        bundle = dict(bundle, tasks=tasks)
    validate_bundle(bundle)
    return bundle


def read_advdoc(bundle, k, source):
    source = Path(source)
    wanted = {(t["task"], s) for t in bundle["tasks"] for s in range(k)}
    rows = {}
    for line in (source / "gen.jsonl").read_text().splitlines():
        row = json.loads(line)
        key = row["task"], row["sample"]
        if row["arm"] != "advdoc" or key not in wanted:
            continue
        if key in rows:
            raise ValueError("duplicate advdoc round-one row")
        rows[key] = row
    if set(rows) != wanted:
        raise ValueError("missing advdoc round-one rows; generation never regenerates them")
    docs, hashes = {}, {}
    for task in bundle["tasks"]:
        path = source / "advanced_doc" / str(task["task"]) / "parsed.json"
        parsed = json.loads(path.read_text())
        # parsed.docstring already contains the original docstring on parse failure.
        if parsed["task"] != task["task"] or not isinstance(parsed["docstring"], str):
            raise ValueError("invalid saved advdoc docstring")
        if any(rows[task["task"], s]["run_id"] != parsed["run_id"] for s in range(k)):
            raise ValueError("advdoc row/docstring provenance mismatch")
        docs[task["task"]] = parsed
        hashes[str(task["task"])] = sha(path.read_bytes())
    return rows, docs, dict(gen_sha256=sha((source / "gen.jsonl").read_bytes()),
                            parsed_sha256=hashes)


def provenance(bundle, client, k, python, source_hashes, bundle_file_sha256):
    sources = v4_runtime.source_hashes() | {
        name: sha((HARNESS / name).read_bytes()) for name in (
            "evalmitigate/run_advhyb.py", "evalmitigate/prompts.py", "evalmitigate/run.py",
            "evaluate.py", "oracle_b01.py", "spec_facts.py")}
    templates = dict(injected=INJECTED_PROMPT, injected_system=prompts.SYSTEM,
                     hybrid_system=v4_prompts.SYSTEM, target=v4_prompts.TARGET,
                     control=v4_prompts.CONTROL, retry=v4_prompts.RETRY)
    return dict(version="advhyb-v4-v1", facts_version="v4", model=client.model, k=k,
                arms=list(ARMS), bundle_sha256=digest(bundle), bundle_file_sha256=bundle_file_sha256,
                prereg_sha256=sha((HARNESS / "PREREG.md").read_bytes()),
                source_sha256=sources, prompt_sha256={n: sha(t) for n, t in templates.items()},
                advdoc_source=source_hashes, python=str(python), tools=v4_runtime.VERSIONS,
                n_round2=100, per_fact=2, sampling=dict(strategy=STRATEGY_SETTINGS, oracle=ORACLE_SETTINGS),
                seed_scheme="3000000000 + (((task*2 + arm_index)*1000 + sample)*512 + stage*128 + request*2 + retry)",
                round1_cost_accounting="same saved advdoc logical calls attributed to both arms")


def generate(bundle, out=OUT, *, source=ADVDOC, python=None, k=3, workers=16,
             client=None, bundle_file_sha256=None):
    if k not in range(1, 1000) or workers < 1:
        raise ValueError("K must be 1..999 and workers must be positive")
    validate_bundle(bundle)
    python = v4_runtime.interpreter(python)
    originals, docs, source_hashes = read_advdoc(bundle, k, source)
    out = Path(out).resolve()
    if out == Path(source).resolve() or Path(source).resolve() in out.parents:
        raise ValueError("generation output must be separate from saved advdoc")
    if not (out / "manifest.json").exists() and any((out / n).exists() for n in ("tasks.json", "gen.jsonl", "eval.jsonl")):
        raise ValueError("output contains artifacts from another run")
    client = client or Client(out / "cache", workers=workers)
    if client.model.lower() not in ("qwen2.5-coder-7b-instruct", "qwen/qwen2.5-coder-7b-instruct"):
        raise ValueError("requires Qwen2.5-Coder-7B-Instruct")
    manifest = provenance(bundle, client, k, python, source_hashes, bundle_file_sha256)
    immutable(out / "manifest.json", manifest)
    immutable(out / "tasks.json", bundle)
    run_id = digest(manifest)

    def work(pair):
        task, sample = pair
        original = originals[task["task"], sample]
        round1 = original.get("assertions")
        if round1 is None:
            round1 = run_v4.assertions(original["text"])
        results = {}
        for arm in ARMS:
            directory = out / "artifacts" / str(task["task"]) / str(sample) / arm
            directory.mkdir(parents=True, exist_ok=True)
            saved = directory / "result.json"
            if saved.exists():
                result = json.loads(saved.read_text())
                if result["run_id"] != run_id:
                    raise ValueError("sample manifest mismatch")
                results[arm] = result
                continue
            calls = list(original["calls"])
            selected, attempts, stage1_summaries = [], [], []
            count = 0

            def query(messages, stage, request=0, retry=0, label="response", strategy=False):
                save(directory / (label + "_prompt.json"), messages)
                response = scrub(client.chat(messages, seed(task["task"], arm, sample, stage, request, retry),
                                             **(STRATEGY_SETTINGS if strategy else ORACLE_SETTINGS)))
                save(directory / (label + ".json"), response)
                calls.append(response)
                return response["text"]

            plain = arm == "advdoc-plainhybrid"
            shown = [] if plain else task["concept_meta"]
            r1 = run_v4.classify(task, directory / "round1_inputs", python, assertions=round1, shown=shown)
            missed = [i for i, h in enumerate(r1["summary"]["shown_hit_counts"]) if not h]
            budget = results[ARMS[0]]["round2_strategy_requests"] if plain else len(missed)
            for request in range(budget):
                fact = None if plain else shown[missed[request]]
                messages = v4_prompts.hybrid_messages(task, fact, round1)
                for retry in range(1 if plain else 2):
                    d = directory / f"request_{request}_{retry}"
                    d.mkdir(exist_ok=True)
                    raw = query(messages, 1, request, retry, f"strategy_{request}_{retry}", True)
                    count += 1
                    error = None
                    generated = flagged = None
                    try:
                        code = v4_strategies.checked(raw)
                        (d / "strategy.py").write_text(code)
                        generated = v4_strategies.draws(code, task, d, python,
                                                       seed(task["task"], arm, sample, 3, request, retry))
                        flagged = run_v4.classify(task, d, python, candidates=generated["candidates"],
                                                  shown=[fact] if fact else [], requested_draws=100)
                        stage1_summaries.append(flagged["summary"])
                        good = [r for r in flagged["records"] if r["valid"] and (fact is None or r["shown_hits"][0])]
                        if not good:
                            error = "No valid input exercised the fact." if fact else "No valid inputs returned."
                        if generated["nonliteral"] or generated["wrong_arity"] or generated["errors"]:
                            error = json.dumps({key: generated[key] for key in ("nonliteral", "wrong_arity", "errors")})
                    except (SyntaxError, ValueError, RuntimeError) as exc:
                        good = []
                        error = f"{type(exc).__name__}: {exc}"
                    picked = random.Random(seed(task["task"], arm, sample, 3, request, retry)).sample(
                        good, min(2, len(good))) if not error else []
                    attempts.append(dict(request=request, retry=retry, fact_index=missed[request] if fact else None,
                                         error=error, selected=picked, generated=generated,
                                         summary=flagged["summary"] if flagged else None))
                    selected += picked
                    if not error or retry == 1 or plain:
                        break
                    messages += [dict(role="assistant", content=raw),
                                 dict(role="user", content=v4_prompts.RETRY.format(error=error))]
            selected = list({r["input_repr"]: r for r in selected}.values())
            injected = run_v4.assertions(query(injected_messages(task, docs[task["task"]]["docstring"], selected),
                                               2, label="oracle")) if count else []
            final = run_v4.merge(round1, injected)
            inputs = run_v4.classify(task, directory / "final_inputs", python, assertions=final)
            result = dict(task=task["task"], split=task["split"], arm=arm, sample=sample, model=client.model,
                          facts_version="v4", run_id=run_id, text="```python\n" + "\n".join(final) + "\n```",
                          assertions=final, n_assertions=len(final), n_inputs=len(inputs["records"]),
                          n_valid_inputs=inputs["summary"]["valid"], llm_calls=len(calls),
                          n_in=sum(c["n_in"] for c in calls), n_out=sum(c["n_out"] for c in calls),
                          seconds=sum(c["seconds"] for c in calls), calls=calls, selected_inputs=selected,
                          input_summary=inputs["summary"], round1_assertions=round1,
                          round2_strategy_requests=count, generator_attempts=attempts,
                          stage1_summaries=stage1_summaries, round1_input_summary=r1["summary"],
                          missed_fact_indices=missed, advdoc_run_id=original["run_id"],
                          docstring_parse_failure=docs[task["task"]].get("parse_failure"))
            if plain:
                result["matched_strategy_requests"] = budget
                assert count == budget
            save(saved, result)
            results[arm] = result
        return [results[a] for a in ARMS]

    with ThreadPoolExecutor(max_workers=workers) as pool:
        groups = list(pool.map(work, [(t, s) for t in bundle["tasks"] for s in range(k)]))
    pending = out / "gen.pending.jsonl"
    pending.write_text("".join(json.dumps(scrub(r), ensure_ascii=False) + "\n" for g in groups for r in g))
    pending.replace(out / "gen.jsonl")
    print(f"advhyb generation ready: {len(bundle['tasks'])*k*2} rows", flush=True)
    return out / "gen.jsonl"


def check_cohort(out, name="gen.jsonl"):
    manifest = json.loads((out / "manifest.json").read_text())
    bundle = json.loads((out / "tasks.json").read_text())
    rows = [json.loads(line) for line in (out / name).read_text().splitlines()]
    expected = {(t["task"], a, s) for t in bundle["tasks"] for a in ARMS for s in range(manifest["k"])}
    if (manifest["arms"] != list(ARMS) or digest(bundle) != manifest["bundle_sha256"]
            or {(r["task"], r["arm"], r["sample"]) for r in rows} != expected
            or len(rows) != len(expected) or any(r["run_id"] != digest(manifest) for r in rows)):
        raise ValueError("cohort incomplete or mismatched; resume generate first")
    return manifest, bundle, rows


def report(out):
    _, _, rows = check_cohort(out, "eval.jsonl")
    stats = {}
    lines = ["Advdoc hybrid o0 evaluation", "", "split arm samples detecting_samples any_of_K false_alarms/assertions strategy_requests calls tokens_in tokens_out"]
    for split in sorted({r["split"] for r in rows}):
        group = [r for r in rows if r["split"] == split]
        stats[split] = {}
        for arm in ARMS:
            rs = [r for r in group if r["arm"] == arm]
            aa = [a for r in rs for a in r["asserts"]]
            m = dict(samples=len(rs), detecting_samples=sum(v4_evaluation.detects(r["asserts"]) for r in rs),
                     any_of_k=sum(any(v4_evaluation.detects(r["asserts"]) for r in rs if r["task"] == n)
                                  for n in {r["task"] for r in rs}),
                     false_alarms=sum(a["canon"] != "ok" for a in aa), assertions=len(aa),
                     strategy_requests=sum(r["round2_strategy_requests"] for r in rs),
                     calls=sum(r["llm_calls"] for r in rs), n_in=sum(r["n_in"] for r in rs),
                     n_out=sum(r["n_out"] for r in rs))
            stats[split][arm] = m
            lines.append(f"{split} {arm} {m['samples']} {m['detecting_samples']} {m['any_of_k']} "
                         f"{m['false_alarms']}/{m['assertions']} {m['strategy_requests']} {m['calls']} {m['n_in']} {m['n_out']}")
        stats[split]["comparisons"] = [v4_evaluation.comparison(group, *ARMS, matched=matched)
                                        for matched in (False, True)]
    save(out / "report.json", stats)
    text = "\n".join(lines) + "\n"
    (out / "report.txt").write_text(text)
    print(text, end="")


def evaluate(out=OUT, python=None):
    out = Path(out)
    manifest, _, _ = check_cohort(out)
    python = v4_runtime.interpreter(python or manifest["python"])
    if str(python) != manifest["python"]:
        raise ValueError("evaluation must use the generation v4 interpreter")
    evaluator.evaluate(out / "tasks.json", out / "gen.jsonl", out / "eval.jsonl", python=python)
    # The existing v4 report requires all seven original arms. Keep its evaluator
    # and write a two-arm report directly, so eval.jsonl is always delivered.
    report(out)


def oracle(stage, run=OUT, out=ORACLE_OUT, *, workers=16, use_llm=True, cache_source=ORACLE_CACHE):
    run, out, cache_source = Path(run).resolve(), Path(out).resolve(), Path(cache_source).resolve()
    if workers < 1 or stage not in ("collect", "llm", "score", "all"):
        raise ValueError("invalid oracle stage/workers")
    if out == run or run in out.parents or out in run.parents or out == cache_source.parent:
        raise ValueError("oracle output must be separate from source runs")
    check_cohort(run, "eval.jsonl")
    config = dict(version="advhyb-oracle-v1", run_manifest_sha256=sha((run / "manifest.json").read_bytes()),
                  tasks_sha256=sha((run / "tasks.json").read_bytes()), eval_sha256=sha((run / "eval.jsonl").read_bytes()),
                  oracle_source_sha256=sha((HARNESS / "oracle_b01.py").read_bytes()),
                  wrapper_source_sha256=sha(Path(__file__).read_bytes()),
                  prereg_sha256=sha((HARNESS / "PREREG.md").read_bytes()))
    immutable(out / "manifest.json", config)
    if cache_source.exists():
        for source in cache_source.glob("*.json"):
            target = out / "cache" / source.name
            if not target.exists():
                save(target, json.loads(source.read_text()))
    if stage in ("collect", "all"):
        oracle_b01.collect(run, out)
    if stage in ("llm", "all"):
        oracle_b01.llm(run, out, workers=workers)
    if stage in ("score", "all"):
        oracle_b01.score(run, out, workers=min(workers, 12), use_llm=use_llm)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate")
    gen.add_argument("--tasks", type=Path, default=TASKS)
    gen.add_argument("--task-ids", type=int, nargs="+")
    gen.add_argument("--advdoc-run", type=Path, default=ADVDOC)
    gen.add_argument("--out", type=Path, default=OUT)
    gen.add_argument("--python", type=Path, default=os.environ.get("V4_PYTHON"))
    gen.add_argument("--k", type=int, default=3)
    gen.add_argument("--workers", type=int, default=16)
    ev = sub.add_parser("evaluate")
    ev.add_argument("--out", type=Path, default=OUT)
    ev.add_argument("--python", type=Path)
    ora = sub.add_parser("oracle")
    ora.add_argument("stage", choices=("collect", "llm", "score", "all"))
    ora.add_argument("--run", type=Path, default=OUT)
    ora.add_argument("--out", type=Path, default=ORACLE_OUT)
    ora.add_argument("--cache-source", type=Path, default=ORACLE_CACHE)
    ora.add_argument("--workers", type=int, default=16)
    ora.add_argument("--no-llm", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "oracle" and args.no_llm and args.stage in ("llm", "all"):
        parser.error("--no-llm is only valid for collect/score")
    try:
        out = baseline.under_out(args.out)
        if args.command == "generate":
            generate(load_bundle(args.tasks, args.task_ids), out, source=args.advdoc_run, python=args.python,
                     k=args.k, workers=args.workers, bundle_file_sha256=sha(args.tasks.read_bytes()))
        elif args.command == "evaluate":
            evaluate(out, args.python)
        else:
            oracle(args.stage, baseline.under_out(args.run), out, workers=args.workers,
                   use_llm=not args.no_llm, cache_source=args.cache_source)
    except Exception as exc:
        print(f"advhyb failed ({type(exc).__name__}); inspect artifacts and resume with the same configuration",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
