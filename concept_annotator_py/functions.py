#!/usr/bin/env python3
"""Function-level C1-C8 concept tags for real-world Python code (stdlib ``ast`` only).

Unlike ``annotator.py`` (TestEval records, algorithmic tags), this module takes the
source of one function or method, e.g. a ``text`` entry of an Agentless/CoSIL repo
structure, and returns bug-oriented concepts with evidence lines, in the shared
vocabulary used across this repo:

  C1 null/None   C2 empty/blank   C3 boundary/index/length   C4 error contract
  C5 format/escape/parse   C6 numeric   C7 chars/case/encoding/locale   C8 state/mutation

Facts are syntactic heuristics: they say where a concept is handled, not that it is
handled correctly.

usage: python3 -m concept_annotator_py.functions selftest
       python3 -m concept_annotator_py.functions stats <dir>   (tag rate per concept)
"""

from __future__ import annotations

import ast
import sys
import textwrap
from pathlib import Path
from typing import Any

CONCEPTS = {
    "C1": "null/None", "C2": "empty/blank", "C3": "boundary/index/length", "C4": "error contract",
    "C5": "format/escape/parse", "C6": "numeric", "C7": "chars/case/encoding/locale", "C8": "state/mutation",
}
_EMPTY = ("", b"")
_STR_METHODS = {"split", "rsplit", "partition", "rpartition", "replace", "strip", "lstrip", "rstrip",
                "startswith", "endswith", "splitlines", "expandtabs", "zfill", "ljust", "rjust", "center"}
_PARSE_WORDS = ("escape", "quote", "parse", "serial", "dumps", "loads", "format_", "literal_eval")
_NUMERIC_CALLS = {"round", "int", "float", "abs", "divmod", "pow", "Decimal", "Fraction", "complex"}
_NUMERIC_ROOTS = ("math.", "cmath.", "decimal.", "fractions.", "numpy.", "np.", "statistics.")
_CASE = {"lower", "upper", "casefold", "title", "capitalize", "swapcase"}
_CHAR_PRED = {"isalpha", "isdigit", "isalnum", "isdecimal", "isnumeric", "isidentifier", "isprintable",
              "isascii", "isupper", "islower", "istitle"}
_MUTATORS = {"append", "extend", "insert", "pop", "popitem", "remove", "clear", "update", "setdefault",
             "add", "discard", "sort", "reverse"}
_MESSAGE_SINKS = ("log", "logger", "logging", "warnings", "print", "_")  # call roots whose strings are messages


def annotate_function(source: str, line_offset: int = 0) -> dict[str, Any]:
    """Concept facts for the first function/method defined in ``source``.

    ``line_offset`` is added to evidence lines (pass ``start_line - 1`` to get file lines).
    Returns {"name", "facts": [{"concept", "kind", "line", "detail"}], "concepts": sorted ids}
    or {"error": ...} when the code does not parse (e.g. Python 2).
    """
    try:
        tree = ast.parse(textwrap.dedent(source))
    except SyntaxError as exc:
        return {"name": None, "facts": [], "concepts": [], "error": f"SyntaxError: {exc.msg}"}
    func = next((n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))), None)
    if func is None:
        return {"name": None, "facts": [], "concepts": [], "error": "no function definition"}
    facts = _Collector(func, line_offset).run()
    return {"name": func.name, "facts": facts, "concepts": sorted({f["concept"] for f in facts})}


def render_tags(annotation: dict[str, Any], max_details: int = 2, width: int = 120) -> str:
    """Compact one-line rendering, e.g. ``C1 None-check(value) · C4 raises ValueError``."""
    by_concept: dict[str, list[str]] = {}
    for fact in annotation.get("facts", []):
        details = by_concept.setdefault(fact["concept"], [])
        if fact["detail"] not in details:
            details.append(fact["detail"])
    # every concept id always survives; details shrink until the line fits (ids only as the last resort)
    for keep, limit in ((max_details, 60), (1, 28), (1, 16), (0, 0)):
        parts = []
        for cid in sorted(by_concept):
            details = [_short(d, limit) for d in by_concept[cid][:keep]]
            more = " …" if keep and len(by_concept[cid]) > keep else ""
            parts.append(f"{cid} {', '.join(details)}{more}".rstrip())
        text = " · ".join(parts)
        if len(text) <= width:
            return text
    return text


