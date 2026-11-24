"""Freeze the same JSON view that read-only replay will load."""
from final.src.modular.generators.base import InputGenerator
from final.src.modular.pipeline import generate_task_inputs
from final.src.modular.tests.test_spec_obligation import context
from final.src.runtime.artifacts import digest


def test_mixed_metadata_keys_freeze_from_persisted_json_without_changing_inputs(tmp_path):
    class Generator(InputGenerator):
        def generate(self, ctx):
            return {'task_id': ctx.task['task_id'], 'arms': {'fixture': {
                'inputs': [{'args': '([2,2],)', 'kwargs': '{}'}],
                'metadata': {1: 'one', 'two': 2}}}}
    ctx = context(tmp_path, None)
    generate_task_inputs(ctx, Generator())
    saved = ctx.artifacts.read(ctx.task_directory + '/inputs.json')
    assert ctx.inputs == saved
    assert ctx.inputs['arms']['fixture']['inputs'][0]['args'] == '([2,2],)'
    assert digest(ctx.inputs) == digest(saved)
