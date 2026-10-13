"""Execution helpers shared by facts.py and evaluate.py (stdlib only; each task runs in its own process).

- abstract values: ConceptCoder BP-style classes (sign / zero / small / large, True / False, empty, alpha, None)
- `instrument`: AST rewrite that records (site, class) cells for conditions, loops, variables, operands, returns
- `call` / `trace`: one call under a deterministic step budget; `trace` also returns cells and executed lines
- `run_base`: run HumanEval's `check` with a recording `candidate`

Ported from the round-1 feasibility worker (scratchpad, 2026-10-10); behaviour unchanged.
"""

# Direct-script workers run with -I: establish this copy's package explicitly.
import sys as _package_sys
from pathlib import Path as _PackagePath
if not __package__:
    _package_here = _PackagePath(__file__).resolve().parent
    _package_sys.path.insert(0, str(_package_here.parents[2]))
    __package__ = "trickcatcher_linefacts.pipelines." + _package_here.name
from .paths import REPO as _REPO, DATA_OUT, CONFIG, dataset_paths
import ast, builtins, contextlib, copy, io, math, random, resource, signal, sys

resource.setrlimit(resource.RLIMIT_AS, (3 << 30, 3 << 30))
sys.setrecursionlimit(5000)
try:
    sys.set_int_max_str_digits(0)
except Exception:
    pass


class Timeout(BaseException):
    pass


def _alarm(sig, frm):
    raise Timeout()


signal.signal(signal.SIGALRM, _alarm)


@contextlib.contextmanager
def alarm(t):
    signal.setitimer(signal.ITIMER_REAL, t)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


def dcopy(x):
    try:
        return copy.deepcopy(x)
    except Exception:
        return x


# ---------------------------------------------------------------- abstract values
def numcls(x):
    try:
        if x != x:
            return "nan"
        if x in (math.inf, -math.inf):
            return "inf"
    except Exception:
        return None
    if x == 0:
        return "zero"
    if x < 0:
        return "neg-small" if x >= -1000 else "neg-large"
    return "pos-small" if x <= 1000 else "pos-large"


CONT = (list, tuple, dict, set, frozenset)


def absval(v):
    t = type(v)
    if v is None:
        return "None"
    if t is bool:
        return "bool:" + str(v)
    if t is int:
        return "int:" + numcls(v)
    if t is float:
        return "float:" + numcls(v)
    if t is str:
        return "str:empty" if not v else ("str:alpha" if v.isalpha() else "str:nonalpha")
    if t in CONT:
        return t.__name__ + (":empty" if len(v) == 0 else ":nonempty")
    return None


CUR = [set()]
LAST = {}  # var/operand site -> class of the value it last produced
LASTVAL = {}  # var/operand site -> the value itself
DEFS = {}
DU_LIMIT = 4096

MEMBERS = {}  # condition site -> var/operand sites read inside it (filled by `instrument`)
PROBES = {}  # condition site -> [("eqc", site, const) | ("eqv", site, site)] from the comparisons inside it


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def __v(sid, v):
    c = absval(v)
    if c is not None:
        CUR[0].add((sid, c))
        LAST[sid] = c
    LASTVAL[sid] = v
    return v


def __c(sid, v):
    o = "T" if v else "F"
    CUR[0].add((sid, o))
    for p in PROBES.get(sid, ()):  # boundary / relation probes on the values this condition just compared
        if p[0] == "eqc":
            x = LASTVAL.get(p[1], None)
            if _num(x):
                for d in (-1, 0, 1):
                    CUR[0].add((sid, f"eqc|{p[1]}|{p[2]}|{d}|{x == p[2] + d}"))
        else:
            x, y = LASTVAL.get(p[1], None), LASTVAL.get(p[2], None)
            if x is not None and y is not None and (type(x) is type(y) or (_num(x) and _num(y))):
                try:
                    CUR[0].add((sid, f"eqv|{p[1]}|{p[2]}|{bool(x == y)}"))
                except Exception:
                    pass
    for m in MEMBERS.get(sid, ()):  # outcome paired with the class of each value the condition just read
        c = LAST.pop(m, None)
        LASTVAL.pop(m, None)
        if c is not None:
            CUR[0].add((sid, f"{o}|{m}|{c}"))
    return v


