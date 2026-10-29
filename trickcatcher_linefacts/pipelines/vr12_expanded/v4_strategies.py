"""Strategy syntax checks and cached B5 domain mining. Generated code runs only in workers."""

# Direct-script workers run with -I: establish this copy's package explicitly.
import sys as _package_sys
from pathlib import Path as _PackagePath
if not __package__:
    _package_here = _PackagePath(__file__).resolve().parent
    _package_sys.path.insert(0, str(_package_here.parents[2]))
    __package__ = "trickcatcher_linefacts.pipelines." + _package_here.name
from .paths import REPO as _REPO, DATA_OUT, CONFIG, dataset_paths
import ast
import fcntl
import json
import re
from pathlib import Path
from . import gen_inputs, preconditions, v4_prompts, v4_runtime
from .llm_client import atomic_json

METHODS = preconditions.PURE_METHODS | {'join', 'map', 'filter', 'flatmap'}
STRATEGIES = {'booleans', 'integers', 'floats', 'text', 'characters', 'binary', 'none', 'just', 'sampled_from',
              'one_of', 'tuples', 'lists', 'sets', 'frozensets', 'dictionaries', 'fixed_dictionaries',
              'builds', 'recursive', 'deferred', 'from_regex', 'from_type', 'permutations'}
TYPES = {'List','Tuple','Dict','Set','FrozenSet','Optional','Union','Sequence','Any'}


def checked(raw):
    raw = re.sub(r'^```(?:python|py)?\s*\n|\n```\s*$', '', raw.strip())
    tree = ast.parse(raw)
    body = []
    for n in tree.body:
        if isinstance(n, ast.ImportFrom) and n.module == 'hypothesis' and n.level == 0 and len(n.names) == 1 and n.names[0].name == 'strategies' and (n.names[0].asname or n.names[0].name) == 'st':
            continue
        if isinstance(n, ast.Import) and len(n.names) == 1 and n.names[0].name == 'hypothesis.strategies' and n.names[0].asname == 'st':
            continue
        body.append(n)
    if len(body) != 1 or not isinstance(body[0], ast.FunctionDef) or body[0].name != 'strategy':
        raise ValueError('reply must contain only def strategy() and the optional st import')
    fn = body[0]
    if fn.args.args or fn.args.posonlyargs or fn.args.kwonlyargs or fn.args.vararg or fn.args.kwarg or fn.decorator_list or fn.returns:
        raise ValueError('strategy must be an undecorated zero-argument function without annotations')
    for n in ast.walk(fn):
        if isinstance(n, (ast.Import, ast.ImportFrom, ast.Try, ast.TryStar, ast.Global, ast.Nonlocal, ast.ClassDef,
                          ast.With, ast.AsyncWith, ast.Delete, ast.Raise, ast.Yield, ast.YieldFrom, ast.Await,
                          ast.AugAssign, ast.While, ast.For, ast.AsyncFunctionDef, ast.NamedExpr)):
            raise ValueError('unsupported strategy operation')
        if isinstance(n, ast.FunctionDef) and n is not fn:
            raise ValueError('nested definitions are unsupported; use lambdas')
        if isinstance(n, ast.Name) and n.id.startswith('_'):
            raise ValueError('private names are forbidden')
        if isinstance(n, (ast.Attribute, ast.Subscript)) and isinstance(n.ctx, ast.Store):
            raise ValueError('mutation is forbidden')
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store) and n.id in {'st'} | TYPES | set(preconditions.SAFE_BUILTINS):
            raise ValueError('cannot shadow a library or builtin')
        if isinstance(n, ast.Attribute):
            if isinstance(n.value, ast.Name) and n.value.id == 'st':
                if n.attr not in STRATEGIES:
                    raise ValueError('unsupported st strategy')
            elif n.attr not in METHODS:
                raise ValueError('only pure builtin and strategy methods are allowed')
        if isinstance(n, ast.Call):
            if isinstance(n.func, ast.Name) and n.func.id not in preconditions.SAFE_BUILTINS:
                raise ValueError('only pure builtin and st calls are allowed')
            if not isinstance(n.func, (ast.Name, ast.Attribute)):
                raise ValueError('indirect calls are forbidden')
    tree.body = body
    return ast.unparse(tree) + '\n'


