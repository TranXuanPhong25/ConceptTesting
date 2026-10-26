"""Line-level gap facts for one PUT, computed only from method-visible material (PUT source + HumanEval base tests).

usage: python3 -I facts.py <task_num> <put.py> <humaneval.jsonl> <out.json>

Fuzz validity uses EvalPlus prompt + contract or mined specification predicates; HumanEval+ tests remain evaluation-only.

Concepts (fixed vocabulary, see PREREG.md):
  OUTCOME  a decision or sub-condition with a missing outcome                 -- C2 / C3
  STMT     statements the base tests never executed                            -- statement coverage
  MUTANT   a one-token change at a line that the base tests do not detect       -- mutation / RIPR
  BOUND    equality to a comparison constant or its neighbours
  REL      equality / order / prefix / length relations (dev gate)
  SHAPE    sequence / string properties (dev gate)
  NUM      numeric argument properties
  LOOP / LOOP-MAX, OUTPUT, DU, DECISION and extended MUTANT operators have separate dev gates.
Each fact is rendered by a fixed template; it names the line and the behaviour, never an input.

Fuzzing (type-aware variations of the base inputs) is used only to (a) confirm that a fact is reachable,
(b) drop mutants that no fuzz input distinguishes (likely equivalent), and (c) give the tool-input arm a
concrete input per fact. Placebo facts use the same templates on behaviour the base tests already cover.
"""

# Direct-script workers run with -I: establish this copy's package explicitly.
import sys as _package_sys
from pathlib import Path as _PackagePath
if not __package__:
    _package_here = _PackagePath(__file__).resolve().parent
    _package_sys.path.insert(0, str(_package_here.parents[2]))
    __package__ = "trickcatcher_linefacts.pipelines." + _package_here.name
from .paths import REPO as _REPO, DATA_OUT, CONFIG, dataset_paths
import ast, json, math, random, re, sys, time
from pathlib import Path


from .tracer import HOOKS, call, instrument, load_module, run_base, same, trace, fact_hit  # noqa: E402

SEED = CONFIG["seeds"]["facts"]
KIND_ORDER = ("OUTCOME", "STMT", "MUTANT", "BOUND", "REL", "SHAPE", "NUM")
SLOTS = KIND_ORDER + ("MUTANT-X", "LOOP", "LOOP-MAX", "OUTPUT", "DU", "DECISION")
BASE_SLOTS = ("OUTCOME", "STMT", "MUTANT", "BOUND", "NUM")
GATE_ORDER = ("MUTANT-X", "LOOP", "LOOP-MAX", "OUTPUT", "DU", "REL", "DECISION", "SHAPE")
GATED_SLOTS = ('MUTANT-X', 'DU')
RANK_SLOTS = BASE_SLOTS + tuple(s for s in GATE_ORDER if s in GATED_SLOTS and s != "MUTANT-X")
K = 3
G_PRIME = True  # even/odd dev strong coverage is nondecreasing at K=3 and K=5
CONSTS = []  # numeric constants of the PUT (boundary values for fuzzing), set per task
N_FUZZ = 400
FUZZ_CAP = 5 * N_FUZZ


# ---------------------------------------------------------------- fuzzing
def scalar_variants(v):
    t = type(v)
    if t is bool:
        return [not v]
    if t is int:
        return [0, -v, v + 1, v - 1, 1, -1, v * 1000 + 7, -(abs(v) * 1000 + 7), 10 ** 17 + 3] \
            + [int(c) + d for c in CONSTS for d in (-1, 0, 1)]
    if t is float:
        return [0.0, -v, v + 0.5, v * 1e6, -1.5, 2.0 ** 53 + 1, float(round(v))] + [float(c) for c in CONSTS]
    if t is str:
        return ["", " ", v + " ", " " + v, v.upper(), v.lower(), v.swapcase(), v[::-1], v[:1], v * 2, v + "9",
                v.replace(" ", "  "), "-" + v, v + "!", v.capitalize(), v.title()]
    return []


def variants(v, rng):
    t = type(v)
    if t in (list, tuple):
        seq = list(v)
        out = [[], seq[:1], seq[::-1], seq + seq[:1], seq[1:], seq[:-1]]
        if seq:
            out.append([seq[0]] * len(seq))
            try:
                out += [sorted(seq), sorted(seq, reverse=True)]
            except TypeError:
                pass
        if seq:
            # same transformation applied to every element, and to one random element
            per = [variants(x, rng) for x in seq]
            width = min(len(p) for p in per)
            for j in range(width):
                out.append([p[j] for p in per])
            i = rng.randrange(len(seq))
            for nv in per[i][:8]:
                out.append(seq[:i] + [nv] + seq[i + 1:])
        return [t(x) for x in out]
    if t is dict:
        out = [{}]
        if v:
            k = next(iter(v))
            out.append({kk: vv for kk, vv in v.items() if kk != k})
        return out
    return scalar_variants(v)


def literal_ok(args):
    try:
        return ast.literal_eval(repr(args)) == args
    except Exception:
        return False


