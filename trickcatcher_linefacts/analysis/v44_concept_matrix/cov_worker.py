"""Branch-arc coverage of one PUT per input with coverage.py, in an isolated process (no network, bounded).

job: {source, entry, inputs: [repr], per_call_timeout}. Output: {"arcs": [[[from, to], ...] | null per input], "measured": bool}. Module-level state (caches) can make
arcs depend on input order; inputs are run in the fixed pool order.
Only arcs executed during each call are recorded (module import is outside the measured window).
"""
import ast
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import resource
import signal
import sys

import coverage


class Deadline(BaseException):
    pass


def main():
    job = json.loads(Path(sys.argv[1]).read_text())
    resource.setrlimit(resource.RLIMIT_AS, (1024 * 1024 * 1024,) * 2)
    src = Path(sys.argv[1]).with_name('put_src.py')
    src.write_text(job['source'])

    def expire(*_):
        raise Deadline()
    signal.signal(signal.SIGALRM, expire)
    spec = importlib.util.spec_from_file_location('put_src', src)
    module = importlib.util.module_from_spec(spec)
    signal.alarm(10)
    with contextlib.redirect_stdout(io.StringIO()):
        spec.loader.exec_module(module)
    signal.alarm(0)
    fn = getattr(module, job['entry'])
    out, measured = [], False
    for lit in job['inputs']:
        args = ast.literal_eval(lit)
        cov = coverage.Coverage(branch=True, data_file=None, include=[str(src)])
        signal.alarm(job['per_call_timeout'])
        cov.start()
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                fn(*copy.deepcopy(args))
            ok = True
        except Deadline:
            ok = False
        except BaseException:
            ok = True  # an exception still executed arcs
        finally:
            cov.stop()
            signal.alarm(0)
        data = cov.get_data()
        measured = measured or str(src) in data.measured_files()
        out.append(sorted(data.arcs(str(src)) or []) if ok else None)
    Path(sys.argv[2]).write_text(json.dumps(dict(arcs=out, measured=measured)) + '\n')


if __name__ == '__main__':
    main()