class _Collector:
    def __init__(self, func: ast.FunctionDef | ast.AsyncFunctionDef, offset: int):
        self.func, self.offset, self.facts = func, offset, []
        args = func.args
        self.params = {a.arg for a in (*args.posonlyargs, *args.args, *args.kwonlyargs)} - {"self", "cls"}
        if args.vararg:
            self.params.add(args.vararg.arg)
        if args.kwarg:
            self.params.add(args.kwarg.arg)
        self.message_nodes = self._message_nodes()

    def add(self, concept: str, kind: str, node: ast.AST, detail: str) -> None:
        line = getattr(node, "lineno", self.func.lineno) + self.offset
        if not any(f["concept"] == concept and f["detail"] == detail for f in self.facts):
            self.facts.append({"concept": concept, "kind": kind, "line": line, "detail": _short(detail)})

    def run(self) -> list[dict[str, Any]]:
        self._signature()
        returns_value = any(isinstance(n, ast.Return) and n.value is not None for n in self._walk())
        for node in self._walk():
            if isinstance(node, ast.Compare):
                self._compare(node)
            elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not) and self._is_test(node):
                if isinstance(node.operand, (ast.Name, ast.Attribute, ast.Subscript)):
                    self.add("C2", "truthiness", node, f"not {_src(node.operand)}")
            elif isinstance(node, ast.Subscript):
                self._subscript(node)
            elif isinstance(node, ast.Raise) and node.exc is not None:
                self.add("C4", "raise", node, f"raises {_exc_name(node.exc)}")
            elif isinstance(node, ast.ExceptHandler):
                self.add("C4", "except", node, f"catches {_src(node.type) if node.type else 'everything'}")
            elif isinstance(node, ast.Assert):
                self.add("C4", "assert", node, f"assert {_src(node.test)}")
            elif isinstance(node, ast.Return) and node.value is None and returns_value:
                self.add("C1", "returns-none", node, "bare return (None) on some path")
            elif isinstance(node, ast.Return) and _is_none(node.value):
                self.add("C1", "returns-none", node, "returns None")
            elif isinstance(node, ast.BinOp):
                self._binop(node)
            elif isinstance(node, ast.Call):
                self._call(node)
            elif isinstance(node, ast.JoinedStr) and node not in self.message_nodes:
                self.add("C5", "format", node, "f-string")
            elif isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign, ast.Delete)):
                self._mutation(node)
            elif isinstance(node, (ast.Global, ast.Nonlocal)):
                self.add("C8", "global", node, f"{type(node).__name__.lower()} {', '.join(node.names)}")
            elif isinstance(node, (ast.Yield, ast.YieldFrom)):
                self.add("C8", "generator", node, "generator (yields)")
        self._unchecked_none()
        return sorted(self.facts, key=lambda f: (f["concept"], f["line"]))

    def _unchecked_none(self) -> None:
        """A parameter that may be None (None default / Optional) but is never tested: a likely C1 gap."""
        maybe_none = {f["detail"].split("=")[0].split(":")[0] for f in self.facts if f["kind"] in ("none-default", "optional")}
        checked: set[str] = set()
        for node in self._walk():
            tests = []
            if isinstance(node, (ast.If, ast.While, ast.IfExp, ast.Assert)):
                tests = [node.test]
            elif isinstance(node, ast.BoolOp):
                tests = node.values
            elif isinstance(node, ast.Call) and _call_name(node) in {"isinstance", "callable", "bool"}:
                tests = node.args[:1]
            checked |= {n.id for t in tests for n in ast.walk(t) if isinstance(n, ast.Name)}
        for name in sorted(maybe_none - checked):
            self.add("C1", "unchecked-none", self.func, f"{name} may be None, never checked")

    # signature: defaults, annotations, decorators
    def _signature(self) -> None:
        args = self.func.args
        positional = [*args.posonlyargs, *args.args]
        pairs = list(zip(positional[len(positional) - len(args.defaults):], args.defaults))
        pairs += [(a, d) for a, d in zip(args.kwonlyargs, args.kw_defaults) if d is not None]
        for arg, default in pairs:
            if _is_none(default):
                self.add("C1", "none-default", default, f"{arg.arg}=None")
            elif isinstance(default, (ast.List, ast.Dict, ast.Set)):
                self.add("C8", "mutable-default", default, f"mutable default {arg.arg}={_src(default)}")
        for arg in (*positional, *args.kwonlyargs):
            if arg.annotation is not None and "Optional" in _src(arg.annotation):
                self.add("C1", "optional", arg, f"{arg.arg}: Optional")
        for deco in self.func.decorator_list:
            name = _src(deco)
            if "cache" in name or "memo" in name:
                self.add("C8", "cached", deco, f"@{name}")

    def _compare(self, node: ast.Compare) -> None:
        operands = [node.left, *node.comparators]
        ops = node.ops
        if any(_is_none(o) for o in operands):
            self.add("C1", "none-check", node, f"None-check {_src(node)}")
        if any(isinstance(o, ast.Constant) and o.value in _EMPTY for o in operands) or any(
            isinstance(o, (ast.List, ast.Tuple, ast.Dict, ast.Set)) and not _elts(o) for o in operands
        ):
            self.add("C2", "empty-check", node, f"empty-check {_src(node)}")
        has_len = any(_call_named(o, "len") for o in operands)
        zero = any(isinstance(o, ast.Constant) and o.value in (0, 1) and not isinstance(o.value, bool) for o in operands)
        if has_len and zero and all(isinstance(op, (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE)) for op in ops):
            self.add("C2", "empty-check", node, f"empty-check {_src(node)}")
        elif any(isinstance(op, (ast.Lt, ast.LtE, ast.Gt, ast.GtE)) for op in ops) and (
            has_len or any(_plus_minus_one(o) for o in operands)
        ):
            self.add("C3", "bound", node, f"bound {_src(node)}")

    def _subscript(self, node: ast.Subscript) -> None:
        index = node.slice
        if isinstance(index, ast.Slice):
            if any(b is not None and not (isinstance(b, ast.Constant) and b.value in (0, None)) for b in
                   (index.lower, index.upper)):
                self.add("C3", "slice", node, f"slice {_src(node)}")
        elif _plus_minus_one(index) or (isinstance(index, ast.UnaryOp) and isinstance(index.op, ast.USub)):
            self.add("C3", "index", node, f"index {_src(node)}")

    def _binop(self, node: ast.BinOp) -> None:
        if isinstance(node.op, ast.Mod) and isinstance(node.left, (ast.Constant, ast.JoinedStr)) and isinstance(
            getattr(node.left, "value", None), str
        ):
            if node not in self.message_nodes:
                self.add("C5", "format", node, "%-format")
        elif isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)):
            self.add("C6", "arith", node, f"{type(node.op).__name__.lower()} {_src(node)}")

    def _call(self, node: ast.Call) -> None:
        name = _call_name(node)
        leaf = name.rsplit(".", 1)[-1]
        if name in {"getattr"} and len(node.args) == 3 and _is_none(node.args[2]):
            self.add("C1", "none-default", node, f"{_src(node)} (None fallback)")
        if name == "range" and any(_plus_minus_one(a) or _call_named(a, "len") for a in node.args):
            self.add("C3", "range", node, f"range bound {_src(node)}")
        if name in {"min", "max"} and any(_call_named(a, "len") for a in node.args):
            self.add("C3", "clamp", node, f"clamp {_src(node)}")
        if name.startswith("re.") or name.startswith("regex."):
            self.add("C5", "regex", node, f"regex {name}")
            if any(f in _src(node) for f in ("IGNORECASE", "re.I", "UNICODE", "re.U", "ASCII", "re.A")):
                self.add("C7", "regex-flags", node, "regex case/unicode flags")
        if leaf == "format" and isinstance(node.func, ast.Attribute) and node not in self.message_nodes:
            self.add("C5", "format", node, "str.format")
        if any(w in leaf.lower() for w in _PARSE_WORDS):
            self.add("C5", "parse", node, f"{leaf}()")
        if isinstance(node.func, ast.Attribute) and leaf in _STR_METHODS:
            self.add("C5", "string-op", node, f".{leaf}()")
            if leaf in {"strip", "lstrip", "rstrip"} and self._is_test(node):
                self.add("C2", "blank-check", node, f"blank-check {_src(node)}")
        if leaf == "isspace":
            self.add("C2", "blank-check", node, "isspace()")
        if name in _NUMERIC_CALLS or name.startswith(_NUMERIC_ROOTS):
            self.add("C6", "numeric-call", node, f"{name}()")
        if name == "float" and node.args and isinstance(node.args[0], ast.Constant) and str(node.args[0].value).lower() in {
            "inf", "-inf", "nan"
        }:
            self.add("C6", "numeric-limit", node, f"float({node.args[0].value!r})")
        if isinstance(node.func, ast.Attribute) and leaf in _CASE:
            self.add("C7", "case", node, f".{leaf}()")
        if isinstance(node.func, ast.Attribute) and leaf in _CHAR_PRED:
            self.add("C7", "char-class", node, f".{leaf}()")
        if name in {"ord", "chr"} or name.startswith(("unicodedata.", "locale.")):
            self.add("C7", "chars", node, f"{name}()")
        if isinstance(node.func, ast.Attribute) and leaf in {"encode", "decode"}:
            self.add("C7", "encoding", node, f".{leaf}({', '.join(_src(a) for a in node.args)})")
        if name in {"setattr", "delattr"}:
            self.add("C8", "setattr", node, f"{name}()")
        if name.startswith("warnings.warn"):
            self.add("C4", "warn", node, "warnings.warn")
        if isinstance(node.func, ast.Attribute) and leaf in _MUTATORS:
            root = _root_name(node.func.value)
            if root in self.params:
                self.add("C8", "mutates-param", node, f"mutates param {root}.{leaf}()")

    def _mutation(self, node: ast.AST) -> None:
        targets = node.targets if isinstance(node, (ast.Assign, ast.Delete)) else [node.target]
        for target in targets:
            for t in (target.elts if isinstance(target, ast.Tuple) else [target]):
                if isinstance(t, ast.Attribute) and _root_name(t) in {"self", "cls"}:
                    self.add("C8", "sets-attr", node, f"sets {_src(t)}")
                elif isinstance(t, (ast.Subscript, ast.Attribute)) and _root_name(t) in self.params:
                    self.add("C8", "mutates-param", node, f"mutates param {_src(t)}")

    def _is_test(self, node: ast.AST) -> bool:
        """True when node sits in the condition of an if/while/assert/ternary/comprehension filter."""
        for parent in self._walk():
            tests = []
            if isinstance(parent, (ast.If, ast.While, ast.IfExp, ast.Assert)):
                tests = [parent.test]
            elif isinstance(parent, ast.comprehension):
                tests = parent.ifs
            if any(node is sub for t in tests for sub in ast.walk(t)):
                return True
        return False

    def _message_nodes(self) -> set[ast.AST]:
        """String-building nodes that only produce messages (raise text, logging, warnings, print)."""
        nodes: set[ast.AST] = set()
        for node in self._walk():
            owner = None
            if isinstance(node, ast.Raise) and node.exc is not None:
                owner = node.exc
            elif isinstance(node, ast.Call) and _call_name(node).split(".", 1)[0] in _MESSAGE_SINKS:
                owner = node
            if owner is not None:
                nodes.update(sub for sub in ast.walk(owner) if isinstance(sub, (ast.JoinedStr, ast.BinOp, ast.Call)))
        return nodes

    def _walk(self):
        return ast.walk(self.func)


