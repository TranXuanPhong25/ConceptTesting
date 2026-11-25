"""Offline unit tests for 4-tool prior-input loading and ControlFlowFourToolArm (0 LLM calls)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from final.src.models.core_model import ModelResponse
from final.src.modular.arm_names import ANALYSIS_FAMILY_COUNTS, generation_call_cap, retained_input_budget
from final.src.modular.arms import available_arms, selected_arms
from final.src.modular.arms.control_flow import ControlFlowArm, ControlFlowFourToolArm, ControlFlowSettings
from final.src.modular.artifacts import ArtifactStore
from final.src.modular.catalogue_reporting import usage_by_arm
from final.src.modular.context import PipelineSettings, TaskContext
from final.src.modular.control_flow.tool_inputs import (
    FOUR_TOOLS,
    compact_prompt_prior_inputs,
    default_tool_runs_dir,
    load_four_tool_prior_inputs,
)
from final.src.modular import run as modular_run
from final.src.orchestration import config, names, worker
from final.src.runtime.execution import ExecutionError

SOURCE = '''def f(xs: list[int], k: int):
    if k < 1:
        return False
    unique = set(xs)
    count = len(unique)
    if count == k:
        return True
    return False
'''
SPEC = 'def f(xs: list[int], k: int):\n    """Return whether the number of distinct integers in xs equals k."""\n'


def _program(source=SOURCE):
    return {
        "id": "p0",
        "code": source,
        "base": {
            "status": "pass",
            "calls": [{"args": "([1, 1], 2)", "kwargs": "{}"}],
            "coverage": {
                "lines": [1, 2, 4, 5, 6, 8],
                "arcs": [[-1, 2], [2, 4], [4, 5], [5, 6], [6, 8], [8, -1]],
            },
        },
    }


def _context(tmp_path, calls=None, *, contract="", context_tokens=40960, input_tokens=8192):
    return TaskContext(
        {"task_id": "HumanEval/0", "entry_point": "f", "prompt": SPEC, "test": ""},
        {"contract": contract},
        ArtifactStore(tmp_path),
        PipelineSettings(input_budget=4, input_tokens=input_tokens, context_tokens=context_tokens),
        calls,
        cohort_task={"generated": 1, "programs": [_program()]},
        packet={"visible_put_ids": ["p0"], "common": ""},
    )


def _write_receipt(root: Path, task_num: int, put_id: str, tool: str, calls: list[dict], *, base="pass"):
    path = root / "tasks" / str(task_num) / put_id / tool / "receipt.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "task_id": f"HumanEval/{task_num}",
        "put": put_id,
        "tool": tool,
        "base": base,
        "calls": calls,
    }))


def test_loader_is_strictly_oracle_free_excludes_klara_dedups_and_balances_round_robin(tmp_path):
    runs_dir = tmp_path / "tools"
    task_dir = runs_dir / "tasks" / "0"
    task_dir.mkdir(parents=True)
    # Invalid JSON in oracle_replay.json proves the loader NEVER opens it.
    (task_dir / "oracle_replay.json").write_text("{CORRUPT_ORACLE_MUST_NEVER_BE_READ")

    _write_receipt(runs_dir, 0, "0", "klara", [{"args": "([99], 1)", "kwargs": "{}"}])
    _write_receipt(runs_dir, 0, "0", "crosshair", [
        {"args": "([1, 1], 2)", "kwargs": "{}"},  # base duplicate -> skip
        {"args": "([1], 'bad_int')", "kwargs": "{}"},  # type mismatch -> invalid_signature
        {"args": "([], 0)", "kwargs": "{}"},
        {"args": "([2, 3], 2)", "kwargs": "{}"},
    ])
    _write_receipt(runs_dir, 0, "0", "pynguin", [
        {"args": "([], 0)", "kwargs": "{}"},  # duplicate of crosshair -> merge tool provenance
        {"args": "([10], 1)", "kwargs": "{}"},
    ])
    _write_receipt(runs_dir, 0, "0", "utbot", [
        {"args": f"([{i}], 3)", "kwargs": "{}"} for i in range(5)
    ])
    _write_receipt(runs_dir, 0, "0", "ghostwriter", [
        {"args": "([7, 8, 9], 3)", "kwargs": "{}"},
    ])
    # Base-failing PUT receipt must be ignored.
    _write_receipt(runs_dir, 0, "1", "crosshair", [{"args": "([42], 1)", "kwargs": "{}"}], base="fail")

    task = {"task_id": "HumanEval/0", "entry_point": "f", "prompt": SPEC}
    loaded = load_four_tool_prior_inputs(
        task,
        {"contract": ""},
        [_program()],
        tool_runs_dir=runs_dir,
        max_prior_inputs=5,
    )
    stats = loaded["stats"]
    assert stats["tools"] == list(FOUR_TOOLS)
    assert stats["base_duplicates_skipped"] == 1
    assert stats["invalid_signature"] == 1
    assert stats["domain_checked"] is False
    assert stats["selected"] == 5

    # Klara and base-failing inputs never enter.
    args_list = [row["args"] for row in loaded["inputs"]]
    assert "([99], 1)" not in args_list
    assert "([42], 1)" not in args_list
    # Round-robin across the 4 tools guarantees all 4 tools appear within limit=5!
    stages = [row["source_stage"] for row in loaded["inputs"]]
    assert set(stages) == {"tool4:crosshair", "tool4:pynguin", "tool4:utbot", "tool4:ghostwriter"}
    # Duplicate between crosshair and pynguin kept merged tool provenance.
    merged = next(row for row in loaded["inputs"] if row["args"] == "([], 0)")
    assert merged["tools"] == ["crosshair", "pynguin"]


def test_loader_domain_validation_and_infrastructure_error_fail_fast(tmp_path, monkeypatch):
    import final.src.modular.control_flow.tool_inputs as module

    runs_dir = tmp_path / "tools"
    _write_receipt(runs_dir, 0, "0", "crosshair", [
        {"args": "([1], 1)", "kwargs": "{}"},
        {"args": "([], -5)", "kwargs": "{}"},
    ])
    task = {"task_id": "HumanEval/0", "entry_point": "f", "prompt": SPEC}

    loaded = load_four_tool_prior_inputs(
        task,
        {"contract": "\n    assert k >= 0\n"},
        [_program()],
        tool_runs_dir=runs_dir,
        validator=lambda t, c, cands, **kw: [
            {"status": "valid" if row["args"] == "([1], 1)" else "invalid_domain"}
            for row in cands
        ],
    )
    assert loaded["stats"]["domain_checked"] is True
    assert loaded["stats"]["domain_rejected"] == 1
    assert [row["args"] for row in loaded["inputs"]] == ["([1], 1)"]

    # bwrap infrastructure failure MUST raise ExecutionError rather than silently dropping candidates.
    def failing_execute(job):
        raise ExecutionError("Sandbox infrastructure exited 1: bwrap: Creating new namespace failed")

    monkeypatch.setattr(module, "execute", failing_execute)
    with pytest.raises(ExecutionError, match="bwrap"):
        load_four_tool_prior_inputs(
            task,
            {"contract": "\n    assert k >= 0\n"},
            [_program()],
            tool_runs_dir=runs_dir,
        )


def test_compact_prompt_prior_inputs_caps_count_and_skips_oversized_calls():
    raw = [
        {"input_id": f"tool4_{i}", "source_stage": f"tool4:{FOUR_TOOLS[i % 4]}",
         "args": f"([{i}], 1)", "kwargs": "{}"}
        for i in range(24)
    ]
    raw.insert(0, {
        "input_id": "tool4_huge",
        "source_stage": "tool4:utbot",
        "args": f"({'x' * 400!r}, 1)",
        "kwargs": "{}",
    })
    compact, summary = compact_prompt_prior_inputs(raw, limit=8)
    assert len(compact) == 8
    assert summary["total_prior_inputs"] == 25
    assert summary["shown_examples"] == 8
    assert summary["omitted_from_prompt"] == 17
    assert all(row["input_id"] != "tool4_huge" for row in compact)
    assert len({row["source_stage"] for row in compact}) == 4


def test_control_flow_4tool_closes_covered_tasks_with_zero_llm_calls(tmp_path, monkeypatch):
    runs_dir = tmp_path / "tools"
    _write_receipt(runs_dir, 0, "0", "crosshair", [
        {"args": "([], 0)", "kwargs": "{}"},
        {"args": "([1, 2], 2)", "kwargs": "{}"},
    ])

    class ForbidCalls:
        def token_count(self, messages):
            raise AssertionError("Should not tokenize when 4 tools close all C1/C2 targets")

        def complete(self, *args, **kwargs):
            raise AssertionError("Should not invoke LLM when 4 tools close all C1/C2 targets")

    arm = ControlFlowFourToolArm(tool_runs_dir=runs_dir)

    def fake_trace(ctx, program, records):
        out = []
        for rec in records:
            if rec["args"] == "([], 0)":
                out.append({"domain": "valid", "status": "executed", "coverage": {
                    "lines": [1, 2, 3], "arcs": [[-1, 2], [2, 3], [3, -1]],
                }})
            else:
                out.append({"domain": "valid", "status": "executed", "coverage": {
                    "lines": [1, 2, 4, 5, 6, 7], "arcs": [[-1, 2], [2, 4], [4, 5], [5, 6], [6, 7], [7, -1]],
                }})
        return out

    monkeypatch.setattr(arm, "trace", fake_trace)
    ctx = _context(tmp_path / "run", calls=ForbidCalls())
    ctx.extensions["keep_me"] = "unchanged"
    result = arm.run(ctx)

    assert result["status"] == "no_measured_gaps"
    assert result["inputs"] == []
    assert result["rounds"] == []
    assert result["tool4_prior_summary"]["base_targets_before_4tool"] == 4
    assert result["tool4_prior_summary"]["residual_targets_after_4tool"] == 0
    assert result["tool4_prior_summary"]["targets_eliminated_by_4tool"] == 4
    assert result["tool4_prior_summary"]["closed_by_4tool"] is True
    # Parent extensions must never be mutated.
    assert ctx.extensions == {"keep_me": "unchanged"}


def test_control_flow_4tool_focuses_llm_on_residual_targets_caps_prompt_and_replays(tmp_path, monkeypatch):
    runs_dir = tmp_path / "tools"
    # 20 distinct 4-tool inputs covering ONLY the `k < 1` branch (line 3), leaving line 7 / arc [6, 7].
    for idx, tool in enumerate(FOUR_TOOLS):
        _write_receipt(runs_dir, 0, "0", tool, [
            {"args": f"([{idx * 10 + j}], 0)", "kwargs": "{}"} for j in range(5)
        ])

    class ResidualCalls:
        def __init__(self):
            self.payloads = []

        def token_count(self, messages):
            return 200

        def complete(self, task_number, call_name, messages, **kwargs):
            assert call_name.startswith("control_flow_4tool_round_")
            payload = json.loads(messages[-1]["content"])
            self.payloads.append(payload)
            target = next(t for t in payload["targets"] if t.get("arc") == [6, 7])
            raw = {
                "concepts": [{
                    "id": "distinct_eq",
                    "target_id": target["id"],
                    "name": "Distinct equals k",
                    "input_relation": "distinct_count(xs) == k",
                    "instruction": "Pass k distinct ints with k >= 1.",
                    "evidence_lines": [2, 4, 5, 6],
                    "predicate": "distinct_count(xs) == k and k >= 1",
                    "strategies": {},
                }],
                "inputs": [
                    # Repeat one 4-tool input (must be deduplicated) + one novel residual input!
                    {"arguments": {"xs": [0], "k": 0}, "concept_id": "distinct_eq"},
                    {"arguments": {"xs": [1, 2], "k": 2}, "concept_id": "distinct_eq"},
                ],
            }
            return ModelResponse(json.dumps(raw), finish_reason="stop")

    calls = ResidualCalls()
    arm = ControlFlowFourToolArm(
        ControlFlowSettings(rounds=1),
        tool_runs_dir=runs_dir,
        max_prompt_prior_inputs=6,
    )

    def fake_trace(ctx, program, records):
        out = []
        for rec in records:
            if ", 0)" in rec["args"]:
                out.append({"domain": "valid", "status": "executed", "coverage": {
                    "lines": [1, 2, 3], "arcs": [[-1, 2], [2, 3], [3, -1]],
                }})
            else:
                out.append({"domain": "valid", "status": "executed", "coverage": {
                    "lines": [1, 2, 4, 5, 6, 7], "arcs": [[-1, 2], [2, 4], [4, 5], [5, 6], [6, 7], [7, -1]],
                }})
        return out

    monkeypatch.setattr(arm, "trace", fake_trace)
    ctx = _context(tmp_path / "run", calls=calls)
    result = arm.run(ctx)

    assert len(calls.payloads) == 1
    payload = calls.payloads[0]
    # Only residual targets (line 7 and arc [6, 7]) sent to LLM — line 3 and arc [2, 3] eliminated!
    target_ids = {t["id"] for t in payload["targets"]}
    assert target_ids == {"p0:C1:7", "p0:C2:6:7"}
    # Prompt capped to 6 examples while summary records all 20 traced inputs!
    assert len(payload["prior_stage_inputs"]) == 6
    assert payload["prior_stage_summary"]["total_prior_inputs"] == 20
    assert payload["prior_stage_summary"]["omitted_from_prompt"] == 14
    # Prior duplicate ([0], 0) excluded; novel residual ([1, 2], 2) retained!
    assert [row["args"] for row in result["inputs"]] == ["([1, 2], 2)"]
    assert result["tool4_prior_summary"]["base_targets_before_4tool"] == 4
    assert result["tool4_prior_summary"]["residual_targets_after_4tool"] == 2
    assert result["tool4_prior_summary"]["targets_eliminated_by_4tool"] == 2
    assert result["tool4_prior_summary"]["closed_by_4tool"] is False

    # Read-only replay uses cached generation.json with zero calls.
    ctx.artifacts = ArtifactStore(tmp_path / "run", read_only=True)
    ctx.calls = None
    assert ControlFlowFourToolArm(tool_runs_dir=runs_dir).run(ctx) == result


def test_trace_prior_batches_chunks_and_isolates_poison_input(tmp_path, monkeypatch):
    import final.src.modular.arms.control_flow as module

    chunk_sizes = []

    def fake_execute(job):
        chunk_sizes.append(len(job["tests"]))
        if any(row["args"] == "('poison',)" for row in job["tests"]):
            raise ExecutionError("Sandbox exceeded overall wall timeout")
        return {"tests": [{"domain": "valid", "status": "executed", "coverage": {"lines": [1], "arcs": []}} for _ in job["tests"]]}

    monkeypatch.setattr(module, "execute", fake_execute)
    arm = ControlFlowArm()
    records = [
        {"args": "(1,)", "kwargs": "{}"},
        {"args": "('poison',)", "kwargs": "{}"},
        {"args": "(3,)", "kwargs": "{}"},
        {"args": "(4,)", "kwargs": "{}"},
    ]
    obs = arm.trace_prior(_context(tmp_path), _program(), records, chunk_size=4)
    assert chunk_sizes[0] == 4
    assert [row["status"] for row in obs] == ["executed", "error", "executed", "executed"]
    assert obs[1]["exception"] == "SandboxCrash"

    # Infrastructure error must fail fast immediately without splitting.
    monkeypatch.setattr(module, "execute", lambda job: (_ for _ in ()).throw(
        ExecutionError("Sandbox infrastructure exited 1: bwrap: Creating new namespace failed")
    ))
    with pytest.raises(ExecutionError, match="bwrap"):
        arm.trace_prior(_context(tmp_path), _program(), records, chunk_size=4)


def test_usage_by_arm_separates_control_flow_and_control_flow_4tool(tmp_path):
    for call_name, total in (
        ("control_flow_round_0", 100),
        ("control_flow_4tool_round_0", 250),
        ("control_flow_4tool_round_1_unknown_attempt_0000", None),
    ):
        call_dir = tmp_path / "tasks" / "0" / "calls" / call_name
        worker.save(call_dir / "attempt.json", {"state": "received" if total else "unknown"})
        if total is not None:
            worker.save(call_dir / "response.json", {
                "usage": {"prompt_tokens": total // 2, "completion_tokens": total // 2, "total_tokens": total}
            })
    usage = usage_by_arm(tmp_path, ["control_flow", "control_flow_4tool"])
    assert usage["control_flow"]["invocations"] == 1
    assert usage["control_flow"]["known_usage"]["total_tokens"] == 100
    assert usage["control_flow_4tool"]["invocations"] == 2
    assert usage["control_flow_4tool"]["received"] == 1
    assert usage["control_flow_4tool"]["unknown"] == 1
    assert usage["control_flow_4tool"]["known_usage"]["total_tokens"] == 250


def test_humaneval_registry_orchestration_preset_prepare_and_cli_wiring(tmp_path, monkeypatch):
    assert "control_flow_4tool" in ANALYSIS_FAMILY_COUNTS
    assert generation_call_cap("control_flow_4tool") == "pending"
    assert retained_input_budget("control_flow_4tool", 20) == "pending"
    assert "control_flow_4tool" in {arm.name for arm in available_arms()}
    assert selected_arms(["control_flow_4tool"])[0].name == "control_flow_4tool"

    limits = config.preview({"arms": ["plain", "control_flow_4tool"], "context_tokens": 20480, "completion_tokens": 4096})
    assert limits["logical_calls_by_arm"]["control_flow_4tool"] == "pending"
    assert limits["max_input_slots_by_arm"]["control_flow_4tool"] == "pending"
    assert limits["logical_call_cap"] == limits["completion_token_cap_total"] == "pending"
    assert "Control-flow + 4-tool trace" in names.benchmark_run_name(limits["config"], preview_only=True)

    with pytest.raises(ValueError, match="control_flow_4tool"):
        config.normalize({"arms": ["plain"], "tool_runs_dir": "final/out/put_pytest_tools_20261122"})

    presets = json.loads((config.ROOT / "final/presets/run_console.json").read_text())
    preset = next(item for item in presets if item["name"] == "Full164 · Control-flow + 4-tool trace · batch")
    assert preset["preview_only"] is True
    assert preset["parameters"]["context_tokens"] == 20480
    assert preset["parameters"]["completion_tokens"] == 4096
    preset_preview = config.preview(preset["parameters"])
    assert preset_preview["logical_call_cap"] == "pending"

    monkeypatch.setattr(worker, "private_endpoint", lambda *args: tmp_path / "private.env")
    prepared = tmp_path / "prepared"
    worker.prepare({"arms": ["control_flow_4tool"], "task_numbers": [0], "context_tokens": 20480, "completion_tokens": 4096}, prepared)
    plan = worker.read(prepared / "launch_plan.json")
    assert plan["tool_runs_dir"].endswith("final/out/put_pytest_tools_20261122")
    assert (prepared / "runtime/final/src/modular/control_flow/tool_inputs.py").is_file()

    parser, options = modular_run.load_options([
        "--arms", "control_flow_4tool", "--tool-runs-dir", str(tmp_path),
        "--context-tokens", "20480", "--input-tokens", "4096",
    ])
    _, arms, _ = modular_run.load_pipeline_settings(parser, options)
    assert isinstance(arms[0], ControlFlowFourToolArm)
    assert arms[0].tool_runs_dir == str(tmp_path)

    bad_parser, bad_options = modular_run.load_options(["--arms", "plain", "--tool-runs-dir", str(tmp_path)])
    with pytest.raises(SystemExit):
        modular_run.load_pipeline_settings(bad_parser, bad_options)


def test_default_tool_runs_dir_resolves_via_workspace_env(tmp_path, monkeypatch):
    he_dir = tmp_path / "final/out/put_pytest_tools_20261122"
    mbpp_dir = tmp_path / "final/out/mbppplus_put_pytest_tools_20261122"
    he_dir.mkdir(parents=True)
    mbpp_dir.mkdir(parents=True)
    monkeypatch.setenv("CONCEPTTESTER_WORKSPACE", str(tmp_path))
    assert default_tool_runs_dir("HumanEval/0") == he_dir
    assert default_tool_runs_dir("MBPP/2") == mbpp_dir
