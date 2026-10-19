"""Mechanical bounded evidence; no keyword-to-fault or property-to-effect alignment."""
from .binding import bind, observation
from .common import digest
from .execution import execute
from .predicates import evaluate


def replay(task, arguments, root):
    normalized, literal = bind(task, arguments)
    return {'arguments': normalized, 'execution': execute(task, literal, root), 'input_id': digest(normalized)}


def qualify(case, contract, bank, root):
    if contract.get('state') != 'valid':
        return {'state': 'unqualified', 'reason': 'invalid_contract_artifact'}
    value = contract['value']
    if not bank:
        return {'state': 'unknown_spec', 'reason': 'authored_diagnostic_has_no_normative_oracle',
                'model_abstained': value['decision'] == 'unknown'}
    if value['decision'] != 'proposed':
        return {'state': 'unqualified', 'reason': 'model_abstained'}
    checks = evaluate(value['predicate_source'], 'obligation', bank, root)
    mismatch = [i for i, (row, result) in enumerate(zip(bank, checks))
                if result.get('state') != 'evaluated' or result.get('value') is not row['expected']]
    return {'state': 'calibrated' if not mismatch else 'unqualified', 'probes': len(bank),
            'mismatches': len(mismatch), 'failed_indices_evaluator_only': mismatch,
            'scope': 'authored finite semantic bank only; not universal semantic proof'}


def contract_results(contract, qualification, pool, root):
    if qualification['state'] != 'calibrated':
        return [{'state': 'unknown', 'reason': 'unqualified_contract'} for _ in pool]
    selected = [(i, {'arguments': row['arguments'], 'observation': observation(row['execution'])})
                for i, row in enumerate(pool) if observation(row['execution']) is not None]
    values = evaluate(contract['value']['predicate_source'], 'obligation', [x for _, x in selected], root)
    result = [{'state': 'unknown', 'reason': 'unverified_native'} for _ in pool]
    for (i, _), value in zip(selected, values):
        result[i] = value
    return result


def hypothesis_evidence(task, hypothesis, pool, checks, root):
    violated = [i for i, x in enumerate(checks) if x.get('state') == 'evaluated' and x.get('value') is False]
    result = {'state': 'unverified', 'witness_indices': [], 'counterexample_indices': [],
              'contract_violation_indices': violated, 'trigger_results': [],
              'target_reach': [], 'unknown_indices': [], 'complete_coverage': False,
              'scope': 'observed trigger+line reach+output violation, not causal/universal proof'}
    if hypothesis.get('state') != 'valid':
        result['reason'] = 'invalid_or_missing_hypothesis'
        return result
    value = hypothesis['value']
    if value['verdict'] != 'mismatch':
        result.update(state='contradicted_consistency' if value['verdict'] == 'consistent' and violated
                      else 'unverified', reason='no_model_mismatch')
        return result
    triggers = evaluate(value['trigger_source'], 'trigger', [{'arguments': x['arguments']} for x in pool], root)
    # A short/malformed worker reply cannot silently lose rows through zip().
    def boolean(value):
        return (type(value) is dict and value.get('state') == 'evaluated'
                and type(value.get('value')) is bool)
    lengths_match = len(checks) == len(pool) == len(triggers)
    triggers = [triggers[i] if i < len(triggers) else {'state': 'unknown', 'reason': 'missing_trigger'}
                for i in range(len(pool))]
    checks = [checks[i] if i < len(checks) else {'state': 'unknown', 'reason': 'missing_check'}
              for i in range(len(pool))]
    result['trigger_results'] = triggers
    result['target_reach'] = [any(x['event'] == 'line' and x['line'] == value['target_line']
                                 and x['function'] == task['entry'] for x in row['execution']['events'])
                              if row['execution']['native_checked'] else None for row in pool]
    unknown = not lengths_match or not pool
    for i, (row, check, trigger) in enumerate(zip(pool, checks, triggers)):
        if (not boolean(trigger) or not boolean(check) or not row['execution']['native_checked']
                or observation(row['execution']) is None):
            unknown = True
            result['unknown_indices'].append(i)
            continue
        if not trigger['value']:
            continue
        reached = any(x['event'] == 'line' and x['line'] == value['target_line']
                      and x['function'] == task['entry'] for x in row['execution']['events'])
        if not row['execution']['native_checked']:
            unknown = True
        elif check['value'] is True or (not reached and row['execution']['omitted_events'] == 0):
            result['counterexample_indices'].append(i)
        elif reached:
            result['witness_indices'].append(i)
        else:
            unknown = True
            result['unknown_indices'].append(i)
    result['complete_coverage'] = not unknown
    if result['counterexample_indices']:
        result['state'] = 'contradicted_trigger'
    elif result['witness_indices'] and not unknown:
        result['state'] = 'observed_supported'
    elif unknown:
        result['reason'] = 'unknown_predicate_trigger_or_trace'
    else:
        result['reason'] = 'no_triggered_violation_in_finite_pool'
    return result


