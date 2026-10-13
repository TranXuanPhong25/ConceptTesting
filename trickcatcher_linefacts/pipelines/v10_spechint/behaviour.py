"""Cached behavioural mining; model code and base capture execute only in workers."""
from __future__ import annotations
import sys
from pathlib import Path
if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = 'trickcatcher_linefacts.pipelines.' + Path(__file__).resolve().parent.name

import ast
import copy
import fcntl
import json
import re
from . import behaviour_prompts, gen_inputs, preconditions
from .paths import CONFIG, HERE, DATA_OUT
from .llm_client import atomic_json

SEED = CONFIG['seeds']['mining']
ROOT = DATA_OUT / 'behaviour'


def _norm(text):
    # Amendment 1: verbatim check up to whitespace (docstrings wrap lines and indent).
    return re.sub(r'\s+', ' ', text).strip()


def checked_predicate(raw, name, params):
    """Reuse the precondition miner's pure-code gate and calling-convention wrapper."""
    raw = re.sub(r'^```(?:python|py)?\s*\n|\n```\s*$', '', raw.strip())
    tree = ast.parse(raw)
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef) or tree.body[0].name != name:
        raise ValueError(f'expected only def {name}')
    fn = tree.body[0]
    expected = [a.arg for a in params.posonlyargs + params.args + params.kwonlyargs]
    actual = [a.arg for a in fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs]
    if len(actual) != len(expected) or fn.args.vararg or fn.args.kwarg:
        raise ValueError('predicate must take all specification parameters in order')
    if actual != expected:
        # Amendment 1: Qwen often renames parameters (e.g. D(xs) for make_palindrome(string)); same arity ->
        # rename positionally, references included, then apply the unchanged gate.
        mapping = dict(zip(actual, expected))
        if len(set(actual)) != len(actual) or (set(expected) - set(mapping)) & {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}:
            raise ValueError('predicate must take all specification parameters in order')
        class _Rename(ast.NodeTransformer):
            def visit_Name(self, node):
                return ast.copy_location(ast.Name(id=mapping.get(node.id, node.id), ctx=node.ctx), node)
        fn = _Rename().visit(fn)
        all_args = fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs
        for a, new_name in zip(all_args, expected):
            a.arg = new_name
        ast.fix_missing_locations(fn)
    return preconditions.predicate(fn, name, params)


def output_params(params):
    args = copy.deepcopy(params)
    if 'out' in [a.arg for a in args.posonlyargs + args.args + args.kwonlyargs]:
        raise ValueError('reserved output parameter conflicts with specification')
    args.kwonlyargs.append(ast.arg(arg='out'))
    args.kw_defaults.append(None)
    return args


def isolated(job, directory, name, python=None, timeout=600):
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    jp, op = directory / (name + '_job.json'), directory / (name + '.json')
    atomic_json(jp, job)
    op.unlink(missing_ok=True)
    return gen_inputs.sandbox(python or sys.executable, Path(__file__), jp, op, timeout)