def fallback_source(task):
    args = preconditions.specification(task)[2]
    annotations, missing = [], []
    for a in args.posonlyargs + args.args:
        node = a.annotation
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            node = ast.parse(node.value, mode='eval').body
        if node is None:
            missing.append(a.arg); annotations.append('object'); continue
        for n in ast.walk(node):
            if not isinstance(n, (ast.Name, ast.Subscript, ast.Tuple, ast.Load, ast.Constant, ast.BinOp, ast.BitOr)):
                raise ValueError('unsupported annotation in from_type fallback')
            if isinstance(n, ast.Name) and n.id not in TYPES | {'int','float','str','bool','list','tuple','dict','set','frozenset','bytes','object'}:
                raise ValueError('unknown annotation in from_type fallback')
        annotations.append(ast.unparse(node))
    return 'def strategy():\n    return st.tuples(' + ', '.join('st.from_type('+a+')' for a in annotations) + ')\n', missing


def draws(code, task, directory, python, sample_seed, n=100, cap=500, base=()):
    return v4_runtime.isolated('draw', dict(code=code, task=task, seed=sample_seed, n=n, cap=cap,
                                          exclude=list(base)), directory, python, timeout=180)


def mine(task, client, precond_dir, root, python):
    if client.model != CONFIG['model']:
        raise ValueError('strategy model differs from registered model')
    pd = Path(precond_dir)/str(task['task'])
    summary = json.loads((pd/'summary.json').read_text())
    if summary.get('evidence_filter') is not False or summary.get('preconditions_version') != 'B5':
        raise ValueError('v4 requires B5 preconditions, mined with evidence_filter=False')
    valid = (pd/'valid.py').read_text()
    if preconditions.sha(valid) != summary['valid_sha256']:
        raise ValueError('validator hash mismatch')
    survivors = set(json.loads((pd/'verifier.json').read_text())['survivors'])
    conditions = [x['condition'] for x in json.loads((pd/'kept.json').read_text()) if x['id'] in survivors]
    task = dict(task, mined_valid_src=valid)
    messages = v4_prompts.domain_messages(task, conditions)
    key = preconditions.sha(json.dumps(dict(messages=messages, valid=valid, model=client.model,
                           tools=v4_runtime.VERSIONS, seed=CONFIG["seeds"]["mining"]+task['task'],
                           sources={p: preconditions.sha((v4_runtime.HERE/p).read_bytes()) for p in
                                    ('v4_strategies.py','v4_worker.py','v4_prompts.py')}), sort_keys=True))
    directory = Path(root).resolve()/str(task['task']); directory.mkdir(parents=True, exist_ok=True)
    with (directory/'.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        saved = directory/'summary.json'
        if saved.exists():
            result = json.loads(saved.read_text())
            if result['cache_key'] != key or result['strategy_sha256'] != preconditions.sha((directory/'strategy.py').read_bytes()):
                raise ValueError('strategy cache changed; choose a fresh directory')
            return result
        errors, responses = [], []
        fallback = False
        for retry in range(2):
            d = directory/f'attempt_{retry}'; d.mkdir(exist_ok=True)
            atomic_json(d/'prompt.json', messages)
            response = client.chat(messages, CONFIG["seeds"]["mining"]+task['task'], temperature=0, top_p=1, max_tokens=4096)
            atomic_json(d/'response.json', response); responses.append(response)
            try:
                code = checked(response['text'])
                verification = draws(code, task, d, python, CONFIG["seeds"]["mining"]+task['task'])
                if verification['nonliteral'] or verification['wrong_arity'] or not verification['candidates'] or verification['errors']:
                    raise ValueError(json.dumps({k: verification[k] for k in ('nonliteral','wrong_arity','valid','errors')}))
                break
            except (SyntaxError, ValueError, RuntimeError) as exc:
                error = str(exc); errors.append(error)
                messages += [{'role':'assistant','content':response['text']},
                             {'role':'user','content':v4_prompts.RETRY.format(error=error)}]
        else:
            fallback = True
            code, missing = fallback_source(task)
            verification = draws(code, task, directory/'fallback', python, CONFIG["seeds"]["mining"]+task['task'])
        (directory/'strategy.py').write_text(code)
        result = dict(task=task['task'], cache_key=key, strategy_sha256=preconditions.sha(code),
                      valid_sha256=summary['valid_sha256'], fallback=fallback, missing_annotations=missing if fallback else [],
                      conditions=conditions, errors=errors, verification=verification,
                      llm_calls=len(responses), n_in=sum(r['n_in'] for r in responses), n_out=sum(r['n_out'] for r in responses))
        atomic_json(saved, result)
        return result
