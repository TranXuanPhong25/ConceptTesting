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
    functions = [
        node
        for node in ast.parse(source).body
        if isinstance(node, ast.FunctionDef) and node.name == entry_point
    ]
    if len(functions) != 1:
        raise ValueError("expected_one_top_level_function")
    return functions[0]


def input_signature(function):
    args = function.args
    if args.vararg or args.kwarg:
        raise ValueError("variadic_signature_unsupported")

    parameters = []
    positional = args.posonlyargs + args.args
    positional_only_count = len(args.posonlyargs)
    default_start = len(positional) - len(args.defaults)

    for index, argument in enumerate(positional):
        # Arguments before "/" can only be passed by position.
        kind = (
            inspect.Parameter.POSITIONAL_ONLY
            if index < positional_only_count
            else inspect.Parameter.POSITIONAL_OR_KEYWORD
        )
        # The AST stores defaults only for the trailing positional arguments.
        default = inspect.Parameter.empty
        if index >= default_start:
            default = ast.literal_eval(args.defaults[index - default_start])
        # Keep the annotation as source text for later validation.
        annotation = inspect.Parameter.empty
        if argument.annotation is not None:
            annotation = ast.unparse(argument.annotation)
        parameters.append(
            inspect.Parameter(argument.arg, kind, default=default, annotation=annotation)
        )

    # Keyword-only defaults align one-to-one with their arguments in the AST.
    for argument, default_node in zip(args.kwonlyargs, args.kw_defaults):
        # A required argument has no default node, whereas "= None" has one.
        default = inspect.Parameter.empty
        if default_node is not None:
            default = ast.literal_eval(default_node)
        annotation = inspect.Parameter.empty
        if argument.annotation is not None:
            annotation = ast.unparse(argument.annotation)
        parameters.append(
            inspect.Parameter(
                argument.arg,
                inspect.Parameter.KEYWORD_ONLY,
                default=default,
                annotation=annotation,
            )
        )

    return inspect.Signature(parameters)


def input_identity(signature, record):
    arguments = ast.literal_eval(record["args"])
    keywords = ast.literal_eval(record["kwargs"])
    bound = signature.bind(*arguments, **keywords)
    bound.apply_defaults()
    return bound_input_identity(bound.arguments)


def bound_input_identity(arguments):
    # Strict identity preserves literal types and container ordering.
    return repr([(name, type(value).__name__, repr(value)) for name, value in arguments.items()])


def supported_value(value, depth=0):
    if depth > 8:
        return False
    if type(value) is float:
        return math.isfinite(value)
    if type(value) in (int, str, bool, type(None)):
        return True
    if type(value) in (list, tuple, set):
        return len(value) <= MAX_CONTAINER_ITEMS and all(
            supported_value(item, depth + 1) for item in value
        )
    if type(value) is dict:
        return len(value) <= MAX_CONTAINER_ITEMS and all(
            supported_value(key, depth + 1) and supported_value(item, depth + 1)
            for key, item in value.items()
        )
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


def validate_annotation(annotation, depth=0):
    if not isinstance(annotation, str) or depth > 8:
        raise ValueError("unsupported_type_annotation")
    node = ast.parse(annotation, mode="eval").body
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return validate_annotation(node.value, depth + 1)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        validate_annotation(ast.unparse(node.left), depth + 1)
        validate_annotation(ast.unparse(node.right), depth + 1)
        return
    if isinstance(node, ast.Constant) and node.value is None:
        return
    name = ast.unparse(node.value if isinstance(node, ast.Subscript) else node).removeprefix("typing.")
    if not isinstance(node, ast.Subscript):
        if name not in {"Any", "int", "float", "bool", "str", "None", "list", "List", "dict", "Dict", "set", "Set", "tuple", "Tuple"}:
            raise ValueError("unsupported_type_annotation:" + annotation)
        return
    arguments = list(node.slice.elts) if isinstance(node.slice, ast.Tuple) else [node.slice]
    arity = {"list": 1, "List": 1, "set": 1, "Set": 1, "dict": 2, "Dict": 2, "Optional": 1}
    if name not in {*arity, "tuple", "Tuple", "Union"} or (name in arity and len(arguments) != arity[name]):
        raise ValueError("unsupported_type_annotation:" + annotation)
    for index, argument in enumerate(arguments):
        if name in ("tuple", "Tuple") and len(arguments) == 2 and index == 1 and isinstance(argument, ast.Constant) and argument.value is Ellipsis:
            continue
        validate_annotation(ast.unparse(argument), depth + 1)


