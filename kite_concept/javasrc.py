"""Java method-boundary localization used by the deterministic task-manifest rule.

KITE's paper does not publish its Java parser. This module uses ``javalang`` (a real
Java grammar, not a lexical heuristic) to find every *named* method/constructor
declaration in a compilation unit together with its precise source line span, and
to map a changed source line to the smallest enclosing named method.

"Named" excludes methods declared inside an anonymous class body (``new X() { ... }``)
or an enum-constant body, because those cannot be referenced as a stable focal method
across the buggy/fixed versions. A change located inside such a body is attributed to
the nearest enclosing named method instead (KITE's "stable localization"), which falls
out for free here: a named method's line span already contains any anonymous body
nested lexically inside it, so anonymous methods are simply excluded from the
candidate list before the smallest-enclosing-span lookup.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import javalang

_ANONYMOUS_ANCESTORS = frozenset({"ClassCreator", "EnumConstantDeclaration"})
_CLASS_LIKE = (javalang.tree.ClassDeclaration, javalang.tree.InterfaceDeclaration, javalang.tree.EnumDeclaration)

# Token scanner used only to find a method body's matching closing brace, respecting
# string/char literals and comments so that braces inside them are never counted.
_TOKEN_RE = re.compile(
    r"//[^\n]*"                    # line comment
    r"|/\*.*?\*/"                  # block comment
    r'|"(?:\\.|[^"\\])*"'          # string literal
    r"|'(?:\\.|[^'\\])*'"          # char literal
    r"|[{}]",                      # brace
    re.DOTALL,
)


@dataclass(frozen=True)
class MethodSpan:
    class_path: str
    name: str
    params: tuple[str, ...]
    is_constructor: bool
    start_line: int
    end_line: int

    @property
    def signature_key(self) -> str:
        return f"{self.class_path}#{self.name}({','.join(self.params)})"


class UnparseableSource(ValueError):
    pass


def _param_type(param: "javalang.tree.FormalParameter") -> str:
    ptype = param.type
    name = getattr(ptype, "name", type(ptype).__name__)
    dims = len(getattr(ptype, "dimensions", None) or [])
    if getattr(param, "varargs", False):
        dims += 1
    return name + "[]" * dims


def _line_offsets(source: str) -> list[int]:
    offsets = [0]
    for match in re.finditer("\n", source):
        offsets.append(match.end())
    return offsets


def _line_of(offset: int, line_offsets: list[int]) -> int:
    lo, hi = 0, len(line_offsets) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if line_offsets[mid] <= offset:
            lo = mid
        else:
            hi = mid - 1
    return lo + 1


def _find_body_end_line(source: str, line_offsets: list[int], search_from_line: int) -> int | None:
    """Find the line of the ``}`` matching the first ``{`` at or after ``search_from_line``."""
    start_offset = line_offsets[search_from_line - 1] if search_from_line - 1 < len(line_offsets) else len(source)
    depth = 0
    opened = False
    for match in _TOKEN_RE.finditer(source, start_offset):
        token = match.group(0)
        if token == "{":
            depth += 1
            opened = True
        elif token == "}":
            if not opened:
                continue
            depth -= 1
            if depth == 0:
                return _line_of(match.start(), line_offsets)
    return None


def _class_path(path: list) -> str:
    names = [node.name for node in path if isinstance(node, _CLASS_LIKE)]
    return ".".join(names)


def _is_anonymous(path: list) -> bool:
    return any(type(node).__name__ in _ANONYMOUS_ANCESTORS for node in path)


def find_named_methods(source: str) -> list[MethodSpan]:
    """Return every named (non-anonymous) method/constructor with a precise line span.

    Raises ``UnparseableSource`` if ``javalang`` cannot parse the file; callers must
    treat that as a rejection reason rather than silently skipping the task.
    """
    try:
        tree = javalang.parse.parse(source)
    except (javalang.parser.JavaSyntaxError, javalang.tokenizer.LexerError) as exc:
        raise UnparseableSource(str(exc)) from exc
    line_offsets = _line_offsets(source)
    spans: list[MethodSpan] = []
    kinds = (javalang.tree.MethodDeclaration, javalang.tree.ConstructorDeclaration)
    nodes = [item for kind in kinds for item in tree.filter(kind)]
    for path, node in nodes:
        if _is_anonymous(path):
            continue
        if getattr(node, "body", None) is None:
            continue  # abstract/interface method with no body
        start_line = node.position.line if node.position else None
        if start_line is None:
            continue
        end_line = _find_body_end_line(source, line_offsets, start_line)
        if end_line is None:
            continue
        params = tuple(_param_type(p) for p in node.parameters)
        spans.append(
            MethodSpan(
                class_path=_class_path(path),
                name=node.name,
                params=params,
                is_constructor=isinstance(node, javalang.tree.ConstructorDeclaration),
                start_line=start_line,
                end_line=end_line,
            )
        )
    return spans


def enclosing_method(spans: list[MethodSpan], line: int) -> MethodSpan | None:
    containing = [s for s in spans if s.start_line <= line <= s.end_line]
    if not containing:
        return None
    return min(containing, key=lambda s: s.end_line - s.start_line)


def method_source(source: str, span: MethodSpan) -> str:
    lines = source.splitlines()
    return "\n".join(lines[span.start_line - 1 : span.end_line])


def find_method_by_signature(spans: list[MethodSpan], class_path: str, name: str, params: tuple[str, ...]) -> MethodSpan | None:
    for span in spans:
        if span.class_path == class_path and span.name == name and span.params == params:
            return span
    return None
