"""Build Python calls from named data without evaluating model-written code."""
from __future__ import annotations

import ast
import copy
import inspect
import math

MAX_CONTAINER_ITEMS = 1000
MAX_LITERAL_CHARACTERS = 16000


def entry_function(source, entry_point):
    if not isinstance(source, str) or len(source) > 100000:
        raise ValueError("invalid_source")
    functions = [node for node in ast.parse(source).body
                 if isinstance(node, ast.FunctionDef) and node.name == entry_point]
    if len(functions) != 1:
        raise ValueError("expected_one_top_level_function")
    return functions[0]


def input_signature(function):
    """Read signature/default data from AST, never execute the function/annotations."""
    if function.args.vararg or function.args.kwarg:
        raise ValueError("variadic_signature_unsupported")
    parameters = []
    positional = function.args.posonlyargs + function.args.args
    default_start = len(positional) - len(function.args.defaults)
    for index, argument in enumerate(positional):
        kind = inspect.Parameter.POSITIONAL_ONLY if index < len(function.args.posonlyargs) else inspect.Parameter.POSITIONAL_OR_KEYWORD
        default = inspect.Parameter.empty
        if index >= default_start:
            default = ast.literal_eval(function.args.defaults[index - default_start])
        parameters.append(inspect.Parameter(argument.arg, kind, default=default))
    for argument, default_node in zip(function.args.kwonlyargs, function.args.kw_defaults):
        default = inspect.Parameter.empty if default_node is None else ast.literal_eval(default_node)
        parameters.append(inspect.Parameter(argument.arg, inspect.Parameter.KEYWORD_ONLY, default=default))
    return inspect.Signature(parameters)


def supported_value(value, depth=0):
    if depth > 8:
        return False
    if type(value) is float:
        return math.isfinite(value)
    if type(value) in (int, str, bool, type(None)):
        return True
    if type(value) in (list, tuple, set):
        return len(value) <= MAX_CONTAINER_ITEMS and all(supported_value(item, depth + 1) for item in value)
    if type(value) is dict:
        return len(value) <= MAX_CONTAINER_ITEMS and all(supported_value(key, depth + 1) and supported_value(item, depth + 1)
                                          for key, item in value.items())
    return False


def decode_value(value, depth=0):
    if depth > 8:
        raise ValueError("argument_nesting_limit")
    if isinstance(value, list):
        return [decode_value(item, depth + 1) for item in value]
    if isinstance(value, dict):
        if "__python_type__" in value:
            if set(value) != {"__python_type__", "items"} or not isinstance(value["items"], list):
                raise ValueError("invalid_argument_type_tag")
            items = [decode_value(item, depth + 1) for item in value["items"]]
            if value["__python_type__"] == "tuple":
                return tuple(items)
            if value["__python_type__"] == "set":
                return set(items)
            raise ValueError("unsupported_argument_type_tag")
        return {key: decode_value(item, depth + 1) for key, item in value.items()}
    return value


class CallBuilder:
    def __init__(self, signature):
        self.signature = signature

    @classmethod
    def for_source(cls, source, entry_point):
        return cls(input_signature(entry_function(source, entry_point)))

    def decode_arguments(self, arguments):
        if not isinstance(arguments, dict) or set(arguments) - set(self.signature.parameters):
            raise ValueError("unknown_or_invalid_parameters")
        return {name: decode_value(value) for name, value in arguments.items()}

    def build(self, arguments, *, guidance_id=None):
        return self.build_values(self.decode_arguments(arguments), guidance_id=guidance_id)

    def build_values(self, arguments, *, guidance_id=None):
        # VALIDATION START: named values bind to exactly the declared interface.
        if set(arguments) - set(self.signature.parameters):
            raise ValueError("unknown_parameters")
        positional = []
        keywords = {}
        for name, parameter in self.signature.parameters.items():
            if name in arguments:
                value = arguments[name]
            elif parameter.default is not inspect.Parameter.empty:
                value = copy.deepcopy(parameter.default)
            else:
                raise ValueError("missing_parameter")
            if not supported_value(value):
                raise ValueError("unsupported_or_nonfinite_argument")
            if parameter.kind == inspect.Parameter.KEYWORD_ONLY:
                keywords[name] = value
            else:
                positional.append(value)
        self.signature.bind(*positional, **keywords)
        args_literal = repr(tuple(positional))
        kwargs_literal = repr(keywords)
        if len(args_literal) > MAX_LITERAL_CHARACTERS or len(kwargs_literal) > MAX_LITERAL_CHARACTERS:
            raise ValueError("argument_literal_size_limit")
        # VALIDATION END: named values bind to exactly the declared interface.
        return {"args": args_literal, "kwargs": kwargs_literal, "guidance_id": guidance_id}
