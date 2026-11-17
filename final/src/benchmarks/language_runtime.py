"""Typed calls and bounded bwrap execution; generated source never runs on the host."""
from __future__ import annotations

import ast
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile

from final.src.modular.call_builder import CallBuilder
from final.src.runtime.artifacts import read_sandbox_file


class UnsupportedSignature(ValueError):
    pass


def split_parameters(text):
    parts, start, depth = [], 0, 0
    for index, char in enumerate(text):
        if char == '<':
            depth += 1
        elif char == '>':
            depth -= 1
        elif char == ',' and depth == 0:
            parts.append(text[start:index].strip())
            start = index + 1
    if text[start:].strip():
        parts.append(text[start:].strip())
    return parts


def signature(declaration, language):
    # HumanEval-X declarations can include helper functions before the target.
    without_comments = re.sub(r'/\*.*?\*/|//[^\n]*', '', declaration, flags=re.S)
    without_literals = re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', lambda m: ' '*len(m.group()), without_comments)
    depths, depth = [], 0
    for char in without_literals:
        depths.append(depth)
        depth += (char == '{') - (char == '}')
    function_depth = 1 if language == 'java' and re.search(r'\bclass\s+Solution\b', without_literals) else 0
    matches = [m for m in re.finditer(r'([\w:<> ,]+)\s+(\w+)\s*\(([^()]*)\)\s*(?:throws\s+[\w., ]+)?\s*\{', without_literals)
               if depths[m.start()] == function_depth and m.group(2) not in ('for','if','while','switch','catch')]
    if not matches:
        raise UnsupportedSignature('unsupported function declaration')
    match = matches[-1]
    if re.search(r'[*&\[\]=]', match.group(3)):
        raise UnsupportedSignature('unsupported pointer/reference/array/default parameter')
    parameters = []
    for parameter in split_parameters(match.group(3)):
        parsed = re.fullmatch(r'(.+[\s>])([A-Za-z_]\w*)\s*', parameter)
        if parsed is None:
            raise UnsupportedSignature('unsupported parameter: ' + parameter)
        type_name, name = parsed.groups()
        type_name = re.sub(r'\b(?:const|final)\s+', '', type_name).strip()
        parameters.append((type_name, name))
    return match.group(2), parameters, 'static' in match.group(1).split()


def value_literal(kind, value, language):
    kind = kind.replace('std::', '').strip()
    if len(json.dumps(value, ensure_ascii=True, allow_nan=False)) > 16000:
        raise UnsupportedSignature('argument literal exceeds limit')
    if kind in ('bool', 'boolean', 'Boolean'):
        if type(value) is not bool:
            raise UnsupportedSignature('expected boolean')
        return 'true' if value else 'false'
    if kind in ('int', 'Integer', 'long', 'Long', 'long long', 'short'):
        bits = 64 if kind in ('long', 'Long', 'long long') else 32
        if type(value) is not int or not -(2 ** (bits - 1)) <= value < 2 ** (bits - 1):
            raise UnsupportedSignature('integer type/range mismatch')
        suffix = 'L' if kind in ('long', 'Long') and language == 'java' else 'LL' if kind in ('long', 'long long') else ''
        return str(value) + suffix
    if kind in ('float', 'double', 'Float', 'Double'):
        if type(value) not in (int, float) or not math.isfinite(value):
            raise UnsupportedSignature('expected finite number')
        if kind.lower() == 'float' and abs(value) > 3.402823466e38:
            raise UnsupportedSignature('float range mismatch')
        return repr(float(value)) + ('f' if kind.lower() == 'float' else '')
    if kind in ('string', 'String'):
        if not isinstance(value, str) or any(0xD800 <= ord(c) <= 0xDFFF for c in value):
            raise UnsupportedSignature('expected valid Unicode string')
        if language == 'cpp':
            # Fixed-width octal bytes avoid C++ hex escapes consuming the next digit.
            encoded = ''.join('\\%03o' % byte for byte in value.encode('utf-8'))
            return f'std::string{{"{encoded}", {len(value.encode("utf-8"))}}}'
        return json.dumps(value, ensure_ascii=True)
    if language == 'cpp' and kind == 'boost::any':
        if type(value) is bool:
            return f'boost::any({"true" if value else "false"})'
        if type(value) is int:
            return f'boost::any({value})'
        if type(value) is float and math.isfinite(value):
            return f'boost::any({value!r})'
        if isinstance(value, str):
            return 'boost::any(' + value_literal('string', value, language) + ')'
        raise UnsupportedSignature('unsupported boost::any value')
    if language == 'cpp' and kind == 'list_any':
        if not isinstance(value, list) or len(value) > 1000:
            raise UnsupportedSignature('expected bounded list_any')
        items = ', '.join(value_literal('boost::any', item, language) for item in value)
        return f'list_any{{{items}}}'
    generic = re.fullmatch(r'(vector|List|ArrayList|Map|map)<(.+)>', kind)
    if generic:
        container, types = generic.groups()
        arguments = split_parameters(types)
        if container in ('vector', 'List', 'ArrayList'):
            if not isinstance(value, list) or len(value) > 1000 or len(arguments) != 1:
                raise UnsupportedSignature('expected bounded list')
            items = ', '.join(value_literal(arguments[0], item, language) for item in value)
            if language == 'cpp':
                return f'std::vector<{types}>{{{items}}}'
            return f'new ArrayList<{types}>(Arrays.asList({items}))'
        if not isinstance(value, dict) or len(arguments) != 2 or len(value) > 1000:
            raise UnsupportedSignature('expected bounded map')
        pairs = [(value_literal(arguments[0], key, language), value_literal(arguments[1], item, language)) for key, item in value.items()]
        if language == 'cpp':
            return f'std::map<{types}>{{' + ', '.join('{' + k + ', ' + v + '}' for k, v in pairs) + '}'
        return f'new HashMap<{types}>(){{{{' + ''.join(f'put({k}, {v});' for k, v in pairs) + '}}'
    if kind == 'Object' and language == 'java':
        inferred = {str:'String', int:'Integer', float:'Double', bool:'Boolean'}
        if value is None:
            return 'null'
        if type(value) in inferred:
            return value_literal(inferred[type(value)], value, language)
    raise UnsupportedSignature('unsupported parameter type: ' + kind)


