"""Cached specification-only mining and sandboxed semantic verification (v3m)."""
from __future__ import annotations

# Direct-script workers run with -I: establish this copy's package explicitly.
import sys as _package_sys
from pathlib import Path as _PackagePath
if not __package__:
    _package_here = _PackagePath(__file__).resolve().parent
    _package_sys.path.insert(0, str(_package_here.parents[2]))
    __package__ = "trickcatcher_linefacts.pipelines." + _package_here.name
from .paths import REPO as _REPO, DATA_OUT, CONFIG, dataset_paths

import ast
import copy
import doctest
import fcntl
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

from . import gen_inputs, precond_prompts
from .llm_client import atomic_json

ROOT = DATA_OUT / 'precond_qwen7b'
SEED = CONFIG["seeds"]["mining"]
SAFE_BUILTINS = ("abs", "all", "any", "bool", "dict", "enumerate", "float", "int", "isinstance", "len",
                 "list", "max", "min", "range", "reversed", "round", "set", "sorted", "str", "sum", "tuple", "type", "zip")
PURE_METHODS = {"isalnum", "isalpha", "isascii", "isdecimal", "isdigit", "islower", "isnumeric", "isspace",
                "istitle", "isupper", "startswith", "endswith", "count", "index", "lower", "upper", "strip",
                "lstrip", "rstrip", "split", "rsplit", "replace", "keys", "values", "items", "get"}


def sha(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode()).hexdigest()


def specification(task):
    fn = copy.deepcopy(next(n for n in ast.parse(task["put"]).body
                            if isinstance(n, ast.FunctionDef) and n.name == task["entry"]))
    doc = ast.get_docstring(fn, clean=False) or ""
    fn.decorator_list = []
    fn.body = [ast.Expr(ast.Constant(doc))]
    return ast.unparse(ast.fix_missing_locations(fn)), doc, fn.args


def json_list(raw):
    raw = re.sub(r"^```(?:json)?\s*\n|\n```\s*$", "", raw.strip())
    value = json.loads(raw)
    if not isinstance(value, list) or not all(isinstance(x, dict) for x in value):
        raise ValueError("mining response must be a JSON list of objects")
    return value


def norm(text):
    return " ".join(text.split())


def predicates(raw, ids, params):
    """Inspect syntax only. Execution is exclusively in namespace-isolated workers.
    Returns ({id: code}, [dropped]); a bad predicate is dropped alone, never the whole task."""
    raw = re.sub(r"^```(?:python|py)?\s*\n|\n```\s*$", "", raw.strip())
    try:
        tree = ast.parse(raw)
    except SyntaxError as exc:
        return {}, [dict(id=i, reason='code_unparsable', error=str(exc)) for i in ids]
    defs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    result, dropped = {}, []
    for pid in ids:
        if pid not in defs:
            dropped.append(dict(id=pid, reason='no_code'))
            continue
        try:
            result[pid] = predicate(defs[pid], pid, params)
        except (ValueError, TypeError) as exc:
            dropped.append(dict(id=pid, reason='code_rejected', error=str(exc)))
    return result, dropped


def predicate(fn, pid, params):
    """Model predicates may take any subset of the specification's parameters (by name); a wrapper with
    the original signature binds the call and passes that subset."""
    expected = [a.arg for a in params.posonlyargs + params.args + params.kwonlyargs]
    if fn.decorator_list:
        raise ValueError("only undecorated functions are allowed")
    actual = [a.arg for a in fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs]
    if fn.args.vararg or fn.args.kwarg or len(set(actual)) != len(actual) or not set(actual) <= set(expected):
        raise ValueError("predicate parameters are not a subset of the specification's parameters")
    fn = copy.deepcopy(fn)
    fn.name = pid + '_m'
    fn.args = ast.arguments(posonlyargs=[], args=[ast.arg(a) for a in actual], kwonlyargs=[], kw_defaults=[],
                            defaults=[], vararg=None, kwarg=None)
    fn.returns = None
    for node in ast.walk(fn):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.Try, ast.TryStar, ast.Global, ast.Nonlocal,
                             ast.ClassDef, ast.Lambda, ast.With, ast.AsyncWith, ast.Delete, ast.Raise,
                             ast.Yield, ast.YieldFrom, ast.Await, ast.AugAssign)):
            raise ValueError("unsupported predicate operation")
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node is not fn:
            raise ValueError("nested functions are forbidden")
        if isinstance(node, ast.Name) and node.id.startswith('__'):
            raise ValueError("private names are forbidden")
        if isinstance(node, ast.Attribute) and node.attr not in PURE_METHODS:
            raise ValueError("only pure builtin methods are allowed")
        if isinstance(node, (ast.Attribute, ast.Subscript)) and isinstance(node.ctx, ast.Store):
            raise ValueError("parameter mutation is forbidden")
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id not in SAFE_BUILTINS:
                raise ValueError("only builtin calls are allowed")
            if not isinstance(node.func, (ast.Name, ast.Attribute)):
                raise ValueError("indirect calls are forbidden")
    # Original calling convention/defaults; model annotations are never evaluated.
    wrapper_args = copy.deepcopy(params)
    for a in wrapper_args.posonlyargs + wrapper_args.args + wrapper_args.kwonlyargs:
        a.annotation = None
    for default in wrapper_args.defaults + [d for d in wrapper_args.kw_defaults if d is not None]:
        ast.literal_eval(default)
    call = ast.Call(ast.Name(fn.name, ast.Load()), [ast.Name(a, ast.Load()) for a in actual], [])
    wrapper = ast.FunctionDef(name=pid, args=wrapper_args, body=[ast.Return(call)], decorator_list=[], returns=None,
                              type_params=[])
    module = ast.Module([fn, wrapper], [])
    return ast.unparse(ast.fix_missing_locations(module)) + '\n'