def fuzz_inputs(base_args, rng, valid=None, task=None, stats=None):
    seen, out = set(), []

    def add(a):
        if not literal_ok(a[0]) or not literal_ok(a[1]):
            return
        key = repr(a)
        if key not in seen:
            seen.add(key)
            out.append(a)

    targeted, level1 = [], []
    for a, k in base_args:
        for i, x in enumerate(a):
            for j in range(i + 1, len(a)):
                y = a[j]
                pairs = []
                if type(x) is type(y):
                    pairs += [(x, x), (y, y), (y, x)]
                    if isinstance(x, (list, tuple, str)):
                        pairs += [(x[:1], x), (x, x[:1]), (x[:min(len(x), len(y))], y[:min(len(x), len(y))])]
                for u, v in ((i, j), (j, i)):
                    if type(a[u]) is int and isinstance(a[v], (list, tuple, str)):
                        for z in (0, len(a[v]), len(a[v]) - 1, len(a[v]) + 1):
                            pairs.append((z, y) if u == i else (x, z))
                for x_, y_ in pairs:
                    vals = list(a); vals[i], vals[j] = x_, y_
                    targeted.append((tuple(vals), k))
            for nv in variants(x, rng):
                level1.append((a[:i] + (nv,) + a[i + 1:], k))
    rng.shuffle(targeted)
    rng.shuffle(level1)
    if valid is not None:
        return valid_fuzz(base_args, targeted, level1, rng, valid, task, stats)
    base_keys = {repr(b) for b in base_args}
    seen.update(base_keys)
    for a in targeted:
        add(a)
        if len(out) >= N_FUZZ // 4:
            break
    for a in level1:
        add(a)
    for _ in range(N_FUZZ):
        if not level1:
            break
        a, k = rng.choice(level1)
        if not a:
            continue
        i = rng.randrange(len(a))
        vs = variants(a[i], rng)
        if vs:
            add((a[:i] + (rng.choice(vs),) + a[i + 1:], k))
    return out[:N_FUZZ]


def valid_fuzz(base_args, targeted, level1, rng, valid, task, stats):
    seen, out = {repr(a) for a in base_args}, []
    stats.update(validator="evalplus", cap=FUZZ_CAP, attempts=0, checked=0, invalid=0,
                 duplicate=0, nonliteral=0)
    target = dict(cap=FUZZ_CAP // 4, goal=N_FUZZ // 4, attempts=0, checked=0, invalid=0, valid=0)

    def add(a, relation=False):
        stats["attempts"] += 1
        if relation: target["attempts"] += 1
        if not literal_ok(a[0]) or not literal_ok(a[1]):
            stats["nonliteral"] += 1
            return
        key = repr(a)
        if key in seen:
            stats["duplicate"] += 1
            return
        seen.add(key)
        stats["checked"] += 1
        if relation: target["checked"] += 1
        if not valid(task, a):
            stats["invalid"] += 1
            if relation: target["invalid"] += 1
            return
        out.append(a)
        if relation: target["valid"] += 1

    for a in targeted:
        if target["valid"] >= target["goal"] or target["attempts"] >= target["cap"]:
            break
        add(a, True)
    for a in level1:
        if len(out) >= N_FUZZ or stats["attempts"] >= FUZZ_CAP:
            break
        add(a)
    while level1 and len(out) < N_FUZZ and stats["attempts"] < FUZZ_CAP:
        a, k = rng.choice(level1)
        if not a:
            add((a, k))
            continue
        i = rng.randrange(len(a))
        vs = variants(a[i], rng)
        add((a[:i] + (rng.choice(vs),) + a[i + 1:], k) if vs else (a, k))
    stats.update(valid=len(out), valid_rate=len(out) / max(1, stats["attempts"]),
                 contract_valid_rate=len(out) / max(1, stats["checked"]), relation=target)
    target["valid_rate"] = target["valid"] / max(1, target["attempts"])
    target["contract_valid_rate"] = target["valid"] / max(1, target["checked"])
    return out


def call_src(entry, args):
    a, k = args
    parts = [repr(x) for x in a] + [f"{kk}={vv!r}" for kk, vv in k.items()]
    return f"{entry}({', '.join(parts)})"


# ---------------------------------------------------------------- statements
def statements(src):
    """(line, first source line) of every statement inside a function body, docstrings excluded, in order."""
    tree = ast.parse(src)
    lines = src.splitlines()
    out = []

    def walk(body):
        for s in body:
            if isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and isinstance(s.value.value, str):
                continue
            if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)):
                walk(s.body)
                continue
            out.append((s.lineno, lines[s.lineno - 1].strip()))
            for f in ("body", "orelse", "finalbody"):
                walk(getattr(s, f, []) or [])
            for h in getattr(s, "handlers", []) or []:
                walk(h.body)

    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            walk(n.body)
    return sorted(set(out))


# ---------------------------------------------------------------- mutation (legacy points followed by extended operators)
SWAP_CMP = {ast.Lt: [ast.LtE, ast.Gt], ast.LtE: [ast.Lt, ast.GtE], ast.Gt: [ast.GtE, ast.Lt],
            ast.GtE: [ast.Gt, ast.LtE], ast.Eq: [ast.NotEq], ast.NotEq: [ast.Eq], ast.In: [ast.NotIn],
            ast.NotIn: [ast.In], ast.Is: [ast.IsNot], ast.IsNot: [ast.Is]}
SWAP_BIN = {ast.Add: [ast.Sub], ast.Sub: [ast.Add], ast.Mult: [ast.Add, ast.FloorDiv], ast.Div: [ast.Mult],
            ast.FloorDiv: [ast.Div, ast.Mult], ast.Mod: [ast.FloorDiv], ast.Pow: [ast.Mult]}
BOUNDARY = {(ast.Lt, ast.LtE), (ast.LtE, ast.Lt), (ast.Gt, ast.GtE), (ast.GtE, ast.Gt)}


