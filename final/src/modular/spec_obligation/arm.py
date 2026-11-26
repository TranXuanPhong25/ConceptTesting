"""Repaired CF obligation generation using semantic scenarios and C1/C2 gaps."""
import json
from itertools import islice, zip_longest

from ..arm_names import REPAIRED_OBLIGATION_ARM_NAME
from ..common import InputGenerationMethod
from ..common.membership import membership_row, membership_summary
from ..catalogue_reporting import usage_by_arm
from ..control_flow.analysis import hit, unobserved_step
from .prompts import INSTRUCTION, OBLIGATION_LIMIT, SOFT_EXAMPLES, messages, propose_retry_messages
from ..response_json import read_input_object
from .schema import parse_obligations
from final.src.runtime.artifacts import digest


PROTOCOL = 'source-obligations-v1-seed-feedback'


def is_llm_candidate(candidate):
    return any(origin.get('tool') == 'llm' for origin in candidate['sources'])


def interleave_sources(candidates):
    groups = {}
    for candidate in candidates:
        origin = candidate['sources'][0]
        group = origin['obligation_id'] if origin['tool'] == 'hypothesis' else None
        groups.setdefault(group, []).append(candidate)
    return [row for turn in zip_longest(*groups.values()) for row in turn if row is not None]


def order_candidates_for_trace(candidates):
    llm_rows = [row for row in candidates if is_llm_candidate(row)]
    hypothesis_rows = [row for row in candidates if not is_llm_candidate(row)]
    return llm_rows + interleave_sources(hypothesis_rows)


def select_candidates(valid_candidates, limit, covered=None):
    selected = []
    covered_labels = set() if covered is None else set(covered)
    for row in sorted(valid_candidates, key=lambda item: -(len(item['target_hits']) + len(item['obligation_hits']))):
        gains = set(row['target_hits'] + row['obligation_hits']) - covered_labels
        if gains and len(selected) < limit:
            selected.append(row)
            covered_labels |= gains
    for row in valid_candidates:
        if len(selected) >= limit:
            break
        if row not in selected:
            selected.append(row)
    return selected, covered_labels


def observation_pairs(candidates, owners, owner_by_label):
    if not owners:
        return
    orders = []
    for index, row in enumerate(candidates):
        start = index % len(owners)
        rotated = owners[start:] + owners[:start]
        preferred = [owner_by_label[label] for origin in row['sources'] for field in ('target_id', 'obligation_id')
                     if isinstance(label := origin.get(field), str) and label in owner_by_label]
        orders.append(list(dict.fromkeys(preferred + rotated)))
    for owner_index in range(len(owners)):
        for row, order in zip(candidates, orders):
            yield row, order[owner_index]


def trace_candidate(evidence, candidate, call, owner, targets):
    observation = evidence.observe(evidence.by_id[owner], call)
    return {'candidate_id': candidate['candidate_id'], 'program_id': owner,
            'source_sha256': evidence.analyses[owner]['source_sha256'], 'call': call,
            'sources': list(candidate['sources']),
            'hit_targets': [t['id'] for t in targets if t['program_id'] == owner and hit(t, observation)],
            **observation}


def observe_seeds(evidence, candidates, targets):
    """Try one novel seed per supplied target on its own PUT before construct."""
    unique = {}
    for row in candidates:
        key = evidence.key(row['canonical_args'])
        if key not in evidence.base_keys:
            unique.setdefault(key, row)
    seeds = list(unique.values())
    observations = {}
    if not seeds:
        return observations
    for index, target in enumerate(targets):
        row = next((seed for seed in seeds if any(origin.get('target_id') == target['id']
                   for origin in seed['sources'])), seeds[index % len(seeds)])
        owner = target['program_id']
        pair = (row['candidate_id'], owner)
        if pair not in observations:
            observations[pair] = trace_candidate(evidence, row, row['canonical_args'], owner, targets)
            observations[pair]['trace_phase'] = 'propose'
    return observations


