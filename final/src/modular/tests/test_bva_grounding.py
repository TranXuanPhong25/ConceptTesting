"""Scoped source receipts and checked construction; no model/PUT execution."""
import ast
from dataclasses import replace

import pytest

from final.src.modular.artifacts import ArtifactStore
from final.src.modular.boundary_value_analysis.legacy import BoundarySettings, BoundaryValueAnalysis
from final.src.modular.boundary_value_analysis.legacy.pipeline import BoundaryContext
from final.src.modular.boundary_value_analysis.legacy.types import InputTypeExtraction
from final.src.modular.boundary_value_analysis.legacy.templates import BoundaryTemplates
from final.src.modular.boundary_value_analysis.legacy.binding import BoundaryGuidance
from final.src.modular.boundary_value_analysis.legacy.construction import TargetCompiler, instantiate_value
from final.src.modular.boundary_value_analysis.legacy.context_requirements import parse_context_requirements, validate_context_requirements
from final.src.modular.boundary_value_analysis.legacy.characteristics import characteristic_values
from final.src.modular.boundary_value_analysis.legacy.grounding import enrich_guidance, source_facts, declared_scalar_types, audit_boundary, context_goals, goal_coverage
from final.src.modular.call_builder import CallBuilder
from final.src.modular.tests.test_bva_compiled import boundary
from final.src.modular.tests.test_boundary_value_analysis import ScriptedCalls


PREFIX_SOURCE = '''def f(xs: list[int], limit: int):
    total = 0
    count = len(xs)
    for i in range(count):
        total += xs[i]
        if total > limit:
            return False
        if xs[i] != xs[count - 1 - i]:
            return False
    return True
'''


def context(source, contract="", *, base=None, mode="checked"):
    ctx = BoundaryContext(0, "0", "f", source.split(":\n", 1)[0] + ':\n    """Process input values."""\n',
                          contract, source, base or [], BoundarySettings(grounding_mode=mode), None, None)
    ctx.input_types = InputTypeExtraction().run(ctx)
    ctx.templates = BoundaryTemplates().run(ctx)
    ctx.guidance = BoundaryGuidance().run(ctx)
    ctx.guidance = enrich_guidance(ctx, ctx.guidance)
    return ctx


def test_encoding_and_codepoint_receipts_do_not_become_string_length():
    source = '''def f(text: str):
    size = len(text.encode('utf-8'))
    for char in text.lower():
        code = ord(char)
        if code < 256:
            return size
'''
    ctx = context(source)
    facts = source_facts(ctx)["facts"]
    encoded = next(row for row in facts if row.get("measure") == "encoded_length")
    point = next(row for row in facts if row["kind"] == "code_point_transition")
    assert encoded["unit"] == "bytes" and encoded["encoding"] == "utf-8"
    assert point["transform"] == "lower" and point["threshold"] == 256
    selected = boundary("text", "length", 256, "Process input values.")
    assert audit_boundary(selected, ctx.guidance)[0]["kind"] == "codepoint_threshold_bound_to_length"


def test_reassigned_character_does_not_inherit_input_codepoint_receipt():
    ctx = context('''def f(text: str):
    for char in text:
        char = 'a'
        code = ord(char)
        if code < 256:
            return True
''')
    assert not any(row["kind"] == "code_point_transition" for row in source_facts(ctx)["facts"])


def test_character_is_not_a_numeric_ord_result():
    ctx = context("def f(text: str):\n    for char in text:\n        if char < 256:\n            return True\n")
    assert not any(row["kind"] == "code_point_transition" for row in source_facts(ctx)["facts"])


@pytest.mark.parametrize("source", [
    "def f(text: str, len):\n    return len(text.encode())\n",
    "def len(x):\n    return 1\ndef f(text: str):\n    return len(text.encode())\n",
    "def f(text: str):\n    text = 'x'\n    return len(text.encode())\n",
])
def test_shadowed_or_rebound_builtin_quantities_are_not_trusted(source):
    assert not source_facts(context(source))["facts"]


@pytest.mark.parametrize("source", [
    "def f(text: str):\n    def inner(text):\n        return len(text.encode('utf-8'))\n    return len(text)\n",
    "def f(text: str):\n    inner = lambda text: len(text.encode())\n    return len(text)\n",
    "from unknown import *\ndef f(text: str):\n    return len(text.encode())\n",
])
def test_nested_scopes_and_wildcard_imports_do_not_create_outer_quantity_receipts(source):
    facts = source_facts(context(source))
    assert facts["facts"] == []
    assert facts["scope"] == "unknown_nested_scope_or_wildcard_import"


