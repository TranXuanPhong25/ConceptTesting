"""Typed calls and bounded bwrap execution; generated source never runs on the host."""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile

from final.src.modular.call_builder import CallBuilder
from final.src.runtime.artifacts import read_sandbox_file


class UnsupportedSignature(ValueError):
    pass


def sandbox(command, directory, timeout, *, result_directory=None):
    if not shutil.which('bwrap') or not shutil.which('prlimit'):
        raise RuntimeError('bwrap and prlimit are required; refusing host execution')
    args = ['bwrap', '--unshare-all', '--die-with-parent', '--new-session', '--cap-drop', 'ALL']
    for name in ('/usr', '/lib', '/lib64'):
        if Path(name).exists():
            args += ['--ro-bind', name, name]
    prefix = str(Path(sys.base_prefix).resolve())
    if not prefix.startswith('/usr/') and prefix != '/usr':
        args += ['--ro-bind', prefix, prefix]
    mount = '--ro-bind' if result_directory is not None else '--bind'
    args += ['--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp', mount, str(directory), '/work', '--chdir', '/work']
    if result_directory is not None:
        args += ['--bind', str(result_directory), '/results']
    uid_tasks = 0
    for process_path in Path('/proc').iterdir():
        try:
            if process_path.name.isdigit() and process_path.stat().st_uid == os.getuid():
                uid_tasks += len(list((process_path/'task').iterdir()))
        except OSError:
            pass
    args += ['prlimit', '--as=3221225472', '--cpu=' + str(math.ceil(timeout) + 1), '--fsize=4194304',
             '--nproc='+str(uid_tasks+64), '--nofile=128', '--core=0', '--', *command]
    env = {'PATH': '/usr/bin:/bin', 'HOME':'/tmp', 'LANG':'C.UTF-8', 'PYTHONHASHSEED':'0'}
    with (directory / 'stdout.log').open('wb') as stdout, (directory / 'stderr.log').open('wb') as stderr:
        process = subprocess.Popen(args, env=env, stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            return {'status':'timeout'}
    # Logs are private artifacts only; no generated code can flood host memory.
    detail = read_sandbox_file(directory, 'stderr.log', max_bytes=4 << 20)[:4000].decode(errors='replace')
    if process.returncode and not detail:
        detail = read_sandbox_file(directory, 'stdout.log', max_bytes=4 << 20)[:4000].decode(errors='replace')
    return {'status':'ok' if process.returncode == 0 else 'runtime_error', 'returncode':process.returncode, 'detail': detail}


def execute_program(task, source, calls, *, timeout=8, base=False):
    """Return independent input receipts; generated source stays inside the sandbox."""
    language = task['language']
    if language != 'python':
        raise UnsupportedSignature('unsupported adapter language: ' + language)
    if not base:
        builder = CallBuilder.for_source(task['declaration'], task['entry_point'])
    with tempfile.TemporaryDirectory(prefix='concepttester-language-') as temporary:
        directory = Path(temporary)
        shutil.copyfile(Path(__file__).with_name('python_worker.py'), directory / 'worker.py')
        (directory / 'program.py').write_text(source)
        command = [str(Path(sys.executable).resolve()), '-I', '-S', '/work/worker.py']
        results = []
        for arguments in [{}] if base else calls:
            record = builder.build(arguments) if not base else {}
            (directory / 'job.json').write_text(json.dumps({'entry':task['entry_point'], 'input':record,
                'base':task['test'] if base else None}))
            with tempfile.TemporaryDirectory(prefix='concepttester-result-') as output:
                observation = sandbox(command, directory, timeout, result_directory=Path(output))
                if observation['status'] != 'ok':
                    results.append(observation)
                    continue
                if base:
                    results.append({'status':'ok'})
                    continue
                try:
                    value = json.loads(read_sandbox_file(Path(output), 'ct-result.json', max_bytes=4 << 20))
                    json.dumps(value, allow_nan=False)
                    results.append({'status':'ok', 'value':value})
                except (OSError, ValueError, RecursionError):
                    results.append({'status':'output_error'})
        return {'status':'ok', 'tests':results}


def equivalent(actual, expected):
    if isinstance(actual, bool) or isinstance(expected, bool):
        return type(actual) is type(expected) and actual == expected
    if type(actual) in (int, float) and type(expected) in (int, float):
        return actual == expected or (isinstance(expected, float) and math.isclose(actual, expected, rel_tol=1e-7, abs_tol=1e-6))
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(equivalent(a, b) for a, b in zip(actual, expected))
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(equivalent(actual[k], expected[k]) for k in expected)
    return actual == expected
