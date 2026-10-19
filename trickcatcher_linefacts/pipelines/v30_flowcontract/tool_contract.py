"""One action contract for prompt disclosure and charged dispatch, not whole-reply rejection."""
import copy
import json
import math
from jsonschema import Draft202012Validator, validators
from .paths import CONFIG

F = CONFIG['flowtools']
ID = {'anyOf': [{'type': 'string'}, {'type': 'integer'}]}
FIELDS = {'tool', 'ids', 'radius', 'names', 'input', 'trace', 'sequence', 'hypothesis'}


def ids(*, required=False):
    return dict(type='array' if required else ['array', 'null'], items=copy.deepcopy(ID),
                minItems=1 if required else 0, maxItems=F['max_names'])


def action_schemas():
    common = {'hypothesis': {'type': ['string', 'null']}}
    names = dict(type=['array', 'null'], maxItems=F['max_names'], items=dict(type='string', maxLength=64))
    specs = {
        'inspect_flow': (dict(ids=ids(required=True), radius=dict(type='integer', minimum=0, maximum=3, default=1)), ['ids']),
        'inspect_data': (dict(ids=ids(), names=names), []),
        'replay_input': (dict(input=dict(type='string', maxLength=CONFIG['chain']['max_input_chars']), ids=ids(), names=names), ['input']),
        'check_path': (dict(trace=dict(type='string'), sequence=dict(type='array', minItems=1, maxItems=64, items=ID)), ['trace', 'sequence']),
    }
    out = {}
    for tool, (props, required) in specs.items():
        out[tool] = dict(type='object', properties=dict(common, tool={'const': tool}, **props),
                         required=['tool'] + required, additionalProperties=False)
    out['inspect_data']['anyOf'] = [
        dict(required=[field], properties={field: dict(type='array', minItems=1)}) for field in ('ids', 'names')]
    return copy.deepcopy(out)


# JSON Schema permits integral float values for integer; v21's radius/IDs use exact int, not bool/float.
ExactValidator = validators.extend(Draft202012Validator, type_checker=Draft202012Validator.TYPE_CHECKER.redefine(
    'integer', lambda checker, value: type(value) is int))
SCHEMAS = action_schemas()
VALIDATORS = {k: ExactValidator(v) for k, v in SCHEMAS.items()}


class ActionError(ValueError):
    def __init__(self, validator, path='', limit=None):
        super().__init__('action_schema:' + validator)
        self.details = dict(code='action_schema:' + validator, field=path, constraint=validator)
        if limit is not None:
            self.details['limit'] = limit


def validate(action):
    """Call only after an action slot and legacy replay reservation have been charged."""
    tool = action['tool']
    errors = sorted(VALIDATORS[tool].iter_errors(action), key=lambda e: (list(map(str, e.path)), e.validator))
    if not errors:
        return
    err = errors[0]
    path = ''.join('/' + (str(p) if type(p) is int else p if p in FIELDS else 'unknown_field') for p in err.path)
    if err.validator == 'required':
        missing = [p for p in err.validator_value if p not in err.instance]
        path += '/' + missing[0] if missing else ''
    limit = err.validator_value if err.validator in ('maxItems', 'maxLength', 'minimum', 'maximum', 'minItems') else None
    raise ActionError(err.validator, path, limit)


def protocol():
    contract = dict(actions_per_round=F['actions_per_round'], rounds=F['rounds'], max_actions=F['max_actions'],
                    max_action_chars=F['max_action_chars'], input_UTF8_bytes=CONFIG['chain']['max_input_chars'],
                    input_format='Python literal full positional argument tuple, e.g. (value,) for one parameter; no expressions/calls',
                    literal_limits={k: CONFIG['chain'][k] for k in (
                        'max_input_chars', 'max_input_nodes', 'max_input_depth', 'max_items')},
                    scalar_characters=CONFIG['chain']['max_input_chars'], integer_bits=4096,
                    string_limits='JSON Schema maxLength counts characters; runtime additionally limits input UTF8 bytes',
                    action_object_depth=CONFIG['chain']['max_input_depth'],
                    ID_types='string alias/full ID or exact integer line number; booleans and floats invalid',
                    radius='exact integer 0..3, default1; defaults never rewrite your submitted action',
                    tools=action_schemas())
    return ('Send each action as one JSON object. Invalid actions consume a slot and return error_details with field/limit; '
            'valid sibling actions still execute. Correct an error with a new action inside the remaining budget. '
            'Do not silently truncate IDs or assume a structural fact proves the spec. Observed outputs are not expected '
            'oracles. Optional hypothesis links use a string ID; no shell/evaluator is available. Contract: '
            + json.dumps(contract, sort_keys=True, ensure_ascii=False))


