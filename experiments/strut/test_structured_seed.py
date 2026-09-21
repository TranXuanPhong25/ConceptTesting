import json
import tempfile
import unittest
from pathlib import Path

from structured_seed import derive_seed, render_harness, write_artifacts


ROOT = Path(__file__).resolve().parent


class StructuredSeedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = (ROOT / "fixture" / "target.c").read_text()
        self.hints = json.loads((ROOT / "fixture" / "concept_hints.json").read_text())

    def test_derives_function_guards_and_boundary_cases(self) -> None:
        seed = derive_seed(self.source, self.hints)
        self.assertEqual(seed["function"], "classify_window")
        self.assertEqual(seed["parameters"], ["value", "lower", "upper"])
        self.assertEqual(seed["static_concepts"]["guards"][2]["op"], ">")
        self.assertEqual(seed["cases"][2]["inputs"], [10, 5, 10])

    def test_renders_boundary_oracle(self) -> None:
        harness = render_harness(derive_seed(self.source, self.hints))
        self.assertIn("assert(classify_window(10, 5, 10) == 0);", harness)

    def test_writes_reproducible_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            paths = write_artifacts(ROOT / "fixture" / "target.c", ROOT / "fixture" / "concept_hints.json", Path(temp))
            self.assertTrue(paths["seed"].exists())
            self.assertTrue(paths["harness"].exists())


if __name__ == "__main__":
    unittest.main()
