"""Type admission rejects invalid calls even when the reference would accept them."""
import ast
from types import SimpleNamespace

import pytest

from final.src.benchmarks.datasets import load_metadata, load_tasks
from final.src.modular.artifacts import ArtifactStore
from final.src.modular.call_builder import CallBuilder, entry_function, input_signature
from final.src.modular.context import PipelineSettings, TaskContext
from final.src.modular.reference_oracle import run_reference_oracle
from final.src.modular.references import TaskReferencePrograms


@pytest.mark.parametrize('annotation,value', [
    ('List[str]', {'a': 'a'}), ('List[str]', ['a', 1]),
    ('str', set()), ('list[int]', ['', -816.25]),
    ('list[int]', [1, True]), ('int', True), ('float', False),
    ('list[list[int]]', [[1], [2.5]]), ('dict[str, int]', {'x': False}),
    ('tuple[int, str]', (1, 2)), ('list[int]', (1, 2)),
])
def test_builder_rejects_wrong_argument_and_nested_types(annotation, value):
    builder = CallBuilder.for_source(f'def f(x: {annotation}): pass', 'f')
    with pytest.raises(ValueError, match='argument_type_mismatch:x'):
        builder.build_values({'x': value})
    with pytest.raises(ValueError, match='argument_type_mismatch:x'):
        builder.validate_call({'args': repr((value,)), 'kwargs': '{}'})


@pytest.mark.parametrize('annotation,value', [
    ('List[float]', [1, 2.5]), ('list[Any]', [True, None, {}, 'a']),
    ('dict[Any, Any]', {1: 'a', 'b': 2}), ('bool', True),
    ('Optional[int]', None), ('int | str', 'a'),
    ('typing.List[typing.List[int]]', [[1], []]),
    ('tuple[int, ...]', (1, 2, 3)), ('tuple[int, str]', (1, 'a')),
    ("'list[int]'", [1]),
])
def test_builder_preserves_valid_values_without_coercion(annotation, value):
    record = CallBuilder.for_source(f'def f(x: {annotation}): pass', 'f').build_values({'x': value})
    assert record['args'] == repr((value,))


@pytest.mark.parametrize('annotation', ['Dangerous()', 'list[Dangerous()]', 'list[Unknown]', 'int[str]'])
def test_unsupported_annotations_fail_closed_without_execution(annotation):
    with pytest.raises(ValueError, match='unsupported_type_annotation'):
        CallBuilder.for_source(f'def f(x: {annotation}): pass', 'f')


def test_defaults_positional_only_and_keyword_only_are_type_checked():
    builder = CallBuilder.for_source('def f(x: int, /, *, y: list[str] = []): pass', 'f')
    assert builder.build({'x': 1})['kwargs'] == "{'y': []}"
    with pytest.raises(ValueError, match='argument_type_mismatch:y'):
        builder.validate_call({'args': '(1,)', 'kwargs': "{'y': [2]}"})
    with pytest.raises(TypeError):
        builder.validate_call({'args': '()', 'kwargs': "{'x': 1}"})


def test_humaneval_uses_original_signatures_and_contracts():
    import json
    from final.src.benchmarks.datasets import METADATA_PATH
    original = json.loads(METADATA_PATH.read_text())
    assert load_metadata() == original
    tasks = load_tasks()
    assert len(tasks) == 164
    for task in tasks:
        source, entry = task['prompt'], task['entry_point']
        assert CallBuilder.for_source(source, entry).signature == input_signature(entry_function(source, entry))
    # Explicitly heterogeneous tasks stay heterogeneous; numeric predicates can receive floats.
    for number, arguments in [(22, {'values': ['a', {}, 1, True]}),
                              (92, {'x': 1.5, 'y': 2, 'z': 3.5}),
                              (95, {'dict': {1: 'a', 'B': False}}),
                              (137, {'a': '2,5', 'b': 3}),
                              (151, {'lst': [1, -2, 3.5]})]:
        task = next(t for t in tasks if t['task_id'] == f'HumanEval/{number}')
        builder = CallBuilder.for_source(task['prompt'], task['entry_point'])
        builder.build_values(arguments)


@pytest.mark.parametrize('number,args', [(29, "({'a': 'a'}, 'a')"), (40, '(42,)')])
def test_wrong_declared_types_never_reach_reference_oracle(tmp_path, monkeypatch, number, args):
    task = next(t for t in load_tasks() if t['task_id'] == f'HumanEval/{number}')
    context = TaskContext(task, load_metadata()[task['task_id']], ArtifactStore(tmp_path), PipelineSettings())
    context.inputs_frozen = True
    context.cohort_task = {'base_input_keys': []}
    context.inputs = {'arms': {'pynguin': {'inputs': [{'args': args, 'kwargs': '{}'}]}}}
    monkeypatch.setattr('final.src.modular.reference_oracle.execute',
                        lambda job: pytest.fail('Invalid input reached the reference'))
    run_reference_oracle(context)
    assert context.oracle['tests'] == []
    assert context.oracle['arm_indices'] == {'pynguin': []}
    assert context.oracle['rejected'][0]['reason'] == 'input_type_rejects'


