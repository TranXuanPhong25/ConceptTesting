"""Inspect input evidence without importing or executing the PUT."""
from __future__ import annotations

import ast
import inspect
import math


MAX_LITERAL_LENGTH = 16000
SCALAR_TYPES = {"int", "float", "str", "bool", "NoneType"}
CONTAINER_TYPES = {"list", "tuple", "set", "dict"}


def literal_value(text):
    if not isinstance(text, str) or len(text) > MAX_LITERAL_LENGTH:
        raise ValueError("invalid_or_oversized_literal")
    return ast.literal_eval(text)


def literal_arguments(record):
    if not isinstance(record, dict):
        raise ValueError("input_must_be_object")
    arguments = literal_value(record.get("args"))
    keywords = literal_value(record.get("kwargs"))
    if not isinstance(arguments, (list, tuple)) or not isinstance(keywords, dict):
        raise ValueError("invalid_args_kwargs")
    if any(not isinstance(name, str) for name in keywords):
        raise ValueError("invalid_keyword_name")
    return arguments, keywords


def finite_literal(value, depth=0):
    """Keep the supported literal language finite and small enough to inspect."""
    if depth > 8:
        return False
    if type(value) is float:
        return math.isfinite(value)
    if type(value) in (int, bool, str, type(None)):
        return True
    if type(value) in (list, tuple, set):
        return all(finite_literal(item, depth + 1) for item in value)
    if type(value) is dict:
        return all(finite_literal(key, depth + 1) and finite_literal(item, depth + 1)
                   for key, item in value.items())
    return False


def entry_function(source, entry_point):
    if not isinstance(source, str) or len(source) > 100000:
        raise ValueError("invalid_source")
    functions = []
    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef) and node.name == entry_point:
            functions.append(node)
    if len(functions) != 1:
        raise ValueError("expected_one_top_level_function")
    return functions[0]


def input_signature(function):
    """Build inspect.Signature from AST; annotations/default expressions never run."""
    if function.args.vararg or function.args.kwarg:
        raise ValueError("variadic_signature_unsupported")
    parameters = []
    positional = function.args.posonlyargs + function.args.args
    default_start = len(positional) - len(function.args.defaults)
    for index, argument in enumerate(positional):
        kind = inspect.Parameter.POSITIONAL_OR_KEYWORD
        if index < len(function.args.posonlyargs):
            kind = inspect.Parameter.POSITIONAL_ONLY
        default = inspect.Parameter.empty
        if index >= default_start:
            default = ast.literal_eval(function.args.defaults[index - default_start])
        parameters.append(inspect.Parameter(argument.arg, kind, default=default))
    for argument, default_node in zip(function.args.kwonlyargs, function.args.kw_defaults):
        default = inspect.Parameter.empty if default_node is None else ast.literal_eval(default_node)
        parameters.append(inspect.Parameter(argument.arg, inspect.Parameter.KEYWORD_ONLY, default=default))
    return inspect.Signature(parameters)


def describe_value(value, depth=0):
    kind = type(value).__name__
    if kind not in SCALAR_TYPES | CONTAINER_TYPES or depth > 4:
        return {"kind": "unknown"}
    description = {"kind": kind}
    if kind in CONTAINER_TYPES:
        descriptions = []
        values = list(value.values()) if kind == "dict" else list(value)
        # All elements of these bounded literals are inspected; no sampled min/max.
        for item in values:
            item_description = describe_value(item, depth + 1)
            if item_description not in descriptions:
                descriptions.append(item_description)
        description["items"] = sorted(descriptions, key=repr)
    return description


