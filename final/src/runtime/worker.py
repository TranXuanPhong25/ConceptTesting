"""Executed only inside a filesystem/network sandbox. No model/API credentials."""
from __future__ import annotations

import ast
import builtins
import contextlib
import copy
import inspect
import json
import math
import os
import random
import resource
import signal
import sys
import time

from contracts import SAFE_BUILTINS, validate_test


def execution_progress(mode=None, input_index=None):
    """Tell the parent whether a user call is active if SIGALRM cannot fire."""
    path = os.environ.get("FINAL_EXECUTION_PROGRESS")
    if path is not None:
        with open(path, "w") as handle:
            json.dump({"mode": mode, "input_index": input_index} if mode else {}, handle)


class Deadline(BaseException):
    pass


def expired(signum, frame):
    raise Deadline()


@contextlib.contextmanager
def deadline(seconds):
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


def frozen(value):
    """Typed, order-independent identity for dict/set input values."""
    if isinstance(value, dict):
        return ("dict", tuple(sorted(((frozen(k), frozen(v)) for k, v in value.items()), key=repr)))
    if isinstance(value, (list, tuple)):
        return (type(value).__name__, tuple(frozen(v) for v in value))
    if isinstance(value, (set, frozenset)):
        return (type(value).__name__, tuple(sorted((frozen(v) for v in value), key=repr)))
    return (type(value).__name__, repr(value))


def input_key(signature, args, kwargs):
    bound = signature.bind(*args, **kwargs)
    bound.apply_defaults()
    return repr(frozen(dict(bound.arguments)))


def load(source, entry, context=""):
    ns = {"__name__": "__candidate__"}
    if context:
        exec(compile(context, "<specification>", "exec"), ns)
    exec(compile(source, "/work/program.py", "exec"), ns)
    if not callable(ns.get(entry)):
        raise ValueError("Missing entry point")
    return ns


def base(job):
    calls, call_records = [], []
    cov = None
    if job.get('trace'):
        import coverage
        cov = coverage.Coverage(branch=True, data_file=None, include=['/work/program.py'])
        cov.start()
    result = {}
    try:
        with deadline(job["timeout"]):
            random.seed(job.get("seed", 0))
            ns = load(job["source"], job["entry"], job.get("context", ""))
            fn = ns[job["entry"]]
            test_ns = {}
            if job.get("context"):
                exec(compile(job["context"], "<specification>", "exec"), test_ns)
            signature = inspect.signature(test_ns.get(job["entry"], fn))

            def wrapped(*args, **kwargs):
                calls.append(input_key(signature, args, kwargs))
                bound = signature.bind(*args, **kwargs)
                bound.apply_defaults()
                if len(call_records) < 300:
                    call_records.append(dict(args=repr(args),kwargs=repr(kwargs),
                                             bound={k:repr(v) for k,v in bound.arguments.items()}))
                return fn(*args, **kwargs)

            # HumanEval/33 directly calls its entry point from check() as well
            # as calling candidate. Preserve that original base-suite behavior.
            test_ns[job["entry"]] = wrapped
            exec(compile(job["base"], "<base-tests>", "exec"), test_ns)
            random.seed(job.get("seed", 0))
            test_ns["check"](wrapped)
        result = {"status": "pass"}
    except Deadline:
        result = {"status": "timeout"}
    except AssertionError:
        result = {"status": "fail"}
    except BaseException as exc:
        result = {"status": "error", "exception": type(exc).__name__}
    finally:
        if cov:
            cov.stop()
            data = cov.get_data()
            result['coverage'] = dict(lines=sorted(data.lines('/work/program.py') or []),
                                      arcs=sorted(data.arcs('/work/program.py') or []))
    result.update(input_keys=sorted(set(calls)), calls=call_records)
    return result


def validate_input(record):
    if not isinstance(record, dict):
        raise ValueError('Input must be an object')
    for key in ('args','kwargs'):
        if not isinstance(record.get(key),str) or len(record[key]) > 16000:
            raise ValueError('Input literal too large or missing')
    args, kwargs = ast.literal_eval(record['args']), ast.literal_eval(record['kwargs'])
    if not isinstance(args,(list,tuple)) or not isinstance(kwargs,dict):
        raise ValueError('Need positional list/tuple and keyword dict')
    if not all(isinstance(k,str) for k in kwargs):
        raise ValueError('Keyword names must be strings')
    return args, kwargs


def domain_function(job):
    # Trusted EvalPlus contract, inserted as function body after the prompt.
    source = job['context'] + job.get('contract','') + '\n    return True\n'
    return load(source, job['entry'])[job['entry']]


def oracle(job):
    results = []
    for input_index, record in enumerate(job['tests']):
        try:
            with deadline(job['timeout']):
                args, kwargs = validate_input(record)
                domain = domain_function(job)
                signature = inspect.signature(domain)
                key = input_key(signature,args,kwargs)
                try:
                    domain(*copy.deepcopy(args),**copy.deepcopy(kwargs))
                except AssertionError:
                    results.append(dict(status='invalid_domain',input_key=key))
                    continue
                if job['mode'] == 'validate':
                    results.append(dict(status='valid',input_key=key))
                    continue
                random.seed(job.get('seed',0))
                fn = load(job['source'],job['entry'])[job['entry']]
                started = time.monotonic()
                execution_progress(job['mode'], input_index)
                value = fn(*copy.deepcopy(args),**copy.deepcopy(kwargs))
                duration = time.monotonic()-started
                literal = repr(value)
                if len(literal)>200000:
                    raise ValueError('Reference output too large')
                ast.literal_eval(literal)
                results.append(dict(status='ok',input_key=key,expected=literal,duration=duration))
        except Deadline:
            results.append(dict(status='timeout'))
        except BaseException as exc:
            results.append(dict(status='error',exception=type(exc).__name__))
        finally:
            execution_progress()
    return dict(tests=results)