def mutation_points(tree, extra=True):
    docs = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.Module)) and n.body and isinstance(n.body[0], ast.Expr) \
                and isinstance(n.body[0].value, ast.Constant):
            docs.add(id(n.body[0].value))
    pts = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Compare):
            for j, op in enumerate(n.ops):
                for r in SWAP_CMP.get(type(op), []):
                    pts.append((n, ("cmp", j, r)))
        elif isinstance(n, (ast.BinOp, ast.AugAssign)):
            for r in SWAP_BIN.get(type(n.op), []):
                pts.append((n, ("bin", r)))
        elif isinstance(n, ast.BoolOp):
            pts.append((n, ("bool", ast.Or if isinstance(n.op, ast.And) else ast.And)))
        elif isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.Not):
            pts.append((n, ("dropnot",)))
        elif isinstance(n, ast.Constant) and type(n.value) is int and id(n) not in docs:
            for d in (1, -1):
                pts.append((n, ("const", d)))
    if extra:
        for n in ast.walk(tree):
            if isinstance(n, ast.Expr) and id(n.value) not in docs or isinstance(n, ast.AugAssign):
                pts.append((n, ("SDL",)))
            if isinstance(n, ast.Call) and not n.keywords:
                if isinstance(n.func, ast.Attribute) and n.func.attr in STRING_CALLS and not n.args:
                    pts.append((n, ("CALL", "receiver")))
                elif isinstance(n.func, ast.Name) and n.func.id in BUILTIN_CALLS and len(n.args) == 1:
                    pts.append((n, ("CALL", "argument")))
            if isinstance(n, ast.Slice):
                for f in ("lower", "upper", "step"):
                    if getattr(n, f) is not None: pts.append((n, ("SIR", f)))
            if isinstance(n, (ast.Break, ast.Continue)):
                pts.append((n, ("BCR",)))
            if isinstance(n, (ast.For, ast.While)):
                pts += [(n, ("ZIL",)), (n, ("OIL",))]
                if isinstance(n, ast.For): pts.append((n, ("RIL",)))
    return pts


STRING_CALLS = {"lower", "upper", "strip", "lstrip", "rstrip", "title", "capitalize", "swapcase"}
BUILTIN_CALLS = {"sorted", "reversed", "abs", "round", "int"}
FAMILIES = {"cmp": "ROR", "bin": "AOR", "bool": "COR", "dropnot": "UOI/negation", "const": "CRP constant", "CALL": "call-result removal"}


def make_mutant(src, k, *, source=False):
    """Returns (code, line, original fragment, mutated fragment, boundary?)."""
    tree = ast.parse(src)
    parents = {id(c): p for p in ast.walk(tree) for c in ast.iter_child_nodes(p)}
    n, m = mutation_points(tree)[k]
    shown = n
    if m[0] in ("const", "dropnot", "SIR"):
        p = parents.get(id(n))
        if isinstance(p, ast.expr):
            shown = p
    def frag():
        if isinstance(shown, ast.For):
            return f"for {ast.unparse(shown.target)} in {ast.unparse(shown.iter)}"
        if isinstance(shown, ast.While):
            return "while " + ast.unparse(shown.test)
        return ast.unparse(shown)

    before = frag()
    boundary = False
    if m[0] == "cmp":
        boundary = (type(n.ops[m[1]]), m[2]) in BOUNDARY
        n.ops[m[1]] = m[2]()
        after = frag()
    elif m[0] in ("bin", "bool"):
        n.op = m[1]()
        after = frag()
    elif m[0] == "const":
        p = parents.get(id(n))
        while isinstance(p, ast.expr):
            if isinstance(p, ast.Compare):
                boundary = True
                break
            p = parents.get(id(p))
        n.value = n.value + m[1]
        after = frag()
    elif m[0] == "SIR":
        setattr(n, m[1], None)
        after = frag()
    elif m[0] in ("ZIL", "OIL", "RIL"):
        if m[0] == "ZIL":
            n.body = [ast.copy_location(ast.Break(), n.body[0])]
        elif m[0] == "OIL":
            flag = f"__one_iteration_{k}"
            if isinstance(n, ast.For):
                n.iter = ast.Call(ast.Name("__mut_one__", ast.Load()), [n.iter], [])
            else:
                original = n.test
                n.test = ast.BoolOp(ast.And(), [ast.Name(flag, ast.Load()), original])
                n.body.insert(0, ast.copy_location(ast.Assign([ast.Name(flag, ast.Store())], ast.Constant(False)), n))
                parent = parents[id(n)]
                for field, val in ast.iter_fields(parent):
                    if isinstance(val, list) and n in val:
                        val.insert(val.index(n), ast.copy_location(ast.Assign([ast.Name(flag, ast.Store())], ast.Constant(True)), n))
                        break
        else:
            n.iter = ast.Call(ast.Name("__mut_reverse__", ast.Load()), [n.iter], [])
        after = {"ZIL": "skip the loop body", "OIL": "execute at most its first iteration",
                 "RIL": "iterate in reverse order"}[m[0]]
    elif m[0] in ("SDL", "CALL", "BCR"):
        replacement = (ast.Pass() if m[0] == "SDL" else
                       (n.func.value if m[1] == "receiver" else n.args[0]) if m[0] == "CALL" else
                       ast.Continue() if isinstance(n, ast.Break) else ast.Break())
        after = ast.unparse(replacement)
        parent = parents[id(n)]
        for field, val in ast.iter_fields(parent):
            if val is n: setattr(parent, field, ast.copy_location(replacement, n))
            elif isinstance(val, list):
                setattr(parent, field, [ast.copy_location(replacement, n) if x is n else x for x in val])
    else:  # drop `not`
        p = parents.get(id(n))
        after = ast.unparse(n.operand) if shown is n else None
        for f, val in ast.iter_fields(p):
            if val is n:
                setattr(p, f, n.operand)
            elif isinstance(val, list):
                setattr(p, f, [n.operand if x is n else x for x in val])
        if after is None:
            after = frag()
    if m[0] == "OIL" and isinstance(n, ast.For):
        tree.body = ast.parse("def __mut_one__(it):\n    for x in it:\n        yield x\n        return\n").body + tree.body
    if m[0] == "RIL":
        tree.body = ast.parse("def __mut_reverse__(it):\n    if isinstance(it, (list, tuple, str, range)):\n        return reversed(it)\n    return it\n").body + tree.body
    ast.fix_missing_locations(tree)
    return (ast.unparse(tree) if source else compile(tree, "<mut>", "exec")), n.lineno, before, after, boundary


# ---------------------------------------------------------------- templates
def t_outcome(line, src, missing, sub=False, decision=None):
    value = 'False' if missing == 'F' else 'True'
    if sub:
        return f"Condition coverage (C3): the sub-condition `{src}` of the decision at line {decision or line} is never {value} in the existing tests."
    return f"Branch coverage (C2): the {value} branch of `{src}` (line {line}) is never taken by the existing tests."


