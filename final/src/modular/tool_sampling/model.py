"""Validate executable preparation while preserving unsupported target evidence."""
import copy
import json

from .membership import expression


def validate_model(value, builder):
    if not isinstance(value, dict):
        raise ValueError('preparation_must_be_object')
    result = copy.deepcopy(value)
    required = {'types', 'domain', 'domain_source_quote', 'strategies', 'targets', 'inputs', 'factors'}
    if set(result) != required:
        raise ValueError('preparation_fields:' + ','.join(sorted(required)))
    try:
        # Seed inputs are decoded independently in the candidate ledger, where
        # invalid encodings/literals must remain auditable rather than crash I/O.
        json.dumps({key: item for key, item in result.items() if key != 'inputs'},
                   ensure_ascii=False, allow_nan=False).encode('utf-8')
    except (ValueError, TypeError) as exc:
        raise ValueError('preparation_metadata_must_be_JSON:' + str(exc)) from None
    if not isinstance(result['types'], dict) or set(result['types']) != set(builder.signature.parameters):
        raise ValueError('complete_parameter_types_required')
    if any(not isinstance(tag, str) or tag not in {'int', 'bool', 'float', 'str', 'list', 'list[int]', 'list[float]', 'list[str]', 'any'}
           for tag in result['types'].values()):
        raise ValueError('unsupported_parameter_type')
    if not isinstance(result['domain_source_quote'], str) or not result['domain_source_quote'].strip():
        raise ValueError('domain_source_quote_required')
    if not isinstance(result['domain'], str):
        raise ValueError('domain_must_be_expression')
    # Unsupported domain means unknown membership, never an unconstrained replacement.
    try:
        expression(result['domain'], result['types'])
        result['domain_support'] = 'supported'
    except (ValueError, SyntaxError) as error:
        result['domain_support'] = 'unsupported'
        result['domain_error'] = str(error)
    if not isinstance(result['strategies'], dict) or set(result['strategies']) != set(result['types']):
        raise ValueError('complete_strategies_required')
    if not isinstance(result['inputs'], list) or len(result['inputs']) > 1000:
        raise ValueError('invalid_seed_inputs')
    if not isinstance(result['targets'], list) or len(result['targets']) > 128:
        raise ValueError('invalid_targets')
    seen = set()
    for target in result['targets']:
        if (not isinstance(target, dict) or not isinstance(target.get('id'), str)
                or not target['id'] or target['id'] in seen):
            raise ValueError('invalid_or_duplicate_target_id')
        seen.add(target['id'])
        if (not isinstance(target.get('origin'), str) or target.get('origin') not in {'spec', 'contract', 'impl'}
                or not isinstance(target.get('source_quote'), str) or not target['source_quote'].strip()):
            raise ValueError('target_source_info_required')
        if not isinstance(target.get('kind'), str) or target.get('kind') not in {'class', 'boundary', 'rule'}:
            raise ValueError('invalid_target_kind')
        if not isinstance(target.get('status', 'unresolved'), str) or target.get('status', 'unresolved') not in {'feasible', 'infeasible', 'unresolved'}:
            raise ValueError('invalid_feasibility_status')
        if target.get('status') == 'infeasible' and not target.get('reason'):
            raise ValueError('infeasible_requires_reason')
        for field in ('boundary_side', 'fault_rationale'):
            if field in target and target[field] is not None and not isinstance(target[field], str):
                raise ValueError(field + '_must_be_string')
        for field in ('actions', 'merged_from'):
            if field in target and (not isinstance(target[field], list)
                                    or any(not isinstance(item, str) for item in target[field])):
                raise ValueError(field + '_must_be_string_list')
        target.setdefault('context', 'True')
        target.setdefault('predicate', '')
        target['support'] = 'supported'
        try:
            for key in ('context', 'predicate'):
                expression(target.get(key), result['types'])
        except (ValueError, SyntaxError) as error:
            target['support'], target['support_error'] = 'unsupported', str(error)
    if not isinstance(result['factors'], dict) or len(result['factors']) > 16:
        raise ValueError('invalid_factors')
    for levels in result['factors'].values():
        if not isinstance(levels, dict) or not 1 <= len(levels) <= 16:
            raise ValueError('invalid_factor_levels')
        for predicate in levels.values():
            expression(predicate, result['types'])
    return result
