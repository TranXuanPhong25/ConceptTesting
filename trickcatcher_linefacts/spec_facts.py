"""v7: specification-level input-class facts (tool-only, no LLM) for tasks without code facts.

A fact says that the existing tests never pass a value of some input class that the mined (B5) preconditions allow.
Classes were derived only from the even-numbered dev tasks among the Codex-only finds (out/codex_nofacts: 8, 16, 26, 46,
66, 86, 130); odd tasks are held out.
  LARGE     a container/string with >= 1000 items or an int >= 1000
  DUP       a list containing a repeated element
  NONASCII  a string (or list of strings) containing non-ASCII letters
  SPACE     a string with leading, trailing or repeated spaces (only when base strings contain spaces)
A witness is built from a base-test input by a fixed transformation and kept only if the B5 validator accepts it.

  python3 -B trickcatcher_linefacts/spec_facts.py build      # out/spec_facts_v7/<n>.json, out/tasks_v7*.json
  python3 -B trickcatcher_linefacts/spec_facts.py offline    # out/offline_v7/report.txt (HumanEval+ labels, dev only)
"""
import argparse, ast, json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
OUT = HERE / "out/spec_facts_v7"
PRIORITY = ("LARGE", "DUP", "NONASCII", "SPACE")
N_LARGE = 1000
ACCENT = str.maketrans("aeiouAEIOUcnsy", "áéíóúÁÉÍÓÚçñšý")


def in_class(cls, v):
    """True if value v belongs to the class (used for base coverage, witnesses and hits)."""
    if cls == "LARGE":
        if isinstance(v, bool):
            return False
        if isinstance(v, int):
            return v >= N_LARGE
        return isinstance(v, (list, tuple, str, dict)) and len(v) >= N_LARGE
    if cls == "DUP":
        if not isinstance(v, (list, tuple)):
            return False
        try:
            return len(set(map(repr, v))) < len(v)
        except Exception:
            return False
    if cls == "NONASCII":
        if isinstance(v, str):
            return any(ord(c) > 127 for c in v)
        return isinstance(v, (list, tuple)) and any(isinstance(x, str) and any(ord(c) > 127 for c in x) for x in v)
    if cls == "SPACE":
        return isinstance(v, str) and (v[:1] == " " or v[-1:] == " " or "  " in v)
    return False


def applies(cls, values):
    """The class is meaningful for a parameter given its base values."""
    vals = [v for v in values if v is not None]
    if not vals:
        return False
    if cls == "LARGE":
        return all(isinstance(v, (list, tuple, str)) or (isinstance(v, int) and not isinstance(v, bool)) for v in vals)
    if cls == "DUP":
        return all(isinstance(v, (list, tuple)) for v in vals)
    if cls == "NONASCII":
        return all(isinstance(v, str) for v in vals) or all(isinstance(v, (list, tuple)) and v and all(isinstance(x, str) for x in v) for v in vals)
    if cls == "SPACE":
        return all(isinstance(v, str) for v in vals) and any(" " in v.strip() for v in vals)
    return False


