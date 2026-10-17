"""Prospectively fixed envelopes, separate code/prose tasks and raw/verified controls."""
import copy
import json
import re

from jsonschema import Draft202012Validator

from .binding import from_literal
from .common import base_inputs, strict_json, syntax_evidence, digest
from .predicates import validate_code

TEXT = {'type': 'string', 'maxLength': 2400}
NONEMPTY = dict(TEXT, minLength=1)


def obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


SCHEMAS = {
    'meta': obj({'decision': {'enum': ['proposed', 'unknown'], 'description': 'Unknown if the required behavior is undefined.'},
                 'spec_quote': dict(NONEMPTY, description='Exact original quote supporting the required behavior.'),
                 'input_domain': dict(NONEMPTY, description='Exact original quote describing allowed input values, not a programming language.'),
                 'required_relation': dict(TEXT, description='Natural-language rule linking input and returned output. No Python code.'),
                 'uncertainty': dict(TEXT, description='Explain undefined intent; required nonempty for decision unknown.')}),
    'behavior': obj({'summary': NONEMPTY, 'source_lines': {'type': 'array', 'maxItems': 12, 'items': {'type': 'integer'}},
                     'limitations': TEXT}),
    'hypothesis': obj({'verdict': {'enum': ['mismatch', 'consistent', 'unknown']},
                       'target_line': {'type': ['integer', 'null'], 'description': 'One existing executable statement for a mismatch; otherwise null.'},
                       'trigger_condition': dict(TEXT, description='Natural-language sufficient input condition; empty unless mismatch.'),
                       'explanation': dict(NONEMPTY, description='Explain actual versus required behavior, not merely whether a base example passes.')}),
}


def input_schema(task):
    public = from_literal(task, base_inputs({'base': task['base'], 'entry': task['entry']})[0])
    properties = {}
    for name in task['parameter_ids']:
        if type(public[name]) is list:
            properties[name] = {'type': 'array', 'items': {'type': 'integer'}, 'maxItems': 64}
        elif type(public[name]) is int:
            properties[name] = {'type': 'integer'}
        else:
            raise ValueError('unsupported_public_argument_type')
    return obj({'inputs': {'type': 'array', 'maxItems': 3,
                           'items': obj({'arguments': obj(properties), 'purpose': {'enum': ['trigger', 'contrast']}})},
                'reason': NONEMPTY})


def envelope(text, kind):
    """No extraction/repair: entire payload bare, or one complete matching fence."""
    if type(text) is not str or len(text.encode()) > 65536:
        raise ValueError('payload_size')
    clean = text.strip()
    if not clean.startswith('```'):
        if '```' in clean:
            raise ValueError('embedded_fence_or_extra_prose')
        return clean, 'bare'
    tag = 'python' if kind == 'code' else 'json'
    match = re.fullmatch(r'```' + tag + r'[ \t]*\r?\n([\s\S]*?)\r?\n```', clean, re.IGNORECASE)
    if not match or '```' in match.group(1):
        raise ValueError('invalid_whole_envelope')
    return match.group(1), 'single_' + tag + '_fence'


def parse(stage, raw, task):
    if stage in ('predicate', 'trigger'):
        payload, framing = envelope(raw, 'code')
        validate_code(payload, 'obligation' if stage == 'predicate' else 'trigger')
        return {'source': payload}, payload, framing
    payload, framing = envelope(raw, 'json')
    value = strict_json(payload)
    schema = input_schema(task) if stage == 'inputs' else SCHEMAS[stage]
    errors = list(Draft202012Validator(schema).iter_errors(value))
    if errors:
        raise ValueError('schema:' + errors[0].validator)
    statements = {n['span'][0] for n in task['nodes']
                  if n['is_statement'] and n['execution_scope'] == 'function_body'}
    if stage == 'meta':
        if value['spec_quote'] not in task['spec'] or value['input_domain'] not in task['spec']:
            raise ValueError('metadata_quote_provenance')
        if value['decision'] == 'unknown' and not value['uncertainty'].strip():
            raise ValueError('unknown_requires_uncertainty')
        if value['decision'] == 'proposed' and not value['required_relation'].strip():
            raise ValueError('proposed_requires_relation')
    if stage == 'behavior' and any(x not in statements for x in value['source_lines']):
        raise ValueError('behavior_source_lines')
    if stage == 'hypothesis':
        if value['verdict'] == 'mismatch':
            if value['target_line'] not in statements or not value['trigger_condition'].strip():
                raise ValueError('mismatch_target_or_condition')
        elif value['target_line'] is not None or value['trigger_condition']:
            raise ValueError('non_mismatch_has_no_trigger')
    return value, payload, framing


