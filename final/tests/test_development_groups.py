"""Development selection invariants; never invoke a model or execute PUT code."""
import json
from dataclasses import replace
from pathlib import Path

import pytest

from final.development_groups import COHORT, DevelopmentGroups, GROUPS, REVIEW, ProgramStructure, read_review
from final.experiments.concept_reference_v1.cohort import load_cohort
from final.modular.context import PipelineSettings


@pytest.fixture(scope="module")
def inventory():
    if not COHORT.is_file() or not (REVIEW / "inventory.json").is_file():
        pytest.skip("Requires the local frozen PUT cohort and offline development_groups build")
    return json.loads((REVIEW / "inventory.json").read_text())


def test_all_tasks_have_one_primary_and_valid_secondary_groups(inventory):
    reviews = read_review()
    assert len(reviews) == 164
    assert {record["task_id"] for record in inventory["task_records"]} == {f"HumanEval/{number}" for number in range(164)}
    assert sum(len(record["programs"]) for record in inventory["task_records"]) == 1634
    assert sum(program["base_status"] == "pass" for record in inventory["task_records"] for program in record["programs"]) == 1465


def test_small_subsets_are_disjoint_from_development_checks(inventory):
    builder = DevelopmentGroups()
    all_development = set()
    all_checks = set()
    smoke_programs = set()
    for group in GROUPS:
        plan = builder.make_plan(inventory, group)
        smoke = plan["tiers"]["smoke"]
        development = plan["tiers"]["development"]
        checks = plan["tiers"]["check"]
        assert len(smoke) == 6
        assert len(development) <= 12
        assert len(checks) == 4
        assert set(smoke) <= set(development)
        assert len(development) == len(set(development))
        all_development.update(development)
        all_checks.update(checks)
        smoke_programs.update((number, plan["representatives"][str(number)]) for number in smoke)
    assert not all_development & all_checks
    assert len(smoke_programs) == 24


@pytest.mark.parametrize("group", GROUPS)
def test_export_reuses_exact_saved_sources_ids_and_base_results(tmp_path, inventory, group):
    builder = DevelopmentGroups()
    destination = tmp_path / group
    selection = builder.export(group, "smoke", destination)
    exported = load_cohort(destination / "cohort.json")
    originals = {task["task_id"]: task for task in builder.cohort["tasks"]}
    assert selection["target_programs"] == 1
    settings = replace(PipelineSettings(), target_programs=selection["target_programs"])
    assert len(exported["tasks"]) == 6
    for task in exported["tasks"]:
        assert task["generated"] == task["base_pass"] == settings.target_programs
        program = task["programs"][0]
        original = next(value for value in originals[task["task_id"]]["programs"] if value["id"] == program["id"])
        assert program == original
        assert program["base"]["status"] == "pass"
    with pytest.raises(ValueError, match="empty output"):
        builder.export(group, "smoke", destination)


def test_reject_stale_review_or_cohort(inventory):
    builder = DevelopmentGroups()
    with pytest.raises(ValueError, match="different PUT cohort"):
        builder.verify_inventory(dict(inventory, source_cohort_sha256="wrong"))
    with pytest.raises(ValueError, match="classification changed"):
        builder.verify_inventory(dict(inventory, task_review_sha256="wrong"))


def test_one_line_base_coverage_is_not_claimed_as_def_use_coverage():
    source = "def choose(flag):\n    value = 1\n    if flag:\n        value = 2\n    return value\n"
    evidence = ProgramStructure().analyze({"code": source, "base": {"status": "pass", "coverage": {"lines": [1, 2, 3, 5]}}})
    assert evidence["base_uncovered_lines"] == [4]
    assert evidence["alternative_reaching_definitions"]
    assert "UNKNOWN" in evidence["data_flow_status"]
    assert not evidence["graph_error"]


def test_no_missing_statement_gap_is_invented():
    source = "def add(left, right):\n    return left + right\n"
    analyzer = ProgramStructure()
    full = analyzer.analyze({"code": source, "base": {"coverage": {"lines": [1, 2]}}})
    unknown = analyzer.analyze({"code": source, "base": {}})
    assert full["base_uncovered_lines"] == []
    assert unknown["base_uncovered_lines"] is None