def _src(node: ast.AST | None) -> str:
    return ast.unparse(node) if node is not None else ""


def _short(text: str, limit: int = 60) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _is_none(node: ast.AST | None) -> bool:
    return isinstance(node, ast.Constant) and node.value is None


def _elts(node: ast.AST) -> list:
    return node.keys if isinstance(node, ast.Dict) else node.elts


def _call_name(node: ast.Call) -> str:
    parts, cur = [], node.func
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
    return ".".join(reversed(parts))


def _call_named(node: ast.AST, name: str) -> bool:
    return isinstance(node, ast.Call) and _call_name(node) == name


def _root_name(node: ast.AST) -> str:
    while isinstance(node, (ast.Attribute, ast.Subscript, ast.Call)):
        node = node.func if isinstance(node, ast.Call) else node.value
    return node.id if isinstance(node, ast.Name) else ""


def _plus_minus_one(node: ast.AST) -> bool:
    return isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub)) and any(
        isinstance(side, ast.Constant) and side.value == 1 for side in (node.left, node.right)
    )


def _exc_name(node: ast.AST) -> str:
    return _call_name(node) if isinstance(node, ast.Call) else _src(node)


def iter_functions(path: Path):
    """Yield (qualified name, source, start_line) for every function/method in a file."""
    try:
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
    except (SyntaxError, UnicodeDecodeError, ValueError):
        return
    lines = text.splitlines()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start = min([d.lineno for d in node.decorator_list] + [node.lineno])
            yield node.name, "\n".join(lines[start - 1: node.end_lineno]), start


