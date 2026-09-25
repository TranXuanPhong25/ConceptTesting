import unittest

from conceptcoder_bridge.paper_labels import PAPER_LABELS, project_item


class ConceptCoderBridgeTests(unittest.TestCase):
    def test_exact_seven_paper_labels_and_no_patch_leak(self):
        self.assertEqual(len(PAPER_LABELS), 7)
        item = {
            "id": "fixture",
            "func_vuln": "p = NULL;\nif (p == NULL) return;\np->x = 1;",
            "lines_concept": {
                "0": [1, 0, 0, 0, 0, 0, 0, 1],
                "1": [0, 1, 0, 0, 0, 0, 0, 1],
                "2": [0, 0, 1, 0, 0, 0, 0, 0],
            },
            "fault_cond": "SECRET_PATCH_DERIVED_CONDITION",
            "fix_hint": "SECRET_PATCH_DERIVED_FIX",
            "family_pred": "null_deref",
        }
        projected = project_item(item)
        self.assertEqual([row["labels"] for row in projected["statements"]], [
            ["Null assignment"], ["Null check"], ["Pointer dereference"]
        ])
        self.assertNotIn("SECRET_PATCH", repr(projected))
        self.assertNotIn("family_pred", repr(projected))

    def test_rejects_misaligned_local_annotation(self):
        with self.assertRaisesRegex(ValueError, "outside source"):
            project_item({"id": "x", "func_vuln": "p = 0;", "lines_concept": {"3": [0] * 8}})


if __name__ == "__main__":
    unittest.main()
