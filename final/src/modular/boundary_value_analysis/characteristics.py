"""Typed characteristic evaluators and exact boundary neighborhoods."""
import math
import re

MAX_NUMERIC_STRING_CHARACTERS = 1000


def number(value):
    return type(value) in (int, float) and (type(value) is int or math.isfinite(value))


def parsed_float(value):
    """Interpret data using float(), never evaluate a Python expression."""
    if type(value) is not str:
        raise ValueError("numeric_string_required")
    if len(value) > MAX_NUMERIC_STRING_CHARACTERS:
        raise ValueError("numeric_string_resource_limit")
    try:
        result = float(value)
    except ValueError:
        raise ValueError("invalid_numeric_string") from None
    if not math.isfinite(result):
        raise ValueError("nonfinite_numeric_string")
    return result


def characteristic_values(expression, arguments):
    value = arguments[expression["parameter"]]
    operation = expression["operation"]
    if operation == "value" and number(value):
        return [value]
    if operation == "parsed_float":
        return [parsed_float(value)]
    if operation == "length" and type(value) in (str, list, tuple, set, dict):
        return [len(value)]
    if operation == "run_length" and isinstance(value, str):
        token = expression["token"]
        if not isinstance(token, str) or len(token) != 1:
            raise ValueError("run_token_must_be_one_character")
        return [max((len(match.group()) for match in re.finditer(re.escape(token) + "+", value)), default=0)]
    if operation in ("sum", "elements", "minimum", "maximum", "range"):
        if type(value) not in (list, tuple) or not all(number(item) for item in value):
            raise ValueError("numeric_sequence_required")
        if operation == "elements":
            return list(value)
        if operation == "sum":
            return [sum(value)]
        if not value:
            raise ValueError("nonempty_sequence_required")
        if operation == "minimum":
            return [min(value)]
        if operation == "maximum":
            return [max(value)]
        return [max(value) - min(value)]
    raise ValueError("input_does_not_support_characteristic")


def boundary_target(boundary, arguments, side):
    threshold = boundary["threshold"]
    value = threshold["value"] if threshold["kind"] == "constant" else characteristic_values(threshold, arguments)[0]
    if not number(value):
        raise ValueError("nonfinite_threshold")
    if boundary.get("numeric_kind") == "float" and type(value) is int:
        try:
            converted = float(value)
        except OverflowError:
            raise ValueError("threshold_not_on_float_grid") from None
        if converted != value:
            raise ValueError("threshold_not_on_float_grid")
        value = converted
    integer_grid = boundary.get("numeric_kind") == "int"
    if side == "at":
        if integer_grid and int(value) != value:
            raise ValueError("threshold_not_on_integer_grid")
        return int(value) if integer_grid else value
    neighborhood = boundary["neighborhood"]
    if neighborhood["mode"] == "float_adjacent":
        target = math.nextafter(value, -math.inf if side == "below" else math.inf)
    else:
        step = neighborhood["step"]
        if integer_grid:
            if int(step) != step or step < 1:
                raise ValueError("integer_step_required")
            target = math.ceil(value) - int(step) if side == "below" else math.floor(value) + int(step)
        else:
            target = value - step if side == "below" else value + step
    if not number(target) or target == value:
        raise ValueError("unrepresentable_neighbor")
    return target
