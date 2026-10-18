"""Run model-written property / metamorphic code once in a clean isolated process. No network, bounded."""
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


def value(text):
    return None if text is None else ast.literal_eval(text)


def run(job):
    namespace = {'__name__': '__model_oracle__'}
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile(job['code'], '<model-oracle>', 'exec'), namespace)
        args = value(job['args_repr'])
        if job['mode'] == 'property':
            result = namespace['check'](copy.deepcopy(args), value(job.get('output_repr')), job.get('error'))
            return dict(status='ok', result=result is True, raw_type=type(result).__name__)
        if job['mode'] == 'follow':
            new = namespace['follow'](copy.deepcopy(args))
            text = repr(new)
            ast.literal_eval(text)  # follow-up must be a literal
            return dict(status='ok', args2_repr=text if len(text) <= 1000 else None)
        if job['mode'] == 'relation':
            result = namespace['relation'](copy.deepcopy(args), value(job.get('output_repr')),
                                           value(job['args2_repr']), value(job.get('output2_repr')))
            return dict(status='ok', result=result is True, raw_type=type(result).__name__)
    raise ValueError('mode')


def main():
    job = json.loads(Path(sys.argv[1]).read_text())
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_CPU, (job['timeout'] + 2,) * 2)

    def expire(*_):
        raise Deadline()
    signal.signal(signal.SIGALRM, expire)
    signal.alarm(job['timeout'])
    try:
        result = run(job)
    except BaseException as exc:
        result = dict(status='error', error=type(exc).__name__)
    finally:
        signal.alarm(0)
    Path(sys.argv[2]).write_text(json.dumps(result) + '\n')


if __name__ == '__main__':
    main()
