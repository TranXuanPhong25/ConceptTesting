"""Network-isolated CPython replay of a realized witness: instrumented and uninstrumented, twice."""
import contextlib
import copy
import io
import json
import resource
import signal
import sys
from pathlib import Path


class Deadline(BaseException):
    pass


def execute(pkg, source, entry, args, hypothesis, variant, instrumented):
    recorder = pkg.path_instrument.Recorder() if instrumented else None
    try:
        signal.alarm(4)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            program = pkg.path_instrument.load_program(source, entry, hypothesis, variant=variant, recorder=recorder)
            result = program(*copy.deepcopy(args))
        row = {'status': 'ok', 'output': pkg.value_graph.encode(result, observation=True)}
    except Deadline:
        row = {'status': 'timeout'}
    except BaseException as exc:
        row = {'status': 'error', 'reason': type(exc).__name__ + ':' + str(exc)[:160]}
    finally:
        signal.alarm(0)
    if instrumented:
        row.update(branches=[list(x) for x in recorder.branches],
                   events=[dict(frame=b[1], prestate=pkg.value_graph.encode(dict(b[2]), observation=True),
                                value=pkg.value_graph.encode(v, observation=True), branch_prefix=b[3])
                           for b, v in recorder.events])
    return row, recorder


def once(pkg, request):
    args = pkg.value_graph.decode(request['arguments'])
    source, entry, h = request['source'], request['entry'], request['hypothesis']
    put, put_rec = execute(pkg, source, entry, args, h, False, True)
    alt, alt_rec = execute(pkg, source, entry, args, h, True, True)
    plain_put, _ = execute(pkg, source, entry, args, h, False, False)
    plain_alt, _ = execute(pkg, source, entry, args, h, True, False)
    index = None
    if put['status'] == 'ok' and alt['status'] == 'ok':
        same = lambda a, b: type(a) is type(b) and a == b
        index = pkg.path_instrument.local_difference(put_rec, alt_rec, h['family'], same)
    return dict(put=put, alternative=alt, plain_put=plain_put.get('output'), plain_alternative=plain_alt.get('output'),
                local_difference_index=index)


def main():
    resource.setrlimit(resource.RLIMIT_AS, (1024 * 1024 * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1 << 23,) * 2)
    resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(Deadline()))
    request = json.loads(Path(sys.argv[1]).read_text())
    sys.path.insert(0, request['repo'])
    import importlib
    pkg = importlib.import_module('trickcatcher_linefacts.pipelines.v68_symbolicgen')
    for name in ('path_instrument', 'value_graph'):
        importlib.import_module(pkg.__name__ + '.' + name)
    Path(sys.argv[2]).write_text(json.dumps(dict(run=once(pkg, request)), ensure_ascii=True) + '\n')


if __name__ == '__main__':
    main()