def error_details(error, action, number, round_number, schema=None):
    """Only static field names/codes and bounded linkage; no arbitrary malformed payload in feedback."""
    details = dict(schema or {}, action=number, round=round_number)
    if 'code' not in details:
        details['code'] = error.split(':', 1)[0][:64]
    details.setdefault('field', '')
    generic = {
        'action_too_long': ('', F['max_action_chars']),
        'unknown_field': ('/unknown_field', None), 'hypothesis_shape': ('/hypothesis', None),
        'unknown_tool': ('/tool', None),
        'execution_budget_exhausted': ('', F['max_execution_requests']),
    }
    if error in generic:
        field, limit = generic[error]
        details['field'] = field
        if limit is not None:
            details['limit'] = limit
    if error.startswith('input:'):
        details['field'] = '/input'
        reason = error.split(':', 1)[1]
        bounds = {
            'literal_text_size': dict(UTF8_bytes=CONFIG['chain']['max_input_chars']),
            'literal_size_depth': dict(nodes=CONFIG['chain']['max_input_nodes'], depth=CONFIG['chain']['max_input_depth']),
            'container_size': dict(items=CONFIG['chain']['max_items']),
            'scalar_size': dict(characters=CONFIG['chain']['max_input_chars']),
            'integer_size': dict(bits=4096),
        }
        if reason in bounds:
            details['limit'] = bounds[reason]
    if details['code'] == 'unknown_trace':
        details['field'] = '/trace'
    elif details['code'] in ('unknown_id', 'id_shape', 'not_a_cfg_statement'):
        details['field'] = '/sequence' if action.get('tool') == 'check_path' else '/ids'
    if isinstance(action.get('hypothesis'), str) and len(action['hypothesis']) <= 64:
        details['hypothesis'] = action['hypothesis']
    return details


def logged_action(action):
    """JSON host values only; unrepresentable host inputs get a static rejection marker, never repr/evaluation."""
    pending, visited, count = [(action, 0)], set(), 0
    while pending:
        value, depth = pending.pop()
        count += 1
        if count > F['max_action_chars']:
            return '!unrepresentable_action:node_budget'
        if depth > CONFIG['chain']['max_input_depth']:
            return '!unrepresentable_action:depth_budget'
        if type(value) in (dict, list):
            if id(value) in visited:
                return '!unrepresentable_action:container_alias'
            visited.add(id(value))
            if type(value) is dict:
                if any(type(k) is not str for k in value):
                    return '!unrepresentable_action:JSON_key'
                pending.extend((v, depth + 1) for v in value.values())
            else:
                pending.extend((v, depth + 1) for v in value)
        elif type(value) not in (str, int, float, bool, type(None)):
            return '!unrepresentable_action:JSON_type'
        elif type(value) is float and not math.isfinite(value):
            return '!unrepresentable_action:nonfinite'
    try:
        json.dumps(action, allow_nan=False)
    except (ValueError, TypeError, RecursionError, OverflowError):
        return '!unrepresentable_action:serialization'
    return action


def project_history(history, max_chars=12000):
    """Legacy first-three projection plus a bounded digest retaining every error, including omitted slots."""
    if len(json.dumps(history, ensure_ascii=False)) <= max_chars:
        return copy.deepcopy(history)
    out = []
    for h in history:
        errors = copy.deepcopy(h.get('error_digest', []))
        for slot, result in enumerate(h['feedback'], 1):
            if result.get('status') not in ('error', 'refused'):
                continue
            detail = result.get('error_details') or dict(code=result.get('error', 'tool_error').split(':')[0][:64])
            row = dict(detail, slot=slot)
            row.setdefault('round', h['round'])
            if row not in errors:
                errors.append(row)
        out.append(dict(round=h['round'], feedback=copy.deepcopy(h['feedback'][:3]),
                        omitted=h.get('omitted', 0) + max(0, len(h['feedback']) - 3), error_digest=errors))
    return out
