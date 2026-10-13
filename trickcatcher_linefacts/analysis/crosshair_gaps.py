"""CrossHair (symbolic execution, Z3) on the v5 hard gaps. CPU only, no LLM, no endpoint.

Question: can CrossHair find witness inputs for the 276 facts that the base-input fuzz never reached (v5 step 2,
out/strategy_qwen7b_v5: Qwen-written Hypothesis strategies reached 10/276) better than those strategies?

Settings (fixed before any CrossHair result on the gap set was read; also in out/crosshair_gaps/settings.json):
- Gap set: every gap row of out/strategy_qwen7b_v5/<task>/summary.json (first 10 unreached facts per task, all 133
  tasks; 238 of them on DEV tasks, 38 on pilot; v5's 10/276 used the same rows). The raw fact dict is the target;
  cell ids refer to tracer.instrument(put). Kinds: BOUND 133, SHAPE 51, OUTCOME 35, NUM 30, STMT 14, REL 13, MUTANT 0.
- Tool: crosshair-tool 0.0.111 / z3-solver 5.1.0.0 in out/venvs/crosshair (Python 3.12), `crosshair check
  --analysis_kind asserts --report_all --per_condition_timeout 60` (CPU s; per-path timeout = CrossHair default,
  sqrt(60) s), one process per gap under `timeout -k 5 300 unshare -rn` (no network), 12 gaps in parallel.
- Harness per gap (generated file harness/<id>/harness.py, function `_target(<params>)`): the leading assert is the
  precondition = the B5 validator out/precond_qwen7b_v4/<task>/valid.py (restricted builtins as in
  preconditions.load_predicate; an exception counts as invalid). Then the PUT runs; reaching the target sets a flag and
  raises an internal BaseException, turned into `assert not reached`. Other PUT exceptions are swallowed (a crash is
  not a witness).
  * STMT: a copy of the PUT with a `_hit()` call inserted before each statement that starts on a target line.
  * cell facts (OUTCOME 'T'/'F', BOUND 'eqc'; extension: REL 'eqv'/'R', NUM/SHAPE 'P'): tracer.Inst instruments the
    PUT exactly as facts.py does (same site ids) with target-only hooks: every hook is a pass-through except at the
    target site, where the tracer's own cell rule is evaluated (branch outcome; `x == const + d` for the boundary
    probe; `x == y` for the relation probe; the shape/relation predicate of the arguments at function entry).
  * MUTANT: `crosshair diffbehavior` between PUT and mutant wrappers that return a constant on inputs failing the
    validator (precondition), --exception_equivalence SAME_TYPE. (There are 0 MUTANT gaps among the 276.)
  * Registered scope (caller): STMT/OUTCOME/BOUND/MUTANT; other kinds unsupported. NUM/SHAPE/REL use the same
    cell-hook harness and are run as a declared extension, reported in a separate table.
- Parameter types (CrossHair needs annotations): the union of types observed in the task's base-test inputs
  (recursively; empty containers take element types from other observations, else the PUT's own annotation, else int).
- Statuses: found (counterexample carrying REACHED), proven_unreachable (--report_all "Confirmed over all paths"),
  budget (not confirmed, no counterexample), error (other counterexample, bad exit, unparsable witness),
  hard_timeout (wall-clock kill), unsupported.
- Count rule: the witness is parsed from CrossHair's output into a literal, then in a sandboxed worker with the repo
  interpreter: tracer.trace + tracer.fact_hit on the raw fact, and the B5 validator (1 s alarm, `is True`). Counted
  only if both. The v2 validator (v5's rule) is reported alongside; the 10 Hypothesis witnesses are re-verified the
  same way.
- Measurement only: EvalPlus contract validity and PUT != HumanEval+ canonical (analysis/worker.py's rule) on every
  verified witness (CrossHair and Hypothesis).
- Positive control (declared before the run): in each of the first 20 tasks (by id) with gaps, the first REACHED fact
  of each registered kind, same harness and budget; plus a concrete harness-fidelity check (no CrossHair): each
  harness run on known witnesses (control fuzz witness, Hypothesis witness) must agree with the repo tracer.

Run (CPU only):
  python3 -B trickcatcher_linefacts/analysis/crosshair_gaps.py all
Outputs: out/crosshair_gaps/ (harness/<id>/, verify/, reveal/, summary.json, settings.json) and
analysis/crosshair_gaps_report.md.
"""
import argparse, ast, collections, copy, hashlib, json, os, re, signal, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

H = Path(__file__).resolve().parents[1]
OUT = H / "out/crosshair_gaps"
REPORT = H / "analysis/crosshair_gaps_report.md"
VPY = H / "out/venvs/crosshair/bin/python"
STRAT = H / "out/strategy_qwen7b_v5"
FACTS = H / "out/facts_v5"
TASKS = H / "out/tasks_v5_all.json"
V2 = H / "out/precond_qwen7b_v2"
V4 = H / "out/precond_qwen7b_v4"
SETTINGS = dict(budget_cpu_s=60, per_path_timeout="crosshair default (sqrt(budget) CPU s)", hard_wall_s=300,
                analysis_kind="asserts", workers=12, crosshair="crosshair-tool 0.0.111", z3="z3-solver 5.1.0.0",
                precondition="valid_v4 (out/precond_qwen7b_v4, B5)", types="base-observed union",
                diff_exceptions="SAME_TYPE", registered_kinds=["STMT", "OUTCOME", "BOUND", "MUTANT"],
                extension_kinds=["NUM", "SHAPE", "REL"], count_rule="tracer.fact_hit and valid_v4 is True",
                positive_control="first reached supported fact, first 20 tasks with gaps")
ENV = {"PATH": os.defpath, "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1"}


def sha(x):
    return hashlib.sha256(x.encode() if isinstance(x, str) else x).hexdigest()


# ---------------------------------------------------------------- gap set
def load_gaps():
    bundle = json.loads(TASKS.read_text())
    tasks = {t["task"]: t for t in bundle["tasks"]}
    gaps = []
    for n in sorted(tasks):
        p = STRAT / str(n) / "summary.json"
        if not p.exists():
            continue
        row = json.loads(p.read_text())
        fr = json.loads((FACTS / f"{n}.json").read_text())
        hf = fr["hypothesis_fallback"]
        if hf["gaps"] != len(row["gaps"]):
            raise ValueError(f"gap count mismatch for task {n}")
        for g in row["gaps"]:
            gaps.append(dict(id=f"{n}_{g['fact_index']}", task=n, split=tasks[n]["split"], fact_index=g["fact_index"],
                             fact=g["fact"], kind=g["fact"]["kind"], hyp_witness=g["witness"]))
    return tasks, gaps


