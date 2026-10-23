"""Per-item admission is transport bookkeeping, never normative validation."""
import copy
from collections import Counter
from jsonschema import Draft202012Validator

from .flow_common import strict_json
from . import identify_tools as relations

CAP = 3
CONCEPTS = relations.CONCEPTS + ['unknown']
JUDGMENTS = ['observed_mismatch', 'no_observed_mismatch', 'unknown']


def binding_schema():
    return {'type': 'object', 'additionalProperties': False,
            'required': ['id', 'concept', 'relation', 'arguments', 'spec_quote', 'spec_status'],
            'properties': {
                'id': {'type': 'string', 'minLength': 1, 'maxLength': 16},
                'concept': {'enum': CONCEPTS}, 'relation': {'enum': list(relations.RELATIONS)},
                'arguments': {'type': 'array', 'maxItems': 2, 'items': {'type': 'string', 'maxLength': 30}},
                'spec_quote': {'type': 'string', 'maxLength': 300},
                'spec_status': {'enum': ['justified', 'unknown', 'rejected']}}}


def schema(final=False):
    properties = {'bindings': {'type': 'array', 'maxItems': CAP, 'items': binding_schema()}}
    if final:
        properties.update(implementation_judgment={'enum': JUDGMENTS},
                          reason={'type': 'string', 'maxLength': 2000},
                          evidence={'type': 'array', 'uniqueItems': True, 'items': {'type': 'string'}})
    return {'type': 'object', 'additionalProperties': False,
            'required': list(properties), 'properties': properties}


def errors(value, rule):
    return [{'path': list(e.absolute_path), 'rule': e.validator}
            for e in Draft202012Validator(rule).iter_errors(value)]


def unavailable(reason):
    """Slot with no reply (never sent); same shape as an unparseable reply."""
    return {'parseable': False, 'envelope_valid': False, 'envelope_errors': [], 'items': [],
            'accepted': [], 'initial_unavailable': True, 'parse_error': reason}


def admit(response, final=False, evidence_ids=()):
    """Preserve every item; never coerce arguments, quotes, concepts or JSON fields."""
    result = {'parseable': False, 'envelope_valid': False, 'envelope_errors': [],
              'items': [], 'accepted': [], 'initial_unavailable': True}
    if response.get('finish_reason') != 'stop':
        result['parse_error'] = 'incomplete_response'
        return result
    try:
        text = response['text'].strip()
        if text.startswith('```json\n') and text.endswith('\n```') and text.count('```') == 2:
            text = text[8:-4]
        value = strict_json(text)
    except (ValueError, KeyError, TypeError, AttributeError):
        result['parse_error'] = 'invalid_JSON'
        return result
    result.update(parseable=True, parsed=value)
    envelope = schema(final)
    envelope['properties']['bindings'] = {'type': 'array', 'maxItems': CAP}
    result['envelope_errors'] = errors(value, envelope)
    result['envelope_valid'] = not result['envelope_errors']
    if type(value) is not dict or type(value.get('bindings')) is not list:
        return result
    result['initial_unavailable'] = False
    items = value['bindings']
    ids = Counter(x.get('id') for x in items if type(x) is dict and type(x.get('id')) is str)
    for i, item in enumerate(items):
        issues = errors(item, binding_schema())
        if i >= CAP:
            issues.append({'path': [], 'rule': 'item_budget_exceeded'})
        if type(item) is dict and type(item.get('id')) is str and ids[item['id']] > 1:
            issues.append({'path': ['id'], 'rule': 'duplicate_id'})
        result['items'].append({'index': i, 'raw': copy.deepcopy(item), 'errors': issues, 'admitted': not issues})
        if not issues:
            result['accepted'].append(copy.deepcopy(item))
    if final:
        refs = value.get('evidence')
        result['unknown_evidence_ids'] = [x for x in refs if type(x) is str and x not in evidence_ids] if type(refs) is list else []
        result['judgment_valid'] = value.get('implementation_judgment') in JUDGMENTS
        result['evidence_valid'] = (not errors(refs, schema(True)['properties']['evidence'])
                                    and not result['unknown_evidence_ids'])
    return result


def checks(items, row):
    result = {b['id']: relations.binding_checks(b, row['parameters'], row['spec']) for b in items}
    for b in items:
        if b['concept'] == 'unknown':
            result[b['id']]['concept_relation_vocabulary_compatible'] = None
            result[b['id']]['concept_label_status'] = 'unknown, not a vocabulary contradiction'
    return result


def compare_feedback(items, row):
    table = []
    for observation in row['rows']:
        for b in items:
            computed = relations.compare(b, observation, row['parameters'])
            table.append([observation['id'], b['id'], computed['status'], computed.get('candidate_value'),
                          computed.get('candidate_exception'), computed.get('holds_on_observation'), computed.get('reason')])
    return {'scope': 'Candidate relation vs observed execution ONLY; spec entailment unverified.',
            'columns': ['observation', 'binding', 'status', 'candidate_value', 'candidate_exception', 'holds', 'reason'],
            'rows': table}


def vocabulary():
    return {'concepts': CONCEPTS, 'relations': relations.RELATIONS,
            'relation_concepts': dict(relations.RELATION_CONCEPTS, unknown=CONCEPTS),
            'argument_convention': 'List only input parameter names, in operator order. Output is implicit, never an argument.',
            'unknown_convention': 'concept=unknown and/or relation=unknown are legal; use spec_status=unknown when unjustified.'}


def initial_packet(row):
    return dict(instruction='Propose up to3 fallible bindings of requirements stated in SPEC. Quote the supporting spec. '
                'Distinguish a requirement from what the implementation currently does. Do not invent undefined rules.',
                spec=row['spec'], code=row['code'], parameters=row['parameters'], vocabulary=vocabulary(), reply_schema=schema())


def final_packet(row, initial, feedback, arm):
    if arm not in ('raw', 'tool'):
        raise ValueError('unknown_arm')
    admission = initial['admission']
    return dict(instruction='Reconsider the requirements using SPEC and evidence. Return FULL final bindings: you may add '
                'new IDs, replace operators or arguments, retain or reject candidates, or leave bindings empty. '
                'A relation violated by code may still be the correct REQUIREMENT. Code agreement cannot define missing spec rules. '
                'Judge observed mismatch separately. Unknown is allowed. Cite only supplied evidence IDs.',
                spec=row['spec'], code=row['code'], parameters=row['parameters'], vocabulary=vocabulary(),
                initial_response=initial['raw']['text'] if initial['raw'] else None, initial_admission={
                    k: admission[k] for k in ('parseable', 'envelope_valid', 'envelope_errors', 'initial_unavailable')},
                item_admission=[{k: item[k] for k in ('index', 'errors', 'admitted')} for item in admission['items']],
                candidate_checks=checks(admission['accepted'], row), observations=row['rows'],
                evidence_ids=['original_spec', 'source_return'] + [o['id'] for o in row['rows']],
                tool_feedback=feedback if arm == 'tool' else None, reply_schema=schema(True))


def transitions(initial_items, final_items):
    """Syntactic provenance only. A reviewer determines semantic correction/retention."""
    before = {x['id']: x for x in initial_items}
    after = {x['id']: x for x in final_items}
    return {'added': sorted(after.keys() - before.keys()), 'removed': sorted(before.keys() - after.keys()),
            'changed': sorted(k for k in before.keys() & after.keys() if before[k] != after[k]),
            'unchanged': sorted(k for k in before.keys() & after.keys() if before[k] == after[k]),
            'scope': 'ID/content transitions only, no semantic correctness inference'}
