"""TrickCatcher adapter: task bundles, budgeted cached LLM calls, assertion flattening and gen.jsonl rows.

This file is identical in baselines/symprompt/ and baselines/ach/ (each paper folder is self-contained).
Nothing here executes model-written code: assertion extraction is purely syntactic.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ARMS_SEED = 20261010          # pipelines/v7/config.json seeds.arms
MODEL = 'qwen2.5-coder-7b-instruct'   # pipelines/v7/config.json model
SYSTEM = 'You are an expert software tester.'   # the system message of every v7 arm
MAX_ASSERT_CHARS = 50_000


def sha(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode()).hexdigest()


def digest(obj):
    return sha(json.dumps(obj, sort_keys=True, ensure_ascii=False))


def atomic_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + f'.{os.getpid()}.{threading.get_ident()}.tmp')
    temp.write_text(json.dumps(obj, ensure_ascii=False, indent=1) + '\n')
    temp.replace(path)


def immutable(path, value):
    path = Path(path)
    if path.exists():
        if json.loads(path.read_text()) != json.loads(json.dumps(value)):
            raise ValueError(f'artifact changed; use a fresh --out directory: {path}')
    else:
        atomic_json(path, value)


def seed(offset, task, sample, stage=0, index=0):
    """Deterministic per (baseline, task, sample, stage, index); disjoint from the v7 arm seeds and < 2**31."""
    n = int(task) if str(task).lstrip('-').isdigit() else int(sha(str(task))[:6], 16)
    return ARMS_SEED + offset + ((n * 1000 + sample) * 64 + stage * 16 + index)


# ------------------------------------------------------------------ tasks
def load_tasks(path, ids=None):
    bundle = json.loads(Path(path).read_text())
    tasks = bundle['tasks'] if isinstance(bundle, dict) else bundle
    meta = {k: v for k, v in bundle.items() if k != 'tasks'} if isinstance(bundle, dict) else {}
    if ids:
        wanted = [str(i) for i in ids]
        tasks = [t for t in tasks if str(t['task']) in wanted]
        if {str(t['task']) for t in tasks} != set(wanted):
            raise ValueError('requested task absent from bundle')
    if not tasks or len({str(t['task']) for t in tasks}) != len(tasks):
        raise ValueError('empty or duplicate task list')
    for t in tasks:
        for key in ('task', 'entry', 'put', 'base'):
            if key not in t:
                raise ValueError(f'task {t.get("task")}: missing {key}')
    return meta, tasks


def visible(task):
    """The TrickCatcher setting: spec (docstring inside the PUT), PUT code and base tests. No facts/oracles."""
    return {k: task[k] for k in ('task', 'entry', 'put', 'base', 'split') if k in task}


def docstring(task):
    tree = ast.parse(task['put'])
    fn = next((n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == task['entry']), None)
    return (ast.get_docstring(fn, clean=False) or '') if fn else ''


# ------------------------------------------------------------------ code blocks
def code_block(text):
    blocks = re.findall(r'```(?:python|py|Python)?[ \t]*\n(.*?)(?:```|\Z)', text, re.S)
    return '\n'.join(blocks) if blocks else text


def module_names(src):
    """Module-level names of the PUT, and whether it uses star imports (then any name may exist)."""
    tree = ast.parse(src)
    names, star = set(), False
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                if a.name == '*':
                    star = True
                else:
                    names.add((a.asname or a.name).split('.')[0])
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                names.update(n.id for n in ast.walk(t) if isinstance(n, ast.Name))
    return names, star


# ------------------------------------------------------------------ assertion flattening
class _Subst(ast.NodeTransformer):
    def __init__(self, env, entry):
        self.env, self.entry = env, entry

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            if node.id == 'candidate':
                return ast.copy_location(ast.Name(id=self.entry, ctx=ast.Load()), node)
            if node.id in self.env:
                return copy.deepcopy(self.env[node.id])
        return node

    def visit_Lambda(self, node):   # do not substitute into a lambda's own parameters
        return node


def _bound(node):
    """Names bound anywhere inside a statement (loop targets, assignments, imports, defs, handlers)."""
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
            out.add(n.id)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(n.name)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            out.update((a.asname or a.name).split('.')[0] for a in n.names)
        elif isinstance(n, ast.ExceptHandler) and n.name:
            out.add(n.name)
    return out


def _unittest_assert(node):
    """self.assertEqual(a, b) / assertTrue(x) / assertFalse(x) -> an equivalent assert statement."""
    if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute)):
        return None
    name, args = node.value.func.attr, node.value.args
    if name in ('assertEqual', 'assertEquals') and len(args) >= 2:
        test = ast.Compare(left=args[0], ops=[ast.Eq()], comparators=[args[1]])
    elif name == 'assertTrue' and args:
        test = args[0]
    elif name == 'assertFalse' and args:
        test = ast.UnaryOp(op=ast.Not(), operand=args[0])
    else:
        return None
    return ast.copy_location(ast.Assert(test=test, msg=None), node)


def flatten(code, entry, put_src, skip_functions=(), helpers=()):
    """Turn test code into standalone assertions over `entry` (no execution).

    Local single-assignment variables are substituted into later assertions; `candidate` is renamed to the
    entry point. An assertion is rejected when it still depends on a test-local name that cannot be
    substituted (loop variables, mutated objects, helper defs, names imported by the test only), or when
    it does not call the entry point. A comparison helper of the existing tests or of the test code itself
    (e.g. `_heldout_same(candidate(x), y, tol)` in the held-out check()) called as `helper(X, Y, ...)` with X
    calling the entry point is normalised to `X == Y` (the row format); any other use of such a helper is
    rejected because the assertion would not run on its own. Returns (assertions, rejected)."""
    if isinstance(code, str):
        tree = ast.parse(code)
    else:
        tree = code
    put_names, star = module_names(put_src)
    available = put_names | {'math', entry}
    out, rejected = [], []
    own = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
           and not n.name.startswith('test') and n.name not in ('check', entry)}
    helpers = (set(helpers) | own) - put_names - {entry}

    def check_names(test, unsafe):
        used = {n.id for n in ast.walk(test) if isinstance(n, ast.Name)}
        return sorted(used & unsafe)

    def calls_entry(test):
        return any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == entry for n in ast.walk(test))

    def body(stmts, env, unsafe):
        env, unsafe = dict(env), set(unsafe) | helpers
        for node in stmts:
            converted = _unittest_assert(node)
            if converted is not None:
                node = converted
            if isinstance(node, ast.Assert):
                test = node.test
                if isinstance(test, ast.Call) and isinstance(test.func, ast.Name) and test.func.id in helpers \
                        and len(test.args) >= 2:
                    a, b = test.args[:2]
                    if not calls_entry(_Subst(env, entry).visit(copy.deepcopy(a))):
                        a, b = b, a
                    if calls_entry(_Subst(env, entry).visit(copy.deepcopy(a))):
                        test = ast.Compare(left=a, ops=[ast.Eq()], comparators=[b])
                test = _Subst(env, entry).visit(copy.deepcopy(test))
                ast.fix_missing_locations(test)
                bad = check_names(test, unsafe)
                src = ast.unparse(ast.Assert(test=test, msg=None))
                if bad:
                    rejected.append(dict(source=ast.unparse(node), reason='unresolved test-local names: ' + ', '.join(bad)))
                elif not calls_entry(test):
                    rejected.append(dict(source=ast.unparse(node), reason=f'does not call {entry}'))
                elif len(src) > MAX_ASSERT_CHARS:
                    rejected.append(dict(source=src[:200] + '...', reason='assertion too long'))
                else:
                    out.append(src)
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                value = node.value
                if value is None:
                    continue
                value = _Subst(env, entry).visit(copy.deepcopy(value))
                ast.fix_missing_locations(value)
                tainted = bool(check_names(value, unsafe))
                for target in targets:
                    if isinstance(target, ast.Name):
                        if tainted:
                            env.pop(target.id, None); unsafe.add(target.id)
                        else:
                            env[target.id] = value; unsafe.discard(target.id)
                    elif isinstance(target, (ast.Tuple, ast.List)) and isinstance(value, (ast.Tuple, ast.List)) \
                            and len(target.elts) == len(value.elts) and not tainted \
                            and all(isinstance(e, ast.Name) for e in target.elts):
                        for e, v in zip(target.elts, value.elts):
                            env[e.id] = v; unsafe.discard(e.id)
                    else:
                        for name in _bound(target) | {n.id for n in ast.walk(target) if isinstance(n, ast.Name)}:
                            env.pop(name, None); unsafe.add(name)
            elif isinstance(node, ast.AugAssign):
                if isinstance(node.target, ast.Name) and node.target.id in env:
                    value = _Subst(env, entry).visit(copy.deepcopy(node.value))
                    if check_names(value, unsafe):
                        env.pop(node.target.id); unsafe.add(node.target.id)
                    else:
                        env[node.target.id] = ast.BinOp(left=env[node.target.id], op=node.op, right=value)
                else:
                    for name in {n.id for n in ast.walk(node.target) if isinstance(n, ast.Name)}:
                        env.pop(name, None); unsafe.add(name)
            elif isinstance(node, ast.Expr):
                # x.append(...), x.sort() ... may mutate a local object: its snapshot is no longer valid.
                for call in (n for n in ast.walk(node) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)):
                    base = call.func.value
                    while isinstance(base, (ast.Attribute, ast.Subscript)):
                        base = base.value
                    if isinstance(base, ast.Name) and base.id in env:
                        env.pop(base.id); unsafe.add(base.id)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for a in node.names:
                    name = (a.asname or a.name).split('.')[0]
                    if a.name == '*' or (name not in available and not star):
                        unsafe.add(name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                env.pop(node.name, None); unsafe.add(node.name)
            elif isinstance(node, (ast.For, ast.AsyncFor, ast.While, ast.If, ast.With, ast.AsyncWith, ast.Try)
                            ) or type(node).__name__ in ('TryStar', 'Match'):
                inner = _bound(node)
                local_unsafe = unsafe | inner
                local_env = {k: v for k, v in env.items() if k not in inner}
                for field in ('body', 'orelse', 'finalbody'):
                    body(getattr(node, field, []) or [], local_env, local_unsafe)
                for h in getattr(node, 'handlers', []) or []:
                    body(h.body, local_env, local_unsafe)
                for case in getattr(node, 'cases', []) or []:
                    body(case.body, local_env, local_unsafe)
                for name in inner:
                    env.pop(name, None); unsafe.add(name)
            elif isinstance(node, (ast.Delete, ast.Global, ast.Nonlocal)):
                for name in _bound(node) | set(getattr(node, 'names', [])):
                    env.pop(name, None); unsafe.add(name)

    def walk_defs(stmts):
        top = []
        for node in stmts:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == entry or node.name in skip_functions:
                    continue
                params = {a.arg for a in node.args.posonlyargs + node.args.args + node.args.kwonlyargs}
                params |= {a.arg for a in (node.args.vararg, node.args.kwarg) if a}
                body(node.body, {}, params - {'candidate', 'self'})
            elif isinstance(node, ast.ClassDef):
                walk_defs(node.body)
            else:
                top.append(node)
        return top

    top = walk_defs(tree.body)
    body(top, {}, set())
    return list(dict.fromkeys(out)), rejected


def base_helpers(task):
    """Module-level helper functions of the existing tests (e.g. a tolerance comparator), not check()."""
    try:
        tree = ast.parse(task['base'])
    except SyntaxError:
        return set()
    return {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name != 'check'}


def base_assertions(task):
    try:
        found, _ = flatten(task['base'], task['entry'], task['put'], helpers=base_helpers(task))
    except SyntaxError:
        return set()
    return set(found)


def round_robin(groups, cap):
    """Interleave per-path (SymPrompt) or per-mutant (ACH) test groups, deduplicated, up to `cap`."""
    seen, out, i = set(), [], 0
    while len(out) < cap and any(i < len(g) for g in groups):
        for g in groups:
            if i < len(g) and g[i] not in seen and len(out) < cap:
                seen.add(g[i]); out.append(g[i])
        i += 1
    return out


# ------------------------------------------------------------------ LLM calls
class BudgetExhausted(RuntimeError):
    pass


class Session:
    """Per-sample, budgeted access to the cached client; every prompt/response is stored as an artifact."""

    def __init__(self, client, directory, budget):
        self.client, self.directory, self.budget = client, Path(directory), budget
        self.directory.mkdir(parents=True, exist_ok=True)
        self.calls = []

    @property
    def remaining(self):
        return self.budget - len(self.calls)

    def query(self, messages, seed_value, label, **params):
        if self.remaining <= 0:
            raise BudgetExhausted(label)
        atomic_json(self.directory / f'{len(self.calls):02d}_{label}_prompt.json', messages)
        response = self.client.chat(messages, seed_value, **params)
        record = dict(response, label=label)
        atomic_json(self.directory / f'{len(self.calls):02d}_{label}.json', record)
        self.calls.append(record)
        return response['text']


def make_client(out, *, online=False, fake=False, workers=4, fake_factory=None):
    """--fake: scripted local client (no network); --online: the v7 cached Qwen client; default: cache replay."""
    if fake:
        return fake_factory()
    from trickcatcher_linefacts.pipelines.v7.llm_client import Client
    return Client(Path(out) / 'cache', offline=not online, workers=workers, model=MODEL)


def row(task, arm, sample, run_id, model, assertions, calls, **extra):
    return dict(task=task['task'], split=task.get('split', 'dev'), arm=arm, sample=sample, model=model,
                facts_version=task.get('facts_version'), run_id=run_id,
                text='```python\n' + '\n'.join(assertions) + '\n```', assertions=assertions,
                n_assertions=len(assertions), llm_calls=len(calls),
                n_in=sum(c.get('n_in', 0) for c in calls), n_out=sum(c.get('n_out', 0) for c in calls),
                seconds=sum(c.get('seconds', 0) for c in calls), calls=calls, **extra)


def source_hashes(folder):
    return {p.name: sha(p.read_bytes()) for p in sorted(Path(folder).glob('*.py')) if not p.name.startswith('test_')}


def run_all(tasks, k, workers, one):
    """one(task, sample) -> row; rows ordered by (bundle order, sample)."""
    jobs = [(t, s) for t in tasks for s in range(k)]
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        return list(pool.map(lambda job: one(*job), jobs))


def write_rows(out, rows):
    out = Path(out)
    temp = out / 'gen.pending.jsonl'
    temp.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))
    temp.replace(out / 'gen.jsonl')
    return out / 'gen.jsonl'
