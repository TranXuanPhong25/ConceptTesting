"""Copied into bwrap, never imported in the host process."""
import ast
import contextlib
import json
import math
import random


def encode(value):
    if type(value) in (str, bool, int, type(None)):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if type(value) in (list, tuple):
        return {'python_type':'tuple', 'items':[encode(x) for x in value]} if type(value) is tuple else [encode(x) for x in value]
    if type(value) is dict:
        return {'python_type':'dict', 'items':[[encode(k), encode(value[k])] for k in sorted(value, key=lambda k: (type(k).__name__, repr(k)))]}
    if type(value) in (set, frozenset):
        return {'python_type':type(value).__name__, 'items':sorted([encode(x) for x in value], key=repr)}
    raise ValueError('unsupported reference output')


if __name__ == '__main__':
    with open('/work/job.json') as handle:
        job = json.load(handle)
    namespace = {'__name__':'__candidate__'}
    random.seed(271828)
    with open('/dev/null', 'w') as sink, contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
        exec(compile(open('/work/program.py').read(), '/work/program.py', 'exec'), namespace)
        if job['base'] is not None:
            exec(compile(job['base'], '<base-tests>', 'exec'), namespace)
        else:
            record = job['input']
            result = namespace[job['entry']](*ast.literal_eval(record['args']), **ast.literal_eval(record['kwargs']))
            with open('/results/ct-result.json', 'w') as handle:
                json.dump(encode(result), handle, allow_nan=False)
