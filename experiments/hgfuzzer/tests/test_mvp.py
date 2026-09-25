"""Regression tests for the bounded HGFuzzer-inspired MVP."""

from __future__ import annotations

import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("hgfuzzer_mvp", ROOT / "run.py")
assert SPEC and SPEC.loader
MVP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MVP)


class HGFuzzerMvpTests(unittest.TestCase):
    def test_concept_seed_satisfies_all_predicates(self) -> None:
        plan = MVP.load_plan(ROOT / "concept_plan.json")
        seed = MVP.seed_from_plan(plan)
        self.assertEqual(seed[:2], b"HG")
        self.assertEqual(seed[2], 1)
        self.assertGreater(seed[3], 8)
        self.assertEqual(MVP.xor_checksum(seed[:-1]), seed[-1])
        self.assertTrue(MVP.satisfies_plan(seed, plan))

    def test_mutator_preserves_the_targeting_constraints(self) -> None:
        plan = MVP.load_plan(ROOT / "concept_plan.json")
        seed = MVP.seed_from_plan(plan)
        mutated = MVP.mutate_toward_target(seed, plan, case_index=7)
        self.assertTrue(MVP.satisfies_plan(mutated, plan))
        self.assertNotEqual(seed, mutated)

    def test_smoke_reaches_target_and_distinguishes_fixed_fixture(self) -> None:
        result = MVP.run_smoke(ROOT, cases=4, timeout_seconds=2.0)
        self.assertTrue(result["vulnerable"]["target_hit"])
        self.assertTrue(result["vulnerable"]["sanitizer_detected"])
        self.assertTrue(result["fixed"]["target_hit"])
        self.assertFalse(result["fixed"]["sanitizer_detected"])


if __name__ == "__main__":
    unittest.main()