def test_reject_polarity_complement_checks_this_predicate_only():
    ctx = context("def f(x: int):\n    if x <= 0:\n        return False\n    return False\n")
    fact = source_facts(ctx)["facts"][0]
    assert fact["rejection_operator"] == "<=" and fact["acceptance_operator"] == ">"
    assert fact["scope"] == "necessary_condition_to_continue"
    selected = boundary("x", "value", 0, "Process input values.", comparison=">")
    selected.update(alignment="operator", code_quote="if x <= 0:\n        return False")
    assert audit_boundary(selected, ctx.guidance)[0]["kind"] == "complementary_reject_not_operator_mismatch"
    selected["comparison"] = ">="
    assert audit_boundary(selected, ctx.guidance) == []  # Genuine inclusive/exclusive discrepancy is not hidden.


def test_prefix_recurrence_has_different_scope_from_full_sum():
    ctx = context(PREFIX_SOURCE)
    fact = next(row for row in source_facts(ctx)["facts"] if row["kind"] == "prefix_sum_rejection")
    assert fact["parameter"] == "xs" and fact["limit_parameter"] == "limit" and fact["scope"] == "visited_prefix"
    selected = boundary("xs", "sum", 0, "Process input values.")
    assert audit_boundary(selected, ctx.guidance)[0]["kind"] == "full_vs_prefix_quantity"


def test_sum_with_offset_does_not_become_plain_total_sum():
    ctx = context("def f(xs: list[int]):\n    return sum(xs, start=5)\n")
    assert not any(row.get("measure") == "sum" for row in source_facts(ctx)["facts"])


@pytest.mark.parametrize("source", [
    PREFIX_SOURCE.replace("total = 0", "total = 1"),
    PREFIX_SOURCE.replace("total += xs[i]", "total += xs[i]\n        xs[i] += 1"),
    PREFIX_SOURCE.replace("count = len(xs)", "count = len(xs)\n    total += 2"),
    PREFIX_SOURCE.replace("count = len(xs)", "count = len(xs)\n    xs.sort()"),
    PREFIX_SOURCE.replace("count = len(xs)", "count = len(xs)\n    xs[0] = 1"),
    PREFIX_SOURCE.replace("total += xs[i]", "total += xs[i]\n        total += 1"),
    PREFIX_SOURCE.replace("range(count)", "range(1, count)"),
    PREFIX_SOURCE.replace("total += xs[i]", "total = total + xs[i]"),
    PREFIX_SOURCE.replace("    for i in range(count):", "    for extra in [1]:\n        total += 10\n    for i in range(count):"),
    PREFIX_SOURCE.replace("        if xs[i] !=", "        xs[0]: int = 999\n        if xs[i] !="),
])
def test_unsupported_recurrences_remain_unknown(source):
    assert not any(row["kind"] == "prefix_sum_rejection" for row in source_facts(context(source))["facts"])


@pytest.mark.parametrize("contract, expected_float", [
    ("assert type(x) in [int, float]", True),
    ("assert isinstance(x, (int, float))", True),
    ("assert type(x) == int", False),
    ("assert type(x) == int or type(x) == float", False),
    ("x = int(x)\nassert type(x) in [int, float]", False),
    ("assert unknown(x)\nassert type(x) in [int, float]", False),
])
def test_declared_types_can_widen_observations_but_not_guess_from_unknown_contracts(contract, expected_float):
    ctx = context("def f(x):\n    return x\n", contract, base=[{"args": "(1,)", "kwargs": "{}"}])
    template = ctx.templates["candidates"][0]
    assert ("float_adjacent" in template["neighborhood_modes"]) == expected_float
    assert ("float" in declared_scalar_types(ctx).get("x", {}).get("types", [])) == expected_float


def test_off_mode_retains_observed_integer_templates():
    ctx = context("def f(x):\n    return x\n", "assert type(x) in [int, float]",
                  base=[{"args": "(1,)", "kwargs": "{}"}], mode="off")
    assert ctx.templates["candidates"][0]["neighborhood_modes"] == ["step"]
    assert "code_point" not in {r["characteristic"]["operation"] for r in context("def f(text: str):\n    return text\n", mode="off").templates["candidates"]}


