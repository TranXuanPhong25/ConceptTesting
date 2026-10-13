"""Execute only input-generator code; invoked under unshare -rn venv/python -I."""
import ast
import contextlib
import io
import json
import os
import random
import resource
import signal
import sys


class CallTimeout(BaseException):
    pass


def timed_out(signum, frame):
    raise CallTimeout()


def main(job_path, output_path):
    resource.setrlimit(resource.RLIMIT_AS, (512 << 20, 512 << 20))
    resource.setrlimit(resource.RLIMIT_FSIZE, (8 << 20, 8 << 20))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    job = json.load(open(job_path))
    result = dict(attempted=0, returned=0, duplicates=0, rejected=0, candidates=[], errors=[])
    signal.signal(signal.SIGALRM, timed_out)
    seen = {}
    try:
        ns = {"__name__": "__generator__"}
        signal.setitimer(signal.ITIMER_REAL, job["per_call_timeout"])
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            exec(compile(job["code"], "<generator>", "exec"), ns)
        signal.setitimer(signal.ITIMER_REAL, 0)
        fn = ns["sample_one"]
        random.seed(job["sample_seed"])
        for _ in range(job["n"]):
            result["attempted"] += 1
            signal.setitimer(signal.ITIMER_REAL, job["per_call_timeout"])
            try:
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    try:
                        value = fn()
                    except BaseException as exc:
                        if len(result["errors"]) < 3:
                            result["errors"].append(f"{type(exc).__name__}: {str(exc)[:300]}")
                        continue
                if type(value) not in (list, tuple) or len(value) != job["arity"]:
                    raise ValueError("sample_one must return a list/tuple with the PUT's arity")
                literal = repr(value)
                if len(literal) > 65536:
                    raise ValueError("input exceeds 65536 repr characters")
                restored = ast.literal_eval(literal)
                # tc_full_v2: no JSON round-trip (it rejected tuples, e.g. task 127 lost 400/400 inputs); inputs
                # travel as repr and are rebuilt with ast.literal_eval, so only the repr round-trip is required.
                if type(restored) is not type(value) or restored != value:
                    raise ValueError("input failed repr roundtrip")
                result["returned"] += 1
                if literal in seen:
                    result["duplicates"] += 1
                    result["candidates"][seen[literal]]["occurrences"] += 1
                else:
                    seen[literal] = len(result["candidates"])
                    result["candidates"].append(dict(input_repr=literal, occurrences=1))
            except (ValueError, TypeError, SyntaxError, OverflowError) as exc:
                result["rejected"] += 1
                if not result.get("first_rejection"):
                    result["first_rejection"] = f"{type(exc).__name__}: {str(exc)[:300]}"
            except BaseException as exc:
                if len(result["errors"]) < 3:
                    result["errors"].append(f"{type(exc).__name__}: {str(exc)[:300]}")
            finally:
                signal.setitimer(signal.ITIMER_REAL, 0)
    except BaseException as exc:
        result["errors"].append(f"{type(exc).__name__}: {str(exc)[:300]}")
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    with open(output_path, "w") as stream:
        json.dump(result, stream, allow_nan=False)


if __name__ == "__main__":
    main(*sys.argv[1:])
