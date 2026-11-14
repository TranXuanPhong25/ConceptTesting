"""Two opt-in arms: semantic scenarios alone, or alongside C1/C2 gaps."""
import json

from .base import InputGenerationMethod
from ..catalogue_membership import membership_row, membership_summary
from ..catalogue_reporting import usage_by_arm
from ..control_flow.analysis import hit
from ..spec_obligation.prompts import INSTRUCTION, SOFT_EXAMPLES, messages
from ..spec_obligation.schema import parse_obligations, read_response
from final.src.runtime.artifacts import digest


class SpecObligationArm(InputGenerationMethod):
    name = 'spec_obligation'
    hybrid = False
    uses_shared_prompt = False
    default_input_tokens = 4096

    def configuration(self):
        return {'protocol': 'source-obligations-v1', 'hybrid': self.hybrid, 'model_calls': 2,
            'obligation_limit': 3, 'target_limit': 6, 'selected_input_limit': 20,
            'native_observation_limit': 64, 'base_replay_limit': 300,
            'hypothesis_draws_per_obligation': 32, 'sampling_seconds_per_obligation': 2,
            'instruction': INSTRUCTION, 'soft_examples': list(SOFT_EXAMPLES),
            'retrieval': False, 'functional_bug_detection': 'independent_shared_oracle_after_freeze'}

    def runtime_dependencies(self):
        return ('coverage', 'python-graphs', 'hypothesis', 'pydantic')

    def build_guidance(self, packet):
        return INSTRUCTION

    def run(self, context):
        path = context.task_directory + f'/{self.name}/generation.json'
        return context.artifacts.load_or_compute(path, lambda: self.discover(context))

    def discover(self, context):
        from ..spec_obligation.evidence import Evidence
        from ..tool_sampling.constructors import sample_hypothesis
        from ..tool_sampling.ledger import CandidateLedger
        if context.calls is None or context.packet is None:
            raise RuntimeError('Obligation generation requires prepared context and model calls')
        evidence = Evidence(context, self.name)
        targets = evidence.targets() if self.hybrid else []
        result = {'protocol': 'source-obligations-v1', 'inputs': [], 'rejected': [],
            'obligations': [], 'selected_targets': targets, 'rounds': [], 'sampling': [],
            'candidate_receipts': [], 'errors': list(evidence.errors), 'model_calls': 0,
            'functional_bug_detection': 'pending_shared_reference_evaluation'}
        input_budget = min(20, context.settings.input_budget)
        direct, selected_obligations = [], []
        for phase in ('propose', 'construct'):
            if phase == 'construct' and not (targets or selected_obligations):
                break
            request = messages(context, evidence, hybrid=self.hybrid, phase=phase,
                obligations=selected_obligations, targets=targets, input_budget=input_budget)
            if request is None:
                result['errors'].append('prompt_too_large:' + phase)
                break
            payload = json.loads(request[-1]['content'])
            supplied_ids = {p['program_id'] for p in payload['programs']}
            # Do not report model exposure to packets removed by the tokenizer gate.
            targets = payload['coverage_targets']
            response = context.calls.complete(context.task_number, f'{self.name}_{phase}', request,
                temperature=context.settings.input_temperature, max_tokens=context.settings.input_tokens,
                seed=context.settings.input_seed + context.task_number + result['model_calls'])
            result['model_calls'] += 1
            context.artifacts.write(context.task_directory + f'/{self.name}/response_{phase}.json',
                {'text': response.text, 'finish_reason': response.finish_reason, 'usage': response.usage,
                 'request_sha256': digest(request)})
            try:
                raw, repairs = read_response(response.text)
            except (ValueError, TypeError, RecursionError) as error:
                raw, repairs = {}, []
                result['errors'].append(str(error))
            if response.finish_reason != 'stop':
                result['errors'].append('incomplete_response:' + str(response.finish_reason))
            rows = raw.get('inputs', [])
            if isinstance(rows, list):
                direct.extend((row, {'tool': 'llm', 'phase': phase, 'index': index,
                    'obligation_id': row.get('obligation_id') if isinstance(row, dict) else None})
                    for index, row in enumerate(rows[:input_budget]))
            else:
                result['errors'].append('inputs_list_required')
            if phase == 'propose':
                obligations, errors = parse_obligations(raw, evidence)
                result['errors'].extend(errors)
                for obligation in obligations:
                    if obligation['program_id'] not in supplied_ids:
                        result['errors'].append('obligation_bound_to_omitted_program')
                        continue
                    obligation['base_membership'] = evidence.base_membership(obligation)
                    result['obligations'].append(obligation)
                    if obligation['base_membership']['status'] != 'hit':
                        selected_obligations.append(obligation)
                result['selected_obligation_ids'] = [row['id'] for row in selected_obligations]
            result['rounds'].append({'phase': phase, 'response_repairs': repairs,
                'finish_reason': response.finish_reason, 'supplied_program_ids': sorted(supplied_ids, key=repr),
                'supplied_target_ids': [row['id'] for row in targets]})

        model = {'types': {name: 'any' for name in evidence.builder.signature.parameters},
                 'domain': 'True', 'targets': [], 'strategies': {}}
        ledger = CandidateLedger(context.task['task_id'], self.name, evidence.builder, model)
        for raw, origin in direct:
            try:
                # Canonicalization ignores bad labels, never signature/value errors.
                call = evidence.canonical_call(raw)
                ledger.add(call, origin)
            except (ValueError, TypeError, KeyError, SyntaxError, RecursionError) as error:
                result['rejected'].append({'source': origin, 'reason': str(error)[:500]})
        for obligation in selected_obligations:
            if not obligation['strategies']:
                continue
            if set(obligation['strategies']) != set(evidence.builder.signature.parameters):
                result['sampling'].append({'obligation_id': obligation['id'], 'tool': 'hypothesis',
                    'status': 'unsupported', 'draws': 0, 'detail': 'strategy_parameter_mismatch'})
                continue
            ledger.model = {**model, 'strategies': obligation['strategies']}
            receipt = sample_hypothesis(ledger, draws=32,
                seed=context.settings.input_seed + context.task_number + len(result['sampling']), seconds=2,
                predicate=obligation['predicate'], source={'obligation_id': obligation['id']})
            result['sampling'].append({'obligation_id': obligation['id'], **receipt})

        candidates, candidate_keys = [], set()
        for row in ledger.pool():
            if evidence.key(row['canonical_args']) in evidence.base_keys:
                result['rejected'].append({'candidate_id': row['candidate_id'], 'reason': 'duplicate_base',
                                           'sources': row['sources']})
                continue
            key = evidence.key(row['canonical_args'])
            if key in candidate_keys:
                result['rejected'].append({'candidate_id': row['candidate_id'], 'reason': 'duplicate_generated'})
                continue
            candidate_keys.add(key)
            candidates.append({'call': row['canonical_args'], 'sources': row['sources'],
                'candidate_id': row['candidate_id'], 'observations': {}, 'target_hits': [], 'obligation_hits': []})
        # Give every candidate an initial observation before spending the rest on other PUTs.
        owners = list(dict.fromkeys([row['program_id'] for row in selected_obligations] +
                                    [row['program_id'] for row in targets])) or list(evidence.by_id)
        for offset in range(len(owners)):
            for index, candidate in enumerate(candidates):
                if len(result['candidate_receipts']) >= 64:
                    break
                program_id = owners[(index + offset) % len(owners)]
                observation = evidence.observe(evidence.by_id[program_id], candidate['call'])
                candidate['observations'][program_id] = observation
                hits = [t['id'] for t in targets if t['program_id'] == program_id and hit(t, observation)]
                candidate['target_hits'].extend(hits)
                result['candidate_receipts'].append({'candidate_id': candidate['candidate_id'],
                    'program_id': program_id, 'source_sha256': evidence.analyses[program_id]['source_sha256'],
                    'call': candidate['call'], 'sources': candidate['sources'], 'hit_targets': hits, **observation})
            if len(result['candidate_receipts']) >= 64:
                break
        for candidate in candidates:
            for obligation in result['obligations']:
                status, _ = evidence.scenario(obligation, candidate['call'],
                                             candidate['observations'].get(obligation['program_id']))
                if status is True:
                    candidate['obligation_hits'].append(obligation['id'])
        valid = [row for row in candidates if any(obs.get('domain') == 'valid'
                                                  for obs in row['observations'].values())]
        selected, covered = [], set()
        for row in sorted(valid, key=lambda row: -(len(row['target_hits']) + len(row['obligation_hits']))):
            gains = set(row['target_hits'] + row['obligation_hits']) - covered
            if gains and len(selected) < input_budget:
                selected.append(row)
                covered |= gains
        for row in valid:
            if len(selected) >= input_budget:
                break
            if row not in selected:
                selected.append(row)
        for obligation in result['obligations']:
            outcomes = [evidence.scenario(obligation, row['call'], row['observations'].get(obligation['program_id']))
                        for row in selected]
            obligation['new_membership'] = membership_row(obligation['id'], outcomes, list(range(len(selected))))
        for row in candidates:
            if not any(obs.get('domain') == 'valid' for obs in row['observations'].values()):
                result['rejected'].append({'candidate_id': row['candidate_id'],
                    'reason': 'no_valid_native_observation' if row['observations'] else 'native_budget_exhausted'})
        result.update(inputs=[row['call'] for row in selected], selected_targets=targets,
            target_coverage={'covered': len({t for row in selected for t in row['target_hits']}), 'total': len(targets)},
            candidate_ledger=ledger.rows, base_receipts=evidence.base_receipts,
            analysis=list(evidence.analyses.values()), model_calls=result['model_calls'],
            coverage_pending_programs=sum(row['coverage_status'] == 'unknown' for row in evidence.analyses.values()),
            observation_count=len(result['candidate_receipts']), candidate_count=len(candidates),
            status='generated' if selected else 'no_valid_novel_inputs' if result['rounds'] else 'prompt_too_large')
        context.artifacts.write(context.task_directory + f'/{self.name}/evidence.json',
            {'analysis': result['analysis'], 'errors': evidence.errors, 'base_receipts': evidence.base_receipts})
        return result

    def extend_summary(self, contexts, summary, reporting):
        batches = [ctx.inputs['arms'][self.name] for ctx in contexts if not ctx.inputs.get('skip')]
        obligations = [row for batch in batches for row in batch.get('obligations', [])]
        summary[self.name] = {'model_calls': sum(batch.get('model_calls', 0) for batch in batches),
            'call_usage': usage_by_arm(contexts[0].artifacts.directory, [self.name])[self.name],
            'obligations': len(obligations),
            'base_membership': membership_summary([row['base_membership'] for row in obligations]),
            'new_membership': membership_summary([row['new_membership'] for row in obligations]),
            'selected_structural_targets': sum(batch.get('target_coverage', {}).get('total', 0) for batch in batches),
            'hit_structural_targets': sum(batch.get('target_coverage', {}).get('covered', 0) for batch in batches),
            'coverage_pending_tasks': sum('target_coverage' not in batch or bool(batch.get('coverage_pending_programs')) for batch in batches),
            'duplicate_base_inputs': sum(row['reason'] == 'duplicate_base' for batch in batches for row in batch.get('rejected', [])),
            'hypothesis_receipts': len([row for batch in batches for row in batch.get('sampling', [])]),
            'hypothesis_unsupported': sum(row['status'] == 'unsupported' for batch in batches for row in batch.get('sampling', []))}

    def render_summary(self, summary):
        return (f'\n{self.name}: số obligation instances và structural targets được đo theo task/PUT; '
                'hit là scenario/reach, không phải số bug. Applicability vẫn là hypothesis.\n\n' +
                json.dumps(summary[self.name], ensure_ascii=False) + '\n')


class ControlFlowObligationArm(SpecObligationArm):
    name = 'control_flow_obligation'
    hybrid = True
