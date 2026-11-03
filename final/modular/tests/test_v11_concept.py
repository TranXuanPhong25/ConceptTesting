"""Adapter boundaries, provenance and input-only generation; no benchmark inference."""
import json
from types import SimpleNamespace

import pytest

from final.core_model import ModelResponse
from final.pipeline import digest, save
from final.modular.arms import selected_arms
from final.modular.arms.plain import PlainArm
from final.modular.arms.v11_concept import V11ConceptArm
from final.modular.artifacts import ArtifactStore
from final.modular.context import PipelineSettings, TaskContext
from final.modular.calls import ConceptPreparationCallError
from final.modular.pipeline import BenchmarkPipeline
from final.modular.stages.concept_analysis import ConceptAnalysisStage
from final.modular.stages.input_generation import InputGenerationStage
from final.modular.stages.v11_concept import (
    V11ConceptStage, WORKER_PACKAGES, method_source_hashes, select_concept_cards,
)
from final.modular.stages.v11_concept_reporting import V11ConceptReportingStage
from final.run import DATA_SHA256
from final.v11_clean_runtimefix.cohort import V11ProgramView


TASK = {
    "task_id": "HumanEval/0", "entry_point": "threshold",
    "prompt": 'def threshold(value: int) -> bool:\n    """Return whether value exceeds two."""\n',
    "test": "def check(candidate):\n    assert candidate(3) is True\n",
    "canonical_solution": "    SECRET_REFERENCE_MUST_NOT_REACH_GENERATION\n",
}
PROGRAMS = [
    {"id": 0, "code": "def threshold(value):\n    return value > 2\n", "base": {"status": "pass", "calls": []}},
    {"id": 1, "code": "def threshold(value):\n    return 2 < value\n", "base": {"status": "pass", "calls": []}},
]


class InputCalls:
    model_id = "fixture-model"

    def __init__(self):
        self.requests = []

    def token_count(self, messages):
        return sum(len(message["content"]) for message in messages) // 4

    def complete(self, task_number, call_name, messages, **parameters):
        self.requests.append((task_number, call_name, messages, parameters))
        return ModelResponse('{"inputs":[{"args":"(2,)","kwargs":"{}","concept_id":"v11_c0"}]}')


def make_context(tmp_path, *, read_only=False):
    context = TaskContext(TASK, {"contract": "value is an integer", "atol": 0},
                          ArtifactStore(tmp_path / "run", read_only=read_only),
                          PipelineSettings(target_programs=2), InputCalls())
    context.cohort_task = {"task_id": TASK["task_id"], "generated": 2, "base_pass": 2,
                           "base_input_keys": [], "programs": PROGRAMS}
    return context


def write_cache(cache_directory, context):
    save(cache_directory / "manifest.json", {
        "model": context.calls.model_id, "worker_packages": WORKER_PACKAGES,
        "source_hashes": method_source_hashes(),
    })
    for program in PROGRAMS:
        directory = cache_directory / "cases" / str(program["id"])
        view = V11ProgramView().build(TASK, program)
        fact = {"kind": "BOUND", "line": len(view.splitlines()),
                "text": f"Boundary value: at line {len(view.splitlines())}, test equality to 2.",
                "witness_call": "DO_NOT_EXPOSE_TOOL_WITNESS", "mutant_src": "DO_NOT_EXPOSE_MUTANT"}
        save(directory / "bundle.json", {"task": program["id"], "entry": TASK["entry_point"],
             "put": view, "base": TASK["test"], "concept_meta": [fact],
             "tool_inputs": ["DO_NOT_EXPOSE_TOOL_INPUT"], "placebo_facts": ["DO_NOT_EXPOSE_PLACEBO"]})
        save(directory / "program_view.json", {"raw_source_sha256": V11ConceptStage.identity(context, program)["raw_source_sha256"]})
        save(directory / "mining.json", {"physical_request_keys": [f"historical-{program['id']}"]})


