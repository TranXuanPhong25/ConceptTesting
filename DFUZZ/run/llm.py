"""The only LLM gateway of the pilot: Vertex AI gemini-2.5-flash, thinking budget 0, ADC auth, per-call ledger.

Runs in /opt/pilot (dfuzz-pilot:arm64). Needs VERTEX_PROJECT / VERTEX_LOCATION (from scripts/vertex_env.sh) and
GOOGLE_APPLICATION_CREDENTIALS (ADC). Never prints project, location, token or key.
`patch_openai()` swaps openai 0.27's ChatCompletion.create so DFUZZ's own code (genPrograms.py, OpenAIModel.generate)
talks to Vertex; whatever api_key/model DFUZZ passes (a dummy) is ignored.
Self-test: python run/llm.py
"""
import json, os, re, threading, time

MODEL = "gemini-2.5-flash"
USD_IN, USD_OUT = 0.30 / 1e6, 2.50 / 1e6
LEDGER = os.environ.get("LEDGER", os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "ledger.jsonl"))
CAP = float(os.environ.get("BUDGET_CAP", "18"))          # whole pilot, hard
PHASE_CAP = float(os.environ.get("PHASE_CAP", CAP))       # per-step soft cap (e.g. 2 for phase 0)
MAX_OUT = int(os.environ.get("MAX_OUTPUT_TOKENS", "8192"))  # guard against runaway repetition at T=0

_lock = threading.Lock()
_ctx = threading.local()
_client = None
_spent = None


class BudgetExceeded(BaseException):
    """BaseException on purpose: DFUZZ's retry loops catch Exception and would otherwise loop forever."""


def spent():
    global _spent
    if _spent is None:
        _spent = 0.0
        if os.path.exists(LEDGER):
            for line in open(LEDGER):
                _spent += json.loads(line).get("usd", 0.0)
    return _spent


def set_ctx(arm, api, kind="mutate", **extra):
    _ctx.v = {"arm": arm, "api": api, "kind": kind, **extra}


def _get_client():
    global _client
    if _client is None:
        from google import genai
        _client = genai.Client(vertexai=True, project=os.environ["VERTEX_PROJECT"],
                               location=os.environ.get("VERTEX_LOCATION", "global"))
    return _client


def chat(messages, temperature=0.0, ctx=None):
    """messages: OpenAI-style [{'role': 'system'|'user'|'assistant', 'content': str}]. Returns the reply text."""
    from google.genai import types
    ctx = ctx or getattr(_ctx, "v", None) or {"arm": "?", "api": "?", "kind": "?"}
    with _lock:
        if spent() >= CAP or spent() >= PHASE_CAP:
            raise BudgetExceeded(f"ledger total ${spent():.4f} >= cap (pilot {CAP}, step {PHASE_CAP})")
    system = "\n".join(m["content"] for m in messages if m["role"] == "system") or None
    contents = [types.Content(role="model" if m["role"] == "assistant" else "user", parts=[types.Part(text=m["content"])])
                for m in messages if m["role"] != "system"]
    cfg = types.GenerateContentConfig(system_instruction=system, temperature=temperature, max_output_tokens=MAX_OUT,
                                      thinking_config=types.ThinkingConfig(thinking_budget=0),
                                      automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True))
    t0, err = time.time(), None
    for attempt in range(10):
        try:
            r = _get_client().models.generate_content(model=MODEL, contents=contents, config=cfg)
            break
        except Exception as e:  # 429 / 5xx / transient network: back off (cf. EvalAndMitigate/run/gemini_shim.py)
            err = re.sub(r"projects/[^/\s]+", "projects/<p>", str(e))[:300]
            if attempt == 9:
                _log({**ctx, "ok": False, "error": err, "in_tok": 0, "out_tok": 0, "usd": 0.0})
                raise
            time.sleep(min(90, 3 * 2 ** attempt))
    u = r.usage_metadata
    tin, tout, tthink = u.prompt_token_count or 0, u.candidates_token_count or 0, u.thoughts_token_count or 0
    text = r.text or ""
    fin = str(r.candidates[0].finish_reason) if r.candidates else "none"
    _log({**ctx, "ok": bool(text), "in_tok": tin, "out_tok": tout, "think_tok": tthink, "finish": fin,
          "usd": round(tin * USD_IN + (tout + tthink) * USD_OUT, 7), "secs": round(time.time() - t0, 1),
          "retries": attempt})
    return text


def _log(rec):
    global _spent
    rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": MODEL, "api_route": "vertex.generate_content", **rec}
    with _lock:
        spent()
        _spent += rec.get("usd", 0.0)
        with open(LEDGER, "a") as f:
            f.write(json.dumps(rec) + "\n")


def patch_openai(default_arm):
    """Route openai.ChatCompletion.create (0.27) to Vertex. The API for the ledger comes from set_ctx(), or, for
    genPrograms.py (sequential), from its own seed prompt ('invoke <API> to process', debug calls inherit it)."""
    import openai
    last = {"api": "?"}

    def create(model=None, messages=None, temperature=0, api_key=None, **_):
        ctx = getattr(_ctx, "v", None)
        if ctx is None:
            m = re.search(r"invoke <?([\w.]+)>? to process", messages[-1]["content"])
            if m:
                last["api"] = m.group(1)
            ctx = {"arm": default_arm, "api": last["api"], "kind": "seed" if m else "seed-repair"}
        return {"choices": [{"message": {"role": "assistant", "content": chat(messages, temperature, ctx)}}]}

    openai.ChatCompletion.create = create
    openai.api_key = "dummy"


if __name__ == "__main__":
    out = chat([{"role": "system", "content": "Reply tersely."}, {"role": "user", "content": "Say OK."}],
               ctx={"arm": "selftest", "api": "-", "kind": "selftest"})
    last = json.loads(open(LEDGER).read().splitlines()[-1])
    print("reply:", out.strip()[:40], "| tokens in/out/think:", last["in_tok"], last["out_tok"], last["think_tok"],
          "| usd:", last["usd"], "| ledger total:", round(spent(), 5))
