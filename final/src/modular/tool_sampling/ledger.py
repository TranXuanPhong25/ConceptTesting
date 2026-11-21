"""Keep every emission and all same-stage errors; never evaluate generated code."""
import ast
import hashlib
import json
import math

from ..call_builder import input_identity, supported_value
from .membership import evaluate, expression

STAGES = ('P1', 'P2', 'P3', 'P4', 'P5', 'V1', 'V2', 'V3')


def identity(value):
    return hashlib.sha256(repr(value).encode('utf-8', errors='backslashreplace')).hexdigest()


def error(stage, code, detail):
    return {'stage': stage, 'code': code, 'detail': str(detail)}


def check_value(value, expected=None, path='arguments', depth=0):
    errors = []
    if depth > 8 or (type(value) in (tuple, list, set, dict) and len(value) > 1000):
        return [error('P3', 'non_json_literal', path + ':resource_limit')]
    if type(value) is float and not math.isfinite(value):
        errors.append(error('P3', 'nan_inf', path))
    if type(value) is str:
        try:
            value.encode('utf-8')
        except UnicodeError:
            errors.append(error('P3', 'string_encoding', path))
    if expected and expected != 'any':
        kinds = {'int': int, 'bool': bool, 'float': float, 'str': str, 'list': list}
        kind = list if expected.startswith('list[') else kinds[expected]
        if type(value) is not kind:
            code = 'bool_int_confusion' if kind is int and type(value) is bool else 'type_mismatch'
            errors.append(error('P3', code, path + ':' + expected))
    if type(value) not in (tuple, list, set, dict) and not supported_value(value):
        if not (type(value) is float and not math.isfinite(value)):
            errors.append(error('P3', 'non_json_literal', path))
    if type(value) in (tuple, list, set):
        for index, item in enumerate(value):
            inner_type = expected[5:-1] if expected and expected.startswith('list[') and type(value) is list else None
            errors.extend(check_value(item, inner_type, path=f'{path}[{index}]', depth=depth + 1))
    elif type(value) is dict:
        for key, item in value.items():
            errors.extend(check_value(item, path=f'{path}.{key}', depth=depth + 1))
    return errors


def predicate_status(text, arguments):
    try:
        expression(text, arguments)
    except (ValueError, SyntaxError) as exc:
        return 'unknown', type(exc).__name__ + ':' + str(exc)
    try:
        return ('true' if evaluate(text, arguments) else 'false'), None
    except Exception as exc:
        return 'error', type(exc).__name__ + ':' + str(exc)


