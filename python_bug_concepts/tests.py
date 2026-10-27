"""Corpus integrity and retrieval smoke checks, not efficacy evaluation."""

import json
import shutil
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from .base import (
    ROOT, build_index, get_concept, load_jsonl, render, search, validate,
)
from .ingest import bugbear_patterns, python_patterns, ruff_patterns


class ConceptBaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.db = Path(cls.directory.name) / "index.sqlite3"
        cls.stats = build_index(cls.db)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def ids(self, query="", **kwargs):
        return [r["concept"]["id"] for r in search(query, db=self.db, **kwargs)["results"]]

    def test_all_cards_have_valid_templates_and_evidence(self):
        stats = validate()
        self.assertEqual(stats["concepts"], 132)
        self.assertEqual(stats["patterns"], 279)
        self.assertEqual(stats["source_files"], 172)
        self.assertEqual(stats["linked_patterns"], 248)
        self.assertEqual(stats["excluded_patterns"], 31)
        self.assertEqual(stats["unresolved_patterns"], 0)
        for raw in json.loads((ROOT / "data/concepts.json").read_text()):
            card = get_concept(raw["id"], self.db)
            output = render(card, {slot: f"bound_{slot}" for slot in card["required_bindings"]})
            self.assertEqual(set(output), {"where", "how", "what"})
            self.assertTrue(all("{" not in value for value in output.values()))
            self.assertTrue(all(s["revision"] and s["sha256"] and s["url"] for s in card["sources"]))

    def test_offline_ingestion_reproduces_checked_in_patterns(self):
        records = sorted(ruff_patterns() + bugbear_patterns() + python_patterns(), key=lambda r: r["id"])
        self.assertEqual(records, load_jsonl(ROOT / "data/patterns.jsonl"))

    def test_natural_language_retrieval(self):
        probes = [
            ("mutable default list shared between calls", "py.mutable-default"),
            ("lambda loop closure callbacks final value", "py.late-bound-closure"),
            ("return finally swallowed exception", "py.finally-overrides-control-flow"),
            ("dict.fromkeys shared mutable values", "py.fromkeys-shared-value"),
            ("strip substring prefix", "py.strip-character-set"),
            ("zip unequal lengths strict", "py.zip-truncates"),
            ("floor division negative", "py.floor-division-negatives"),
            ("pytest.raises wrong exception", "py.broad-raises-oracle"),
        ]
        for query, expected in probes:
            with self.subTest(query=query):
                self.assertEqual(self.ids(query, top_k=1), [expected])

    def test_vietnamese_with_and_without_diacritics(self):
        for query in ("tham số mặc định", "tham so mac dinh", "biến mặc định danh sách chia sẻ"):
            with self.subTest(query=query):
                self.assertIn("py.mutable-default", self.ids(query, top_k=3))

    def test_newly_curated_mechanisms_are_retrievable(self):
        for query, expected in [
            ("os.path.commonprefix path component", "py.path-character-prefix"),
            ("logging message argument count mismatch", "py.logging-format-arguments"),
            ("AST visitor generic_visit missing recursion", "py.ast-visitor-no-recursion"),
            ("list index out of bounds", "py.index-out-of-bounds"),
            ("exception pickle copy args", "py.exception-roundtrip"),
            ("getenv default non string", "py.getenv-type-contract"),
            ("TypeVar covariant contravariant", "py.typevar-conflicting-variance"),
        ]:
            with self.subTest(query=query):
                self.assertIn(expected, self.ids(query, top_k=3))

    def test_rule_code_retrieval(self):
        self.assertEqual(self.ids("B006", top_k=1), ["py.mutable-default"])
        self.assertEqual(self.ids("B023", top_k=1), ["py.late-bound-closure"])
        self.assertEqual(self.ids("B038", top_k=1), ["py.mutate-while-iterating"])
        self.assertEqual(self.ids("PLE0643", top_k=1), ["py.index-out-of-bounds"])
        self.assertEqual(self.ids("PLE0118", top_k=1), ["py.scope-declaration-conflict"])

    def test_code_retrieval(self):
        for file, expected in [
            ("mutable_default.py", "py.mutable-default"),
            ("closure_loop.py", "py.late-bound-closure"),
            ("finally_cleanup.py", "py.finally-overrides-control-flow"),
        ]:
            with self.subTest(file=file):
                self.assertEqual(self.ids(code=(ROOT / "examples" / file).read_text(), top_k=1), [expected])

    def test_code_is_not_executed(self):
        marker = Path(self.directory.name) / "must_not_exist"
        code = f"from pathlib import Path\nPath({str(marker)!r}).touch()\n"
        self.ids(code=code)
        self.assertFalse(marker.exists())

    def test_partial_code_falls_back_to_lexical_retrieval(self):
        result = search("mutable default B006", code="def broken(", db=self.db)
        self.assertIn("lexical retrieval only", result["warning"])
        self.assertEqual(result["results"][0]["concept"]["id"], "py.mutable-default")

    def test_filters_are_applied_before_limit(self):
        results = search("class shared state", source="cpython", category="state", top_k=1, db=self.db)["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["concept"]["category"], "state")
        self.assertTrue(any(s["source"] == "cpython" for s in results[0]["concept"]["sources"]))
        self.assertNotEqual(results[0]["concept"]["id"], self.ids("class shared state", category="state", top_k=1)[0])
        for result in search("exception", category="exceptions", source="ruff", top_k=100, db=self.db)["results"]:
            self.assertEqual(result["concept"]["category"], "exceptions")
            self.assertTrue(any(s["source"] == "ruff" for s in result["concept"]["sources"]))

    def test_field_search(self):
        for field, query, expected in [
            ("where", "finally", "py.finally-overrides-control-flow"),
            ("how", "character set", "py.strip-character-set"),
            ("what", "unmatched suffix", "py.zip-truncates"),
        ]:
            with self.subTest(field=field):
                self.assertIn(expected, self.ids(query, field=field, top_k=3))

    def test_plain_text_query_cannot_change_fts_or_sql(self):
        for query in ('" OR title:* NOT (', "'; DROP TABLE concepts; --", "{} [] :::"):
            self.ids(query)
        self.assertEqual(len(self.ids("B006", top_k=1)), 1)

    def test_empty_and_unmatched_query(self):
        self.assertEqual(self.ids(""), [])
        self.assertEqual(self.ids("the and là của"), [])
        self.assertEqual(self.ids("qzjxxunmatchedtoken"), [])

    def test_template_requires_complete_bindings(self):
        card = get_concept("py.mutable-default", self.db)
        with self.assertRaisesRegex(ValueError, "Missing template bindings"):
            render(card, {"function": "collect"})
        bindings = json.loads((ROOT / "examples/mutable_default_bindings.json").read_text())
        result = render(card, bindings)
        self.assertIn("collect", result["how"])
        self.assertIn("empty collection", result["what"])

    def test_removed_and_preview_sources_remain_labeled(self):
        patterns = {p["id"]: p for p in load_jsonl(ROOT / "data/patterns.jsonl")}
        self.assertEqual(patterns["ruff:RUF011"]["status"], "removed")
        self.assertEqual(patterns["ruff:B909"]["status"], "preview")

    def test_source_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            copy = Path(folder) / "corpus"
            shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns("*.sqlite3", "__pycache__"))
            file = copy / "sources/flake8-bugbear/README.rst"
            file.write_text(file.read_text() + "\nmodified\n")
            with self.assertRaisesRegex(ValueError, "Source hash mismatch"):
                validate(copy)

    def test_every_raw_record_has_one_review_disposition(self):
        coverage = json.loads((ROOT / "data/coverage.json").read_text())
        decisions = coverage["pattern_decisions"]
        self.assertEqual(len(decisions), 279)
        self.assertEqual({d["pattern_id"] for d in decisions}, {p["id"] for p in load_jsonl(ROOT / "data/patterns.jsonl")})
        self.assertEqual(coverage["unresolved_pattern_count"], 0)
        self.assertEqual(coverage["unresolved_patterns"], [])
        self.assertEqual(sum(d["disposition"] == "mapped" for d in decisions), 248)
        self.assertEqual(sum(d["disposition"] == "excluded" for d in decisions), 31)
        for decision in decisions:
            if decision["disposition"] == "mapped":
                self.assertTrue(decision["concept_ids"])
                for concept_id in decision["concept_ids"]:
                    self.assertIn(decision["pattern_id"], get_concept(concept_id, self.db)["pattern_ids"])
            else:
                self.assertTrue(decision["reason"].strip())

    def test_unreviewed_record_cannot_be_hidden_by_exports(self):
        with tempfile.TemporaryDirectory() as folder:
            copy = Path(folder) / "corpus"
            shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns("*.sqlite3", "__pycache__"))
            path = copy / "data/exclusions.json"
            decisions = json.loads(path.read_text())
            removed = decisions.pop()
            path.write_text(json.dumps(decisions))
            with self.assertRaisesRegex(ValueError, "Unresolved patterns: " + removed["pattern_id"]):
                build_index(copy / "test.sqlite3", root=copy)

    def test_exclusion_requires_a_reason_and_cannot_hide_a_mapped_record(self):
        with tempfile.TemporaryDirectory() as folder:
            copy = Path(folder) / "corpus"
            shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns("*.sqlite3", "__pycache__"))
            path = copy / "data/exclusions.json"
            decisions = json.loads(path.read_text())
            decisions.append({"pattern_id": "ruff:B006", "kind": "style", "reason": ""})
            path.write_text(json.dumps(decisions))
            with self.assertRaisesRegex(ValueError, "both mapped and excluded: ruff:B006"):
                validate(copy)
            with self.assertRaisesRegex(ValueError, "Missing exclusion reason: ruff:B006"):
                validate(copy)

    def test_exclusion_decisions_invalidate_the_cached_index(self):
        with tempfile.TemporaryDirectory() as folder:
            copy = Path(folder) / "corpus"
            shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns("*.sqlite3", "__pycache__"))
            db = copy / "test.sqlite3"
            build_index(db, root=copy)
            with closing(sqlite3.connect(db)) as conn:
                before = conn.execute("SELECT value FROM metadata WHERE key='corpus_digest'").fetchone()[0]
            path = copy / "data/exclusions.json"
            decisions = json.loads(path.read_text())
            decisions[0]["reason"] += " Review note changed."
            path.write_text(json.dumps(decisions))
            get_concept("py.mutable-default", db=db, root=copy)
            with closing(sqlite3.connect(db)) as conn:
                after = conn.execute("SELECT value FROM metadata WHERE key='corpus_digest'").fetchone()[0]
            self.assertNotEqual(before, after)

    def test_stale_index_is_rebuilt(self):
        path = Path(self.directory.name) / "stale.sqlite3"
        build_index(path)
        with closing(sqlite3.connect(path)) as conn, conn:
            conn.execute("UPDATE metadata SET value='stale' WHERE key='corpus_digest'")
            conn.execute("DELETE FROM concepts WHERE id='py.mutable-default'")
        self.assertEqual(get_concept("py.mutable-default", path)["id"], "py.mutable-default")

    def test_argument_validation(self):
        with self.assertRaisesRegex(ValueError, "top_k"):
            search("hello", top_k=0, db=self.db)
        with self.assertRaisesRegex(ValueError, "Unknown search field"):
            search("hello", field="bad", db=self.db)
        with self.assertRaisesRegex(ValueError, "Unknown concept"):
            get_concept("missing", self.db)


if __name__ == "__main__":
    unittest.main()
