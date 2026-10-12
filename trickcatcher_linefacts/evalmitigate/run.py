"""Generate, evaluate, and re-oracle the two EvalAndMitigate baselines."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
HARNESS = HERE.parent
sys.path.insert(0, str(HARNESS.parent))
from trickcatcher_linefacts import evaluate as evaluator, oracle_b01, preconditions
from trickcatcher_linefacts import prompts as harness_prompts
from trickcatcher_linefacts.evalmitigate import prompts
from trickcatcher_linefacts.llm_client import Client, atomic_json

TASKS = HARNESS / "out/tasks_v3m2_all.json"
OUT = HARNESS / "out/gen2_qwen7b_evalmitigate"
ORACLE_OUT = HARNESS / "out/oracle_evalmitigate"
PAPER_PROMPTS = HARNESS.parent / "EvalAndMitigate/Prompt_example"
TEST_SETTINGS = dict(temperature=0.7, top_p=0.95, max_tokens=1024)
DOC_SETTINGS = dict(temperature=0, top_p=1, max_tokens=4096)
CALL_FIELDS = ("key", "params", "n_in", "n_out", "seconds", "cache_hit", "transport_attempts")


def sha(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def digest(value):
    return sha(json.dumps(value, sort_keys=True, ensure_ascii=False))


def scrub(value):
    """Protect even canned responses and old cache hits; never serialize the endpoint."""
    if isinstance(value, str):
        for name in ("QWEN_BASE_URL", "QWEN_API_KEY"):
            secret = os.environ.get(name)
            if secret:
                value = value.replace(secret, "[redacted]")
        return value
    if isinstance(value, dict):
        return {scrub(k): scrub(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [scrub(v) for v in value]
    return value


def save(path, value):
    atomic_json(path, scrub(value))


def immutable(path, value):
    value = json.loads(json.dumps(scrub(value)))
    if path.exists() and json.loads(path.read_text()) != value:
        raise ValueError("Manifest changed; choose a fresh output directory")
    save(path, value)


def provenance(bundle, model, k, arms):
    templates = dict(system=prompts.SYSTEM, test_generation=prompts.TEST_GENERATION_PROMPT,
                     advanced_docstring=prompts.ADVANCED_DOCSTRING_PROMPT, assertion_tail=harness_prompts.TAIL)
    return dict(version="evalmitigate-v1", model=model, facts_version=bundle["facts_version"],
                k=k, arms=list(arms), tasks_sha256=digest(bundle),
                sampling=dict(test_generation=TEST_SETTINGS, advanced_docstring=DOC_SETTINGS),
                seed_scheme="20261010 + ((250000 + task*2 + arm_index)*1000 + sample)*8 + stage*2",
                stage1_cost_accounting="charged once to advdoc sample 0",
                prompt_sha256={name: sha(text) for name, text in templates.items()},
                paper_prompt_sha256={name: sha((PAPER_PROMPTS / name).read_bytes()) for name in
                                     ("Test_Generation_Prompt", "Advanced_Docstring_Prompt_Base_Model")},
                prereg_sha256=sha((HARNESS / "PREREG.md").read_bytes()),
                source_sha256={name: sha((HARNESS / name).read_bytes()) for name in
                               ("evalmitigate/run.py", "evalmitigate/prompts.py", "llm_client.py", "preconditions.py",
                                "prompts.py", "evaluate.py", "gen_evaluation.py", "oracle_b01.py")})


def load_bundle(path=TASKS, ids=None):
    bundle = json.loads(Path(path).read_text())
    if ids is not None:
        if len(set(ids)) != len(ids):
            raise ValueError("task ids must be distinct")
        tasks = [t for t in bundle["tasks"] if t["task"] in ids]
        if {t["task"] for t in tasks} != set(ids):
            raise ValueError("unknown task id")
        bundle = dict(bundle, tasks=tasks)
    tasks = bundle["tasks"]
    if not tasks or len({t["task"] for t in tasks}) != len(tasks):
        raise ValueError("expected nonempty distinct tasks")
    if bundle["facts_version"] != "v3m" or any(t.get("facts_version") != "v3m" for t in tasks):
        raise ValueError("expected the v3m2 mined task bundle (facts_version=v3m)")
    for task in tasks:
        if sha(task["mined_valid_src"]) != task["valid_sha256"]:
            raise ValueError("mined validator hash mismatch")
    return bundle


def advanced_doc(task, client, directory, run_id):
    directory.mkdir(parents=True, exist_ok=True)
    messages = prompts.advanced_messages(task)
    prompt_hash = digest(messages)
    parsed_path = directory / "parsed.json"
    if parsed_path.exists():
        parsed = json.loads(parsed_path.read_text())
        if parsed["run_id"] != run_id or parsed["prompt_sha256"] != prompt_hash:
            raise ValueError("stage-1 artifact mismatch")
        if sha((directory / "response.json").read_bytes()) != parsed["response_sha256"]:
            raise ValueError("stage-1 response changed")
        return parsed, json.loads((directory / "response.json").read_text())
    save(directory / "prompt.json", messages)
    response_path = directory / "response.json"
    # A crash after saving the response does not repeat the stage-1 request.
    if response_path.exists():
        response = json.loads(response_path.read_text())
    else:
        response = scrub(client.chat(messages, prompts.seed(task["task"], "advdoc", 0, stage=1), **DOC_SETTINGS))
        save(response_path, response)
    original = preconditions.specification(task)[1]
    doc, failure = prompts.parse_docstring(response["text"], original)
    parsed = dict(task=task["task"], run_id=run_id, prompt_sha256=prompt_hash,
                  response_sha256=sha(response_path.read_bytes()), docstring=doc,
                  parse_failure=failure, used_fallback=failure is not None,
                  seed=prompts.seed(task["task"], "advdoc", 0, stage=1))
    save(parsed_path, parsed)
    return parsed, response


def generate(bundle, out=OUT, *, k=3, workers=16, arms=prompts.ARMS, client=None):
    """Library API permits temporary directories for offline verification."""
    if k not in range(1, 1000) or workers < 1:
        raise ValueError("K must be 1..999 and workers must be positive")
    if not arms or len(set(arms)) != len(arms) or not set(arms) <= set(prompts.ARMS):
        raise ValueError("expected distinct supported arms")
    arms = tuple(a for a in prompts.ARMS if a in arms)
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if not (out / "manifest.json").exists() and any((out / n).exists() for n in ("tasks.json", "gen.jsonl", "eval.jsonl")):
        raise ValueError("output contains artifacts from another run")
    client = client or Client(out / "cache", workers=workers)
    if client.model.lower() not in ("qwen2.5-coder-7b-instruct", "qwen/qwen2.5-coder-7b-instruct"):
        raise ValueError("requires Qwen2.5-Coder-7B-Instruct")
    manifest = provenance(bundle, client.model, k, arms)
    immutable(out / "manifest.json", manifest)
    immutable(out / "tasks.json", bundle)
    run_id = digest(manifest)
    path = out / "gen.jsonl"
    expected = {(t["task"], a, s) for t in bundle["tasks"] for a in arms for s in range(k)}
    done = {}
    if path.exists():
        for line in path.read_text().splitlines():
            row = json.loads(line)
            key = row["task"], row["arm"], row["sample"]
            if row.get("run_id") != run_id or key not in expected or key in done:
                raise ValueError("existing gen.jsonl has mismatched or duplicate rows")
            done[key] = row
    print(f"{len(bundle['tasks'])} tasks; K={k}; {len(done)} completed; {len(expected)-len(done)} pending", flush=True)

    def work(task):
        missing = [(a, s) for a in arms for s in range(k) if (task["task"], a, s) not in done]
        if not missing:
            return []
        parsed, stage1 = (advanced_doc(task, client, out / "advanced_doc" / str(task["task"]), run_id)
                          if any(a == "advdoc" for a, _ in missing) else (None, None))
        results = []
        for arm, sample in missing:
            directory = out / "artifacts" / str(task["task"]) / arm / str(sample)
            messages = prompts.test_messages(task, parsed["docstring"] if arm == "advdoc" else None)
            prompt_hash = digest(messages)
            seed = prompts.seed(task["task"], arm, sample)
            result_path = directory / "result.json"
            if result_path.exists():
                row = json.loads(result_path.read_text())
                if row["run_id"] != run_id or row["prompt_sha256"] != prompt_hash or row["seed"] != seed:
                    raise ValueError("sample artifact mismatch")
            else:
                save(directory / "prompt.json", messages)
                response = scrub(client.chat(messages, seed, **TEST_SETTINGS))
                save(directory / "direct_response.json", response)
                calls = ([stage1] if arm == "advdoc" and sample == 0 else []) + [response]
                row = dict(task=task["task"], split=task["split"], arm=arm, sample=sample, model=client.model,
                           text=response["text"], run_id=run_id, facts_version=bundle["facts_version"],
                           llm_calls=len(calls), n_in=sum(c["n_in"] for c in calls), n_out=sum(c["n_out"] for c in calls),
                           seconds=sum(c["seconds"] for c in calls), calls=[{f: c[f] for f in CALL_FIELDS} for c in calls],
                           seed=seed, prompt_sha256=prompt_hash)
                if arm == "advdoc":
                    row.update(docstring_parse_failure=parsed["parse_failure"], stage1_task=task["task"])
                save(result_path, row)
            results.append(row)
        return results

    # Only the main thread appends rows. Completed task artifacts survive failures.
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for results in pool.map(work, bundle["tasks"]):
            with path.open("a") as stream:
                for row in results:
                    stream.write(json.dumps(scrub(row), ensure_ascii=False) + "\n")
    print(f"generation ready: {path}", flush=True)
    return path


def evaluate(out=OUT):
    out = Path(out)
    manifest = json.loads((out / "manifest.json").read_text())
    bundle = json.loads((out / "tasks.json").read_text())
    rows = [json.loads(line) for line in (out / "gen.jsonl").read_text().splitlines()]
    expected = {(t["task"], a, s) for t in bundle["tasks"] for a in manifest["arms"] for s in range(manifest["k"])}
    keys = {(r["task"], r["arm"], r["sample"]) for r in rows}
    if keys != expected or len(rows) != len(expected) or any(r["run_id"] != digest(manifest) for r in rows):
        raise ValueError("generation is incomplete or mismatched; resume generate first")
    evaluator.evaluate(out / "tasks.json", out / "gen.jsonl", out / "eval.jsonl")
    evaluator.report(out / "tasks.json", out / "eval.jsonl")


def oracle(stage, run=OUT, out=ORACLE_OUT, *, workers=16, use_llm=True, cache_source=None):
    run, out = Path(run).resolve(), Path(out).resolve()
    if out == run or run in out.parents or out in run.parents:
        raise ValueError("oracle output must be separate from generation")
    cache_source = Path(cache_source) if cache_source else HARNESS / "out/oracle_b01/cache"
    if out == cache_source.resolve().parent:
        raise ValueError("cannot overwrite the original oracle run")
    config = dict(version="evalmitigate-oracle-v1", run_manifest_sha256=sha((run / "manifest.json").read_bytes()),
                  tasks_sha256=sha((run / "tasks.json").read_bytes()), eval_sha256=sha((run / "eval.jsonl").read_bytes()),
                  oracle_source_sha256=sha((HARNESS / "oracle_b01.py").read_bytes()),
                  prereg_sha256=sha((HARNESS / "PREREG.md").read_bytes()))
    immutable(out / "manifest.json", config)
    # Copy response cache entries only. Locks and calls.jsonl are not reusable responses.
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


def under_out(path):
    path = Path(path).resolve()
    if HARNESS / "out" not in path.parents:
        raise ValueError("output directory must be under trickcatcher_linefacts/out/")
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate", aliases=["gen"])
    gen.add_argument("--tasks", type=Path, default=TASKS)
    gen.add_argument("--task-ids", type=int, nargs="+")
    gen.add_argument("--out", type=Path, default=OUT)
    gen.add_argument("--k", type=int, default=3)
    gen.add_argument("--workers", type=int, default=16)
    gen.add_argument("--arms", choices=prompts.ARMS, nargs="+", default=prompts.ARMS)
    ev = sub.add_parser("evaluate")
    ev.add_argument("--out", type=Path, default=OUT)
    ora = sub.add_parser("oracle")
    ora.add_argument("stage", choices=("collect", "llm", "score", "all"))
    ora.add_argument("--run", type=Path, default=OUT)
    ora.add_argument("--out", type=Path, default=ORACLE_OUT)
    ora.add_argument("--workers", type=int, default=16)
    ora.add_argument("--no-llm", action="store_true", help="score only, abstain on uncached B4 judgments")
    args = parser.parse_args(argv)
    if args.command == "oracle" and args.no_llm and args.stage in ("llm", "all"):
        parser.error("--no-llm is only valid for collect/score")
    try:
        out = under_out(args.out)
        if args.command in ("gen", "generate"):
            generate(load_bundle(args.tasks, args.task_ids), out, k=args.k, workers=args.workers, arms=args.arms)
        elif args.command == "evaluate":
            evaluate(out)
        else:
            if args.workers < 1:
                raise ValueError("workers must be positive")
            oracle(args.stage, under_out(args.run), out, workers=args.workers, use_llm=not args.no_llm)
    except Exception as exc:
        # Server/transport exception messages can contain credentials. Show only the class.
        print(f"evalmitigate failed ({type(exc).__name__}); inspect artifacts and resume with the same configuration",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
