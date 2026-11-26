"""Offline contracts for tool-generated inputs; no benchmark or model calls."""
import ast
import copy

import pytest

from final.src.modular.call_builder import CallBuilder


def builder():
    return CallBuilder.for_source('def f(a: int, b: int = 0):\n    pass\n', 'f')


def model():
    return {'types': {'a': 'int', 'b': 'int'}, 'domain': '1 <= a <= 5 and 0 <= b <= 4 and a+b <= 6',
            'domain_source_quote': 'adults 1–5, children 0–4, total at most 6',
            'strategies': {'a': {'kind': 'int', 'min': 1, 'max': 5},
                           'b': {'kind': 'int', 'min': 0, 'max': '6-a'}},
            'targets': [
                {'id': 'small', 'predicate': 'a+b < 4', 'context': 'True', 'origin': 'spec',
                 'source_quote': 'below four', 'kind': 'class'},
                {'id': 'edge', 'predicate': 'a+b == 4', 'context': 'a == 2', 'origin': 'spec',
                 'source_quote': 'four people', 'kind': 'boundary', 'boundary_side': 'at'},
                {'id': 'large', 'predicate': 'a+b >= 4', 'context': 'True', 'origin': 'spec',
                 'source_quote': 'discount for four or more', 'kind': 'rule', 'status': 'feasible'}],
            'factors': {'size': {'small': 'a+b < 4', 'large': 'a+b >= 4'},
                        'capacity': {'full': 'a+b == 6', 'spare': 'a+b < 6'}},
            'inputs': [{'arguments': {'a': 2, 'b': 2}}]}


def test_ledger_keeps_errors_at_earliest_stage_and_all_same_stage_errors():
    from final.src.modular.tool_sampling.ledger import CandidateLedger
    ledger = CandidateLedger('HumanEval/7', 'fixture', builder(), model())
    row = ledger.add({'oops': 3}, {'tool': 'direct', 'draw_index': 0})
    assert {e['code'] for e in row['errors']} == {'missing_field', 'unexpected_field'}
    assert row['primary_error']['stage'] == 'P2'
    assert row['standard_args'] is None and row['membership'] is None
    row = ledger.add({'arguments': {'a': True, 'b': float('inf')}}, {'tool': 'direct', 'draw_index': 1})
    assert {e['code'] for e in row['errors']} == {'bool_int_confusion', 'nan_inf', 'type_mismatch'}
    assert {e['stage'] for e in row['errors']} == {'P3'}
    assert row['membership'] is None


def test_ledger_binds_defaults_and_merges_sources_without_losing_duplicates():
    from final.src.modular.tool_sampling.ledger import CandidateLedger
    ledger = CandidateLedger('HumanEval/7', 'fixture', builder(), model())
    first = ledger.add({'arguments': {'a': 2}}, {'tool': 'direct', 'draw_index': 0})
    duplicate = ledger.add({'args': '(2, 0)', 'kwargs': '{}'}, {'tool': 'hypothesis', 'draw_index': 0})
    assert len(ledger.rows) == 2 and len(ledger.pool()) == 1
    assert first['dedup_group'] == duplicate['dedup_group']
    assert {s['tool'] for s in ledger.pool()[0]['sources']} == {'direct', 'hypothesis'}
    assert duplicate['selection_reason'] == 'duplicate'
    assert first['membership']['small']['target'] == 'true'


def test_membership_error_is_not_coverage_and_domain_rejection_is_not_parse_error():
    from final.src.modular.tool_sampling.ledger import CandidateLedger
    spec = model()
    spec['targets'][0]['predicate'] = 'a[0] == 1'
    ledger = CandidateLedger('HumanEval/7', 'fixture', builder(), spec)
    row = ledger.add({'arguments': {'a': 2}}, {'tool': 'direct', 'draw_index': 0})
    assert row['membership']['small']['target'] == 'error'
    error = next(e for e in row['errors'] if e['code'] == 'membership_error')
    assert 'TypeError' in error['detail']
    invalid = ledger.add({'arguments': {'a': 5, 'b': 4}}, {'tool': 'direct', 'draw_index': 1})
    assert invalid['primary_error']['code'] == 'domain_rejects'
    assert invalid['primary_error']['stage'] == 'V1'
    assert invalid not in ledger.pool()