def shape_preds(v):
    """Tester-level properties of one argument value: (label, holds?)."""
    out = []
    if isinstance(v, (list, tuple)):
        out.append(("len1", len(v) == 1))
        if len(v) >= 2:
            try:
                out.append(("dup", len(set(v)) < len(v)))
            except TypeError:
                pass
            try:
                out.append(("asc", all(a <= b for a, b in zip(v, v[1:]))))
                out.append(("desc", all(a >= b for a, b in zip(v, v[1:]))))
            except TypeError:
                pass
        if v and all(_num(x) for x in v):
            out.append(("hasneg", any(x < 0 for x in v)))
            out.append(("haszero", any(x == 0 for x in v)))
    elif isinstance(v, str):
        out += [("len1", len(v) == 1), ("upper", any(c.isupper() for c in v)),
                ("lower", any(c.islower() for c in v)), ("digit", any(c.isdigit() for c in v)),
                ("dblspace", "  " in v), ("edgespace", v[:1] == " " or v[-1:] == " "),
                ("punct", any(not c.isalnum() and not c.isspace() for c in v))]
    elif _num(v):
        out += [("neg", v < 0), ("zero", v == 0)]
        if isinstance(v, int):
            out.append(("odd", v % 2 == 1))
        elif math.isfinite(v):
            out.append(("nonint", v != int(v)))
    return out


def rel_preds(names, vals):
    """Relations between the arguments of one call: (label, holds?)."""
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


def __p(fsid, names, *vals):
    """Function entry: shape of each argument and relations between arguments."""
    for i, v in enumerate(vals):
        for lab, t in shape_preds(v):
            CUR[0].add((fsid, f"P|{i}|{lab}|{t}"))
    for lab, t in rel_preds(names, vals):
        CUR[0].add((fsid, f"R|{lab}|{t}"))


def output_preds(v):
    out = [("class|" + absval(v), True)] if absval(v) is not None else []
    out += [("pred|" + lab, t) for lab, t in shape_preds(v)]
    return out


def __d(scope, names, line, fresh=False):
    key = (id(sys._getframe(1)), scope)
    if fresh:
        DEFS[key] = {}
    ds = DEFS.setdefault(key, {})
    for name in names:
        ds[name] = line


def __u(scope, name, line, kind, v):
    ds = DEFS.get((id(sys._getframe(1)), scope), {})
    if name in ds and len(CUR[0]) < DU_LIMIT:
        CUR[0].add((-2, f"du|{scope}|{name}|{ds[name]}|{line}|{kind}"))
    return v


def __named(scope, name, line, v):
    DEFS.setdefault((id(sys._getframe(1)), scope), {})[name] = line
    return v


def __del(scope, names):
    ds = DEFS.get((id(sys._getframe(1)), scope), {})
    for name in names:
        ds.pop(name, None)


@contextlib.contextmanager
def __loop(sid):
    count = [0]
    try:
        yield count
    finally:
        CUR[0].add((sid, f"loop:{count[0]}"))


def __tick(count):
    count[0] += 1


def __it(sid, it):
    n = 0
    try:
        for x in it:
            n += 1
            yield x
    finally:
        CUR[0].add((sid, "iter:0" if n == 0 else "iter:1" if n == 1 else "iter:many"))
        CUR[0].add((sid, f"loop:{n}"))


HOOKS = {"__v": __v, "__c": __c, "__it": __it, "__p": __p, "__d": __d, "__u": __u, "__named": __named,
         "__del": __del, "__loop": __loop, "__tick": __tick}
SKIP_NAMES = set(dir(builtins))


