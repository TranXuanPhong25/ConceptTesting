"""Offline budgets and launch wiring; no upstream/native/model workload."""
import json
from pathlib import Path

import pytest

from final.src.orchestration import config, worker


def settings(mode='pynguin', **overrides):
    return {'mode': mode, 'arms': ['pynguin'],
            'pynguin': {'python': '/missing/external/python', **overrides}}


def test_pynguin_model_caps():
    baseline = config.preview(settings())
    assert baseline['logical_call_cap'] == baseline['completion_token_cap_total'] == 0
    assert baseline['pynguin_budgets']['owner_search_count_cap'] == baseline['evaluated_base_pass_put_count']
    assert baseline['pynguin_budgets']['search_seconds_cap_total'] == 10 * baseline['evaluated_base_pass_put_count']


@pytest.mark.parametrize('changes', [
    {'pynguin': {'python': '/tmp/python', 'api_key': 'secret'}},
    {'arms': ['pynguin', 'plain']}, {'inputs_per_task': 21},
    {'pynguin': {'python': '/tmp/python', 'owner_limit': True}},
    {'tool_sampling': {}},
])
def test_pynguin_rejects_ambiguous_or_secret_configuration(changes):
    with pytest.raises((TypeError, ValueError)):
        config.normalize({**settings(), **changes})


def test_baseline_prepare_requires_no_endpoint_and_snapshots_assets(tmp_path, monkeypatch):
    monkeypatch.setattr(worker, 'private_endpoint', lambda *args: pytest.fail('baseline endpoint access'))
    directory = tmp_path / 'prepared'
    worker.prepare(settings(), directory)
    plan = worker.read(directory / 'launch_plan.json')
    assert plan['endpoint_env_file'] is None
    assert plan['logical_call_cap'] == 0
    assert Path(plan['runtime'], 'final/src/modular/pynguin/runner.py').is_file()
    assert Path(plan['runtime'], 'final/pynguin-requirements.txt').is_file()


def test_prepared_presets_are_preview_only_and_normalizable():
    presets = json.loads((config.ROOT / 'final/presets/criteria_pynguin.json').read_text())
    assert len(presets) == 1
    for preset in presets:
        assert preset['preview_only'] is True
        config.preview(preset['parameters'])


def test_missing_runtime_blocks_worker_before_endpoint_or_result(tmp_path, monkeypatch):
    from importlib import import_module
    model = import_module("final.src.models.model")
    from types import SimpleNamespace

    worker.save(tmp_path / 'config_snapshot.json', config.normalize(settings()))
    worker.save(tmp_path / 'launch_plan.json', {})
    monkeypatch.setattr(worker.signal, 'signal', lambda *args: None)
    monkeypatch.setattr(model, 'QwenModel', lambda **kwargs: pytest.fail('missing runtime accessed model'))
    with pytest.raises(ValueError):
        worker.run(tmp_path)
    assert not (tmp_path / 'result_digest.json').exists()


@pytest.mark.parametrize('name', ['ep_bva_vf4', 'decision_table_vf4'])
def test_removed_vf4_arms_are_rejected_and_v2_is_kept(name):
    from final.src.modular import selected_arms
    with pytest.raises(ValueError):selected_arms([name])
    with pytest.raises(ValueError):config.normalize({'arms':[name]})
    assert selected_arms(['ep_bva_v2','decision_table_v2','control_flow'])


def test_removed_hybrid_mode_is_rejected():
    with pytest.raises(ValueError):config.normalize(settings('pynguin_hybrid'))