def t_outcome_placebo(line, src, sub=False, decision=None):
    if sub:
        return f"Condition coverage (C3): the sub-condition `{src}` of the decision at line {decision or line} is both True and False in the existing tests."
    return f"Branch coverage (C2): the True and False branches of `{src}` (line {line}) are taken by the existing tests."


def t_stmt(a, b, first):
    span = f"line {a}" if a == b else f"lines {a}-{b}"
    return f"Statement coverage (C1): {span} (starting with `{first}`) {'is' if a == b else 'are'} never executed by the existing tests."


def t_stmt_placebo(a, first):
    return f"Statement coverage (C1): line {a} (`{first}`) is executed by the existing tests."


def t_mutant(line, before, after, family, covered=False):
    state = "is killed: an existing test distinguishes them" if covered else "survives: no existing test distinguishes them"
    return f"Mutation ({family}): the mutant `{before}` -> `{after}` at line {line} {state}."


# ---------------------------------------------------------------- invariant families (BOUND, REL, SHAPE, NUM)
PRED_TEXT = {
    "len1": ("be", "of length 1"), "dup": ("verb", "contained duplicate elements"),
    "asc": ("be", "sorted in ascending order"), "desc": ("be", "sorted in descending order"),
    "hasneg": ("verb", "contained a negative number"), "haszero": ("verb", "contained a zero"),
    "upper": ("verb", "contained an uppercase letter"), "lower": ("verb", "contained a lowercase letter"),
    "digit": ("verb", "contained a digit"), "dblspace": ("verb", "contained two consecutive spaces"),
    "edgespace": ("verb", "started or ended with a space"),
    "punct": ("verb", "contained a character that is neither a letter, a digit nor a space"),
    "neg": ("be", "negative"), "zero": ("be", "zero"), "odd": ("be", "odd"), "nonint": ("be", "a non-integer number"),
}
SHAPE_LABELS = {"len1", "dup", "asc", "desc", "hasneg", "haszero", "upper", "lower", "digit", "dblspace",
                "edgespace", "punct"}


def say(subj, plural, form, pred, mode):
    be = "were" if plural else "was"
    if form == "be":
        return {"never": f"{subj} {be} never {pred}", "always": f"{subj} {be} always {pred}",
                "both": f"{subj} {be} sometimes {pred} and sometimes not"}[mode]
    return {"never": f"{subj} never {pred}", "always": f"{subj} always {pred}",
            "both": f"{subj} sometimes {pred} and sometimes did not"}[mode]


def describe(sites, sid, key):
    """(kind, line, subject, plural, form, predicate, prefix) of an invariant key, or None."""
    s = sites[sid]
    parts = key.split("|")
    if parts[0] == "eqc":
        m, c, d = int(parts[1]), parts[2], int(parts[3])
        cv = float(c) if "." in c or "e" in c else int(c)
        val = cv + d
        note = f"the constant in `{s['src']}`" if d == 0 else f"next to the constant {cv} in `{s['src']}`"
        return ("BOUND", s["line"], f"`{sites[m]['src']}`", False, "be", f"equal to {val!r} ({note})",
                f"Boundary value: at line {s['line']}, ")
    if parts[0] == "eqv":
        a, b = sites[int(parts[1])]["src"], sites[int(parts[2])]["src"]
        return ("REL", s["line"], f"`{a}` and `{b}`", True, "be", f"equal (in `{s['src']}`)",
                f"Decision table / dependent inputs: at line {s['line']}, ")
    pre = "Equivalence class: in the existing tests, "
    names = s.get("params", [])
    if parts[0] == "P":
        i, lab = int(parts[1]), parts[2]
        form, pred = PRED_TEXT[lab]
        return ("SHAPE" if lab in SHAPE_LABELS else "NUM", s["line"], f"parameter `{names[i]}` of `{s['src']}`",
                False, form, pred, pre)
    if parts[0] == "R":
        i, j, lab = int(parts[1]), int(parts[2]), parts[3]
        a, b = names[i], names[j]
        subj, plural, pred = {"eq": (f"the arguments `{a}` and `{b}`", True, "equal"),
                              "eqlen": (f"the argument `{a}`", False, f"equal to `len({b})`"),
                              "gtlen": (f"the argument `{a}`", False, f"greater than `len({b})`"),
                              "samelen": (f"the arguments `{a}` and `{b}`", True, "of the same length"),
                              "gt": (f"the argument `{a}`", False, f"greater than `{b}`"),
                              "prefix": (f"the argument `{a}`", False, f"a prefix of `{b}`")}[lab]
        return ("REL", s["line"], subj, plural, "be", pred, "Decision table / dependent inputs: in the existing tests, ")
    return None


def call_plausible(src, node, sites, traces):
    cells = set().union(*(tr[0] for tr in traces))

    def types(expr):
        if isinstance(expr, ast.Constant): return {type(expr.value).__name__}
        if isinstance(expr, (ast.List, ast.ListComp)): return {"list"}
        if isinstance(expr, ast.Tuple): return {"tuple"}
        if isinstance(expr, ast.BinOp): return types(expr.left) & types(expr.right)
        if isinstance(expr, ast.UnaryOp): return types(expr.operand)
        if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name) and expr.func.id in ("list", "tuple", "str", "int", "float", "range"):
            return {expr.func.id}
        text = ast.unparse(expr)
        ids = {i for i, s in enumerate(sites) if s["line"] == expr.lineno and s["src"] == text}
        return {c.split(":")[0] for sid, c in cells if sid in ids and isinstance(c, str) and "|" not in c}

    if isinstance(node.func, ast.Attribute):
        ts = types(node.func.value)
        return bool(ts) and ts <= {"str"}
    ts = types(node.args[0])
    allowed = {"list"} if node.func.id == "sorted" else ({"list", "tuple", "str", "range"} if node.func.id == "reversed" else {"int", "float"})
    return bool(ts) and ts <= allowed


