"""Concept-binding ablation on frozen E4 T2 contexts (see PREREG.md). Reuses the OBS-null probe scorer/transport.

Usage: QWEN_BASE_URL=... python3 -I run.py [--dry-run]
"""
import hashlib, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "../obs_null_probe_20261021"))
from run import MODEL, PARAMS, R, call, score  # noqa: E402

CONTEXTS = ["E4__concept_adaptive__2", "E4__concept_committed__2"]
PACKET = ("concept", "concept_binding", "abstract_gap")
ARMS = ("control", "no_allowed_outcome", "no_packet")


def build(ctx, arm):
    wire = json.load(open(os.path.join(R, "transport/calls", ctx, "wire_request.json")))["payload"]
    assert wire["model"] == MODEL and all(wire[k] == v for k, v in PARAMS.items()), "params drift"
    msgs = json.loads(json.dumps(wire["messages"]))
    content = msgs[-1]["content"]
    user = json.loads(content)
    assert json.dumps(user, ensure_ascii=False) == content, "serialization round-trip"
    c = user["context"]
    assert c["concept_binding"]["allowed_outcome"] == "return None" and all(k in c for k in PACKET)
    if arm == "control":
        assert msgs == wire["messages"]
        return {"model": MODEL, "messages": msgs, **PARAMS}
    if arm == "no_allowed_outcome":
        del c["concept_binding"]["allowed_outcome"]
    elif arm == "no_packet":
        for k in PACKET:
            del c[k]
    else:
        raise ValueError(arm)
    msgs[-1]["content"] = json.dumps(user, ensure_ascii=False)
    return {"model": MODEL, "messages": msgs, **PARAMS}


def main():
    dry = "--dry-run" in sys.argv
    if not dry and not os.environ.get("QWEN_BASE_URL"):
        sys.exit("QWEN_BASE_URL not set; no slot consumed")
    out_dir = os.path.join(HERE, "responses")
    os.makedirs(out_dir, exist_ok=True)
    paths = [os.path.join(out_dir, f"{c}__{a}.json") for c in CONTEXTS for a in ARMS]
    if not dry and any(os.path.exists(p) for p in paths):
        sys.exit("responses already exist; no retries")
    results = []
    for ctx in CONTEXTS:
        for arm in ARMS:
            payload = build(ctx, arm)
            rec = {"context": ctx, "arm": arm, "messages_sha256": hashlib.sha256(
                json.dumps(payload["messages"], sort_keys=True).encode()).hexdigest()}
            path = os.path.join(out_dir, f"{ctx}__{arm}.json")
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
                if arm == "control":
                    rec["identical_to_original"] = rec.get("text") == orig
                json.dump(rec, open(path, "w"), indent=1, ensure_ascii=False)
                rec["score"] = score(rec["text"].replace("`", "")) if rec.get("text") is not None else {"state": "invalid"}
            results.append(rec)
            print(ctx, arm, rec.get("score", {}).get("state", "dry"), rec.get("user_chars", ""), rec.get("error", ""),
                  flush=True)
    if not dry:
        json.dump(results, open(os.path.join(HERE, "results.json"), "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