def feedback_for_targets(targets, receipts):
    feedback = []
    for target in targets:
        row = {'target_id': target['id'], 'status': 'untried'}
        feedback.append(row)
        on_owner = [r for r in receipts if r['program_id'] == target['program_id']]
        if not on_owner:
            continue
        best = max(on_owner, key=lambda r: (target['id'] in r['hit_targets'],
                   r.get('domain') == 'valid' and r.get('status') == 'executed' and 'coverage' in r,
                   any(s.get('target_id') == target['id'] for s in r['sources'])))
        row['input'] = {k: best['call'][k] for k in ('args', 'kwargs')}
        if target['id'] in best['hit_targets']:
            row['status'] = 'hit'
        elif best.get('domain') == 'valid' and best.get('status') == 'executed' and 'coverage' in best:
            row['status'] = 'miss'
            row.update(unobserved_step(target, best['coverage']))
        else:
            row.update(status='unknown', reason=best.get('status', 'missing_trace'))
    return feedback


class RepairedControlFlowObligationArm(InputGenerationMethod):
    name = REPAIRED_OBLIGATION_ARM_NAME
    uses_shared_prompt = False

    def configuration(self):
        return {'protocol': PROTOCOL,
            'obligation_limit': OBLIGATION_LIMIT, 'target_limit': 6, 'selected_input_limit': 20,
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
        from .evidence import Evidence
        from ..tool_sampling.constructors import sample_hypothesis
        from ..tool_sampling.ledger import CandidateLedger
        if context.calls is None or context.packet is None:
            raise RuntimeError('Obligation generation requires prepared context and model calls')
        evidence = Evidence(context, self.name)
        targets = evidence.targets()
        result = {'protocol': PROTOCOL, 'inputs': [], 'rejected': [],
            'obligations': [], 'selected_targets': targets, 'rounds': [], 'sampling': [],
            'candidate_receipts': [], 'errors': list(evidence.errors),
            'functional_bug_detection': 'pending_shared_reference_evaluation'}
        input_budget = min(20, context.settings.input_budget)
        model = {'types': {name: 'any' for name in evidence.builder.signature.parameters},
                 'domain': 'True', 'targets': [], 'strategies': {}}
        ledger = CandidateLedger(context.task['task_id'], self.name, evidence.builder, model)
        selected_obligations = []
        failed_proposal = None
        seed_observations, prompted_targets = {}, {}
        seed_feedback = None
        for phase in ('propose', 'construct'):
            if phase == 'construct' and not (targets or selected_obligations or failed_proposal):
                break
            request = messages(
                context,
                evidence,
                phase=phase,
                obligations=selected_obligations,
                targets=targets,
                input_budget=input_budget,
                failed_proposal=failed_proposal,
                seed_feedback=seed_feedback,
            )
            if request is None:
                result['errors'].append('prompt_too_large:' + phase)
                break
            payload = json.loads(request[-1]['content'])
            if failed_proposal is not None:
                result['proposal_history_supplied'] = any(message['role'] == 'assistant' and
                    message['content'] == failed_proposal[1] for message in request)
            supplied_ids = {p['program_id'] for p in payload['programs']}
            supplied_obligations = {row['id'] for row in payload['obligations']}
            # Do not report model exposure to packets removed by the tokenizer gate.
            targets = payload['coverage_targets']
            supplied_targets = {t['id']: t for t in targets}
            prompted_targets.update(supplied_targets)
            call_index = len(result['rounds']) + ('propose_retry' in result)
            response = context.calls.complete(
                context.task_number,
                f'{self.name}_{phase}',
                request,
                temperature=context.settings.input_temperature,
                max_tokens=context.settings.input_tokens,
                seed=context.settings.input_seed + context.task_number + call_index,
            )
            context.artifacts.write(context.task_directory + f'/{self.name}/response_{phase}.json',
                {'text': response.text, 'finish_reason': response.finish_reason, 'usage': response.usage,
                 'request_sha256': digest(request)})
            parse_failure = None
            try:
                raw, repairs = read_input_object(response.text)
                if phase == 'propose' and targets and 'complete_input_records_salvaged' in repairs:
                    parse_failure = 'complete_input_records_salvaged'
            except (ValueError, TypeError, RecursionError) as error:
                raw, repairs = {}, []
                result['errors'].append(str(error))
                parse_failure = str(error)
            if response.finish_reason != 'stop':
                result['errors'].append('incomplete_response:' + str(response.finish_reason))
                if parse_failure is None and phase == 'propose':
                    parse_failure = 'incomplete_response:' + str(response.finish_reason)

            if phase == 'propose' and parse_failure is not None:
                retry_request = propose_retry_messages(context, request, parse_failure)
                if retry_request is not None:
                    retry_response = context.calls.complete(
                        context.task_number,
                        f'{self.name}_propose_retry',
                        retry_request,
                        temperature=context.settings.input_temperature,
                        max_tokens=context.settings.input_tokens,
                        seed=context.settings.input_seed + context.task_number + 1000,
                    )
                    context.artifacts.write(
                        context.task_directory + f'/{self.name}/response_propose_retry.json',
                        {'text': retry_response.text, 'finish_reason': retry_response.finish_reason,
                         'usage': retry_response.usage, 'request_sha256': digest(retry_request)},
                    )
                    retry_failure = None
                    try:
                        retry_raw, retry_repairs = read_input_object(retry_response.text)
                        if 'complete_input_records_salvaged' in retry_repairs:
                            retry_failure = 'complete_input_records_salvaged'
                    except (ValueError, TypeError, RecursionError) as retry_error:
                        retry_raw, retry_repairs = {}, []
                        result['errors'].append('propose_retry:' + str(retry_error))
                        retry_failure = str(retry_error)
                    if retry_response.finish_reason != 'stop':
                        result['errors'].append('propose_retry:incomplete_response:' + str(retry_response.finish_reason))
                        if retry_failure is None:
                            retry_failure = 'incomplete_response:' + str(retry_response.finish_reason)
                    trigger = parse_failure
                    if retry_failure is None:
                        raw, repairs, response = retry_raw, retry_repairs, retry_response
                        parse_failure = None
                        result['propose_retry'] = {'retried': True, 'succeeded': True, 'trigger': trigger}
                    else:
                        result['propose_retry'] = {
                            'retried': True, 'succeeded': False,
                            'trigger': trigger, 'retry_error': retry_failure,
                        }
                        if len(retry_raw.get('inputs', [])) > len(raw.get('inputs', [])):
                            raw, repairs, response = retry_raw, retry_repairs, retry_response
                            parse_failure = retry_failure
                if parse_failure is not None:
                    failed_proposal = (request, response.text, parse_failure)
                    result['proposal_history_supplied'] = False
            rows = raw.get('inputs', [])
            if isinstance(rows, list):
                for index, row in enumerate(rows[:input_budget]):
                    origin = {'tool': 'llm', 'phase': phase, 'index': index,
                              'obligation_id': row.get('obligation_id') if isinstance(row, dict) else None}
                    obligation_label = origin['obligation_id']
                    if obligation_label is not None and (
                            not isinstance(obligation_label, str) or
                            phase == 'construct' and obligation_label not in supplied_obligations):
                        origin['unbound_obligation_id'] = (obligation_label if isinstance(obligation_label, str)
                                                           else type(obligation_label).__name__)
                        origin['obligation_id'] = None
                    label = row.get('target_id') if isinstance(row, dict) else None
                    if isinstance(label, str) and label in supplied_targets:
                        origin['target_id'] = label
                    try:
                        ledger.add(evidence.canonical_call(row), origin)
                    except (ValueError, TypeError, KeyError, SyntaxError, RecursionError) as error:
                        result['rejected'].append({'source': origin, 'reason': str(error)[:500]})
            else:
                result['errors'].append('inputs_list_required')
            if phase == 'propose':
                obligations, errors = parse_obligations(raw, evidence, limit=OBLIGATION_LIMIT)
                result['errors'].extend(errors)
                for obligation in obligations:
                    if obligation['program_id'] not in supplied_ids:
                        result['errors'].append('obligation_bound_to_omitted_program')
                        continue
                    obligation['base_membership'] = evidence.base_membership(obligation)
                    result['obligations'].append(obligation)
                    if obligation['base_membership']['status'] != 'hit':
                        selected_obligations.append(obligation)
                if not selected_obligations and result['obligations']:
                    # A coarse predicate can mark base_membership='hit' without exercising
                    # the deeper semantic/implementation scenario; retain for construct & sampling.
                    selected_obligations = list(result['obligations'])
                    result['base_hit_obligations_retained'] = True
                result['selected_obligation_ids'] = [row['id'] for row in selected_obligations]
                accepted_ids = {o['id'] for o in result['obligations']}
                for row in ledger.pool():
                    for origin in row['sources']:
                        label = origin['obligation_id']
                        if label is not None and label not in accepted_ids:
                            origin['unbound_obligation_id'] = label
                            origin['obligation_id'] = None
                if targets:
                    seed_observations = observe_seeds(evidence, ledger.pool(), targets)
                    seed_feedback = feedback_for_targets(targets, seed_observations.values())
                    result['seed_feedback'] = seed_feedback
                    result['seed_observation_count'] = len(seed_observations)
                    result['candidate_receipts'].extend(seed_observations.values())
            result['rounds'].append({'phase': phase, 'response_repairs': repairs,
                'finish_reason': response.finish_reason, 'supplied_program_ids': sorted(supplied_ids, key=repr),
                'supplied_target_ids': [row['id'] for row in targets]})
            if phase == 'construct':
                result['rounds'][-1]['supplied_obligation_ids'] = sorted(supplied_obligations)
                result['rounds'][-1]['feedback_target_ids'] = [r['target_id'] for r in payload.get('seed_feedback', [])]
                result['rounds'][-1]['omitted_target_ids'] = sorted(prompted_targets.keys() - supplied_targets.keys())
                result['rounds'][-1]['omitted_obligation_ids'] = [o['id'] for o in selected_obligations
                                                                  if o['id'] not in supplied_obligations]

        targets = list(prompted_targets.values())
        for obligation in selected_obligations:
            if not obligation['strategies']:
                continue
            if set(obligation['strategies']) != set(evidence.builder.signature.parameters):
                result['sampling'].append({'obligation_id': obligation['id'], 'tool': 'hypothesis',
                    'status': 'unsupported', 'draws': 0, 'detail': 'strategy_parameter_mismatch'})
                continue
            ledger.model = {**model, 'strategies': obligation['strategies']}
            receipt = sample_hypothesis(
                ledger,
                draws=32,
                seed=context.settings.input_seed + context.task_number + len(result['sampling']),
                seconds=2,
                predicate=obligation['predicate'],
                source={'obligation_id': obligation['id']},
            )
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
        owner_by_label = {}
        candidates = order_candidates_for_trace(candidates)
        owner_by_label = {row['id']: row['program_id'] for row in selected_obligations}
        owner_by_label.update({t['id']: t['program_id'] for t in targets})
        by_id = {c['candidate_id']: c for c in candidates}
        for (candidate_id, owner), receipt in seed_observations.items():
            candidate = by_id[candidate_id]
            candidate['observations'][owner] = receipt
            candidate['target_hits'].extend(receipt['hit_targets'])
        owners = list(dict.fromkeys([row['program_id'] for row in selected_obligations] +
                                    [row['program_id'] for row in targets])) or list(evidence.by_id)
        unseen = ((candidate, owner) for candidate, owner in observation_pairs(candidates, owners, owner_by_label)
                  if owner not in candidate['observations'])
        for candidate, owner in islice(unseen, 64 - len(seed_observations)):
            receipt = trace_candidate(evidence, candidate, candidate['call'], owner, targets)
            receipt['trace_phase'] = 'construct'
            candidate['observations'][owner] = receipt
            candidate['target_hits'].extend(receipt['hit_targets'])
            result['candidate_receipts'].append(receipt)
        for candidate in candidates:
            for obligation in result['obligations']:
                status, _ = evidence.scenario(obligation, candidate['call'],
                                             candidate['observations'].get(obligation['program_id']))
                if status is True:
                    candidate['obligation_hits'].append(obligation['id'])
        valid = [row for row in candidates if any(obs.get('domain') == 'valid'
                                                  for obs in row['observations'].values())]
        llm_valid = [row for row in valid if is_llm_candidate(row)]
        hypothesis_valid = [row for row in valid if not is_llm_candidate(row)]
        selected, covered = select_candidates(llm_valid, input_budget)
        llm_input_count = len(selected)
        hypothesis_selected, covered = select_candidates(hypothesis_valid, len(hypothesis_valid), covered)
        selected.extend(hypothesis_selected)
        result['llm_input_count'] = llm_input_count
        result['hypothesis_input_count'] = len(hypothesis_selected)
        selected_ids = {row['candidate_id'] for row in selected}
        for row in ledger.pool():
            row['selected'] = row['candidate_id'] in selected_ids
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
            analysis=list(evidence.analyses.values()),
            coverage_pending_programs=sum(row['coverage_status'] == 'unknown' for row in evidence.analyses.values()),
            observation_count=len(result['candidate_receipts']), candidate_count=len(candidates),
            status='generated' if selected else 'no_valid_novel_inputs' if result['rounds'] else 'prompt_too_large')
        context.artifacts.write(context.task_directory + f'/{self.name}/evidence.json',
            {'analysis': result['analysis'], 'errors': evidence.errors, 'base_receipts': evidence.base_receipts})
        return result

    def extend_summary(self, contexts, summary, reporting):
        batches = [ctx.inputs['arms'][self.name] for ctx in contexts if not ctx.inputs.get('skip')]
        obligations = [row for batch in batches for row in batch.get('obligations', [])]
        summary[self.name] = {'model_calls': sum(len(batch.get('rounds', [])) + ('propose_retry' in batch)
                                                 for batch in batches),
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
        histories = [batch['proposal_history_supplied'] for batch in batches if 'proposal_history_supplied' in batch]
        salvaged = sum(any('complete_input_records_salvaged' in r['response_repairs']
                           for r in batch['rounds'] if r['phase'] == 'propose')
                       for batch in batches if 'proposal_history_supplied' in batch)
        retries = [batch['propose_retry'] for batch in batches if 'propose_retry' in batch]
        summary[self.name]['proposal_recovery'] = {'parse_error_tasks': len(histories),
            'salvaged_input_tasks': salvaged, 'full_history_sent_tasks': sum(histories),
            'history_not_sent_tasks': histories.count(False),
            'propose_retry_tasks': len(retries),
            'propose_retry_succeeded_tasks': sum(bool(r.get('succeeded')) for r in retries),
            'propose_retry_failed_tasks': sum(not r.get('succeeded') for r in retries),
            'base_hit_obligations_retained_tasks': sum(bool(batch.get('base_hit_obligations_retained')) for batch in batches)}
        seeds = [row for batch in batches for row in batch.get('seed_feedback', [])]
        summary[self.name]['seed_traces'] = {
            'tasks': sum('seed_feedback' in batch for batch in batches),
            'observations': sum(batch.get('seed_observation_count', 0) for batch in batches),
            'target_status': {status: sum(row['status'] == status for row in seeds)
                              for status in ('hit', 'miss', 'unknown', 'untried')}}

    def render_summary(self, summary):
        metrics = summary[self.name]
        eligible = summary['expected_tasks'] - len(summary['skips'])
        if not eligible:
            return "\nTất cả task đã chọn được ghi skip theo lý do trong summary.\n"
        arm = summary['arms'][self.name]
        recovery = metrics['proposal_recovery']
        seeds = metrics['seed_traces']
        calls = metrics['call_usage']
        return (f"\n## CF + obligation v1 sửa proposal và chia lượt trace\n\n"
                f"Phát hiện {arm['detected']}/{summary['evaluated_base_pass']} PUT ở "
                f"{arm['tasks_detected']}/{eligible} task đủ điều kiện từ {arm['valid_inputs']} input qua oracle. "
                f"Retry propose: {recovery.get('propose_retry_succeeded_tasks', 0)}/{recovery.get('propose_retry_tasks', 0)} task phục hồi sạch. "
                f"Có {recovery['parse_error_tasks']} task lỗi parse ở proposal phải fallback sang repair_construct. "
                f"Lượt construct nhận full history ở {recovery['full_history_sent_tasks']} task. "
                f"Số task thiếu history là {recovery['history_not_sent_tasks']}. "
                f"Trước construct có {seeds['observations']} lượt trace seed trên {seeds['tasks']} task có target. "
                f"Trạng thái theo target gồm {seeds['target_status']}.\n\n"
                f"Đã nhận {calls['received']} response trên {calls['invocations']} attempts, "
                f"{calls['known_usage']['total_tokens']} token có usage và {calls['unknown']} attempts chưa rõ usage. "
                f"Target hit được tính theo candidate đã trace. Oracle chấm các input trong suite cuối.\n")
