import json
import tempfile
import unittest
from pathlib import Path

from . import corpus
from .engine import build, search, structural_evidence
from .evaluate import binding_score, check_gold_freeze, score


class RetrievalV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.db = Path(cls.temp.name) / "index.sqlite3"
        build(cls.db)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def ids(self, code, **kwargs):
        return [r["concept"]["id"] for r in search(code=code, db=self.db, **kwargs)["results"]]

    def test_source_grounding_and_templates(self):
        result = corpus.verify()
        self.assertEqual(result["original_cards"], 132)
        self.assertEqual(result["extended_cards"], 162)
        self.assertEqual(result["new_semantic_cards"], 30)

    def test_known_index_miss_is_repaired(self):
        self.assertEqual(self.ids("def f(items):\n return items[len(items)]", top_k=1), ["py.index-out-of-bounds"])

    def test_renaming_does_not_change_index_evidence(self):
        for code in ("def f(items):\n return items[len(items)]", "def unrelated_name(xyz):\n return xyz[len(xyz)]"):
            self.assertEqual(self.ids(code, top_k=1), ["py.index-out-of-bounds"])

    def test_generic_return_does_not_retrieve_finally_or_dunder(self):
        self.assertEqual(self.ids("def f(a,b):\n return a+b"), [])

    def test_annotations_are_not_runtime_indexing(self):
        code = "from typing import List\ndef f(xs: List[int]) -> List[int]:\n return xs"
        self.assertNotIn("py.index-out-of-bounds", self.ids(code, top_k=100))

    def test_late_binding_in_comprehension(self):
        self.assertEqual(self.ids("def f(xs):\n return [lambda: x for x in xs]", top_k=1), ["py.late-bound-closure"])

    def test_mutable_default_and_finally_are_preserved(self):
        self.assertEqual(self.ids("def f(x, out=[]):\n out.append(x)\n return out", top_k=1), ["py.mutable-default"])
        self.assertEqual(self.ids("def f():\n try:\n  raise ValueError()\n finally:\n  return 1", top_k=1), ["py.finally-overrides-control-flow"])

    def test_finally_evidence_does_not_enter_nested_function(self):
        code = "def f():\n try:\n  pass\n finally:\n  def cleanup():\n   return 1\n  cleanup()"
        self.assertNotIn("py.finally-overrides-control-flow", self.ids(code, top_k=100))

    def test_statement_append_is_not_a_consumed_return_value(self):
        code = "def f(xs):\n out=[]\n for x in xs:\n  out.append(x)\n return out"
        self.assertNotIn("py.mutator-return-none", self.ids(code, top_k=100))

    def test_consumed_mutator_return_is_detected(self):
        self.assertIn("py.mutator-return-none", self.ids("def f(xs):\n return xs.sort()"))

    def test_module_aliases_and_shadowed_aliases(self):
        positive = "import os.path as paths\ndef f(a,b):\n return paths.commonprefix([a,b])"
        self.assertEqual(self.ids(positive, top_k=1), ["py.path-character-prefix"])
        negative = "import os\ndef f(os,a,b):\n return os.path.commonprefix([a,b])"
        self.assertNotIn("py.path-character-prefix", self.ids(negative, top_k=100))

    def test_extremum_sentinel_remembers_initial_assignment(self):
        code = "def pick(values):\n best=0\n for item in values:\n  if item>best:\n   best=item\n return best"
        self.assertIn("py.extremum-initial-sentinel", self.ids(code))

    def test_no_target_execution(self):
        marker = Path(self.temp.name) / "not-executed"
        self.ids("from pathlib import Path\nPath(" + repr(str(marker)) + ").touch()")
        self.assertFalse(marker.exists())

    def test_syntax_error_fallback_and_text_search(self):
        result = search("B006", code="def bad(", db=self.db)
        self.assertIn("lexical fallback", result["warning"])
        self.assertEqual(result["results"][0]["concept"]["id"], "py.mutable-default")
        self.assertEqual(search("B038", top_k=1, db=self.db)["results"][0]["concept"]["id"], "py.mutate-while-iterating")

    def test_evidence_cites_source_lines(self):
        result = search(code="def f(xs):\n return xs[len(xs)]", db=self.db)
        for hit in result["results"]:
            self.assertTrue(hit["evidence"])
            self.assertTrue(all(r["line"] >= 1 and r["expression"] for r in hit["evidence"]))

    def test_matching_family_on_wrong_site_is_not_a_bound_hit(self):
        sites = {"py.branch-boundary-contract": [{"line": 8}]}
        hit = {"concept": {"id": "py.branch-boundary-contract"}, "evidence": [{"line": 3}, {"line": 8}]}
        self.assertEqual(binding_score([hit], sites), {"first_site_hit_at_3": False, "any_site_hit_at_3": True})
        hit["evidence"] = [{"line": 3}]
        self.assertEqual(binding_score([hit], sites), {"first_site_hit_at_3": False, "any_site_hit_at_3": False})

    def test_wrong_family_on_right_site_is_not_a_bound_hit(self):
        hit = {"concept": {"id": "py.index-out-of-bounds"}, "evidence": [{"line": 8}]}
        self.assertFalse(binding_score([hit], {"py.branch-boundary-contract": [{"line": 8}]})["any_site_hit_at_3"])

    def test_score_obeys_top_three_and_empty_gold(self):
        self.assertFalse(score(["a", "b", "c", "d"], ["d"])["hit_at_3"])
        self.assertFalse(score(["a"], [])["hit_at_3"])
        self.assertEqual(score(["b", "a"], ["a"])["rank"], 2)

    def test_gold_and_input_manifests_are_still_frozen(self):
        check_gold_freeze()

    def test_at_most_three_sites_are_returned_per_concept(self):
        result = search(code="def f(x):\n if x == 1: return 1\n if x == 2: return 2\n if x == 3: return 3\n if x == 4: return 4\n return 0", db=self.db)
        self.assertTrue(all(len(h["evidence"]) <= 3 for h in result["results"]))


if __name__ == "__main__":
    unittest.main()
