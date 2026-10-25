"""Small evaluator-only worker for frozen v57 scoring.

It deliberately has no generation, tracing, model, or pipeline-config imports.
"""
import ast
import contextlib
import copy
import io
import json
from pathlib import Path
import resource
import signal
import sys


class Deadline(BaseException):
    pass


def literal_output(value):
    if value is None or type(value) in (bool, int, float, str):
        text = repr(value)
    elif type(value) in (list, tuple, dict):
        text = repr(value)
        ast.literal_eval(text)
    else:
        raise ValueError("unsupported_output_type")
    if len(text.encode()) > 8192:
        raise ValueError("output_size")
    return text


def main():
    job = json.loads(Path(sys.argv[1]).read_text())
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_CPU, (4, 4))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(Deadline()))
    signal.alarm(2)
    try:
        args = ast.literal_eval(job["input_repr"])
        if type(args) is not tuple:
            raise ValueError("arguments_not_tuple")
        namespace = {"__name__": "__v60_score__"}
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            try:exec(compile(job["source"], "<v60-score>", "exec"), namespace)
            except Deadline:raise
            except BaseException as exc:
                result={'status':'unresolved','reason':'module_load:'+type(exc).__name__}
                Path(sys.argv[2]).write_text(json.dumps(result)+'\n');return
            if job.get('kind')=='contract':
                checker=namespace.get('is_valid_test')
                if checker is None: raise ValueError('missing_validity_checker')
                accepted=checker(*copy.deepcopy(args))
                if type(accepted)is not bool: raise ValueError('nonboolean_validity_result')
                result={'status':'ok' if accepted else 'invalid','output_repr':'None','reason':'explicit_checker_boolean'}
                Path(sys.argv[2]).write_text(json.dumps(result)+'\n')
                return
            value = namespace[job["entry"]](*copy.deepcopy(args))
        try:
            result = {"status": "ok", "output_repr": literal_output(value)}
        except (ValueError,TypeError,RecursionError,SyntaxError):
            result={'status':'unresolved','reason':'output_serialization_failure'}
    except Deadline:
        result = {"status": "unresolved", "reason": "timeout"}
    except BaseException as exc:
        result = {"status": "exception", "exception_type": type(exc).__name__}
    finally:
        signal.alarm(0)
    Path(sys.argv[2]).write_text(json.dumps(result) + "\n")


if __name__ == "__main__":
    main()
