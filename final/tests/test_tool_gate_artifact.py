"""Publish stopped treatment gates without invoking model or native evaluation."""
import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

try:
    from final.src.orchestration import flows
except ImportError:
    pytest.skip('Uses the isolated orchestration environment', allow_module_level=True)


def test_generation_gate_is_published_with_actual_failure_before_metrics(tmp_path):
    gate = {'ready': False, 'tasks': {}, 'failures': [{'task_id': 'HumanEval/7', 'arm': 'tool_hypothesis',
        'status': 'not_exercised', 'reason': 'No clean candidate'}]}
    (tmp_path/'tool_generation_gate.json').write_text(json.dumps(gate))
    publish = AsyncMock()
    with patch.object(flows, 'create_markdown_artifact', publish):
        asyncio.run(flows.attach_tool_generation_gate(tmp_path))
    kwargs = publish.await_args.kwargs
    assert kwargs['key'] == 'tool-generation-gate'
    assert 'not_exercised' in kwargs['markdown'] and 'HumanEval/7' in kwargs['markdown']
    assert 'pending' in kwargs['markdown']
