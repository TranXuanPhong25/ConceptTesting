"""Validate model concepts as source-bound hypotheses; retain direct inputs."""
import ast
from pydantic import BaseModel, ConfigDict, Field, StrictInt, ValidationError

from ..common.predicates import expression


class Concept(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(min_length=1, max_length=80)
    target_id: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=200)
    input_relation: str = Field(min_length=1, max_length=1600)
    instruction: str = Field(min_length=1, max_length=1600)
    evidence_lines: list[StrictInt] = Field(min_length=1, max_length=30)
    predicate: str = Field(max_length=2000)
    strategies: dict[str, dict] = Field(max_length=20)


def parse_response(raw, targets, parameter_names):
    known = {target['id']: target for target in targets}
    result = {'concepts': [], 'inputs': [], 'errors': []}
    if not isinstance(raw, dict):
        return {**result, 'errors': ['response_object_required']}
    if isinstance(raw.get('inputs'), list):
        result['inputs'] = raw['inputs']
    else:
        result['errors'].append('inputs_list_required')
    if set(raw) != {'concepts', 'inputs'}:
        result['errors'].append('expected_concepts_and_inputs')
    if not isinstance(raw.get('concepts'), list) or len(raw['concepts']) > 6:
        result['errors'].append('concepts_list_limit_6')
        return result
    if not raw['concepts'] and targets:
        result['errors'].append('at_least_one_concept_required_for_supplied_targets')
    identifiers = set()
    for index, item in enumerate(raw['concepts']):
        try:
            concept = Concept.model_validate(item)
            if concept.id in identifiers:
                raise ValueError('duplicate_concept_id')
            if concept.target_id not in known:
                raise ValueError('unknown_target_id')
            if not set(concept.evidence_lines) <= set(known[concept.target_id]['evidence_lines']):
                raise ValueError('unknown_source_line')
            if concept.strategies and set(concept.strategies) != set(parameter_names):
                raise ValueError('strategy_parameter_mismatch')
            if concept.predicate:
                tree = expression(concept.predicate, parameter_names)
                clauses = [tree.body, *(node for node in ast.walk(tree) if isinstance(node, ast.Compare))]
                if any(not ({node.id for node in ast.walk(clause) if isinstance(node, ast.Name)}
                            & set(parameter_names)) for clause in clauses):
                    raise ValueError('predicate_clause_must_depend_on_input; use empty predicate when unsupported')
            identifiers.add(concept.id)
            result['concepts'].append(concept.model_dump())
        except (ValidationError, ValueError, TypeError, SyntaxError) as error:
            result['errors'].append({'concept_index': index, 'reason': str(error)[:1000]})
    return result
