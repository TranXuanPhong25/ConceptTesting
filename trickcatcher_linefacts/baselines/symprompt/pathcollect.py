"""SymPrompt Step I (paper Section 3.2): approximate path constraints from the focal method's AST.

Reimplementation from the paper's description (no official code). Preorder traversal of the focal method;
every branch and loop condition is recorded on each path (inverted when the branch is not taken); a path
that reaches `return` is recorded with its return expression (3.2.1). After every branching statement the
live path set is minimized with the paper's Algorithm 5a (3.2.2), which keeps a path only if it contains a
branch constraint not yet in the linearized constraint set, so k sequential if/else give at most k+1 paths.
Conditions are kept as source expressions (no symbolic resolution), as in the paper.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Constraint:
    key: str      # branch identity: line:col:polarity (the same text at two places is two branches)
    text: str


@dataclass
class Path:
    constraints: tuple = ()
    end: str = 'end'            # 'return' | 'raise' | 'end' (fell off the end of the method)
    returns: str | None = None  # return-value expression (only for 'return' paths, paper 3.4)

    def keys(self):
        return {c.key for c in self.constraints}

    def as_dict(self):
        return dict(constraints=[c.text for c in self.constraints], keys=[c.key for c in self.constraints],
                    end=self.end, returns=self.returns)


def _neg(expr):
    if isinstance(expr, ast.UnaryOp) and isinstance(expr.op, ast.Not):
        return ast.unparse(expr.operand)
    return ast.unparse(ast.UnaryOp(op=ast.Not(), operand=expr))


def _const_truth(expr):
    if isinstance(expr, ast.Constant):
        return bool(expr.value)
    return None


def minimize(paths):
    """Paths are live constraint tuples or recorded Path objects. Paper Algorithm 5a (the figure's set 'intersection' is read as union, as the text describes)."""
    seen, kept = set(), []
    for p in paths:
        keys = p.keys() if isinstance(p, Path) else {c.key for c in p}
        if keys - seen:
            kept.append(p)
            seen |= keys
    if paths and not kept:      # e.g. a single unconstrained path: one path must survive
        kept.append(paths[0])
    return kept


class _Loop:
    def __init__(self):
        self.breaks, self.continues = [], []


class Collector:
    def __init__(self):
        self.done = []
        self.loops = []

    def run(self, fn):
        live = self.block(fn.body, [()])
        for p in live:
            self.done.append(Path(p, 'end', None))
        return self.done

    def block(self, stmts, live):
        for s in stmts:
            if not live:
                break
            live = self.stmt(s, live)
        return live

    @staticmethod
    def _c(node, polarity, text):
        return Constraint(f'{node.lineno}:{node.col_offset}:{polarity}', text)

    def _branch(self, node, test, body, orelse, live):
        truth = _const_truth(test)
        out = []
        if truth is not False:
            add = () if truth is True else (self._c(node, 'T', ast.unparse(test)),)
            out += self.block(body, [p + add for p in live])
        if truth is not True:
            add = () if truth is False else (self._c(node, 'F', _neg(test)),)
            out += self.block(orelse, [p + add for p in live])
        return minimize(out)

    def _loop(self, node, enter, skip, live):
        ctx = _Loop()
        self.loops.append(ctx)
        entered = [p + ((enter,) if enter else ()) for p in live]
        body_out = self.block(node.body, entered)
        self.loops.pop()
        skipped = [p + ((skip,) if skip else ()) for p in live] if skip is not False else []
        normal = skipped + body_out + ctx.continues   # one-iteration approximation of the loop
        after = self.block(node.orelse, normal) + ctx.breaks
        return minimize(after)

    def stmt(self, s, live):
        if isinstance(s, ast.Return):
            value = ast.unparse(s.value) if s.value is not None else 'None'
            self.done += [Path(p, 'return', value) for p in live]
            return []
        if isinstance(s, ast.Raise):
            self.done += [Path(p, 'raise', None) for p in live]
            return []
        if isinstance(s, ast.If):
            return self._branch(s, s.test, s.body, s.orelse, live)
        if isinstance(s, ast.While):
            truth = _const_truth(s.test)
            enter = None if truth is True else self._c(s, 'T', ast.unparse(s.test))
            skip = False if truth is True else self._c(s, 'F', _neg(s.test))
            return self._loop(s, enter, skip, live)
        if isinstance(s, (ast.For, ast.AsyncFor)):
            enter = self._c(s, 'T', f'{ast.unparse(s.target)} in {ast.unparse(s.iter)}')
            skip = self._c(s, 'F', _neg(s.iter))
            return self._loop(s, enter, skip, live)
        if isinstance(s, (ast.Break, ast.Continue)):
            if self.loops:
                (self.loops[-1].breaks if isinstance(s, ast.Break) else self.loops[-1].continues).extend(live)
            return []
        if isinstance(s, (ast.With, ast.AsyncWith)):
            return self.block(s.body, live)
        if isinstance(s, ast.Try) or type(s).__name__ == 'TryStar':
            body_out = self.block(s.body, live)
            out = self.block(s.orelse, body_out)
            for h in s.handlers:
                exc = ast.unparse(h.type) if h.type is not None else 'Exception'
                c = Constraint(f'{h.lineno}:{h.col_offset}:H', f'the try block raises {exc}')
                out += self.block(h.body, [p + (c,) for p in live])
            out = self.block(s.finalbody, out) if s.finalbody else out
            return minimize(out)
        if type(s).__name__ == 'Match':
            subject = ast.unparse(s.subject)
            out, wildcard = [], False
            for case in s.cases:
                text = f'{subject} matches {ast.unparse(case.pattern)}'
                if case.guard is not None:
                    text += f' and {ast.unparse(case.guard)}'
                if isinstance(case.pattern, ast.MatchAs) and case.pattern.pattern is None and case.guard is None:
                    wildcard = True
                c = Constraint(f'{case.pattern.lineno}:{case.pattern.col_offset}:M', text)
                out += self.block(case.body, [p + (c,) for p in live])
            if not wildcard:
                c = Constraint(f'{s.lineno}:{s.col_offset}:N', f'{subject} matches no case')
                out += [p + (c,) for p in live]
            return minimize(out)
        # Nested defs/classes are separate methods; plain statements add no constraint.
        return live


def collect(fn):
    """All recorded paths of a FunctionDef, in preorder."""
    return Collector().run(fn)


def select(paths, budget):
    """Budget adaptation (not in the paper, which prompts every collected path): first the paths that add a
    branch constraint not yet covered (Algorithm 5a over the recorded set, preorder), then the rest in
    preorder, truncated to `budget` prompts."""
    basis = minimize(paths)
    ids = {id(p) for p in basis}
    ordered = basis + [p for p in paths if id(p) not in ids]
    return ordered[:budget]


# ------------------------------------------------------------------ focal method
def focal(put_src, entry):
    """(focal FunctionDef, focal ClassDef or None, wrapper FunctionDef or None, module tree).

    A thin module-level wrapper `def f(*a): return Cls().method(...)` (the held-out VibePass format) is
    resolved to the class method it calls; the wrapper stays the function the tests call."""
    tree = ast.parse(put_src)
    top = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
    fn = top.get(entry)
    if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
        raise ValueError(f'entry {entry} is not a module-level function')
    body = fn.body[1:] if fn.body and isinstance(fn.body[0], ast.Expr) and isinstance(getattr(fn.body[0], 'value', None), ast.Constant) \
        and isinstance(fn.body[0].value.value, str) else fn.body
    if len(body) == 1 and isinstance(body[0], ast.Return) and isinstance(body[0].value, ast.Call):
        call = body[0].value.func
        if isinstance(call, ast.Attribute) and isinstance(call.value, ast.Call) and isinstance(call.value.func, ast.Name):
            cls = top.get(call.value.func.id)
            if isinstance(cls, ast.ClassDef):
                method = next((n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == call.attr), None)
                if method is not None:
                    return method, cls, fn, tree
    return fn, None, None, tree