def annotation_types(node, depth=0):
    """A small syntax reader, not eval/get_type_hints on untrusted code."""
    if node is None or depth > 5:
        return []
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        try:
            return annotation_types(ast.parse(node.value, mode="eval").body, depth + 1)
        except SyntaxError:
            return []
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return annotation_types(node.left, depth + 1) + annotation_types(node.right, depth + 1)
    if isinstance(node, ast.Constant) and node.value is None:
        return [{"kind": "NoneType"}]
    name = node.id if isinstance(node, ast.Name) else node.attr if isinstance(node, ast.Attribute) else ""
    aliases = {"List": "list", "Tuple": "tuple", "Set": "set", "Dict": "dict"}
    kind = aliases.get(name, name)
    if kind in SCALAR_TYPES | CONTAINER_TYPES:
        return [{"kind": kind}]
    if not isinstance(node, ast.Subscript):
        return []
    outer_name = node.value.id if isinstance(node.value, ast.Name) else (
        node.value.attr if isinstance(node.value, ast.Attribute) else "")
    arguments = list(node.slice.elts) if isinstance(node.slice, ast.Tuple) else [node.slice]
    if outer_name in ("Optional", "Union"):
        descriptions = []
        for argument in arguments:
            descriptions.extend(annotation_types(argument, depth + 1))
        if outer_name == "Optional":
            descriptions.append({"kind": "NoneType"})
        return descriptions
    kind = aliases.get(outer_name, outer_name)
    if kind not in CONTAINER_TYPES:
        return []
    if kind == "dict":
        arguments = arguments[1:2]
    items = []
    for argument in arguments:
        for description in annotation_types(argument, depth + 1):
            if description not in items:
                items.append(description)
    return [{"kind": kind, "items": items}]


class InputTypeExtraction:
    name = "input_types"

    def run(self, context):
        # VALIDATION START: supported PUT entry point and input signature.
        try:
            function = entry_function(context.program_source, context.entry_point)
            signature = input_signature(function)
        except (ValueError, SyntaxError, TypeError, RecursionError):
            return {"status": "unsupported_signature", "parameters": [], "rejected": []}
        # VALIDATION END: supported PUT entry point and input signature.
        parameters = {}
        for argument in function.args.posonlyargs + function.args.args + function.args.kwonlyargs:
            parameters[argument.arg] = {
                "name": argument.arg, "kind": signature.parameters[argument.arg].kind.name,
                "evidence": [],
            }
            if argument.annotation is not None:
                parameters[argument.arg]["evidence"].append({
                    "source": "put_annotation", "text": ast.unparse(argument.annotation),
                    "types": annotation_types(argument.annotation),
                })
        # Task annotations can fill missing PUT annotations, with distinct provenance.
        try:
            specification_function = entry_function(context.specification, context.entry_point)
        except (ValueError, SyntaxError, TypeError, RecursionError):
            specification_function = None
        if specification_function is not None:
            for argument in (specification_function.args.posonlyargs + specification_function.args.args
                             + specification_function.args.kwonlyargs):
                if argument.arg in parameters and argument.annotation is not None:
                    parameters[argument.arg]["evidence"].append({
                        "source": "spec_annotation", "text": ast.unparse(argument.annotation),
                        "types": annotation_types(argument.annotation),
                    })
        rejected = []
        for index, record in enumerate(context.base_inputs):
            try:
                # VALIDATION START: observed input binding and supported literal types.
                bound_values = self.validate_observed_input(record, signature, parameters)
                # VALIDATION END: observed input binding and supported literal types.
                for name, value in bound_values.items():
                    descriptions = [describe_value(value)]
                    previous = None
                    for evidence in parameters[name]["evidence"]:
                        if evidence["source"] == "observed_input" and evidence["types"] == descriptions:
                            previous = evidence
                            break
                    if previous is None:
                        previous = {"source": "observed_input", "input_indices": [],
                                    "observation_count": 0, "types": descriptions}
                        parameters[name]["evidence"].append(previous)
                    previous["observation_count"] += 1
                    if len(previous["input_indices"]) < 8:
                        previous["input_indices"].append(index)
            except (ValueError, SyntaxError, TypeError, RecursionError):
                rejected.append({"input_index": index, "reason": "invalid_input_evidence"})
        return {"status": "extracted", "parameters": list(parameters.values()), "rejected": rejected,
                "domain_status": "types_are_evidence_not_complete_domain"}

    @staticmethod
    def validate_observed_input(record, signature, parameters):
        """Bind saved arguments or verify saved bound names before extracting types."""
        if "args" in record and "kwargs" in record:
            arguments, keywords = literal_arguments(record)
            bound = signature.bind(*arguments, **keywords)
            bound.apply_defaults()
            bound_values = bound.arguments
        elif "bound" in record:
            if not isinstance(record["bound"], dict) or set(record["bound"]) - set(parameters):
                raise ValueError("unknown_bound_parameters")
            bound_values = {}
            for name, text in record["bound"].items():
                bound_values[name] = literal_value(text)
        else:
            raise ValueError("missing_input_arguments")
        if not all(finite_literal(value) for value in bound_values.values()):
            raise ValueError("unsupported_literal")
        return bound_values
