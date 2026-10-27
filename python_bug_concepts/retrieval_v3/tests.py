import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from .client import Client
from . import prompts
from .run import validate_judge, verify_inputs
from .grade_utility import equal, valid_tests
from .report import discounted


class QualityRetrievalTests(unittest.TestCase):
    def test_input_snapshot_is_unchanged(self):
        verify_inputs()

    def test_retrieval_prompt_has_no_task_identifier_or_grading_payload(self):
        task = {"task_id": "HumanEval/private", "code": "def f(xs):\n return xs[len(xs)]"}
        text = json.dumps(prompts.retrieval(task))
        self.assertNotIn(task["task_id"], text)
        for field in ("canonical_solution", "gold_witness", "accepted_concepts", "validated_witness"):
            self.assertNotIn(field, text)
        self.assertIn("C001", text)

    def test_selection_ids_and_lines_are_validated(self):
        value = {"status": "received", "parsed": {"selected": [{"id": "C001", "line": 2, "where": "x", "how": "y", "what": "z"}]}}
        rows, error = prompts.parse_retrieval(value, "def f():\n return 1")
        self.assertIsNone(error)
        self.assertEqual(len(rows), 1)
        value["parsed"]["selected"][0]["line"] = 99
        self.assertEqual(prompts.parse_retrieval(value, "a\nb")[1], "invalid_source_line")
        value["parsed"]["selected"][0]["id"] = "not-a-card"
        self.assertEqual(prompts.parse_retrieval(value, "a\nb")[1], "invalid_catalog_id")

    def test_failed_response_is_not_a_successful_abstention(self):
        self.assertEqual(prompts.parse_retrieval({"status": "failed"}, "x")[1], "no_valid_retrieval_response")
        self.assertEqual(prompts.parse_retrieval({"status": "received", "parsed": {"selected": []}}, "x"), ([], None))

    def test_decimal_line_normalization_is_explicit(self):
        response = {"status": "received", "parsed": {"selected": [{"id": "C001", "line": "2", "where": "x", "how": "y", "what": "z"}]}}
        rows, error = prompts.parse_retrieval(response, "a\nb")
        self.assertIsNone(error)
        self.assertEqual(rows[0]["line"], 2)
        self.assertTrue(rows[0]["line_normalized_from_string"])

    def test_native_oracle_value_comparison(self):
        self.assertFalse(equal(True, 1))
        self.assertTrue(equal([1.00001, 2], [1, 2], 0.001))
        self.assertFalse(equal([1, 2], [1, 3]))
        self.assertTrue(equal({"a": [1]}, {"a": [1]}))

    def test_utility_parser_rejects_missing_and_nonfinite_values(self):
        response = {"status": "received", "parsed": {"tests": [{"args": [[1]], "expected": 2}]}}
        self.assertIsNone(valid_tests(response)[1])
        response["parsed"]["tests"][0]["expected"] = float("nan")
        self.assertEqual(valid_tests(response)[1], "non_json_or_nonfinite_data")
        response["parsed"]["tests"] = [{"args": []}]
        self.assertEqual(valid_tests(response)[1], "invalid_test_record")

    def test_graded_rank_discount_prefers_relevant_items_first(self):
        self.assertGreater(discounted([3, 1, 0]), discounted([0, 1, 3]))
        self.assertEqual(discounted([0, 0, 0]), 0)

    def test_judge_hides_systems_and_deduplicates_cards(self):
        task = {"code": "def f():\n return 1"}
        row = {"concept_id": "py.mutable-default", "line": 2, "where": "x", "how": "y", "what": "z"}
        messages, mapping = prompts.judge(task, {"secret_method_a": [row], "secret_method_b": [row]}, "reference", None)
        text = json.dumps(messages)
        self.assertNotIn("secret_method_a", text)
        self.assertNotIn("secret_method_b", text)
        self.assertEqual(len(mapping["cards"]), 1)
        self.assertEqual(len(mapping["bindings"]), 2)

    def test_all_judge_keys_and_score_domains_required(self):
        mapping = {"cards": {"K0": "x"}, "bindings": {"B0": {}}}
        response = {"parsed": {"cards": [{"key": "K0", "grade": 2}], "bindings": [{"key": "B0", "where": 1, "how": 0, "what": 1}]}}
        self.assertTrue(validate_judge(response, mapping))
        response["parsed"]["cards"][0]["grade"] = 4
        self.assertFalse(validate_judge(response, mapping))

    def test_utility_has_no_reference_and_matched_hint_format(self):
        task = {"entry_point": "f", "code": "def f(x):\n return x"}
        nohint = prompts.utility(task, [])
        hint = prompts.utility(task, [{"concept_id": "py.mutable-default"}])
        self.assertEqual(nohint[0], hint[0])
        self.assertEqual(json.loads(nohint[1]["content"])["concept_hints"], [])
        self.assertNotIn("canonical_solution", json.dumps(hint))

    def test_transport_does_not_repeat_cached_or_unknown_attempts(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {"CT_RETRIEVAL_BASE_URL": "https://unit.ngrok-free.dev/v1"}):
            client = Client(Path(folder))
            with patch.object(client, "tokens", return_value={"prompt_tokens": 10, "context_limit": 8192}), patch.object(client, "http", return_value={"model": "qwen3.5-27b-awq", "choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}], "usage": {}}) as http:
                one = client.complete([{"role": "user", "content": "test"}], stage="test", max_tokens=10, seed=1)
                two = client.complete([{"role": "user", "content": "test"}], stage="test", max_tokens=10, seed=1)
                self.assertEqual(one, two)
                self.assertEqual(http.call_count, 1)
            with self.assertRaisesRegex(ValueError, "previous_attempt"):
                client.reserve({"request_sha256": one["request_sha256"], "stage": "test"})
            for p in Path(folder).rglob("*.json*"):
                self.assertNotIn("unit.ngrok", p.read_text())

    def test_context_overflow_is_blocked_before_completion(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {"CT_RETRIEVAL_BASE_URL": "https://unit.ngrok-free.dev/v1"}):
            client = Client(Path(folder))
            with patch.object(client, "tokens", return_value={"prompt_tokens": 8100, "context_limit": 8192}), patch.object(client, "http") as http:
                with self.assertRaisesRegex(ValueError, "context_preflight"):
                    client.complete([], stage="test", max_tokens=1200, seed=1)
                http.assert_not_called()


if __name__ == "__main__":
    unittest.main()