def test_selector_preserves_unique_dt_witness_and_is_draw_order_independent():
    from final.src.modular.tool_sampling.ledger import CandidateLedger
    from final.src.modular.tool_sampling.selection import select_suite
    records = [{'arguments': {'a': a, 'b': b}} for a, b in [(1, 0), (2, 2), (2, 1)]]
    selections = []
    for candidates in (records, records[::-1]):
        ledger = CandidateLedger('HumanEval/7', 'fixture', builder(), model())
        for index, record in enumerate(candidates):
            ledger.add(record, {'tool': 'direct', 'draw_index': index})
        selected = select_suite(ledger, 1)
        selections.append(selected[0]['args'])
        assert ledger.selected_rows()[0]['membership']['large']['hit'] is True
    assert selections == ['(2, 2)', '(2, 2)']


def test_model_keeps_unsupported_expression_and_rejects_untrusted_domain():
    from final.src.modular.tool_sampling.model import validate_model
    spec = model()
    spec['targets'][0]['predicate'] = 'custom_predicate(a)'
    validated = validate_model(spec, builder())
    assert validated['targets'][0]['support'] == 'unsupported'
    spec['domain_source_quote'] = ''
    with pytest.raises(ValueError, match='domain_source_quote'):
        validate_model(spec, builder())


def test_hypothesis_real_constructor_is_seeded_and_respects_dependent_bounds():
    from final.src.modular.tool_sampling.constructors import sample_hypothesis
    from final.src.modular.tool_sampling.ledger import CandidateLedger
    ledgers = [CandidateLedger('HumanEval/7', 'fixture', builder(), model()) for _ in range(2)]
    receipts = [sample_hypothesis(ledger, draws=25, seed=17, seconds=5) for ledger in ledgers]
    calls = [[row['standard_args'] for row in ledger.rows] for ledger in ledgers]
    assert calls[0] == calls[1] and len(calls[0]) > 1
    for call in calls[0]:
        a, b = ast.literal_eval(call['args'])
        assert a + b <= 6
    assert all(receipt['draws'] <= 25 for receipt in receipts)


def test_planner_preserves_partial_rows_and_records_unrealizable_combination():
    from final.src.modular.tool_sampling.constructors import plan_combinations
    from final.src.modular.tool_sampling.ledger import CandidateLedger
    ledger = CandidateLedger('HumanEval/7', 'fixture', builder(), model())
    receipt = plan_combinations(ledger, rows=8, draws_per_row=5, seed=19, seconds=5)
    assert any(row['status'] == 'realized' for row in receipt['results'])
    impossible = [row for row in receipt['results'] if row['levels'] == {'size': 'small', 'capacity': 'full'}]
    assert impossible and impossible[0]['status'] == 'unknown'
    assert 'witness' not in impossible[0]['sampling']
    assert all(row['membership']['large']['domain'] == 'true' for row in ledger.pool())


def budgets():
    return dict(arms=['tool_direct', 'tool_hypothesis', 'tool_hypothesis_extra', 'tool_planner'],
                draws=12, sample_seconds=3, extra_draws=12, extra_seconds=3,
                planner_rows=4, planner_draws=4, planner_seconds=3,
                audit_cap=50, random_seeds=[11, 19])


