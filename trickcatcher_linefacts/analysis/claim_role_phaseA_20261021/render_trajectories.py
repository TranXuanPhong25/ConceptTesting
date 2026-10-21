import json, sys, os
R = sys.argv[1]; ep = sys.argv[2]
arms = ["concept_adaptive", "generic_adaptive", "concept_committed"]
def j(p): return json.load(open(os.path.join(R, p)))
req = j(f"requests/{ep}__concept_adaptive__1.json")
ctx = json.loads(req[-1]["content"])["context"]
print(f"## {ep} sig={ctx['signature']}\nSPEC: {ctx['spec']}\nCODE: {' '.join(l.strip() for l in ctx['code'].splitlines() if l.strip())}\nH0: {ctx['initial_hypothesis']}")
print("BINDING:", json.dumps(ctx.get("concept_binding")))
for o in ctx["initial_observations"]:
    print(f"  {o['observation_id']}: {o['input']} -> {o['execution_status']} {o.get('exception_type')} {o['output']}")
for arm in arms:
    print(f"\n### {ep} {arm}")
    for t in (1, 2, 3):
        a = j(f"artifacts/{ep}__{arm}__{t}.json"); e = j(f"events/{ep}__{arm}__{t}.json")
        p = a.get("parsed") or {}
        print(f"-- T{t} state={a.get('state')} reply_state={e.get('reply_state')} err={e.get('reply_error')}")
        if not p:
            print("RAW:", a["raw"]["text"][:1500])
        for c in p.get("claims", []):
            print(f"  CLAIM {c.get('id')} [{c.get('kind')}/{c.get('stance')}] {c.get('statement')} ev={c.get('evidence')}")
        for q in p.get("queries", []) + [dict(x, _later=1) for x in p.get("later_queries", []) or []]:
            act = q.get("action", {})
            tgt = act.get("input") or act.get("ids") or act.get("names")
            print(f"  Q{'(later)' if q.get('_later') else ''} {act.get('tool')} {tgt} claim={q.get('claim')} pred={q.get('prediction')!r} why={q.get('why')!r}")
        if p.get("final_inputs"): print("  FINAL:", p["final_inputs"])
        for f in e.get("feedback") or []:
            out = f.get("output")
            if f.get("tool") not in (None, "replay_input"): out = json.dumps({k: f.get(k) for k in ("snapshots","reach","lines","flow","data") if f.get(k)})[:200]
            print(f"  OBS {f.get('observation_id')} {f.get('tool')} {f.get('input','')} status={f.get('status')} exec={f.get('execution_status')} exc={f.get('exception_type')} out={out} refusal={f.get('refusal') or f.get('error')}")