class Inst(ast.NodeTransformer):
    def __init__(self):
        self.sites = []
        self.varsite = {}
        self.members = {}
        self.probes = {}
        self.scope, self.locals, self.usekind = None, set(), "c-use"
        self.cmpinfo = {}  # id(Compare node) -> per operand ("site", sid) | ("const", value)

    def site(self, line, kind, src):
        self.sites.append({"line": line, "kind": kind, "src": src})
        return len(self.sites) - 1

    def wrap(self, fn, sid, expr):
        return ast.Call(ast.Name(fn, ast.Load()), [ast.Constant(sid), expr], [])

    def vsite(self, line, name, kind="var"):
        k = (line, name, kind)
        if k not in self.varsite:
            self.varsite[k] = self.site(line, kind, name)
        return self.varsite[k]

    def visit_Name(self, node):
        if not isinstance(node.ctx, ast.Load) or node.id.startswith("__"):
            return node
        value = node
        if self.scope is not None and node.id in self.locals:
            value = ast.copy_location(ast.Call(ast.Name("__u", ast.Load()),
                [ast.Constant(self.scope), ast.Constant(node.id), ast.Constant(node.lineno),
                 ast.Constant(self.usekind), node], []), node)
        if node.id not in SKIP_NAMES:
            value = ast.copy_location(self.wrap("__v", self.vsite(node.lineno, node.id), value), node)
        return value

    def visit_Call(self, node):
        if not isinstance(node.func, ast.Name) or node.func.id in self.locals:
            node.func = self.visit(node.func)
        node.args = [self.visit(a) for a in node.args]
        for kw in node.keywords:
            kw.value = self.visit(kw.value)
        return node

    def _members(self, expr, start):
        names = {self.vsite(n.lineno, n.id) for n in ast.walk(expr) if isinstance(n, ast.Name)
                 and isinstance(n.ctx, ast.Load) and n.id not in SKIP_NAMES and not n.id.startswith("__")}
        ops = {i for i in range(start, len(self.sites)) if self.sites[i]["kind"] == "operand"}
        return sorted(names | ops)

    def _probes(self, expr):
        out = []
        for n in ast.walk(expr):
            info = self.cmpinfo.get(id(n))
            if not info:
                continue
            for a, b in zip(info, info[1:]):
                if a[0] == "site" and b[0] == "site":
                    out.append(("eqv", a[1], b[1]))
                elif a[0] == "site" and b[0] == "const":
                    out.append(("eqc", a[1], b[1]))
                elif a[0] == "const" and b[0] == "site":
                    out.append(("eqc", b[1], a[1]))
        return out

    def _cond(self, test):
        old = self.usekind
        self.usekind = "p-use"
        try:
            return self._condition(test)
        finally:
            self.usekind = old

    def _condition(self, test):
        src = ast.unparse(test)
        line = test.lineno
        if isinstance(test, ast.BoolOp):
            # members are paired per operand (short-circuit leaves the top-level condition's reads stale)
            vals = []
            for o in test.values:
                start, ln, s_ = len(self.sites), o.lineno, ast.unparse(o)
                mem = self._members(o, start)
                nv = self.visit(o)
                mem = sorted(set(mem) | {i for i in range(start, len(self.sites))
                                         if self.sites[i]["kind"] == "operand"})
                sid = self.site(ln, "subcond", s_)
                self.sites[sid]["decision_line"] = line
                self.members[sid] = mem
                self.probes[sid] = self._probes(o)
                vals.append(self.wrap("__c", sid, nv))
            test.values = vals
            return self.wrap("__c", self.site(line, "cond", src), test)
        start = len(self.sites)
        mem = self._members(test, start)
        t = self.visit(test)
        mem = sorted(set(mem) | {i for i in range(start, len(self.sites)) if self.sites[i]["kind"] == "operand"})
        sid = self.site(line, "cond", src)
        self.members[sid] = mem
        self.probes[sid] = self._probes(test)
        return self.wrap("__c", sid, t)

    def stmts(self, lst):
        out = []
        for s in lst:
            r = self.visit(s)
            out.extend(r if isinstance(r, list) else [r])
        return out

    def visit_If(self, node):
        node.test = self._cond(node.test)
        node.body = self.stmts(node.body)
        node.orelse = self.stmts(node.orelse)
        return node

    def loop_wrap(self, node, sid):
        token = f"__loop_count_{sid}"
        tick = ast.Expr(ast.Call(ast.Name("__tick", ast.Load()), [ast.Name(token, ast.Load())], []))
        ast.copy_location(tick, node)
        node.body.insert(0, tick)
        wrap = ast.With([ast.withitem(ast.Call(ast.Name("__loop", ast.Load()), [ast.Constant(sid)], []),
                                     ast.Name(token, ast.Store()))], [node])
        return ast.copy_location(wrap, node)

    def visit_While(self, node):
        sid = self.site(node.lineno, "loop", "while " + ast.unparse(node.test))
        node = self.visit_If(node)
        return self.loop_wrap(node, sid)

    def visit_IfExp(self, node):
        node.test = self._cond(node.test)
        node.body = self.visit(node.body)
        node.orelse = self.visit(node.orelse)
        return node

    def visit_comprehension(self, node):
        src = ast.unparse(node.iter)
        line = node.iter.lineno
        node.iter = self.wrap("__it", self.site(line, "loop", f"for {ast.unparse(node.target)} in {src}"),
                              self.visit(node.iter))
        node.ifs = [self._cond(c) for c in node.ifs]
        return node

    def visit_For(self, node):
        src = f"for {ast.unparse(node.target)} in {ast.unparse(node.iter)}"
        sid = self.site(node.lineno, "loop", src)
        node.iter = self.visit(node.iter)
        names = self.target_names(node.target)
        node.body = self.def_stmts(names, node.lineno) + self.stmts(node.body)
        node.orelse = self.stmts(node.orelse)
        return self.loop_wrap(node, sid)

    def target_names(self, target):
        return sorted({n.id for n in ast.walk(target) if isinstance(n, ast.Name)
                       and isinstance(n.ctx, (ast.Store, ast.Del)) and n.id in self.locals})

    def def_stmts(self, names, line, fresh=False):
        if self.scope is None or not names and not fresh:
            return []
        stmt = ast.Expr(ast.Call(ast.Name("__d", ast.Load()),
            [ast.Constant(self.scope), ast.Constant(tuple(names)), ast.Constant(line), ast.Constant(fresh)], []))
        stmt.lineno = stmt.end_lineno = line
        stmt.col_offset = stmt.end_col_offset = 0
        return [stmt]

    def visit_Delete(self, node):
        names = sorted({v for t in node.targets for v in self.target_names(t)})
        if self.scope is None or not names:
            return node
        stmt = ast.Expr(ast.Call(ast.Name("__del", ast.Load()),
                                [ast.Constant(self.scope), ast.Constant(tuple(names))], []))
        return [node, ast.copy_location(stmt, node)]

    def visit_NamedExpr(self, node):
        node.value = self.visit(node.value)
        if self.scope is not None and isinstance(node.target, ast.Name) and node.target.id in self.locals:
            node.value = ast.copy_location(ast.Call(ast.Name("__named", ast.Load()),
                [ast.Constant(self.scope), ast.Constant(node.target.id), ast.Constant(node.lineno), node.value], []), node)
        return node

    def visit_With(self, node):
        names = []
        for item in node.items:
            item.context_expr = self.visit(item.context_expr)
            if item.optional_vars:
                names += self.target_names(item.optional_vars)
        node.body = self.def_stmts(names, node.lineno) + self.stmts(node.body)
        return node

    def visit_ExceptHandler(self, node):
        node.body = self.def_stmts([node.name] if node.name else [], node.lineno) + self.stmts(node.body)
        return node

    def visit_Compare(self, node):
        raw = [node.left] + list(node.comparators)
        rsrc = [ast.unparse(x) for x in raw]
        new = [self.visit(x) for x in raw]
        out, info = [], []
        for o, n, rs in zip(raw, new, rsrc):
            if isinstance(o, ast.Constant):
                out.append(n)
                c = o.value
                info.append(("const", c) if isinstance(c, (int, float)) and not isinstance(c, bool) else ("other",))
            elif isinstance(o, ast.Name):
                out.append(n)
                info.append(("site", self.vsite(o.lineno, o.id)) if o.id not in SKIP_NAMES
                            and not o.id.startswith("__") else ("other",))
            else:
                sid = self.site(o.lineno, "operand", rs)
                out.append(self.wrap("__v", sid, n))
                info.append(("site", sid))
        node.left, node.comparators = out[0], out[1:]
        self.cmpinfo[id(node)] = info
        return node

    def visit_Assign(self, node):
        src = " = ".join(ast.unparse(t) for t in node.targets)
        node.targets = [self.visit(t) for t in node.targets]
        node.value = self.wrap("__v", self.site(node.lineno, "assign", src), self.visit(node.value))
        return [node] + self.def_stmts(sorted({v for t in node.targets for v in self.target_names(t)}), node.lineno)

    def visit_AnnAssign(self, node):
        if node.value is not None:
            node.value = self.wrap("__v", self.site(node.lineno, "assign", ast.unparse(node.target)),
                                   self.visit(node.value))
        return [node] + self.def_stmts(self.target_names(node.target), node.lineno) if node.value is not None else node

    def visit_AugAssign(self, node):
        node.value = self.visit(node.value)
        if isinstance(node.target, ast.Name):
            sid = self.site(node.lineno, "assign", node.target.id)
            after = ast.Expr(self.wrap("__v", sid, ast.Name(node.target.id, ast.Load())))
            ast.copy_location(after, node)
            before = ast.Expr(self.visit_Name(ast.copy_location(ast.Name(node.target.id, ast.Load()), node)))
            ast.copy_location(before, node)
            return [before, node, after] + self.def_stmts(self.target_names(node.target), node.lineno)
        return node

    def visit_Return(self, node):
        if node.value is not None:
            node.value = self.wrap("__v", self.site(node.lineno, "return", "return value"), self.visit(node.value))
        return node

    def _fn(self, node):
        old = self.scope, self.locals, self.usekind
        a = node.args
        params = [x.arg for x in a.posonlyargs + a.args + a.kwonlyargs]
        if a.vararg:
            params.append(a.vararg.arg)
        if a.kwarg:
            params.append(a.kwarg.arg)
        class Locals(ast.NodeVisitor):
            def __init__(self): self.names = set(params)
            def visit_Name(self, n):
                if isinstance(n.ctx, ast.Store): self.names.add(n.id)
            def visit_ExceptHandler(self, n):
                if n.name: self.names.add(n.name)
                self.generic_visit(n)
            def visit_FunctionDef(self, n): self.names.add(n.name)
            visit_AsyncFunctionDef = visit_FunctionDef
            def visit_ClassDef(self, n): self.names.add(n.name)
            def visit_Lambda(self, n): pass
            def visit_ListComp(self, n): pass
            visit_SetComp = visit_DictComp = visit_GeneratorExp = visit_ListComp
        loc = Locals()
        for stmt in node.body: loc.visit(stmt)
        self.scope, self.locals, self.usekind = node.lineno, loc.names, "c-use"
        node.body = self.stmts(node.body)
        stm = self.def_stmts(params, node.lineno, True) + [ast.Expr(self.wrap("__v", self.vsite(node.lineno, p, "param"), ast.Name(p, ast.Load())))
               for p in params]
        if params:
            fsid = self.site(node.lineno, "entry", node.name)
            self.sites[fsid]["params"] = params
            stm.append(ast.Expr(ast.Call(ast.Name("__p", ast.Load()),
                                         [ast.Constant(fsid), ast.Constant(tuple(params))]
                                         + [ast.Name(p, ast.Load()) for p in params], [])))
        k = 1 if (node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant)
                  and isinstance(node.body[0].value.value, str)) else 0
        node.body[k:k] = stm
        self.scope, self.locals, self.usekind = old
        return node

    def visit_FunctionDef(self, node):
        node.decorator_list = [self.visit(d) for d in node.decorator_list]
        return self._fn(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Lambda(self, node):
        old, self.scope = self.scope, None
        node.body = self.visit(node.body)
        self.scope = old
        return node

    def visit_ListComp(self, node):
        old, self.scope = self.scope, None
        node = self.generic_visit(node)
        self.scope = old
        return node

    visit_SetComp = visit_DictComp = visit_GeneratorExp = visit_ListComp


def instrument(src):
    tree = ast.parse(src)
    ins = Inst()
    tree = ins.visit(tree)
    ast.fix_missing_locations(tree)
    MEMBERS.clear()
    MEMBERS.update(ins.members)
    PROBES.clear()
    PROBES.update(ins.probes)
    for sid, mem in ins.members.items():
        ins.sites[sid]["members"] = mem
    for sid, pr in ins.probes.items():
        ins.sites[sid]["probes"] = pr
    return compile(tree, "<put>", "exec"), ins.sites


def load_module(code_or_src, extra=None, filename="<put>"):
    g = {"__name__": "__put__"}
    if extra:
        g.update(extra)
    if isinstance(code_or_src, str):
        code_or_src = compile(code_or_src, filename, "exec")
    with contextlib.redirect_stdout(io.StringIO()):
        exec(code_or_src, g)
    return g


BASE_STEP_LIMIT = 5_000_000


def run_base(fn, base_test, T=120, record=True, ns=None):
    """Run HumanEval's check(candidate). Returns (recorded (args, kwargs) list, True or exception name)."""
    REC = []

    def cand(*a, **k):
        if record:
            REC.append((dcopy(a), dcopy(k)))
        return fn(*a, **k)

    g = dict(ns or {})
    g["__name__"] = "__base__"
    random.seed(0)
    n = [0]

    def tr(frame, event, arg):  # whole check under a step budget, so survive/killed does not depend on load
        if event == "line":
            n[0] += 1
            if n[0] > BASE_STEP_LIMIT:
                raise Timeout()
        return tr

    sys.settrace(tr)
    try:
        with contextlib.redirect_stdout(io.StringIO()), alarm(T):
            exec(base_test, g)
            g["check"](cand)
        ok = True
    except BaseException as e:
        ok = type(e).__name__
    finally:
        sys.settrace(None)
    return REC, ok


STEP_LIMIT = 200_000  # executed lines per call; deterministic, unlike a wall-clock timeout


def call(fn, args, T=20.0, lines=None, filename="<put>"):
    """Call fn on a deep copy of (args, kwargs) under a step budget (counted line events).

    Returns (status, value): status is "ok", "timeout" (step budget, or the wall-clock safety net T for work
    done inside C code) or the exception name. If `lines` is a set, the executed lines of `filename` are added.
    """
    a, k = dcopy(args[0]), dcopy(args[1])
    n = [0]

    def tr(frame, event, arg):
        if event == "line":
            n[0] += 1
            if n[0] > STEP_LIMIT:
                raise Timeout()
            if lines is not None and frame.f_code.co_filename == filename:
                lines.add(frame.f_lineno)
        return tr

    sys.settrace(tr)
    try:
        with contextlib.redirect_stdout(io.StringIO()), alarm(T):
            return "ok", fn(*a, **k)
    except Timeout:
        return "timeout", None
    except BaseException as e:
        return type(e).__name__, None
    finally:
        sys.settrace(None)


def trace(ifn, args, T=20.0):
    """One call of the instrumented function: (cells (site, class), executed lines, status, value)."""
    CUR[0] = set()
    LAST.clear()
    LASTVAL.clear()
    DEFS.clear()
    lines = set()
    st, val = call(ifn, args, T, lines)
    if st == "ok":
        for key, holds in output_preds(val):
            CUR[0].add((-1, f"output|{key}|{holds}"))
    return CUR[0], lines, st, val


def same(a, b):
    try:
        r = a == b
        if isinstance(r, bool):
            return r
        return bool(r.all())
    except Exception:
        return False


def fact_hit(f, tr, pout=None, mout=None, *, args=None, valid=None):
    if f['kind'] == 'BEHAV':
        from .behav_facts import input_hit
        return input_hit(f, args, valid)
    if 'input_class' in f and args is not None:
        from . import spec_facts
        c = f['input_class']
        return c['param'] < len(args[0]) and spec_facts.in_class(c['cls'], args[0][c['param']])
    cells, lines, pst, pval = tr
    if "all_cells" in f:
        return all(tuple(c) in cells for c in f["all_cells"])
    if "loop_max" in f:
        sid, bound = f["loop_max"]
        return any(s == sid and isinstance(c, str) and c.startswith("loop:")
                   and int(c[5:]) > bound for s, c in cells)
    if "cell" in f or "cells" in f:
        return any(tuple(c) in cells for c in f.get("cells", [f.get("cell")]) if c is not None)
    if f["kind"] == "STMT":
        return bool(set(f["lines"]) & lines)
    if f["kind"] == "MUTANT" and mout is not None:
        ps, pv = pout if pout is not None else (pst, pval)
        ms, mv = mout
        return ms != ps or ms == "ok" and not same(mv, pv)
    return False