class CandidateLedger:
    def __init__(self, task_id, arm, builder, model):
        self.task_id, self.arm, self.builder, self.model = task_id, arm, builder, model
        self.rows, self.groups = [], {}

    def add(self, raw, source, *, errors=(), tool_raw=None):
        row = {'candidate_id': identity((self.task_id, self.arm, repr(raw), source)),
               'task_id': self.task_id, 'arm': self.arm, 'sources': [source],
               'raw': repr(raw if tool_raw is None else tool_raw), 'canonical_args': None, 'errors': list(errors),
               'primary_error': None, 'membership': None, 'dedup_group': None,
               'selected': False, 'selection_reason': None}
        self.rows.append(row)
        if not row['errors']:
            self.parse(row, raw)
        if row['errors']:
            row['primary_error'] = min(row['errors'], key=lambda item: STAGES.index(item['stage']))
            stage = row['primary_error']['stage']
            row['selection_reason'] = 'parse_error' if stage.startswith('P') else 'invalid' if stage == 'V1' else 'membership_unknown'
        if row['canonical_args'] is not None:
            group = row['dedup_group']
            if group in self.groups:
                representative = self.groups[group]
                for item in row['sources']:
                    if item not in representative['sources']:
                        representative['sources'].append(item)
                row['selection_reason'] = 'duplicate'
            else:
                self.groups[group] = row
        return row

    def parse(self, row, raw):
        errors = row['errors']
        if not isinstance(raw, dict):
            errors.append(error('P2', 'wrong_record_type', type(raw).__name__))
            return
        named = 'arguments' in raw
        allowed = {'arguments', 'guidance_id', 'covers'} if named else {'args', 'kwargs', 'guidance_id', 'covers'}
        required = {'arguments'} if named else {'args'}
        for field in sorted(required - set(raw)):
            errors.append(error('P2', 'missing_field', field))
        for field in sorted(set(raw) - allowed):
            errors.append(error('P2', 'unexpected_field', field))
        if errors:
            return
        if named:
            if not isinstance(raw['arguments'], dict):
                errors.append(error('P3', 'type_mismatch', 'arguments must be object'))
                return
            arguments = {}
            for key, value in raw['arguments'].items():
                try:
                    # Decode each field independently so one bad type tag does
                    # not hide other errors in the same value-decoding stage.
                    arguments[key] = self.builder.decode_arguments({key: value})[key] if key in self.builder.signature.parameters else value
                    errors.extend(check_value(arguments[key], self.model.get('admission_types', self.model['types']).get(key), key))
                except (TypeError, ValueError) as exc:
                    errors.append(error('P3', 'non_json_literal', str(key) + ':' + str(exc)))
        else:
            values = {}
            for key, default in (('args', None), ('kwargs', '{}')):
                try:
                    text = raw.get(key, default)
                    if not isinstance(text, str) or len(text) > 16000:
                        raise ValueError('bounded_literal_required')
                    values[key] = ast.literal_eval(text)
                    errors.extend(check_value(values[key]))
                except (ValueError, SyntaxError, TypeError) as exc:
                    errors.append(error('P3', 'non_json_literal', f'{key}:{exc}'))
            if errors:
                return
            if not isinstance(values['args'], (tuple, list)) or not isinstance(values['kwargs'], dict):
                errors.append(error('P3', 'type_mismatch', 'args/kwargs'))
                return
            arguments = None
        if errors:
            return
        try:
            if named:
                unknown = set(arguments) - set(self.builder.signature.parameters)
                if unknown:
                    errors.append(error('P5', 'unknown_kwarg', sorted(unknown)))
                    return
                call = self.builder.build_values(arguments)
                bound = self.builder.signature.bind(*ast.literal_eval(call['args']), **ast.literal_eval(call['kwargs']))
            else:
                unknown = set(values['kwargs']) - set(self.builder.signature.parameters)
                if unknown:
                    errors.append(error('P5', 'unknown_kwarg', sorted(unknown)))
                    return
                bound = self.builder.signature.bind(*values['args'], **values['kwargs'])
            bound.apply_defaults()
            arguments = dict(bound.arguments)
        except (TypeError, ValueError) as exc:
            code = 'type_mismatch' if str(exc).startswith('argument_type_mismatch:') else 'arity_mismatch'
            errors.append(error('P5', code, exc))
            return
        for key, value in arguments.items():
            errors.extend(check_value(value, self.model.get('admission_types', self.model['types']).get(key), key))
        if errors:
            return
        try:
            call = self.builder.build_values(arguments)
        except (TypeError, ValueError) as exc:
            errors.append(error('P5', 'call_builder_error', exc))
            return
        row['canonical_args'] = call
        row['bound_values'] = {name: repr(value) for name, value in arguments.items()}
        row['dedup_group'] = identity(input_identity(self.builder.signature, call))
        domain, detail = predicate_status(self.model['domain'], arguments)
        row['domain'] = domain
        if domain == 'false':
            errors.append(error('V1', 'domain_rejects', self.model['domain']))
            return
        if domain != 'true':
            errors.append(error('V1', 'membership_unknown' if domain == 'unknown' else 'membership_error', detail))
            return
        row['membership'] = {}
        for target in self.model['targets']:
            context, context_error = predicate_status(target.get('context', 'True'), arguments)
            membership, target_error = predicate_status(target.get('predicate'), arguments)
            row['membership'][target['id']] = {'domain': domain, 'context': context, 'target': membership,
                                               'hit': context == membership == 'true'}
            for status, detail in ((context, context_error), (membership, target_error)):
                if status in {'unknown', 'error'}:
                    errors.append(error('V2', 'membership_' + status, target['id'] + ':' + detail))

    def pool(self):
        return [row for row in self.groups.values() if row.get('domain') == 'true'
                and not row.get('solver_rejected')
                and not any(item['stage'].startswith('P') or item['stage'] == 'V1' for item in row['errors'])]

    def selected_rows(self):
        return [row for row in self.pool() if row['selected']]