def stats(root: str) -> dict[str, Any]:
    """Share of functions tagged with each concept: a concept on ~every function cannot discriminate."""
    total, tagged, errors, untagged = 0, {c: 0 for c in CONCEPTS}, 0, 0
    base = Path(root)
    for path in [base] if base.is_file() else sorted(base.rglob("*.py")):
        for _, source, start in iter_functions(path):
            ann = annotate_function(source, start - 1)
            total += 1
            errors += "error" in ann
            untagged += not ann["concepts"]
            for c in ann["concepts"]:
                tagged[c] += 1
    return {"functions": total, "errors": errors, "untagged": round(untagged / max(1, total), 3),
            "rate": {c: round(n / max(1, total), 3) for c, n in tagged.items()}}


def selftest() -> None:
    src = '''
    @functools.lru_cache(maxsize=None)
    def parse(self, text: Optional[str] = None, items=[], *, sep=","):
        """Docstring with a {placeholder} is not formatting."""
        if text is None or not text.strip():
            return None
        if len(items) == 0 and text == "":
            raise ValueError(f"empty {text}")
        if not items:
            items = [text]
        try:
            n = int(text[1:]) / len(items)
        except (TypeError, ZeroDivisionError):
            logger.warning("bad %s" % text)
            return
        for i in range(len(items) - 1):
            if i + 1 < len(items) and items[i + 1] > n:
                items.append(text.lower())
        self.count += 1
        return re.sub(r"\\s+", sep, text).encode("utf-8")
    '''
    ann = annotate_function(src, line_offset=100)
    kinds = {(f["concept"], f["kind"]) for f in ann["facts"]}
    expect = {
        ("C1", "none-default"), ("C1", "optional"), ("C1", "none-check"), ("C1", "returns-none"),
        ("C2", "truthiness"), ("C2", "blank-check"), ("C2", "empty-check"),
        ("C3", "slice"), ("C3", "range"), ("C3", "index"), ("C3", "bound"),
        ("C4", "raise"), ("C4", "except"),
        ("C5", "regex"), ("C5", "string-op"),
        ("C6", "arith"), ("C6", "numeric-call"),
        ("C7", "case"), ("C7", "encoding"),
        ("C8", "cached"), ("C8", "mutable-default"), ("C8", "mutates-param"), ("C8", "sets-attr"),
    }
    missing = expect - kinds
    assert not missing, f"missing facts: {sorted(missing)}"
    assert ann["name"] == "parse" and ann["concepts"] == [f"C{i}" for i in range(1, 9)], ann["concepts"]
    # messages are not formatting: f-string in raise and %-format in logger must not create C5 format facts
    assert not any(f["kind"] == "format" for f in ann["facts"]), [f for f in ann["facts"] if f["kind"] == "format"]
    raise_line = next(f["line"] for f in ann["facts"] if f["kind"] == "raise")
    assert raise_line == 100 + 8, raise_line  # offset applied; `raise` is line 8 of the dedented source (line 1 is blank)
    plain = annotate_function("def add(a, b):\n    return a + b\n")
    assert plain["facts"] == [] and render_tags(plain) == ""
    assert annotate_function("print 'py2'\n")["error"].startswith("SyntaxError")
    line = render_tags(ann, max_details=1)
    ids = [part.split(" ", 1)[0] for part in line.split(" · ")]
    assert ids == [f"C{i}" for i in range(1, 9)] and len(line) <= 120, line  # ids never dropped
    one = render_tags(annotate_function("def g(x=None):\n    if x is None:\n        raise TypeError('x')\n"))
    assert one == "C1 x=None, None-check x is None · C4 raises TypeError", one
    assert annotate_function("def f(x):\n    return x[0]\n")["facts"] == []  # x[0] is not off-by-one-prone
    gap = annotate_function("def h(a, b=None, c=None):\n    if c:\n        a += 1\n    return a + b.count\n")
    assert [f["detail"] for f in gap["facts"] if f["kind"] == "unchecked-none"] == ["b may be None, never checked"], gap
    print("selftest ok:", len(ann["facts"]), "facts;", render_tags(ann, max_details=1))


if __name__ == "__main__":
    if sys.argv[1:2] == ["stats"]:
        import json
        print(json.dumps(stats(sys.argv[2]), indent=1))
    else:
        selftest()
