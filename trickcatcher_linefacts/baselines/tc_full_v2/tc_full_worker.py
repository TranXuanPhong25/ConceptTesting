"""TrickCatcher execution worker. Launch only through unshare -rn python -I -B."""
import ast
import contextlib
import copy
import io
import importlib.metadata
import json
import resource
import signal
import sys
from pathlib import Path


class CallTimeout(BaseException):
    pass


def expired(*_):
    raise CallTimeout()


# Analysis/utils.py:to_hashable, including its dictionary conversion.
def to_hashable(obj):
    if isinstance(obj, (list, tuple)):
        return tuple(to_hashable(item) for item in obj)
    if isinstance(obj, dict):
        return frozenset((key, to_hashable(value)) for key, value in obj.items())
    return obj


def same(a, b):
    return bool(to_hashable(a) == to_hashable(b))


def timed(fn, seconds):
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return 'ok', fn()
    except BaseException as exc:
        return type(exc).__name__, None
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


def load(src, entry, seconds):
    ns = {'__name__': '__tc_program__'}
    status, _ = timed(lambda: exec('from typing import *\nimport math\n' + src, ns), seconds)
    fn = ns.get(entry) if status == 'ok' else None
    return ('ok', fn) if callable(fn) else (status if status != 'ok' else 'MissingFunction', None)


def base_filter(job):
    kept, records = [], []
    for variant in job['variants']:
        status, fn = load(variant['src'], job['entry'], job['load_timeout'])
        if status == 'ok':
            def check():
                ns = {'__name__': '__tc_base__'}
                exec(job['base'], ns)
                ns['check'](fn)
            status, _ = timed(check, job['base_timeout'])
        records.append(dict(index=variant['index'], status=status))
        if status == 'ok':
            kept.append(variant)
    return dict(survivors=kept, base_results=records)


# Container assertions express the artifact's equality rather than Python's
# list-versus-tuple inequality. The source remains self-contained for readers.
NORMALIZER = '''def _tc_output(obj):
    if isinstance(obj, (list, tuple)):
        return tuple(_tc_output(item) for item in obj)
    if isinstance(obj, dict):
        return frozenset((key, _tc_output(value)) for key, value in obj.items())
    return obj
'''


def assertion(entry, args, value):
    literal = repr(value)
    # No execution of an output repr: only literal, round-trippable expectations.
    restored = ast.literal_eval(literal)
    if not same(restored, value):
        raise ValueError('nonliteral output')
    call = entry + '(' + ', '.join(repr(a) for a in args) + ')'
    if isinstance(value, (list, tuple, dict)):
        return NORMALIZER + f'assert _tc_output({call}) == _tc_output({literal})'
    return f'assert {call} == {literal}'


def execute(job):
    entry, seconds = job['entry'], job['call_timeout']
    ps, put = load(job['put'], entry, job['load_timeout'])
    cs, canon = load(job['canon'], entry, job['load_timeout'])
    vs, validator = load(job['contract_src'], entry, job['load_timeout'])
    if cs != 'ok' or vs != 'ok':
        raise ValueError(f'canonical/contract load failed: {cs}/{vs}')
    variants = [(v['index'], *load(v['src'], entry, job['load_timeout'])) for v in job['variants']]
    records = []
    for candidate in job['pool']:
        args = ast.literal_eval(candidate['input_repr'])
        run = lambda fn: timed(lambda: fn(*copy.deepcopy(args)), seconds)
        pstatus, pv = run(put) if ps == 'ok' else (ps, None)
        cstatus, cv = run(canon)
        valid_status, _ = run(validator)
        row = dict(input_repr=candidate['input_repr'], put_status=pstatus, canon_status=cstatus,
                   valid=valid_status == 'ok', contract_status=valid_status, groups=[], variants=[])
        groups = []
        for index, status, fn in variants:
            status, value = run(fn) if status == 'ok' else (status, None)
            rec = dict(index=index, status=status, agrees=None)
            if status == 'ok' and pstatus == 'ok':
                eqstatus, agrees = timed(lambda: same(pv, value), seconds)
                rec['agrees'] = agrees if eqstatus == 'ok' else None
                if eqstatus != 'ok':
                    rec['status'] = eqstatus
                elif not agrees:
                    found = next((g for g in groups if same(g['value'], value)), None)
                    if found is None:
                        found = dict(value=copy.deepcopy(value), members=[])
                        groups.append(found)
                    found['members'].append(index)
            row['variants'].append(rec)
        # PUT failures cannot supply output_0; those inputs are discarded.
        for group in groups:
            status, correct = timed(lambda: same(cv, group['value']), seconds) if cstatus == 'ok' else (cstatus, False)
            status_src, src = timed(lambda: assertion(entry, args, group['value']), seconds)
            row['groups'].append(dict(members=group['members'], expected_repr=repr(group['value']),
                                      correct=status == 'ok' and correct, tp=valid_status == 'ok' and status == 'ok' and correct,
                                      src=src if status_src == 'ok' else None, serialization_status=status_src))
        if groups:
            best = max(range(len(groups)), key=lambda i: len(groups[i]['members']))
            group = row['groups'][best]
            if group['src'] is None:
                row['emit_error'] = group['serialization_status']
            else:
                row['assertion'] = dict(src=group['src'], canon='ok' if group['tp'] else
                                        ('contract-invalid' if not row['valid'] else
                                         ('fail' if cstatus == 'ok' else cstatus)), put='fail', hits=[],
                                        input_valid=row['valid'], expected=group['expected_repr'],
                                        members=group['members'])
        records.append(row)
    return dict(records=records)


def main(job_path, output_path):
    resource.setrlimit(resource.RLIMIT_AS, (512 << 20, 512 << 20))
    resource.setrlimit(resource.RLIMIT_FSIZE, (8 << 20, 8 << 20))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    signal.signal(signal.SIGALRM, expired)
    job = json.loads(Path(job_path).read_text())
    if job['mode'] == 'environment':
        import cyaron
        result = dict(python=sys.version, cyaron=importlib.metadata.version('cyaron'))
    else:
        result = base_filter(job) if job['mode'] == 'filter' else execute(job)
    Path(output_path).write_text(json.dumps(result, allow_nan=False))


if __name__ == '__main__':
    main(*sys.argv[1:])