def load_controls(tasks, gaps):
    """Positive control: in each of the first 20 tasks (by id) with gaps, the first REACHED fact of each registered
    kind (STMT, OUTCOME, BOUND); its fuzz witness is kept for the concrete harness check."""
    out = []
    for n in sorted({g["task"] for g in gaps})[:20]:
        fr = json.loads((FACTS / f"{n}.json").read_text())
        seen = set()
        for i, f in enumerate(fr["facts"]):
            w = f["witness"]
            # reached by the base-input fuzz itself (an index past fuzz_inputs is a v5 Hypothesis fallback witness)
            known = fr["fuzz_inputs"][w] if isinstance(w, int) and 0 <= w < len(fr["fuzz_inputs"]) else None
            if not f["reached"] or known is None or f["kind"] not in ("STMT", "OUTCOME", "BOUND") or f["kind"] in seen:
                continue
            seen.add(f["kind"])
            raw = {k: v for k, v in f.items() if k not in ('reached', 'witness_call', 'block', 'g_demote', 'tier',
                                                       'guard_line', 'guard_forced', 'guard_class', 'guard_counts')}
            out.append(dict(id=f"ctl_{n}_{i}", task=n, split=tasks[n]["split"], fact_index=i, fact=raw,
                            kind=f["kind"], hyp_witness=None, control=True, known_witness=known))
    return out


# ---------------------------------------------------------------- types from base inputs
def tnode(v):
    if v is None:
        return ("None",)
    if isinstance(v, bool):
        return ("bool",)
    if isinstance(v, int):
        return ("int",)
    if isinstance(v, float):
        return ("float",)
    if isinstance(v, str):
        return ("str",)
    if isinstance(v, list):
        return ("list", frozenset(tnode(x) for x in v))
    if isinstance(v, tuple):
        return ("tuple", tuple(tnode(x) for x in v))
    if isinstance(v, dict):
        return ("dict", frozenset(tnode(k) for k in v), frozenset(tnode(x) for x in v.values()))
    if isinstance(v, (set, frozenset)):
        return (type(v).__name__, frozenset(tnode(x) for x in v))
    raise ValueError(f"unsupported base value type {type(v).__name__}")


def merge(nodes):
    """Union of observed type nodes; containers of the same kind merge element sets."""
    by = collections.OrderedDict()
    for n in sorted(nodes, key=repr):
        k = n[0]
        if k in ("list", "set", "frozenset"):
            by[k] = (k, (by[k][1] if k in by else frozenset()) | n[1])
        elif k == "dict":
            a = by.get(k, (k, frozenset(), frozenset()))
            by[k] = (k, a[1] | n[1], a[2] | n[2])
        elif k == "tuple":
            by.setdefault(("tuple", len(n[1])), []).append(n)
        else:
            by[k] = n
    out = []
    for key, n in by.items():
        if isinstance(key, tuple):
            ln = key[1]
            out.append(("tuple", tuple(frozenset(x[1][i] for x in n) for i in range(ln))))
        else:
            out.append(n)
    return out


def render(nodes, fallback="int"):
    parts = []
    for n in merge(nodes):
        k = n[0]
        if k in ("None", "bool", "int", "float", "str"):
            parts.append(k)
        elif k in ("list", "set", "frozenset"):
            inner = render(n[1], fallback) if n[1] else fallback
            parts.append({"list": "List", "set": "Set", "frozenset": "FrozenSet"}[k] + f"[{inner}]")
        elif k == "dict":
            parts.append(f"Dict[{render(n[1], fallback) if n[1] else 'str'}, {render(n[2], fallback) if n[2] else fallback}]")
        elif k == "tuple":
            parts.append("Tuple[()]" if not n[1] else "Tuple[" + ", ".join(render(x, fallback) for x in n[1]) + "]")
    parts = list(dict.fromkeys(parts))
    return parts[0] if len(parts) == 1 else "Union[" + ", ".join(parts) + "]"


def element_fallback(ann):
    """Element type from the PUT's own annotation (List[X] -> X), else int."""
    m = re.match(r"^(?:typing\.)?(?:List|list|Set|set|Tuple|tuple)\[(.+)\]$", ann or "")
    return m.group(1).replace("...", "").strip(", ") if m else "int"


def annotations(task, params, fn):
    bases = [ast.literal_eval(b) for b in json.loads((FACTS / f"{task}.json").read_text())["base_inputs"]]
    anns = {}
    for i, p in enumerate(params):
        own = fn.args.args[i].annotation
        own = ast.unparse(own) if own is not None else None
        vals = [b[0][i] for b in bases if len(b[0]) > i]
        if not vals:
            if own is None:
                raise ValueError(f"no observed type for parameter {p}")
            anns[p] = own
            continue
        anns[p] = render({tnode(v) for v in vals}, element_fallback(own))
    return anns


