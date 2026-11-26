"""Corrected reference selection and exact-input rescoring without model calls."""
import copy
import json
from dataclasses import replace

import pytest

from final.src.runtime.artifacts import digest, save
from final.src.benchmarks.datasets import DatasetLoader, load_tasks
from final.src.modular.plain import PlainArm
from final.src.modular.artifacts import ArtifactStore
from final.src.modular.context import PipelineSettings, TaskContext
from final.src.modular.generators.base import InputGenerator
from final.src.modular.generators.frozen import FrozenInputsGenerator
from final.src.modular.pipeline import BenchmarkPipeline
from final.src.modular.reference_oracle import run_reference_oracle
from final.src.modular.references import HumanEvalPlusReferencePrograms, TaskReferencePrograms, DEFAULT_REFERENCES
from final.src.modular.rescore import build_rescore_pipeline


TASKS = {task["task_id"]: task for task in load_tasks()}
METADATA = json.loads((DEFAULT_REFERENCES.parent / "contracts.json").read_text())


class FrozenFixtureGenerator(InputGenerator):
    methods = (PlainArm(),)

    def generate(self, context):
        return {"task_id": context.task["task_id"], "arms": {
            "plain": {"inputs": [{"args": "(-1, 2)", "kwargs": "{}"}], "rejected": []},
        }}


@pytest.fixture
def original_run(tmp_path):
    task = TASKS["HumanEval/97"]
    corrected = HumanEvalPlusReferencePrograms().for_task(task, METADATA[task["task_id"]])
    record = {"task_id": task["task_id"], "generated": 1, "base_pass": 1, "base_input_keys": [],
              "programs": [{"id": 0, "code": corrected["source"], "base": {"status": "pass", "calls": []}}]}
    path = tmp_path / "cohort.json"
    save(path, {"tasks": [record], "cohort_sha256": digest([record]), "dataset_sha256": "fixture-dataset"})
    artifacts = ArtifactStore(tmp_path / "old")
    pipeline = BenchmarkPipeline(path, artifacts, input_generator=FrozenFixtureGenerator(),
        settings=PipelineSettings(target_programs=1), reference_programs=TaskReferencePrograms())
    summary = pipeline.run([task], {task["task_id"]: METADATA[task["task_id"]]})
    assert summary["arms"]["plain"]["detected"] == 1
    return path, artifacts


def test_all164_reference_bindings_match_current_specs_and_metadata():
    provider = HumanEvalPlusReferencePrograms()
    assert len(provider.package["tasks"]) == 164
    for task in TASKS.values():
        reference = provider.for_task(task, METADATA[task["task_id"]])
        compile(reference["source"], "reference", "exec")
    assert provider.package["hidden_tests_retained"] is False
    assert all("plus_input" not in record for record in provider.package["tasks"].values())


@pytest.mark.parametrize("number,args,expected", [(97, "(-1, 2)", "2"), (140, "('  ',)", "'__'"),
                                                  (115, "([[0, 1, 1]], 2)", "1")])
def test_default_stage_executes_corrected_reference_not_original(tmp_path, number, args, expected):
    task = {**TASKS[f"HumanEval/{number}"], "canonical_solution": "    raise RuntimeError('OLD_REFERENCE_USED')\n"}
    context = TaskContext(task, METADATA[task["task_id"]], ArtifactStore(tmp_path), PipelineSettings())
    context.inputs = {"arms": {"method": {"inputs": [{"args": args, "kwargs": "{}"}]}}}
    context.cohort_task = {"base_input_keys": []}
    context.inputs_frozen = True
    run_reference_oracle(context)
    assert context.oracle["tests"][0]["expected"] == expected
    record = context.artifacts.read(context.task_directory + "/reference_program.json")
    assert record["source"] == "EvalPlus/HumanEval+" and record["version"] == "v0.1.10"


def test_reference_provider_uses_its_loaded_package_without_drift_guards(tmp_path):
    path = tmp_path / "references.json"
    path.write_bytes(DEFAULT_REFERENCES.read_bytes())
    provider = HumanEvalPlusReferencePrograms(path)
    task = TASKS["HumanEval/97"]
    expected = provider.for_task(task, METADATA[task["task_id"]])
    path.write_text(path.read_text() + "\n")
    assert provider.for_task({**task, "prompt": "changed"}, {}) == expected


def test_modern_pipeline_defaults_to_evalplus_reference_programs(original_run, tmp_path):
    cohort, _ = original_run
    pipeline = BenchmarkPipeline(cohort, ArtifactStore(tmp_path / "modern"), input_generator=FrozenFixtureGenerator())
    assert isinstance(pipeline.reference_programs, HumanEvalPlusReferencePrograms)


def test_rescore_reuses_exact_inputs_without_instantiating_a_model(original_run, tmp_path, monkeypatch):
    cohort, source = original_run
    before = {path: path.read_bytes() for path in source.directory.rglob("*") if path.is_file()}

    def forbidden(*arguments, **keywords):
        pytest.fail("Rescore must not create or call a model")

    monkeypatch.setattr("final.src.models.model.QwenModel.__init__", forbidden)
    pipeline, tasks, metadata = build_rescore_pipeline(source.directory, cohort, tmp_path / "corrected",
                                                      cache_directory=tmp_path / "execution_cache")
    summary = pipeline.run(tasks, metadata)
    assert summary["arms"]["plain"]["detected"] == 0
    assert summary["reused_generation"]["new_model_calls"] == 0
    assert summary["tester_calls"]["invocations"] == 0
    assert pipeline.artifacts.read("tasks/97/inputs.json") == source.read("tasks/97/inputs.json")
    assert before == {path: path.read_bytes() for path in source.directory.rglob("*") if path.is_file()}
    assert pipeline.run(tasks, metadata) == summary
    replay = BenchmarkPipeline(cohort, ArtifactStore(pipeline.artifacts.directory, read_only=True),
        input_generator=FrozenInputsGenerator(source.directory, methods=(PlainArm(),)),
        settings=pipeline.settings, reference_programs=HumanEvalPlusReferencePrograms())
    assert replay.run(tasks, metadata) == summary


def test_rescore_accepts_changed_inputs_without_original_freeze(original_run, tmp_path):
    cohort, source = original_run
    path = source.path("tasks/97/inputs.json")
    record = json.loads(path.read_text());record["arms"]["plain"]["inputs"][0]["args"] = "(2, 3)"
    path.write_text(json.dumps(record))
    pipeline, tasks, metadata = build_rescore_pipeline(source.directory, cohort, tmp_path / "corrected",
                                                      cache_directory=tmp_path / "cache")
    source.path("generation_frozen.json").unlink(missing_ok=True)
    pipeline.run(tasks, metadata)
    saved = pipeline.artifacts.read("tasks/97/inputs.json")
    assert saved["arms"]["plain"]["inputs"][0]["args"] == "(2, 3)"


def test_rescore_refuses_original_output_directory(original_run, tmp_path):
    cohort, source = original_run
    with pytest.raises(ValueError, match="separate output directory"):
        build_rescore_pipeline(source.directory, cohort, source.directory, cache_directory=tmp_path / "cache")


def test_dataset_loader_returns_expected_reference_programs():
    assert isinstance(DatasetLoader("HE-py").load_reference_programs(), HumanEvalPlusReferencePrograms)
    assert isinstance(DatasetLoader("MBPP-py").load_reference_programs(), TaskReferencePrograms)