def test_tool_generator_shares_pool_preserves_cap_and_replay_artifacts(tmp_path):
    from final.src.modular.artifacts import ArtifactStore
    from final.src.modular.context import PipelineSettings, TaskContext
    from final.src.modular.tool_sampling import ToolInputGenerator
    task = {'task_id': 'HumanEval/7', 'entry_point': 'f',
            'prompt': 'def f(a: int, b: int = 0):\n    pass\n'}
    context = TaskContext(task, {'contract': ''}, ArtifactStore(tmp_path), PipelineSettings(input_budget=2))
    context.cohort_task = {'generated': 1, 'programs': [], 'base_input_keys': []}
    generator = ToolInputGenerator(budgets(), preparations={'HumanEval/7': model()})
    result = generator.generate(context)
    assert all(len(batch['inputs']) <= 2 for batch in result['arms'].values())
    a0, a1 = (result['arms'][name] for name in ('tool_hypothesis', 'tool_hypothesis_extra'))
    assert a0['initial_pool_sha256'] == a1['initial_pool_sha256']
    snapshot = {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    context.artifacts = ArtifactStore(tmp_path, read_only=True)
    assert generator.generate(context) == result
    assert all(p.read_bytes() == data for p, data in snapshot.items())


def test_tool_budgets_are_explicit_and_reject_bools_or_empty_controls():
    from final.src.modular.tool_sampling import ToolInputGenerator
    with pytest.raises(ValueError):
        ToolInputGenerator({'draws': 10})
    for field, value in [('draws', True), ('sample_seconds', float('inf')), ('random_seeds', []), ('arms', ['typo'])]:
        config = budgets()
        config[field] = value
        with pytest.raises(ValueError):
            ToolInputGenerator(config)


def test_post_freeze_miss_taxonomy_distinguishes_selection_catalogue_and_pending():
    from final.src.modular.tool_sampling.audit import classify_misses
    rows = [dict(candidate_id='selected', selected=True, membership={'T': {'hit': True}}, sources=[]),
            dict(candidate_id='hit', selected=False, membership={'T': {'hit': True}}, sources=[]),
            dict(candidate_id='no_hit', selected=False, membership={'T': {'hit': False}}, sources=[])]
    failures = {'p1': {'hit'}, 'p2': {'no_hit'}, 'p3': set(), 'p4': {'selected'}}
    report = classify_misses(rows, failures, suite_detected=set(), complete=True)
    assert report['p1']['gap'] == 'selector_gap'
    assert report['p2']['gap'] == 'catalogue_gap'
    assert report['p3']['gap'] == 'generation_gap'
    assert report['p3']['parse_interface_gap'] == 'unknown'
    assert report['p4']['gap'] == 'oracle_eval_gap'
    partial = classify_misses(rows, failures, suite_detected=set(), complete=False)
    assert partial['p3']['gap'] == 'pending_audit_cap'


def test_pipeline_tool_generator_freezes_before_audit_and_replays_without_work(tmp_path, monkeypatch):
    from final.src.modular.artifacts import ArtifactStore
    from final.src.modular.context import PipelineSettings
    from final.src.modular.tool_sampling import ToolInputGenerator
    from final.src.modular.pipeline import BenchmarkPipeline
    from final.src.modular.references import TaskReferencePrograms
    from final.src.modular.tests.test_testing_arms_integration import write_fixture_cohort
    task = {'task_id': 'HumanEval/7', 'entry_point': 'f', 'prompt': 'def f(a: int, b: int = 0):\n    pass\n',
            'canonical_solution': '    return a+b\n', 'test': ''}
    cohort = write_fixture_cohort(tmp_path / 'cohort.json', [task])
    directory = tmp_path / 'run'
    def oracle(job):
        assert (directory / 'tasks/7/inputs.json').exists()
        return {'tests': [{'status': 'ok', 'expected': '0', 'input_key': call['args']} for call in job['tests']]}
    def evaluate(job):
        assert (directory / 'tasks/7/inputs.json').exists()
        return {'tests': [{'status': 'fail' if ast.literal_eval(call['args'])[0] == 2 else 'pass'} for call in job['tests']]}
    monkeypatch.setattr('final.src.modular.reference_oracle.execute', oracle)
    monkeypatch.setattr('final.src.modular.put_evaluation.execute', evaluate)
    generator = ToolInputGenerator(budgets(), preparations={'HumanEval/7': model()})
    pipeline = BenchmarkPipeline(cohort, ArtifactStore(directory), input_generator=generator,
        settings=PipelineSettings(input_budget=2), reference_programs=TaskReferencePrograms())
    result = pipeline.run([task], {'HumanEval/7': {'contract': '', 'atol': 0}})
    assert result['tool_sampling']['HumanEval/7']['tool_hypothesis']['pool_ceiling']['complete'] is True
    assert result['arms']['tool_hypothesis']['detected'] == 1
    saved_inputs = (directory / 'tasks/7/inputs.json').read_bytes()
    def forbidden(*args, **kwargs):
        pytest.fail('Replay invoked workload')
    monkeypatch.setattr('final.src.modular.reference_oracle.execute', forbidden)
    monkeypatch.setattr('final.src.modular.put_evaluation.execute', forbidden)
    monkeypatch.setattr('final.src.modular.tool_sampling.generator.sample_hypothesis', forbidden)
    replay = BenchmarkPipeline(cohort, ArtifactStore(directory, read_only=True), input_generator=generator,
        settings=pipeline.settings, reference_programs=TaskReferencePrograms())
    assert replay.run([task], {'HumanEval/7': {'contract': '', 'atol': 0}}) == result
    assert (directory / 'tasks/7/inputs.json').read_bytes() == saved_inputs


def test_console_tool_preview_counts_shared_preparation_once_per_task():
    from final.src.orchestration.config import preview
    config = budgets()
    result = preview({'cohort': 'humaneval164', 'task_numbers': [0,5,18,81,99,120], 'mode': 'tools', 'arms': config['arms'],
                      'tool_sampling': config})
    assert result['logical_call_cap'] == result['eligible_task_count']
    assert result['logical_calls_by_arm'] == {'tool_preparation_shared': result['eligible_task_count']}
    assert set(result['max_input_slots_by_arm'].values()) == {20 * result['eligible_task_count']}
    assert result['tool_sampling_budgets']['audit_cap'] == 50


@pytest.mark.parametrize('raw,code', [
    ([], 'wrong_record_type'),
    ({'args': 'not_a_literal'}, 'non_json_literal'),
    ({'args': '(1, 2, 3)'}, 'arg_count_mismatch'),
    ({'args': '(1,)', 'kwargs': "{'unknown': 1}"}, 'unknown_kwarg'),
    ({'arguments': {'a': '\ud800'}}, 'string_encoding'),
    ({'arguments': {'a': 1, 'b': 2, 'unknown': 0}}, 'unknown_kwarg'),
])
def test_candidate_taxonomy_raw_examples(raw, code):
    from final.src.modular.tool_sampling.ledger import CandidateLedger
    ledger = CandidateLedger('HumanEval/7', 'fixture', builder(), model())
    row = ledger.add(raw, {'tool': 'direct', 'draw_index': 0})
    assert code in {e['code'] for e in row['errors']}
    assert row['selected'] is False and row['membership'] is None


def test_planner_coverage_measures_actual_rows_instead_of_requested_labels():
    from final.src.modular.tool_sampling.ledger import CandidateLedger
    from final.src.modular.tool_sampling.reporting import coverage
    spec = model()
    ledger = CandidateLedger('HumanEval/7', 'fixture', builder(), spec)
    ledger.add({'arguments': {'a': 2, 'b': 2}},
               {'tool': 'hypothesis', 'planner_row_id': 'r0',
                'planner_levels': {'size': 'small', 'capacity': 'full'}})
    result = coverage({'candidate_ledger': ledger.rows, 'preparation': spec})
    assert result['combinations']['covered_pairwise'] == 1
    assert result['combinations']['cartesian_pairwise'] == 4
    assert result['planner_rows']['r0']['actual_witnesses'] == 0


def test_capped_pool_is_not_reported_as_full_ceiling(tmp_path, monkeypatch):
    from final.src.modular.tool_sampling.audit import classify_misses
    report = classify_misses([], {'p1': set()}, suite_detected=set(), complete=False)
    assert report['p1']['gap'] == 'pending_audit_cap'


@pytest.mark.parametrize('section,field', [('types', 'a'), ('target', 'origin'), ('target', 'kind'), ('target', 'status')])
def test_malformed_model_scalar_is_contract_error_not_crash(section, field):
    from final.src.modular.tool_sampling.model import validate_model
    spec = model()
    if section == 'types':
        spec[section][field] = []
    else:
        spec['targets'][0][field] = []
    with pytest.raises(ValueError):
        validate_model(spec, builder())


def test_value_decode_collects_errors_for_every_argument_in_same_stage():
    from final.src.modular.tool_sampling.ledger import CandidateLedger
    ledger = CandidateLedger('HumanEval/7', 'fixture', builder(), model())
    row = ledger.add({'arguments': {'a': {'__python_type__': 'bad', 'items': []},
                                    'b': {'__python_type__': 'bad', 'items': []}}},
                     {'tool': 'direct', 'draw_index': 0})
    assert len(row['errors']) == 2
    assert {item['stage'] for item in row['errors']} == {'P3'}
    assert {item['detail'].split(':', 1)[0] for item in row['errors']} == {'a', 'b'}


def test_detection_attribution_requires_exclusive_source_and_no_shared_witness():
    from final.src.modular.tool_sampling.audit import source_contributions
    rows = [dict(candidate_id='seed', sources=[{'tool': 'direct'}]),
            dict(candidate_id='shared', sources=[{'tool': 'direct'}, {'tool': 'hypothesis'}]),
            dict(candidate_id='planner', sources=[{'tool': 'hypothesis', 'planner_row_id': 'r0'}])]
    result = source_contributions(rows, {'p0': {'seed'}, 'p1': {'seed', 'shared'}, 'p2': {'planner'}})
    assert result['direct']['exclusive_only_detected_puts'] == ['p0']
    assert result['planner']['exclusive_only_detected_puts'] == ['p2']


def test_malformed_seed_encoding_is_retained_in_ledger_without_breaking_artifacts(tmp_path):
    from final.src.modular.artifacts import ArtifactStore
    from final.src.modular.context import PipelineSettings, TaskContext
    from final.src.modular.tool_sampling import ToolInputGenerator
    spec = model()
    spec['inputs'].append({'arguments': {'a': '\ud800', 'b': 0}})
    context = TaskContext({'task_id': 'HumanEval/7', 'entry_point': 'f',
        'prompt': 'def f(a: int, b: int = 0):\n    pass\n'}, {'contract': ''}, ArtifactStore(tmp_path), PipelineSettings())
    generator = ToolInputGenerator(budgets(), preparations={'HumanEval/7': spec})
    output = generator.generate(context)
    row = output['arms']['tool_direct']['candidate_ledger'][1]
    assert 'string_encoding' in {item['code'] for item in row['errors']}
    assert context.artifacts.read('tasks/7/tool_generation.json') == output


def test_hypothesis_does_not_swallow_worker_cancellation(monkeypatch):
    from final.src.modular.tool_sampling.constructors import sample_hypothesis
    from final.src.modular.tool_sampling.ledger import CandidateLedger
    class WorkerCancelled(Exception):
        pass
    ledger = CandidateLedger('HumanEval/7', 'fixture', builder(), model())
    def cancelled(*args, **kwargs):
        raise WorkerCancelled('cancel requested')
    monkeypatch.setattr(ledger, 'add', cancelled)
    with pytest.raises(WorkerCancelled):
        sample_hypothesis(ledger, draws=1, seed=1, seconds=3)


def test_selector_defers_membership_unknown_until_after_clean_diversity():
    from final.src.modular.tool_sampling.ledger import CandidateLedger
    from final.src.modular.tool_sampling.selection import select_suite
    spec = model()
    spec['targets'][0]['predicate'] = 'a == 1 or a[0] == 1'
    ledger = CandidateLedger('HumanEval/7', 'fixture', builder(), spec)
    ledger.add({'arguments': {'a': 2, 'b': 2}}, {'tool': 'direct', 'draw_index': 0})
    ledger.add({'arguments': {'a': 1, 'b': 0}}, {'tool': 'direct', 'draw_index': 1})
    suite = select_suite(ledger, 1)
    assert suite[0]['args'] == '(1, 0)'


def test_runtime_value_error_in_predicate_is_error_not_unsupported():
    from final.src.modular.tool_sampling.ledger import CandidateLedger
    spec = model()
    spec['targets'][0]['predicate'] = 'int("not a number") == a'
    row = CandidateLedger('HumanEval/7', 'fixture', builder(), spec).add(
        {'arguments': {'a': 2}}, {'tool': 'direct', 'draw_index': 0})
    assert row['membership']['small']['target'] == 'error'
    assert any(item['code'] == 'membership_error' and 'ValueError' in item['detail'] for item in row['errors'])


def test_invalid_boundary_side_is_schema_error_before_selection():
    from final.src.modular.tool_sampling.model import validate_model
    spec = model()
    spec['targets'][1]['boundary_side'] = []
    with pytest.raises(ValueError, match='boundary_side'):
        validate_model(spec, builder())


def test_tools_skip_ineligible_task_before_any_preparation_call(tmp_path):
    from final.src.modular.artifacts import ArtifactStore
    from final.src.modular.context import PipelineSettings, TaskContext
    from final.src.modular.tool_sampling import ToolInputGenerator
    context = TaskContext({'task_id': 'HumanEval/7'}, {}, ArtifactStore(tmp_path), PipelineSettings())
    context.cohort_task = {'generated': 0, 'programs': []}
    generator = ToolInputGenerator(budgets())
    generator.prepare_context(context)
    assert generator.generate(context) == {'task_id': 'HumanEval/7', 'skip': 'no_base_pass'}
    assert not (tmp_path / 'tasks/7/tool_generation.json').exists()



def test_list_any_annotation_preserves_unconstrained_elements_and_does_not_disable_tools(tmp_path):
    from final.src.modular.artifacts import ArtifactStore
    from final.src.modular.context import PipelineSettings, TaskContext
    from final.src.modular.tool_sampling import ToolInputGenerator
    task = {'task_id': 'HumanEval/22', 'entry_point': 'f',
            'prompt': 'from typing import List, Any\ndef f(values: List[Any]):\n    pass\n'}
    spec = {'types': {'values': 'list'}, 'domain': 'True', 'domain_source_quote': 'arbitrary list elements',
            'strategies': {'values': {'kind': 'sampled', 'values': [[1, "a", True], []]}},
            'targets': [{'id': 'empty', 'kind': 'class', 'origin': 'spec', 'source_quote': 'empty list',
                         'predicate': 'len(values) == 0', 'context': 'True'}], 'factors': {},
            'inputs': [{'arguments': {'values': [1, "a", True]}}]}
    context = TaskContext(task, {'contract': ''}, ArtifactStore(tmp_path), PipelineSettings())
    generator = ToolInputGenerator(budgets(), preparations={'HumanEval/22': spec})
    result = generator.generate(context)
    batch = result['arms']['tool_hypothesis']
    assert batch['status'] == 'generated' and batch['preparation_error'] is None
    assert batch['tool_receipts'][0]['status'] == 'complete'
    assert any('hypothesis' in {source['tool'] for source in row['sources']} for row in batch['candidate_ledger'])
    assert any(ast.literal_eval(call['args'])[0] == [1, 'a', True] for call in result['arms']['tool_direct']['inputs'])


def test_preparation_schema_pins_parameter_maps_and_rejects_saved_list_shape():
    from final.src.modular.tool_sampling.schema import preparation_schema, parse_preparation
    schema = preparation_schema(builder())
    assert schema['properties']['strategies']['additionalProperties'] is False
    assert set(schema['properties']['strategies']['required']) == {'a', 'b'}
    raw = model()
    assert parse_preparation(raw, builder())['strategies']['a']['kind'] == 'int'
    raw['strategies'] = list(raw['strategies'].values())
    with pytest.raises(ValueError, match='strategies'):
        parse_preparation(raw, builder())


def test_strict_preparation_rejects_prose_context_and_never_weakens_domain():
    from final.src.modular.tool_sampling.schema import parse_preparation
    raw=model()
    raw['targets'][0]['context']='Group with fewer than four people'
    prepared=parse_preparation(raw,builder())
    assert prepared['targets'][0]['support']=='unsupported'
    assert prepared['targets'][0]['context']==raw['targets'][0]['context']
    raw=model();raw['domain']='all(a > 0 for a in values)'
    with pytest.raises(ValueError,match='expression'):
        parse_preparation(raw,builder())


def test_strict_preparation_keeps_unsupported_constructor_explicit():
    from final.src.modular.tool_sampling.schema import parse_preparation
    raw = model()
    raw['strategies']['a'] = {'kind': 'unsupported', 'reason': 'No exact constructor for specified constraint'}
    assert parse_preparation(raw, builder())['strategies']['a']['kind'] == 'unsupported'
    raw['strategies']['b']['constraint'] = 'some prose'
    with pytest.raises(ValueError, match='constraint'):
        parse_preparation(raw, builder())


def test_any_parameter_preserves_literal_types_without_accepting_unsafe_values():
    from final.src.modular.tool_sampling.schema import parse_preparation
    from final.src.modular.tool_sampling.ledger import CandidateLedger
    raw = model()
    raw['types']['a'] = 'any'
    raw['domain'] = 'True'
    raw['targets'] = []
    signature = CallBuilder.for_source('def f(a: Any, b: int = 0): pass', 'f')
    prepared = parse_preparation(raw, signature)
    ledger = CandidateLedger('HumanEval/7', 'fixture', signature, prepared)
    row = ledger.add({'arguments': {'a': '2,3', 'b': 0}}, {'tool': 'direct'})
    assert ast.literal_eval(row['standard_args']['args']) == ('2,3', 0)
    bad = ledger.add({'arguments': {'a': float('inf'), 'b': 0}}, {'tool': 'direct'})
    assert bad['primary_error']['code'] == 'nan_inf'


def test_generator_requests_schema_without_adding_model_calls(tmp_path):
    import json
    from final.src.models.core_model import ModelResponse
    from final.src.modular.artifacts import ArtifactStore
    from final.src.modular.context import PipelineSettings, TaskContext
    from final.src.modular.tool_sampling import ToolInputGenerator
    class Calls:
        requests = []
        def token_count(self, messages):
            return 1
        def complete(self, task_number, call_name, messages, *, response_format, **kwargs):
            assert response_format['type'] == 'json_schema'
            self.requests.append((task_number, call_name, response_format['json_schema']['schema']))
            return ModelResponse(json.dumps(model()), {'total_tokens': 1}, 'stop')
    context = TaskContext({'task_id': 'HumanEval/7', 'entry_point': 'f',
        'prompt': 'def f(a: int, b: int = 0):\n    pass\n'}, {'contract': ''}, ArtifactStore(tmp_path),
        PipelineSettings(), calls=Calls())
    raw, failure = ToolInputGenerator(budgets()).prepare(context)
    assert failure is None and raw['types'] == {'a': 'int', 'b': 'int'}
    assert len(context.calls.requests) == 1
    assert context.calls.requests[0][2]['properties']['strategies']['additionalProperties'] is False


def test_generation_gate_blocks_invalid_preparation_before_freeze_or_evaluation(tmp_path, monkeypatch):
    import json
    from final.src.modular.artifacts import ArtifactStore
    from final.src.modular.context import PipelineSettings
    from final.src.modular.tool_sampling import ToolInputGenerator
    from final.src.modular.pipeline import BenchmarkPipeline
    from final.src.modular.references import TaskReferencePrograms
    from final.src.modular.tests.test_testing_arms_integration import write_fixture_cohort
    task = {'task_id': 'HumanEval/7', 'entry_point': 'f', 'prompt': 'def f(a: int, b: int = 0):\n    pass\n',
            'canonical_solution': '    return a+b\n', 'test': ''}
    cohort = write_fixture_cohort(tmp_path/'cohort.json', [task])
    raw = model()
    raw['strategies'] = list(raw['strategies'].values())
    generator = ToolInputGenerator(budgets(), preparations={'HumanEval/7': raw})
    def forbidden(*args, **kwargs):
        pytest.fail('Oracle ran despite invalid treatment')
    monkeypatch.setattr('final.src.modular.reference_oracle.execute', forbidden)
    out = tmp_path/'run'
    pipeline = BenchmarkPipeline(cohort, ArtifactStore(out), input_generator=generator,
        settings=PipelineSettings(), reference_programs=TaskReferencePrograms())
    with pytest.raises(ValueError, match='tool_generation_gate'):
        pipeline.run([task], {'HumanEval/7': {'contract': '', 'atol': 0}})
    gate = json.loads((out/'tool_generation_gate.json').read_text())
    assert gate['ready'] is False and not (out/'generation_frozen.json').exists()
    assert not (out/'tasks/7/oracle_0.json').exists()
    assert (out/'tasks/7/inputs.json').exists()


def test_tool_treatment_gate_distinguishes_actual_tools_from_unsupported():
    from final.src.modular.tool_sampling.gate import treatment_status
    base = dict(preparation_error=None, preparation=model(), candidate_ledger=[], tool_receipts=[])
    assert treatment_status('tool_hypothesis', base)['status'] == 'not_exercised'
    base['tool_receipts'] = [{'tool': 'hypothesis', 'status': 'complete', 'draws': 1, 'seed': 17}]
    base['candidate_ledger'] = [{'domain': 'true', 'errors': [], 'sources': [{'tool': 'hypothesis', 'seed': 17}]}]
    assert treatment_status('tool_hypothesis', base)['status'] == 'exercised'
    base['preparation']['factors'] = {}
    assert treatment_status('tool_planner', base)['status'] == 'not_applicable'
    base['preparation_error'] = {'code': 'invalid_response'}
    assert treatment_status('tool_direct', base)['status'] == 'invalid_preparation'


def test_real_tools_gate_requires_hypothesis_draw_and_planner_row(tmp_path):
    from final.src.modular.artifacts import ArtifactStore
    from final.src.modular.context import PipelineSettings, TaskContext
    from final.src.modular.tool_sampling import ToolInputGenerator
    from final.src.modular.tool_sampling.gate import treatment_status
    config = budgets()
    config['draws'] = 1
    spec = model()
    spec['inputs'] = [{'arguments': {'a': 1, 'b': 0}}]
    context = TaskContext({'task_id': 'HumanEval/7', 'entry_point': 'f',
        'prompt': 'def f(a: int, b: int = 0):\n    pass\n'}, {'contract': ''}, ArtifactStore(tmp_path), PipelineSettings())
    generator = ToolInputGenerator(config, preparations={'HumanEval/7': spec})
    context.inputs = generator.generate(context)
    status = {name: treatment_status(name, batch) for name, batch in context.inputs['arms'].items()}
    assert status['tool_hypothesis']['status'] == 'exercised'
    assert status['tool_planner']['status'] == 'exercised'
    assert status['tool_planner']['realized_rows'] >= 1
    generator.validate_generation([context])
    assert context.artifacts.read('tool_generation_gate.json')['ready'] is True


def test_saved_response_audit_keeps_raw_bytes_and_collects_shape_and_expression_errors(tmp_path, monkeypatch):
    import json
    from final.src.modular.tool_sampling import response_audit
    raw = model()
    raw['strategies'] = list(raw['strategies'].values())
    raw['targets'][0]['context'] = 'only small groups'
    path = tmp_path/'tasks/7/calls/tool_preparation/response.json'
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({'text': json.dumps(raw), 'finish_reason': 'stop'}))
    before = path.read_bytes()
    monkeypatch.setattr(response_audit, 'load_tasks', lambda: [{'task_id': 'HumanEval/7', 'entry_point': 'f',
        'prompt': 'def f(a: int, b: int = 0):\n    pass\n'}])
    report = response_audit.audit_saved_responses(tmp_path)
    assert report['tasks'] == 1 and report['valid_preparations'] == 0
    assert {'schema', 'expression'} <= {item['stage'] for item in report['rows'][0]['issues']}
    assert report['rows'][0]['automatic_repairs'] == []
    assert path.read_bytes() == before and report['source_unchanged'] is True