# ---------------------------------------------------------------- harness generation (prepare stage; no PUT executes)
HOOKS_SRC = r'''
class _Reached(BaseException):  # BaseException: a PUT's `except Exception` must not swallow it
    pass

_FLAG = [False]

_LAST, _LASTVAL = {}, {}

def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)

def _numcls(x):
    if x != x:
        return "nan"
    if x in (math.inf, -math.inf):
        return "inf"
    if x == 0:
        return "zero"
    if x < 0:
        return "neg-small" if x >= -1000 else "neg-large"
    return "pos-small" if x <= 1000 else "pos-large"

def _absval(v):
    t = type(v)
    if v is None:
        return "None"
    if t is bool:
        return "bool:" + str(v)
    if t is int:
        return "int:" + _numcls(v)
    if t is float:
        return "float:" + _numcls(v)
    if t is str:
        return "str:empty" if not v else ("str:alpha" if v.isalpha() else "str:nonalpha")
    if t in (list, tuple, dict, set, frozenset):
        return t.__name__ + (":empty" if len(v) == 0 else ":nonempty")
    return None

def _pred(v, lab):
    """tracer.shape_preds restricted to one label: the label's truth value, or None if not produced."""
    if isinstance(v, (list, tuple)):
        if lab == "len1":
            return len(v) == 1
        if lab in ("dup", "asc", "desc"):
            if len(v) < 2:
                return None
            try:
                if lab == "dup":
                    return len(set(v)) < len(v)
                if lab == "asc":
                    return all(a <= b for a, b in zip(v, v[1:]))
                return all(a >= b for a, b in zip(v, v[1:]))
            except TypeError:
                return None
        if lab in ("hasneg", "haszero"):
            if v and all(_num(x) for x in v):
                return any(x < 0 for x in v) if lab == "hasneg" else any(x == 0 for x in v)
        return None
    if isinstance(v, str):
        if lab == "len1": return len(v) == 1
        if lab == "upper": return any(c.isupper() for c in v)
        if lab == "lower": return any(c.islower() for c in v)
        if lab == "digit": return any(c.isdigit() for c in v)
        if lab == "dblspace": return "  " in v
        if lab == "edgespace": return v[:1] == " " or v[-1:] == " "
        if lab == "punct": return any(not c.isalnum() and not c.isspace() for c in v)
        return None
    if _num(v):
        if lab == "neg": return v < 0
        if lab == "zero": return v == 0
        if lab == "odd": return v % 2 == 1 if isinstance(v, int) else None
        if lab == "nonint":
            return v != int(v) if isinstance(v, float) and math.isfinite(v) else None
    return None

def _rel_preds(vals):
    out = []
    for i in range(len(vals)):
        for j in range(len(vals)):
            if i == j:
                continue
            a, b = vals[i], vals[j]
            if i < j and type(a) is type(b) and isinstance(a, (int, float, list, tuple, str)):
                out.append((f"{i}|{j}|eq", a == b))
                try:
                    out.append((f"{i}|{j}|gt", a > b))
                except TypeError:
                    pass
                if isinstance(a, (list, tuple, str)):
                    out.append((f"{i}|{j}|prefix", b[:len(a)] == a))
            if isinstance(a, int) and not isinstance(a, bool) and isinstance(b, (list, tuple, str)):
                out.append((f"{i}|{j}|eqlen", a == len(b)))
                out.append((f"{i}|{j}|gtlen", a > len(b)))
            if i < j and isinstance(a, (list, tuple, str)) and isinstance(b, (list, tuple, str)):
                out.append((f"{i}|{j}|samelen", len(a) == len(b)))
    return out

def __v(sid, v):
    if sid in _NEED:
        _LASTVAL[sid] = v
        if _NEED_CLASS:
            c = _absval(v)
            if c is not None:
                _LAST[sid] = c
    return v

def _reach():
    _FLAG[0] = True
    raise _Reached()

def __c(sid, v):
    if sid == _T[1]:
        o = bool(v)
        k = _T[0]
        if k == "outcome" and o == _T[2]:
            _reach()
        if k == "eqc":
            x = _LASTVAL.get(_T[2], None)
            if _num(x) and (x == _T[3] + _T[4]) == _T[5]:
                _reach()
        if k == "eqv":
            x, y = _LASTVAL.get(_T[2], None), _LASTVAL.get(_T[3], None)
            if x is not None and y is not None and (type(x) is type(y) or (_num(x) and _num(y))):
                try:
                    hit = bool(x == y) == _T[4]
                except Exception:
                    hit = False
                if hit:
                    _reach()
        if k == "member":
            c = _LAST.get(_T[3], None)
            if o == _T[2] and c is not None and c == _T[4]:
                _reach()
    for m in _MEMBERS.get(sid, ()):
        _LAST.pop(m, None)
        _LASTVAL.pop(m, None)
    return v

def __p(fsid, names, *vals):
    if fsid != _T[1]:
        return
    if _T[0] == "P":
        i, lab, want = _T[2], _T[3], _T[4]
        if i < len(vals):
            r = _pred(vals[i], lab)
            if r is not None and r == want:
                _reach()
    elif _T[0] == "R":
        for lab, t in _rel_preds(vals):
            if lab == _T[2] and t == _T[3]:
                _reach()

class _NoLoop:
    def __enter__(self):
        return None
    def __exit__(self, *a):
        return False

def __loop(sid):
    return _NoLoop()

def __tick(count):
    pass

def __it(sid, it):
    return it

def __d(scope, names, line, fresh=False):
    pass

def __u(scope, name, line, kind, v):
    return v

def __named(scope, name, line, v):
    return v

def __del(scope, names):
    pass

def _hit():
    _reach()
'''


def cell_target(fact, sites, members, probes):
    sid, lab = fact["cell"]
    if not (0 <= sid < len(sites)):
        raise ValueError("cell site out of range")
    kind = sites[sid]["kind"]
    if kind in ("cond", "subcond") and lab in ("T", "F"):
        return ("outcome", sid, lab == "T"), set(), False
    parts = lab.split("|")
    if kind in ("cond", "subcond") and parts[0] == "eqc":
        x, c, d, want = int(parts[1]), parts[2], int(parts[3]), parts[4] == "True"
        consts = [p[2] for p in probes.get(sid, []) if p[0] == "eqc" and p[1] == x and str(p[2]) == c]
        if not consts:
            raise ValueError("eqc probe not found")
        return ("eqc", sid, x, consts[0], d, want), {x}, False
    if kind in ("cond", "subcond") and parts[0] == "eqv":
        a, b, want = int(parts[1]), int(parts[2]), parts[3] == "True"
        return ("eqv", sid, a, b, want), {a, b}, False
    if kind in ("cond", "subcond") and parts[0] in ("T", "F") and len(parts) == 3:
        return ("member", sid, parts[0] == "T", int(parts[1]), parts[2]), {int(parts[1])}, True
    if kind == "entry" and parts[0] == "P":
        return ("P", sid, int(parts[1]), parts[2], parts[3] == "True"), set(), False
    if kind == "entry" and parts[0] == "R":
        return ("R", sid, "|".join(parts[1:-1]), parts[-1] == "True"), set(), False
    raise ValueError(f"unsupported cell {kind}:{lab}")


class Marker(ast.NodeTransformer):
    def __init__(self, lines):
        self.lines, self.done = set(lines), set()

    def generic_visit(self, node):
        super().generic_visit(node)
        for field in ("body", "orelse", "finalbody", "handlers"):
            lst = getattr(node, field, None)
            if isinstance(lst, list) and lst and all(isinstance(s, ast.stmt) for s in lst):
                out = []
                for s in lst:
                    if s.lineno in self.lines:
                        self.done.add(s.lineno)
                        out.append(ast.Expr(ast.Call(ast.Name("_hit", ast.Load()), [], [])))
                    out.append(s)
                setattr(node, field, out)
        return node


def entry_fn(put, entry):
    fn = next(n for n in ast.parse(put).body if isinstance(n, ast.FunctionDef) and n.name == entry)
    a = fn.args
    if a.vararg or a.kwarg or a.kwonlyargs or a.posonlyargs:
        raise ValueError("variable/keyword-only arity is unsupported")
    return fn, [x.arg for x in a.args]


