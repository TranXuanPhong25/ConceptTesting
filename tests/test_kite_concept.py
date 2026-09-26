import tempfile
import unittest
from pathlib import Path

from kite_concept.checkpoint import CheckpointStore
from kite_concept.arms import ArmWorkflows
from kite_concept.dataset import PROJECT_COUNTS, seeded_tuning_subset, validate_manifest
from kite_concept.evaluator import Execution, independent_reexecution
from kite_concept.extraction import parse_concept, parse_mechanism
from kite_concept.injection import InjectionPlan, promotion_gate, validate_injection
from kite_concept.knowledge import build_knowledge_base, concept_from_mechanism, retrieve
from kite_concept.metrics import paired_comparison, project_rbdr, rbdr
from kite_concept.models import MechanismRecord
from kite_concept.prompts import concept_prompt, mutgen_prompt
from kite_concept.structure import extract_unit_structures, multiset_jaccard
from kite_concept.models import TaskRecord


JAVA = """public int clamp(int x) {
  if (x < 0) return 0;
  int y = x + 1;
  return y;
}"""


class KiteConceptTests(unittest.TestCase):
    def test_unit_structure_is_deterministic_and_paper_shaped(self):
        first = extract_unit_structures(JAVA)
        second = extract_unit_structures(JAVA)
        self.assertTrue(first)
        self.assertEqual(first, second)
        self.assertTrue(all(len(unit.fingerprint) == 16 for unit in first))
        self.assertTrue(all(relation.split(":")[1] in {
            "condition_of", "expr_in_stmt", "guard_to_body", "adjacent_stmt", "same_block"
        } for unit in first for relation in unit.relations))
        self.assertEqual(multiset_jaccard(first[0], first[0]), 1.0)

    def test_deleakage_retrieval_and_concept_contract(self):
        structures = tuple(extract_unit_structures(JAVA))
        mechanism = MechanismRecord(
            "m1", "boundary excludes the minimum valid value", "integer comparison guard",
            "change strict to inclusive comparison", "valid boundary is rejected", "return value differs",
            ("Bears-1",), structures, "Bears",
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "kb.jsonl"
            report = build_knowledge_base([
                mechanism.to_dict(),
                {**mechanism.to_dict(), "id": "leak", "source_project": "Cli"},
            ], path)
            self.assertEqual(report, {"accepted": 1, "skipped_leakage": 1, "skipped_invalid": 0})
        ranked = retrieve([mechanism], "integer comparison boundary and guard", structures)
        self.assertEqual(ranked[0][0].id, "m1")
        self.assertGreater(ranked[0][1]["structural"], 0)
        concept = concept_from_mechanism(mechanism, "x == minimum", "assert exact accepted value")
        self.assertEqual(concept.trigger_input_relation, "x == minimum")
        task = TaskRecord("Cli", 1, "C", "clamp", "/f", "/b", JAVA)
        prompt = concept_prompt(task, concept)
        self.assertIn("x == minimum", prompt)
        self.assertIn("assert exact accepted value", prompt)

    def test_strict_mechanism_and_concept_extraction(self):
        mechanism = parse_mechanism(
            '{"what":"wrong bound","where":"integer guard","how":"shift bound",'
            '"expected_buggy_behavior":"rejects zero","expected_failure_signal":"return differs"}',
            "m2", ("GHRB-2",), tuple(extract_unit_structures(JAVA)), "GHRB",
        )
        concept = parse_concept('{"trigger_input_relation":"x == 0","expected_oracle":"returns one"}', mechanism)
        self.assertEqual(concept.violated_constraint, "wrong bound")
        self.assertEqual(concept.expected_oracle, "returns one")
        with self.assertRaises(ValueError):
            parse_concept('{"trigger_input_relation":"x == 0"}', mechanism)

    def test_four_injection_gates_and_promotion_gate(self):
        before = "x < 0"
        start = JAVA.index(before)
        plan = InjectionPlan("m1", before, "x <= 0", start, start + len(before), "zero rejected", "x == 0")
        result = validate_injection(JAVA, plan, lambda source: "<=" in source,
                                    lambda source: "clamp" in source, lambda old, new: old != new)
        self.assertTrue(result.accepted)
        self.assertIn("x <= 0", result.injected_source)
        self.assertTrue(promotion_gate(True, True, {"old-a": True, "old-b": True}))
        self.assertFalse(promotion_gate(True, True, {"old-a": False}))

    def test_mutgen_prompt_contains_pit_tuple_and_only_actionable_statuses(self):
        task = TaskRecord("Cli", 1, "C", "clamp", "/f", "/b", JAVA)
        prompt = mutgen_prompt(task, "clamps integers", [
            {"id": "1", "operator": "ConditionalsBoundaryMutator", "line": 2,
             "status": "SURVIVED", "mutated_statement": "x <= 0"},
            {"id": "2", "operator": "NegateConditionalsMutator", "line": 2,
             "status": "KILLED", "mutated_statement": "x >= 0"},
        ])
        self.assertIn("1. ConditionalsBoundaryMutator at line 2, SURVIVED", prompt)
        self.assertNotIn("2. NegateConditionalsMutator", prompt)

    def test_anypoc_requires_stable_independent_fixed_pass_buggy_fail(self):
        def execution(version, attempt, code, digest="same"):
            return Execution(version, attempt, code, False, 0.01, digest, "")
        outcome = independent_reexecution(
            lambda attempt: execution("fixed", attempt, 0),
            lambda attempt: execution("buggy", attempt, 1),
        )
        self.assertTrue(outcome.detected)
        flaky = independent_reexecution(
            lambda attempt: execution("fixed", attempt, 0),
            lambda attempt: execution("buggy", attempt, 1 if attempt == 1 else 0),
        )
        self.assertFalse(flaky.detected)
        self.assertFalse(flaky.stable)

    def test_checkpoint_enforces_budget_and_resumes_completed_task(self):
        with tempfile.TemporaryDirectory() as directory:
            with CheckpointStore(Path(directory) / "state.sqlite") as store:
                self.assertTrue(store.begin("Cli-1:C#m", "kite", 2))
                store.record_call("Cli-1:C#m", "kite", 10, 4)
                store.record_call("Cli-1:C#m", "kite", 11, 5)
                with self.assertRaises(RuntimeError):
                    store.record_call("Cli-1:C#m", "kite")
                store.finish("Cli-1:C#m", "kite", {"detected": False})
                self.assertFalse(store.begin("Cli-1:C#m", "kite", 2))
                self.assertEqual(store.get("Cli-1:C#m", "kite")["calls_used"], 2)

    def test_callable_arm_workflows_charge_calls_and_promote_only_valid_suite(self):
        calls = []
        generated = iter((("bad suite", 10, 2), ("good suite", 11, 3)))
        workflow = ArmWorkflows(
            generate=lambda _prompt: next(generated),
            correct_check=lambda suite: (suite == "good suite", "ok" if suite == "good suite" else "compile error"),
            target_check=lambda suite, _target: (suite == "good suite", "killed" if suite == "good suite" else "survived"),
            charge=lambda input_tokens, output_tokens: calls.append((input_tokens, output_tokens)),
        )
        task = TaskRecord("Cli", 1, "C", "clamp", "/f", "/b", JAVA)
        direct = workflow.direct(task, "context")
        self.assertFalse(direct["correct_pass"])
        concept = concept_from_mechanism(
            MechanismRecord("m", "bound", "guard", "shift", "wrong", "diff"), "x == 0", "returns 0"
        )
        result = workflow.concept(task, [concept], budget=1)
        self.assertEqual(result["suite"], "good suite")
        self.assertEqual(calls, [(10, 2), (11, 3)])

    def test_exact_split_seeded_subset_and_paired_statistics(self):
        rows = []
        for project, count in PROJECT_COUNTS.items():
            rows.extend({"project": project, "bug_id": i, "focal_class": "C", "focal_method": f"m{i}"}
                        for i in range(1, count + 1))
        self.assertEqual(len(validate_manifest(rows)), 172)
        subset = seeded_tuning_subset(rows, size=40)
        self.assertEqual(len(subset), 40)
        self.assertEqual({row["project"] for row in subset}, set(PROJECT_COUNTS))
        self.assertEqual(subset, seeded_tuning_subset(rows, size=40))
        self.assertEqual(rbdr([{"detected": True}, {"detected": False}]), .5)
        self.assertEqual(project_rbdr([{"project": "Cli", "detected": True}], {"Cli": 2})["Cli"], .5)
        stats = paired_comparison({"a": True, "b": True, "c": False},
                                  {"a": False, "b": True, "c": True}, bootstrap_samples=1000, seed=1)
        self.assertEqual(stats["n"], 3)
        self.assertEqual(stats["left_only"], 1)
        self.assertEqual(stats["right_only"], 1)
        self.assertEqual(stats["mcnemar_exact_p"], 1.0)


if __name__ == "__main__":
    unittest.main()