def output_text(key):
    typ, label = key.split("|", 1)
    if typ == "class":
        if label == "None": return "None"
        if label.startswith("bool:"): return label[5:]
        t, c = label.split(":", 1)
        if t in ("list", "tuple", "dict", "set", "frozenset"):
            return f"an {'empty' if c == 'empty' else 'non-empty'} {t}"
        if t == "str":
            return {"empty": "an empty string", "alpha": "a string of letters only",
                    "nonalpha": "a non-empty string with non-letter characters"}[c]
        return f"a {t} value in the class '{c}'"
    return {"len1": "a sequence of length 1", "dup": "a sequence containing duplicate elements",
            "asc": "a sequence sorted in ascending order", "desc": "a sequence sorted in descending order",
            "hasneg": "a sequence containing a negative number", "haszero": "a sequence containing zero",
            "upper": "a string containing an uppercase letter", "lower": "a string containing a lowercase letter",
            "digit": "a string containing a digit", "dblspace": "a string containing two consecutive spaces",
            "edgespace": "a string starting or ending with a space", "punct": "a string containing punctuation",
            "neg": "a negative number", "zero": "zero", "odd": "an odd integer",
            "nonint": "a non-integer number"}[label]


def new_facts(src, sites, base, fuzz, facts, placebo):
    bc = set().union(*(tr[0] for tr in base)) if base else set()
    fc = set().union(*(tr[0] for tr in fuzz)) if fuzz else set()

    def emit(f, selector, seen):
        f.update(selector)
        if seen:
            placebo.append(f)
        else:
            f["witness"] = next((i for i, tr in enumerate(fuzz) if fact_hit(f, tr)), None)
            if f["witness"] is not None: facts.append(f)

    for sid, s in enumerate(sites):
        if s["kind"] != "loop": continue
        bn = sorted({int(c[5:]) for x, c in bc if x == sid and c.startswith("loop:")})
        fn = sorted({int(c[5:]) for x, c in fc if x == sid and c.startswith("loop:")})
        for count in (0, 1, 2):
            seen = count in bn
            f = {"kind": "LOOP", "line": s["line"], "text": f"Loop coverage: the loop at line {s['line']} {'iterates' if seen else 'never iterates'} exactly {count} times in a single execution {'in' if seen else 'under'} the existing tests."}
            emit(f, {"cell": [sid, f"loop:{count}"]}, seen)
        if bn and fn and max(fn) > max(bn):
            f = {"kind": "LOOP-MAX", "line": s["line"], "text": f"Loop coverage: the loop at line {s['line']} never iterates more than {max(bn)} times in a single execution under the existing tests."}
            emit(f, {"loop_max": [sid, max(bn)]}, False)
        if bn:
            mx = max(bn)
            placebo.append({"kind": "LOOP-MAX", "line": s["line"], "text": f"Loop coverage: the loop at line {s['line']} iterates {mx} times in a single execution under the existing tests.", "cell": [sid, f"loop:{mx}"]})

    returns = [n.lineno for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Return)]
    line = min(returns) if returns else min(s['line'] for s in sites)
    for sid, c in sorted(bc | fc):
        if sid != -1 or not c.endswith("|True"): continue
        key = c[len("output|"):-len("|True")]
        seen = (sid, c) in bc
        f = {"kind": "OUTPUT", "line": line, "text": f"Output equivalence class: the function {'returns' if seen else 'never returns'} {output_text(key)} in the existing tests."}
        emit(f, {"cell": [sid, c]}, seen)

    for seen, cs in ((False, fc - bc), (True, bc)):
        pairs = [(sid, c) for sid, c in sorted(cs) if sid == -2][:64]
        for sid, c in pairs:
            _, scope, name, define, use, kind = c.split("|")
            f = {"kind": "DU", "line": int(use), "text": f"Def-use pair (all-uses, {kind}): the value assigned to `{name}` at line {define} {'reaches' if seen else 'never reaches'} its use at line {use} in the existing tests."}
            emit(f, {"cell": [sid, c]}, seen)

    tree = ast.parse(src)
    parents = {id(c): p for p in ast.walk(tree) for c in ast.iter_child_nodes(p)}
    nodes = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.If, ast.While, ast.IfExp)): continue
        sid = next((i for i, s in enumerate(sites) if s["kind"] == "cond" and s["line"] == node.test.lineno
                    and s["src"] == ast.unparse(node.test)), None)
        if sid is not None: nodes[sid] = node

    def ancestors(node):
        out = []
        while id(node) in parents:
            node = parents[id(node)]; out.append(node)
        return out

    pairs = []
    for a, n in sorted(nodes.items()):
        for b, m in sorted(nodes.items()):
            if a >= b: continue
            an, am = ancestors(n), ancestors(m)
            scopes = [next((x for x in aa if isinstance(x, (ast.FunctionDef, ast.Lambda))), None) for aa in (an, am)]
            if scopes[0] is not scopes[1] or n in am or m in an: continue
            pairs.append((a, b))
    for a, b in pairs[:32]:
        for x in ("T", "F"):
            for y in ("T", "F"):
                cs = [[a, x], [b, y]]
                seen = any(all(tuple(c) in tr[0] for c in cs) for tr in base)
                sa, sb = sites[a], sites[b]
                ta, tb = x == 'T', y == 'T'
                f = {"kind": "DECISION", "line": sa["line"], "text": f"Decision table: {'an existing test' if seen else 'no existing test'} makes `{sa['src']}` (line {sa['line']}) {ta} and `{sb['src']}` (line {sb['line']}) {tb} in the same call."}
                emit(f, {"all_cells": cs}, seen)


# ---------------------------------------------------------------- ranking / spec examples
def slot(f):
    return "MUTANT-X" if f.get("extended") else f["kind"]


