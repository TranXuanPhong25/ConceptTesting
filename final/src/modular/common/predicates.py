"""Small, bounded input-expression contract, never arbitrary model-written code."""
from __future__ import annotations

import ast
import math
from ..call_builder import MAX_CONTAINER_ITEMS, entry_function


def bounded(value):
    if len(value) > MAX_CONTAINER_ITEMS:
        raise ValueError('predicate_resource_limit')
    return value


def distinct_count(values):
    distinct = []
    for value in bounded(values):
        if value not in distinct:
            distinct.append(value)
    return len(distinct)


def chars_in(value, alphabet):
    if type(value) is not str or type(alphabet) is not str:
        return False
    return set(bounded(value)) <= set(bounded(alphabet))


def all_in_range(values, lower, upper):
    return all(lower <= value <= upper for value in bounded(values))


def numeric_text(value):
    if type(value) not in (int, float, str):
        raise ValueError('numeric_input_type')
    return bounded(str(value)).replace(',', '.')


def numeric_value(value):
    return float(numeric_text(value))


def is_numeric(value):
    if type(value) not in (int, float, str):
        return False
    text = numeric_text(value)
    try:
        float(text)
        return True
    except ValueError:
        return False


def is_instance(value, tag):
    types = {'int': int, 'bool': bool, 'float': float, 'str': str, 'list': list, 'tuple': tuple}
    if tag not in types:
        raise ValueError('unsupported_instance_type')
    return isinstance(value, types[tag])


def all_instance(values, tags):
    return all(any(is_instance(value, tag) for tag in tags.split(',')) for value in bounded(values))


def all_type(values, tag):
    types = {'int': int, 'float': float, 'str': str, 'bool': bool, 'list': list}
    if tag not in types:
        raise ValueError('unsupported_exact_type')
    return all(type(value) is types[tag] for value in bounded(values))


def any_type(values, tag):
    return any(all_type([value], tag) for value in bounded(values))


def any_in(values, choices):
    bounded(choices)
    return any(value in choices for value in bounded(values))


def all_in(values, choices):
    bounded(choices)
    return all(value in choices for value in bounded(values))


def any_not_in(values, choices):
    return not all_in(values, choices)


def slice_values(values, start, step):
    if type(start) is not int or type(step) is not int or step == 0:
        raise ValueError('invalid_slice_coordinates')
    return bounded(values)[start::step]


def any_multiple(values, divisor):
    if type(divisor) is not int or divisor == 0:
        raise ValueError('invalid_multiple_divisor')
    return any(type(value) is int and value % divisor == 0 for value in bounded(values))


def overlapping_occurrences(text, fragment):
    if type(text) is not str or type(fragment) is not str or not fragment:
        raise ValueError('overlap_requires_strings_and_nonempty_fragment')
    bounded(text);bounded(fragment)
    previous = None
    for position in range(len(text)-len(fragment)+1):
        if text.startswith(fragment, position):
            if previous is not None and position-previous < len(fragment):
                return True
            previous = position
    return False


def is_finite_numeric_string(value):
    if type(value) is not str:
        return False
    bounded(value)
    try:
        return math.isfinite(float(value))
    except ValueError:
        return False

def split(value, separator):
    if type(value) is not str or type(separator) is not str or not separator:
        raise ValueError("split_requires_string_and_nonempty_separator")
    return value.split(separator)


FUNCTIONS = {"len": len, "sum": sum, "min": min, "max": max, "abs": abs,
             'distinct_count': distinct_count,
             "float": float, "int": int, "floor": math.floor, "ceil": math.ceil,
             "isfinite": math.isfinite, "isinf": math.isinf, "isnan": math.isnan,
             "split": split, 'chars_in': chars_in, 'all_in_range': all_in_range,
             'numeric_value': numeric_value, 'is_numeric': is_numeric, 'is_instance': is_instance,
             'all_instance': all_instance, 'all_type': all_type, 'is_finite_numeric_string': is_finite_numeric_string,
             'any_type': any_type, 'any_in': any_in, 'all_in': all_in, 'any_not_in': any_not_in,
             'slice_values': slice_values, 'any_multiple': any_multiple, 'overlapping_occurrences': overlapping_occurrences,
             "defined": lambda value: True,
             "is_int": lambda v: type(v) is int,
             "is_float": lambda v: type(v) is float,
             "is_bool": lambda v: type(v) is bool,
             "is_str": lambda v: type(v) is str,
             "is_list": lambda v: type(v) is list,
             "is_number": lambda v: isinstance(v, (int, float)),
             "all_numbers": lambda v: all(type(x) in (int, float) for x in v),
             "all_ints": lambda v: all(type(x) is int for x in v),
             "all_floats": lambda v: all(type(x) is float for x in v),
             "all_strs": lambda v: all(type(x) is str for x in v)}
