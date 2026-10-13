"""Scripted stand-in for the Qwen client (dry runs and tests). No network, no environment variables.

Make a fault -> flips one comparison/arithmetic operator of the entry function (marked with MUTANT comments);
Equivalence detector -> 'no' (every fifth seed: 'yes'); Make a test -> the existing check() plus variants
of its inputs (small number/list/string perturbations) with expected value 0."""
from __future__ import annotations

import ast
import copy
import re

from .tc import digest

FLIP = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt, ast.Eq: ast.NotEq, ast.NotEq: ast.Eq,
        ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.Add, ast.FloorDiv: ast.Mult, ast.Mod: ast.FloorDiv}


class FakeClient:
    model = 'fake-scripted'

    def __init__(self, script=None):
        self.script = script or default_script
        self.requests = []

    def chat(self, messages, seed, *, temperature=0.7, top_p=0.95, max_tokens=1024):
        params = dict(model=self.model, temperature=temperature, top_p=top_p, max_tokens=max_tokens, seed=seed)
        self.requests.append(dict(params, messages=messages))
        text = self.script(messages, seed)
        prompt = ''.join(m['content'] for m in messages)
        return dict(key=digest(dict(params, messages=messages)), params=params, text=text,
                    n_in=len(prompt) // 4, n_out=len(text) // 4, seconds=0.0, cache_hit=False)


def _blocks(text):
    return re.findall(r'```python\n(.*?)\n```', text, re.S)


def fake_mutant(put, entry, seed):
    tree = ast.parse(put)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == entry)
    sites = [n for n in ast.walk(fn) if (isinstance(n, ast.Compare) and type(n.ops[0]) in FLIP)
             or (isinstance(n, ast.BinOp) and type(n.op) in FLIP)]
    before = ast.unparse(fn).splitlines()
    if sites:
        site = sites[seed % len(sites)]
        if isinstance(site, ast.Compare):
            site.ops[0] = FLIP[type(site.ops[0])]()
        else:
            site.op = FLIP[type(site.op)]()
    after = ast.unparse(fn).splitlines()
    out = []
    for old, new in zip(before, after):
        if old != new:
            pad = new[:len(new) - len(new.lstrip())]
            out += [pad + '# MUTANT <START>', new, pad + '# MUTANT <END>']
        else:
            out.append(new)
    return '\n'.join(out)


def _variants(node):
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return [ast.Constant(node.value + 1), ast.Constant(-node.value), ast.Constant(node.value * 3)]
    if isinstance(node, ast.List) and node.elts:
        return [ast.List(elts=node.elts[::-1], ctx=ast.Load()), ast.List(elts=node.elts[:-1], ctx=ast.Load()),
                ast.List(elts=node.elts + [ast.UnaryOp(op=ast.USub(), operand=ast.Constant(7))], ctx=ast.Load())]
    if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value:
        return [ast.Constant(node.value[::-1]), ast.Constant(node.value[:-1])]
    return []


def fake_tests(base):
    """Existing check() plus `assert candidate(<variant>) == 0` for variants of every base input."""
    tree = ast.parse(base)
    check = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'check')
    extra = []
    for node in ast.walk(check):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'candidate':
            for i, arg in enumerate(node.args):
                for v in _variants(arg):
                    new = copy.deepcopy(node)
                    new.args[i] = v
                    extra.append(f'    assert {ast.unparse(new)} == 0')
    return base.rstrip() + '\n' + '\n'.join(list(dict.fromkeys(extra))[:12]) + '\n'


def default_script(messages, seed):
    user = messages[-1]['content']
    blocks = _blocks(user)
    if user.startswith('CONTEXT:'):
        entry = re.search(r'makes `([^`]+)` violate', user).group(1)
        return 'Here is the mutated code:\n```python\n' + fake_mutant(blocks[0], entry, seed) + '\n```'
    if user.startswith("I'm going to show you"):
        return 'yes' if seed % 5 == 0 else 'no, the second version returns a different value for some inputs.'
    if user.startswith('What follows is two versions'):
        return '```python\n' + fake_tests(blocks[2]) + '```'
    raise ValueError('unexpected prompt')
