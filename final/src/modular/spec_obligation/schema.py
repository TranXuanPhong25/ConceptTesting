"""Tolerant metadata parsing; only complete literal inputs can be recovered."""
import ast
import json
import re

from pydantic import BaseModel, ConfigDict, Field, StrictInt, ValidationError

from ..response_json import load_response_json
from ..call_builder import decode_value, supported_value
from ..tool_sampling.membership import expression


class Obligation(BaseModel):
    model_config = ConfigDict(extra='ignore')
    program_id: StrictInt | str
    line: StrictInt
    requirement: str = Field(min_length=1, max_length=1000)
    pattern: str = Field(min_length=1, max_length=500)
    scenario: str = Field(min_length=1, max_length=1200)
    instruction: str = Field(min_length=1, max_length=1200)
    counterexample: str = Field(min_length=1, max_length=1000)
    predicate: str = Field(default='', max_length=2048)
    strategies: dict = Field(default_factory=dict)
    source_sha256: str | None = None


def read_response(text):
    if not isinstance(text, str) or len(text) > 160000:
        raise ValueError('response_size_limit')
    try:
        raw, repairs = load_response_json(text)
        if not isinstance(raw, dict):
            raise ValueError('response_object_required')
        return raw, repairs
    except (ValueError, SyntaxError, TypeError, RecursionError):
        # Keep complete records preceding a truncated tail; never synthesize closing values.
        match = re.search(r'"inputs"\s*:\s*\[', text)
        if match is None:
            raise ValueError('no_complete_input_records') from None
        decoder, inputs, position = json.JSONDecoder(), [], match.end()
        for _ in range(128):
            while position < len(text) and text[position] in ' \t\r\n,':
                position += 1
            try:
                record, position = decoder.raw_decode(text, position)
            except (ValueError, RecursionError):
                break
            if not isinstance(record, dict):
                break
            inputs.append(record)
        if not inputs:
            raise ValueError('no_complete_input_records') from None
        return {'inputs': inputs, 'obligations': []}, ['complete_input_records_salvaged']


def normalize_strategies(strategies):
    """Translate documented Hypothesis names only; constructors still validate each field."""
    try:
        encoded = json.dumps(strategies, allow_nan=False)
    except (TypeError, ValueError, RecursionError) as error:
        raise ValueError('strategy_not_json_data') from error
    if json.loads(encoded) != strategies:
        raise ValueError('strategy_requires_json_type_tags')
    def normalize(descriptor):
        if not isinstance(descriptor, dict):
            return descriptor
        result = dict(descriptor)
        if 'values' in result and (not isinstance(result['values'], list) or
                not all(supported_value(decode_value(value)) for value in result['values'])):
            raise ValueError('unsupported_sampled_input_value')
        aliases = {'integers': 'int', 'floats': 'float', 'booleans': 'bool',
                   'text': 'str', 'lists': 'list', 'sampled_from': 'sampled'}
        result['kind'] = aliases.get(result.get('kind'), result.get('kind'))
        for old, new in (('min_value', 'min'), ('max_value', 'max')):
            if old in result:
                if new in result and result[old] != result[new]:
                    raise ValueError('conflicting_strategy_bounds')
                result[new] = result.pop(old)
        if 'elements' in result:
            result['elements'] = normalize(result['elements'])
        return result
    return {name: normalize(value) for name, value in strategies.items()}


def parse_obligations(raw, evidence, *, required=False):
    accepted, errors = [], []
    if required and 'obligations' not in raw:
        return [],['obligations_key_required']
    records = raw.get('obligations', [])
    if not isinstance(records, list):
        return [], ['obligations_list_required']
    if required and not records:
        if isinstance(raw.get('reason'),str) and raw['reason'].strip():
            return [],['no_obligations_declared']
        return [],['no_obligations_declared; reason_required']
    for index, item in enumerate(records[:3]):
        try:
            candidate = dict(item) if isinstance(item, dict) else item
            if isinstance(candidate, dict) and isinstance(candidate.get('strategies'), list):
                parameters = list(evidence.builder.signature.parameters)
                if len(candidate['strategies']) != len(parameters):
                    raise ValueError('strategy_list_parameter_mismatch')
                candidate['strategies'] = dict(zip(parameters, candidate['strategies']))
            row = Obligation.model_validate(candidate).model_dump()
            program = evidence.by_id.get(row['program_id'])
            if program is None:
                raise ValueError('unknown_program_id')
            analysis = evidence.analyses[row['program_id']]
            if row['source_sha256'] not in (None, analysis['source_sha256']):
                raise ValueError('source_hash_mismatch')
            if row['line'] not in analysis['executable_lines']:
                raise ValueError('unknown_executable_source_line')
            if row['requirement'] in evidence.specification:
                requirement_grounding = 'quote'
            else:
                def words(text):
                    return {word[:-1] if word.endswith('s') and len(word) > 5 else word
                            for word in re.findall(r'[A-Za-z_]{4,}', text.lower())}
                specification_words = words(evidence.specification)
                requirement_words = words(row['requirement'])
                if len(specification_words & requirement_words) < 2:
                    raise ValueError('requirement_not_grounded_in_specification')
                requirement_grounding = 'overlap_hypothesis'
            row.update(id=f'O{index + 1}', source_sha256=analysis['source_sha256'],
                       applicability_status='hypothesis', requirement_grounding=requirement_grounding,
                       predicate_status='supported',
                       checker_scope='input_relation_and_bound_site_reach')
            try:
                tree = expression(row['predicate'], evidence.builder.signature.parameters)
                names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
                if not names & set(evidence.builder.signature.parameters):
                    raise ValueError('predicate_must_depend_on_input')
            except (ValueError, SyntaxError, TypeError, RecursionError) as error:
                row.update(predicate_status='unsupported', predicate_error=str(error)[:400])
            try:
                row['strategies'] = normalize_strategies(row['strategies'])
            except (ValueError, TypeError, RecursionError) as error:
                row.update(strategies={}, strategy_error=str(error)[:400])
                errors.append({'obligation_index': index, 'reason': str(error)[:400]})
            accepted.append(row)
        except (ValidationError, ValueError, TypeError, SyntaxError, RecursionError) as error:
            errors.append({'obligation_index': index, 'reason': str(error)[:800]})
    if len(records) > 3:
        errors.append('obligation_limit_3')
    return accepted, errors