def messages(stage, task, **data):
    if stage in ('predicate', 'trigger'):
        system = ('Output only one complete Python function. No prose, JSON, imports or helper '
                  'functions. A single whole python fence is allowed. Follow the exact signature.')
        if stage == 'predicate':
            context = {'signature': task['signature'], 'spec': task['spec'], 'concept_metadata': data['metadata']}
            instruction = (
                'Write def obligation(arguments, observation): returning strict bool to decide '
                'whether the observed returned value satisfies the FULL original spec for these '
                'inputs. arguments is a named JSON object before execution. observation is '
                '{"status":"ok","value":...} or {"status":"exception","exception_type":...}. '
                'First reject non-ok status when normal return is required; then inspect value. '
                'Check exact JSON types: bool is not int, float is not int, including list elements. '
                'Link output to input; a nonnegative-output check alone or a predicate on inputs '
                'alone is insufficient. Preserve all output obligations such as order, occurrence '
                'counts, every/any, extras and equality boundaries stated in the spec. '
                'Do not invent a rule if intent is undefined. You see no implementation.')
        else:
            context = {'signature': task['signature'], 'hypothesis': data['hypothesis']}
            instruction = (
                'Write def trigger(arguments): returning strict bool. Encode exactly the supplied '
                'trigger_condition as a condition over named JSON inputs; do not invent another '
                'fault. This must describe a distinguishing condition, not merely a base input '
                'or generic line reach. Use only original parameters.')
        instruction += (
            ' Allowed pure names: Counter,all,any,bool,int,isinstance,len,list,max,min,set,sorted,'
            'sum,tuple,type. Counter is preloaded. No attributes (.get/.count included), lambda, '
            'imports, recursion, mutation or statement loops. Local assignments, if/return and '
            'single-generator comprehensions allowed. Use type(value) is int/bool when exact '
            'type is needed. The entire response must be this function source only.')
        return [{'role': 'system', 'content': system},
                {'role': 'user', 'content': json.dumps({'instruction': instruction, 'context': context}, ensure_ascii=False)}]
    system = ('Output one JSON object matching the given schema. No Python code or prose outside '
              'JSON. Bare JSON or one complete json fence is accepted. Do not omit required '
              'fields. Unknown specification intent must remain unknown.')
    if stage == 'meta':
        context = {'signature': task['signature'], 'spec': task['spec']}
        instruction = ('Read the original spec only. Provide decision proposed/unknown, exact '
                       'spec_quote and exact input_domain quote, required_relation in natural '
                       'language and uncertainty. input_domain describes actual allowed arguments, '
                       'not language Python. No code in any field. Undefined eligibility/suitable '
                       'means unknown; do not assume every element is suitable.')
        schema = SCHEMAS['meta']
    elif stage == 'behavior':
        context = {'code': task['source_masked'], 'syntax': syntax_evidence(task)}
        instruction = ('Describe actual returned behavior. Cite statement lines. Track whether '
                       'a local operation affects the returned expression; recognize unreachable '
                       'operations. Do not invent unsupported empty-input defects or input rules.')
        schema = SCHEMAS['behavior']
    elif stage == 'hypothesis':
        context = {'signature': task['signature'], 'spec': task['spec'], 'code': task['source_masked'],
                   'base_tests': task['base'], **data}
        instruction = ('Compare normative obligation with actual returned behavior and bounded '
                       'native/obligation evidence. Emit verdict mismatch/consistent/unknown, '
                       'one real target_line or null, trigger_condition as natural language '
                       '(empty unless mismatch), and explanation. A mismatch needs a sufficient '
                       'distinguishing input condition: the two behaviors must differ under it. '
                       'Passing base examples cannot prove consistency. Do not invent outside-domain '
                       'obligations. Unknown suitability must stay unknown. Evidence is bounded, '
                       'not a universal or causal proof.')
        schema = SCHEMAS['hypothesis']
    else:
        context = data['context']
        instruction = ('Emit up to3 named JSON argument objects using exactly the actual parameter '
                       'names in schema, with purpose trigger or contrast; provide reason. '
                       'No Python tuples, expected values, predicted values or code. Respect '
                       'the original input domain. For an observed-supported hypothesis, trigger '
                       'inputs must satisfy trigger(arguments), reach target_line and violate '
                       'obligation(arguments, observation). Contrast challenges that condition. '
                       'For consistent code provide a normal contrast with obligation=True. '
                       'For ambiguous intent abstain with inputs=[] and explain uncertainty. '
                       'Prefer new inputs outside the shown shared examples; do not silently '
                       'count shared witnesses as new detections.')
        schema = input_schema(task)
    return [{'role': 'system', 'content': system},
            {'role': 'user', 'content': json.dumps({'instruction': instruction, 'context': context,
                                                   'schema': schema}, ensure_ascii=False)}]


def raw_record(record):
    response = record.get('response') if record else None
    return {'state': record.get('state', 'missing') if record else 'missing',
            'origin': response.get('origin') if response else None,
            'raw_text': response.get('text') if response else None,
            'request_hash': record.get('request_hash') if record else None,
            'response_hash': digest(response) if response else None,
            'reason': record.get('reason') if record else 'not_requested'}


def control_contexts(task, rows, records, qualification, contract, hypothesis, support):
    common = {'signature': task['signature'], 'spec': task['spec'], 'code': task['source_masked'],
              'base_tests': task['base'], 'common_inputs_and_native_traces': rows}
    result = {arm: copy.deepcopy(common) for arm in ('verified_hyp', 'text_hyp', 'toolinput')}
    result['text_hyp']['raw_guidance'] = {name: raw_record(records.get(name))
                                          for name in ('meta', 'predicate', 'hypothesis', 'trigger')}
    result['verified_hyp'].update(qualification_state=qualification['state'],
                                  contract=contract.get('value') if qualification['state'] == 'calibrated' else None,
                                  hypothesis=hypothesis.get('value') if support['state'] == 'observed_supported' else None,
                                  hypothesis_support_state=support['state'])
    return result
