"""New methods plug into the orchestration/reference contract without concept stages."""
import pytest

from final.src.modular.artifacts import ArtifactStore
from final.src.modular.context import PipelineSettings
from final.src.modular.generators import InputGenerator, MethodInputGenerator
from final.src.modular.pipeline import BenchmarkPipeline
from final.src.modular.references import TaskReferencePrograms
from final.src.modular.stages.base import PipelineStage
from final.src.modular.tests.test_boundary_arm import TASK, META, write_cohort, BoundaryFixtureModel
from final.src.modular.tests.helpers import FixtureCalls


class SavedInputsGenerator(InputGenerator):
    def __init__(self, argument="([5, 6],)"):
        self.argument = argument
        self.invocations = 0

    def configuration(self):
        return {"argument": self.argument}

    def generate(self, context):
        self.invocations += 1
        return {"task_id": context.task["task_id"], "arms": {"new_method": {
            "inputs": [{"args": self.argument, "kwargs": "{}"}]}}}


class NewMethodStage(PipelineStage):
    """An ordinary stage can produce inputs without inheriting InputGenerationMethod."""
    name = "another_method"

    def run(self, context):
        return {"inputs": [{"args": "([8, 9],)", "kwargs": "{}"}], "status": "generated"}




def test_default_shell_has_no_concept_or_witness_stages(tmp_path, monkeypatch):
    path = write_cohort(tmp_path / "cohort.json")
    artifacts = ArtifactStore(tmp_path / "run")
    model = BoundaryFixtureModel()
    calls = FixtureCalls(model, artifacts.directory)
    pipeline = BenchmarkPipeline(path, artifacts, calls=calls, settings=PipelineSettings(target_programs=1), reference_programs=TaskReferencePrograms())
    assert [stage.name for stage in pipeline.generation_stages] == ["cohort_loader", "input_context", "input_generation"]
    result = pipeline.run([TASK], {TASK["task_id"]: META})
    assert set(result["arms"]) == {"plain"}
    assert len(model.requests) == 1
    assert "analysis" not in artifacts.read("tasks/7/packet.json")
    assert "witnesses" not in artifacts.read("tasks/7/packet.json")


def test_injected_generator_needs_no_arm_packet_model_or_concepts(tmp_path, monkeypatch):
    path = write_cohort(tmp_path / "cohort.json")
    artifacts = ArtifactStore(tmp_path / "run")
    generator = SavedInputsGenerator()
    pipeline = BenchmarkPipeline(path, artifacts, input_generator=generator,
                                 settings=PipelineSettings(target_programs=1), reference_programs=TaskReferencePrograms())
    assert [stage.name for stage in pipeline.generation_stages] == ["cohort_loader", "input_generation"]
    summary = pipeline.run([TASK], {TASK["task_id"]: META})
    assert summary["arms"]["new_method"]["detected"] == 1
    assert not artifacts.exists("tasks/7/packet.json")
    assert generator.invocations == 1
    assert pipeline.run([TASK], {TASK["task_id"]: META}) == summary
    assert generator.invocations == 1
    replay = BenchmarkPipeline(path, ArtifactStore(artifacts.directory, read_only=True),
                               input_generator=SavedInputsGenerator(), settings=PipelineSettings(target_programs=1), reference_programs=TaskReferencePrograms())
    assert replay.run([TASK], {TASK["task_id"]: META}) == summary
    assert replay.input_generator.invocations == 0


def test_any_input_producing_stage_can_use_method_adapter(tmp_path, monkeypatch):
    path = write_cohort(tmp_path / "cohort.json")
    generator = MethodInputGenerator([NewMethodStage()], preparation_stages=())
    pipeline = BenchmarkPipeline(path, ArtifactStore(tmp_path / "run"), input_generator=generator,
                                 settings=PipelineSettings(target_programs=1), reference_programs=TaskReferencePrograms())
    summary = pipeline.run([TASK], {TASK["task_id"]: META})
    assert summary["arms"]["another_method"]["valid_inputs"] == 1
    assert summary["arms"]["another_method"]["detected"] == 1
    assert [stage.name for stage in pipeline.generation_stages] == ["cohort_loader", "input_generation"]


@pytest.mark.parametrize("arguments", ["(__import__('os').getcwd(),)", "1", "{}"])
def test_invalid_calls_are_saved_and_rejected_without_execution(tmp_path, monkeypatch, arguments):
    path = write_cohort(tmp_path / "cohort.json")
    artifacts = ArtifactStore(tmp_path / "run")
    monkeypatch.setattr("final.src.modular.stages.reference_oracle.execute", lambda job: pytest.fail("Reference ran"))
    generator = SavedInputsGenerator(arguments)
    pipeline = BenchmarkPipeline(path, artifacts, input_generator=generator,
                                 settings=PipelineSettings(target_programs=1), reference_programs=TaskReferencePrograms())
    summary = pipeline.run([TASK], {TASK["task_id"]: META})
    assert summary["arms"]["new_method"]["valid_inputs"] == 0
    assert summary["diagnostics"]["oracle_rejections"]["input_type_rejects"] == 1
    assert not artifacts.exists("generation_frozen.json")
    assert artifacts.read("tasks/7/inputs.json")["arms"]["new_method"]["inputs"][0]["args"] == arguments


def test_saved_inputs_are_loaded_despite_generator_configuration_changes(tmp_path, monkeypatch):
    path = write_cohort(tmp_path / "cohort.json")
    artifacts = ArtifactStore(tmp_path / "run")
    BenchmarkPipeline(path, artifacts, input_generator=SavedInputsGenerator(),
                      settings=PipelineSettings(target_programs=1), reference_programs=TaskReferencePrograms()).run([TASK], {TASK["task_id"]: META})
    write = artifacts.write

    def reject_input_rewrite(relative_path, data):
        if relative_path == "tasks/7/inputs.json":
            pytest.fail("Rewrote the saved inputs checkpoint")
        return write(relative_path, data)

    monkeypatch.setattr(artifacts, "write", reject_input_rewrite)
    changed = SavedInputsGenerator("([10, 11],)")
    BenchmarkPipeline(path, artifacts, input_generator=changed,
                      settings=PipelineSettings(target_programs=1), reference_programs=TaskReferencePrograms()).run([TASK], {TASK["task_id"]: META})
    assert changed.invocations == 0


def test_all_injected_inputs_freeze_before_reference_across_tasks(tmp_path):
    tasks = [TASK, {**TASK, "task_id": "HumanEval/8"}]
    path = write_cohort(tmp_path / "cohort.json", tasks)
    pipeline = BenchmarkPipeline(path, ArtifactStore(tmp_path / "run"), input_generator=SavedInputsGenerator(),
                                 settings=PipelineSettings(target_programs=1), reference_programs=TaskReferencePrograms())
    pipeline.run(tasks, {task["task_id"]: META for task in tasks})
    generated_positions = [index for index, event in enumerate(pipeline.stage_events)
                           if event["stage"] == "input_generation" and event["state"] == "complete"]
    oracle_positions = [index for index, event in enumerate(pipeline.stage_events)
                        if event["stage"] == "reference_oracle" and event["state"] == "started"]
    assert max(generated_positions) < min(oracle_positions)