def harness(gap, task):
    """Returns (mode, harness source). Raises ValueError for unsupported gaps."""
    sys.path.insert(0, str(H))
    from tracer import Inst  # AST only; the PUT is not executed here
    from preconditions import SAFE_BUILTINS
    put, entry = task["put"], task["entry"]
    fn, params = entry_fn(put, entry)
    anns = annotations(gap["task"], params, fn)
    v2 = (V2 / str(gap["task"]) / "valid.py").read_text()
    v4 = (V4 / str(gap["task"]) / "valid.py").read_text()
    if v2 != task["mined_valid_src"]:
        raise RuntimeError("v2 validator differs from the bundle")
    f = gap["fact"]
    head = ["import builtins, copy, math", "from typing import *", "", HOOKS_SRC,
            f"_SAFE = {{n: getattr(builtins, n) for n in {tuple(SAFE_BUILTINS)!r}}}",
            "def _load_valid(src):",
            "    ns = {'__builtins__': dict(_SAFE)}",
            "    exec(compile(src, '<mined>', 'exec'), ns)",
            "    return ns['valid']",
            f"_VALID4 = _load_valid({v4!r})",
            "def _ok(v, args):",
            "    try:",
            "        return v(*args) is True",
            "    except Exception:",
            "        return False", ""]
    sig = ", ".join(f"{p}: {anns[p]}" for p in params)
    names = ", ".join(params) + ("," if len(params) == 1 else "")
    if f["kind"] == "MUTANT":
        import facts as F
        msrc = f.get("mutant_src") or F.make_mutant(put, f["k"])[0]
        body = head + [f"_NEED, _NEED_CLASS, _MEMBERS, _T = set(), False, {{}}, ('none', -99)",
                       "_PNS, _MNS = {'__name__': '__put__'}, {'__name__': '__put__'}",
                       f"exec(compile({put!r}, '<put>', 'exec'), _PNS)",
                       f"exec(compile({msrc!r}, '<mut>', 'exec'), _MNS)", "",
                       f"def put_w({sig}):",
                       f"    a = ({names})",
                       "    if not _ok(_VALID4, a):",
                       "        return '__invalid__'",
                       f"    return _PNS[{entry!r}](*a)", "",
                       f"def mut_w({sig}):",
                       f"    a = ({names})",
                       "    if not _ok(_VALID4, a):",
                       "        return '__invalid__'",
                       f"    return _MNS[{entry!r}](*a)", ""]
        return "diff", "\n".join(body), anns
    if f["kind"] == "STMT":
        tree = ast.parse(put)
        mk = Marker(f["lines"])
        tree = mk.visit(tree)
        if not mk.done:
            raise ValueError("no statement starts on the target line(s)")
        ast.fix_missing_locations(tree)
        src = ast.unparse(tree)
        spec = "_NEED, _NEED_CLASS, _MEMBERS, _T = set(), False, {}, ('stmt', -99)"
    elif "cell" in f and f["kind"] in ("OUTCOME", "BOUND", "REL", "NUM", "SHAPE"):
        ins = Inst()
        tree = ins.visit(ast.parse(put))
        ast.fix_missing_locations(tree)
        src = ast.unparse(tree)
        t, need, need_class = cell_target(f, ins.sites, ins.members, ins.probes)
        members = {k: tuple(v) for k, v in ins.members.items()}
        spec = f"_NEED, _NEED_CLASS, _MEMBERS, _T = {need!r}, {need_class!r}, {members!r}, {t!r}"
        if not need:
            spec = spec.replace("set(), ", "set(), ", 1)
    else:
        raise ValueError(f"unsupported kind {f['kind']}")
    body = head + [spec,
                   "_PNS = {'__name__': '__put__'}",
                   "_PNS.update({k: globals()[k] for k in ('__v', '__c', '__p', '__loop', '__tick', '__it', '__d',"
                   " '__u', '__named', '__del', '_hit')})",
                   f"exec(compile({src!r}, '<put>', 'exec'), _PNS)", "",
                   "def _probe(*a):",
                   "    _LAST.clear(); _LASTVAL.clear(); _FLAG[0] = False",
                   "    try:",
                   f"        _PNS[{entry!r}](*a)",
                   "    except _Reached:",
                   "        return True",
                   "    except Exception:",
                   "        pass",
                   "    return _FLAG[0]", "",
                   f"def _target({sig}) -> None:",
                   f"    assert _ok(_VALID4, ({names}))",
                   f"    reached = _probe({', '.join(params)})",
                   "    assert not reached, 'REACHED'", ""]
    return "check", "\n".join(body), anns


def prepare(items):
    tasks = json.loads(TASKS.read_text())["tasks"]
    tasks = {t["task"]: t for t in tasks}
    rows = []
    for g in items:
        d = OUT / "harness" / g["id"]
        d.mkdir(parents=True, exist_ok=True)
        try:
            mode, src, anns = harness(g, tasks[g["task"]])
            (d / "harness.py").write_text(src)
            rows.append(dict(id=g["id"], mode=mode, annotations=anns, harness_sha256=sha(src)))
        except (ValueError, StopIteration) as exc:
            rows.append(dict(id=g["id"], mode="unsupported", reason=f"{type(exc).__name__}: {exc}"))
    return rows


# ---------------------------------------------------------------- CrossHair runs
def run_one(g, prep):
    d = OUT / "harness" / g["id"]
    res = d / "result.json"
    if res.exists():
        old = json.loads(res.read_text())
        if old.get("harness_sha256") == prep.get("harness_sha256") and old.get("settings") == SETTINGS:
            old.update(classify(prep["mode"], old["returncode"], old["stdout"], old["stderr"]))
            return old
    if prep["mode"] == "unsupported":
        return dict(id=g["id"], status="unsupported", reason=prep["reason"])
    b = SETTINGS["budget_cpu_s"]
    common = ["--per_condition_timeout", str(b)]
    if prep["mode"] == "check":
        cmd = [str(VPY), "-m", "crosshair", "check", "--analysis_kind", "asserts", "--report_all"] + common + [
            str(d / "harness.py")]
    else:
        cmd = [str(VPY), "-m", "crosshair", "diffbehavior", "--exception_equivalence", "SAME_TYPE"] + common + [
            "harness.put_w", "harness.mut_w"]
    full = ["timeout", "-k", "5", str(SETTINGS["hard_wall_s"]), "unshare", "-rn"] + cmd
    t0 = time.time()
    with open(d / "stdout.txt", "w") as fo, open(d / "stderr.txt", "w") as fe:
        p = subprocess.Popen(full, cwd=d, env=dict(ENV, PYTHONPATH=str(d)), stdout=fo, stderr=fe,
                             start_new_session=True)
        _, status, ru = os.wait4(p.pid, 0)  # rusage of the whole subtree (timeout -> unshare -> crosshair)
        p.returncode = os.waitstatus_to_exitcode(status)
    wall = time.time() - t0
    out, err = (d / "stdout.txt").read_text(errors="replace"), (d / "stderr.txt").read_text(errors="replace")
    row = dict(id=g["id"], mode=prep["mode"], returncode=p.returncode, wall_s=round(wall, 2),
               cpu_s=round(ru.ru_utime + ru.ru_stime, 2), maxrss_mb=round(ru.ru_maxrss / 1024),
               stdout=out[-20000:], stderr=err[-4000:], harness_sha256=prep["harness_sha256"], settings=SETTINGS)
    row.update(classify(prep["mode"], p.returncode, out, err))
    res.write_text(json.dumps(row, indent=1))
    return row


