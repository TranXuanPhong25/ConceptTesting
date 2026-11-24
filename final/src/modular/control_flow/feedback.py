"""Keep prompt evidence bound to the source and objectives actually supplied."""
from .analysis import target_feedback


def target_diagnostics(targets, observations, expected_opcodes=None, *, unobserved_reason='no_native_observation'):
    rows = []
    for target in targets:
        measured = [row for row in observations if row['program_id'] == target['program_id']]
        if not measured:
            rows.append({'target_id': target['id'], 'program_id': target['program_id'],
                         'status': 'unknown', 'reason': unobserved_reason})
            continue

        def priority(row):
            feedback = target_feedback(target, row)
            return (feedback['target_hit'], row.get('domain') == 'valid',
                    row.get('status') == 'executed',
                    sum(step['arc'] in row.get('coverage',{}).get('arcs',[]) for step in target.get('path',[])))

        observation = max(measured, key=priority)
        expected = (expected_opcodes or {}).get(target['id'])
        rows.append({**target_feedback(target, observation, expected), 'program_id': target['program_id'],
                     'call': observation['call'], 'domain': observation.get('domain'),
                     'runtime_status': observation.get('status'), 'observations': len(measured)})
    return rows


def scoped_feedback(feedback, targets, program_ids, obligations=()):
    if feedback is None:
        return None
    result = dict(feedback)
    allowed = {target['id'] for target in targets}
    for field in ('remaining_target_ids', 'unpresented_target_ids'):
        if field in result:
            result[field] = [identifier for identifier in result[field] if identifier in allowed]
    for field in ('concepts', 'target_diagnostics', 'concept_checks', 'construction_results', 'feasibility_claims'):
        if field in result:
            result[field] = [row for row in result[field] if row['target_id'] in allowed]
    if 'solver_budget_remaining' in result:
        result['solver_budget_remaining'] = {k: v for k, v in result['solver_budget_remaining'].items() if k in allowed}
    if 'supplied_program_ids' in result:
        result['supplied_program_ids'] = [owner for owner in result['supplied_program_ids'] if owner in program_ids]
    obligation_ids = {row['id'] for row in obligations}
    if 'scenario_membership' in result:
        result['scenario_membership'] = [row for row in result['scenario_membership'] if row['id'] in obligation_ids]
    if 'sampling' in result:
        labels = {row['id'] for row in result.get('concepts', [])} | obligation_ids
        result['sampling'] = [row for row in result['sampling'] if row.get('concept_id', row.get('obligation_id')) in labels]
    if 'candidates' in result:
        result['candidates'] = [{**row, 'hit_targets': [identifier for identifier in row.get('hit_targets', []) if identifier in allowed]}
                                for row in result['candidates'] if row['program_id'] in program_ids]
    return result