def test_reference_rejection_keeps_raw_indices_and_catalogue_survivors(tmp_path, monkeypatch):
    task = {'task_id': 'Toy/1', 'entry_point': 'f', 'prompt': 'def f(x: int): pass'}
    context = TaskContext(task, {'contract': ''}, ArtifactStore(tmp_path), PipelineSettings())
    context.inputs_frozen = True
    context.cohort_task = {'base_input_keys': []}
    valid = {'args': '(3,)', 'kwargs': '{}'}
    invalid = {'args': '(True,)', 'kwargs': '{}'}
    context.inputs = {'arms': {'a': {'inputs': [invalid, valid], 'catalogue_status': 'valid'},
                               'b': {'inputs': [valid, invalid]}}}
    reference = SimpleNamespace(record_source_info=False, for_task=lambda *args: {
        'context': task['prompt'], 'source': '', 'entry': 'f', 'contract': ''})
    calls = []
    def execute(job):
        calls.append(job)
        assert job['tests'] == [valid, valid]
        return {'tests': [{'status': 'ok', 'expected': '3', 'input_key': 'three'}] * 2}
    monkeypatch.setattr('final.src.modular.reference_oracle.execute', execute)
    run_reference_oracle(context, reference_programs=reference)
    assert len(calls) == 2
    assert len(context.oracle['tests']) == 1
    assert context.oracle['arm_indices'] == {'a': [0], 'b': [0]}
    assert [row['index'] for row in context.oracle['rejected']] == [0, 3]
    assert context.oracle['catalogue_valid_input_indices'] == {'a': [1]}
    assert context.inputs['arms']['a']['inputs'] == [invalid, valid]


def test_unannotated_humaneval_inputs_reach_reference_with_contract(tmp_path, monkeypatch):
    task = next(t for t in load_tasks() if t['task_id'] == 'HumanEval/31')
    metadata = load_metadata()[task['task_id']]
    context = TaskContext(task, metadata, ArtifactStore(tmp_path), PipelineSettings())
    context.cohort_task = {'base_input_keys': []}
    record = {'args': "('7',)", 'kwargs': '{}'}
    context.inputs = {'arms': {'plain': {'inputs': [record]}}}

    def execute(job):
        assert job['tests'] == [record]
        assert job['contract'] == metadata['contract']
        assert 'type(n) == int' in job['contract']
        return {'tests': [{'status': 'invalid_domain'}]}

    monkeypatch.setattr('final.src.modular.reference_oracle.execute', execute)
    run_reference_oracle(context)
    assert context.oracle['tests'] == []
    assert context.oracle['rejected'][0]['reason'] == 'domain_or_reference_rejects'


def test_oracle_keeps_dict_order_distinct_from_a_saved_base_call(tmp_path):
    from final.src.runtime.contracts import bound_call_key

    task = {
        'task_id': 'Toy/0',
        'entry_point': 'f',
        'prompt': 'def f(items):\n    """Return the first key."""\n',
        'canonical_solution': '    return next(iter(items))\n',
    }
    context = TaskContext(task, {'contract': ''}, ArtifactStore(tmp_path), PipelineSettings())
    base = {'args': "({'a': 1, 'b': 2},)", 'kwargs': '{}'}
    reversed_order = {'args': "({'b': 2, 'a': 1},)", 'kwargs': '{}'}
    context.cohort_task = {
        'base_input_keys': [bound_call_key({'items': {'a': 1, 'b': 2}}, legacy=True)],
        'programs': [{'base': {'calls': [base]}}],
    }
    context.inputs = {'arms': {'plain': {'inputs': [base, reversed_order]}}}
    run_reference_oracle(context, reference_programs=TaskReferencePrograms())
    assert context.oracle['rejected'] == [{'index': 0, 'reason': 'base_duplicate'}]
    assert [row['expected'] for row in context.oracle['tests']] == ["'b'"]


