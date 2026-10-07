"""subset150 spend ledger and per-call log for every Vertex call (hard cap CAP).

run/gemini_shim.py drops the usage metadata, so pipeline scripts run through this wrapper, which wraps the shim
client's generate_content (same hook as m9.gen's): every API attempt goes to out/llm_calls.jsonl with its tokens, USD
(m9's prices), the prompt's sha1/length and the finish reason. The request itself is unchanged. Before each call the
total spend (this log + the m9-path log out/m9/llm_calls.jsonl) must be under CAP, else the run stops (SystemExit, which
the notebooks' retry loops do not catch).

usage (container):  python3 subset150/calllog.py <stage tag> <script.py>     run a nb2py script with logging
host or container:  python3 subset150/calllog.py total | selftest           print the ledger | check the hook
"""
import hashlib, json, os, runpy, sys, time

REPO = "/repo" if os.path.isdir("/repo/run") else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = f"{REPO}/subset150/out"
LOGS = (f"{OUT}/llm_calls.jsonl", f"{OUT}/m9/llm_calls.jsonl")  # notebook-path calls, m9.py-path calls (m9's own logger)
PRICE_IN, PRICE_OUT = 0.30e-6, 2.50e-6  # = m9.PRICE_IN / PRICE_OUT (gemini-2.5-flash, Vertex list price, USD per token)
CAP = 25.0  # USD, all subset150 Vertex calls (user-approved hard cap)


def calls():
    return [dict(json.loads(l), log=p) for p in LOGS if os.path.exists(p) for l in open(p)]


def total(quiet=True):
    cs = calls()
    t = sum(c["usd"] for c in cs)
    if not quiet:
        by = {}
        for c in cs:
            k = by.setdefault(c.get("stage") or f"m9 {c.get('arm')}", [0, 0, 0, 0.0])
            k[0] += 1; k[1] += bool(c.get("in_tok")); k[2] += (c.get("out_tok") or 0) >= 65536; k[3] += c["usd"]
        for s, (n, billed, loops, usd) in sorted(by.items()):
            print(f"{s}: {n} API attempts ({billed} billed, {loops} at the 65,536-token limit) ${usd:.3f}")
        print(f"TOTAL ${t:.3f} of cap ${CAP}")
    return t


def install(stage):
    sys.path[:0] = [REPO, f"{REPO}/run"]
    import gemini_shim
    init = gemini_shim.GeminiChat.__init__

    def patched(self, **kw):
        init(self, **kw)
        raw = self.client.models.generate_content

        def logged(**k):
            spent = total()
            if spent >= CAP:
                raise SystemExit(f"subset150 cap reached: ${spent:.3f} >= ${CAP}")
            c = k.get("contents")
            c = c if isinstance(c, str) else str(c)
            e = {"stage": stage, "in_chars": len(c), "prompt_sha": hashlib.sha1(c.encode()).hexdigest()[:12]}
            t0, err = time.time(), None
            try:
                r = raw(**k)
                u = r.usage_metadata
                it, ot, tt = u.prompt_token_count or 0, u.candidates_token_count or 0, u.thoughts_token_count or 0
                e.update(in_tok=it, out_tok=ot, thought_tok=tt, usd=it * PRICE_IN + (ot + tt) * PRICE_OUT,
                         finish=str(r.candidates[0].finish_reason) if r.candidates else None)
            except Exception as ex:  # 429 etc.: not billed
                err = ex
                e.update(error=repr(ex)[:200], usd=0.0)
            e.update(ts=time.strftime("%Y-%m-%dT%H:%M:%S"), secs=round(time.time() - t0, 1))
            os.makedirs(OUT, exist_ok=True)
            with open(LOGS[0], "a") as f:
                f.write(json.dumps(e) + "\n")
            if err:
                raise err
            return r

        self.client.models.generate_content = logged

    gemini_shim.GeminiChat.__init__ = patched


def selftest():
    """fake shim: a logged call writes tokens/USD; at the cap the next call stops before reaching the API."""
    import tempfile, types
    global LOGS, CAP
    d = tempfile.mkdtemp()
    LOGS, CAP = (f"{d}/a.jsonl", f"{d}/b.jsonl"), 0.001
    um = types.SimpleNamespace(prompt_token_count=1000, candidates_token_count=200, thoughts_token_count=0)
    sent = []
    fake = types.ModuleType("gemini_shim")
    fake.GeminiChat = type("GeminiChat", (), {"__init__": lambda self, **_: setattr(self, "client", types.SimpleNamespace(
        models=types.SimpleNamespace(generate_content=lambda **k: sent.append(k) or types.SimpleNamespace(usage_metadata=um, candidates=[]))))})
    sys.modules["gemini_shim"] = fake
    install("t")
    g = fake.GeminiChat()
    g.client.models.generate_content(model="m", contents="hi", config=None)
    e = json.loads(open(LOGS[0]).read())
    assert sent == [{"model": "m", "contents": "hi", "config": None}] and e["in_tok"] == 1000 and abs(e["usd"] - 0.0008) < 1e-12
    open(LOGS[1], "w").write(json.dumps({"usd": 0.0005, "arm": "concept"}) + "\n")  # the m9-path log counts too
    try:
        g.client.models.generate_content(model="m", contents="again", config=None)
        raise AssertionError("cap not enforced")
    except SystemExit:
        pass
    assert len(sent) == 1 and abs(total() - 0.0013) < 1e-12
    print("selftest ok")


if __name__ == "__main__":
    if sys.argv[1] == "selftest":
        selftest()
    elif sys.argv[1] == "total":
        total(quiet=False)
    else:
        install(sys.argv[1])
        sys.argv = sys.argv[2:]
        runpy.run_path(sys.argv[0], run_name="__main__")
