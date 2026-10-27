import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from . import get_concept, search
from .__main__ import main


class PublicRetrievalTests(unittest.TestCase):
    def test_code_defaults_to_evaluated_v2(self):
        result = search(code="def f(items):\n return items[len(items)]", top_k=1)
        self.assertEqual(result["engine_version"], "structure-v2.2")
        self.assertEqual(result["results"][0]["concept"]["id"], "py.index-out-of-bounds")

    def test_original_is_still_explicitly_available(self):
        result = search("B006", retriever="original", top_k=1)
        self.assertNotIn("engine_version", result)
        self.assertEqual(result["results"][0]["concept"]["id"], "py.mutable-default")

    def test_v2_text_can_retrieve_new_semantic_cards(self):
        result = search("Unicode encoded bytes character length", retriever="v2", top_k=3)
        self.assertIn("py.unicode-text-byte-domain", [h["concept"]["id"] for h in result["results"]])

    def test_extended_card_can_be_shown(self):
        card = get_concept("py.branch-boundary-contract")
        self.assertEqual(card["id"], "py.branch-boundary-contract")
        self.assertTrue(card["sources"])
        with self.assertRaisesRegex(ValueError, "Unknown concept"):
            get_concept("py.missing-not-a-real-card")

    def test_field_search_preserves_the_original_behavior(self):
        result = search("finally", field="where", top_k=3)
        self.assertNotIn("engine_version", result)
        with self.assertRaisesRegex(ValueError, "all fields"):
            search("finally", field="where", retriever="v2")

    def test_standard_cli_uses_v2_for_code(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "case.py"
            p.write_text("def f(x):\n return x[len(x)]\n")
            with patch("builtins.print") as output:
                self.assertEqual(main(["search", "--code", str(p), "--top-k", "1"]), 0)
            printed = "\n".join(str(c.args[0]) for c in output.call_args_list)
            self.assertIn("py.index-out-of-bounds", printed)
            self.assertIn("L2:", printed)


if __name__ == "__main__":
    unittest.main()