def display_slot(f):
    s = slot(f)
    return "MUTANT" if s == "MUTANT-X" and s in GATED_SLOTS else s


def set_blocks(src, facts):
    guards = [g for g in ast.walk(ast.parse(src)) if isinstance(g, ast.If) and g.body
              and len(g.body) <= 2 and isinstance(g.body[-1], (ast.Return, ast.Raise, ast.Break, ast.Continue))]
    for f in facts:
        gs = [g for g in guards if g.lineno <= f["line"] <= max(s.end_lineno for s in g.body)]
        g = min(gs, key=lambda g: g.end_lineno - g.lineno) if gs else None
        f["block"] = g.lineno if g else f["line"]


def tier(f, g_prime=G_PRIME):
    return int(bool(g_prime and f.get("g_demote")))


def du_key(f):
    return ("DU", f["cell"][1].split("|")[2]) if f["kind"] == "DU" else None


def pick(pool, n, k=K, g_prime=G_PRIME, shape=False):
    slots = RANK_SLOTS + (("SHAPE",) if shape and "SHAPE" not in RANK_SLOTS else ())
    rng = random.Random(SEED + n)
    by = {}
    for tv in (0, 1):
        for s in slots:
            fs = [f for f in pool if f["reached"] and display_slot(f) == s and tier(f, g_prime) == tv]
            rng.shuffle(fs)
            if s == "MUTANT":
                fs.sort(key=lambda f: bool(f.get("boundary")))
            by[tv, s] = fs
    top, used, used_du = [], set(), set()
    for tv in (0, 1):
        while len(top) < k and any(by[tv, s] for s in slots):
            for s in slots:
                fs = by[tv, s]
                while fs and (fs[0]["block"] in used or du_key(fs[0]) in used_du):
                    fs.pop(0)
                if fs and len(top) < k:
                    f = fs.pop(0)
                    top.append(f)
                    used.add(f["block"])
                    if du_key(f) is not None:
                        used_du.add(du_key(f))
    return top


def make_forced(src, entry, node, forced):
    pos = (node.lineno, node.col_offset, node.end_lineno, node.end_col_offset)

    class Force(ast.NodeTransformer):
        def visit(self, n):
            if isinstance(n, ast.expr) and (n.lineno, n.col_offset, n.end_lineno, n.end_col_offset) == pos:
                v = ast.Call(ast.Name("__force", ast.Load()), [self.generic_visit(n)], [])
                return ast.copy_location(v, n)
            return self.generic_visit(n)

    tree = Force().visit(ast.parse(src))
    ast.fix_missing_locations(tree)
    changed = [False]

    def force(v):
        if bool(v) != forced:
            changed[0] = True
        return forced

    return load_module(compile(tree, "<put>", "exec"), {"__force": force})[entry], changed


def guard_features(src, entry, facts, sites, base_cells, fz, fz_cells, fz_lines, fz_out, mfns, put):
    guards = [g for g in ast.walk(ast.parse(src)) if isinstance(g, ast.If) and g.body
              and any(isinstance(s, (ast.Return, ast.Raise)) for s in g.body)]
    cache, plain = {}, {}
    for f in facts:
        f["g_demote"] = False
        if not f["reached"]:
            continue
        gs = [g for g in guards if g.lineno <= f["line"] <= max(s.end_lineno for s in g.body)]
        g = min(gs, key=lambda g: g.end_lineno - g.lineno) if gs else None
        if g is None:
            continue
        header = g.lineno <= f["line"] <= g.test.end_lineno
        if f["kind"] == "MUTANT" and header:
            continue
        sid = next((i for i, s in enumerate(sites) if s["kind"] == "cond"
                    and s["line"] == g.test.lineno and s["src"] == ast.unparse(g.test)), None)
        seen = {c for x, c in base_cells if x == sid and c in ("T", "F")}
        if len(seen) != 1:
            continue
        forced = "T" in seen
        f["guard_line"], f["guard_forced"] = g.lineno, forced
        key = (g.lineno, g.col_offset, forced)
        if key not in cache:
            fn, changed = make_forced(src, entry, g.test, forced)
            cache[key] = fn, changed, {}
        fn, changed, outs = cache[key]
        cnt = {"same": 0, "necessary": 0, "differ": 0}
        for i in range(len(fz)):
            if (sid, "F" if forced else "T") not in fz_cells[i]:
                continue
            mout = call(mfns[f["k"]], fz[i]) if f["kind"] == "MUTANT" else None
            if i not in plain:
                plain[i] = call(put, fz[i])
            hit = fact_hit(f, (fz_cells[i], fz_lines[i], *fz_out[i]), plain[i], mout)
            if not hit:
                continue
            if i not in outs:
                changed[0] = False
                outs[i] = call(fn, fz[i]), changed[0]
            (st, val), took = outs[i]
            if not took:
                continue
            if i not in plain:
                plain[i] = call(put, fz[i])
            ps, pv = plain[i]
            if ps != "ok" and st != "ok" or ps == st == "ok" and same(pv, val):
                cnt["same"] += 1
            elif ps == "ok" and st != "ok":
                cnt["necessary"] += 1
            else:
                cnt["differ"] += 1
        cls = "na" if not sum(cnt.values()) else ("differ" if cnt["differ"] else
                                                   "necessary" if cnt["necessary"] else "same")
        f["guard_class"], f["guard_counts"] = cls, cnt
        f["g_demote"] = cls in ("same", "necessary")