def test_oracle_reports_output_limit_without_losing_other_inputs(tmp_path):
    task = {'task_id': 'Toy/1', 'entry_point': 'f', 'prompt': 'def f(n: int):\n    """Return n characters."""\n',
            'canonical_solution': '    return "x" * n\n'}
    context = TaskContext(task, {'contract': '    assert n >= 0\n'},
                          ArtifactStore(tmp_path), PipelineSettings())
    context.cohort_task = {'base_input_keys': []}
    context.inputs = {'arms': {'plain': {'inputs': [
        {'args': '(200000,)', 'kwargs': '{}'}, {'args': '(1,)', 'kwargs': '{}'},
    ]}}}

    result = run_reference_oracle(context, reference_programs=TaskReferencePrograms())
    assert result['arm_indices'] == {'plain': [0]}
    assert result['tests'][0]['expected'] == "'x'"
    rejected, = result['rejected']
    assert rejected['index'] == 0 and rejected['reason'] == 'reference_output_limit'
    assert rejected['outcomes'] == [
        {'status': 'error', 'reason': 'reference_output_limit', 'output_chars': 200002, 'max_output_chars': 200000}
    ] * 2


def test_model_any_cannot_override_a_declared_integer():
    from final.src.modular.tool_sampling.ledger import CandidateLedger
    from final.src.modular.tests.test_tool_sampling import builder, model
    raw = model()
    raw['types']['a'] = 'any'
    raw['domain'] = 'True'
    row = CandidateLedger('Toy/1', 'fixture', builder(), raw).add(
        {'arguments': {'a': '2,3', 'b': 0}}, {'tool': 'direct'})
    assert row['standard_args'] is None
    assert row['primary_error']['code'] == 'type_mismatch'


def test_pynguin_cannot_admit_wrong_type_when_trusted_contract_accepts_it(tmp_path, monkeypatch):
    from final.src.modular.pynguin import adapter
    from final.src.modular.pynguin import PynguinInputGenerator, PynguinSettings
    from final.src.modular.tests.test_pynguin_adapter import context, PYTHON
    ctx = context(tmp_path)
    ctx.metadata['contract'] = 'assert True'
    generator = PynguinInputGenerator(PynguinSettings(python=PYTHON))
    candidates = [{'args': repr((value,)), 'kwargs': '{}', 'test': f'test_{index}'}
                  for index, value in enumerate([True, {}, 2])]
    monkeypatch.setattr(generator, 'search_owner', lambda *args: {
        'owner': 'p1', 'status': 'complete', 'calls': candidates, 'rejected': []})
    monkeypatch.setattr(adapter, 'execute', lambda job: {'tests': [{'status': 'valid'}] * len(job['tests'])})
    batch = generator.construct(ctx, 'unused/', {})
    assert [row['args'] for row in batch['inputs']] == ['(2,)']
    assert [row['reason'] for row in batch['rejected']] == ['argument_type_mismatch:x'] * 2


def test_type_schema_changes_invalidate_pynguin_batch_source_info(tmp_path):
    from final.src.modular.pynguin import PynguinInputGenerator, PynguinSettings
    from final.src.modular.tests.test_pynguin_adapter import context
    ctx = context(tmp_path)
    generator = PynguinInputGenerator(PynguinSettings(python='/missing/python'))
    generator.run_task(ctx)
    ctx.metadata['input_types'] = {'x': 'str'}
    with pytest.raises(ValueError, match='source_info'):
        generator.run_task(ctx)


def test_public_literal_base_inputs_against_declared_types():
    checked = 0
    for task in load_tasks():
        builder = CallBuilder.for_source(task['prompt'], task['entry_point'])
        for call in ast.walk(ast.parse(task['test'])):
            if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name) or call.func.id != 'candidate':
                continue
            try:
                args = tuple(ast.literal_eval(arg) for arg in call.args)
                kwargs = {kw.arg: ast.literal_eval(kw.value) for kw in call.keywords}
            except (ValueError, TypeError):
                continue
            builder.validate_call({'args': repr(args), 'kwargs': repr(kwargs)})
            checked += 1
    assert checked == 1151


def test_metadata_only_fills_missing_annotations():
    builder = CallBuilder.for_source('def f(x: list[int]): pass', 'f', input_types={'x': 'Any'})
    with pytest.raises(ValueError, match='argument_type_mismatch:x'):
        builder.build_values({'x': [True]})

    builder = CallBuilder.for_source(
        'def f(xs: list, n): pass', 'f', input_types={'xs': 'list[int]', 'n': 'int'}
    )
    assert builder.build({'xs': ['a'], 'n': 1})['args'] == "(['a'], 1)"
    with pytest.raises(ValueError, match='argument_type_mismatch:n'):
        builder.build({'xs': ['a'], 'n': '1'})


def test_generic_humaneval_annotation_stays_generic():
    task = next(t for t in load_tasks() if t['task_id'] == 'HumanEval/30')
    builder = CallBuilder.for_source(task['prompt'], task['entry_point'])
    assert builder.signature.parameters['l'].annotation == 'list'
    assert builder.build({'l': ['a']})['args'] == "(['a'],)"