def test_shadowed_contract_type_builtin_does_not_establish_declared_types():
    ctx = context("def f(x, type):\n    return x\n", "assert type(x) in [int, float]",
                  base=[{"args": "(1, 2)", "kwargs": "{}"}])
    assert declared_scalar_types(ctx) == {}


def test_concrete_excluded_targets_are_pruned_before_context_budget():
    ctx = context("def f(x: float, other: int):\n    return x\n", "assert x > 0")
    ctx.selection = {"boundaries": [boundary("x", "value", 0, "Process input values.")]}
    compiled = TargetCompiler().run(ctx)
    assert [row["side"] for row in compiled["obligations"]] == ["above"]
    assert compiled["obligations"][0]["context_budget"] == 20
    assert len(compiled["blocked"]) == 2
    assert {row["reason"] for row in compiled["blocked"]} == {"target_outside_recognized_domain"}
    ctx.settings = replace(ctx.settings, grounding_mode="off")
    assert len(TargetCompiler().run(ctx)["obligations"]) == 3


@pytest.mark.parametrize("code", [0, 127, 128, 255, 256, 0x10ffff])
def test_raw_codepoint_constructor_hits_codepoint_not_size(code):
    expression = {"parameter": "text", "operation": "code_point"}
    value = instantiate_value(expression, code, "ab")
    assert len(value) == 2 and code in characteristic_values(expression, {"text": value})


@pytest.mark.parametrize("code", [-1, 0xd800, 0xdfff, 0x110000, True])
def test_unsupported_unicode_scalar_targets_fail_explicitly(code):
    with pytest.raises(ValueError, match="unsupported_unicode_scalar_target"):
        instantiate_value({"operation": "code_point"}, code, "")


def test_context_properties_check_the_full_proper_prefix_condition():
    requirement = [{"property": "prefix_exceeds_limit", "parameter": "xs", "limit_parameter": "limit"}]
    signature = CallBuilder.for_source(PREFIX_SOURCE, "f").signature
    parse_context_requirements(requirement, signature)
    validate_context_requirements(requirement, {"xs": [-1, -1], "limit": -2})
    for values, limit in [([1, 1], 2), ([-1], -2), ([3, -1], 1)]:
        with pytest.raises(ValueError, match="context_requirement_not_met"):
            validate_context_requirements(requirement, {"xs": values, "limit": limit})
    validate_context_requirements([{"parameter": "text", "property": "non_ascii"}], {"text": "é"})
    with pytest.raises(ValueError, match="context_requirement_not_met"):
        validate_context_requirements([{"parameter": "text", "property": "non_ascii"}], {"text": "abc"})


def test_checked_named_contexts_preserve_and_report_prefix_goal_coverage(tmp_path):
    selected = boundary("xs", "sum", 0, "Process input values.", comparison="<=", sides=["at"])
    selected["threshold"] = {"kind": "expression", "parameter": "limit", "operation": "value"}
    record = {"obligation_id": "b1:at", "arguments": {"xs": [-1, -1], "limit": -2},
              "context_requirements": [{"parameter": "xs", "property": "palindrome"},
                  {"parameter": "xs", "property": "prefix_exceeds_limit", "limit_parameter": "limit"}]}
    calls = ScriptedCalls({"status": "selected", "reason": "Supported total-sum target.", "boundaries": [selected]}, {"inputs": [record]})
    spec = 'def f(xs: list[int], limit: int):\n    """Process input values."""\n'
    settings = BoundarySettings(grounding_mode="checked")
    arguments = dict(task_number=0, program_id=0, specification=spec, program_source=PREFIX_SOURCE,
                     entry_point="f", base_inputs=[])
    result = BoundaryValueAnalysis(settings).run(**arguments, artifacts=ArtifactStore(tmp_path), calls=calls)
    assert result["status"] == "generated" and ast.literal_eval(result["inputs"][0]["args"]) == ([-1, -1], -2)
    generation = ArtifactStore(tmp_path).read("tasks/0/boundary/0/generation.json")
    assert generation["context_goal_coverage"][0]["status"] == "covered"
    replay = BoundaryValueAnalysis(settings).run(**arguments, artifacts=ArtifactStore(tmp_path, read_only=True))
    assert replay == result
