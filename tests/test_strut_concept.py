from __future__ import annotations

import json
from pathlib import Path

from strut_concept.benchmark import Subject
from strut_concept.evaluator import evaluate
from strut_concept.extractor import build_context, build_seed
from strut_concept.statistics import compare, exact_sign_p
from strut_concept.translator import parse_cases, translate_cases


SUBJECT = Subject("classify", "int", (("int", "integer", "value"), ("int", "integer", "upper")))
SOURCE = """int classify(int value, int upper) {
  if (value > upper) return 1;
  if (value == upper) return 0;
  return -1;
}
"""


def test_seed_matches_paper_triple_and_extension_is_additive():
    context = build_context(SOURCE, SUBJECT)
    basic = build_seed(context)
    extended = build_seed(context, extended=True)
    assert set(basic) == {"Inputs", "Outputs", "Stubs"}
    assert basic["Inputs"][0] == {"ExprInput": "value", "Type": "int", "Value": 0}
    assert set(basic).issubset(extended)
    assert extended["FaultHypotheses"][0]["Branch"] == "value > upper"
    assert extended["InputConstraints"]
    assert extended["PathEffects"]


def test_static_extraction_ignores_documentation_and_preprocessor_calls():
    source = "/* fake_call(1); if (wrong > 2) */\n#define M(x) macro_call(x)\n" + SOURCE
    context = build_context(source, SUBJECT)
    assert "fake_call" not in context["callees"]
    assert "macro_call" not in context["callees"]
    assert context["conditions"] == ["value > upper", "value == upper"]


def test_known_dependency_gets_a_safe_stub_signature():
    subject = Subject("fold", "int", (("int", "integer", "c"),))
    context = build_context("int fold(int c) { return tolower(c); }", subject)
    seed = build_seed(context)
    assert seed["Stubs"] == [{"StubFunctionSig": "int tolower(int c)", "Effects": []}]


def test_parse_individual_or_array_cases():
    case = {"Inputs": [], "Outputs": [], "Stubs": []}
    assert parse_cases(json.dumps(case)) == [case]
    assert parse_cases("```json\n" + json.dumps([case]) + "\n```") == [case]


def test_parse_cases_repairs_c_style_escapes_without_touching_valid_ones():
    # Observed live-model behavior: a deliberate embedded-null or raw-byte
    # probe rendered with C string-literal syntax (\0, \xHH) instead of
    # JSON's, which is otherwise an unrecoverable JSONDecodeError.
    raw = (
        '[{"Inputs": [{"ExprInput": "s", "Type": "const char *", '
        '"Value": "A\\0B\\xffZ\\n"}], "Outputs": [], "Stubs": []}]'
    )
    [case] = parse_cases(raw)
    assert case["Inputs"][0]["Value"] == "A\x00B\xffZ\n"


def test_rule_translator_compiles_runs_and_covers(tmp_path: Path):
    cases = [
        {
            "Inputs": [
                {"ExprInput": "value", "Type": "int", "Value": 8},
                {"ExprInput": "upper", "Type": "int", "Value": 8},
            ],
            "Outputs": [{"ExprOutput": "return", "Type": "int", "Value": 0}],
            "Stubs": [],
        },
        {
            "Inputs": [
                {"ExprInput": "value", "Type": "int", "Value": 9},
                {"ExprInput": "upper", "Type": "int", "Value": 8},
            ],
            "Outputs": [{"ExprOutput": "return", "Type": "int", "Value": 1}],
            "Stubs": [],
        },
    ]
    result = evaluate(SUBJECT, SOURCE, translate_cases(SUBJECT, cases), tmp_path)
    assert result.status == "passed", result.error
    assert result.line_covered > 0
    assert result.branch_total > 0


def test_translator_undefs_focal_name_that_collides_with_a_libc_macro(tmp_path: Path):
    # Recent glibc/gcc redeclares several pointer-returning string/mem
    # functions (strchr, strpbrk, strstr, memchr, rawmemchr, ...) as a
    # `_Generic`-dispatching macro for const-correctness once a C23-capable
    # compiler is in use, so redefining the same name after
    # `#include <string.h>` without `#undef` is a real "expected identifier
    # or '(' before '_Generic'" compile error against the *system* header
    # (unrelated to the toy SOURCE below, which is why this must go through
    # the real `evaluate()`/gcc path rather than only exercising translate).
    subject = Subject("strchr", "char *", (("const char *", "string", "s"), ("int", "char_code", "c")))
    source = "char *strchr(const char *s, int c) {\n  for (; *s; s++) if (*s == c) return (char *)s;\n  return c == 0 ? (char *)s : 0;\n}\n"
    cases = [
        {
            "Inputs": [
                {"ExprInput": "s", "Type": "const char *", "Value": "abc"},
                {"ExprInput": "c", "Type": "int", "Value": 98},
            ],
            "Outputs": [{"ExprOutput": "return_offset:s", "Type": "char *", "Value": 1}],
            "Stubs": [],
        },
    ]
    result = evaluate(subject, source, translate_cases(subject, cases), tmp_path)
    assert result.status == "passed", result.error