def transforms(cls, v):
    if cls == "LARGE":
        if isinstance(v, int):
            return [1500, 1000, 2000, 10 ** 6]
        if v:
            reps = -(-1500 // len(v))
            return [type(v)(v * reps)[:1500] if not isinstance(v, tuple) else tuple((list(v) * reps)[:1500])]
        return []
    if cls == "DUP":
        return [type(v)(list(v) + list(v[:1])), type(v)(list(v[:1]) * 2 + list(v[1:]))] if v else []
    if cls == "NONASCII":
        if isinstance(v, str):
            return [v.translate(ACCENT), v + "é", "é" + v]
        return [type(v)([x.translate(ACCENT) for x in v]), type(v)([v[0] + "é"] + list(v[1:]))]
    if cls == "SPACE":
        return [v.replace(" ", "  ", 1), " " + v, v + " "]
    return []


def text(cls, name, covered, extra=""):
    what = {"LARGE": f"`{name}` of size or value 1000 or more" + extra,
            "DUP": f"`{name}` containing a repeated element",
            "NONASCII": f"`{name}` containing non-ASCII letters (for example accented letters)",
            "SPACE": f"`{name}` with leading, trailing or repeated spaces"}[cls]
    if covered:
        return f"Input-domain class (specification): the existing tests already pass {what}."
    return (f"Input-domain class (specification): no existing test passes {what}; "
            "the specification's input requirements allow it.")


def worker(job_path, out_path):
    import copy, signal
    job = json.loads(Path(job_path).read_text())

    class TO(Exception):
        pass

    def alarm(*_):
        raise TO()

    signal.signal(signal.SIGALRM, alarm)
    ns = {}
    exec(job["valid_src"], ns)
    valid = ns["valid"]

    def ok(args):
        signal.alarm(2)
        try:
            return valid(*copy.deepcopy(args)) is True
        except BaseException:
            return False
        finally:
            signal.alarm(0)

    base, params = [tuple(b) for b in job["base"]], job["params"]
    facts, placebo = [], []
    for cls in PRIORITY:
        for i, name in enumerate(params):
            vals = [b[i] for b in base if len(b) == len(params)]
            if not applies(cls, vals):
                continue
            covered = any(in_class(cls, v) for v in vals)
            extra = ""
            if cls == "LARGE":
                ints = [v for v in vals if isinstance(v, int)]
                big = max((v if isinstance(v, int) else len(v)) for v in vals)
                extra = f" (the largest in the existing tests is {big})"
            if covered:
                placebo.append(dict(kind="SPEC", input_class=dict(cls=cls, param=i), text=text(cls, name, True)))
                continue
            witness = None
            for b in sorted((b for b in base if len(b) == len(params)), key=lambda b: -len(repr(b[i]))):
                for nv in transforms(cls, b[i]):
                    args = list(b); args[i] = nv
                    if in_class(cls, nv) and ok(args):
                        witness = args; break
                if witness:
                    break
            if witness is None:
                continue
            literal = repr(tuple(witness))
            call = job["entry"] + "(" + ", ".join(repr(a) for a in witness) + ")"
            facts.append(dict(kind="SPEC", input_class=dict(cls=cls, param=i), text=text(cls, name, False, extra),
                              witness=0, reached=True, witness_args=witness,
                              witness_call=call if len(literal) <= 1000 else None))
    Path(out_path).write_text(json.dumps(dict(facts=facts, placebo=placebo)))


def base_args(src):
    out = []
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "candidate" and not node.keywords:
            try:
                out.append([ast.literal_eval(a) for a in node.args])
            except Exception:
                pass
    return out


def build():
    from trickcatcher_linefacts import preconditions
    OUT.mkdir(parents=True, exist_ok=True)
    for name in ("tasks_v6_all.json", "tasks_v6hyb_v4.json"):
        b = json.loads((HERE / "out" / name).read_text())
        for t in b["tasks"]:
            n = t["task"]; res = OUT / f"{n}.json"
            if not res.exists():
                spec, _, params = preconditions.specification(t)
                names = [a.arg for a in params.posonlyargs + params.args]
                job = dict(entry=t["entry"], base=base_args(t["base"]), params=names, valid_src=t["mined_valid_src"])
                jp = OUT / f"{n}.job.json"; jp.write_text(json.dumps(job, default=repr))
                subprocess.run(["timeout", "600", "unshare", "-rn", sys.executable, "-I", "-B", str(Path(__file__)), "worker",
                                str(jp), str(res)], check=False, capture_output=True)
            r = json.loads(res.read_text()) if res.exists() else dict(facts=[], placebo=[])
            if not t["concept_facts"] and r["facts"]:
                top = r["facts"][:3]
                t.update(concept_meta=top, concept_facts=[f["text"] for f in top],
                         placebo_meta=r["placebo"][:3], placebo_facts=[f["text"] for f in r["placebo"][:3]],
                         tool_inputs=[f["witness_call"] for f in top if f["witness_call"]], spec_facts=True)
        b["note"] = b.get("note", "") + " | v7: + specification input-class facts (spec_facts.py) for tasks without code facts"
        out = HERE / "out" / name.replace("v6", "v7")
        out.write_text(json.dumps(b))
        dev = [t for t in b["tasks"] if t["split"] == "dev"]
        print(f"{out.name}: dev tasks with facts {sum(bool(t['concept_facts']) for t in dev)}/{len(dev)}, "
              f"with spec facts {sum(bool(t.get('spec_facts')) for t in dev)}")


def offline():
    """PF of each shown spec fact on HumanEval+ inputs (dev only): failing / all inputs in the class."""
    from trickcatcher_linefacts import oracle_b01 as ob
    b = {t["task"]: t for t in json.loads((HERE / "out/tasks_v7_all.json").read_text())["tasks"]}
    hep = {int(r["task_id"].split("/")[1]): r for r in map(json.loads, open(ob.HEP))}
    d = HERE / "out/offline_v7"; d.mkdir(parents=True, exist_ok=True)
    lines = []
    for n, t in sorted(b.items()):
        if t["split"] != "dev" or not t.get("spec_facts"):
            continue
        h = hep[n]
        job = dict(entry=h["entry_point"], put=t["put"], canon=h["prompt"] + h["canonical_solution"],
                   inputs=h["base_input"] + h["plus_input"], facts=[f["input_class"] for f in t["concept_meta"]], atol=h["atol"])
        jp = d / f"{n}.job.json"; rp = d / f"{n}.json"; jp.write_text(json.dumps(job, default=repr))
        if not rp.exists():
            subprocess.run(["timeout", "900", "unshare", "-rn", sys.executable, "-I", "-B", str(Path(__file__)), "offline-worker",
                            str(jp), str(rp)], check=False, capture_output=True)
        r = json.loads(rp.read_text()) if rp.exists() else None
        lines.append(dict(task=n, facts=[f["text"][:90] for f in t["concept_meta"]], pf=r))
    strong = [x["task"] for x in lines if x["pf"] and any(f and f[1] and f[0] / f[1] >= .5 for f in x["pf"])]
    rep = [f"v7 spec facts, dev tasks with spec facts: {len(lines)}; tasks with a strong shown fact (PF >= .5): {len(strong)} {strong}",
           f"  even (derivation): {sum(1 for x in strong if x % 2 == 0)}/{sum(1 for x in lines if x['task'] % 2 == 0)}   "
           f"odd (held-out): {sum(1 for x in strong if x % 2)}/{sum(1 for x in lines if x['task'] % 2)}"]
    for x in lines:
        rep.append(f"  {x['task']}: " + " | ".join(f"{t[:60]} PF {p[0]}/{p[1]}" if p else f"{t[:60]} -" for t, p in zip(x["facts"], x["pf"] or [None] * 3)))
    (d / "report.txt").write_text("\n".join(rep) + "\n"); print("\n".join(rep))


def offline_worker(job_path, out_path):
    import copy, math, signal
    job = json.loads(Path(job_path).read_text())

    class TO(Exception):
        pass

    def alarm(*_):
        raise TO()

    signal.signal(signal.SIGALRM, alarm)

    def load(src):
        ns = {}; exec("from typing import *\nimport math\n" + src, ns); return ns[job["entry"]]

    put, can = load(job["put"]), load(job["canon"])

    def run(f, a):
        signal.alarm(2)
        try:
            return "ok", f(*copy.deepcopy(a))
        except TO:
            return "timeout", None
        except BaseException as e:
            return type(e).__name__, None
        finally:
            signal.alarm(0)

    def same(x, y):
        if isinstance(x, float) and isinstance(y, float):
            return math.isclose(x, y, rel_tol=1e-6, abs_tol=job["atol"] or 1e-9)
        return x == y

    res = []
    for f in job["facts"]:
        n = fail = 0
        for a in job["inputs"]:
            if f["param"] >= len(a) or not in_class(f["cls"], a[f["param"]]):
                continue
            cs, cv = run(can, a)
            if cs != "ok":
                continue
            n += 1
            ps, pv = run(put, a)
            fail += ps != "ok" or not same(cv, pv)
        res.append([fail, n])
    Path(out_path).write_text(json.dumps(res))


if __name__ == "__main__":
    if sys.argv[1:2] == ["worker"]:
        worker(*sys.argv[2:4]); sys.exit()
    if sys.argv[1:2] == ["offline-worker"]:
        offline_worker(*sys.argv[2:4]); sys.exit()
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("build", "offline"))
    a = ap.parse_args()
    build() if a.cmd == "build" else offline()
