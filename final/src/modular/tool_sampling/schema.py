"""One data contract for constrained decoding and native preparation validation."""
from __future__ import annotations

import ast
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, JsonValue, create_model

from ..input_buckets.predicates import validate_projection_types
from .membership import expression, BOOLEAN_METHODS
from .model import validate_model


class StrictObject(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


Bound = Union[int, float, str, None]
Size = Union[Annotated[int, Field(ge=0, le=1000)], Annotated[str, Field(min_length=1, max_length=2048)]]


class IntegerStrategy(StrictObject):
    kind: Literal['int']
    min: Bound = None
    max: Bound = None


class FloatStrategy(StrictObject):
    kind: Literal['float']
    min: Bound = None
    max: Bound = None


class BooleanStrategy(StrictObject):
    kind: Literal['bool']


class SampledStrategy(StrictObject):
    kind: Literal['sampled']
    values: list[JsonValue] = Field(min_length=1, max_length=1000)


class StringStrategy(StrictObject):
    kind: Literal['str']
    min_size: Size
    max_size: Size
    alphabet: str | None = Field(default=None, max_length=1000)


class UnsupportedStrategy(StrictObject):
    kind: Literal['unsupported']
    reason: str = Field(min_length=1, max_length=500)


class ListStrategy(StrictObject):
    kind: Literal['list']
    elements: Strategy
    min_size: int = Field(ge=0, le=1000)
    max_size: int = Field(ge=0, le=1000)


Strategy = Annotated[Union[IntegerStrategy, FloatStrategy, BooleanStrategy, SampledStrategy,
                           StringStrategy, ListStrategy, UnsupportedStrategy], Field(discriminator='kind')]
ListStrategy.model_rebuild()


class Target(StrictObject):
    id: str = Field(min_length=1, max_length=100)
    kind: Literal['class', 'boundary', 'rule']
    predicate: str = Field(min_length=1, max_length=2048)
    context: str = Field(default='True', min_length=1, max_length=2048)
    origin: Literal['spec', 'contract', 'impl']
    source_quote: str = Field(min_length=1, max_length=2000)
    status: Literal['feasible', 'infeasible', 'unresolved'] = 'unresolved'
    reason: str = Field(default='', max_length=1000)
    actions: list[str] = Field(default_factory=list, max_length=128)
    merged_from: list[str] = Field(default_factory=list, max_length=128)
    fault_rationale: str | None = Field(default=None, max_length=1000)
    boundary_side: str | None = Field(default=None, max_length=100)


ParameterType = Literal['int', 'bool', 'float', 'str', 'list', 'list[int]', 'list[float]', 'list[str]', 'any']


def preparation_type(builder, *, trusted_domain=None):
    names = list(builder.signature.parameters)
    types = create_model('ParameterTypes', __base__=StrictObject, **{name: (ParameterType, ...) for name in names})
    strategies = create_model('ParameterStrategies', __base__=StrictObject, **{name: (Strategy, ...) for name in names})
    arguments = create_model('Arguments', __base__=StrictObject, **{name: (JsonValue, ...) for name in names})
    record = create_model('SeedInput', __base__=StrictObject, arguments=(arguments, ...))
    domain_type = str if trusted_domain is None else Literal[trusted_domain]
    return create_model('ToolPreparation', __base__=StrictObject,
        types=(types, ...), domain=(domain_type, ...), domain_source_quote=(str, ...), strategies=(strategies, ...),
        targets=(list[Target], Field(max_length=128)),
        factors=(dict[str, dict[str, str]], ...), inputs=(list[record], Field(max_length=1000)))


def preparation_schema(builder, *, trusted_domain=None):
    schema = preparation_type(builder, trusted_domain=trusted_domain).model_json_schema()
    # Keep parameter mappings visible to the caller and server without relying
    # on the model to infer that a sequence must be keyed by parameter name.
    for name in ('types', 'strategies'):
        reference = schema['properties'][name]['$ref'].split('/')[-1]
        schema['properties'][name] = schema['$defs'][reference]
    return schema


def validate_expression(text, types):
    try:
        tree = expression(text, types)
        try:
            validate_projection_types(text, types)
        except ValueError as exc:
            if str(exc) in {'bool_numeric_projection_confusion','explicit_numeric_projection_required'}:
                raise
        def boolean(node):
            if isinstance(node, ast.BoolOp):
                return all(boolean(operand) for operand in node.values)
            if isinstance(node, ast.IfExp):
                return boolean(node.body) and boolean(node.orelse)
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):
                return node.func.attr in BOOLEAN_METHODS
            return isinstance(node, ast.Compare) or (
                isinstance(node, ast.Constant) and type(node.value) is bool or
                isinstance(node, ast.Name) and types.get(node.id) == 'bool' or
                isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not) or
                isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in {'is_int', 'is_float', 'is_bool', 'is_str', 'is_list',
                                      'is_number', 'all_numbers', 'all_ints', 'all_floats', 'all_strs',
                                      'isfinite', 'isinf', 'isnan', 'defined', 'chars_in',
                                      'all_in_range', 'is_numeric', 'is_instance', 'all_instance', 'all_type',
                                      'all','any','isinstance','bool','is_finite_numeric_string', 'any_type', 'any_in', 'all_in', 'any_not_in',
                                      'any_multiple', 'overlapping_occurrences'})
        if not boolean(tree.body):
            raise ValueError('boolean expression required (and/or operands must return bool)')
    except (ValueError, SyntaxError, TypeError) as exc:
        raise ValueError('invalid executable expression: ' + str(exc)) from None


def parse_preparation(value, builder, *, trusted_domain=None):
    prepared = preparation_type(builder, trusted_domain=trusted_domain).model_validate(value).model_dump()
    model = validate_model(prepared, builder)
    validate_expression(model['domain'], model['types'])
    for target in model['targets']:
        try:
            for field in ('context', 'predicate'):
                validate_expression(target[field], model['types'])
        except ValueError as exc:
            if 'bool_numeric_projection_confusion' in str(exc) or 'boolean expression required' in str(exc):
                raise
            target['support']='unsupported'
            target['support_error']=str(exc)
    for levels in model['factors'].values():
        for predicate in levels.values():
            validate_expression(predicate, model['types'])
    return model