def serialize_call(declaration, arguments, language):
    name, parameters, is_static = signature(declaration, language)
    if not isinstance(arguments, dict) or set(arguments) != {name for _, name in parameters}:
        raise UnsupportedSignature('arguments do not match declaration')
    values = [value_literal(kind, arguments[name], language) for kind, name in parameters]
    receiver = ('Solution.' if is_static else 'solution.') if language == 'java' else ''
    return receiver + name + '(' + ', '.join(values) + ')'


def sandbox(command, directory, timeout, *, result_directory=None):
    if not shutil.which('bwrap') or not shutil.which('prlimit'):
        raise RuntimeError('bwrap and prlimit are required; refusing host execution')
    args = ['bwrap', '--unshare-all', '--die-with-parent', '--new-session', '--cap-drop', 'ALL']
    for name in ('/usr', '/lib', '/lib64'):
        if Path(name).exists():
            args += ['--ro-bind', name, name]
    # Debian's JDK configuration files are symlinks into these public directories.
    for configuration in Path('/etc').glob('java*openjdk'):
        args += ['--ro-bind', str(configuration), str(configuration)]
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
    """Return independent input receipts; compilation happens once per program."""
    language = task['language']
    with tempfile.TemporaryDirectory(prefix='concepttester-language-') as temporary:
        directory = Path(temporary)
        if language == 'python':
            worker = Path(__file__).with_name('python_worker.py')
            shutil.copyfile(worker, directory / 'worker.py')
            (directory / 'program.py').write_text(source)
            command = [str(Path(sys.executable).resolve()), '-I', '-S', '/work/worker.py']
        else:
            compiler = 'g++' if language == 'cpp' else 'javac'
            if not shutil.which(compiler) or (language == 'java' and not shutil.which('java')):
                return {'status':'unsupported_environment', 'tests':[]}
            harness = Path(__file__).with_name('harness.cpp' if language == 'cpp' else 'Harness.java').read_text()
            if base:
                code = source + '\n' + task['example_test']
            else:
                code = source + '\n' + harness
            filename = 'main.cpp' if language == 'cpp' else 'Main.java'
            (directory / filename).write_text(code)
            if language == 'cpp':
                # HumanEval-X uses boost::any in two tasks; std::any is enough for
                # their public source and keeps the harness independent of Boost.
                boost_directory = directory / 'boost'
                boost_directory.mkdir()
                (boost_directory / 'any.hpp').write_text(
                    '#pragma once\n#include <any>\nnamespace boost {\n'
                    'using any = std::any;\nusing std::any_cast;\n}\n')
                compile_command = ['g++', '-std=c++17', '-O0', '-I.', 'main.cpp', '-o', 'main', '-lcrypto']
            else:
                compile_command = ['javac', '-J-Xmx256m', '-J-XX:CompressedClassSpaceSize=64m', '-J-XX:ReservedCodeCacheSize=64m', 'Main.java']
            # Call expressions are data rendered by the typed serializer, never model code.
            if not base:
                call_text = [serialize_call(task['declaration'], a, language) for a in calls]
                # A selector keeps each invocation in a fresh process.
                body = '\n'.join((f'case {i}: ct_write({call}); break;' if language == 'cpp' else f'case {i}: write({call}); break;') for i, call in enumerate(call_text))
                code = code.replace('/* CALLS */', body)
                (directory / filename).write_text(code)
            compiled = sandbox(compile_command, directory, 30)
            if compiled['status'] != 'ok':
                return {'status':'compile_timeout' if compiled['status']=='timeout' else 'compile_error', 'tests':[], 'compiler':compiler, 'detail':compiled.get('detail')}
            command = ['./main'] if language == 'cpp' else ['java', '-ea', '-Xmx256m', '-XX:CompressedClassSpaceSize=64m', '-XX:ReservedCodeCacheSize=64m', '-cp', '/work', 'Main']
        results = []
        for index, arguments in enumerate([{}] if base else calls):
            if language == 'python':
                builder = CallBuilder.for_source(task['declaration'], task['entry_point'])
                record = builder.build(arguments) if not base else {}
                (directory / 'job.json').write_text(json.dumps({'entry':task['entry_point'], 'input':record, 'base':task['test'] if base else None}))
            with tempfile.TemporaryDirectory(prefix='concepttester-result-') as output:
                observation = sandbox(command + ([] if language == 'python' else [str(index)]), directory, timeout,
                                      result_directory=Path(output))
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
