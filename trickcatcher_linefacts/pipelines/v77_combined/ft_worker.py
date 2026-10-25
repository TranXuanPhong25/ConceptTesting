"""Batch execution of the PUT and its mutants on a list of inputs, in one isolated process (no network, bounded).

job: {sources: {name: code}, entry, inputs: [repr], order: [names], per_call_timeout, max_timeouts}
Output: {name: [outcome per input]}, outcome = ['ok', repr] | ['exception', TypeName] | ['timeout'] | ['skipped'].
A source that times out max_timeouts times is skipped for the remaining inputs. Timeouts use the wall clock
(signal.alarm), so a heavily loaded machine can change which calls time out; timeouts never count as a difference.
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


def outcome(fn, args, timeout):
    signal.alarm(timeout)
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            value = fn(*copy.deepcopy(args))
        text = repr(value)
        return ['ok', text if len(text) <= 4000 else text[:4000] + '...<truncated>']
    except Deadline:
        return ['timeout']
    except RecursionError:
        return ['exception', 'RecursionError']
    except BaseException as exc:
        return ['exception', type(exc).__name__]
    finally:
        signal.alarm(0)


def main():
    job = json.loads(Path(sys.argv[1]).read_text())
    resource.setrlimit(resource.RLIMIT_AS, (1024 * 1024 * 1024,) * 2)

    def expire(*_):
        raise Deadline()
    signal.signal(signal.SIGALRM, expire)
    inputs = [ast.literal_eval(x) for x in job['inputs']]
    result = {}
    for name in job['order']:
        namespace = {'__name__': '__ft_put__'}
        try:
            signal.alarm(job['per_call_timeout'] * 2)
            with contextlib.redirect_stdout(io.StringIO()):
                exec(compile(job['sources'][name], '<ft-put>', 'exec'), namespace)
            signal.alarm(0)
            fn = namespace[job['entry']]
        except BaseException as exc:
            signal.alarm(0)
            result[name] = [['exception', 'load:' + type(exc).__name__]] * len(inputs)
            continue
        rows, timeouts = [], 0
        for args in inputs:
            if timeouts >= job['max_timeouts']:
                rows.append(['skipped'])
                continue
            r = outcome(fn, args, job['per_call_timeout'])
            timeouts += r[0] == 'timeout'
            rows.append(r)
        result[name] = rows
    Path(sys.argv[2]).write_text(json.dumps(result) + '\n')


if __name__ == '__main__':
    main()
