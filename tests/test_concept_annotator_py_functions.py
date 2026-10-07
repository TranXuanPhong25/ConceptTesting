import tempfile
import unittest
from pathlib import Path

from concept_annotator_py.functions import annotate_function, render_tags, selftest, stats


class FunctionConceptTests(unittest.TestCase):
    def test_selftest(self):
        selftest()

    def test_stats_on_a_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "m.py"
            path.write_text("def f(x=None):\n    return x.y\n\ndef g(a):\n    return a\n")
            result = stats(tmp)
        self.assertEqual(result["functions"], 2)
        self.assertEqual(result["untagged"], 0.5)
        self.assertEqual(result["rate"]["C1"], 0.5)

    def test_method_text_with_indentation_and_offset(self):
        method = "    def close(self):\n        if self.fp is None:\n            return\n        self.fp = None\n"
        ann = annotate_function(method, line_offset=40)
        self.assertEqual(ann["name"], "close")
        self.assertEqual(render_tags(ann), "C1 None-check self.fp is None · C8 sets self.fp")
        self.assertEqual(next(f["line"] for f in ann["facts"] if f["kind"] == "none-check"), 42)


if __name__ == "__main__":
    unittest.main()
