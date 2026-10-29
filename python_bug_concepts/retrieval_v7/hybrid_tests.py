"""Engineering tests for recall/binding invariants, not model efficacy."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from .hybrid_engine import Retriever, Lexical, fuse, digest, test_packet


class HybridTests(unittest.TestCase):
    def setUp(self):
        self.r = Retriever()

    def tearDown(self):
        self.r.close()

    def test_bm25_can_recall_without_structural_evidence(self):
        out = self.r.search("B006 mutable default argument", code="def f(x):\n return x+1\n")
        self.assertIn("py.mutable-default", out["branch_top12"]["bm25"])
        self.assertNotIn("py.mutable-default", out["branch_top12"]["structural"])

    def test_dense_channel_nominates_outside_recognizer(self):
        cid = "py.mutable-default"
        with patch.object(self.r, "_dense_rank", return_value=[(cid, 1.0)]):
            out = self.r.search(code="def f(x):\n return x+1\n", arm="B")
        candidate = next(c for c in out["candidates"] if c["concept_id"] == cid)
        self.assertTrue(candidate["dense_outside_structural"])
        self.assertFalse(candidate["recognized_candidate"])
        hit = next(h for h in out["results"] if h["concept"]["id"] == cid)
        self.assertEqual(hit["mechanism_support"]["tier"], 0)
        self.assertEqual(hit["instantiated"]["recognition"], "similarity_only_unknown")
        self.assertIsNone(hit["instantiated"]["what"]["expected_output"])
        self.assertTrue(all(r["status"] == "unknown" for r in hit["instantiated"]["required_conditions"]))

    def test_no_dense_fallback(self):
        with self.assertRaisesRegex(ValueError, "requires.*Encoder"):
            self.r.search(code="def f(x):\n return x\n", arm="D")

    def test_runtime_does_not_execute_target(self):
        with tempfile.TemporaryDirectory() as d:
            marker = Path(d) / "never"
            source = f"from pathlib import Path\nPath({str(marker)!r}).touch()\ndef f(x):\n return x\n"
            self.r.search(code=source)
            self.assertFalse(marker.exists())

    def test_source_span_exact_and_packet_keeps_site(self):
        source = 'def f(xs):\n """Return an item from a list."""\n return xs[len(xs)]\n'
        for h in self.r.search(code=source)["results"]:
            b = h["instantiated"]["where"]
            self.assertTrue(b["fact_id"])
            self.assertIn(h["evidence"][0]["expression"], source)
            packet = test_packet(h)
            self.assertEqual(packet["source_site"], b)
            self.assertEqual({k:v for k,v in packet.items() if k != "concept_id"}, test_packet(h, factual=True))

    def test_filters_apply_before_budget(self):
        out = self.r.search("state", code="def f(x, xs=[]):\n xs.append(x)\n return xs\n", category="state")
        self.assertTrue(all(c["concept"]["category"] == "state" for c in out["results"]))
        self.assertLessEqual(len(out["candidates"]), 12)
        self.assertLessEqual(len(out["results"]), 3)
        self.assertEqual(len(out["candidates"]), len({r["concept_id"] for r in out["candidates"]}))

    def test_bad_source_not_fake_binding(self):
        with self.assertRaisesRegex(ValueError, "scoped source unavailable"):
            self.r.search(code="def bad(")

    def test_views_and_digest_change_with_overlay(self):
        self.assertNotEqual(digest(self.r._views[False]), digest(self.r._views[True]))
        self.assertEqual(len(self.r.cards), 162)

    def test_current_packet_does_not_receive_overlay_requirements(self):
        code = 'def f(x, xs=[]):\n """Return accumulated items."""\n xs.append(x)\n return xs\n'
        current = self.r.search(code=code, arm="A")
        revised = self.r.search(code=code, arm="C")
        for h in current["results"]:
            self.assertTrue(all(r["id"].startswith("original-precondition-")
                                for r in h["instantiated"]["required_conditions"]))
        self.assertNotEqual(current["representation_sha256"], revised["representation_sha256"])

    def test_site_cap_reports_omission_without_channel_priority(self):
        code = 'def f(x):\n' + ''.join(f' x = x + {i}\n' for i in range(80)) + ' return x\n'
        out = self.r.search(code=code)
        self.assertEqual(out["source_site_count"], 64)
        self.assertGreater(out["source_sites_omitted"], 0)

    def test_branch_fusion_deterministic(self):
        self.assertEqual(fuse([[('a', 20), ('b', 10)], [('b', 0.9)]]), fuse([['a', 'b'], ['b']]))

    def test_lexical_special_characters_safe(self):
        idx = Lexical({"x": "mutable default", "y": "unicode"})
        try:
            self.assertEqual(idx.ranking('" OR * - ( mutable')[0][0], "x")
            self.assertEqual(idx.ranking(""), [])
        finally:
            idx.close()

    def test_dense_similarity_cannot_restore_excluded_site(self):
        cid = "py.index-out-of-bounds"
        code = 'def f(xs: list):\n """Return first element, or None if empty."""\n if not xs: return None\n return xs[0]\n'
        with patch.object(self.r, "_dense_rank", return_value=[(cid, 1.0)]):
            out = self.r.search(code=code, arm="B")
        for h in out["results"]:
            if h["concept"]["id"] == cid:
                forbidden = {x.get("fact_id") for x in out["excluded_bindings"] if x["concept_id"] == cid}
                self.assertNotIn(h["evidence"][0]["fact_id"], forbidden)
                self.assertNotEqual(h["instantiated"]["recognition"], "existing_v6_relation")


if __name__ == "__main__":
    unittest.main()