def test_treatment_status_survives_summary_and_is_not_an_efficacy_claim(tmp_path, monkeypatch):
    # Existing end-to-end fixture checks the real pre-freeze gate and report path.
    test_pipeline_tool_generator_freezes_before_audit_and_replays_without_work(tmp_path, monkeypatch)
    import json
    summary = json.loads((tmp_path/'run/modular_summary.json').read_text())
    assert summary['tool_treatments']['HumanEval/7']['tool_hypothesis']['status'] == 'exercised'
    assert (tmp_path/'run/tool_generation_gate.json').exists()


def test_extra_hypothesis_arm_rejects_unusable_shared_strategies(tmp_path):
    from final.src.modular.artifacts import ArtifactStore
    from final.src.modular.context import PipelineSettings, TaskContext
    from final.src.modular.tool_sampling import ToolInputGenerator
    from final.src.modular.tool_sampling.gate import treatment_status
    config = budgets()
    config['arms'] = ['tool_hypothesis_extra']
    spec = model()
    spec['strategies']['a'] = {'kind': 'unsupported', 'reason': 'Constructor deliberately unavailable'}
    context = TaskContext({'task_id': 'HumanEval/7', 'entry_point': 'f',
        'prompt': 'def f(a: int, b: int = 0):\n    pass\n'}, {'contract': ''}, ArtifactStore(tmp_path), PipelineSettings())
    generator = ToolInputGenerator(config, preparations={'HumanEval/7': spec})
    context.inputs = generator.generate(context)
    batch = context.inputs['arms']['tool_hypothesis_extra']
    status = treatment_status('tool_hypothesis_extra', batch)
    assert status['status'] == 'not_exercised' and status['component'] == 'shared_hypothesis'
    with pytest.raises(ValueError, match='tool_generation_gate'):
        generator.validate_generation([context])


@pytest.mark.parametrize('field', ['domain', 'predicate'])
def test_boolean_expression_validator_rejects_python_truthiness_of_integers(field):
    from final.src.modular.tool_sampling.schema import parse_preparation
    raw = model()
    if field == 'domain':
        raw['domain'] = 'a and b'
    else:
        raw['targets'][0]['predicate'] = 'a or b'
    with pytest.raises(ValueError, match='boolean expression'):
        parse_preparation(raw, builder())
    raw = model()
    raw['domain'] = 'a > 0 and b >= 0'
    assert parse_preparation(raw, builder())['domain'] == 'a > 0 and b >= 0'