def classify(mode, rc, out, err):
    if rc in (124, 137, -9):
        return dict(status="hard_timeout")
    if mode == "check":
        hits = [ln for ln in out.splitlines() if ": error: " in ln and "REACHED" in ln and "when calling" in ln]
        if hits:
            return dict(status="found", call=hits[0].split("when calling ", 1)[1].strip())
        if rc == 1:
            internal = "CrossHairInternal" in out + err
            return dict(status="error", reason="CrossHair internal error" if internal else "other counterexample")
        if rc == 0 and "Confirmed over all paths" in out:
            return dict(status="proven_unreachable")
        if rc == 0:
            return dict(status="budget")
        return dict(status="error", reason=f"exit {rc}")
    # diffbehavior: exit 1 with "Given: (...)" lines on a difference, 0 when none found.
    if rc == 1 and "Given:" in out:
        m = re.search(r"Given: \((.*)\),\n", out)
        return dict(status="found", call="put_w(" + (m.group(1) if m else "") + ")")
    if rc == 0:
        return dict(status="budget")
    return dict(status="error", reason=f"exit {rc}")


SAFE_NAMES = {"nan": float("nan"), "inf": float("inf")}


def parse_call(call, params):
    """CrossHair prints `_target(a, b)` or `_target(x=..)`; return the positional args tuple as a literal repr."""
    node = ast.parse(call, mode="eval").body
    if not isinstance(node, ast.Call):
        raise ValueError("not a call")
    vals = [lit(a) for a in node.args]
    kw = {k.arg: lit(k.value) for k in node.keywords}
    for p in params[len(vals):]:
        vals.append(kw.pop(p))
    if kw or len(vals) != len(params):
        raise ValueError("argument mismatch")
    return rep((tuple(vals), {}))


def rep(v):
    """repr that stays parseable by lit_eval: non-finite floats become float('nan') / float('inf')."""
    if isinstance(v, float) and not (v == v and abs(v) != float("inf")):
        return f"float({str(v)!r})"
    if isinstance(v, list):
        return "[" + ", ".join(rep(x) for x in v) + "]"
    if isinstance(v, tuple):
        return "(" + ", ".join(rep(x) for x in v) + ("," if len(v) == 1 else "") + ")"
    if isinstance(v, dict):
        return "{" + ", ".join(f"{rep(k)}: {rep(x)}" for k, x in v.items()) + "}"
    if isinstance(v, (set, frozenset)) and v:
        inner = "{" + ", ".join(rep(x) for x in v) + "}"
        return inner if isinstance(v, set) else f"frozenset({inner})"
    return repr(v)


def lit_eval(s):
    """ast.literal_eval plus float('nan'|'inf'|'-inf') calls (as written by rep / printed by CrossHair)."""
    return lit(ast.parse(s, mode="eval").body)


def lit(node):
    try:
        return ast.literal_eval(node)
    except ValueError:
        pass
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "float" \
            and len(node.args) == 1 and isinstance(node.args[0], ast.Constant):
        return float(node.args[0].value)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -lit(node.operand)
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        xs = [lit(e) for e in node.elts]
        return xs if isinstance(node, ast.List) else tuple(xs) if isinstance(node, ast.Tuple) else set(xs)
    if isinstance(node, ast.Dict):
        return {lit(k): lit(v) for k, v in zip(node.keys, node.values)}
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("set", "frozenset") \
            and len(node.args) <= 1 and not node.keywords:
        xs = lit(node.args[0]) if node.args else ()
        return set(xs) if node.func.id == "set" else frozenset(xs)
    raise ValueError(f"non-literal argument {ast.unparse(node)[:80]}")


# ---------------------------------------------------------------- verification (sandboxed worker, repo python)
def verify_worker(job_path, out_path):
    sys.path.insert(0, str(H)); sys.path.insert(0, str(H.parent))
    import facts as F
    from preconditions import load_predicate
    from tracer import HOOKS, alarm, call, dcopy, fact_hit, instrument, load_module, trace
    job = json.loads(Path(job_path).read_text())
    task = job["task"]
    pg = load_module(task["put"]); put = pg[task["entry"]]
    code, _ = instrument(task["put"]); iput = load_module(code, HOOKS)[task["entry"]]
    vals = {k: load_predicate(src, "valid") for k, src in job["validators"].items()}
    out = {}
    for item in job["items"]:
        f = item["fact"]
        args = lit_eval(item["input_repr"])
        r = {}
        for k, v in vals.items():
            try:
                with alarm(1):
                    r[f"valid_{k}"] = v(*dcopy(args[0])) is True
            except BaseException:
                r[f"valid_{k}"] = False
        mutant = None
        if f["kind"] == "MUTANT":
            mutant = load_module(f.get("mutant_src") or F.make_mutant(task["put"], f["k"])[0])[task["entry"]]
        try:
            with alarm(10):
                tr = trace(iput, args)
                r["hit"] = bool(fact_hit(f, tr, call(put, args), call(mutant, args) if mutant else None))
        except BaseException as exc:
            r["hit"] = False; r["trace_error"] = type(exc).__name__
        out[item["key"]] = r
    Path(out_path).write_text(json.dumps(out))


