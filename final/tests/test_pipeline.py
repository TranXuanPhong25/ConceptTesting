"""Engineering fixtures only. No benchmark inference or real model calls."""
import json

import pytest

from final.contracts import fingerprint, validate_test
from final.core_model import CoreModel, ModelResponse
from final.execution import execute
from final.pipeline import Pipeline, Settings, UnknownInvocation, summarize
from final.run import load_tasks


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


class FixtureModel(CoreModel):
    """A small absolute-value fixture exercises counting, not a paper/model mock."""
    def __init__(self):
        self.calls = []

    @property
    def model_id(self):
        return 'engineering-fixture'

    def generate(self, messages, **kwargs):
        self.calls.append(messages)
        if len(self.calls) == 1:
            programs = [dict(approach=f'fixture{i}', code=f'def f(x):\n    return x if x > -{i} else -x')
                        for i in range(10)]
            # Renaming/formatting copy must be rejected, without reducing the cohort.
            programs.insert(1, dict(approach='duplicate', code='def f(y):\n    return y if y > -0 else -y'))
            return ModelResponse(json.dumps(dict(programs=programs)), {'total_tokens': 12})
        if len(self.calls) == 2:
            return ModelResponse(json.dumps(dict(tests=[
                dict(args='(-1,)', kwargs='{}', assertion='result == 1'),
                dict(args='(2,)', kwargs='{}', assertion='result == 2'),
                dict(args='()', kwargs="{'x': 2}", assertion='result == 2'),
                dict(args='(3,)', kwargs='{}', assertion='result == 99'),
                dict(args='(-1,)', kwargs='{}', assertion='result > 0'),
            ])), {'total_tokens': 8})
        raise AssertionError('Unexpected additional model invocation')


TASK = dict(task_id='HumanEval/0', entry_point='f', prompt='def f(x):\n    """Return absolute value."""\n',
            canonical_solution='    return abs(x)\n', test='def check(candidate): assert candidate(2) == 2')


def test_pipeline_counts_new_failures_rejects_bad_or_duplicate_tests_and_resumes(tmp_path):
    model = FixtureModel()
    pipeline = Pipeline(model, tmp_path, Settings())
    result = pipeline.run_task(TASK)
    assert result['generated'] == result['base_pass'] == result['evaluated_programs'] == 10
    assert result['detected_programs'] == 8
    assert result['valid_tests'] == 1
    assert len(model.calls) == 2
    assert 'canonical_solution' not in json.dumps(model.calls)
    assert 'return abs(x)' not in json.dumps(model.calls)
    assert {r['reason'] for r in result['test_rejections']} == {
        'base_input_duplicate', 'reference_rejects', 'new_input_duplicate'}
    assert pipeline.run_task(TASK) == result
    assert len(model.calls) == 2
    summary = summarize(tmp_path, 1)
    assert summary['detected_fraction_of_base_pass'] == .8
    assert summary['received_responses'] == 2
    assert summary['known_usage']['total_tokens'] == 20


def test_checkpoint_replays_known_response_but_never_unknown_invocation(tmp_path):
    model = FixtureModel()
    pipeline = Pipeline(model, tmp_path, Settings())
    kwargs = dict(temperature=.9, max_tokens=100, seed=1)
    first = pipeline.query(tmp_path, 'programs', [], **kwargs)
    assert pipeline.query(tmp_path, 'programs', [], **kwargs) == first
    assert len(model.calls) == 1
    (tmp_path / 'calls/programs/response.json').unlink()
    with pytest.raises(UnknownInvocation):
        pipeline.query(tmp_path, 'programs', [], **kwargs)
    assert len(model.calls) == 1