def test_translator_normalizes_return_offset_kept_under_plain_return():
    # Observed live-model behavior on every pointer-returning subject: the
    # base/offset is encoded inside Value ("return_offset:s1+3",
    # "return_offset:s1:3", or a bare null for NULL) while ExprOutput stays
    # "return", instead of the documented ExprOutput "return_offset:<base>".
    subject = Subject("strchr", "char *", (("const char *", "string", "s"), ("int", "char_code", "c")))
    cases = [
        {
            "Inputs": [{"ExprInput": "s", "Type": "const char *", "Value": "abc"}, {"ExprInput": "c", "Type": "int", "Value": 98}],
            "Outputs": [{"ExprOutput": "return", "Type": "char *", "Value": "return_offset:s+1"}],
            "Stubs": [],
        },
        {
            "Inputs": [{"ExprInput": "s", "Type": "const char *", "Value": "abc"}, {"ExprInput": "c", "Type": "int", "Value": 122}],
            "Outputs": [{"ExprOutput": "return", "Type": "char *", "Value": None}],
            "Stubs": [],
        },
    ]
    code = translate_cases(subject, cases)
    assert "c0_return - (const unsigned char *)c0_s == 1" in code
    assert "c1_return == NULL" in code


def test_coverage_prefers_focal_file_when_header_has_same_symbol(tmp_path: Path):
    source = "#include <string.h>\n#undef strcmp\nint strcmp(const char *a, const char *b) { while (*a && *a == *b) { a++; b++; } return (unsigned char)*a - (unsigned char)*b; }\n"
    subject = Subject("strcmp", "int", (("const char *", "string", "a"), ("const char *", "string", "b")))
    case = {"Inputs": [
        {"ExprInput": "a", "Type": "const char *", "Value": "ab"},
        {"ExprInput": "b", "Type": "const char *", "Value": "ab"},
    ], "Outputs": [{"ExprOutput": "return", "Type": "int", "Value": 0}], "Stubs": []}
    result = evaluate(subject, source, translate_cases(subject, [case]), tmp_path)
    assert result.status == "passed"
    assert result.line_total >= 1
    assert result.branch_total >= 2


def test_translator_encodes_high_byte_string_values_as_single_bytes(tmp_path: Path):
    # A JSON code point in U+0080..U+00FF must become one raw C byte, not the
    # UTF-8 expansion GCC applies to a \u00XX universal-character-name inside
    # a narrow string literal (this previously made high-byte strcmp oracles
    # fail even though the model's Inputs/Outputs were correct).
    subject = Subject("strcmp", "int", (("const char *", "string", "a"), ("const char *", "string", "b")))
    source = "int strcmp(const char *a, const char *b) { return (unsigned char)*a - (unsigned char)*b; }\n"
    case = {
        "Inputs": [
            {"ExprInput": "a", "Type": "const char *", "Value": "ÿ"},
            {"ExprInput": "b", "Type": "const char *", "Value": "\u0001"},
        ],
        "Outputs": [{"ExprOutput": "return", "Type": "int", "Value": 254}],
        "Stubs": [],
    }
    harness = translate_cases(subject, [case])
    assert "\\377" in harness and "\\u00ff" not in harness
    result = evaluate(subject, source, harness, tmp_path)
    assert result.status == "passed", result.error


def test_translator_rejects_narrow_string_values_above_one_byte():
    case = {
        "Inputs": [
            {"ExprInput": "a", "Type": "const char *", "Value": "Ā"},
            {"ExprInput": "b", "Type": "const char *", "Value": ""},
        ],
        "Outputs": [{"ExprOutput": "return", "Type": "int", "Value": 0}],
        "Stubs": [],
    }
    subject = Subject("strcmp", "int", (("const char *", "string", "a"), ("const char *", "string", "b")))
    try:
        translate_cases(subject, [case])
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_translator_rejects_expression_injection():
    case = {
        "Inputs": [
            {"ExprInput": "value", "Type": "int", "Value": "system(\"oops\")"},
            {"ExprInput": "upper", "Type": "int", "Value": 1},
        ],
        "Outputs": [{"ExprOutput": "return", "Type": "int", "Value": 0}],
        "Stubs": [],
    }
    try:
        translate_cases(SUBJECT, [case])
    except ValueError as exc:
        assert "JSON number" in str(exc)
    else:
        raise AssertionError("unsafe expression was accepted")


def test_rule_translator_dispatches_path_specific_stub_effects(tmp_path: Path):
    subject = Subject("use_dep", "int", (("int", "integer", "x"),))
    source = "int dep(int x);\nint use_dep(int x) { return dep(x) + 1; }\n"
    cases = []
    for x, stub_value, expected in ((2, 3, 4), (9, -2, -1)):
        cases.append({
            "Inputs": [{"ExprInput": "x", "Type": "int", "Value": x}],
            "Outputs": [{"ExprOutput": "return", "Type": "int", "Value": expected}],
            "Stubs": [{
                "StubFunctionSig": "int dep(int x)",
                "Effects": [{"ExprOutput": "return", "Type": "int", "Value": stub_value}],
            }],
        })
    result = evaluate(subject, source, translate_cases(subject, cases), tmp_path)
    assert result.status == "passed", result.error


def test_paired_statistics_keep_pairing_and_ties():
    rows = []
    for subject, left, right in (("a", 1, 0), ("b", 1, 1), ("c", 0, 1)):
        for arm, passed in (("extended", left), ("strut", right)):
            rows.append({"subject": subject, "arm": arm, "evaluation": {
                "status": "passed" if passed else "runtime_failure",
                "line_covered": passed, "line_total": 1,
                "branch_covered": passed, "branch_total": 1,
            }})
    result = compare(rows, "extended", "strut", "pass")
    assert (result["wins"], result["ties"], result["losses"]) == (1, 1, 1)
    assert result["mean_difference"] == 0
    assert exact_sign_p([1, 0, -1]) == 1.0
