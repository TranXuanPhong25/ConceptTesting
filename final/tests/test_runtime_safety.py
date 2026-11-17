"""Engineering fixtures only. No benchmark inference or real model calls."""
import pytest

from final.src.runtime.contracts import fingerprint, validate_test
from final.src.runtime.execution import execute
from final.src.benchmarks.datasets import load_tasks


def test_dataset_is_full_original_set():
    assert [t['task_id'] for t in load_tasks()] == [f'HumanEval/{i}' for i in range(164)]


def test_alpha_renames_annotations_and_docstrings_are_duplicates():
    left = 'def f(x: int) -> int:\n    """doc"""\n    y = x + 1\n    return y\n'
    right = '#comment\ndef f(value):\n    answer = value + 1\n    return answer\n'
    assert fingerprint(left, 'f') == fingerprint(right, 'f')
    assert fingerprint(left, 'f') != fingerprint('def f(x): return sum([x, 1])', 'f')


def test_import_alias_renaming_and_unused_import_padding_are_duplicates():
    assert fingerprint('import math as m\ndef f(x): return m.sqrt(x)', 'f') == fingerprint(
        'import math as n\ndef f(x): return n.sqrt(x)', 'f')
    assert fingerprint('def f(x): return x+1', 'f') == fingerprint(
        'import math\nfrom typing import List\ndef f(x: int):\n    dummy=0\n    return x+1', 'f')


def test_base_prompt_helpers_are_available_without_candidate_overrides():
    context = 'def helper(x): return x + 1\ndef f(x):\n    """Use helper."""\n'
    result = execute(dict(mode='base', source=context + '\ndef f(x): return helper(x)',
                          context=context, entry='f', timeout=1,
                          base='def check(candidate): assert candidate(2) == helper(2)'))
    assert result['status'] == 'pass'


def test_base_suite_can_call_target_by_original_name():
    result = execute(dict(mode='base', context='def f(x):\n    """Add one."""\n',
                          source='def f(x): return x+1', entry='f', timeout=1,
                          base='def check(candidate): assert candidate(2) == f(2); assert f(2)==3'))
    assert result['status'] == 'pass'


def test_future_import_in_full_source_works_with_prompt_scaffold():
    context = 'def helper(x): return x + 1\ndef f(x):\n    """Add one."""\n'
    source = 'from __future__ import annotations\ndef f(x: int) -> int: return helper(x)'
    result = execute(dict(mode='base', source=source, context=context, entry='f', timeout=1,
                          base='def check(candidate): assert candidate(2)==3'))
    assert result['status'] == 'pass'
    result = execute(dict(mode='cases', source=source, context=context, entry='f', timeout=1,
                          tests=[dict(args='(2,)', kwargs='{}', assertion='result==3')]))
    assert result['tests'][0]['status'] == 'pass'


def test_random_base_inputs_and_signature_binding_are_reproducible():
    context = 'def f(x):\n    """Identity."""\n'
    base = 'import random\ndef check(candidate):\n    for _ in range(5):\n        x=random.randint(0,100000)\n        assert candidate(x)==x'
    job = dict(mode='base', context=context, source='def f(renamed): return renamed', entry='f',
               base=base, timeout=1, seed=42)
    first, second = execute(job), execute(job)
    assert first == second
    assert first['status'] == 'pass'
    # Original public parameter name, regardless of candidate's local spelling.
    assert "'x'" in first['input_keys'][0]


@pytest.mark.parametrize('expression', ['result.__class__', '__import__("os")',
                                      '(lambda: True)()', '(x := True)', 'open("/etc/passwd")'])
def test_predicate_rejects_unsafe_expressions(expression):
    with pytest.raises(ValueError):
        validate_test(dict(args='(1,)', kwargs='{}', assertion=expression))


def test_property_predicate_accepts_nonunique_roots():
    case = dict(args='([-1, 0, 1],)', kwargs='{}',
                assertion='abs(sum(c * result**i for i, c in enumerate(args[0]))) < 1e-6')
    for answer in (-1, 1):
        result = execute(dict(mode='cases', source=f'def f(xs): return {answer}', entry='f',
                              tests=[case], timeout=1))
        assert result['tests'][0]['status'] == 'pass'


def test_sandbox_hides_host_files_and_credentials(tmp_path, monkeypatch):
    sentinel = tmp_path / 'host-only.txt'
    sentinel.write_text('fixture')
    monkeypatch.setenv('FINAL_API_KEY', 'engineering-fixture-not-a-real-secret')
    source = f'''import os
def f():
    assert 'FINAL_API_KEY' not in os.environ
    try:
        open({str(sentinel)!r}).read()
    except FileNotFoundError:
        return True
    return False
'''
    result = execute(dict(mode='base', source=source, entry='f', timeout=1,
                          base='def check(candidate): assert candidate() is True'))
    assert result['status'] == 'pass'


def test_infinite_program_is_a_timeout():
    result = execute(dict(mode='base', source='def f():\n    while True: pass', entry='f',
                          base='def check(candidate): candidate()', timeout=0.1))
    assert result['status'] == 'timeout'


def test_c_level_input_timeout_does_not_abort_evaluation():
    # reduce(operator.add) does not dispatch Python's pending SIGALRM handler.
    result = execute(dict(mode='evaluate', context='def f(n):\n    pass\n',
        source='from functools import reduce\nfrom operator import add\ndef f(n): return reduce(add, range(n), 0)',
        entry='f', tests=[dict(args='(1000000000000,)', kwargs='{}', expected='0')], timeout=0.1))
    assert result == {'tests': [{'status': 'timeout', 'timeout_source': 'sandbox_wall_guard'}]}


def test_sandbox_startup_hang_is_not_counted_as_a_put_timeout(monkeypatch):
    import subprocess
    from final.src.runtime import execution

    class StuckSandbox:
        pid = 999999

        def __init__(self, *args, **kwargs):
            self.killed = False

        def wait(self, timeout=None):
            if timeout is not None:
                raise subprocess.TimeoutExpired('engineering fixture', timeout)
            return -9

    monkeypatch.setattr(execution.subprocess, 'Popen', StuckSandbox)
    monkeypatch.setattr(execution.os, 'killpg', lambda *args: None)
    with pytest.raises(execution.ExecutionError, match='overall wall timeout'):
        execute(dict(mode='evaluate', source='def f(): return 1', entry='f',
                     tests=[dict(args='()', kwargs='{}', expected='1')], timeout=0.1))


def test_missing_user_dependency_remains_an_error():
    result = execute(dict(mode='evaluate', context='def f(n):\n    pass\n',
        source='import missing_engineering_fixture_module\ndef f(n): return n', entry='f',
        tests=[dict(args='(1,)', kwargs='{}', expected='1')], timeout=1))
    assert result == {'tests': [{'status': 'error', 'exception': 'ModuleNotFoundError'}]}