def cumulative_support(task, hypothesis, pool, checks, replays, new_checks, root, artifact_valid=True):
    """Keep the full original prefix and a durable ledger of EVERY proposal slot."""
    combined, combined_checks = list(pool), list(checks)
    ledger, failures = [], []
    for row in replays:
        entry = {'proposal_slot': row['slot'], 'state': row['state'], 'cumulative_index': None}
        if row['state'] == 'observed':
            index = len(combined)
            entry['cumulative_index'] = index
            combined.append(row)
            k = sum(x['cumulative_index'] is not None for x in ledger)
            combined_checks.append(new_checks[k] if k < len(new_checks)
                                   else {'state': 'unknown', 'reason': 'missing_generated_check'})
        else:
            failures.append(row['slot'])
        ledger.append(entry)
    support = hypothesis_evidence(task, hypothesis, combined, combined_checks, root)
    expected = sum(x['state'] == 'observed' for x in replays)
    failed_coverage = bool(failures) or not artifact_valid or len(new_checks) != expected or len(checks) != len(pool)
    if failed_coverage:
        support['complete_coverage'] = False
        if support['state'] != 'contradicted_trigger':
            support.update(state='unverified', reason='incomplete_proposal_or_evaluator_coverage')
    accepted = [x['proposal_slot'] for x in ledger if support['state'] == 'observed_supported'
                and x['cumulative_index'] in support['witness_indices']]
    shared_ids = {row['input_id'] for row in pool}
    novel = [row['slot'] for row in replays if row['slot'] in accepted and row['input_id'] not in shared_ids]
    return {'support': support, 'proposal_ledger': ledger, 'failed_proposal_slots': failures,
            'proposal_artifact_valid': artifact_valid, 'accepted_slots': accepted,
            'novel_accepted_slots': novel, 'original_rows': len(pool),
            'cumulative_rows': len(combined)}


def shared_selection(pool, checks, support):
    supported = set(support['witness_indices']) if support['state'] == 'observed_supported' else set()
    violated = {i for i, x in enumerate(checks) if x.get('state') == 'evaluated' and x.get('value') is False}
    indices = sorted(range(len(pool)), key=lambda i: (0 if i in supported else 1 if i in violated else 2, i))[:6]
    return {'indices': indices, 'rows': [pool[i] for i in indices],
            'selector': 'supported witness, calibrated-contract violation, frozen original order; no independent oracle score'}


def feedback_for(pool, checks, support):
    # Used only during shared preparation; all rows are bounded fixed pool evidence.
    return [{'index': i, 'arguments': row['arguments'], 'observation': observation(row['execution']),
             'obligation': checks[i],
             'trigger': support['trigger_results'][i] if support['trigger_results'] else None,
             'native_checked': row['execution']['native_checked'],
             'omitted_trace_events': row['execution']['omitted_events'],
             'target_reached': support['target_reach'][i] if support['target_reach'] else None,
             'is_counterexample': i in support['counterexample_indices']}
            for i, row in enumerate(pool)]


def replay_inputs(task, proposal, root):
    result = []
    for slot, candidate in enumerate(proposal['inputs']):
        row = {'slot': slot, 'proposal': candidate}
        try:
            data = replay(task, candidate['arguments'], root)
            row.update(state='observed' if observation(data['execution']) is not None else 'unknown', **data)
        except (ValueError, TypeError, OverflowError) as exc:
            row.update(state='invalid', reason=type(exc).__name__ + ':' + str(exc))
        result.append(row)
    return result
