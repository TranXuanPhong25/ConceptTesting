"""Original-V11 parity and native kernel engineering fixtures; no endpoint calls."""

import ast
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from final.v11_clean_runtimefix.arm import V11HybridStage, V11RoundOneStage
from final.v11_clean_runtimefix.context import V11Context
from final.v11_clean_runtimefix.cohort import V11ProgramView
from final.v11_clean_runtimefix.sandbox import V11Sandbox
from trickcatcher_linefacts.pipelines.v11_fair import (
    v4_prompts,
    gen_prompts,
    prompts,
    fair_generation,
)
from trickcatcher_linefacts.pipelines.v11_fair import test_fair as original_fixtures


class FakeCalls:
    def __init__(self, count=1):
        self.client = original_fixtures.FakeClient(count)

    def complete(self, messages, seed, **kwargs):
        return self.client.chat(messages, seed, **kwargs)


class FakeSandbox:
    def __init__(self, good=True, failed_concept=False, covered_placebo=False):
        self.good = good
        self.failed_concept = failed_concept
        self.covered_placebo = covered_placebo

    def execute(self, job, directory, timeout=600):
        if job["mode"] == "draw":
            if self.failed_concept and "concept-hybrid" in str(directory):
                raise ValueError("fake verification rejection")
            return dict(candidates=[], nonliteral=0, wrong_arity=0, errors=[])
        assert job["mode"] == "classify"
        shown = job.get("shown", [])
        records = (
            []
            if "assertions" in job
            else [
                dict(
                    input_repr="(100,)",
                    call="f(100)",
                    valid=self.good,
                    shown_hits=[self.good] * len(shown),
                ),
                dict(
                    input_repr="(101,)",
                    call="f(101)",
                    valid=self.good,
                    shown_hits=[self.good] * len(shown),
                ),
            ]
        )
        hits = [int(self.covered_placebo and "placebo-hybrid" in str(directory))] * len(
            shown
        )
        return dict(
            records=records,
            summary=dict(
                shown_hit_counts=hits,
                valid=sum(record["valid"] for record in records),
                removed=0,
            ),
        )


@pytest.mark.parametrize(
    "good,failed_concept,covered_placebo,count",
    [
        (True, False, False, 1),
        (False, False, False, 1),
        (True, True, False, 1),
        (True, False, True, 1),
        (True, False, False, 25),
    ],
)
def test_original_v11_hybrid_generation_selection_and_request_parity(
    tmp_path, good, failed_concept, covered_placebo, count
):
    original = original_fixtures.FairTests()
    original.setUp()
    try:
        expected, original_client = original.generate(
            n_assertions=count,
            good=good,
            failed_concept=failed_concept,
            covered_placebo=covered_placebo,
        )
    finally:
        original.doCleanups()
    task = original_fixtures.task()
    context = V11Context(
        task,
        {},
        dict(id=0),
        tmp_path,
        FakeCalls(count),
        FakeSandbox(good, failed_concept, covered_placebo),
        bundle=task,
    )
    first = V11RoundOneStage()
    hybrid = V11HybridStage()
    actual = {}
    actual["concept-hybrid"] = hybrid.run(
        context, "concept-hybrid", first.run(context, "concept-hybrid")
    )
    for arm in ("plain-hybrid", "placebo-hybrid"):
        actual[arm] = hybrid.run(
            context,
            arm,
            first.run(context, arm),
            actual["concept-hybrid"]["round2_strategy_requests"],
        )
    for arm, record in actual.items():
        for key in (
            "assertions",
            "round1_assertions",
            "round2_strategy_requests",
            "strict_missing_expected",
            "missed_fact_indices",
            "llm_calls",
            "dropped_assertions",
        ):
            assert record[key] == expected[arm][key], (arm, key)
        expected_selected = [row["call"] for row in expected[arm]["selected_inputs"]]
        actual_selected = [
            row["call"]
            for attempt in record["generator_attempts"]
            for row in attempt["selected"]
        ]
        assert set(actual_selected) >= set(expected_selected)
        assert record["llm_calls"] <= 8
        assert len(record["assertions"]) <= 20


