"""Saved inputs can change; summaries/union never execute workloads."""
from pathlib import Path

import pytest

from final.src.runtime.artifacts import save
from final.src.modular.artifacts import ArtifactStore
from final.src.modular.rescore import build_rescore_pipeline
from final.src.modular.reporting import Reporter
from final.src.modular.tests.test_references import original_run
from final.src.audits.evaluate_input_union import evaluate


def test_rescore_accepts_new_arm_and_inputs_over_old_budget_and_reuses_cache(original_run, tmp_path):
    cohort, source = original_run
    manifest = source.read('modular_manifest.json')
    manifest['arms'] = [{'name': 'saved_custom_arm', 'configuration': {'retired_option': True}}]
    manifest['settings']['input_budget'] = 1
    manifest['task_data_sha256'] = 'obsolete'
    manifest['metadata_sha256'] = 'obsolete'
    save(source.path('modular_manifest.json'), manifest)
    calls = [{'args': '(2, 3)', 'kwargs': '{}'}, {'args': '(3, 4)', 'kwargs': '{}'}]
    batch = {'task_id': 'HumanEval/97', 'arms': {'saved_custom_arm': {'inputs': calls}}}
    save(source.path('tasks/97/inputs.json'), batch)
    cache = tmp_path / 'shared_cache'
    pipeline, tasks, metadata = build_rescore_pipeline(source.directory, cohort, tmp_path / 'first', cache_directory=cache)
    first = pipeline.run(tasks, metadata)
    assert first['arms']['saved_custom_arm']['valid_inputs'] == 2
    assert first['input_execution_cache']['executed_inputs'] > 0
    pipeline, tasks, metadata = build_rescore_pipeline(source.directory, cohort, tmp_path / 'second', cache_directory=cache)
    second = pipeline.run(tasks, metadata)
    assert second['input_execution_cache']['executed_inputs'] == 0
    assert second['input_execution_cache']['hits'] > 0
    batch['arms']['saved_custom_arm']['inputs'].append({'args': '(4, 5)', 'kwargs': '{}'})
    save(source.path('tasks/97/inputs.json'), batch)
    pipeline, tasks, metadata = build_rescore_pipeline(source.directory, cohort, tmp_path / 'third', cache_directory=cache)
    third = pipeline.run(tasks, metadata)
    assert third['arms']['saved_custom_arm']['valid_inputs'] == 3
    assert third['input_execution_cache']['hits'] > 0
    assert third['input_execution_cache']['executed_inputs'] > 0
    with pytest.raises(ValueError, match='new output directory'):
        build_rescore_pipeline(source.directory, cohort, tmp_path / 'third', cache_directory=cache)


def test_union_reads_recorded_outcomes_without_manifest_inputs_or_executors(tmp_path, monkeypatch):
    for module in ('reference_oracle', 'put_evaluation'):
        monkeypatch.setattr(f'final.src.modular.{module}.execute',
                            lambda *args: pytest.fail('Summarization executed a program'))
    source = tmp_path / 'source'
    for number, failure in [(0, {'status': 'fail'}), (1, {'status': 'error', 'exception': 'IndexError'})]:
        task = source / f'tasks/{number}'
        save(task / 'oracle_valid.json', {'tests': [{'input_key': 'one', 'args': '(1,)', 'kwargs': '{}', 'expected': '1'},
                                                  {'input_key': 'two', 'args': '(2,)', 'kwargs': '{}', 'expected': '2'}],
                                         'arm_indices': {'A': [0], 'B': [0, 1]}})
        save(task / 'result.json', {'task_id': f'HumanEval/{number}', 'base_pass': 1,
             'arms': {'A': {'valid_inputs': 1, 'detected': 1, 'detected_put_ids': ['0']},
                      'B': {'valid_inputs': 2, 'detected': 1, 'detected_put_ids': ['0']}},
             'arm_indices': {'A': [0], 'B': [0, 1]},
             'outcomes': {'0': {'failing': [0], 'retested': [0], 'unstable': []}}})
        save(task / 'evaluation/0_0.json', {'tests': [failure, {'status': 'pass'}]})
        save(task / 'evaluation/0_retry_1.json', {'tests': [failure]})
        (task / 'inputs.json').write_text('manually edited and no longer parseable')
    before = {p: p.read_bytes() for p in source.rglob('*') if p.is_file()}
    result = evaluate(source, tmp_path / 'union')
    assert result['arms']['union'] == {'valid_inputs': 4, 'detected': 2, 'tasks_detected': 2}
    assert result['union_detection_kinds'] == {'wrong_value': 1, 'crash': 1}
    assert result['duplicate_valid_memberships_removed'] == 2
    assert result['new_native_calls'] == result['new_model_calls'] == 0
    assert before == {p: p.read_bytes() for p in source.rglob('*') if p.is_file()}
    # Summary counts come from saved verdicts even when the cached summary is stale.
    save(source / 'modular_summary.json', {'arms': {}, 'evaluated_base_pass': 99})
    summary = Reporter.summarize_saved(ArtifactStore(source, read_only=True))
    assert summary['evaluated_base_pass'] == 2 and summary['arms']['A']['detected'] == 2

    save(source / 'tasks/2/result.json', {
        'task_id': 'HumanEval/2', 'base_pass': 3,
        'arms': {'A': {'valid_inputs': 0, 'detected_put_ids': []},
                 'B': {'valid_inputs': 1, 'detected_put_ids': []}},
    })
    summary = Reporter.summarize_saved(ArtifactStore(source, read_only=True))
    assert summary['evaluated_base_pass'] == summary['tested_base_pass'] == 5
    assert summary['arms']['A']['tested_base_pass'] == 2
    assert summary['arms']['B']['tested_base_pass'] == 5
