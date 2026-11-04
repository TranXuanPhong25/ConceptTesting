"""New methods plug into the orchestration/reference contract without concept stages."""
import pytest

from final.modular.artifacts import ArtifactStore
from final.modular.context import PipelineSettings
from final.modular.generators import InputGenerator, MethodInputGenerator
from final.modular.pipeline import BenchmarkPipeline
from final.modular.stages.base import PipelineStage
from final.modular.tests.test_boundary_arm import TASK, META, write_cohort, BoundaryFixtureModel
from final.modular.tests.test_modular_pipeline import FixtureCalls


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
    """An ordinary stage can produce inputs without inheriting ExperimentArm."""
    name = "another_method"

    def run(self, context):
        return {"inputs": [{"args": "([8, 9],)", "kwargs": "{}"}], "status": "generated"}


def fail_on_old_generation(monkeypatch):
    def forbidden(*arguments, **keywords):
        pytest.fail("Modern input producers must not invoke legacy concept/witness stages")
    for module in ("concept_analysis.ConceptAnalysisStage", "witness_sampling.WitnessSamplingStage"):
        monkeypatch.setattr(f"final.modular.stages.{module}.run", forbidden)


def test_default_shell_has_no_concept_or_witness_stages(tmp_path, monkeypatch):
    fail_on_old_generation(monkeypatch)
    path = write_cohort(tmp_path / "cohort.json")
    artifacts = ArtifactStore(tmp_path / "run")
    model = BoundaryFixtureModel()
    calls = FixtureCalls(model, artifacts.directory)
    pipeline = BenchmarkPipeline(path, artifacts, calls=calls, settings=PipelineSettings(target_programs=1))
    assert [stage.name for stage in pipeline.generation_stages] == ["frozen_cohort", "input_context", "input_generation"]
    result = pipeline.run([TASK], {TASK["task_id"]: META})
    assert set(result["arms"]) == {"plain"}
    assert len(model.requests) == 1
    assert "analysis" not in artifacts.read("tasks/7/packet.json")
    assert "witnesses" not in artifacts.read("tasks/7/packet.json")


def test_injected_generator_needs_no_arm_packet_model_or_concepts(tmp_path, monkeypatch):
    fail_on_old_generation(monkeypatch)
    path = write_cohort(tmp_path / "cohort.json")
    artifacts = ArtifactStore(tmp_path / "run")
    generator = SavedInputsGenerator()
    pipeline = BenchmarkPipeline(path, artifacts, input_generator=generator,
                                 settings=PipelineSettings(target_programs=1))
    assert [stage.name for stage in pipeline.generation_stages] == ["frozen_cohort", "input_generation"]
    summary = pipeline.run([TASK], {TASK["task_id"]: META})
    assert summary["arms"]["new_method"]["detected"] == 1
    assert not artifacts.exists("tasks/7/packet.json")
    assert generator.invocations == 1
    assert pipeline.run([TASK], {TASK["task_id"]: META}) == summary
    assert generator.invocations == 1
    replay = BenchmarkPipeline(path, ArtifactStore(artifacts.directory, read_only=True),
                               input_generator=SavedInputsGenerator(), settings=PipelineSettings(target_programs=1))
    assert replay.run([TASK], {TASK["task_id"]: META}) == summary
    assert replay.input_generator.invocations == 0


def test_any_input_producing_stage_can_use_method_adapter(tmp_path, monkeypatch):
    fail_on_old_generation(monkeypatch)
    path = write_cohort(tmp_path / "cohort.json")
    generator = MethodInputGenerator([NewMethodStage()], preparation_stages=())
    pipeline = BenchmarkPipeline(path, ArtifactStore(tmp_path / "run"), input_generator=generator,
                                 settings=PipelineSettings(target_programs=1))
    summary = pipeline.run([TASK], {TASK["task_id"]: META})
    assert summary["arms"]["another_method"]["valid_inputs"] == 1
    assert summary["arms"]["another_method"]["detected"] == 1
    assert [stage.name for stage in pipeline.generation_stages] == ["frozen_cohort", "input_generation"]


@pytest.mark.parametrize("arguments", ["(__import__('os').getcwd(),)", "1", "{}"])
def test_bad_generator_output_rejected_before_freeze_or_reference(tmp_path, monkeypatch, arguments):
    path = write_cohort(tmp_path / "cohort.json")
    artifacts = ArtifactStore(tmp_path / "run")
    monkeypatch.setattr("final.modular.stages.reference_oracle.execute", lambda job: pytest.fail("Reference ran"))
    generator = SavedInputsGenerator(arguments)
    pipeline = BenchmarkPipeline(path, artifacts, input_generator=generator,
                                 settings=PipelineSettings(target_programs=1))
    with pytest.raises((ValueError, SyntaxError)):
        pipeline.run([TASK], {TASK["task_id"]: META})
    assert not artifacts.exists("generation_frozen.json")
    assert not artifacts.exists("tasks/7/inputs.json")


def test_injected_configuration_drift_rejected_before_producer_runs(tmp_path):
    path = write_cohort(tmp_path / "cohort.json")
    artifacts = ArtifactStore(tmp_path / "run")
    BenchmarkPipeline(path, artifacts, input_generator=SavedInputsGenerator(),
                      settings=PipelineSettings(target_programs=1)).run([TASK], {TASK["task_id"]: META})
    changed = SavedInputsGenerator("([10, 11],)")
    with pytest.raises(ValueError, match="modular_manifest"):
        BenchmarkPipeline(path, artifacts, input_generator=changed,
                          settings=PipelineSettings(target_programs=1)).run([TASK], {TASK["task_id"]: META})
    assert changed.invocations == 0


def test_all_injected_inputs_freeze_before_reference_across_tasks(tmp_path):
    tasks = [TASK, {**TASK, "task_id": "HumanEval/8"}]
    path = write_cohort(tmp_path / "cohort.json", tasks)
    pipeline = BenchmarkPipeline(path, ArtifactStore(tmp_path / "run"), input_generator=SavedInputsGenerator(),
                                 settings=PipelineSettings(target_programs=1))
    pipeline.run(tasks, {task["task_id"]: META for task in tasks})
    generated_positions = [index for index, event in enumerate(pipeline.stage_events)
                           if event["stage"] == "input_generation" and event["state"] == "complete"]
    oracle_positions = [index for index, event in enumerate(pipeline.stage_events)
                        if event["stage"] == "reference_oracle" and event["state"] == "started"]
    assert max(generated_positions) < min(oracle_positions)
