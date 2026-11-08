from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from final.src.audits import run_bva_batch as runner
from final.src.modular.arms.batch import DirectBatchArm, SoftBvaBatchArm
from final.src.modular.artifacts import ArtifactStore
from final.src.modular.context import PipelineSettings, TaskContext
from final.src.modular.stages.input_preparation import InputPreparationStage


def test_batch_arms_only_differ_in_guidance_and_share_argument_encoder():
    from final.src.core_model import ModelResponse
    from final.src.modular.boundary_value_analysis.prompts import GUIDANCE
    packet = {'common': 'same task data'}
    direct, soft = DirectBatchArm(), SoftBvaBatchArm()
    left, right = direct.build_messages(packet), soft.build_messages(packet)
    assert left[0] == right[0]
    assert right[1]['content'] == left[1]['content'] + GUIDANCE
    assert type(direct).run is type(soft).run


def test_context_trimming_is_joint_for_both_arms(tmp_path):
    class Tokenizer:
        def token_count(self, messages):
            content = messages[1]['content']
            programs = 2 if '"id":1' in content else 1
            return programs * 50 + (30 if 'Boundary value analysis' in content else 0)
    settings = replace(PipelineSettings(), target_programs=2, context_tokens=330, input_tokens=100)
    task = {'task_id': 'HumanEval/0', 'prompt': 'def f(x): pass', 'entry_point': 'f', 'test': ''}
    context = TaskContext(task, {'contract': ''}, ArtifactStore(tmp_path), settings, Tokenizer())
    context.cohort_task = {'generated': 2, 'programs': [
        {'id': i, 'code': 'def f(x): return x', 'base': {'status': 'pass'}} for i in range(2)]}
    packet = InputPreparationStage((DirectBatchArm(), SoftBvaBatchArm())).prepare(context)
    assert len(packet['visible_put_ids']) == 1
    assert max(packet['prompt_tokens'].values()) <= settings.context_tokens-settings.input_tokens-128


def test_scheduler_rejects_missing_review_gate_before_creating_run(tmp_path):
    receipt = tmp_path / 'review.json'
    runner.save(receipt, {'review_passed': False, 'tests_passed': True})
    with pytest.raises(ValueError, match='review and tests'):
        runner.prepare_run(tmp_path / 'run', 0, receipt)
    assert not (tmp_path / 'run').exists()


def test_detached_launch_uses_frozen_runtime_and_unique_reservation(tmp_path, monkeypatch):
    runner.save(tmp_path / 'launch_plan.json', {'runtime': str(tmp_path / 'runtime')})
    monkeypatch.setattr(runner.subprocess, 'Popen', lambda *a, **k: SimpleNamespace(pid=123))
    assert runner.launch(tmp_path) == 123
    with pytest.raises(FileExistsError):
        runner.launch(tmp_path)


def test_deadline_wait_never_starts_network_or_keepalive(tmp_path, monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(runner.time, 'time', lambda: clock[0])
    def sleep(seconds):
        assert 0 < seconds <= 30
        clock[0] += seconds
    monkeypatch.setattr(runner.time, 'sleep', sleep)
    monkeypatch.setattr(runner, 'QwenModel', lambda: pytest.fail('model initialized before deadline'))
    runner.wait_until_deadline(tmp_path, 180)
    assert clock[0] == 180
    assert runner.read(tmp_path / 'status.json')['new_model_calls'] == 0


def test_keepalive_counts_actual_observer_receipts(tmp_path):
    runner.save(tmp_path / 'keepalive/0.json', {'state': 'received', 'usage': {'total_tokens': 9}})
    runner.save(tmp_path / 'keepalive/1.json', {'state': 'unknown'})
    runner.save(tmp_path / 'keepalive/2.json', {'state': 'not_sent'})
    assert runner.keepalive_usage(tmp_path) == {'records': 3, 'received': 1, 'unknown': 1, 'not_sent': 1, 'known_total_tokens': 9}
