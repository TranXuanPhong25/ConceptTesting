"""Step ablation of the RBCTest-style precondition miner (B5 = F1b), used as an input-validity filter.

Each variant rebuilds valid.py per task from B5's saved outputs (out/precond_qwen7b_v4), changing one step:
  nover          B5 without the verifier: every coded predicate is kept (no run on base-test inputs)
  noconf         B5 without the confirmation step: code is written for every observed candidate, verifier on
  noconf_nover   neither confirmation nor verifier
(F1 = B5 + the exact-quote evidence filter already exists.) Only noconf/noconf_nover need new LLM calls: one code call
per task with the same CODE prompt, seed and settings as B5, given all candidates instead of the confirmed ones.

  V4=... ; $V4 -B trickcatcher_linefacts/rbc_ablation.py --python $V4      # needs QWEN_BASE_URL for the code calls
"""
import argparse, json, os, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from trickcatcher_linefacts import precond_prompts, preconditions, run_v4
from trickcatcher_linefacts.llm_client import Client, atomic_json

B5 = HERE / "out/precond_qwen7b_v4"
OUT = {v: HERE / f"out/precond_qwen7b_abl_{v}" for v in ("nover", "noconf", "noconf_nover")}


def final(code, keep):
    return "\n".join(code[i] for i in keep) + "\ndef valid(*args, **kwargs):\n    return " + (
        " and ".join(f"{i}(*args, **kwargs) is True" for i in keep) or "True") + "\n"


def one(task, client, python):
    t = str(task["task"]); src = B5 / t
    spec, doc, params = preconditions.specification(task)
    b5 = json.loads((src / "summary.json").read_text())
    res = {}
    # nover: B5's coded predicates, all kept
    code = preconditions.predicates(json.loads((src / "code_response.json").read_text())["text"],
                                    [c["id"] for c in json.loads((src / "kept.json").read_text())], params)[0] \
        if (src / "code_response.json").exists() else {}
    res["nover"] = (code, list(code), dict(coded=len(code)))
    # noconf: code for every candidate (B5's observation reply, unchanged)
    cands = json.loads((src / "candidates.json").read_text()) if (src / "candidates.json").exists() else []
    d = OUT["noconf"] / t; d.mkdir(parents=True, exist_ok=True)
    if cands:
        messages = precond_prompts.messages("code", spec, cands)
        atomic_json(d / "code_prompt.json", messages)
        r = client.chat(messages, preconditions.SEED + task["task"], temperature=0, top_p=1, max_tokens=4096)
        atomic_json(d / "code_response.json", r)
        code2 = preconditions.predicates(r["text"], [c["id"] for c in cands], params)[0]
    else:
        code2 = {}
    ver = preconditions.isolated(dict(mode="verify", task=task, code=code2, doc=doc), d, "verifier", python=python)
    res["noconf"] = (code2, ver["survivors"], dict(coded=len(code2), dropped_verifier=len(ver["dropped"])))
    res["noconf_nover"] = (code2, list(code2), dict(coded=len(code2)))
    for v, (c, keep, info) in res.items():
        o = OUT[v] / t; o.mkdir(parents=True, exist_ok=True)
        (o / "valid.py").write_text(final(c, keep))
        atomic_json(o / "summary.json", dict(task=task["task"], variant=v, candidates=len(cands), surviving=len(keep),
                                             b5_surviving=b5["surviving"], mining_failure=b5["mining_failure"], **info))
    return {v: len(r[1]) for v, r in res.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--python", type=Path, default=os.environ.get("V4_PYTHON", sys.executable))
    a = ap.parse_args()
    ids = [int(n) for n in (HERE / "tasks.txt").read_text().split() if int(n) not in run_v4.run_gen.DESIGN]
    tasks, _, _ = run_v4.task_sources(ids)
    for p in OUT.values():
        p.mkdir(parents=True, exist_ok=True)
    client = Client(OUT["noconf"] / "cache", workers=a.workers)
    with ThreadPoolExecutor(a.workers) as pool:
        res = list(pool.map(lambda t: one(t, client, str(a.python)), tasks))
    print({v: sum(r[v] for r in res) for v in OUT}, "surviving conditions over", len(res), "tasks")


if __name__ == "__main__":
    main()
