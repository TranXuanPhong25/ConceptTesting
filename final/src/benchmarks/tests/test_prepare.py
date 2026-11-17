import json
import os
import subprocess
import sys

import pytest

from final.src.benchmarks.run import prepare


def test_prepare_pins_sources_without_creating_model_or_launching_native(tmp_path, monkeypatch):
    monkeypatch.setattr('final.src.models.create_model', lambda **k: pytest.fail('model during prepare'))
    monkeypatch.setattr('final.src.benchmarks.pipeline.execute_program', lambda *a,**k: pytest.fail('native during prepare'))
    directory = tmp_path/'prepared'
    preview = prepare({'dataset':'humaneval_x_java','task_numbers':[0]}, directory)
    assert preview['cohort_status'] == 'pending'
    assert json.loads((directory/'status.json').read_text())['new_model_calls'] == 0
    assert (directory/'runtime/final/src/benchmarks/Harness.java').is_file()



def test_frozen_runtime_can_load_input_type_metadata(tmp_path):
    directory = tmp_path/'prepared'
    prepare({'dataset':'mbpp','task_numbers':[11]}, directory)
    subprocess.run([sys.executable, '-P', '-B', '-c',
        'from final.src.modular.call_builder import CallBuilder; '
        'CallBuilder.for_source("def f(x): pass", "f")'],
        cwd=tmp_path, env={**os.environ, 'PYTHONPATH':str(directory/'runtime')},
        check=True, capture_output=True, text=True)


def test_model_presets_are_preview_only_and_match_each_dataset():
    from final.src.benchmarks.pipeline import preview
    presets = json.loads(open('final/presets/benchmark_adapters.json').read())
    assert len(presets) == 6
    for preset in presets:
        values = dict(preset['parameters'])
        assert values.pop('preview_only') is True
        description = preview(values)
        assert description['logical_call_cap'] == 3
        assert description['candidate_count'] is None
