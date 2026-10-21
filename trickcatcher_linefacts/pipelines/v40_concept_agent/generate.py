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

# Direct-script workers run with -I: establish this copy's package explicitly.
import sys as _package_sys
from pathlib import Path as _PackagePath
if not __package__:
    _package_here = _PackagePath(__file__).resolve().parent
    _package_sys.path.insert(0, str(_package_here.parents[2]))
    __package__ = "trickcatcher_linefacts.pipelines." + _package_here.name
from .paths import REPO as _REPO, DATA_OUT, CONFIG, dataset_paths

import argparse
import json
import random
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = _REPO


from .prompts import ARMS, build  # noqa: E402

PUTS = dataset_paths()["puts"]
HE = dataset_paths()["he"]
FACTS = DATA_OUT / 'facts_v3f'
TASKS = dataset_paths()["selection"]
TASKS_V3 = DATA_OUT / 'pilot_tasks_v3.json'
GEN = DATA_OUT / 'gen.jsonl'
EXPORT = ROOT / "kaggle/data/prompts.jsonl"
EXCLUDE = {22, 33, 111, 122, 123, 139, 66, 50}
N_PILOT, SEED = 20, CONFIG["seeds"]["pilot"]


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
    raise RuntimeError("Use this package run.py arms stage for v7 generation")


def main() -> None:
    raise SystemExit('v30 CPU-only: inherited generation CLI disabled')
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
