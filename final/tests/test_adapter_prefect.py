"""Run with final/.venv_orchestration: Prefect artifact transport is isolated."""
import asyncio
import json
import importlib.util

import pytest

pytestmark = pytest.mark.skipif(importlib.util.find_spec('prefect') is None, reason='Prefect uses the orchestration venv')


def test_adapter_attachment_handles_its_own_schema(tmp_path, monkeypatch):
    from final.src.orchestration import benchmark_adapters as module
    (tmp_path/'config_snapshot.json').write_text('{"dataset":"mbpp"}')
    result = {'arms':{'plain':{'detected':1}}, 'outcomes':{'p':[0]}}
    (tmp_path/'result_digest.json').write_text(json.dumps(result))
    (tmp_path/'REPORT.md').write_text('Kết quả fixture, không phải benchmark.')
    published = []
    async def publish(**values): published.append(values)
    monkeypatch.setattr(module, 'create_markdown_artifact', publish)
    monkeypatch.setattr(module, 'create_table_artifact', publish)
    assert asyncio.run(module.attach_adapter_outputs(tmp_path)) == result
    assert any(row.get('key') == 'adapter-report' for row in published)