def matches_annotation(value, annotation):
    """Interpret supported type syntax as data; never evaluate annotations or coerce inputs."""
    node = ast.parse(annotation, mode="eval").body
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return matches_annotation(value, node.value)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return matches_annotation(value, ast.unparse(node.left)) or matches_annotation(value, ast.unparse(node.right))
    if isinstance(node, ast.Constant) and node.value is None:
        return value is None
    name = ast.unparse(node.value if isinstance(node, ast.Subscript) else node).removeprefix("typing.")
    if name == "Any":
        return True
    primitives = {"int": int, "float": float, "bool": bool, "str": str, "None": type(None)}
    if name in primitives:
        return type(value) in (int, float) if name == "float" else type(value) is primitives[name]
    if isinstance(node, ast.Subscript):
        arguments = list(node.slice.elts) if isinstance(node.slice, ast.Tuple) else [node.slice]
        if name in ("Optional", "Union"):
            return (name == "Optional" and value is None) or any(
                matches_annotation(value, ast.unparse(arg)) for arg in arguments)
    containers = {"list": list, "List": list, "dict": dict, "Dict": dict,
                  "set": set, "Set": set, "tuple": tuple, "Tuple": tuple}
    if name not in containers:
        raise ValueError("unsupported_type_annotation:" + annotation)
    if type(value) is not containers[name]:
        return False
    if not isinstance(node, ast.Subscript):
        return True
    if name in ("dict", "Dict") and len(arguments) == 2:
        return all(matches_annotation(key, ast.unparse(arguments[0])) and
                   matches_annotation(item, ast.unparse(arguments[1])) for key, item in value.items())
    if name in ("tuple", "Tuple"):
        if len(arguments) == 2 and isinstance(arguments[1], ast.Constant) and arguments[1].value is Ellipsis:
            return all(matches_annotation(item, ast.unparse(arguments[0])) for item in value)
        return len(value) == len(arguments) and all(
            matches_annotation(item, ast.unparse(arg)) for item, arg in zip(value, arguments))
    if len(arguments) != 1:
        raise ValueError("unsupported_type_annotation:" + annotation)
    return all(matches_annotation(item, ast.unparse(arguments[0])) for item in value)


class CallBuilder:
    def __init__(self, signature):
        for parameter in signature.parameters.values():
            if parameter.annotation is not inspect.Parameter.empty:
                validate_annotation(parameter.annotation)
        self.signature = signature

    @classmethod
    def for_source(cls, source, entry_point, *, input_types=None):
        signature = input_signature(entry_function(source, entry_point))
        if input_types:
            if input_types.keys() - signature.parameters.keys():
                raise ValueError("unknown_type_parameters")
            parameters = [
                parameter.replace(annotation=input_types[name])
                if parameter.annotation is inspect.Parameter.empty and name in input_types
                else parameter
                for name, parameter in signature.parameters.items()
            ]
            signature = signature.replace(parameters=parameters)
        return cls(signature)

    def validate_call(self, record):
        bound = self.signature.bind(*ast.literal_eval(record["args"]), **ast.literal_eval(record["kwargs"]))
        bound.apply_defaults()
        self.build_values(bound.arguments)
        return bound.arguments

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
            annotation = parameter.annotation
            if annotation is not inspect.Parameter.empty and not matches_annotation(value, annotation):
                raise ValueError("argument_type_mismatch:" + name)
            if parameter.kind == inspect.Parameter.KEYWORD_ONLY:
                keywords[name] = value
            else:
                positional.append(value)
        args_literal = repr(tuple(positional))
        kwargs_literal = repr(keywords)
        if len(args_literal) > MAX_LITERAL_CHARACTERS or len(kwargs_literal) > MAX_LITERAL_CHARACTERS:
            raise ValueError("argument_literal_size_limit")
        # VALIDATION END: named values bind to exactly the declared interface.
        return {"args": args_literal, "kwargs": kwargs_literal, "guidance_id": guidance_id}
