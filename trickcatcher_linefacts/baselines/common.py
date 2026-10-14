"""Transport, artifacts and assertion normalization shared by the CoverUp and MuTAP adapters.

(SymPrompt and ACH keep their own self-contained `tc.py`; nothing here is imported by them.)
"""
from __future__ import annotations

import argparse
import ast
import builtins
import copy
import hashlib
import itertools
import json
import multiprocessing
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MODEL = 'qwen2.5-coder-7b-instruct'
MAX_LLM_CALLS = 8
MAX_ASSERTIONS = 20
MAX_ASSERT_CHARS = 50_000
MAX_UNROLL = 100


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(path.name + '.pending')
    pending.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    pending.replace(path)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def code_block(text):
    blocks = re.findall(r'```(?:python|py|Python)?[ \t]*\n(.*?)(?:```|\Z)', text, re.S)
    return '\n'.join(blocks) if blocks else text


def original_definitions(path, names, namespace=None):
    """Compile exact author definitions, excluding module-level CLI/transport effects."""
    tree = ast.parse(Path(path).read_text(encoding='utf-8-sig'))
    nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name in names]
    if {n.name for n in nodes} != set(names):
        raise ValueError(f'upstream definitions changed: {path}')
    ns = dict(namespace or {})
    # Postponed annotations avoid importing the authors' unused transport SDKs.
    import __future__
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec', flags=__future__.annotations.compiler_flag), ns)
    return ns


# ------------------------------------------------------------------ assertion extraction (AST only, no execution)
def module_names(src, stars=False):
    """Module-level names of the PUT (defs, classes, imports, assignments); '*' marks a star import if `stars`."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return set()
    names = set()
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names.update((a.asname or a.name).split('.')[0] for a in node.names if stars or a.name != '*')
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            for t in (node.targets if isinstance(node, ast.Assign) else [node.target]):
                names.update(n.id for n in ast.walk(t) if isinstance(n, ast.Name))
    return names


def helper_functions(src):
    """Module-level helper functions of a test file other than check() (e.g. the held-out `_heldout_same`)."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return set()
    return {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            and n.name != 'check' and not n.name.startswith('test')}


def _stored(node):
    """Names bound anywhere inside a node (assignments, loop/comprehension targets, defs, imports, handlers, lambdas)."""
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
        elif isinstance(n, ast.Lambda):
            a = n.args
            out.update(x.arg for x in a.posonlyargs + a.args + a.kwonlyargs + [v for v in (a.vararg, a.kwarg) if v])
    return out


def _free(expr):
    return {n.id for n in ast.walk(expr) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)} - _stored(expr)


class _Resolve(ast.NodeTransformer):
    """Substitute resolvable test-local names; `candidate`/import aliases become the entry name."""
    def __init__(self, env, entry, modules):
        self.env, self.entry, self.modules = env, entry, modules

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load) and node.id in self.env:
            return copy.deepcopy(self.env[node.id])
        return node

    def visit_Attribute(self, node):
        if isinstance(node.value, ast.Name) and node.value.id in self.modules and node.attr == self.entry:
            return ast.Name(id=self.entry, ctx=ast.Load())
        return self.generic_visit(node)

    def _scoped(self, node):
        # A comprehension/lambda binding shadows an outer test-local name of the same spelling.
        inner = _Resolve({k: v for k, v in self.env.items() if k not in _stored(node)}, self.entry, self.modules)
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                setattr(node, field, [inner.visit(v) if isinstance(v, ast.AST) else v for v in value])
            elif isinstance(value, ast.AST):
                setattr(node, field, inner.visit(value))
        return node

    visit_ListComp = visit_SetComp = visit_GeneratorExp = visit_DictComp = visit_Lambda = _scoped


def _calls_entry(expr, entry):
    return any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == entry for n in ast.walk(expr))


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


def _sequence(node):
    """Elements of a literal sequence node (list/tuple/set or range(<=MAX_UNROLL constants)), else None."""
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)) and not any(isinstance(e, ast.Starred) for e in node.elts):
        return list(node.elts) if len(node.elts) <= MAX_UNROLL else None
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'range' and not node.keywords:
        try:
            values = range(*[ast.literal_eval(a) for a in node.args])
            if len(values) > MAX_UNROLL:
                return None
        except (ValueError, TypeError, SyntaxError, OverflowError):
            return None
        return [ast.Constant(v) for v in values] if len(values) <= MAX_UNROLL else None
    return None


