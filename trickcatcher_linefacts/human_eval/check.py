"""Check literal rater calls against frozen dev facts; PUT runs only in a sandboxed worker."""
import ast, json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def literal_call(text, entry):
    c = ast.parse(text, mode="eval").body
    if not isinstance(c, ast.Call) or not isinstance(c.func, ast.Name) or c.func.id != entry:
        raise ValueError(f"expected one literal Python call to {entry}")
    if any(k.arg is None for k in c.keywords):
        raise ValueError("**kwargs is not supported")
    return tuple(ast.literal_eval(x) for x in c.args), {k.arg: ast.literal_eval(k.value) for k in c.keywords}


def worker(item_id, text):
    sys.path.insert(0, str(HERE.parent))
    from tracer import HOOKS, call, fact_hit, instrument, load_module, trace
    from facts import make_mutant
    kit = json.loads((HERE / "items.json").read_text())
    item = next(x for x in kit["items"] if x["id"] == item_id)
    assert item["task"] not in set(kit["excluded"])
    args = literal_call(text, item["entry"])
    code, _ = instrument(item["put"])
    tr = trace(load_module(code, HOOKS)[item["entry"]], args)
    pout = call(load_module(item["put"])[item["entry"]], args)
    f = item["fact"]
    mout = call(load_module(make_mutant(item["put"], f["k"])[0])[item["entry"]], args) if f["kind"] == "MUTANT" else None
    print(json.dumps({"id": item_id, "task": item["task"], "reaches_fact": fact_hit(f, tr, pout, mout),
                      "put_status": pout[0], "trace_status": tr[2]}))


def main():
    if len(sys.argv) == 4 and sys.argv[1] == "worker":
        worker(sys.argv[2], sys.argv[3]); return
    if len(sys.argv) != 3:
        raise SystemExit("usage: python3 human_eval/check.py ITEM_ID 'function(literal_arguments)'")
    cmd = ["timeout", "-k", "5", "120", "unshare", "-rn", "python3", "-I", "-B", str(Path(__file__).resolve()),
           "worker", sys.argv[1], sys.argv[2]]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout.strip() if res.returncode == 0 else json.dumps({"error": res.stderr[-1000:] or f"worker exit {res.returncode}"}))
    raise SystemExit(res.returncode)


if __name__ == "__main__":
    main()