def verify(items, tasks):
    """items: dicts with key, task, fact, input_repr. Sandboxed per task."""
    by = collections.defaultdict(list)
    for it in items:
        by[it["task"]].append(it)
    vd = OUT / "verify"; vd.mkdir(parents=True, exist_ok=True)
    result = {}

    def one(n):
        job = dict(task=dict(put=tasks[n]["put"], entry=tasks[n]["entry"]),
                   validators=dict(v2=(V2 / str(n) / "valid.py").read_text(), v4=(V4 / str(n) / "valid.py").read_text()),
                   items=[dict(key=i["key"], fact=i["fact"], input_repr=i["input_repr"]) for i in by[n]])
        key = sha(json.dumps(job, sort_keys=True))[:16]
        jp, op = vd / f"{n}_{key}.job.json", vd / f"{n}_{key}.out.json"
        if not op.exists():
            jp.write_text(json.dumps(job))
            subprocess.run(["timeout", "-k", "5", "300", "unshare", "-rn", sys.executable, "-I", "-B", __file__,
                            "verify-worker", str(jp), str(op)], env=ENV, cwd=vd, capture_output=True)
        return json.loads(op.read_text()) if op.exists() else {i["key"]: dict(error="verify worker failed") for i in by[n]}

    with ThreadPoolExecutor(8) as pool:
        for r in pool.map(one, sorted(by)):
            result.update(r)
    return result


def reveal(calls_by_task, tasks):
    """EvalPlus contract validity + PUT vs canonical, via analysis/worker.py (measurement only)."""
    sys.path.insert(0, str(H.parent))
    from trickcatcher_linefacts import oracle_b01 as ob
    hep = {int(r["task_id"].split("/")[1]): r for r in map(json.loads, ob.HEP.open())}
    rd = OUT / "reveal"; rd.mkdir(parents=True, exist_ok=True)
    status = {}
    for n, calls in sorted(calls_by_task.items()):
        h = hep[n]
        job = dict(entry=tasks[n]["entry"], put=tasks[n]["put"], canon=h["prompt"] + h["canonical_solution"],
                   contract=h["prompt"] + h["contract"] + "\n    pass\n", atol=h["atol"], calls=sorted(calls))
        key = sha(json.dumps(job, sort_keys=True))[:16]
        jp, op = rd / f"{n}_{key}.job.json", rd / f"{n}_{key}.out.json"
        if not op.exists():
            jp.write_text(json.dumps(job))
            subprocess.run(["timeout", "-k", "5", "300", "unshare", "-rn", sys.executable, "-I", "-B",
                            str(H / "analysis/worker.py"), str(jp), str(op)], env=ENV, cwd=rd, capture_output=True)
        status[n] = json.loads(op.read_text()) if op.exists() else {c: "worker_failed" for c in calls}
    return status


# ---------------------------------------------------------------- concrete harness check (no CrossHair)
SANITY_SRC = r"""
import ast, json, sys
sys.path.insert(0, sys.argv[1])
import harness as h
args = eval(sys.argv[2], {"__builtins__": {"float": float, "frozenset": frozenset, "set": set}})[0]
r = {"valid_v4": h._ok(h._VALID4, tuple(args))}
try:
    r["probe"] = bool(h._probe(*args))
except BaseException as exc:
    r["probe"] = None; r["error"] = type(exc).__name__
print(json.dumps(r))
"""


def sanity(items, preps):
    """Run each harness concretely (venv python, no CrossHair) on a known witness: does the harness signal REACHED
    exactly when the repo tracer's fact_hit says the witness hits? Measures harness fidelity."""
    def one(it):
        d = OUT / "harness" / it["gid"]
        if preps[it["gid"]]["mode"] != "check":
            return it["key"], dict(skipped=preps[it["gid"]]["mode"])
        p = subprocess.run(["timeout", "-k", "5", "60", "unshare", "-rn", str(VPY), "-I", "-B", "-c", SANITY_SRC,
                            str(d), it["input_repr"]], env=ENV, cwd=d, capture_output=True, text=True)
        try:
            return it["key"], json.loads(p.stdout.strip().splitlines()[-1])
        except Exception:
            return it["key"], dict(error=f"exit {p.returncode}: {p.stderr[-300:]}")
    with ThreadPoolExecutor(SETTINGS["workers"]) as pool:
        return dict(pool.map(one, items))


# ---------------------------------------------------------------- orchestration and report
def call_str(entry, input_repr):
    args = lit_eval(input_repr)[0]
    return f"{entry}({', '.join(rep(a) for a in args)})"


def main_all(workers):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "settings.json").write_text(json.dumps(SETTINGS, indent=1))
    tasks, gaps = load_gaps()
    controls = load_controls(tasks, gaps)
    items = gaps + controls
    # prepare in a subprocess: tracer sets RLIMIT_AS on import, which CrossHair children must not inherit
    pj = OUT / "prepare.json"
    (OUT / "items.json").write_text(json.dumps(items))
    subprocess.run([sys.executable, "-B", __file__, "prepare", str(OUT / "items.json"), str(pj)], check=True)
    preps = {r["id"]: r for r in json.loads(pj.read_text())}
    t0 = time.time()
    done = [0]

    def run(g):
        r = run_one(g, preps[g["id"]])
        done[0] += 1
        print(f"[{done[0]}/{len(items)}] {g['id']} {g['kind']} {r['status']} cpu={r.get('cpu_s')}", flush=True)
        return r
    with ThreadPoolExecutor(workers) as pool:
        rows = list(pool.map(run, items))
    wall = time.time() - t0
    # parse witnesses; collect known witnesses (Hypothesis, control fuzz) for re-verification and the harness check
    vitems, sitems = [], []
    for g, r in zip(items, rows):
        if r["status"] == "found":
            try:
                fn, params = entry_fn(tasks[g["task"]]["put"], tasks[g["task"]]["entry"])
                call = r["call"].replace("put_w(", "_t(", 1) if r["mode"] == "diff" else r["call"]
                r["input_repr"] = parse_call(call, params)
                vitems.append(dict(key=g["id"], task=g["task"], fact=g["fact"], input_repr=r["input_repr"]))
            except Exception as exc:
                r["parse_error"] = f"{type(exc).__name__}: {exc}"
        known = None
        if g.get("hyp_witness"):
            known = rep((ast.literal_eval(g["hyp_witness"]), {}))
            vitems.append(dict(key="hyp_" + g["id"], task=g["task"], fact=g["fact"], input_repr=known))
        elif g.get("known_witness"):
            known = g["known_witness"]
            vitems.append(dict(key="known_" + g["id"], task=g["task"], fact=g["fact"], input_repr=known))
        if known:
            sitems.append(dict(key=("hyp_" if g.get("hyp_witness") else "known_") + g["id"], gid=g["id"],
                               input_repr=known))
    ver = verify(vitems, tasks)
    san = sanity(sitems, preps)
    calls = collections.defaultdict(set)
    for it in vitems:
        v = ver.get(it["key"], {})
        it["check"] = v
        it["hit"] = bool(v.get("hit"))
        it["verified"] = bool(v.get("hit") and v.get("valid_v4"))          # primary count rule
        it["verified_v2"] = bool(v.get("hit") and v.get("valid_v2"))       # v5's rule (mined v2 validator)
        it["verified_both"] = bool(it["verified"] and v.get("valid_v2"))
        it["harness_check"] = san.get(it["key"])
        it["call"] = call_str(tasks[it["task"]]["entry"], it["input_repr"])
        if (it["verified"] or it["verified_v2"]) and not it["key"].startswith("known_"):
            calls[it["task"]].add(it["call"])
    rev = reveal(calls, tasks)
    for it in vitems:
        it["evalplus"] = rev.get(it["task"], {}).get(it["call"])
    spans = []
    for r in rows:
        so = OUT / "harness" / r["id"] / "stdout.txt"
        if r.get("wall_s") is not None and so.exists():
            spans.append((so.stat().st_mtime - r["wall_s"], so.stat().st_mtime))
    span = (max(e for _, e in spans) - min(b for b, _ in spans)) if spans else 0.0
    summary = dict(settings=SETTINGS, wall_s=round(wall, 1), crosshair_wall_span_s=round(span, 1),
                   crosshair_wall_sum_s=round(sum(r.get("wall_s") or 0 for r in rows), 1),
                   cpu_s=round(sum(r.get("cpu_s") or 0 for r in rows), 1),
                   gaps=[dict(g, **{k: v for k, v in r.items() if k not in ("stdout", "stderr", "settings")})
                         for g, r in zip(items, rows)],
                   verified_items=vitems)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    write_report(summary)


