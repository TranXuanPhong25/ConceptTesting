"""Sandboxed execution for ACH's rule-based checks. Run only as
    unshare -rn python -I -B sandbox_worker.py job.json out.json
(no network, isolated interpreter, minimal environment; see run.sandbox). Standalone: imports nothing local.

mode 'mutant': does the PUT / mutant build (define the entry point) and pass the existing tests (check())?
mode 'tests' : for each candidate assertion, its outcome on the PUT (repeated) and on the mutant, and whether
               the PUT and the mutant return different results for the calls the assertion makes.
"""
import contextlib
import copy
import io
import json
import resource
import signal
import sys


class Timeout(BaseException):
    pass


def _raise(signum, frame):
    raise Timeout()


@contextlib.contextmanager
def alarm(seconds):
    signal.signal(signal.SIGALRM, _raise)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


def dcopy(x):
    try:
        return copy.deepcopy(x)
    except Exception:
        return x


def same(a, b):
    try:
        r = a == b
        return r if isinstance(r, bool) else bool(r.all())
    except Exception:
        return False


def load(src, timeout):
    g = {'__name__': '__put__'}
    with contextlib.redirect_stdout(io.StringIO()), alarm(timeout):
        exec(compile(src, '<put>', 'exec'), g)
    return g


def status(exc):
    return 'timeout' if isinstance(exc, Timeout) else 'error:' + type(exc).__name__


def build(src, entry, base, timeout):
    r = dict(builds=False, passes=False, error=None)
    try:
        g = load(src, timeout)
        if not callable(g.get(entry)):
            r['error'] = f'{entry} not defined'
            return r, None
    except BaseException as exc:
        r['error'] = status(exc)
        return r, None
    r['builds'] = True
    try:
        tests = load(base, timeout)
        with contextlib.redirect_stdout(io.StringIO()), alarm(timeout):
            tests['check'](g[entry])
        r['passes'] = True
    except AssertionError:
        r['error'] = 'check failed'
    except BaseException as exc:
        r['error'] = status(exc)
    return r, g


def run_assert(src, g, entry, timeout):
    """Outcome of one assertion with `entry` bound to g[entry]; also the (args, kwargs) of every call."""
    calls, fn = [], g[entry]

    def wrapped(*a, **k):
        calls.append((dcopy(a), dcopy(k)))
        return fn(*a, **k)

    ns = dict(g)
    ns[entry] = wrapped
    try:
        with contextlib.redirect_stdout(io.StringIO()), alarm(timeout):
            exec('import math\n' + src, ns)
        return 'pass', calls
    except AssertionError:
        return 'fail', calls
    except BaseException as exc:
        return status(exc), calls


def call(fn, args, timeout):
    try:
        with contextlib.redirect_stdout(io.StringIO()), alarm(timeout):
            return 'ok', fn(*dcopy(args[0]), **dcopy(args[1]))
    except BaseException as exc:
        return status(exc), None


def main(job_path, out_path):
    try:
        resource.setrlimit(resource.RLIMIT_AS, (4 << 30, 4 << 30))
    except (ValueError, OSError):
        pass
    sys.setrecursionlimit(10000)
    job = json.load(open(job_path))
    entry, timeout = job['entry'], job.get('timeout', 5)
    if job['mode'] == 'mutant':
        put, _ = build(job['put'], entry, job['base'], timeout)
        mutant, _ = build(job['mutant'], entry, job['base'], timeout)
        result = dict(put=put, mutant=mutant)
    else:
        put_g, mut_g = load(job['put'], timeout), load(job['mutant'], timeout)
        result = []
        for src in job['assertions']:
            outcomes, calls = [], []
            for rep in range(job.get('repeats', 5)):
                outcome, got = run_assert(src, put_g, entry, timeout)
                outcomes.append(outcome)
                if rep == 0:
                    calls = got
                if outcome != outcomes[0]:
                    break
            calls_ok, differ = bool(calls), False
            for args in calls[:20]:
                p, m = call(put_g[entry], args, timeout), call(mut_g[entry], args, timeout)
                calls_ok = calls_ok and p[0] == 'ok'
                if p[0] != m[0] or (p[0] == 'ok' and not same(p[1], m[1])):
                    differ = True
            mutant_outcome, _ = run_assert(src, mut_g, entry, timeout)
            result.append(dict(source=src, put_outcomes=outcomes, put_calls=len(calls), put_calls_ok=calls_ok,
                               mutant_outcome=mutant_outcome, outputs_differ=differ))
    with open(out_path, 'w') as fh:
        json.dump(result, fh)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