def equivalent(job, args, kwargs, actual, expected):
    import numpy as np
    if job['entry']=='find_zero':
        #HumanEval task 32 https://github.com/evalplus/evalplus/blob/master/evalplus/eval/_special_oracle.py
        from evalplus.eval._special_oracle import _poly
        specification=load(job['context'],job['entry'])[job['entry']]
        bound=inspect.signature(specification).bind(*args,**kwargs)
        bound.apply_defaults()
        coefficients=next(iter(bound.arguments.values()))
        return abs(_poly(coefficients,actual)) <= job['atol']
    if actual == expected:
        return True
    atol = job.get('atol',0)
    # Follow EvalPlus 0.3.1 floating-point conventions; do not compare arbitrary roots.
    float_expected = isinstance(expected,float) or (isinstance(expected,(list,tuple)) and
                        bool(expected) and all(isinstance(x,float) for x in expected))
    if atol==0 and float_expected:
        atol=1e-6
    if atol and type(actual)==type(expected):
        if isinstance(expected,(list,tuple)) and len(actual)!=len(expected):
            return False
        return bool(np.allclose(actual,expected,rtol=1e-7,atol=atol))
    return False


def evaluate(job):
    results=[]
    for input_index, record in enumerate(job['tests']):
        try:
            with deadline(job['timeout']):
                random.seed(job.get('seed',0))
                args,kwargs=validate_input(record)
                expected=ast.literal_eval(record['expected'])
                ns=load(job['source'],job['entry'],job.get('context',''))
                execution_progress(job['mode'], input_index)
                actual=ns[job['entry']](*copy.deepcopy(args),**copy.deepcopy(kwargs))
                matched=equivalent(job,args,kwargs,actual,expected)
                results.append(dict(status='pass' if matched else 'fail',actual=repr(actual)[:2000]))
        except Deadline:
            results.append(dict(status='timeout'))
        except BaseException as exc:
            results.append(dict(status='error',exception=type(exc).__name__))
        finally:
            execution_progress()
    return dict(tests=results)


def control_flow(job):
    """Trace original source; output values never become generation feedback."""
    import coverage
    results = []
    for input_index, record in enumerate(job['tests']):
        observation = {'domain': 'unknown'}
        cov = None
        try:
            with deadline(job['timeout']):
                random.seed(job.get('seed', 0))
                args, kwargs = validate_input(record)
                domain = domain_function(job)
                try:
                    domain(*copy.deepcopy(args), **copy.deepcopy(kwargs))
                except Exception as error:
                    observation.update(domain='invalid', status='domain_rejected', exception=type(error).__name__)
                    continue
                observation['domain'] = 'valid'
                cov = coverage.Coverage(branch=True, data_file=None, include=['/work/program.py'])
                cov.start()
                namespace = load(job['source'], job['entry'], job.get('context', ''))
                execution_progress(job['mode'], input_index)
                namespace[job['entry']](*copy.deepcopy(args), **copy.deepcopy(kwargs))
                observation['status'] = 'executed'
        except Deadline:
            observation['status'] = 'timeout'
        except BaseException as error:
            observation.update(status='error', exception=type(error).__name__)
        finally:
            if cov:
                cov.stop()
                data = cov.get_data()
                observation['coverage'] = {'lines': sorted(data.lines('/work/program.py') or []),
                    'arcs': [list(arc) for arc in sorted(data.arcs('/work/program.py') or [])]}
            execution_progress()
            results.append(observation)
    return {'tests': results}


def cases(job):
    results = []
    for raw in job["tests"]:
        try:
            with deadline(job["timeout"]):
                random.seed(job.get("seed", 0))
                record = validate_test(raw)
                args = ast.literal_eval(record["args"])
                kwargs = ast.literal_eval(record["kwargs"])
                ns = load(job["source"], job["entry"], job.get("context", ""))
                fn = ns[job["entry"]]
                key = input_key(inspect.signature(fn), args, kwargs)
                result = fn(*copy.deepcopy(args), **copy.deepcopy(kwargs))
                env = {n: getattr(builtins, n) for n in SAFE_BUILTINS}
                env.update(result=result, args=args, kwargs=kwargs, math=math, __builtins__={})
                outcome = eval(compile(record["assertion"], "<predicate>", "eval"), env)
                if type(outcome) is not bool:
                    raise ValueError("Predicate must return bool")
                results.append({"status": "pass" if outcome else "fail", "input_key": key})
        except Deadline:
            results.append({"status": "timeout"})
        except BaseException as exc:
            results.append({"status": "error", "exception": type(exc).__name__})
    return {"tests": results}


def main():
    job = json.load(open(sys.argv[1]))
    resource.setrlimit(resource.RLIMIT_AS, (1024 << 20,) * 2)
    resource.setrlimit(resource.RLIMIT_FSIZE, (4 << 20,) * 2)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    resource.setrlimit(resource.RLIMIT_NPROC, (0, 0))
    signal.signal(signal.SIGALRM, expired)
    # Generated output cannot corrupt the result channel or fill memory.
    output = sys.stdout
    with open('/dev/null', 'w') as sink, contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
        if job['mode']=='base':
            result=base(job)
        elif job['mode'] in ('validate','oracle'):
            result=oracle(job)
        elif job['mode']=='evaluate':
            result=evaluate(job)
        elif job['mode']=='control_flow':
            result=control_flow(job)
        else:
            result=cases(job)
    json.dump(result, output)
    output.write("\n")


if __name__ == "__main__":
    main()
