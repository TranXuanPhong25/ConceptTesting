"""OBS-null probe: replay frozen E4 T2 contexts with/without `"output": null` on exception rows (see PREREG.md).

Usage: QWEN_BASE_URL=... python3 -I run.py [--dry-run]
The endpoint URL is read from the environment only and is never printed or written.
"""
import hashlib, json, os, re, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, "../../out/pipelines/v40_concept_agent/humaneval/d1_retry3_20261021")
CONTEXTS = ["E4__concept_adaptive__2", "E4__concept_committed__2", "E4__generic_adaptive__2"]
OLD, NEW = '"output": null, "output_capture": "unavailable"', '"output_capture": "unavailable"'
MODEL = "qwen2.5-coder-32b-instruct"
PARAMS = {"max_tokens": 1536, "temperature": 0, "top_p": 1, "seed": 20261021}


def build(ctx, rendering):
    wire = json.load(open(os.path.join(R, "transport/calls", ctx, "wire_request.json")))["payload"]
    assert wire["model"] == MODEL and all(wire[k] == v for k, v in PARAMS.items()), "params drift"
    msgs = json.loads(json.dumps(wire["messages"]))
    user = msgs[-1]["content"]
    assert user.count(OLD) == 2 and user.count('"output": null') == 2, ctx
    if rendering == "treatment":
        msgs[-1]["content"] = user.replace(OLD, NEW)
        assert '"output": null' not in msgs[-1]["content"]
        assert msgs[-1]["content"].count('"execution_status": "exception"') == 2
    return {"model": MODEL, "messages": msgs, **PARAMS}


RAISE = re.compile(r"valueerror|raise|exception")
NEGATED_RAISE = re.compile(r"\b(not|never|no longer|without)\b[^.]*\b(raise|valueerror|exception)")
NONE_RETURN = re.compile(r"(?<!not )(?<!never )\breturns? none\b|^\s*none\s*\.?\s*$")


def strip_fences(text):
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    return t


def score(text):
    try:
        reply = json.loads(strip_fences(text))
    except (json.JSONDecodeError, TypeError, AttributeError):
        return {"state": "invalid"}
    if not isinstance(reply, dict) or not isinstance(reply.get("claims"), list) or not isinstance(
            reply.get("queries", []), list):
        return {"state": "invalid"}
    claims = [c for c in reply["claims"] if isinstance(c, dict)]
    stmt = lambda c: str(c.get("statement", "")).lower()
    affirm = [c for c in claims if RAISE.search(stmt(c)) and not NEGATED_RAISE.search(stmt(c))]
    negated = [c for c in claims if NEGATED_RAISE.search(stmt(c))]
    live = ("candidate", "keep", "revise")
    retained = (any(c.get("stance") in live for c in affirm) and not any(c.get("stance") == "withdraw" for c in affirm)
                and not any(c.get("stance") in live for c in negated))
    preds = [str(q.get("prediction", "")) for q in reply.get("queries", []) or []
             if isinstance(q, dict) and isinstance(q.get("action"), dict) and q["action"].get("tool") == "replay_input"]
    none_pred = any(NONE_RETURN.search(p.lower()) for p in preds)
    return {"state": "correct" if retained and not none_pred else "wrong", "retained": retained,
            "none_pred": none_pred, "claims": [(c.get("stance"), c.get("statement")) for c in claims],
            "predictions": preds}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect)


def call(payload):
    url = os.environ["QWEN_BASE_URL"].rstrip("/") + "/chat/completions"
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST", headers={
        "Content-Type": "application/json", "ngrok-skip-browser-warning": "1"})
    with OPENER.open(req, timeout=180) as resp:
        return json.load(resp)


def main():
    dry = "--dry-run" in sys.argv
    if not dry and not os.environ.get("QWEN_BASE_URL"):
        sys.exit("QWEN_BASE_URL not set; no slot consumed")
    out_dir = os.path.join(HERE, "responses")
    os.makedirs(out_dir, exist_ok=True)
    results = []
    for ctx in CONTEXTS:
        for rendering in ("control", "treatment"):
            payload = build(ctx, rendering)
            digest = hashlib.sha256(json.dumps(payload["messages"], sort_keys=True).encode()).hexdigest()
            rec = {"context": ctx, "rendering": rendering, "messages_sha256": digest}
            path = os.path.join(out_dir, f"{ctx}__{rendering}.json")
            if dry:
                rec["user_chars"] = len(payload["messages"][-1]["content"])
            elif os.path.exists(path):
                sys.exit(f"refusing to overwrite {path} (no retries)")
            else:
                t0 = time.time()
                try:
                    body = call(payload)
                    ch = body["choices"][0]
                    rec.update(text=ch["message"]["content"], finish_reason=ch.get("finish_reason"),
                               usage=body.get("usage"), model=body.get("model"), seconds=round(time.time() - t0, 1))
                except Exception as e:  # transport failure consumes the slot, never retried
                    rec.update(text=None, error=type(e).__name__)
                orig = json.load(open(os.path.join(R, "artifacts", ctx + ".json")))["raw"]["text"]
                rec["identical_to_original"] = rendering == "control" and rec.get("text") == orig
                json.dump(rec, open(path, "w"), indent=1, ensure_ascii=False)
                rec["score"] = score(rec.get("text")) if rec.get("text") is not None else {"state": "invalid"}
            results.append(rec)
            print(ctx, rendering, rec.get("score", {}).get("state", "dry"), rec.get("error", ""), flush=True)
    if not dry:
        json.dump(results, open(os.path.join(HERE, "results.json"), "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
