"""Offline tests for codehacker_concept (no LLM, no network)."""

from __future__ import annotations

import pytest

from codehacker_concept.analyst import parse_call
from codehacker_concept.autocode import normalize_input, signature
from codehacker_concept.llm import extract_code, extract_json
from codehacker_concept.metrics import mcnemar_exact, paired_compare, wilson_ci
from codehacker_concept.prompts import render
from codehacker_concept.tlocal import parse_generator_cmds


def test_parse_call_triple_quoted():
    text = 'Thought: probe.\nCall: run_cpp("""3\n1 2 3\n""")'
    call = parse_call(text)
    assert call is not None and call.name == "run_cpp" and call.argument == "3\n1 2 3\n"


def test_parse_call_finish_and_last_wins():
    text = 'Call: run_python("print(1)")\nThen finally Call: finish("done")'
    call = parse_call(text)
    assert call.name == "finish" and call.argument == "done"


def test_parse_call_none():
    assert parse_call("no tool here") is None


def test_extract_json_fenced_and_comment():
    text = 'blah\n```json\n{"a": 1, // note\n "b": [1,2]}\n```'
    assert extract_json(text) == {"a": 1, "b": [1, 2]}


def test_extract_code_prefers_main():
    text = "```cpp\nint helper(){}\n```\n```cpp\n#include <bits/stdc++.h>\nint main(){}\n```"
    assert "main" in extract_code(text)


def test_render_missing_placeholder():
    with pytest.raises(ValueError):
        render("{{a}} {{b}}", a=1)


def test_normalize_and_signature():
    assert normalize_input("1 2") == "1 2\n"
    assert signature("1  2\n") == signature("1 2")


def test_generator_cmds():
    cmds = parse_generator_cmds("./gen -n 1 -type random\n\n./gen -n 5 > $\n")
    assert cmds == [["-n", "1", "-type", "random"], ["-n", "5"]]


def test_mcnemar_and_paired():
    assert mcnemar_exact(0, 0) == 1.0
    assert mcnemar_exact(0, 6) < 0.05
    out = paired_compare([True, False, False, True], [True, True, True, True], n_boot=200)
    assert out["b_only"] == 2 and out["a_only"] == 0 and out["diff_b_minus_a"] == 0.5


def test_wilson_bounds():
    lo, hi = wilson_ci(5, 10)
    assert 0 < lo < 0.5 < hi < 1


def test_sandbox_verdicts(tmp_path, monkeypatch):
    import shutil

    if shutil.which("g++") is None:
        pytest.skip("g++ unavailable")
    monkeypatch.setenv("CH_DATA_DIR", str(tmp_path))
    from codehacker_concept.sandbox import run_cpp_source

    ok = run_cpp_source("#include <cstdio>\nint main(){int a,b;scanf(\"%d%d\",&a,&b);printf(\"%d\\n\",a+b);}", "2 3\n")
    assert ok.status == "OK" and ok.stdout.strip() == "5"
    re_ = run_cpp_source("int main(){return 3;}", "")
    assert re_.status == "RE"
    tle = run_cpp_source("int main(){volatile unsigned long x=0;for(;;)x++;}", "", time_limit_ms=300)
    assert tle.status == "TLE"