def test_cached_concepts_feed_exactly_one_modern_inputs_only_call(tmp_path):
    context = make_context(tmp_path)
    cache_directory = tmp_path / "old-run"
    write_cache(cache_directory, context)
    cache_hashes = {path: path.read_bytes() for path in cache_directory.rglob("*.json")}
    arm = V11ConceptArm(cache_directory=cache_directory, cache_only=True)
    arm.preparation_stages()[0].run(context)
    assert not context.calls.requests
    ConceptAnalysisStage((PlainArm(), arm)).run(context)
    plain_prompt = PlainArm().build_messages(context.packet)
    concept_prompt = arm.build_messages(context.packet)
    assert plain_prompt[0] == concept_prompt[0]
    assert concept_prompt[1]["content"].startswith(context.packet["common"])
    assert "INPUTS ONLY, never assertions or expected outputs" in concept_prompt[1]["content"]
    for forbidden in ("DO_NOT_EXPOSE", "SECRET_REFERENCE"):
        assert forbidden not in json.dumps(concept_prompt)
    InputGenerationStage((arm,)).run(context)
    assert len(context.calls.requests) == 1
    assert context.calls.requests[0][1] == "v11_concept"
    assert context.calls.requests[0][3] == {
        "temperature": context.settings.input_temperature, "max_tokens": context.settings.input_tokens,
        "seed": context.settings.input_seed,
    }
    assert context.inputs["arms"]["v11_concept"]["inputs"][0]["args"] == "(2,)"
    assert all(path.read_bytes() == content for path, content in cache_hashes.items())
    assert all(record["provenance"]["origin"] == "imported" for record in context.extensions["v11_concepts"])


@pytest.mark.parametrize("field,value", [("put", "wrong source"), ("base", "wrong base tests"), ("task", 999)])
def test_import_rejects_wrong_put_or_specification(tmp_path, field, value):
    context = make_context(tmp_path)
    cache_directory = tmp_path / "cache"
    write_cache(cache_directory, context)
    path = cache_directory / "cases/0/bundle.json"
    bundle = json.loads(path.read_text())
    save(path, dict(bundle, **{field: value}))
    with pytest.raises(ValueError, match="another PUT/specification"):
        V11ConceptStage(cache_directory, cache_only=True).run(context)


def test_import_rejects_method_or_model_drift(tmp_path):
    context = make_context(tmp_path)
    cache_directory = tmp_path / "cache"
    write_cache(cache_directory, context)
    path = cache_directory / "manifest.json"
    manifest = json.loads(path.read_text())
    save(path, dict(manifest, model="another-model"))
    with pytest.raises(ValueError, match="model"):
        V11ConceptStage(cache_directory).run(context)
    manifest["source_hashes"][next(iter(manifest["source_hashes"]))] = "changed"
    save(path, manifest)
    with pytest.raises(ValueError, match="source mismatch"):
        V11ConceptStage(cache_directory).run(context)


def test_read_only_and_cache_only_never_launch_mining(tmp_path, monkeypatch):
    def forbidden(*arguments, **keywords):
        pytest.fail("Missing cache must not launch a model or sandbox")

    monkeypatch.setattr("final.modular.stages.v11_concept.V11ModelCalls", forbidden)
    monkeypatch.setattr("final.modular.stages.v11_concept.V11Sandbox", forbidden)
    context = make_context(tmp_path, read_only=True)
    with pytest.raises(FileNotFoundError, match="Read-only replay"):
        V11ConceptStage().run(context)
    context.artifacts.read_only = False
    with pytest.raises(FileNotFoundError, match="No matching V11"):
        V11ConceptStage(cache_only=True).run(context)


