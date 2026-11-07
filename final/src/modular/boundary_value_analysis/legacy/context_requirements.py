"""Bounded context properties; no model-authored predicates or PUT execution."""
from .characteristics import number


PROPERTIES = {"palindrome", "all_negative", "all_nonpositive", "all_positive",
              "all_nonnegative", "token_only", "non_ascii", "prefix_exceeds_limit"}


def parse_context_requirements(requirements, signature):
    if not isinstance(requirements, list) or len(requirements) > 32:
        raise ValueError("invalid_context_requirements")
    for requirement in requirements:
        if not isinstance(requirement, dict):
            raise ValueError("invalid_context_requirement")
        parameter = requirement.get("parameter")
        property_name = requirement.get("property")
        if not isinstance(parameter, str) or parameter not in signature.parameters:
            raise ValueError("unknown_context_parameter")
        if not isinstance(property_name, str) or property_name not in PROPERTIES:
            raise ValueError("unsupported_context_property")
        expected_keys = {"parameter", "property"}
        if property_name == "token_only":
            expected_keys.add("token")
            token = requirement.get("token")
            if not isinstance(token, str) or len(token) != 1:
                raise ValueError("invalid_context_token")
        if property_name == "prefix_exceeds_limit":
            expected_keys.add("limit_parameter")
            limit = requirement.get("limit_parameter")
            if not isinstance(limit, str) or limit not in signature.parameters or limit == parameter:
                raise ValueError("invalid_context_limit_parameter")
        if set(requirement) != expected_keys:
            raise ValueError("invalid_context_requirement")
    return requirements


def validate_context_requirements(requirements, arguments):
    """Check declared context choices on the final call, not on a discarded seed."""
    for requirement in requirements:
        value = arguments[requirement["parameter"]]
        property_name = requirement["property"]
        if property_name == "palindrome":
            valid = type(value) in (str, list, tuple) and value == value[::-1]
        elif property_name == "token_only":
            valid = isinstance(value, str) and all(item == requirement["token"] for item in value)
        elif property_name == "non_ascii":
            valid = isinstance(value, str) and any(ord(character) > 127 for character in value)
        elif property_name == "prefix_exceeds_limit":
            limit = arguments[requirement["limit_parameter"]]
            valid = (type(value) in (list, tuple) and len(value) > 1 and all(number(item) for item in value)
                     and number(limit) and sum(value) <= limit)
            if valid:
                total = 0
                exceeded = False
                for item in value[:-1]:
                    total += item
                    exceeded = exceeded or total > limit
                valid = exceeded
        elif property_name in ("all_negative", "all_nonpositive", "all_positive", "all_nonnegative"):
            valid = type(value) in (list, tuple) and bool(value) and all(number(item) for item in value)
            if valid:
                if property_name == "all_negative":
                    valid = all(item < 0 for item in value)
                elif property_name == "all_nonpositive":
                    valid = all(item <= 0 for item in value)
                elif property_name == "all_positive":
                    valid = all(item > 0 for item in value)
                elif property_name == "all_nonnegative":
                    valid = all(item >= 0 for item in value)
        else:
            raise ValueError("unsupported_context_property")
        if not valid:
            raise ValueError("context_requirement_not_met")
