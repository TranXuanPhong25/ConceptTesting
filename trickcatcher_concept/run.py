"""Run the full TrickCatcher pipeline (baseline and/or concept arm) and score it.

Example (resume-safe; rerun the same command after an interruption):
  .venv/bin/python -m trickcatcher_concept.run --split subset --arms baseline,concept \
      --run-dir /home/phong/dev/trickcatcher-concept-data/runs/subset-v1
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import time
import traceback
from pathlib import Path

from trickcatcher_concept import data, sandbox
from trickcatcher_concept.evaluate import EVAL_MODEL, TaskEvaluator, dump, score_arm
from trickcatcher_concept.llm import LLM, load_env_file
from trickcatcher_concept.pipeline import ARMS, ArmRunner, Config, Executor, put_existing_check

DEFAULT_ENV = "/home/phong/dev/ConceptTester/scripts/vertex_env.sh"


def process(entry: dict, index: int, arms: list[str], cfg: Config, llm: LLM, eval_llm: LLM | None,
            executor: Executor, score_only: bool) -> dict:
    task = data.load_task(entry, cfg.artifact)
    row: dict = {"task_num": task.key, "lang": task.lang, "pid": task.pid, "existing_source": task.existing_source}
    row["put_check"] = put_existing_check(task, cfg)
    order = arms if index % 2 == 0 else list(reversed(arms))
    for arm in order:
        if score_only and not (Path(cfg.run_dir) / task.lang / task.pid / arm / "done.json").is_file():
            continue
        runner = ArmRunner(task, arm, cfg, llm, executor)
        row[f"{arm}_summary"] = runner.run()
    items: dict[str, dict] = {}
    task_dir = Path(cfg.run_dir) / task.lang / task.pid
    for arm in arms:
        inputs = json.loads((task_dir / arm / "inputs.json").read_text()) if (task_dir / arm / "inputs.json").is_file() else None
        if inputs:
            for item in inputs["inputs"]:
                items[f"{arm}:{item['id']}"] = dict(item, id=f"{arm}:{item['id']}")
    evaluator = TaskEvaluator(task, cfg, eval_llm, executor)
    facts_all = evaluator.input_facts(list(items.values()))
    row["eval_validator"] = {k: v for k, v in evaluator.eval_validator().items() if k in ("model", "selected", "reason", "n_positives")}
    for arm in arms:
        facts = {key.split(":", 1)[1]: value for key, value in facts_all.items() if key.startswith(arm + ":")}
        inputs = json.loads((task_dir / arm / "inputs.json").read_text()) if (task_dir / arm / "inputs.json").is_file() else {"inputs": []}
        generated = inputs["inputs"]
        usable = [i for i in generated if i["usable"]]
        row[f"{arm}_inputs"] = {
            "generated": len(generated), "usable": len(usable),
            "eval_invalid_generated": sum(facts[i["id"]]["eval_validity"] != "valid" for i in generated),
            "eval_invalid_usable": sum(facts[i["id"]]["eval_validity"] != "valid" for i in usable),
            "byref_invalid_usable": sum(not facts[i["id"]]["byref"] for i in usable),
        }
        for validity in ("strict", "refs"):
            row[f"{arm}_{validity}"] = score_arm(task_dir, arm, facts, validity, use_verify=False)
            if arm == "concept":
                row[f"{arm}_{validity}_verified"] = score_arm(task_dir, arm, facts, validity, use_verify=True)
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", default="subset", help="subset | full | heldout | cpp | python")
    parser.add_argument("--arms", default="baseline,concept")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--artifact", default=str(data.DEFAULT_ARTIFACT))
    parser.add_argument("--env-file", default=DEFAULT_ENV)
    parser.add_argument("--task-workers", type=int, default=4)
    parser.add_argument("--llm-concurrency", type=int, default=8)
    parser.add_argument("--procs", type=int, default=12)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--only", default="", help="comma-separated pids")
    parser.add_argument("--steer-fraction", type=float, default=1.0)
    parser.add_argument("--eval-model", default=EVAL_MODEL)
    parser.add_argument("--score-only", action="store_true")
    parser.add_argument("--out", default="", help="results JSONL (default: <run-dir>/results.jsonl)")
    args = parser.parse_args()

    load_env_file(args.env_file)
    sandbox.set_parallelism(args.procs)
    arms = [a for a in args.arms.split(",") if a]
    assert all(a in ARMS for a in arms), arms
    run_dir = Path(args.run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    cfg = Config(run_dir=run_dir, artifact=Path(args.artifact), steer_fraction=args.steer_fraction, exec_workers=args.procs)
    (run_dir / "config.json").write_text(json.dumps({**{k: str(v) for k, v in vars(cfg).items()}, "arms": arms,
                                                      "split": args.split, "eval_model": args.eval_model}, indent=1))
    import os
    gen_model = os.environ.get("LLM_MODEL", "")
    llm = LLM(run_dir / "llm_cache", args.llm_concurrency, model=gen_model)
    eval_llm = LLM(run_dir / "llm_cache", max(2, args.llm_concurrency // 2), model=args.eval_model)
    executor = Executor(args.procs * 2)
    entries = data.select(args.split)
    if args.only:
        wanted = set(args.only.split(","))
        entries = [e for e in entries if e["pid"] in wanted]
    if args.limit:
        entries = entries[: args.limit]
    out = Path(args.out) if args.out else run_dir / "results.jsonl"
    rows: dict[str, dict] = {}
    started = time.time()
    with cf.ThreadPoolExecutor(max_workers=args.task_workers) as pool:
        futures = {pool.submit(process, e, i, arms, cfg, llm, eval_llm, executor, args.score_only): e
                   for i, e in enumerate(entries)}
        for future in cf.as_completed(futures):
            entry = futures[future]
            key = f"{entry['lang']}/{entry['pid']}"
            try:
                row = future.result()
                rows[key] = row
                bits = " ".join(f"{a}={'X' if (row.get(f'{a}_strict') or {}).get('task_exposed') else '.'}" for a in arms)
                print(f"[{len(rows)}/{len(entries)} {time.time() - started:.0f}s] {key} {bits}", flush=True)
            except Exception as exc:  # noqa: BLE001 - keep the batch going; rerun resumes
                rows[key] = {"task_num": key, "lang": entry["lang"], "pid": entry["pid"],
                             "error": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc()[-2000:]}
                print(f"[ERROR] {key}: {type(exc).__name__}: {str(exc)[:300]}", flush=True)
            dump([rows[k] for k in sorted(rows)], out)
    print(json.dumps({"tasks": len(rows), "errors": sum("error" in r for r in rows.values()), "out": str(out)}), flush=True)


if __name__ == "__main__":
    main()