def test_uncached_extraction_calls_only_mining_and_facts(tmp_path, monkeypatch):
    context = make_context(tmp_path)
    called_stages = []

    def mining_run(stage, preparation):
        assert "canonical_solution" not in preparation.human_eval
        called_stages.append("mining")
        preparation.mining = {"physical_request_keys": []}

    def facts_run(stage, preparation):
        called_stages.append("facts")
        preparation.bundle = {"put": preparation.task["put"], "concept_meta": [
            {"kind": "NUM", "text": "Exercise zero."}]}

    monkeypatch.setattr("final.modular.stages.v11_concept.V11MiningStage.run", mining_run)
    monkeypatch.setattr("final.modular.stages.v11_concept.V11FactsStage.run", facts_run)
    stage = V11ConceptStage()
    stage.calls = SimpleNamespace(model=SimpleNamespace(model_id=context.calls.model_id))
    stage.sandbox = object()
    stage.run(context)
    assert called_stages == ["mining", "facts", "mining", "facts"]
    assert not context.calls.requests
    assert all(record["state"] == "complete" for record in context.extensions["v11_concepts"])
    called_stages.clear()
    stage.run(context)
    assert not called_stages


def test_line_locations_are_translated_and_selection_uses_only_visible_owners(tmp_path):
    context = make_context(tmp_path)
    cache_directory = tmp_path / "cache"
    write_cache(cache_directory, context)
    V11ConceptStage(cache_directory).run(context)
    records = context.extensions["v11_concepts"]
    assert records[0]["cards"][0]["original_line"] == 2
    assert "at line 2" in records[0]["cards"][0]["text"]
    selected = select_concept_cards(records, [PROGRAMS[1]], 4)
    assert all(card["put_id"] == 1 for card in selected)
    assert selected[0]["id"] == "v11_c0"


def test_new_arm_wires_preparation_before_shared_generation_without_hybrid(tmp_path):
    context = make_context(tmp_path)
    cohort_path = tmp_path / "cohort.json"
    save(cohort_path, {"tasks": [context.cohort_task], "cohort_sha256": digest([context.cohort_task]),
                       "dataset_sha256": DATA_SHA256})
    arms = selected_arms(["plain", "v11_concept"])
    pipeline = BenchmarkPipeline(cohort_path, context.artifacts, arms=arms, calls=context.calls,
                                 settings=context.settings)
    pipeline.validate_stage_order()
    assert [stage.name for stage in pipeline.generation_stages] == [
        "frozen_cohort", "v11_concept_extraction", "concept_analysis", "witness_sampling", "input_generation"]
    assert isinstance(pipeline.reporting_stage, V11ConceptReportingStage)
    assert all("hybrid" not in type(stage).__name__.lower() for stage in pipeline.generation_stages)
    assert "v11_concept_extraction" in pipeline.generation_stages[2].requires


def test_model_cache_failures_cannot_be_swallowed_as_empty_concepts(tmp_path, monkeypatch):
    context = make_context(tmp_path)

    def failed_call(*arguments, **parameters):
        raise RuntimeError("Stored permanent transport failure; automatic replay disabled")

    def mining_run(stage, preparation):
        preparation.calls.complete([], 123)

    monkeypatch.setattr("final.modular.stages.v11_concept.V11MiningStage.run", mining_run)
    stage = V11ConceptStage()
    stage.calls = SimpleNamespace(model=SimpleNamespace(model_id=context.calls.model_id), complete=failed_call)
    stage.sandbox = object()
    with pytest.raises(ConceptPreparationCallError, match="model/cache call failed"):
        stage.run(context)
    assert not context.artifacts.exists("tasks/0/v11_concepts/0/concepts.json")


def test_native_idle_failure_is_never_converted_into_empty_guidance(tmp_path, monkeypatch):
    from final.v11_clean_runtimefix.sandbox import WorkerStalled

    context = make_context(tmp_path)

    def stalled(stage, preparation):
        raise WorkerStalled("CPU idle watchdog expired")

    monkeypatch.setattr("final.modular.stages.v11_concept.V11MiningStage.run", stalled)
    stage = V11ConceptStage()
    stage.calls = SimpleNamespace(model=SimpleNamespace(model_id=context.calls.model_id))
    stage.sandbox = object()
    with pytest.raises(WorkerStalled):
        stage.run(context)
    assert not context.artifacts.exists("tasks/0/v11_concepts/0/concepts.json")
