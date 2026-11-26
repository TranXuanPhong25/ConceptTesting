"""CLI generator selection without a dataset or model call."""
import json
from contextlib import nullcontext

import pytest


def test_baseline_run_never_constructs_model(tmp_path, monkeypatch):
    from final.src.modular import run
    from final.src.modular.pynguin.config import PynguinSettings
    from final.src import models

    settings_file = tmp_path / 'settings.json'
    settings_file.write_text(json.dumps({'python': '/fixture/python'}))
    seen = {}
    monkeypatch.setattr(run, 'pynguin_native_lock', nullcontext)
    monkeypatch.setattr(PynguinSettings, 'validate_environment', lambda self: None)
    monkeypatch.setattr(run.DatasetLoader, 'load_tasks', lambda self: [{'task_id': 'fixture/0'}])
    monkeypatch.setattr(models, 'create_model', lambda **kwargs: pytest.fail('baseline model access'))
    class Pipeline:
        def __init__(self, *args, **kwargs):
            seen.update(kwargs)
            self.stage_events = []
        def run(self, tasks, metadata): return {'scored_tasks': 0, 'arms': {}}
    monkeypatch.setattr(run, 'BenchmarkPipeline', Pipeline)
    assert run.main(['--mode', 'run', '--pynguin-config', str(settings_file),
                     '--artifacts', str(tmp_path / 'output')]) == 0
    assert seen['calls'] is None
    assert seen['pynguin_settings'].python == '/fixture/python'


def test_removed_hybrid_flag_is_rejected():
    from final.src.modular.run import main
    with pytest.raises(SystemExit) as error:
        main(['--pynguin-hybrid'])
    assert error.value.code == 2