def _bind(target, value):
    """Bindings for `for target in ...` / parametrize rows, or None when the shapes do not match."""
    if isinstance(target, ast.Name):
        return {target.id: value}
    if isinstance(target, (ast.Tuple, ast.List)) and all(isinstance(e, ast.Name) for e in target.elts) \
            and isinstance(value, (ast.Tuple, ast.List)) and len(value.elts) == len(target.elts):
        return {e.id: v for e, v in zip(target.elts, value.elts)}
    return None


def extract_assertions(source, entry, put_src='', helpers=()):
    """Flatten generated tests into standalone assertions over `entry`; never executes model code.

    Kept: any assert that (after substituting simple test-local assignments, literal parametrize rows and
    literal for-loops) calls the entry and uses no unresolved test-local name; free names must be builtins,
    `math`, or module-level names of the PUT (the v7 evaluator runs assertions in the PUT's globals plus math).
    Normalized: `candidate`/`put.<entry>`/import aliases -> entry; unittest assertEqual/True/False -> assert;
    `x is True|False|None` and `x == pytest.approx(y, ...)` -> `x == y`; a comparison helper of the base tests
    or of the test itself (e.g. `_heldout_same(entry(...), y, tol)`) -> `entry(...) == y`.
    Returns (assertions, rejected)."""
    rejected, result = [], []
    try:
        tree = ast.parse(code_block(source))
    except SyntaxError as exc:
        return [], [dict(reason='syntax', line=exc.lineno)]
    allowed = set(dir(builtins)) | {'math', entry} | module_names(put_src)
    star = '*' in module_names(put_src, stars=True)   # `from m import *` in the PUT: any global may exist
    modules = {'put'}
    env0 = {'candidate': ast.Name(id=entry, ctx=ast.Load())}
    helpers = (set(helpers) | {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                               and not n.name.startswith('test') and n.name not in ('check', entry)}) - {entry}

    def resolve(node, env):
        out = _Resolve(env, entry, modules).visit(copy.deepcopy(node))
        return ast.fix_missing_locations(out)

    def emit(node, env, unsafe):
        test = resolve(node.test, env)
        if isinstance(test, ast.Call) and isinstance(test.func, ast.Name) and test.func.id in helpers and len(test.args) >= 2:
            a, b = test.args[:2]
            if _calls_entry(b, entry) and not _calls_entry(a, entry):
                a, b = b, a
            if _calls_entry(a, entry):
                test = ast.Compare(left=a, ops=[ast.Eq()], comparators=[b])
        if isinstance(test, ast.Compare) and len(test.ops) == 1:
            right = test.comparators[0]
            if isinstance(right, ast.Call) and ast.unparse(right.func) in ('pytest.approx', 'approx') and right.args:
                test = ast.Compare(left=test.left, ops=[ast.Eq()], comparators=[right.args[0]])
            elif isinstance(test.ops[0], ast.Is) and isinstance(right, ast.Constant) and right.value in (True, False, None):
                test = ast.Compare(left=test.left, ops=[ast.Eq()], comparators=[right])
        test = ast.fix_missing_locations(test)
        src = ast.unparse(ast.Assert(test=test, msg=None))
        free = _free(test)
        bad = sorted((free & unsafe) | (set() if star else free - allowed))
        if bad:
            rejected.append(dict(line=node.lineno, reason='unresolved names: ' + ', '.join(bad), source=ast.unparse(node)))
        elif not _calls_entry(test, entry):
            rejected.append(dict(line=node.lineno, reason=f'does not call {entry}', source=ast.unparse(node)))
        elif len(src) > MAX_ASSERT_CHARS:
            rejected.append(dict(line=node.lineno, reason='assertion too long', source=src[:200] + '...'))
        else:
            result.append(src)

    def parametrize_rows(fn, env, unsafe):
        """Bindings of literal @pytest.mark.parametrize decorators (cartesian product), or None."""
        groups = []
        for dec in fn.decorator_list:
            if not (isinstance(dec, ast.Call) and ast.unparse(dec.func).endswith('parametrize') and len(dec.args) >= 2):
                continue
            names = dec.args[0]
            if isinstance(names, ast.Constant) and isinstance(names.value, str):
                names = [s.strip() for s in names.value.split(',') if s.strip()]
            elif isinstance(names, (ast.List, ast.Tuple)) and all(isinstance(e, ast.Constant) for e in names.elts):
                names = [e.value for e in names.elts]
            else:
                return None
            rows = _sequence(resolve(dec.args[1], env))
            if rows is None:
                return None
            bound = []
            for row in rows:
                if isinstance(row, ast.Call) and ast.unparse(row.func).endswith('param'):
                    row = ast.Tuple(elts=list(row.args), ctx=ast.Load()) if len(names) > 1 else (row.args[0] if row.args else None)
                if row is None:
                    return None
                target = ast.Name(id=names[0]) if len(names) == 1 else ast.Tuple(elts=[ast.Name(id=n) for n in names])
                b = _bind(target, row)
                if b is None or any(_free(v) & unsafe for v in b.values()):
                    return None
                bound.append(b)
            groups.append(bound)
        if not groups:
            return [{}]
        combinations = itertools.islice(itertools.product(*groups), MAX_UNROLL + 1)
        product = [dict(itertools.chain.from_iterable(d.items() for d in combo)) for combo in combinations]
        return product if len(product) <= MAX_UNROLL else None

    def walk(body, env, unsafe):
        env, unsafe = dict(env), set(unsafe)
        for node in body:
            node = _unittest_assert(node) or node
            if isinstance(node, ast.Assert):
                emit(node, env, unsafe)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == entry:
                    continue
                if node.name.startswith('test') or node.name == 'check':
                    a = node.args
                    params = {x.arg for x in a.posonlyargs + a.args + a.kwonlyargs + [v for v in (a.vararg, a.kwarg) if v]}
                    rows = parametrize_rows(node, env, unsafe)
                    for row in rows if rows is not None else [{}]:
                        inner = {k: v for k, v in env.items() if k not in params}
                        inner.update(row)
                        if 'candidate' in params:
                            inner['candidate'] = ast.Name(id=entry, ctx=ast.Load())
                        walk(node.body, inner, (unsafe | params) - set(row) - {'candidate'})
                env.pop(node.name, None)
                unsafe.add(node.name)
            elif isinstance(node, ast.ClassDef):
                walk(node.body, env, unsafe)
                env.pop(node.name, None)
                unsafe.add(node.name)
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                value = resolve(node.value, env) if node.value is not None else None
                tainted = value is None or bool(_free(value) & unsafe)
                for target in targets:
                    binding = None if tainted else _bind(target, value)
                    if binding is not None:
                        for k, v in binding.items():
                            env[k] = v
                            unsafe.discard(k)
                    else:
                        for name in _stored(target) | {n.id for n in ast.walk(target) if isinstance(n, ast.Name)}:
                            env.pop(name, None)
                            unsafe.add(name)
            elif isinstance(node, ast.AugAssign):
                name = node.target.id if isinstance(node.target, ast.Name) else None
                value = resolve(node.value, env)
                if name in env and not (_free(value) & unsafe):
                    env[name] = ast.BinOp(left=env[name], op=node.op, right=value)
                else:
                    for n in {x.id for x in ast.walk(node.target) if isinstance(x, ast.Name)}:
                        env.pop(n, None)
                        unsafe.add(n)
            elif isinstance(node, ast.Expr):
                # x.append(...), x.sort() ... may mutate a local object: its snapshot is no longer valid.
                for call in (n for n in ast.walk(node) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)):
                    base = call.func.value
                    while isinstance(base, (ast.Attribute, ast.Subscript)):
                        base = base.value
                    if isinstance(base, ast.Name) and base.id in env:
                        env.pop(base.id)
                        unsafe.add(base.id)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for a in node.names:
                    name = (a.asname or a.name).split('.')[0]
                    if isinstance(node, ast.Import) and a.name == 'put':
                        modules.add(name)
                    elif isinstance(node, ast.ImportFrom) and node.module == 'put' and a.name == entry:
                        env[name] = ast.Name(id=entry, ctx=ast.Load())
                        unsafe.discard(name)
                    elif isinstance(node, ast.ImportFrom) and node.module == 'put' and a.name in allowed:
                        if name != a.name:
                            unsafe.add(name)
                    elif name not in allowed or name != a.name.split('.')[0]:
                        env.pop(name, None)
                        unsafe.add(name)
            elif isinstance(node, (ast.For, ast.AsyncFor)):
                items = _sequence(resolve(node.iter, env))
                jumps = any(isinstance(n, (ast.Break, ast.Continue, ast.Return)) for n in ast.walk(node))
                inner_bound = _stored(ast.Module(body=node.body, type_ignores=[])) | _stored(node.target)
                rows = None if items is None or jumps or node.orelse else [_bind(node.target, v) for v in items]
                if rows is not None and all(r is not None and not any(_free(v) & unsafe for v in r.values()) for r in rows):
                    for row in rows:
                        inner = {k: v for k, v in env.items() if k not in inner_bound}
                        inner.update(row)
                        walk(node.body, inner, unsafe - set(row))
                else:
                    walk(node.body + node.orelse, {k: v for k, v in env.items() if k not in inner_bound}, unsafe | inner_bound)
                for name in inner_bound:
                    env.pop(name, None)
                    unsafe.add(name)
            elif isinstance(node, (ast.While, ast.If, ast.With, ast.AsyncWith, ast.Try)) or type(node).__name__ in ('TryStar', 'Match'):
                inner_bound = _stored(node)
                local_env = {k: v for k, v in env.items() if k not in inner_bound}
                local_unsafe = unsafe | inner_bound
                for field in ('body', 'orelse', 'finalbody'):
                    walk(getattr(node, field, []) or [], local_env, local_unsafe)
                for h in getattr(node, 'handlers', []) or []:
                    walk(h.body, local_env, local_unsafe)
                for case in getattr(node, 'cases', []) or []:
                    walk(case.body, local_env, local_unsafe)
                for name in inner_bound:
                    env.pop(name, None)
                    unsafe.add(name)
            elif isinstance(node, (ast.Delete, ast.Global, ast.Nonlocal)):
                for name in _stored(node) | set(getattr(node, 'names', [])):
                    env.pop(name, None)
                    unsafe.add(name)

    walk(tree.body, env0, set(helpers))
    return list(dict.fromkeys(result)), rejected


