"""CLI task preparation without running the benchmark."""
import pytest

from final.src.modular import run


def test_prepare_pipeline_deduplicates_and_keeps_dataset_order(monkeypatch):
    tasks = [{'task_id': 'HumanEval/0'}, {'task_id': 'HumanEval/18'}]
    monkeypatch.setattr(run, 'load_tasks', lambda: tasks)
    parser, options = run.load_options([
        '--task-ids', 'HumanEval/18', 'HumanEval/0', 'HumanEval/18',
    ])
    selected, metadata = run.prepare_pipeline(parser, options)
    assert selected == tasks
    assert isinstance(metadata, dict)


def test_prepare_pipeline_reports_unsupported_ids(monkeypatch, capsys):
    monkeypatch.setattr(run, 'load_tasks', lambda: [{'task_id': 'HumanEval/0'}])
    parser, options = run.load_options(['--task-ids', 'HumanEval/999'])
    with pytest.raises(SystemExit) as error:
        run.prepare_pipeline(parser, options)
    assert error.value.code == 2
    assert 'Unsupported task IDs: HumanEval/999' in capsys.readouterr().err