NODES = (ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.UnaryOp, ast.Not, ast.USub,
         ast.UAdd, ast.BinOp, ast.Add, ast.Sub, ast.Compare, ast.Eq, ast.NotEq,
         ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn, ast.Name, ast.Load,
         ast.Constant, ast.Call, ast.List, ast.Tuple, ast.Set, ast.Subscript, ast.Slice)
FUNCTION_ARITY = {'split': 2, 'chars_in': 2, 'all_in_range': 3, 'is_instance': 2,
                  'all_instance': 2, 'all_type': 2}
FUNCTION_ARITY.update({'any_type':2,'any_in':2,'all_in':2,'any_not_in':2,
                       'slice_values':3,'any_multiple':2,'overlapping_occurrences':2})


def expression(text, names):
    if not isinstance(text, str) or not text or len(text) > 2048:
        raise ValueError("invalid_predicate_size")
    tree = ast.parse(text, mode="eval")
    nodes = list(ast.walk(tree))
    if len(nodes) > 128:
        raise ValueError("predicate_node_limit")
    for node in nodes:
        if not isinstance(node, NODES):
            raise ValueError("unsupported_predicate_node:" + type(node).__name__)
        if isinstance(node, ast.Name) and node.id not in set(names) | set(FUNCTIONS):
            raise ValueError("unknown_predicate_name:" + node.id)
        if isinstance(node, ast.Call):
            if (not isinstance(node.func, ast.Name) or node.func.id not in FUNCTIONS
                    or len(node.args) != FUNCTION_ARITY.get(node.func.id, 1) or node.keywords):
                raise ValueError("unsupported_predicate_call")
        if isinstance(node, ast.Constant) and (type(node.value) not in (int, float, bool, str, type(None))
                or len(repr(node.value)) > 256):
            raise ValueError("unsupported_predicate_constant")
    return tree


def validate_projection_types(text, types):
    """Catch the common raw-string/numeric confusion without executing inputs."""
    tree = expression(text, types)

    def kind(node):
        if isinstance(node, ast.Name):
            return types.get(node.id)
        if isinstance(node, ast.Constant):
            return {int: "int", float: "float", str: "str", bool: "bool"}.get(type(node.value))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in {'overlapping_occurrences','any_multiple','any_type','any_in','all_in','any_not_in',
                                'chars_in','all_in_range','is_numeric','is_instance','all_instance','all_type',
                                'is_finite_numeric_string','is_int','is_float','is_bool','is_str','is_list'}:
                return 'bool'
            if node.func.id == "split":
                return "list[str]"
            if node.func.id in {"float", "int", "len", "floor", "ceil", 'numeric_value', 'distinct_count'}:
                return "float" if node.func.id in {"float", 'numeric_value'} else "int"
        if isinstance(node, ast.Subscript):
            container = kind(node.value)
            if container == "str":
                return "str"
            if container in {"list[str]", "list[int]", "list[float]"}:
                return container[5:-1]
        if isinstance(node, ast.UnaryOp):
            return kind(node.operand)
        if isinstance(node, ast.BinOp):
            left, right = kind(node.left), kind(node.right)
            if "str" in (left, right) and {left, right} & {"int", "float"}:
                raise ValueError("explicit_numeric_projection_required")
            return "float" if "float" in (left, right) else left
        return None

    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            for left, right in zip([node.left, *node.comparators], node.comparators):
                if {kind(left),kind(right)} & {'bool'} and {kind(left),kind(right)} & {'int','float'}:
                    raise ValueError('bool_numeric_projection_confusion')
                if {kind(left), kind(right)} & {"str"} and {kind(left), kind(right)} & {"int", "float"}:
                    raise ValueError("explicit_numeric_projection_required")
        elif isinstance(node, ast.BinOp):
            kind(node)
    return tree


def evaluate(text, arguments):
    tree = expression(text, arguments)
    result = eval(compile(tree, "<bucket-predicate>", "eval"),
                  {"__builtins__": {}, **FUNCTIONS}, arguments)
    if type(result) is not bool:
        raise ValueError("predicate_must_return_bool")
    return result


def declared_types(source, entry):
    function = entry_function(source, entry)
    result = {}
    for arg in function.args.posonlyargs + function.args.args + function.args.kwonlyargs:
        if arg.annotation is not None:
            text = ast.unparse(arg.annotation).replace("typing.", "").replace("List[", "list[")
            if text == "list[Any]":
                text = "list"
            if text not in {"int", "bool", "float", "str", "list", "list[int]", "list[float]", "list[str]"}:
                raise ValueError("unsupported_declared_type:" + text)
            result[arg.arg] = text
    return result
