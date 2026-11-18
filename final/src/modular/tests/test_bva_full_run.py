"""Full-run preparation, request guards and stable final observer accounting."""
import hashlib
import json
from types import SimpleNamespace

import pytest

from final.src.audits import run_bva_full as runner
from final.src.models.core_model import ModelResponse
from final.src.modular.artifacts import ArtifactStore
from final.src.runtime.artifacts import digest, save


def test_preparation_covers_all_tasks_skips_and_exact_allocated_requests(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    script = tmp_path / "final/src/audits/run_bva_full.py"
    monkeypatch.setattr(runner, "__file__", str(script))
    for name in ["final/__init__.py", "final/src/__init__.py", "final/src/audits/__init__.py",
                 "final/src/benchmarks/__init__.py", "final/src/benchmarks/datasets.py",
                 "final/src/audits/run_bva_full.py", "final/src/audits/run_prompt_style.py", "final/src/models/core_model.py",
                 "final/src/modular/PREREG.md", "final/data/humaneval.jsonl", "final/data/contracts.json",
                 "final/data/humanevalplus_v0.1.10_references.json"]:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture")
    (tmp_path / "final/src/runtime").mkdir()
    for name in ["model.py", "vertex.py", "checkpoint.py"]:
        (tmp_path / "final/src/models" / name).write_text("fixture")
    tasks = [{"task_id": f"HumanEval/{i}", "prompt": 'def f(x: float):\n    """Return x."""\n', "entry_point": "f"}
             for i in range(164)]
    rows = []
    for i, task in enumerate(tasks):
        programs = [{"id": p, "code": "def f(x):\n    return x\n", "base": {
            "status": "fail" if i in (65, 127, 132, 145, 163) else "pass", "calls": []}} for p in range(10)]
        if i in (32, 136):
            programs = programs[:7]
        rows.append({"task_id": task["task_id"], "generated": len(programs), "programs": programs})
    monkeypatch.setattr(runner, "load_tasks", lambda: tasks)
    monkeypatch.setattr(runner, "load_cohort", lambda path: {"tasks": rows, "cohort_sha256": "fixture"})
    monkeypatch.setattr(runner, "load_metadata", lambda: {task["task_id"]: {"contract": ""} for task in tasks})
    cohort = tmp_path / "cohort.json"
    cohort.write_text("fixture")
    output = tmp_path / "output"
    plan = runner.prepare(cohort, output)
    assert plan["tasks"] == 164
    assert len(plan["eligible_task_ids"]) == 157
    assert len(plan["skips"]) == 7
    assert plan["logical_call_cap"] == 1570
    assert all(request["input_budget"] == 2 for request in plan["requests"].values())
    assert plan["precision_tools"] is False and plan["new_plain_calls"] == 0
    # Notes are archived for provenance but unrelated later note edits cannot stop inference.
    (tmp_path / "final/src/modular/PREREG.md").write_text("new notes")
    dispatched = []

    class PlannedCalls:
        model_id = "fixture"

        def token_count(self, messages):
            return 10

        def complete(self, number, name, messages, **settings):
            identity = {"messages": messages, **settings}
            assert digest(identity) == plan["requests"][f"{number}/{name}"]["request_sha256"]
            dispatched.append(name)
            return ModelResponse('{"inputs":[]}', finish_reason="stop")

    context = runner.TaskContext(tasks[0], {"contract": ""}, ArtifactStore(output),
                                 runner.PipelineSettings(target_programs=10, input_budget=20), PlannedCalls())
    context.cohort_task = rows[0]
    context.packet = runner.InputPreparationStage([runner.BoundaryArm()]).prepare(context)
    runner.BoundaryArm().run(context)
    assert len(dispatched) == 10


def test_only_registered_messages_and_completion_identity_can_dispatch(tmp_path):
    dispatched = []
    messages = [{"role": "user", "content": "fixture"}]
    identity = {"messages": messages, "temperature": 0.7, "max_tokens": 2048, "seed": 314159}
    plan = {"requests": {"0/bva_0_soft_inputs": {"request_sha256": digest(identity), "messages_sha256": digest(messages)}}}
    model = SimpleNamespace(model_id="fixture", tokens=lambda messages: 10)
    calls = runner.GuardedCalls(model, ArtifactStore(tmp_path), plan)
    calls.client = SimpleNamespace(query=lambda *args, **kwargs: dispatched.append(args) or ModelResponse('{"inputs":[]}'))
    assert calls.token_count(messages) == 10
    assert calls.complete(0, "bva_0_soft_inputs", **identity).text == '{"inputs":[]}'
    with pytest.raises(ValueError, match="Unregistered completion"):
        calls.complete(0, "plain", **identity)
    with pytest.raises(ValueError, match="Unregistered tokenization"):
        calls.token_count([{"role": "user", "content": "changed"}])
    assert len(dispatched) == 1


def test_last_task_updates_summary_accounting(tmp_path):
    pipeline = runner.ProgressPipeline.__new__(runner.ProgressPipeline)
    pipeline.stage_events = []
    pipeline.artifacts = ArtifactStore(tmp_path)
    pipeline.generated_tasks = pipeline.evaluated_tasks = 0
    context = SimpleNamespace(task={"task_id": "HumanEval/0"})
    pipeline.record_stage_event(context, SimpleNamespace(name="put_evaluation"), "complete")
    assert json.loads((tmp_path / "progress.json").read_text())["evaluated_tasks"] == 1