def base_assertions(task):
    """Normalized assertions of the provided base tests (copies of these add no new input)."""
    found, _ = extract_assertions(task['base'], task['entry'], task['put'], helper_functions(task['base']))
    return set(found)


def visible_task(task):
    # Never pass mined facts, silver/private tests, reference programs or witnesses to generators.
    return {k: task[k] for k in ('task', 'entry', 'put', 'base', 'split', 'spec', 'docstring', 'prompt') if k in task}


def specification(task):
    """Explicit specification takes precedence over the PUT's possibly absent docstring."""
    for key in ('spec', 'docstring', 'prompt'):
        if task.get(key):
            return task[key]
    tree = ast.parse(task['put'])
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == task['entry']:
            return ast.get_docstring(node) or ''
    return ''


def base_test(task):
    return f"from put import {task['entry']}\n" + task['base'] + f"\n\ndef test_base():\n    check({task['entry']})\n"


# ------------------------------------------------------------------ sandbox
def worker(mode, payload, directory, timeout=60):
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    job, output = directory/'job.json', directory/'output.json'
    atomic_json(job, dict(payload, mode=mode))
    output.unlink(missing_ok=True)
    # Explicit environment: do not inspect or propagate endpoint variables or credentials.
    env = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1',
           'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', 'HOME': str(directory)}
    proc = subprocess.Popen(['unshare', '-rn', sys.executable, '-I', '-B', str(HERE/'worker.py'), str(job), str(output)],
                            cwd=directory, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    try:
        _, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        return dict(ok=False, error='worker timeout')
    if proc.returncode or not output.exists():
        return dict(ok=False, error='worker failed', detail=stderr.decode(errors='replace')[-2000:])
    return json.loads(output.read_text())


# ------------------------------------------------------------------ LLM access
class ContextTooLong(Exception):
    """HTTP 400: prompt + completion exceed the model context (dev sanity amendment 4)."""


class TransientResponse(Exception):
    """Marker for a retryable 5xx response."""


def _transient(exc):
    import httpx
    return isinstance(exc, (TransientResponse, httpx.TimeoutException, httpx.TransportError))


class QwenClient:
    """Shared OpenAI-compatible transport. Only explicit online mode reads endpoint credentials.

    Requests are retried on transient transport errors only (amendment 3). Replay reads the local cache only. Endpoint and
    credential values are never written into artifacts or included in transport errors.
    """
    model = MODEL

    def __init__(self, cache, offline=True):
        self.cache, self.offline = Path(cache), offline
        self.cache.mkdir(parents=True, exist_ok=True)
        if not offline:
            base = os.environ.get('QWEN_BASE_URL')
            if not base:
                raise ValueError('online mode requires QWEN_BASE_URL')
            import httpx
            self._endpoint = base.rstrip('/') + '/chat/completions'
            key = os.environ.get('QWEN_API_KEY')
            headers = {'Authorization': 'Bearer ' + key} if key else {}
            # 2026-10-14 (dev sanity amendment 3): same transport policy as the pipelines' client (600 s, up to 8
            # retries on timeouts/connection errors/5xx with backoff); identical payload and seed, so a retry cannot
            # change what the method asks. 4xx errors are not retried.
            self._http = httpx.Client(headers=headers, timeout=600, trust_env=False,
                                      transport=httpx.HTTPTransport(retries=0, trust_env=False))

    def chat(self, messages, seed, **params):
        payload = dict(model=self.model, messages=messages, seed=seed, **params)
        key = digest(payload)
        cached = self.cache/(key + '.json')
        if cached.exists():
            return dict(json.loads(cached.read_text()), cache_hit=True)
        if self.offline:
            raise RuntimeError('offline Qwen cache miss: ' + key)
        start = time.monotonic()
        try:
            for attempt in range(9):
                try:
                    response = self._http.post(self._endpoint, json=payload)
                    if getattr(response, "status_code", 200) >= 500 and attempt < 8:
                        raise TransientResponse()
                    break
                except Exception as exc:
                    if attempt == 8 or not _transient(exc):
                        raise
                    time.sleep(min(60, 2.0 * 2 ** attempt))
            if getattr(response, 'status_code', 200) == 400 and 'maximum context length' in getattr(response, 'text', ''):
                raise ContextTooLong()
            response.raise_for_status()
            data = response.json()
            usage = data.get('usage', {})
            result = dict(text=data['choices'][0]['message']['content'],
                          n_in=usage.get('prompt_tokens', 0), n_out=usage.get('completion_tokens', 0),
                          seconds=time.monotonic()-start, cache_hit=False, key=key)
        except ContextTooLong:
            raise
        except Exception:
            raise RuntimeError('Qwen request failed; generation aborted without retry') from None
        atomic_json(cached, result)
        return result


class ScriptedClient:
    """No network or environment access. Default response replays visible base assertions."""
    model = 'offline-scripted'

    def __init__(self, responses):
        if not responses or not all(isinstance(r, str) for r in responses):
            raise ValueError('empty/invalid script')
        self.responses, self.index = responses, 0

    def chat(self, messages, seed, **kwargs):
        text = self.responses[min(self.index, len(self.responses)-1)]
        self.index += 1
        return dict(text=text, n_in=0, n_out=0, seconds=0, cache_hit=False, seed=seed)


class BudgetExhausted(Exception):
    pass


class Session:
    def __init__(self, task, arm, sample, client, directory, budget, seed, max_tokens=2048):
        if not 0 <= budget <= MAX_LLM_CALLS:
            raise ValueError('per-sample LLM budget must be in 0..8')
        self.task, self.arm, self.sample, self.client = task, arm, sample, client
        self.directory, self.budget, self.seed, self.max_tokens = Path(directory), budget, seed, max_tokens
        self.directory.mkdir(parents=True, exist_ok=True)
        self.calls = []

    @property
    def remaining(self):
        return self.budget-len(self.calls)

    def query(self, messages, stage):
        if self.remaining <= 0:
            raise BudgetExhausted()
        seed = int(digest([self.seed, self.task['task'], self.arm, self.sample, len(self.calls)])[:8], 16) % (2**31)
        label = f'call_{len(self.calls):03d}'
        atomic_json(self.directory/(label+'_prompt.json'), messages)
        try:
            response = self.client.chat(messages, seed, temperature=0.7, top_p=0.95, max_tokens=self.max_tokens)
        except ContextTooLong:
            # dev sanity amendment 4 (as v9 amendment 1): an over-long prompt is a request made (counts toward the
            # budget) with an empty answer, so the method continues/stops by its own logic instead of aborting.
            response = dict(text='', n_in=0, n_out=0, seconds=0, cache_hit=False, error='context_length')
        keep = ('text', 'n_in', 'n_out', 'seconds', 'cache_hit', 'key', 'error')
        record = dict({k: response[k] for k in keep if k in response}, seed=seed, stage=stage)
        self.calls.append(record)
        atomic_json(self.directory/(label+'.json'), record)
        (self.directory/(label+'_raw.py')).write_text(code_block(response['text']))
        return response['text']


# ------------------------------------------------------------------ runner
_CTX = {}


def _client():
    """Per-process client (forked workers each build their own; the file cache is shared and locked)."""
    if 'client' not in _CTX:
        args = _CTX['args']
        if args.online or args.replay:
            _CTX['client'] = QwenClient(_CTX['cache'], offline=not args.online)
        else:
            _CTX['client'] = None
    return _CTX['client']


def _run_job(job):
    index, sample = job
    args, tasks, arm, generate = _CTX['args'], _CTX['tasks'], _CTX['arm'], _CTX['generate']
    task = tasks[index]
    directory = _CTX['out']/'artifacts'/digest(task['task'])[:16]/str(sample)
    done = directory/'result.json'
    if done.exists():
        return json.loads(done.read_text())
    if directory.exists():
        shutil.rmtree(directory)   # incomplete earlier attempt (--resume); cached LLM calls are reused
    visible = visible_task(task)
    client = _client()
    if client is None:
        responses = _CTX['scripts'].get(str(task['task']), ['```python\n'+base_test(visible)+'\n```'])
        if not responses or not all(isinstance(r, str) for r in responses):
            raise ValueError('empty/invalid script')
        client = ScriptedClient(responses)
    session = Session(visible, arm, sample, client, directory, args.llm_budget, args.seed, args.max_tokens)
    generated = generate(visible, session, args)
    uncapped = generated.pop('assertions')
    base = base_assertions(visible)
    fresh = [a for a in uncapped if a not in base]
    final = fresh[:args.max_tests]
    bundle = _CTX['bundle']
    row = dict(task=task['task'], arm=arm, sample=sample, split=task.get('split', 'dev'),
               text='```python\n'+'\n'.join(final)+'\n```', assertions=final, n_assertions=len(final),
               llm_calls=len(session.calls), n_in=sum(c.get('n_in', 0) for c in session.calls),
               n_out=sum(c.get('n_out', 0) for c in session.calls), seconds=sum(c.get('seconds', 0) for c in session.calls),
               calls=session.calls, model=session.client.model, run_id=_CTX['run_id'],
               facts_version=task.get('facts_version', bundle.get('facts_version') if isinstance(bundle, dict) else None),
               offline=not args.online, n_assertions_uncapped=len(fresh), base_copies=[a for a in uncapped if a in base],
               truncated_assertions=fresh[args.max_tests:], n_assertions_dropped=max(0, len(fresh)-args.max_tests),
               **generated)
    atomic_json(done, row)
    return row


def cli(arm, generate, provenance, argv=None):
    config_path = HERE/arm/'config.json'
    defaults = json.loads(config_path.read_text())
    p = argparse.ArgumentParser(description=f'{arm}: offline (scripted) unless --online/--replay is given')
    p.add_argument('--tasks', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--k', type=int, default=defaults['k'])
    mode = p.add_mutually_exclusive_group()
    mode.add_argument('--online', action='store_true', help='shared Qwen client (explicit endpoint requests)')
    mode.add_argument('--replay', action='store_true', help='offline Qwen cache: replay --out/cache, fail on a miss')
    mode.add_argument('--responses', type=Path, help='offline JSON: task ID -> list of scripted responses')
    p.add_argument('--task-ids', nargs='+', help='optional subset; IDs are compared as strings')
    p.add_argument('--split', help='optional: keep only tasks of this split (e.g. dev)')
    p.add_argument('--llm-budget', type=int, default=defaults['llm_budget'], help='LLM calls per sample, ceiling 8')
    p.add_argument('--max-tests', type=int, default=defaults['max_tests'], help='assertions kept in generation order, ceiling 20')
    p.add_argument('--max-mutants', type=int, default=defaults.get('max_mutants', 32), help='MuTAP mutation-pool cap before base screening')
    p.add_argument('--max-surviving-mutants', type=int, default=defaults.get('max_surviving_mutants', 7),
                   help='MuTAP: at most N base-surviving mutants per sample')
    p.add_argument('--max-tokens', type=int, default=2048)
    p.add_argument('--seed', type=int, default=20261013)
    p.add_argument('--workers', type=int, default=1, help='samples generated in parallel processes')
    p.add_argument('--resume', action='store_true', help='continue a run with an identical manifest')
    args = p.parse_args(argv)
    args.online, args.replay = bool(args.online), bool(args.replay)
    if (args.k < 1 or not 0 <= args.llm_budget <= MAX_LLM_CALLS or not 1 <= args.max_tests <= MAX_ASSERTIONS
            or args.max_mutants < 1 or args.max_surviving_mutants < 1 or args.workers < 1 or args.max_tokens < 1):
        p.error('require k>=1, 0<=budget<=8, 1<=max-tests<=20, positive mutant/worker/token limits')
    bundle = json.loads(args.tasks.read_text())
    tasks = bundle['tasks'] if isinstance(bundle, dict) else bundle
    if args.split:
        tasks = [t for t in tasks if t.get('split', 'dev') == args.split]
    if args.task_ids:
        tasks = [t for t in tasks if str(t['task']) in args.task_ids]
        if {str(t['task']) for t in tasks} != set(args.task_ids):
            p.error('unknown task IDs (or excluded by --split)')
    if not tasks or len({str(t['task']) for t in tasks}) != len(tasks):
        p.error('empty/duplicate tasks')
    for t in tasks:
        for key in ('task', 'entry', 'put', 'base'):
            if key not in t:
                p.error(f'task {t.get("task")}: missing {key}')
        if not t['entry'].isidentifier():
            p.error('entry must be a callable module-level name')
    scripts = json.loads(args.responses.read_text()) if args.responses else {}
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    manifest = dict(version='paper-baselines-v3', arm=arm, k=args.k, online=args.online, replay=args.replay,
                    model=MODEL if (args.online or args.replay) else ScriptedClient.model,
                    llm_budget=args.llm_budget, max_tests=args.max_tests, max_mutants=args.max_mutants,
                    max_surviving_mutants=args.max_surviving_mutants,
                    max_tokens=args.max_tokens, temperature=0.7, top_p=0.95, seed=args.seed, split=args.split,
                    tasks_sha256=digest(tasks), scripts_sha256=digest(scripts),
                    source_sha256={str(f.relative_to(HERE)): hashlib.sha256(f.read_bytes()).hexdigest()
                                   for f in [HERE/'common.py', HERE/'worker.py', HERE/arm/'run.py', config_path]},
                    provenance=provenance())
    if (out/'manifest.json').exists():
        if not args.resume:
            p.error('output already contains a run; choose a fresh directory or pass --resume')
        if json.loads((out/'manifest.json').read_text()) != json.loads(json.dumps(manifest)):
            p.error('--resume: manifest differs (sources, tasks or options changed); use a fresh directory')
    run_id = digest(manifest)
    atomic_json(out/'manifest.json', manifest)
    atomic_json(out/'tasks.json', dict(bundle, tasks=tasks) if isinstance(bundle, dict) else dict(tasks=tasks))
    _CTX.clear()
    _CTX.update(args=args, tasks=tasks, arm=arm, generate=generate, out=out, cache=out/'cache', scripts=scripts,
                run_id=run_id, bundle=bundle)
    jobs = [(i, s) for i in range(len(tasks)) for s in range(args.k)]
    if args.workers == 1:
        rows = []
        for job in jobs:
            rows.append(_run_job(job))
            _report(arm, rows[-1])
    else:
        with ProcessPoolExecutor(args.workers, mp_context=multiprocessing.get_context('fork')) as pool:
            rows = []
            for row in pool.map(_run_job, jobs):
                rows.append(row)
                _report(arm, row)
    temp = out/'gen.pending.jsonl'
    temp.write_text(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in rows))
    temp.replace(out/'gen.jsonl')
    print(f'{len(rows)} rows -> {out / "gen.jsonl"}')


def _report(arm, row):
    print(f"{arm} task={row['task']} sample={row['sample']} calls={row['llm_calls']} "
          f"assertions={row['n_assertions']} stop={row['stop_reason']}", flush=True)
