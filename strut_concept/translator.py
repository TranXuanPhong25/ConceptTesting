"""Rule-based conversion of structured test cases to executable C."""

from __future__ import annotations

import json
import re
from typing import Any

from .benchmark import Subject


STUB_SIGNATURE_RE = re.compile(
    r"^\s*(?P<return>void|int|long|long long|size_t|wint_t|wchar_t|char\s*\*|void\s*\*)\s+"
    r"(?P<name>[A-Za-z_]\w*)\s*\((?P<params>[^()]*)\)\s*$"
)


def parse_cases(raw: str) -> list[dict[str, Any]]:
    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.I | re.S)
    if fenced:
        text = fenced.group(1).strip()
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        objects = re.findall(r"\{(?:[^{}]|\{[^{}]*\})*\}", text, re.S)
        value = [json.loads(item) for item in objects]
    if isinstance(value, dict):
        value = value.get("cases", [value])
    if not isinstance(value, list) or not value:
        raise ValueError("model output contains no structured cases")
    return value


def _c_string(value: Any, wide: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError("string input Value must be JSON string")
    literal = json.dumps(value, ensure_ascii=True)
    return ("L" if wide else "") + literal


def _integer(value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("numeric input Value must be a JSON number")
    if isinstance(value, float) and not value.is_integer():
        raise ValueError("integer Value cannot be fractional")
    return str(int(value))


def _input_map(case: dict[str, Any], subject: Subject) -> dict[str, dict[str, Any]]:
    inputs = case.get("Inputs")
    if not isinstance(inputs, list):
        raise ValueError("Inputs must be an array")
    mapped = {item.get("ExprInput"): item for item in inputs if isinstance(item, dict)}
    expected = {name for _, _, name in subject.parameters}
    if set(mapped) != expected:
        raise ValueError(f"Inputs expressions must equal {sorted(expected)}")
    for typ, _, name in subject.parameters:
        if mapped[name].get("Type") != typ:
            raise ValueError(f"Type mismatch for {name}")
    if not isinstance(case.get("Outputs"), list) or not isinstance(case.get("Stubs"), list):
        raise ValueError("Outputs and Stubs must be arrays")
    return mapped


def _stub_return(stub: dict[str, Any], return_type: str) -> str:
    effects = stub.get("Effects", [])
    if not isinstance(effects, list):
        raise ValueError("Stub Effects must be an array")
    returns = [effect for effect in effects if isinstance(effect, dict) and effect.get("ExprOutput") == "return"]
    if return_type == "void":
        return ""
    if not returns:
        return "NULL" if "*" in return_type else "0"
    value = returns[-1].get("Value")
    if "*" in return_type:
        if value is not None:
            raise ValueError("stub pointer returns currently support only null")
        return "NULL"
    return _integer(value)


def _render_stubs(cases: list[dict[str, Any]], focal_name: str) -> list[str]:
    grouped: dict[str, tuple[re.Match[str], dict[int, str]]] = {}
    for index, case in enumerate(cases):
        stubs = case.get("Stubs")
        if not isinstance(stubs, list):
            raise ValueError("Stubs must be an array")
        for stub in stubs:
            if not isinstance(stub, dict):
                raise ValueError("each Stub must be an object")
            signature = stub.get("StubFunctionSig", "")
            match = STUB_SIGNATURE_RE.fullmatch(signature) if isinstance(signature, str) else None
            if not match:
                # A bare callee name is valid seed metadata but cannot safely be
                # synthesized without its interface. It remains linked normally.
                if isinstance(signature, str) and re.fullmatch(r"[A-Za-z_]\w*", signature):
                    continue
                raise ValueError(f"unsafe or unsupported StubFunctionSig {signature!r}")
            if match.group("name") == focal_name:
                raise ValueError("a stub cannot redefine the focal function")
            canonical = " ".join(signature.split())
            if canonical not in grouped:
                grouped[canonical] = (match, {})
            grouped[canonical][1][index] = _stub_return(stub, match.group("return"))
    if not grouped:
        return []
    lines = ["static int strut_case_index = 0;", ""]
    for signature, (match, values) in grouped.items():
        params = match.group("params").strip()
        lines.append(signature + " {")
        if params and params != "void":
            for param in params.split(","):
                name_match = re.search(r"([A-Za-z_]\w*)\s*$", param.strip())
                if not name_match:
                    raise ValueError(f"stub parameter needs a name: {param!r}")
                lines.append(f"  (void){name_match.group(1)};")
        if match.group("return") != "void":
            lines.append("  switch (strut_case_index) {")
            for index, value in sorted(values.items()):
                lines.append(f"    case {index}: return ({match.group('return')})({value});")
            lines.append("    default: return (" + match.group("return") + ")0;")
            lines.append("  }")
        lines.extend(["}", ""])
    return lines


def translate_cases(subject: Subject, cases: list[dict[str, Any]]) -> str:
    lines = [
        "#define _GNU_SOURCE 1", "#include <stddef.h>", "#include <stdint.h>",
        "#include <stdlib.h>", "#include <string.h>", "#include <wchar.h>",
        "#include <wctype.h>", "#include <locale.h>", "",
        subject.return_type + " " + subject.name + "(" + ", ".join(typ + " " + name for typ, _, name in subject.parameters) + ");",
        "",
    ]
    stub_lines = _render_stubs(cases, subject.name)
    lines.extend(stub_lines)
    lines.extend(["int main(void) {", "  int failures = 0;",
        "  (void)setlocale(LC_ALL, \"C\");",
    ])
    for index, case in enumerate(cases):
        mapped = _input_map(case, subject)
        lines.append(f"  /* case {index} */")
        arg_names: list[str] = []
        base_by_name: dict[str, str] = {}
        for typ, kind, name in subject.parameters:
            var = f"c{index}_{name}"
            value = mapped[name].get("Value")
            if kind == "string":
                lines.append(f"  const char *{var} = {_c_string(value)};")
            elif kind == "wstring":
                lines.append(f"  const wchar_t *{var} = {_c_string(value, True)};")
            elif kind == "bytes":
                lines.append(f"  const unsigned char {var}_data[] = {_c_string(value)};")
                lines.append(f"  const void *{var} = {var}_data;")
                base_by_name[name] = f"{var}_data"
            elif kind == "char_buffer":
                lines.append(f"  char {var}[256] = {_c_string(value)};")
            elif kind == "wide_char":
                if isinstance(value, str) and len(value) == 1:
                    lines.append(f"  wchar_t {var} = {_c_string(value, True)}[0];")
                else:
                    lines.append(f"  wchar_t {var} = (wchar_t){_integer(value)};")
            else:
                lines.append(f"  {typ} {var} = ({typ}){_integer(value)};")
            arg_names.append(var)
            if kind in {"string", "wstring", "char_buffer"}:
                base_by_name[name] = var
        ret = f"c{index}_return"
        if stub_lines:
            lines.append(f"  strut_case_index = {index};")
        lines.append(f"  {subject.return_type} {ret} = {subject.name}({', '.join(arg_names)});")
        for output in case["Outputs"]:
            if not isinstance(output, dict):
                raise ValueError("each Output must be an object")
            expr, value = output.get("ExprOutput"), output.get("Value")
            if expr == "return":
                lines.append(f"  failures += !({ret} == ({subject.return_type}){_integer(value)});")
            elif isinstance(expr, str) and expr.startswith("return_offset:"):
                base_name = expr.split(":", 1)[1]
                if base_name not in base_by_name:
                    raise ValueError(f"unknown pointer-offset base {base_name}")
                if value is None:
                    lines.append(f"  failures += !({ret} == NULL);")
                else:
                    lines.append(f"  failures += !((const unsigned char *){ret} - (const unsigned char *){base_by_name[base_name]} == {_integer(value)});")
            elif expr in base_by_name:
                lines.append(f"  failures += !(strcmp({base_by_name[expr]}, {_c_string(value)}) == 0);")
            else:
                raise ValueError(f"unsupported ExprOutput {expr!r}")
    lines.extend(["  return failures ? 1 : 0;", "}", ""])
    return "\n".join(lines)


def clean_c_output(raw: str) -> str:
    text = raw.strip()
    fenced = re.search(r"```(?:c)?\s*(.*?)```", text, re.I | re.S)
    return (fenced.group(1) if fenced else text).strip() + "\n"