def parse_examples(prompt, entry):
    tree = ast.parse(prompt)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == entry)
    doc = ast.get_docstring(fn) or ""
    out, seen = [], set()
    for m in re.finditer(r"\b" + re.escape(entry) + r"\s*\(", doc):
        start, i, depth, quote = m.start(), m.end() - 1, 0, None
        while i < len(doc):
            c = doc[i]
            if quote:
                if c == "\\":
                    i += 1
                elif c == quote:
                    quote = None
            elif c in "'\"":
                quote = c
            elif c in "([{":
                depth += 1
            elif c in ")]}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        if depth:
            continue
        text = doc[start:i + 1]
        rest = doc[i + 1:].splitlines()
        tail = rest[0].strip() if rest else ""
        marker = re.match(r"(?:==|=>|->|➞|→)\s*(.*)", tail)
        prefix = doc[:start].rsplit("\n", 1)[-1].strip()
        exp = marker.group(1) if marker else None
        if exp is None and prefix == ">>>" and not tail:
            exp = next((s.strip() for s in rest[1:] if s.strip()), None)
        if exp is None:
            continue
        try:
            c = ast.parse(text, mode="eval").body
            args = (tuple(ast.literal_eval(a) for a in c.args),
                    {a.arg: ast.literal_eval(a.value) for a in c.keywords if a.arg is not None})
            if any(a.arg is None for a in c.keywords):
                continue
            expected = ast.literal_eval(exp.strip().rstrip(".,;"))
        except (ValueError, SyntaxError):
            continue
        key = repr((args, expected))
        if key not in seen:
            seen.add(key)
            out.append((args, expected))
    return out


def doc_fail(put, prompt, entry):
    out = []
    for args, expected in parse_examples(prompt, entry):
        st, got = call(put, args)
        eq = st == "ok" and same(got, expected)
        if st == "ok" and type(got) in (int, float) and type(expected) in (int, float):
            eq = eq or math.isclose(got, expected, rel_tol=1e-6, abs_tol=1e-6)
        if not eq:
            out.append({"call": call_src(entry, args), "expected": repr(expected),
                        "got": repr(got) if st == "ok" else f"<{st}>"})
    return out


