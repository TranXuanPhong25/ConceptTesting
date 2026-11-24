"""Regression checks for lossless responses and independent completion sampling."""
import json
from types import SimpleNamespace

import pytest

from final.src.benchmarks import adapt_humaneval as adapter
from final.src.models.core_model import ModelResponse


TASK = {'task_id': 'HumanEval/0', 'entry_point': 'f',
        'prompt': 'def f(x):\n    """Return x."""\n', 'test': 'def check(candidate): assert candidate(1) == 1'}


def test_full_chat_source_keeps_imports_helpers_and_entry():
    code = 'import math\n\ndef helper(x):\n    return x\n\ndef f(x):\n    return helper(x)\n'
    assert adapter.source_for(TASK, code) == code
    assert adapter.source_for(TASK, '```python\n' + code + '```') == code.rstrip('\n')


def test_body_completion_preserves_first_line_indentation():
    body = '    if x:\n        return x\n    return 0\n'
    assert adapter.source_for(TASK, body) == TASK['prompt'] + body
    compile(adapter.source_for(TASK, body), '<test>', 'exec')


def test_samples_keep_raw_response_and_allow_duplicate_programs(tmp_path):
    raw = '```python\ndef f(x):\n    return x\n```'
    requests = []

    def generate(messages, **kwargs):
        requests.append((messages, kwargs))
        return ModelResponse(raw, {'total_tokens': 10}, 'stop')

    output = tmp_path / 'samples.jsonl'
    result = adapter.generate(SimpleNamespace(generate=generate), [TASK], samples_per_task=10,
                              seed=17, output=output)
    rows = [json.loads(line) for line in output.read_text().splitlines()]
    assert result['received_samples'] == len(rows) == len(requests) == 10
    assert len({record['completion'] for record in rows}) == 1
    assert all(record['raw_response'] == raw for record in rows)
    assert [request[1]['seed'] for request in requests] == list(range(17, 27))
    assert all(request[0] == requests[0][0] for request in requests)
    with pytest.raises(FileExistsError):
        adapter.generate(None, [TASK], samples_per_task=10, seed=17, output=output)


def test_missing_task_stays_in_pass_at_k_denominator(monkeypatch):
    other = dict(TASK, task_id='HumanEval/1')
    monkeypatch.setattr(adapter, 'run_base_tests', lambda *args, **kwargs: {'status': 'pass'})
    records = [{'task_id': TASK['task_id'], 'sample_index': 0, 'completion': '    return x\n'}]
    result = adapter.evaluate([TASK, other], records)
    assert result['tasks'] == 2 and result['evaluated_tasks'] == 1
    assert result['pass_at_k'] == {'pass@1': None, 'pass@5': None, 'pass@10': None}
    assert result['cohort']['tasks'][0]['programs'][0]['base']['status'] == 'pass'


def test_pass_at_k_matches_combinatorics():
    assert adapter.pass_at_k([10, 10], [0, 10], 1) == .5
    assert adapter.pass_at_k([10], [1], 5) == .5
    assert adapter.pass_at_k([10], [1], 10) == 1


def test_mbpp_prompt_has_signature_and_specification():
    task = dict(TASK, task_id='MBPP/2', declaration='def f(x):\n    pass', prompt='Return x.')
    prompt = adapter.prompt_for(task)
    assert 'Return x.' in prompt and 'def f(x)' in prompt
    compile(adapter.source_for(task, '    return x\n'), '<mbpp>', 'exec')
