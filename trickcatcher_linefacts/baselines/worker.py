"""Disposable execution process (run under `unshare -rn python -I -B`). No endpoint configuration is inherited.

Modes: coverage (CoverUp), mutants / screen / repair / matrix (MuTAP)."""
import ast
import contextlib
import io
import json
import resource
import signal
import socket
import sys
from pathlib import Path


def unavailable(*args, **kwargs):
    raise RuntimeError('network is disabled in baseline workers')


@contextlib.contextmanager
def deadline(seconds=2):
    def expired(*_): raise TimeoutError('execution timeout')
    old = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


def namespace(src):
    ns = {'__name__': 'put'}
    exec(compile(src, 'put.py', 'exec'), ns)
    return ns


def check(src, base, entry, assertions):
    """Base check() plus assertions on one program: survived / killed / timeout / error:<type>."""
    try:
        with deadline(), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            ns = namespace(src)
            exec(base, ns)
            ns['check'](ns[entry])
            for assertion in assertions:
                exec('import math\n' + assertion, ns)
        return 'survived'
    except TimeoutError:
        return 'timeout'
    except AssertionError:
        return 'killed'
    except BaseException as exc:
        return 'error:' + type(exc).__name__


def run_one(src, assertion, seconds=1.0):
    """One standalone assertion in a fresh copy of the program: pass / assert / timeout / error:<type>."""
    try:
        with deadline(seconds), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            ns = namespace(src)
            exec('import math\n' + assertion, ns)
        return 'pass'
    except TimeoutError:
        return 'timeout'
    except AssertionError:
        return 'assert'
    except BaseException as exc:
        return 'error:' + type(exc).__name__


def spread(items, limit):
    """Deterministic, evenly spaced subset in source order (the pool covers the whole PUT, not its first lines)."""
    if len(items) <= limit:
        return list(items)
    return [items[(i * len(items)) // limit] for i in range(limit)]


def main(job):
    mode = job['mode']
    if mode == 'coverage':
        import coverage
        import pytest
        root = Path(job['root'])
        put = root/'put.py'
        sys.path.insert(0, str(root))
        cov = coverage.Coverage(data_file=None, branch=True, config_file=False, include=[str(put)])
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
            cov.start()
            try:
                rc = pytest.main(['-qq', '-x', '-p', 'no:cacheprovider', '--disable-warnings', *job['tests']])
            finally:
                cov.stop()
        report = Path('coverage.json')
        cov.json_report(outfile=str(report))
        report = json.loads(report.read_text())
        files = {}
        for filename, data in report['files'].items():
            # CoverUp/SlipCover denotes function exits by 0; coverage.py uses negative lines.
            for key in ('missing_branches', 'executed_branches'):
                data[key] = [[a, max(0, b)] for a, b in data.get(key, [])]
            files[str(Path(filename).resolve())] = data
        return dict(ok=rc == 0, error=stream.getvalue()[-6000:], coverage=dict(files=files, meta=report['meta']))
    if mode == 'mutants':
        try:
            from mutmut.mutation.file_mutation import create_mutations
            Path('setup.cfg').write_text('[mutmut]\nsource_paths=put.py\n')
            module, mutations, _, _ = create_mutations('put.py', job['put'])
            sources = []
            for mutation in mutations:
                if mutation.contained_by_top_level_function is None:
                    continue
                src = module.deep_replace(mutation.original_node, mutation.mutated_node).code
                try:
                    ast.parse(src)
                except SyntaxError:
                    continue
                if src != job['put'] and src not in sources:
                    sources.append(src)
        except Exception as exc:
            return dict(ok=False, backend='mutmut', error='mutmut unavailable or incompatible: ' + type(exc).__name__)
        chosen = spread(sources, job['max_mutants'])
        return dict(ok=True, backend='mutmut', n_generated=len(sources),
                    mutants=[dict(id=i, source=src) for i, src in enumerate(chosen)])
    if mode == 'screen':
        baseline = check(job['put'], job['base'], job['entry'], job['assertions'])
        if baseline != 'survived':
            return dict(ok=False, error='original suite '+baseline)
        return dict(ok=True, mutants=[dict(id=m['id'], status=check(m['source'], job['base'], job['entry'], job['assertions']))
                                      for m in job['mutants']])
    if mode == 'repair':
        # MuTAP functional repair (Sematic_err_correction.check_test_oracle_sematic): run each assertion on the
        # PUT; a failing `call == expected` gets the PUT's observed value; when the call itself raises, the
        # authors keep the assertion unchanged.
        src = job['put'] + '\n\n' + job.get('base', '')
        details = []
        for assertion in job['assertions']:
            status = run_one(src, assertion, 2.0)
            if status == 'pass':
                details.append(dict(original=assertion, status='pass', assertion=assertion))
                continue
            if status == 'timeout':
                details.append(dict(original=assertion, status='timeout'))
                continue
            test = ast.parse(assertion).body[0].test
            if not (isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], (ast.Eq, ast.Is))):
                details.append(dict(original=assertion, status='unrepairable', error=status))
                continue
            try:
                with deadline(2.0), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    ns = namespace(src)
                    exec('import math', ns)
                    value = eval(compile(ast.Expression(test.left), '<call>', 'eval'), ns)
            except TimeoutError:
                details.append(dict(original=assertion, status='timeout'))
                continue
            except BaseException as exc:
                details.append(dict(original=assertion, status='raises', assertion=assertion, error=type(exc).__name__))
                continue
            try:
                expected = repr(value)
                ast.literal_eval(expected)
            except BaseException as exc:
                details.append(dict(original=assertion, status='nonliteral', error=type(exc).__name__))
                continue
            fixed = 'assert ' + ast.unparse(test.left) + ' == ' + expected
            details.append(dict(original=assertion, status='repaired', assertion=fixed, error=status))
        return dict(ok=True, details=details)
    if mode == 'matrix':
        # Kill matrix for the authors' greedy minimization: assertion i kills mutant m when it does not pass.
        per = job.get('seconds', 1.0)
        kills = {a: [] for a in job['assertions']}
        outcomes = {}
        for m in job['mutants']:
            outcomes[m['id']] = {}
            for a in job['assertions']:
                status = run_one(m['source'], a, per)
                outcomes[m['id']][a] = status
                if status != 'pass':
                    kills[a].append(m['id'])
        return dict(ok=True, kills=kills, outcomes=outcomes)
    raise ValueError(mode)


if __name__ == '__main__':
    job = json.loads(Path(sys.argv[1]).read_text())
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    # facts.py's existing tracer uses the same 3 GiB cap on import.
    resource.setrlimit(resource.RLIMIT_AS, (3*1024**3, 3*1024**3))
    cpu = int(job.get('cpu_seconds', 90))
    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
    socket.socket = unavailable
    socket.create_connection = unavailable
    try:
        result = main(job)
    except BaseException as exc:
        result = dict(ok=False, error=type(exc).__name__+': '+str(exc))
    Path(sys.argv[2]).write_text(json.dumps(result))
