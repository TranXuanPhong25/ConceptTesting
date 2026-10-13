"""ACH rule-based steps (paper Figure 1, Section 5.2-5.3): assemble the LLM's fault into the PUT, remove
syntactically identical faults (lexical comparison after stripping comments), and read the equivalence
detector's yes/no answer. No code is executed here."""
from __future__ import annotations

import ast
import io
import re
import tokenize

MARK_START, MARK_END = '# MUTANT <START>', '# MUTANT <END>'


def _span(node):
    start = min([d.lineno for d in getattr(node, 'decorator_list', [])] + [node.lineno])
    return start, node.end_lineno


def _dedent_block(lines):
    indent = min((len(l) - len(l.lstrip()) for l in lines if l.strip()), default=0)
    return [l[indent:] if l.strip() else l for l in lines]


def assemble(put_src, response_code, entry):
    """Splice the response's top-level definitions into the PUT by name (keeping the response text with its
    MUTANT markers). New helper definitions go before the first replaced one; new imports go first.
    Raises SyntaxError/ValueError when the response does not build into a module defining `entry`."""
    rtree = ast.parse(response_code)
    rlines = response_code.splitlines()
    defs = {n.name: n for n in rtree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
    if not defs:
        raise ValueError('response contains no function or class definition')
    ptree = ast.parse(put_src)
    plines = put_src.splitlines()
    pdefs = {n.name: n for n in ptree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
    if not set(defs) & set(pdefs):
        raise ValueError('response redefines no function of the code under test')
    text = lambda node: _dedent_block(rlines[_span(node)[0] - 1:_span(node)[1]])
    replaced = sorted((pdefs[name] for name in defs if name in pdefs), key=lambda n: n.lineno)
    new_defs = [defs[name] for name in defs if name not in pdefs]
    out, cursor = [], 1
    for i, node in enumerate(replaced):
        start, end = _span(node)
        out += plines[cursor - 1:start - 1]
        if i == 0:
            for extra in new_defs:
                out += text(extra) + ['', '']
        out += text(defs[node.name])
        cursor = end + 1
    out += plines[cursor - 1:]
    put_imports = {ast.unparse(n) for n in ptree.body if isinstance(n, (ast.Import, ast.ImportFrom))}
    imports = [ast.unparse(n) for n in rtree.body if isinstance(n, (ast.Import, ast.ImportFrom))
               and ast.unparse(n) not in put_imports and not (isinstance(n, ast.ImportFrom) and n.module == '__future__')]
    mutant = '\n'.join(imports + out) + '\n'
    tree = ast.parse(mutant)
    if not any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == entry for n in tree.body):
        raise ValueError(f'mutant does not define {entry}')
    return mutant


def strip_comments(src):
    """Remove every `#` comment (the paper's pre-processing for misleading added comments); a line that held
    only a comment is dropped."""
    lines = src.splitlines()
    cuts = {}
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type == tokenize.COMMENT:
                cuts[tok.start[0]] = tok.start[1]
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return src
    out = []
    for i, line in enumerate(lines, start=1):
        if i in cuts:
            kept = line[:cuts[i]].rstrip()
            if kept.strip():
                out.append(kept)
        else:
            out.append(line)
    return '\n'.join(out) + '\n'


def normal_form(src):
    """Lexical identity after comment stripping: the AST dump (Python's AST carries no comments; formatting
    differences are ignored as a lexical comparison of comment-free code would after normalising layout)."""
    return ast.dump(ast.parse(src), include_attributes=False)


def judge(text):
    """'equivalent' (yes) / 'non-equivalent' (no) / 'unsure' (no clear answer). Only non-equivalent mutants
    are used for test generation (paper Table 2: tests come from mutants the agent believes non-equivalent)."""
    t = re.sub(r"^[\s`*'\"{(\[]+", '', text.strip().lower())
    if re.match(r'yes\b', t):
        return 'equivalent'
    if re.match(r'no\b', t):
        return 'non-equivalent'
    return 'unsure'