KINDS = ["STMT", "OUTCOME", "BOUND", "MUTANT", "NUM", "SHAPE", "REL"]
REG = ["STMT", "OUTCOME", "BOUND", "MUTANT"]


def counts(rows, vi, registered_only):
    c = collections.Counter(gaps=len(rows))
    for g in rows:
        st = g["status"]
        if registered_only and g["kind"] not in REG:
            st = "unsupported"
        sup = st != "unsupported"
        c["supported"] += sup
        c["attempted"] += sup
        c["found"] += st == "found"
        c["proven"] += st == "proven_unreachable"
        c["budget"] += st == "budget"
        c["hard"] += st == "hard_timeout"
        c["error"] += st == "error" or (st == "found" and "parse_error" in g)
        w = vi.get(g["id"]) if sup else None
        c["ver"] += bool(w and w["verified"])
        c["ver_both"] += bool(w and w["verified_both"])
        c["ver2"] += bool(w and w["verified_v2"])
        c["cpu"] += (g.get("cpu_s") or 0) if sup else 0
        h = vi.get("hyp_" + g["id"])
        c["hyp2"] += bool(h and h["verified_v2"])
        c["hyp4"] += bool(h and h["verified"])
    return c


def write_report(s):
    gaps = [g for g in s["gaps"] if not g.get("control")]
    ctl = [g for g in s["gaps"] if g.get("control")]
    vi = {it["key"]: it for it in s["verified_items"]}
    L = ["# CrossHair on the v5 hard gaps (offline, CPU only)", "",
         "Generated by `analysis/crosshair_gaps.py`; settings in its docstring and `out/crosshair_gaps/settings.json`,"
         " fixed before any gap result was read. No LLM call. Counted = CrossHair counterexample re-checked with the"
         " repo tracer (`tracer.fact_hit` on the raw fact) AND the B5 validator `out/precond_qwen7b_v4/<task>/valid.py`"
         " returns True. `v2` = the v3m2 mined validator that v5's Hypothesis draws had to pass.", "",
         "Settings: `" + json.dumps(s["settings"]) + "`", ""]
    cr, cx = counts(gaps, vi, True), counts(gaps, vi, False)
    dr = counts([g for g in gaps if g["split"] == "dev"], vi, True)
    dx = counts([g for g in gaps if g["split"] == "dev"], vi, False)
    L += ["## Headline", "",
          f"- Registered scope (STMT/OUTCOME/BOUND/MUTANT attempted, other kinds unsupported): CrossHair verified"
          f" **{cr['ver']}/276** (dev {dr['ver']}/238) vs Hypothesis {cr['hyp2']}/276 under v5's rule (hit + v2;"
          f" {cr['hyp4']}/276 under hit + v4). Attempted {cr['attempted']}, proven unreachable {cr['proven']},"
          f" budget out {cr['budget']}, hard timeouts {cr['hard']}, errors {cr['error']}.",
          f"- With the declared extension (NUM/SHAPE/REL also attempted): {cx['ver']}/276 (dev {dx['ver']}/238).",
          ""]
    hdr = ("| kind | gaps | attempted (supported) | CH counterexample | **verified (hit + v4)** | hit + v4 + v2 |"
           " hit + v2 | proven unreachable | budget out (60 s) | hard timeout | errors | CPU s |"
           " Hyp. hit + v2 (v5 rule) | Hyp. hit + v4 |")
    sep = "|---|" + "---:|" * 13

    def table(rows, title, registered_only, kinds):
        L.extend([f"## {title}", "", hdr, sep])
        for k in kinds + ["all"]:
            rs = [g for g in rows if k == "all" or g["kind"] == k]
            c = counts(rs, vi, registered_only)
            L.append(f"| {k} | {c['gaps']} | {c['attempted']} | {c['found']} | **{c['ver']}** | {c['ver_both']} |"
                     f" {c['ver2']} | {c['proven']} | {c['budget']} | {c['hard']} | {c['error']} | {c['cpu']:.0f} |"
                     f" {c['hyp2']} | {c['hyp4']} |")
        L.append("")

    table(gaps, "Registered scope: all 276 gaps (denominator of v5's 10/276); NUM/SHAPE/REL count as unsupported",
          True, KINDS)
    table([g for g in gaps if g["split"] == "dev"], "Registered scope, DEV tasks only (238 of the 276)", True, KINDS)
    table(gaps, "Declared extension: NUM/SHAPE/REL also attempted (same cell-hook harness), all 276", False, KINDS)
    table(ctl, "Positive control: reached facts (fuzz witness known), first 20 tasks with gaps", False,
          ["STMT", "OUTCOME", "BOUND"])
    # harness fidelity on known witnesses
    agree = collections.Counter()
    for key, it in vi.items():
        if key.startswith(("hyp_", "known_")) and it.get("harness_check") and "probe" in it["harness_check"]:
            hc = it["harness_check"]
            agree[(key.split("_")[0], it["hit"] and bool(hc.get("valid_v4")),
                   bool(hc["probe"]) and bool(hc.get("valid_v4")))] += 1
    L += ["## Harness fidelity (concrete run of each harness on a known witness, no CrossHair)", "",
          "Rows: source of witness, repo tracer says hit+v4, harness says reached+v4 → count. Disagreement would"
          " mean the harness target is not the tracer's fact.", ""]
    for k, v in sorted(agree.items()):
        L.append(f"- {k[0]}: tracer hit+v4 = {k[1]}, harness reached+v4 = {k[2]}: {v}")
    L.append("")
    # overlap
    ch = {g["id"] for g in gaps if g["kind"] in REG and vi.get(g["id"], {}).get("verified")}
    chx = {g["id"] for g in gaps if vi.get(g["id"], {}).get("verified")}
    hy2 = {g["id"] for g in gaps if vi.get("hyp_" + g["id"], {}).get("verified_v2")}
    hy4 = {g["id"] for g in gaps if vi.get("hyp_" + g["id"], {}).get("verified")}
    L += ["## Overlap with the 10 Hypothesis witnesses", "",
          f"- Hypothesis witnesses re-verified: hit + v2 (v5's rule) {len(hy2)}/276, hit + v4 {len(hy4)}/276 {sorted(hy4)}",
          f"- CrossHair verified, registered kinds: {len(ch)}/276 {sorted(ch)}",
          f"- CrossHair verified incl. extension kinds: {len(chx)}/276",
          f"- registered: both {len(ch & hy2)} {sorted(ch & hy2)}; CrossHair only {len(ch - hy2)};"
          f" Hypothesis(v2) only {len(hy2 - ch)} {sorted(hy2 - ch)}; union {len(ch | hy2)}/276",
          f"- incl. extension: both {len(chx & hy2)} {sorted(chx & hy2)}; CrossHair only {len(chx - hy2)};"
          f" Hypothesis(v2) only {len(hy2 - chx)} {sorted(hy2 - chx)}; union {len(chx | hy2)}/276", ""]
    # per-witness table
    ev = collections.defaultdict(collections.Counter)
    L += ["## Witnesses (measurement only: EvalPlus contract validity, PUT vs HumanEval+ canonical)", "",
          "| gap | source | kind | split | hit | v4 | v2 | EvalPlus | call |", "|---|---|---|---|---|---|---|---|---|"]
    gk = {g["id"]: g for g in s["gaps"]}
    for key, it in sorted(vi.items()):
        if key.startswith("known_") or not (it["verified"] or it["verified_v2"]):
            continue
        hyp = key.startswith("hyp_")
        gid = key[4:] if hyp else key
        g = gk[gid]
        src = "Hypothesis" if hyp else "CrossHair" + (" (control)" if g.get("control") else
                                                     "" if g["kind"] in REG else " (ext)")
        if it["verified"]:
            ev[src][it["evalplus"]] += 1
        L.append(f"| {gid} | {src} | {g['kind']} | {g['split']} | {it['hit']} | {it['check'].get('valid_v4')} |"
                 f" {it['check'].get('valid_v2')} | {it['evalplus']} | `{it['call'][:110].replace('|', '/')}` |")
    L += ["", "EvalPlus: `reveal` = contract-valid and PUT != canonical (bug-revealing); `same` = contract-valid, no"
          " difference; `invalid` = violates the EvalPlus contract; `canon_err` = canonical raises; `args` = call not"
          " re-parsable (e.g. nan/inf).", "",
          "Verified (hit + v4) witnesses by EvalPlus status (gap rows; controls listed separately):", ""]
    for src in ["CrossHair", "CrossHair (ext)", "Hypothesis", "CrossHair (control)"]:
        L.append(f"- {src}: " + ", ".join(f"{k} {v}" for k, v in sorted(ev[src].items(), key=str)))
    L.append("")
    nf = [g for g in gaps if g["status"] == "found" and not vi.get(g["id"], {}).get("verified")]
    L += ["## CrossHair counterexamples that did not verify", ""]
    for g in nf:
        it = vi.get(g["id"])
        L.append(f"- {g['id']} ({g['kind']}): {g.get('parse_error') or json.dumps(it['check'] if it else None)}"
                 f" call `{(g.get('call') or '')[:120]}`")
    L += ["", "## Unsupported / errors / hard timeouts", ""]
    for g in gaps:
        if g["status"] in ("unsupported", "error", "hard_timeout"):
            L.append(f"- {g['id']} ({g['kind']}): {g['status']} {g.get('reason', '')}")
    L += ["", f"Total CrossHair CPU (user+sys, all {len(s['gaps'])} runs incl. controls): {s['cpu_s']} s"
          f" ({s['cpu_s'] / 3600:.2f} CPU h); sum of per-run wall {s.get('crosshair_wall_sum_s')} s, run"
          f" {s['settings']['workers']} in parallel on a machine shared with other jobs. First-to-last run span"
          f" {s.get('crosshair_wall_span_s')} s (spans every cached pass, so it includes idle time between passes)."
          f" Last orchestrator pass: {s['wall_s']} s.", "",
          "Rerun: `python3 -B trickcatcher_linefacts/analysis/crosshair_gaps.py all` from the repo root (per-gap results"
          " cached in out/crosshair_gaps/harness/<id>/result.json; delete them to recompute; `report` re-renders).", ""]
    REPORT.write_text("\n".join(L))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("all", "prepare", "verify-worker", "report", "one"))
    ap.add_argument("args", nargs="*")
    ap.add_argument("--workers", type=int, default=SETTINGS["workers"])
    a = ap.parse_args()
    if a.cmd == "prepare":
        items = json.loads(Path(a.args[0]).read_text())
        Path(a.args[1]).write_text(json.dumps(prepare(items)))
    elif a.cmd == "verify-worker":
        verify_worker(*a.args)
    elif a.cmd == "report":
        write_report(json.loads((OUT / "summary.json").read_text()))
    elif a.cmd == "one":  # debugging: prepare + run a single gap id
        tasks, gaps = load_gaps()
        items = [g for g in gaps + load_controls(tasks, gaps) if g["id"] in a.args]
        pj = OUT / "prepare_one.json"; ij = OUT / "items_one.json"
        ij.write_text(json.dumps(items))
        subprocess.run([sys.executable, "-B", __file__, "prepare", str(ij), str(pj)], check=True)
        preps = {r["id"]: r for r in json.loads(pj.read_text())}
        for g in items:
            r = run_one(g, preps[g["id"]])
            print(g["id"], g["kind"], r["status"], r.get("call", r.get("reason", ""))[:200], r.get("wall_s"))
    else:
        main_all(a.workers)


if __name__ == "__main__":
    main()
