"""Executed only inside a filesystem/network sandbox. No model/API credentials."""
from __future__ import annotations

import ast
import builtins
import contextlib
import copy
import inspect
import json
import math
import random
import resource
import signal
import sys

from contracts import SAFE_BUILTINS, validate_test


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
    exec(compile(source, "<solution>", "exec"), ns)
    if not callable(ns.get(entry)):
        raise ValueError("Missing entry point")
    return ns


def base(job):
    calls = []
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
                return fn(*args, **kwargs)

            # HumanEval/33 directly calls its entry point from check() as well
            # as calling candidate. Preserve that original base-suite behavior.
            test_ns[job["entry"]] = wrapped
            exec(compile(job["base"], "<base-tests>", "exec"), test_ns)
            random.seed(job.get("seed", 0))
            test_ns["check"](wrapped)
        return {"status": "pass", "input_keys": sorted(set(calls))}
    except Deadline:
        return {"status": "timeout", "input_keys": sorted(set(calls))}
    except AssertionError:
        return {"status": "fail", "input_keys": sorted(set(calls))}
    except BaseException as exc:
        return {"status": "error", "exception": type(exc).__name__, "input_keys": sorted(set(calls))}


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
        result = base(job) if job["mode"] == "base" else cases(job)
    json.dump(result, output)
    output.write("\n")


if __name__ == "__main__":
    main()