def mine(task, client, root=ROOT, *, k=CONFIG['K'], python=None):
    if client.model.lower() not in ('qwen2.5-coder-7b-instruct', 'qwen/qwen2.5-coder-7b-instruct'):
        raise ValueError('behaviour mining requires Qwen2.5-Coder-7B-Instruct')
    if not 1 <= k < 1000:
        raise ValueError('K must be 1..999')
    spec, _, params = preconditions.specification(task)
    directory = Path(root).resolve() / str(task['task']); directory.mkdir(parents=True, exist_ok=True)
    sources = {p: preconditions.sha((HERE / p).read_bytes()) for p in
               ('behaviour.py', 'behaviour_prompts.py', 'preconditions.py', 'tracer.py')}
    key = preconditions.sha(json.dumps(dict(spec=spec, base=task['base'],
        put_sha256=preconditions.sha(task['put']), model=client.model, k=k,
        seed=SEED + task['task'], temperature=0, top_p=1, sources=sources), sort_keys=True))
    with (directory / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        saved = directory / 'summary.json'
        if saved.exists():
            summary = json.loads(saved.read_text())
            if summary['cache_key'] != key or summary['requirements_sha256'] != preconditions.sha((directory / 'requirements.json').read_bytes()):
                raise ValueError('behaviour mining cache changed; choose a fresh directory')
            return summary
        (directory / 'specification.py').write_text(spec + '\n')
        merged, seen, samples = [], {}, []
        for sample in range(k):
            d = directory / f'sample_{sample}'; d.mkdir(exist_ok=True)
            seed = SEED + task['task'] + 100000 * sample

            def query(stage, rows=None):
                messages = behaviour_prompts.messages(stage, spec, rows)
                atomic_json(d / (stage + '_prompt.json'), messages)
                response = client.chat(messages, seed, temperature=0, top_p=1, max_tokens=4096)
                atomic_json(d / (stage + '_response.json'), response)
                return preconditions.json_list(response['text'])

            dropped, coded, failure = [], [], None
            try:
                candidates = query('observation')
                ids = [c.get('id') for c in candidates]
                if any(not isinstance(i, str) or not re.fullmatch(r'B[1-9][0-9]*', i) for i in ids) or len(set(ids)) != len(ids):
                    raise ValueError('invalid behavioural candidate ids')
                if any(not isinstance(c.get('statement'), str) or not c['statement'].strip() or
                       not isinstance(c.get('quote'), str) for c in candidates):
                    raise ValueError('invalid behavioural candidate schema')
                decisions = query('confirmation', candidates) if candidates else []
                if len(decisions) != len(ids) or {r.get('id') for r in decisions} != set(ids):
                    raise ValueError('confirmation ids do not match observation')
                kept = []
                for c in candidates:
                    decision = next(r for r in decisions if r['id'] == c['id'])
                    if type(decision.get('keep')) is not bool or not isinstance(decision.get('quote'), str):
                        raise ValueError('invalid confirmation schema')
                    reason = ('confirmation_false' if not decision['keep'] else
                              'quote_changed' if decision['quote'] != c['quote'] else
                              'quote_not_in_specification' if not c['quote'].strip() or _norm(c['quote']) not in _norm(spec) else None)
                    if reason: dropped.append(dict(c, reason=reason))
                    else: kept.append(c)
                code_rows = query('code', kept) if kept else []
                if len(code_rows) != len(kept) or {r.get('id') for r in code_rows} != {c['id'] for c in kept}:
                    raise ValueError('code ids do not match confirmed requirements')
                for c in kept:
                    row = next(r for r in code_rows if r['id'] == c['id'])
                    try:
                        D = checked_predicate(row['D'], 'D', params)
                        R = checked_predicate(row['R'], 'R', output_params(params)) if row.get('R') is not None else None
                        coded.append(dict(c, D_src=D, R_src=R))
                    except (ValueError, TypeError, KeyError, AttributeError, SyntaxError) as exc:
                        dropped.append(dict(c, reason='code_rejected', error=str(exc)))
            except (ValueError, TypeError, KeyError, AttributeError, json.JSONDecodeError) as exc:
                failure = f'{type(exc).__name__}: {exc}'
                coded = []
            verified = isolated(dict(mode='verify', task=task, requirements=coded), d, 'verifier', python)
            dropped += verified['dropped']
            for r in verified['requirements']:
                identity = json.dumps([r['quote'], r['statement'], r['D_src'], r['R_src']])
                if identity in seen:
                    merged[seen[identity]]['samples'].append(sample)
                else:
                    seen[identity] = len(merged)
                    merged.append(dict(r, id=f'B{len(merged)+1}', samples=[sample]))
            samples.append(dict(sample=sample, seed=seed, surviving=len(verified['requirements']),
                                dropped=dropped, mining_failure=failure, n_base=verified['n_base']))
        atomic_json(directory / 'requirements.json', merged)
        summary = dict(task=task['task'], version=CONFIG['VERSION'], model=client.model, cache_key=key,
                       k=k, surviving=len(merged), samples=samples,
                       requirements_sha256=preconditions.sha((directory / 'requirements.json').read_bytes()))
        atomic_json(saved, summary)
        return summary


def base_pairs(task):
    from .tracer import alarm, dcopy, load_module, run_base
    with alarm(5):
        pg = load_module(task['put']); put = pg[task['entry']]
    pairs = []

    def capture(*args, **kwargs):
        inputs = (dcopy(args), dcopy(kwargs))
        out = put(*args, **kwargs)
        pairs.append((inputs, dcopy(out)))
        return out

    _, ok = run_base(capture, task['base'], ns=pg)
    if ok is not True or not pairs:
        raise ValueError('base input/output capture failed or empty')
    return pairs


def verify(task, requirements):
    from .tracer import alarm, dcopy
    pairs = base_pairs(task)
    kept, dropped = [], []
    # Recheck syntax inside the isolated process as in the precondition miner.
    params = preconditions.specification(task)[2]
    for r in requirements:
        reason, error = None, None
        try:
            for name in ('D', 'R'):
                src = r.get(name + '_src')
                if src is not None:
                    parameters = params if name == 'D' else output_params(params)
                    tree = ast.parse(src)
                    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name + '_m')
                    preconditions.predicate(fn, name, parameters)
            with alarm(5):
                D = preconditions.load_predicate(r['D_src'], 'D')
                R = preconditions.load_predicate(r['R_src'], 'R') if r.get('R_src') else None
            for (args, kwargs), out in pairs:
                reason = 'D_crashes_on_base'
                with alarm(1): value = D(*dcopy(args), **dcopy(kwargs))
                reason = 'D_nonboolean_on_base'
                if type(value) is not bool: break
                if R is not None:
                    reason = 'R_fails_on_base'
                    with alarm(1): accepted = R(*dcopy(args), **dcopy(kwargs), out=dcopy(out))
                    if accepted is not True: break
                reason = None
        except BaseException as exc:
            error = type(exc).__name__
            reason = reason or 'predicate_load_failed'
        if reason: dropped.append(dict(id=r['id'], reason=reason, error=error))
        else: kept.append(r)
    return dict(requirements=kept, dropped=dropped, n_base=len(pairs))


def worker(job_path, output_path):
    job = json.loads(Path(job_path).read_text())
    if job['mode'] == 'verify': result = verify(job['task'], job['requirements'])
    elif job['mode'] == 'facts':
        from .behav_facts import build
        result = build(job['task'], job['requirements'])
    elif job['mode'] == 'offline':
        from .offline_behav import measure
        result = measure(job['task'], job['hep'])
    else: raise ValueError(job['mode'])
    atomic_json(output_path, result)


if __name__ == '__main__': worker(*sys.argv[1:])
