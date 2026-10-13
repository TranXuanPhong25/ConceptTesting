"""SymPrompt Step II (paper Section 3.3, Figure 6) and Step III (Section 3.4, Figures 3, 7 and 11a).

Context = (1) imports and globals, (2) type context: classes of the focal file used by the focal method,
(3) focal class signature and constructor, (4) focal-class methods and file functions called by the focal
method (dependency context), (5) the focal method. Each path prompt is a test-function stub whose docstring
holds (1) the focal method signature, (2) the path constraints joined so that all must hold, and (3)
`returns: <value>` when the path ends in a return. Previously generated tests precede the next stub.
"""
from __future__ import annotations

import ast
import copy

from .tc import SYSTEM

INSTRUCTION = """Complete the last test function in the Python test file below. The file shows the code under \
test (imports and globals, the type and dependency context, and the focal function), the existing tests, and \
the tests written so far. The docstring of the last test function gives the path constraints that its test \
input must satisfy and, if the path returns, the returned value. Write its body so that it calls `{entry}` \
with an input that satisfies all of these constraints, and check the result with assertions of the form \
`assert {entry}(<arguments>) == <expected>`. Reply with a single ```python code block that contains only the \
completed test function."""

FILE = """```python
{context}


# Existing tests
{base}

# Tests for function {entry}
{previous}{stub}
```"""


def _segment(lines, node, indent=''):
    start = min([d.lineno for d in getattr(node, 'decorator_list', [])] + [node.lineno])
    text = '\n'.join(lines[start - 1:node.end_lineno])
    return text if not indent else '\n'.join(indent + l if l.strip() else l for l in text.splitlines())


def _used_names(node):
    names = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
    names |= {n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute)}
    return names


def _self_calls(node):
    return {n.func.attr for n in ast.walk(node) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and isinstance(n.func.value, ast.Name) and n.func.value.id == 'self'}


def context(put_src, fn, cls, wrapper, tree):
    """The five-part generation context of Figure 6, built from the PUT file."""
    lines = put_src.splitlines()
    used = _used_names(fn) | (_used_names(wrapper) if wrapper else set())
    parts = []
    # (1) imports and globals
    head = [_segment(lines, n) for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign))]
    if head:
        parts.append('\n'.join(head))
    # (2) type context: classes defined in the file and used by the focal method (not the focal class)
    for n in tree.body:
        if isinstance(n, ast.ClassDef) and n is not cls and n.name in used:
            parts.append(_segment(lines, n))
    # (4, file functions) dependency context: module-level functions the focal method uses
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n is not wrapper and n is not fn and n.name in used:
            parts.append(_segment(lines, n))
    if cls is not None:
        # (3) focal class signature + constructor, (4) called focal-class methods, (5) focal method
        bases = [ast.unparse(b) for b in cls.bases] + [ast.unparse(k) for k in cls.keywords]
        header = [f"class {cls.name}{'(' + ', '.join(bases) + ')' if bases else ''}:"]
        members = [n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        init = [n for n in members if n.name == '__init__']
        called = [n for n in members if n.name in _self_calls(fn) and n is not fn and n.name != '__init__']
        body = [_segment(lines, n) for n in init + called + [fn]]
        parts.append('\n'.join(header) + '\n' + '\n\n'.join(body))
        parts.append(_segment(lines, wrapper))    # the function the tests call (it carries the spec)
    else:
        parts.append(_segment(lines, fn))
    return '\n\n\n'.join(parts)


def signature(fn, name=None):
    """`entry(a: T, b: U = 1) -> R` as in the paper's 'Testcase for ...' line."""
    clone = copy.copy(fn)
    clone.name, clone.body, clone.decorator_list = name or fn.name, [ast.Pass()], []
    head = ast.unparse(ast.fix_missing_locations(clone)).splitlines()[0]
    return head[len('def '):].rstrip(':')


def stub(entry, index, sig, path):
    lines = ['"""', f'Testcase {index} for {sig}']
    if path['constraints']:
        lines.append('where ' + ',\n'.join(path['constraints']))
    if path['end'] == 'return':
        lines.append(f"returns: {path['returns']}")
    lines.append('"""')
    doc = '\n'.join(('    ' + l if l else l) for l in '\n'.join(lines).splitlines())
    return f'def test_{entry}_{index}():\n{doc}\n'


def messages(task, ctx, sig, path, index, previous):
    entry = task['entry']
    prev = ''.join(p.rstrip() + '\n\n' for p in previous)
    user = INSTRUCTION.format(entry=entry) + '\n\n' + FILE.format(
        context=ctx, base=task['base'].strip(), entry=entry, previous=prev, stub=stub(entry, index, sig, path))
    return [dict(role='system', content=SYSTEM), dict(role='user', content=user)]


def parse_repair(code):
    """Paper 3.4: delete lines from the end until the generated code parses (truncated outputs)."""
    lines = code.rstrip().splitlines()
    while lines:
        try:
            ast.parse('\n'.join(lines))
            return '\n'.join(lines), True
        except SyntaxError:
            lines.pop()
    return '', False


def test_functions(code):
    """Sources of the generated test functions (kept in later prompts); the whole code if there are none."""
    tree = ast.parse(code)
    lines = code.splitlines()
    found = [_segment(lines, n) for n in tree.body
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith('test')]
    return found or ([code] if code.strip() else [])
