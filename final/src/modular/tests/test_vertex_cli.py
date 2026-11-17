"""Standalone Vertex CLI behavior without network requests."""
import importlib.util
import io
from pathlib import Path

import pytest

from final.src.models.core_model import ModelResponse


def script():
    path = Path(__file__).resolve().parents[4] / 'scripts/call_vertex.py'
    spec = importlib.util.spec_from_file_location('call_vertex', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_vertex_cli_passes_model_project_prompt_and_budget(monkeypatch, capsys):
    cli = script()
    calls = []
    class Model:
        def __init__(self, **options): calls.append(options)
        def generate(self, messages, **options):
            calls.append((messages, options))
            return ModelResponse('Xin chào', {'total_tokens': 12}, 'stop')
    monkeypatch.setattr(cli, 'VertexAIModel', Model)
    assert cli.main(['Hello', '--project', 'fixture-project', '--model', 'fixture-model', '--max-tokens', '256']) == 0
    assert calls[0]['project'] == 'fixture-project' and calls[0]['model'] == 'fixture-model'
    assert calls[1][0] == [{'role': 'user', 'content': 'Hello'}]
    assert calls[1][1]['max_tokens'] == 256
    assert capsys.readouterr().out == 'Xin chào\n'


def test_vertex_cli_reads_stdin_and_rejects_empty_prompt(monkeypatch):
    cli = script()
    monkeypatch.setattr(cli.sys, 'stdin', io.StringIO('   '))
    monkeypatch.setattr(cli, 'VertexAIModel', lambda **kw: pytest.fail('Empty input must not create a client'))
    with pytest.raises(SystemExit) as exc:
        cli.main([])
    assert exc.value.code == 2
