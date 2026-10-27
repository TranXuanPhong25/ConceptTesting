import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from ..api import search
from ..__main__ import main


class V6PublicApiTests(unittest.TestCase):
    def test_explicit_v6_balanced_default(self):
        r = search(code="def f(xs):\n return xs[0]", retriever="v6")
        self.assertEqual(r["policy"], "balanced")
        self.assertTrue(r["engine_version"].startswith("semantic-v6"))
        self.assertTrue(r["results"])

    def test_explicit_precise_abstention(self):
        r = search(code="def f(xs):\n return xs[0]", retriever="v6", policy="precise")
        self.assertEqual(r["results"], [])
        self.assertTrue(r["review_candidates"])

    def test_policy_cannot_silently_apply_to_another_engine(self):
        with self.assertRaisesRegex(ValueError, "only"):
            search(code="x=0", retriever="v2", policy="precise")

    def test_standard_cli_can_select_v6_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "example.py"
            path.write_text("def f(xs):\n return xs[len(xs)]")
            with patch("builtins.print") as output:
                self.assertEqual(
                    main(
                        [
                            "search",
                            "--retriever",
                            "v6",
                            "--policy",
                            "precise",
                            "--code",
                            str(path),
                            "--json",
                        ]
                    ),
                    0,
                )
            r = output.call_args.args[0]
            self.assertIn("semantic-v6", r)
            self.assertIn("py.index-out-of-bounds", r)


if __name__ == "__main__":
    unittest.main()
