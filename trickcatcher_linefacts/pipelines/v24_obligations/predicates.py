"""Restricted pure Python predicates, evaluated only by isolated resource-bound workers."""
import ast
import hashlib
import json
from pathlib import Path
import sys

from .common import D, digest, immutable, worker_identity
from .gen_inputs import sandbox
from .paths import CONFIG
from .isolated import run_once

HERE = Path(__file__).resolve().parent
PURE = ('Counter', 'all', 'any', 'bool', 'int', 'isinstance', 'len', 'list', 'max',
        'min', 'set', 'sorted', 'sum', 'tuple', 'type')
ALLOWED = (ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.Return,
           ast.Assign, ast.If, ast.Expr, ast.Name, ast.Load, ast.Store, ast.Constant,
           ast.Subscript, ast.Slice, ast.List, ast.Tuple, ast.Dict, ast.Set,
           ast.Call, ast.keyword, ast.Compare, ast.BoolOp, ast.UnaryOp, ast.BinOp,
           ast.And, ast.Or, ast.Not, ast.UAdd, ast.USub, ast.Add, ast.Sub, ast.Mult,
           ast.Div, ast.FloorDiv, ast.Mod, ast.Eq, ast.NotEq, ast.Lt, ast.LtE,
           ast.Gt, ast.GtE, ast.In, ast.NotIn, ast.Is, ast.IsNot, ast.IfExp,
           ast.GeneratorExp, ast.ListComp, ast.comprehension)


def validate_code(source, kind):
    if type(source) is not str or len(source.encode()) > 4096:
        raise ValueError('predicate_source_size')
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError, RecursionError) as exc:
        raise ValueError('predicate_syntax') from exc
    nodes = list(ast.walk(tree))
    if len(nodes) > 512 or any(not isinstance(n, ALLOWED) for n in nodes):
        raise ValueError('predicate_AST_policy')
    if len(tree.body) != 1 or type(tree.body[0]) is not ast.FunctionDef:
        raise ValueError('single_predicate_function')
    fn = tree.body[0]
    params = ['arguments', 'observation'] if kind == 'obligation' else ['arguments']
    if (fn.name != kind or [a.arg for a in fn.args.args] != params or fn.args.defaults
            or fn.args.posonlyargs or fn.args.kwonlyargs or fn.args.vararg or fn.args.kwarg
            or fn.decorator_list or fn.returns or any(a.annotation for a in fn.args.args)
            or sum(isinstance(n, ast.FunctionDef) for n in nodes) != 1):
        raise ValueError('predicate_signature')
    known = set(params) | set(PURE)
    for n in nodes:
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            if n.id in known or n.id.startswith('_'):
                raise ValueError('predicate_binding_mutation')
            known.add(n.id)
        if isinstance(n, ast.Assign) and (len(n.targets) != 1 or type(n.targets[0]) is not ast.Name):
            raise ValueError('predicate_mutation')
        if isinstance(n, (ast.GeneratorExp, ast.ListComp)) and len(n.generators) != 1:
            raise ValueError('nested_iteration_not_supported')
        if isinstance(n, ast.comprehension) and (n.is_async or type(n.target) is not ast.Name):
            raise ValueError('comprehension_policy')
        if isinstance(n, ast.Call) and (type(n.func) is not ast.Name or n.func.id not in PURE):
            raise ValueError('predicate_call_policy')
        if isinstance(n, ast.Constant) and type(n.value) is int and n.value.bit_length() > 128:
            raise ValueError('predicate_constant_size')
    for n in nodes:
        if isinstance(n, ast.Name) and (n.id not in known or n.id.startswith('_')):
            raise ValueError('predicate_unknown_name')
    return source


def evaluate(source, kind, rows, root):
    validate_code(source, kind)
    if len(rows) > D['max_predicate_rows']:
        raise ValueError('predicate_rows_cap')
    results = []
    policy = {n: hashlib.sha256((HERE / n).read_bytes()).hexdigest()
              for n in ('predicates.py', 'predicate_worker.py', 'isolated.py', 'binding.py', 'chain_inputs.py', 'config.json')}
    policy['interpreter'] = CONFIG['V4_PYTHON']
    policy['python'] = sys.version
    policy['worker_identity'] = worker_identity()
    for start in range(0, len(rows), D['predicate_batch']):
        batch = rows[start:start + D['predicate_batch']]
        job = {'source': source, 'kind': kind, 'rows': batch, 'policy': policy}
        folder = Path(root) / digest(job)
        jp, op = folder / 'job.json', folder / 'result.json'
        immutable(jp, job)
        result = run_once(HERE / 'predicate_worker.py', job, folder)
        if type(result) is not dict or type(result.get('rows')) is not list or len(result['rows']) != len(batch):
            results += [{'state': 'unknown', 'reason': 'predicate_worker_protocol'} for _ in batch]
        else:
            results += result['rows']
    return results