# ---------------------------------------------------------------- main
def main(n, put_src, he, out, validity="evalplus", contract_data=None, precond_dir=None,
         mutant_points=None, evidence=None):
    t0 = time.time()
    rng = random.Random(SEED + n)
    entry = he["entry_point"]
    pg = load_module(put_src)
    put = pg[entry]
    base_args, ok = run_base(put, he["test"], ns=pg)
    res = {"task": n, "entry": entry, "base_ok": ok, "n_base": len(base_args)}
    res["doc_fail"] = doc_fail(put, he["prompt"], entry)

    code, sites = instrument(put_src)
    iput = load_module(code, HOOKS)[entry]
    base_cells, base_lines, base_traces = set(), set(), []
    for a in base_args:
        tr = trace(iput, a)
        base_traces.append(tr)
        cs, ls, _, _ = tr
        base_cells |= cs
        base_lines |= ls

    CONSTS[:] = sorted({n.value for n in ast.walk(ast.parse(put_src)) if isinstance(n, ast.Constant)
                        and isinstance(n.value, (int, float)) and not isinstance(n.value, bool)
                        and abs(n.value) < 10 ** 6} - {0, 1, -1})[:12]
    from .fuzz_validity import CONTRACTS, validator
    stats = {}
    with validator(validity, n, precond_dir if validity == "mined" else contract_data or CONTRACTS) as valid:
        fz = fuzz_inputs(base_args, rng, valid, n, stats)
    if validity != "none":
        stats["validator"] = validity
        res.update(facts_version="v3m" if validity == "mined" else "v3c", fuzz_validity=stats)
        if validity == "mined":
            from .fuzz_validity import MINED_ROOT
            import hashlib
            res["valid_sha256"] = hashlib.sha256(((Path(precond_dir) if precond_dir else MINED_ROOT) / str(n) / "valid.py").read_bytes()).hexdigest()
    fz_cells, fz_lines, fz_out, fz_traces = [], [], [], []
    for a in fz:
        tr = trace(iput, a)
        fz_traces.append(tr)
        cs, ls, st, val = tr
        fz_cells.append(cs)
        fz_lines.append(ls)
        fz_out.append((st, val))
    res["n_fuzz"] = len(fz)

    def first_hit(pred):
        for i in range(len(fz)):
            if pred(i):
                return i
        return None

    facts, placebo = [], []

    # OUTCOME
    for sid, s in enumerate(sites):
        if s["kind"] not in ("cond", "subcond"):
            continue
        seen = {c for (x, c) in base_cells if x == sid and c in ("T", "F")}
        if len(seen) == 1:
            miss = "F" if "T" in seen else "T"
            w = first_hit(lambda i: (sid, miss) in fz_cells[i])
            facts.append({"kind": "OUTCOME", "line": s["line"], "text": t_outcome(s["line"], s["src"], miss, s["kind"] == "subcond", s.get("decision_line")),
                          "cell": [sid, miss], "witness": w})
        elif len(seen) == 2:
            placebo.append({"kind": "OUTCOME", "line": s["line"], "text": t_outcome_placebo(s["line"], s["src"], s["kind"] == "subcond", s.get("decision_line")),
                            "cells": [[sid, "T"], [sid, "F"]]})

    # STMT: maximal runs of consecutive never-executed statements
    stmts = statements(put_src)
    run = []
    for ln, txt in stmts + [(None, None)]:
        if ln is not None and ln not in base_lines:
            run.append((ln, txt))
            continue
        if run:
            lines = [x for x, _ in run]
            w = first_hit(lambda i: bool(set(lines) & fz_lines[i]))
            facts.append({"kind": "STMT", "line": lines[0], "text": t_stmt(lines[0], lines[-1], run[0][1]),
                          "lines": lines, "witness": w})
            run = []
        if ln is not None:
            placebo.append({"kind": "STMT", "line": ln, "text": t_stmt_placebo(ln, txt), "lines": [ln]})

    # BOUND / REL / SHAPE / NUM: a property that held the same way in every base execution ("never" or "always")
    inv = {}
    for (sid, c) in base_cells:
        if isinstance(c, str) and c.split("|", 1)[0] in ("eqc", "eqv", "P", "R"):
            key, t = c.rsplit("|", 1)
            inv.setdefault((sid, key), set()).add(t)
    for (sid, key), ts in sorted(inv.items()):
        d = describe(sites, sid, key)
        if d is None:
            continue
        kind, line, subj, plural, form, pred, pre = d
        if len(ts) == 2:
            placebo.append({"kind": kind, "line": line, "text": pre + say(subj, plural, form, pred, "both") + ".",
                            "cells": [[sid, f"{key}|True"], [sid, f"{key}|False"]]})
            continue
        t = next(iter(ts))
        cell = f"{key}|{'False' if t == 'True' else 'True'}"
        w = first_hit(lambda i: (sid, cell) in fz_cells[i])
        mode = "always" if t == "True" else "never"
        facts.append({"kind": kind, "line": line, "cell": [sid, cell], "witness": w,
                      "text": pre + say(subj, plural, form, pred, mode) + "."})

    # MUTANT: retain the v2 sample, then sample the extended operators separately.
    tree = ast.parse(put_src)
    pts = mutation_points(tree)
    legacy = len(mutation_points(tree, False))
    order, extra = list(range(legacy)), list(range(legacy, len(pts)))
    if mutant_points is not None:
        pts = mutant_points
        order = [p['k'] for p in pts if not p['extended']]
        extra = [p['k'] for p in pts if p['extended']]
        legacy = len(order)
    random.Random(SEED).shuffle(order)
    random.Random(SEED).shuffle(extra)
    n_surv = n_equiv = 0
    mfns, plain = {}, {}
    for k in sorted(order[:80] + extra[:80]):
        family = pts[k]['family'] if mutant_points is not None else FAMILIES.get(pts[k][1][0], pts[k][1][0])
        try:
            if mutant_points is not None:
                mcode, line, before, after, boundary = (pts[k][key] for key in ('mutant_src','line','before','after','boundary'))
            else:
                mcode, line, before, after, boundary = make_mutant(put_src, k)
                if pts[k][1][0] == "CALL" and not call_plausible(put_src, pts[k][0], sites, base_traces):
                    continue
            mg = load_module(mcode)
            mfn = mg[entry]
        except BaseException:
            continue
        _, mok = run_base(mfn, he["test"], record=False, ns=mg)
        common = {"kind": "MUTANT", "line": line, "k": k, "family": family, "extended": k >= legacy}
        if mutant_points is not None:
            common.update({key: pts[k][key] for key in ('extended','operator','mutant_src')})
        if mok is not True:
            placebo.append(dict(common, text=t_mutant(line, before, after, family, True)))
            continue
        n_surv += 1
        w = None
        for i, a in enumerate(fz):
            st, val = call(mfn, a)
            if i not in plain: plain[i] = call(put, a)
            pst, pval = plain[i]
            if st != pst or (st == "ok" and not same(val, pval)):
                w = i
                break
        if w is None:
            n_equiv += 1
            continue
        facts.append(dict(common, text=t_mutant(line, before, after, family), witness=w, boundary=boundary))
        mfns[k] = mfn
    res["n_points"], res["n_survived"], res["n_equiv_dropped"] = len(pts), n_surv, n_equiv
    res["n_points_legacy"], res["n_points_extended"] = legacy, len(pts) - legacy

    new_facts(put_src, sites, base_traces, fz_traces, facts, placebo)

    # dedupe identical texts, attach witness call source
    def dedupe(lst):
        seen, out = set(), []
        for f in lst:
            if f["text"] not in seen:
                seen.add(f["text"])
                out.append(f)
        return out

    facts, placebo = dedupe(facts), dedupe(placebo)
    if evidence is not None:
        evidence(locals())
    for f in facts:
        f["reached"] = f["witness"] is not None
        f["witness_call"] = call_src(entry, fz[f["witness"]]) if f["reached"] else None

    set_blocks(put_src, facts)
    guard_features(put_src, entry, facts, sites, base_cells, fz, fz_cells, fz_lines, fz_out, mfns, put)
    for f in facts:
        f["tier"] = tier(f)
    top = pick(facts, n)
    # placebo: same kind mix as `top` where possible, seeded random
    prng = random.Random(SEED + n + 1)
    plc, pool = [], [p for p in placebo if display_slot(p) in RANK_SLOTS]
    prng.shuffle(pool)
    for f in top:
        c = next((p for p in pool if p["kind"] == f["kind"]), None) or (pool[0] if pool else None)
        if c:
            plc.append(c)
            pool.remove(c)

    res["facts"] = facts
    res["rank_version"], res["rank_k"], res["g_prime"] = "v3", K, G_PRIME
    res["gated_slots"] = list(GATED_SLOTS)
    res["top3"] = [facts.index(f) for f in top]
    res["placebo3"] = plc
    res["placebo_all"] = placebo
    res["counts"] = {k: sum(slot(f) == k for f in facts) for k in SLOTS}
    res["reached"] = {k: sum(slot(f) == k and f["reached"] for f in facts) for k in SLOTS}
    res["secs"] = round(time.time() - t0, 1)
    json.dump(res, open(out, "w"), indent=1)


if __name__ == "__main__":
    import argparse
    from .fuzz_validity import CONTRACTS, VALIDATORS
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", type=int)
    parser.add_argument("put")
    parser.add_argument("humaneval")
    parser.add_argument("out")
    parser.add_argument("--validity", choices=("none", *VALIDATORS), default="evalplus")
    parser.add_argument("--contract-data", type=Path, default=CONTRACTS)
    parser.add_argument("--precond-dir", type=Path)
    args = parser.parse_args()
    n, putp, hep_, out = args.task, args.put, args.humaneval, args.out
    he = [r for r in map(json.loads, open(hep_)) if r["task_id"] == f"HumanEval/{n}"][0]
    main(n, open(putp).read(), he, out, args.validity, args.contract_data, args.precond_dir)
