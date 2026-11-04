"""Resource exclusions bind source/spec and affect analysis, prompts and scoring."""
import json
from dataclasses import replace

import pytest

from final.pipeline import save
from final.modular.stages.resource_exclusions import ResourceExclusionPlan
from final.modular.stages.v11_concept import V11ConceptStage
from final.modular.stages.concept_analysis import ConceptAnalysisStage
from final.modular.arms.plain import PlainArm
from final.modular.tests.test_v11_concept import make_context, PROGRAMS


def prepare_plan(context, tmp_path, *, decision_overrides=None):
    identity = V11ConceptStage.identity(context, PROGRAMS[0])
    record = dict(identity, decision="exclude_put", reason="Synthetic unbounded expensive input loop")
    record.update(decision_overrides or {})
    plan_path = tmp_path / "plan.json"
    save(plan_path, {"schema": "v11-resource-exclusions-1", "scope": "preparation_prompt_and_evaluation",
                     "cohort_sha256": "fixture-cohort", "records": [record]})
    context.artifacts.write("modular_manifest.json", {"cohort_sha256": "fixture-cohort"})
    return plan_path


def test_excluded_put_never_reaches_preparation_or_shared_prompt(tmp_path, monkeypatch):
    context = make_context(tmp_path)
    original_cohort = context.cohort_task
    path = prepare_plan(context, tmp_path)
    plan = ResourceExclusionPlan(path)
    plan.apply(context, V11ConceptStage.identity)
    assert [program["id"] for program in context.cohort_task["programs"]] == [1]
    assert context.cohort_task["base_pass"] == 1
    assert len(original_cohort["programs"]) == 2
    assert context.extensions["resource_exclusions"][0]["put_id"] == 0
    ConceptAnalysisStage((PlainArm(),)).run(context)
    assert context.packet["visible_put_ids"] == [1]
    assert PROGRAMS[0]["code"].strip() not in context.packet["common"]
    # Same original cohort can replay the exact exclusion marker after resume.
    context.cohort_task = original_cohort
    plan.apply(context, V11ConceptStage.identity)


def test_all_base_pass_excluded_task_skips_without_any_model_or_native_work(tmp_path, monkeypatch):
    context = make_context(tmp_path)
    context.cohort_task = dict(context.cohort_task, generated=1, base_pass=1, programs=[PROGRAMS[0]])
    context.settings = replace(context.settings, target_programs=1)
    path = prepare_plan(context, tmp_path)

    def forbidden(*arguments, **parameters):
        pytest.fail("All-excluded task must not initialize model, view or sandbox")

    for name in ("V11ModelCalls", "V11Sandbox", "V11ProgramView"):
        monkeypatch.setattr("final.modular.stages.v11_concept." + name, forbidden)
    V11ConceptStage(resource_exclusions=path).run(context)
    ConceptAnalysisStage((PlainArm(),)).run(context)
    assert context.packet["skip"] == "all_base_pass_resource_excluded"
    assert context.extensions["v11_concepts"] == []
    assert context.cohort_task["base_pass"] == 0


@pytest.mark.parametrize("field", ["raw_source_sha256", "specification_sha256"])
def test_plan_rejects_other_put_or_specification(tmp_path, field):
    context = make_context(tmp_path)
    path = prepare_plan(context, tmp_path, decision_overrides={field: "changed"})
    with pytest.raises(ValueError, match="PUT/spec mismatch"):
        ResourceExclusionPlan(path).apply(context, V11ConceptStage.identity)


def test_plan_rejects_other_cohort_and_changed_file(tmp_path):
    context = make_context(tmp_path)
    path = prepare_plan(context, tmp_path)
    plan = ResourceExclusionPlan(path)
    data = json.loads(path.read_text())
    save(path, dict(data, cohort_sha256="other-cohort"))
    with pytest.raises(ValueError, match="changed during"):
        plan.apply(context, V11ConceptStage.identity)
    with pytest.raises(ValueError, match="another cohort"):
        ResourceExclusionPlan(path).apply(context, V11ConceptStage.identity)


def test_plan_refuses_outcome_based_retroactive_exclusions(tmp_path):
    context = make_context(tmp_path)
    path = prepare_plan(context, tmp_path)
    context.artifacts.write("tasks/0/inputs.json", {"arms": {}})
    with pytest.raises(ValueError, match="after task generation"):
        ResourceExclusionPlan(path).apply(context, V11ConceptStage.identity)


def test_evaluation_receives_only_retained_puts(tmp_path, monkeypatch):
    from final.modular.stages.put_evaluation import PutEvaluationStage

    context = make_context(tmp_path)
    path = prepare_plan(context, tmp_path)
    ResourceExclusionPlan(path).apply(context, V11ConceptStage.identity)
    context.inputs = {"arms": {"plain": {"inputs": []}}}
    context.oracle = {"tests": [{"args": "(2,)", "kwargs": "{}", "expected": "False"}],
                      "arm_indices": {"plain": [0]}, "rejected": []}
    seen_sources = []

    def execute_fixture(job):
        seen_sources.append(job["source"])
        return {"tests": [{"status": "ok"}]}

    monkeypatch.setattr("final.modular.stages.put_evaluation.execute", execute_fixture)
    result = PutEvaluationStage().evaluate_programs(context)
    assert seen_sources == [PROGRAMS[1]["code"], PROGRAMS[1]["code"]]
    assert result["base_pass"] == 1
    assert set(result["outcomes"]) == {"1"}
