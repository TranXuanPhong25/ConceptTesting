"""Scripted stand-in for the Qwen client (dry runs and tests). No network, no environment variables."""
from __future__ import annotations

import ast
import json
import re

from .tc import digest


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


def default_script(messages, seed):
    """Answer a path prompt with a test that reuses one base-test input through a local variable; every
    second answer ends with a truncated line so that the paper's parse repair is exercised."""
    user = messages[-1]['content']
    code = re.search(r'```python\n(.*)```', user, re.S).group(1)
    tree = ast.parse(code)
    stub = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')][-1]
    entry, index = re.fullmatch(r'test_(.+)_(\d+)', stub.name).groups()
    index = int(index)
    check = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'check'), None)
    calls = []
    for node in ast.walk(check) if check else []:
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'candidate':
            calls.append(node)
    call = calls[(index - 1) % len(calls)] if calls else None
    args = ', '.join(ast.unparse(a) for a in call.args) if call else ''
    body = [f'def {stub.name}():', f'    value = {entry}({args})', f'    assert value == {json.dumps(seed % 7)}']
    if index % 2 == 0:
        body.append('    assert value ==')
    return '```python\n' + '\n'.join(body) + '\n```'
