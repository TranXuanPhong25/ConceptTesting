"""LLM generation for the PBT_EdgeCases pilot. Runs ONLY in the llm container (MODE=llm bash run/dock.sh python gen.py).
It writes model text to files and never executes generated code.

Prompts: the authors' own builders (vendor pbteval.commands.generate.create_pbt_prompt / create_ebt_prompt) and the
authors' system message. Concept/placebo arms append run/concepts/<arm>/HumanEval_<n>.txt to the unchanged PBT prompt.
Model: gemini-2.5-flash on Vertex (ADC), default temperature (none sent), thinking_budget=0, max_output_tokens=8192.
Concurrency 1; exponential backoff on 429/5xx; hard budget cap BUDGET_CAP (USD, default 3) over the whole ledger.
Order: for k in K, for task, for arm -> arms stay balanced if the cap stops the run. Resumable (skips existing files).
env: K (samples per task per arm, default 1), ARMS (comma list), ONLY (comma list of task numbers).
"""
import json, os, re, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pbteval.commands.generate as G  # vendored, imported read-only
from concepts import TASKS, load_prompts

HERE = Path(__file__).resolve().parent
G.PROMPTS_DIR = Path("/vendor/prompts")  # runtime override of the relative path; vendored file untouched
MODEL = "gemini-2.5-flash"
USD_IN, USD_OUT = 0.30 / 1e6, 2.50 / 1e6
SYSTEM = "You are a code developer assistant."  # verbatim from vendor generate.py
CAP = float(os.environ.get("BUDGET_CAP", "3"))
K = int(os.environ.get("K", "1"))
ARMS = os.environ.get("ARMS", "ebt,pbt,pbt_concept,pbt_placebo").split(",")
ONLY = [int(x) for x in os.environ["ONLY"].split(",")] if os.environ.get("ONLY") else TASKS
LEDGER = HERE / "gen" / "ledger.jsonl"


def build_prompt(arm, prompt, task):
    if arm == "ebt":
        return G.create_ebt_prompt(prompt)
    base = G.create_pbt_prompt(prompt)
    if arm == "pbt":
        return base
    return base + "\n" + (HERE / "concepts" / arm.removeprefix("pbt_") / f"HumanEval_{task}.txt").read_text()


def spent():
    return sum(json.loads(l)["usd"] for l in LEDGER.open()) if LEDGER.exists() else 0.0


def call(client, text, ctx):
    from google.genai import types
    cfg = types.GenerateContentConfig(system_instruction=SYSTEM, max_output_tokens=8192,
                                      thinking_config=types.ThinkingConfig(thinking_budget=0))
    t0 = time.time()
    for attempt in range(8):
        try:
            r = client.models.generate_content(model=MODEL, contents=text, config=cfg)
            break
        except Exception as e:  # 429 / 5xx / network: back off
            err = re.sub(r"projects/[^/\s]+", "projects/<p>", str(e))[:200]
            print(f"  retry {attempt}: {err}", flush=True)
            if attempt == 7:
                raise
            time.sleep(min(120, 5 * 2 ** attempt))
    u = r.usage_metadata
    tin, tout, tth = u.prompt_token_count or 0, u.candidates_token_count or 0, u.thoughts_token_count or 0
    rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": MODEL, **ctx, "in_tok": tin, "out_tok": tout,
           "think_tok": tth, "usd": round(tin * USD_IN + (tout + tth) * USD_OUT, 7), "secs": round(time.time() - t0, 1),
           "retries": attempt, "finish": str(r.candidates[0].finish_reason) if r.candidates else "none"}
    with LEDGER.open("a") as f:
        f.write(json.dumps(rec) + "\n")
    return r.text or "", rec


if __name__ == "__main__":
    from google import genai
    client = genai.Client(vertexai=True, project=os.environ["VERTEX_PROJECT"],
                          location=os.environ.get("VERTEX_LOCATION", "global"))
    prompts = load_prompts(HERE / "data" / "humaneval.jsonl")  # prompt + entry_point only
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    worst = 0.02
    for k in range(K):
        for TASK in ONLY:
            for arm in ARMS:
                out = HERE / "gen" / arm / f"k{k}" / f"HumanEval_{TASK}.txt"
                if out.exists():
                    continue
                text = build_prompt(arm, prompts[TASK][0], TASK)
                pdir = HERE / "gen" / "prompts" / arm
                pdir.mkdir(parents=True, exist_ok=True)
                (pdir / f"HumanEval_{TASK}.txt").write_text(text)
                if spent() + worst > CAP:
                    sys.exit(f"STOP: ledger ${spent():.4f} + next-call estimate ${worst:.4f} > cap ${CAP}")
                reply, rec = call(client, text, {"arm": arm, "task": TASK, "k": k})
                worst = max(worst, rec["usd"] * 1.5)
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(reply)
                print(f"k={k} HumanEval/{TASK} {arm}: in {rec['in_tok']} out {rec['out_tok']} ${rec['usd']:.5f} "
                      f"total ${spent():.4f}", flush=True)
    print(f"DONE total ${spent():.4f}")
