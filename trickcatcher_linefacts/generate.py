"""Pilot bundles and prompts; export for Kaggle or optionally call Gemini (Vertex).

  python -m trickcatcher_linefacts.generate select            # writes out/pilot_tasks.json ($0)
  python -m trickcatcher_linefacts.generate bundle            # fixed pilot -> out/pilot_tasks_v3.json ($0)
  python -m trickcatcher_linefacts.generate export --k 3      # v3 -> kaggle/data/prompts.jsonl ($0)
  python -m trickcatcher_linefacts.generate prompts           # dry run: prints token estimate + one prompt per arm ($0)
  python -m trickcatcher_linefacts.generate run --k 3         # paid: appends to out/gen.jsonl, resumes

Selection (PREREG.md): PUTs in tasks.txt with >= 1 fuzz-confirmed fact, minus the 6 PUTs used to design the
concepts, HumanEval/66 (no failing HumanEval+ input on this toolchain) and HumanEval/50 (spec-ambiguous);
20 drawn with random.Random(20261010).
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
sys.path.insert(0, str(REPO))

from trickcatcher_linefacts.prompts import ARMS, build  # noqa: E402

PUTS = REPO / "vendor/TrickCatcher/Datasets/EvalPlus/PUTs"
HE = REPO / "PBT_EdgeCases/run/data/humaneval.jsonl"
FACTS = ROOT / "out/facts_v3f"
TASKS = ROOT / "out/pilot_tasks.json"
TASKS_V3 = ROOT / "out/pilot_tasks_v3.json"
GEN = ROOT / "out/gen.jsonl"
EXPORT = ROOT / "kaggle/data/prompts.jsonl"
EXCLUDE = {22, 33, 111, 122, 123, 139, 66, 50}
N_PILOT, SEED = 20, 20261010


def bundle(n: int, he: dict, facts_dir: Path = FACTS) -> dict:
    r = json.load(open(facts_dir / f"{n}.json"))
    top = [r["facts"][i] for i in r["top3"]]
    return {"task": n, "entry": he["entry_point"], "put": (PUTS / f"HumanEval_{n}/put0.py").read_text(),
            "base": he["test"], "concept_facts": [f["text"] for f in top],
            "concept_meta": top, "placebo_facts": [p["text"] for p in r["placebo3"]],
            "tool_inputs": list(dict.fromkeys(f["witness_call"] for f in top)), "doc_fail": r["doc_fail"]}


def select(tasks_path: Path) -> None:
    he = {int(r["task_id"].split("/")[1]): r for r in map(json.loads, open(HE))}
    ids = [int(x) for x in (ROOT / "tasks.txt").read_text().split()]
    elig = sorted(n for n in ids if n not in EXCLUDE and json.load(open(FACTS / f"{n}.json"))["top3"])
    pick = sorted(random.Random(SEED).sample(elig, N_PILOT))
    tasks_path.parent.mkdir(parents=True, exist_ok=True)
    tasks_path.write_text(json.dumps({"eligible": elig, "pilot": pick, "tasks": [bundle(n, he[n]) for n in pick]},
                                     indent=1) + "\n")
    print(f"eligible {len(elig)}/{len(ids)}; pilot {pick}")


def rebuild(tasks_path: Path, source: Path) -> None:
    if tasks_path.resolve() == source.resolve():
        raise ValueError("bundle output must differ from the original pilot file")
    d = json.loads(source.read_text())
    pick = d["pilot"]
    if len(pick) != N_PILOT or len(set(pick)) != N_PILOT:
        raise ValueError("expected the existing 20 unique pilot ids")
    he = {int(r["task_id"].split("/")[1]): r for r in map(json.loads, open(HE))}
    tasks = [bundle(n, he[n]) for n in pick]
    tasks_path.parent.mkdir(parents=True, exist_ok=True)
    tasks_path.write_text(json.dumps({"pilot": pick, "facts_version": "v3f", "tasks": tasks}, indent=1) + "\n")
    print(f"bundled {len(tasks)} fixed pilot tasks -> {tasks_path}")
    print(f"empty top3: {[t['task'] for t in tasks if not t['concept_meta']]}")


def prompts(tasks_path: Path) -> None:
    d = json.loads(tasks_path.read_text())
    chars = 0
    for t in d["tasks"]:
        for arm in ARMS:
            s, p = build(arm, t)
            chars += len(s) + len(p)
    n = len(d["tasks"]) * len(ARMS)
    print(f"{n} prompts per sample, ~{chars / n / 4:.0f} input tokens each")
    t = d["tasks"][0]
    for arm in ARMS:
        print(f"===== {arm} (task {t['task']})\n{build(arm, t)[1]}\n")


def export(tasks_path: Path, out: Path, k: int) -> None:
    d = json.loads(tasks_path.read_text())
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as fh:
        for sample in range(k):
            for t in d["tasks"]:
                for arm in ARMS:
                    system, user = build(arm, t)
                    fh.write(json.dumps({"task": t["task"], "arm": arm, "sample": sample,
                                         "system": system, "user": user}) + "\n")
    print(f"exported {len(d['tasks']) * len(ARMS) * k} rows -> {out}")


def run(k: int, workers: int, temperature: float, model: str, tasks_path: Path, gen_path: Path) -> None:
    import os
    from ULT_concept.generate import Client
    from testcase_eval.llm import load_env_file

    load_env_file()
    os.environ["LLM_MODEL"] = model
    os.environ["LLM_THINKING_BUDGET"] = "0"
    d = json.loads(tasks_path.read_text())
    gen_path.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if gen_path.exists():
        done = {(r["task"], r["arm"], r["sample"]) for r in map(json.loads, gen_path.open())}
    jobs = [(t, arm, s) for s in range(k) for t in d["tasks"] for arm in ARMS if (t["task"], arm, s) not in done]
    print(f"{len(done)} done, {len(jobs)} to go, model={model}", flush=True)
    client = Client(temperature, 2048)
    lock = threading.Lock()

    def work(job):
        t, arm, s = job
        system, prompt = build(arm, t)
        try:
            text = client.chat(system, [{"role": "user", "parts": [{"text": prompt}]}])
        except Exception as exc:
            print(f"task {t['task']} {arm} {s} failed: {exc}", flush=True)
            return
        with lock, gen_path.open("a") as fh:
            fh.write(json.dumps({"task": t["task"], "arm": arm, "sample": s, "model": model, "text": text}) + "\n")

    with ThreadPoolExecutor(workers) as pool:
        list(pool.map(work, jobs))
    u = client.usage
    cost = u["input_tokens"] * 0.30e-6 + u["output_tokens"] * 2.50e-6
    print(f"usage {u}  est. cost ${cost:.3f} (Gemini 2.5 Flash list price)", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["select", "bundle", "prompts", "export", "run"])
    ap.add_argument("--tasks", type=Path, help="tasks file; bundle/export default to pilot_tasks_v3.json")
    ap.add_argument("--source-tasks", type=Path, default=TASKS, help="existing pilot ids for bundle")
    ap.add_argument("--gen", type=Path, default=GEN)
    ap.add_argument("--export", type=Path, default=EXPORT)
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--model", default="gemini-2.5-flash")
    a = ap.parse_args()
    if a.k < 1:
        ap.error("--k must be positive")
    tasks_path = a.tasks or (TASKS_V3 if a.cmd in ("bundle", "export") else TASKS)
    if a.cmd == "select":
        select(tasks_path)
    elif a.cmd == "bundle":
        rebuild(tasks_path, a.source_tasks)
    elif a.cmd == "prompts":
        prompts(tasks_path)
    elif a.cmd == "export":
        export(tasks_path, a.export, a.k)
    else:
        run(a.k, a.workers, a.temperature, a.model, tasks_path, a.gen)


if __name__ == "__main__":
    main()
