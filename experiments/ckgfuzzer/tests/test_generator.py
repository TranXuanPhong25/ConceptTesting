"""Tests for the bounded CKGFuzzer-inspired local MVP."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generate_harness import choose_call_sequence, render_harness


class HarnessGenerationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = json.loads((ROOT / "graph.json").read_text())

    def test_selects_state_valid_sequence_to_target_sink(self) -> None:
        sequence = choose_call_sequence(self.graph)
        self.assertEqual([step["api"] for step in sequence], ["ledger_create", "ledger_add", "ledger_commit"])
        self.assertEqual(sequence[1]["arguments"], [0])

    def test_rendered_harness_encodes_public_contract(self) -> None:
        source = render_harness(self.graph, choose_call_sequence(self.graph))
        self.assertIn("assert(ledger_commit(ledger) == -2);", source)
        self.assertIn("assert(ledger_add(ledger, 0) == 0);", source)
        self.assertNotIn("mutant", source.lower())


if __name__ == "__main__":
    unittest.main()
