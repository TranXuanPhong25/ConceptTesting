import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from structured_mutation import (  # noqa: E402
    Packet,
    apply_delta,
    derive_delta,
    run_smoke,
    synthesize_candidate,
)


class StructuredMutationTests(unittest.TestCase):
    def test_delta_preserves_declared_length_dependency(self):
        seed = Packet.parse("MSG|3|cat")
        target = Packet.parse("MSG|7|MAGMA!!")

        delta = derive_delta(seed, target)
        candidate = apply_delta(seed, delta)

        self.assertEqual(candidate.render(), target.render())
        self.assertTrue(candidate.is_well_formed())

    def test_seed_pair_synthesis_selects_guard_hitting_pair(self):
        seed = Packet.parse("MSG|3|cat")
        pairs = [
            {"source": "MSG|3|cat", "target": "MSG|5|hello", "label": "accepted"},
            {"source": "MSG|3|cat", "target": "MSG|7|MAGMA!!", "label": "guard_hit"},
        ]
        concept = {"required_label": "guard_hit", "relations": ["declared_len == len(payload)"]}

        candidate = synthesize_candidate(seed, pairs, concept)

        self.assertEqual(candidate.render(), "MSG|7|MAGMA!!")
        self.assertTrue(candidate.is_well_formed())

    def test_local_harness_discriminates_controlled_boundary_mutant(self):
        result = run_smoke()

        self.assertTrue(result["success"])
        self.assertEqual(result["original"]["outcome"], "GUARD_HIT")
        self.assertEqual(result["controlled_mutant"]["outcome"], "ACCEPT")


if __name__ == "__main__":
    unittest.main()
