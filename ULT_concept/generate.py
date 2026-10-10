"""ULT test generation with the authors' prompts, on native Vertex Gemini.

Mirrors `vendor_ULT/src/generate_cov_openai.py::testgeneration_multiround`:
system.txt + template_base.txt as round 1, then the authors' "Generate another
test method ..." follow-up for rounds 2..K, full chat history kept, temperature
0.2, max_tokens 1024.  Only the client changes (OpenAI -> google-genai), since
the vendored script hard-codes the OpenAI SDK and a missing dataset path.

Append-only, resumes by task_id.

  python -m ULT_concept.generate --dataset ULT_Lite --arm baseline \
      --out ULT_concept/out/ULT_Lite_baseline.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENDOR = ROOT / "vendor_ULT"
sys.path.insert(0, str(ROOT.parent))

from testcase_eval.llm import load_env_file  # noqa: E402

FOLLOW_UP = ("Generate another test method for the function under test. Your answer must be different from "
             "previously-generated test cases, and should cover different statements and branches.")
ARMS = ("baseline",)


def load_dataset(name: str) -> list[dict]:
    # The vendored *.jsonl files are a single JSON array, not JSON lines.
    return json.loads((VENDOR / "datasets" / f"{name}.jsonl").read_text())


def build_prompt(arm: str, task: dict) -> tuple[str, str]:
    system = (VENDOR / "src/prompt/system.txt").read_text().format(lang="python")
    template = (VENDOR / "src/prompt/template_base.txt").read_text()
    prompt = template.format(lang="python", program=task["code"], description=task["prompt"],
                             func_name=task["func_name"])
    if arm != "baseline":
        raise ValueError(f"unknown arm {arm}")
    return system, prompt


class Client:
    def __init__(self, temperature: float, max_tokens: int):
        from google import genai
        from google.genai import types

        self.types = types
        self.client = genai.Client(vertexai=True, project=os.environ["VERTEX_PROJECT"],
                                   location=os.environ.get("VERTEX_LOCATION", "global"))
        self.model = os.environ.get("LLM_MODEL", "gemini-3-flash-preview")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.lock = threading.Lock()
        self.usage = {"calls": 0, "input_tokens": 0, "output_tokens": 0}

    def chat(self, system: str, history: list[dict]) -> str:
        config = self.types.GenerateContentConfig(
            system_instruction=system, temperature=self.temperature, max_output_tokens=self.max_tokens,
            thinking_config=self.types.ThinkingConfig(thinking_budget=int(os.environ.get("LLM_THINKING_BUDGET", "0"))))
        for attempt in range(8):
            try:
                resp = self.client.models.generate_content(model=self.model, contents=history, config=config)
                meta = resp.usage_metadata
                with self.lock:
                    self.usage["calls"] += 1
                    self.usage["input_tokens"] += meta.prompt_token_count or 0
                    self.usage["output_tokens"] += (meta.candidates_token_count or 0) + (meta.thoughts_token_count or 0)
                return resp.text or ""
            except Exception as exc:  # 429 / 5xx: back off and retry
                if attempt == 7:
                    raise
                time.sleep(min(60, 2 ** attempt) + random.random())
        raise RuntimeError("unreachable")


def multiround(client: Client, system: str, prompt: str, k: int) -> list[str]:
    history = [{"role": "user", "parts": [{"text": prompt}]}]
    tests = []
    for _ in range(k):
        text = client.chat(system, history)
        tests.append(text)
        history.append({"role": "model", "parts": [{"text": text}]})
        history.append({"role": "user", "parts": [{"text": FOLLOW_UP}]})
    return tests


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="ULT_Lite", choices=["ULT_Lite", "ULT"])
    ap.add_argument("--arm", default="baseline", choices=ARMS)
    ap.add_argument("--out", required=True)
    ap.add_argument("--num-tests", type=int, default=5)
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--max-tokens", type=int, default=1024)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    load_env_file()
    tasks = load_dataset(args.dataset)[: args.limit]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = {json.loads(l)["task_id"] for l in out.read_text().splitlines()} if out.exists() else set()
    todo = [t for t in tasks if t["task_id"] not in done]
    print(f"[ULT] {args.dataset} arm={args.arm}: {len(done)} done, {len(todo)} to go", flush=True)

    client = Client(args.temperature, args.max_tokens)
    write_lock = threading.Lock()

    def work(task: dict) -> None:
        system, prompt = build_prompt(args.arm, task)
        try:
            tests = multiround(client, system, prompt, args.num_tests)
        except Exception as exc:
            print(f"[ULT] task {task['task_id']} failed: {exc}", flush=True)
            return
        row = {"task_id": task["task_id"], "func_name": task["func_name"], "arm": args.arm,
               "model": client.model, "prompt": prompt, "tests": tests}
        with write_lock, out.open("a") as fh:
            fh.write(json.dumps(row) + "\n")

    with ThreadPoolExecutor(args.workers) as pool:
        list(pool.map(work, todo))
    print(f"[ULT] usage {client.usage}", flush=True)


if __name__ == "__main__":
    main()
