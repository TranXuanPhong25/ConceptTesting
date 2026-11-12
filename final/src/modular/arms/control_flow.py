"""Adaptive concept discovery with bounded, domain-checked coverage feedback."""
import ast
import copy
from dataclasses import asdict, dataclass

from .base import InputGenerationMethod
from ..call_builder import CallBuilder
from ..control_flow.analysis import analyze, hit
from ..control_flow.prompts import INSTRUCTION, messages
from ..control_flow.schema import parse_response
from ..input_prompts import compact_source
from ..response_json import load_response_json
from final.src.runtime.artifacts import digest
from final.src.runtime.execution import execute


@dataclass(frozen=True)
class ControlFlowSettings:
    rounds: int = 2
    target_limit: int = 6
    draws_per_concept: int = 32
    candidate_limit: int = 64
    sampling_seconds: float = 2

    def __post_init__(self):
        for name, upper in (('rounds', 3), ('target_limit', 6), ('draws_per_concept', 128), ('candidate_limit', 128)):
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= upper:
                raise ValueError('Invalid control-flow budget: ' + name)
        if type(self.sampling_seconds) not in (int, float) or not 0 < self.sampling_seconds <= 10:
            raise ValueError('Invalid sampling_seconds')


class ControlFlowArm(InputGenerationMethod):
    name = 'control_flow'
    uses_shared_prompt = False
    default_input_tokens = 4096

    def __init__(self, settings=None):
        self.settings = settings or ControlFlowSettings()

    def configuration(self):
        return {'protocol': 'coverage-concept-discovery-v1', 'budgets': asdict(self.settings),
                'instruction': INSTRUCTION, 'trace_timeout_cap_seconds': 1, 'baseline_call_limit': 300}

    def runtime_dependencies(self):
        return ('coverage', 'python-graphs', 'hypothesis', 'pydantic')

    def build_guidance(self, packet):
        return INSTRUCTION

    def run(self, context):
        return context.artifacts.load_or_compute(context.task_directory + '/control_flow/generation.json',
                                                 lambda: self.discover(context))

    @staticmethod
    def trace(context, program, records):
        observations = []
        for record in records:
            result = execute({'mode': 'control_flow', 'source': program['code'], 'entry': context.task['entry_point'],
                'context': context.task['prompt'], 'contract': context.metadata.get('contract', ''),
                'tests': [record], 'timeout': min(1, context.settings.timeout_seconds),
                'seed': context.settings.input_seed})
            observations.extend(result['tests'])
        return observations

    def discover(self, context):
        from ..tool_sampling.constructors import sample_hypothesis
        from ..tool_sampling.ledger import CandidateLedger, predicate_status
        from ..boundary_value_analysis.legacy.construction import input_identity
        if context.calls is None or context.packet is None:
            raise RuntimeError('Control-flow discovery requires prepared context and model calls')
        builder = CallBuilder.for_source(context.task['prompt'], context.task['entry_point'])
        visible = set(context.packet['visible_put_ids'])
        programs = [copy.deepcopy(program) for program in context.cohort_task['programs']
                    if program['id'] in visible and program['base']['status'] == 'pass']
        analyses, analysis_errors = [], []
        for program in programs:
            try:
                had_coverage = program['base'].get('coverage') is not None
                base_calls = program['base'].get('calls', [])
                if not had_coverage and len(base_calls) > 300:
                    analysis_errors.append({'program_id': program['id'], 'reason': 'baseline_call_budget_exceeded'})
                elif not had_coverage and base_calls:
                    observations = context.artifacts.load_or_compute(
                        context.task_directory + '/control_flow/base_' + digest(program['id'])[:16] + '.json',
                        lambda: self.trace(context, program, program['base']['calls']))
                    measured = [row['coverage'] for row in observations if row.get('domain') == 'valid' and 'coverage' in row]
                    # Only a complete recorded-call replay supports missing-gap claims.
                    if measured and len(measured) == len(observations):
                        program['base']['coverage'] = {
                            'lines': sorted({line for row in measured for line in row['lines']}),
                            'arcs': [list(arc) for arc in sorted({tuple(arc) for row in measured for arc in row['arcs']})]}
                analysis = analyze(program, context.task['entry_point'])
                analysis['baseline'] = {'source': 'cached_coverage' if had_coverage else 'recorded_call_replay',
                                        'recorded_calls': len(program['base'].get('calls', [])),
                                        'scope': 'available_base_evidence_not_unrecorded_calls'}
                analyses.append(analysis)
            except (ValueError, SyntaxError) as error:
                analysis_errors.append({'program_id': program['id'], 'reason': str(error)})
        # Round-robin prevents one early guard in one PUT from taking every slot.
        targets = []
        for index in range(self.settings.target_limit):
            for analysis in analyses:
                if index < len(analysis['targets']) and len(targets) < self.settings.target_limit:
                    targets.append(analysis['targets'][index])
        evidence = [{'program_id': row['program_id'], 'source_sha256': row['source_sha256'],
                     'def_use': row['def_use'], 'data_flow_status': row['data_flow_status'],
                     'coverage_status': row['coverage_status']} for row in analyses]
        source = [{'id': p['id'], 'code': compact_source(p['code']),
                   'base_inputs': [{key: call[key] for key in ('args', 'kwargs') if key in call}
                                   for call in p['base'].get('calls', [])[:12]]} for p in programs]
        omitted = []
        selected_source, selected_evidence = source, evidence
        while targets:
            used = {target['program_id'] for target in targets}
            selected_source = [row for row in source if row['id'] in used]
            selected_evidence = [row for row in evidence if row['program_id'] in used]
            request = messages(context.task, context.metadata.get('contract', ''), selected_source,
                               selected_evidence, targets, context.settings.input_budget)
            if context.calls.token_count(request) + context.settings.input_tokens + 128 <= context.settings.context_tokens:
                break
            omitted.append(targets.pop()['id'])
        source, evidence = selected_source, selected_evidence
        context.artifacts.write(context.task_directory + '/control_flow/analysis.json',
                                {'programs': analyses, 'errors': analysis_errors, 'selected_targets': targets,
                                 'context_omitted_targets': omitted})
        if not targets:
            unknown = not analyses or any(row['coverage_status'] == 'unknown' for row in analyses)
            return {'inputs': [], 'concepts': [], 'status': ('prompt_too_large' if omitted else
                    'coverage_unknown' if unknown else 'no_measured_gaps'),
                    'analysis_errors': analysis_errors,
                    'target_coverage': {'covered': None if unknown or omitted else 0,
                                        'total': None if unknown or omitted else 0},
                    'candidate_receipts': [], 'rounds': []}
        base_keys = set()
        for program in programs:
            for call in program['base'].get('calls', []):
                try:
                    base_keys.add(repr(input_identity(builder.signature, call)))
                except (ValueError, TypeError, SyntaxError):
                    pass
        concepts, receipts, rounds, errors = [], [], [], []
        candidates, covered = {}, set()
        target_programs = {target['program_id'] for target in targets}
        checks_per_round = self.settings.candidate_limit // self.settings.rounds
        candidates_per_round = max(1, checks_per_round // len(target_programs))
        feedback = None
        for round_index in range(self.settings.rounds):
            request = messages(context.task, context.metadata.get('contract', ''), source, evidence, targets,
                               context.settings.input_budget, feedback)
            if context.calls.token_count(request) + context.settings.input_tokens + 128 > context.settings.context_tokens:
                errors.append('prompt_too_large')
                break
            response = context.calls.complete(context.task_number, f'control_flow_round_{round_index}', request,
                temperature=context.settings.input_temperature, max_tokens=context.settings.input_tokens,
                seed=context.settings.input_seed + context.task_number + round_index)
            raw_path = context.task_directory + f'/control_flow/response_{round_index}.json'
            context.artifacts.write(raw_path, {'text': response.text, 'finish_reason': response.finish_reason,
                                               'usage': response.usage, 'request_sha256': digest(request)})
            try:
                raw, repairs = load_response_json(response.text)
                parsed = parse_response(raw, targets, builder.signature.parameters)
            except (ValueError, TypeError) as error:
                parsed, repairs = {'inputs': [], 'concepts': [], 'errors': [str(error)]}, []
            if response.finish_reason != 'stop':
                parsed['errors'].append('incomplete_response:' + str(response.finish_reason))
                parsed['concepts'] = []
            errors.extend(parsed['errors'])
            for concept in parsed['concepts']:
                concepts.append({**concept, 'round': round_index, 'semantic_status': 'hypothesis'})
            sampling = []
            model = {'types': {name: 'any' for name in builder.signature.parameters},
                     'domain': 'True', 'targets': [], 'factors': [], 'strategies': {}}
            ledger = CandidateLedger(context.task['task_id'], self.name, builder, model)
            for index, record in enumerate(parsed['inputs'][:context.settings.input_budget]):
                if not isinstance(record, dict):
                    continue
                ledger.add({'arguments': record.get('arguments')},
                           {'tool': 'llm', 'round': round_index, 'draw_index': index,
                            'concept_id': record.get('concept_id')})
            for concept in parsed['concepts']:
                if concept['strategies']:
                    ledger.model['strategies'] = concept['strategies']
                    sampling.append(sample_hypothesis(ledger, draws=self.settings.draws_per_concept,
                        seed=context.settings.input_seed + round_index * 1009 + len(sampling),
                        seconds=self.settings.sampling_seconds,
                        source={'concept_id': concept['id'], 'round': round_index}))
            pool = ledger.pool()
            # Direct calls keep their opportunity even if concept metadata failed.
            direct = [row for row in pool if any(s['tool'] == 'llm' for s in row['sources'])]
            sampled = [row for row in pool if row not in direct]
            pending = []
            for row in [*direct, *sampled]:
                call = row['canonical_args']
                key = repr(input_identity(builder.signature, call))
                if key in candidates:
                    for source_item in row['sources']:
                        if source_item not in candidates[key]['sources']:
                            candidates[key]['sources'].append(source_item)
                    continue
                if key in base_keys or len(pending) >= candidates_per_round:
                    continue
                candidates[key] = {'call': call, 'sources': row['sources'], 'hit_targets': []}
                pending.append((key, call))
            round_receipts = []
            for program in programs:
                relevant = [target for target in targets if target['program_id'] == program['id']]
                if not relevant or not pending:
                    continue
                remaining_checks = self.settings.candidate_limit - len(receipts) - len(round_receipts)
                attempted = pending[:max(0, remaining_checks)]
                if not attempted:
                    break
                observations = self.trace(context, program, [call for _, call in attempted])
                for (key, call), observation in zip(attempted, observations):
                    hits = [target['id'] for target in relevant if hit(target, observation)]
                    covered.update(hits)
                    candidates[key]['hit_targets'].extend(hits)
                    candidates[key].setdefault('domain', observation.get('domain'))
                    receipt = {'candidate_key': digest(key), 'program_id': program['id'], 'call': call,
                               'hit_targets': hits, **observation}
                    round_receipts.append(receipt)
            receipts.extend(round_receipts)
            concept_checks = []
            for concept in parsed['concepts']:
                target_hits, predicate_checks = [], []
                for key, candidate in candidates.items():
                    if not any(s.get('concept_id') == concept['id'] and s.get('round') == round_index
                               for s in candidate['sources']):
                        continue
                    bound = builder.signature.bind(*ast.literal_eval(candidate['call']['args']),
                                                    **ast.literal_eval(candidate['call']['kwargs']))
                    bound.apply_defaults()
                    status, detail = (predicate_status(concept['predicate'], dict(bound.arguments))
                                      if concept['predicate'] else ('unknown', 'predicate_not_supplied'))
                    predicate_checks.append({'candidate_key': digest(key), 'predicate': status, 'detail': detail})
                    if concept['target_id'] in candidate['hit_targets']:
                        target_hits.append(digest(key))
                concept_checks.append({'concept_id': concept['id'], 'target_id': concept['target_id'],
                                       'realized_candidate_keys': target_hits, 'predicate_checks': predicate_checks,
                                       'status': 'observed' if target_hits else 'pending',
                                       'semantic_status': 'hypothesis'})
            rounds.append({'round': round_index, 'errors': parsed['errors'], 'response_repairs': repairs,
                           'sampling': sampling, 'concept_checks': concept_checks,
                           'candidate_count': len(pending), 'candidate_ledger': ledger.rows})
            remaining = [target['id'] for target in targets if target['id'] not in covered]
            feedback = {'remaining_target_ids': remaining, 'concepts': parsed['concepts'],
                        'errors': parsed['errors'], 'concept_checks': concept_checks,
                        'candidate_observations_total': len(round_receipts),
                        'candidates': [{key: row[key] for key in ('candidate_key', 'program_id', 'call', 'domain', 'status', 'hit_targets')}
                                       for row in round_receipts[:12]]}
            if (not remaining and not parsed['errors']) or len(receipts) >= self.settings.candidate_limit:
                break
        valid = [row for row in candidates.values() if row.get('domain') == 'valid']
        selected, selected_coverage = [], set()
        for row in sorted(valid, key=lambda item: -len(set(item['hit_targets']))):
            if len(selected) >= context.settings.input_budget:
                break
            if set(row['hit_targets']) - selected_coverage:
                selected.append(row)
                selected_coverage.update(row['hit_targets'])
        for row in valid:
            if len(selected) >= context.settings.input_budget:
                break
            if row not in selected:
                selected.append(row)
        result = {'inputs': [row['call'] for row in selected], 'concepts': concepts,
                  'status': 'generated' if rounds else 'prompt_too_large', 'errors': errors,
                  'candidate_receipts': receipts, 'rounds': rounds,
                  'target_coverage': {'covered': len(covered), 'total': len(targets),
                                      'selected_covered': len(selected_coverage)},
                  'selected_targets': targets, 'analysis_errors': analysis_errors,
                  'model_calls': len(rounds), 'candidate_count': len(candidates),
                  'functional_bug_detection': 'pending_shared_reference_evaluation'}
        return result

    def extend_summary(self, contexts, summary, reporting):
        batches = [context.inputs['arms'][self.name] for context in contexts if not context.inputs.get('skip')]
        summary[self.name] = {'concepts': sum(len(batch['concepts']) for batch in batches),
            'model_calls': sum(batch.get('model_calls', 0) for batch in batches),
            'observed_targets': sum(batch['target_coverage']['covered'] or 0 for batch in batches),
            'selected_targets': sum(batch['target_coverage']['total'] or 0 for batch in batches),
            'coverage_pending_tasks': sum(batch['target_coverage']['total'] is None for batch in batches)}

    def render_summary(self, summary):
        return '\nConcept control-flow và target hits (tổng theo task, không phải số bug):\n\n' + str(summary[self.name]) + '\n'