def test_program_view_restores_metadata_preserves_body_and_future_import():
    he = dict(
        prompt='from typing import List\ndef f(values: List[int]) -> int:\n    """Return the total."""\n',
        entry_point="f",
    )
    raw = "from __future__ import annotations\ndef f(items):\n    return sum(items)\n"
    view = V11ProgramView().build(he, dict(code=raw))
    compile(view, "<view>", "exec")
    before = next(
        node for node in ast.parse(raw).body if isinstance(node, ast.FunctionDef)
    )
    after = next(
        node for node in ast.parse(view).body if isinstance(node, ast.FunctionDef)
    )
    assert ast.dump(before.body[0]) == ast.dump(after.body[1])
    assert after.args.args[0].arg == "items"
    assert ast.get_docstring(after) == "Return the total."
    assert ast.unparse(after.args.args[0].annotation) == "List[int]"


def test_pinned_native_strategy_and_fact_kernels(tmp_path):
    sandbox = V11Sandbox()
    source = 'def f(x: int) -> int:\n    """Return x plus one."""\n    return x+1\n'
    task = dict(
        task=0,
        entry="f",
        put=source,
        base="def check(candidate): assert candidate(1)==2",
        mined_valid_src="def valid(x): return isinstance(x,int)",
        strategy_src="def strategy():\n    return st.sampled_from([(1,),(2,),(0,)])\n",
    )
    he = dict(
        prompt='def f(x: int) -> int:\n    """Return x plus one."""\n',
        entry_point="f",
        test=task["base"],
    )
    result = sandbox.execute(
        dict(mode="facts", task=task, he=he), tmp_path / "facts", timeout=120
    )
    assert result["base_ok"] is True
    assert result["facts_version"] == "v4"
    assert result["n_points"] > 0
    assert result["tools"] == {
        "hypothesis": "6.169.0",
        "mutmut": "3.8.0",
        "coverage": "7.16.2",
        "libcst": "1.9.0",
    }
    again = sandbox.execute(
        dict(mode="facts", task=task, he=he), tmp_path / "facts", timeout=120
    )
    assert again == result


def test_gold_evaluation_uses_raw_owner_source_and_reference_not_llm_expected(tmp_path):
    from final.v11_clean_runtimefix.evaluation import V11ReferenceEvaluationStage

    human_eval = dict(
        task_id="HumanEval/0",
        entry_point="f",
        prompt='def f(x: int) -> int:\n    """Return x plus one."""\n',
        canonical_solution="    return x+1\n",
    )
    program = dict(
        id=0, code="def f(x):\n    return 0 if x<0 else x+1\n", base=dict(input_keys=[])
    )
    context = V11Context(
        dict(task=0, put="def f(x): return x+1"),
        human_eval,
        program,
        tmp_path,
        None,
        None,
        arm_results={
            "v11_concept": dict(
                inputs=[dict(input_repr="(-2,)", valid=True)],
                assertions=["assert f(-2)==999"],
                llm_calls=1,
            ),
            "v11_plain": dict(
                inputs=[dict(input_repr="(3,)", valid=True)], llm_calls=1
            ),
        },
    )
    result = V11ReferenceEvaluationStage().run(
        context, dict(contract="\n    assert type(x)==int\n", atol=0)
    )
    assert result["arms"]["v11_concept"]["detected"] is True
    assert result["arms"]["v11_plain"]["detected"] is False
    assert result["tests"][0]["expected"] == "-1"


def test_bridge_failure_is_an_explicit_case_failure(tmp_path):
    from final.v11_clean_runtimefix.run import V11BenchmarkRunner

    runner = V11BenchmarkRunner.__new__(V11BenchmarkRunner)
    runner.directory = tmp_path
    runner.calls = None
    runner.sandbox = None
    human_eval = dict(
        task_id="HumanEval/0",
        entry_point="missing",
        prompt='def missing(x):\n    """Return x."""\n',
        test="def check(candidate): pass",
    )
    program = dict(id=0, code="def f(x):return x", base=dict(status="pass"))
    result = runner.one_case((0, human_eval, program))
    assert result["state"] == "preparation_or_execution_failed"
    assert result["error_type"] == "StopIteration"


def test_original_top_p_is_forwarded_by_streaming_adapter(monkeypatch):
    from final.v11_clean_runtimefix.model_calls import V11Model, TOP_P
    from final.experiments.concept_reference_v1_recovery.model import QwenModel

    monkeypatch.setattr(
        QwenModel, "request", lambda self, operation, body=None, **keywords: body
    )
    model = V11Model.__new__(V11Model)
    token = TOP_P.set(0.83)
    try:
        assert model.request("completion", dict(stream=True))["top_p"] == 0.83
    finally:
        TOP_P.reset(token)