def doc_inputs(doc, entry):
    result, skipped = [], []
    try:
        examples = doctest.DocTestParser().get_examples(doc)
    except ValueError:
        return [], ["unparsable doctest"]
    for example in examples:
        try:
            tree = ast.parse(example.source)
            calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                     and isinstance(n.func, ast.Name) and n.func.id == entry]
            if not calls:
                skipped.append(example.source)
            for node in calls:
                if any(k.arg is None for k in node.keywords):
                    raise ValueError("expanded kwargs")
                result.append((tuple(ast.literal_eval(n) for n in node.args),
                               {k.arg: ast.literal_eval(k.value) for k in node.keywords}))
        except (SyntaxError, ValueError, TypeError):
            skipped.append(example.source)
    return result, skipped


def isolated(job, directory, name, timeout=180, python=None):
    jp, op = directory / (name + '_job.json'), directory / (name + '.json')
    atomic_json(jp, job)
    op.unlink(missing_ok=True)
    return gen_inputs.sandbox(python or sys.executable, Path(__file__), jp, op, timeout)


def mine(task, client, root=ROOT, *, evidence_filter=True, python=None):
    if client.model != CONFIG['model']:
        raise ValueError('mining model differs from registered model')
    directory = Path(root).resolve() / str(task['task'])
    directory.mkdir(parents=True, exist_ok=True)
    spec, doc, params = specification(task)
    # Preserve old cache identity when the default evidence policy is selected.
    source_hashes = {p: sha((HERE/p).read_bytes()) for p in
                     ('precond_prompts.py', 'preconditions.py', 'tracer.py')}
    if evidence_filter:
        source_hashes['preconditions.py'] = '628058ccb7d0e337ca0cd98d95be9e9bb4ee504aa409da02ed38886ebc3b210e'
    policy = {} if evidence_filter else {'evidence_filter': False, 'preconditions_version': 'B5'}
    key = sha(json.dumps(dict(spec=spec, base=task['base'], put_sha256=sha(task['put']), model=client.model,
                             seed=SEED+task['task'], temperature=0, top_p=1,
                             sources=source_hashes, **policy), sort_keys=True))
    with (directory / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        summary_path = directory / 'summary.json'
        if summary_path.exists():
            summary = json.loads(summary_path.read_text())
            if summary['cache_key'] != key or summary['valid_sha256'] != sha((directory/'valid.py').read_bytes()):
                raise ValueError('mining cache changed; choose a fresh precondition directory')
            return summary
        (directory/'specification.py').write_text(spec+'\n')

        def query(stage, conditions=None):
            messages = precond_prompts.messages(stage, spec, conditions)
            atomic_json(directory/(stage+'_prompt.json'), messages)
            response = client.chat(messages, SEED+task['task'], temperature=0, top_p=1, max_tokens=4096)
            atomic_json(directory/(stage+'_response.json'), response)
            return response['text']

        def confirm():
            candidates = json_list(query('observation'))
            ids = [c.get('id') for c in candidates]
            if any(not isinstance(i, str) or not re.fullmatch(r'P[1-9][0-9]*', i) for i in ids) or len(set(ids)) != len(ids):
                raise ValueError('invalid candidate ids')
            if any(not isinstance(c.get('condition'), str) or not c['condition'].strip() for c in candidates):
                raise ValueError('invalid candidate condition')
            atomic_json(directory/'candidates.json', candidates)
            confirmations = json_list(query('confirmation', candidates)) if candidates else []
            if len(confirmations) != len(ids) or {c.get('id') for c in confirmations} != set(ids):
                raise ValueError('confirmation ids do not match observation')
            keep, dropped = [], []
            for c in candidates:
                decision = next(d for d in confirmations if d['id'] == c['id'])
                evidence = decision.get('evidence', '')
                if type(decision.get('keep')) is not bool or not isinstance(evidence, str):
                    raise ValueError('invalid confirmation schema')
                reason = 'confirmation_false' if not decision['keep'] else (
                    'evidence_not_in_specification' if evidence_filter and
                    (not norm(evidence) or norm(evidence) not in norm(spec)) else None)
                row = dict(c, evidence=evidence)
                (dropped if reason else keep).append(dict(row, reason=reason) if reason else row)
            atomic_json(directory/'confirmation.json', confirmations)
            return candidates, keep, dropped

        # A malformed observation/confirmation reply leaves the task unconstrained (always valid), recorded.
        try:
            candidates, keep, dropped = confirm()
            failure = None
        except (ValueError, TypeError, KeyError, AttributeError, json.JSONDecodeError) as exc:
            candidates, keep, dropped, failure = [], [], [], f'{type(exc).__name__}: {exc}'
        atomic_json(directory/'kept.json', keep)
        code, dropped_code = predicates(query('code', keep), [c['id'] for c in keep], params) if keep else ({}, [])
        (directory/'code.py').write_text('\n'.join(code.values()))
        verified = isolated(dict(mode='verify', task=task, code=code, doc=doc), directory, 'verifier', python=python)
        survivors = verified['survivors']
        final = '\n'.join(code[i] for i in survivors)
        final += '\ndef valid(*args, **kwargs):\n    return ' + (' and '.join(f'{i}(*args, **kwargs) is True' for i in survivors) or 'True') + '\n'
        (directory/'valid.py').write_text(final)
        summary = dict(task=task['task'], facts_version='v3m', model=client.model, cache_key=key,
                       candidates=len(candidates), confirmed=len(keep), coded=len(code), surviving=len(survivors),
                       mining_failure=failure, dropped_confirmation=dropped, dropped_code=dropped_code,
                       dropped_verifier=verified['dropped'],
                       valid_sha256=sha(final), seed=SEED+task['task'])
        if not evidence_filter:
            summary.update(evidence_filter=False, preconditions_version='B5')
        atomic_json(summary_path, summary)
        return summary


def load_predicate(code, name):
    """Call only in a sandbox worker, never in an orchestrator."""
    import builtins
    namespace = {'__builtins__': {n: getattr(builtins, n) for n in SAFE_BUILTINS}}
    exec(compile(code, '<mined>', 'exec'), namespace)
    return namespace[name]


def worker(job_path, output_path):
    from .tracer import alarm, dcopy, load_module, run_base
    job = json.loads(Path(job_path).read_text())
    task = job['task']
    with alarm(5):
        pg = load_module(task['put'])
    base, ok = run_base(pg[task['entry']], task['base'], ns=pg)
    if ok is not True:
        raise ValueError('base-test capture failed')
    docs, skipped = doc_inputs(job['doc'], task['entry'])
    known = [('base', a) for a in base] + [('docstring', a) for a in docs]
    survivors, dropped, log = [], [], []
    for pid, code in job['code'].items():
        with alarm(5):
            fn = load_predicate(code, pid)
        rejected = []
        for index, (source, (args, kwargs)) in enumerate(known):
            error = None
            try:
                with alarm(1):
                    accepted = fn(*dcopy(args), **dcopy(kwargs)) is True
            except BaseException as exc:
                accepted, error = False, type(exc).__name__
            row = dict(id=pid, index=index, source=source, input_repr=repr((args, kwargs)), accepted=accepted, error=error)
            log.append(row)
            if not accepted:
                rejected.append(row)
                break  # One counterexample suffices; do not spend further timeout budgets.
        if rejected:
            dropped.append(dict(id=pid, reason='known_valid_rejection', failures=rejected))
        else:
            survivors.append(pid)
    atomic_json(output_path, dict(survivors=survivors, dropped=dropped, log=log,
                                 n_base=len(base), n_docstring=len(docs), skipped_docstring=skipped))


if __name__ == '__main__':
    if len(sys.argv)>1 and sys.argv[1]=='mine':
        import argparse
        from . import run_v4, v4_runtime
        from .llm_client import Client
        ap=argparse.ArgumentParser()
        ap.add_argument('--no-evidence-filter',action='store_true',help='B5: retain evidence without substring rejection')
        ap.add_argument('--root',type=Path,required=True)
        ap.add_argument('--task-ids',type=int,nargs='+',required=True)
        ap.add_argument('--python',type=Path)
        args=ap.parse_args(sys.argv[2:])
        if args.no_evidence_filter: run_v4.safe_path(args.root)
        client=Client(args.root/'cache')
        for task in run_v4.task_sources(args.task_ids)[0]:
            mine(task,client,args.root,evidence_filter=not args.no_evidence_filter,
                 python=v4_runtime.interpreter(args.python) if args.no_evidence_filter else args.python)
    else:
        worker(*sys.argv[1:])
