import argparse
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from concept_annotator_py import annotate_record
from testeval_py.llm_runner import (
    PROMPT_VERSION,
    _chat,
    _default_llm_factory,
    build_branch_prompt,
    build_line_prompt,
    clean_model_output,
    result_record,
    run,
)


RECORD = {
    "task_num": 1,
    "task_title": "Two Sum",
    "difficulty": 0,
    "func_name": "twoSum",
    "description": "Return indices of two numbers that add up to target.",
    "python_solution": """class Solution:
    def twoSum(self, nums, target):
        seen = {}
        for i, x in enumerate(nums):
            need = target - x
            if need in seen:
                return [seen[need], i]
            seen[x] = i
        return []
""",
    "target_lines": [6],
    "blocks": [{"type": "if", "start": 6, "end": 7}],
}


class TestEvalPyLLMTests(unittest.TestCase):
    def setUp(self):
        self.record = annotate_record(RECORD)
        self.annotation = self.record["concept_annotation_py"]

    def test_line_prompt_contains_target_and_python_concepts(self):
        prompt = build_line_prompt(self.record, self.annotation, self.annotation["line_targets"][0])

        self.assertIn("target line 6", prompt)
        self.assertIn("Target-specific symbolic concept", prompt)
        self.assertIn("required path constraint", prompt)
        self.assertIn("enumerate(nums) must produce at least one iteration", prompt)
        self.assertIn("def twoSum", prompt)
        self.assertIn("def test_twoSum():", prompt)
        self.assertIn("Do not return explanations", prompt)

    def test_branch_prompt_contains_condition(self):
        prompt = build_branch_prompt(self.record, self.annotation, self.annotation["branch_targets"][0])

        self.assertIn("target branch", prompt)
        self.assertIn("need in seen", prompt)
        self.assertIn("branch must execute", prompt)

    def test_clean_model_output_keeps_one_python_test(self):
        raw = "Here is the test:\n```python\ndef test_twoSum():\n    solution = Solution()\n```"

        self.assertEqual(clean_model_output(raw), "def test_twoSum():\n    solution = Solution()")

    def test_chat_extracts_text_from_vertex_content_blocks(self):
        llm = _SequenceLLM(
            [[{"type": "text", "text": "```python\ndef test_twoSum():\n    Solution().twoSum([1, 2], 3)\n```", "thought_signature": "private"}]]
        )

        generated = _chat(llm, "prompt")

        self.assertEqual(generated, "def test_twoSum():\n    Solution().twoSum([1, 2], 3)")
        self.assertNotIn("private", generated)

    def test_chat_rejects_unittest_instance_method(self):
        llm = _SequenceLLM(["def test_twoSum(self):\n    self.assertEqual(Solution().twoSum([1, 2], 3), [0, 1])"])

        with self.assertRaisesRegex(ValueError, "zero parameters"):
            _chat(llm, "prompt")

    def test_result_record_matches_testeval_targeted_line_shape(self):
        row = result_record(self.record, "line", {6: "def test_twoSum():\n    solution = Solution()"})

        self.assertEqual(row["task_num"], 1)
        self.assertEqual(row["func_name"], "twoSum")
        self.assertEqual(row["tests"]["6"].splitlines()[0], "def test_twoSum():")
        self.assertNotIn("concept_annotation_py", row)

    def test_runner_checkpoints_each_target_and_resumes_after_failure(self):
        record = dict(RECORD)
        record["target_lines"] = [6, 7]

        with tempfile.TemporaryDirectory() as td:
            input_path = Path(td) / "input.jsonl"
            output_path = Path(td) / "output.jsonl"
            cache_path = Path(td) / "cache.jsonl"
            input_path.write_text(json.dumps(record) + "\n")
            args = argparse.Namespace(
                input=str(input_path),
                paths=None,
                out=str(output_path),
                cache=str(cache_path),
                mode="line",
                limit=0,
                max_targets=0,
                temperature=0.0,
                request_timeout=1.0,
                max_output_tokens=4096,
                retries=0,
                retry_sleep=0.0,
                dry_run=False,
                fail_fast=True,
            )

            first_llm = _SequenceLLM(["def test_twoSum():\n    Solution().twoSum([1, 2], 3)", RuntimeError("timeout")])
            with self.assertRaises(RuntimeError):
                run(args, llm_factory=lambda temperature, timeout, max_tokens: first_llm)

            cached = [json.loads(line) for line in cache_path.read_text().splitlines()]
            self.assertEqual(len(cached), 1)
            self.assertEqual(cached[0]["key"], f"{PROMPT_VERSION}:line:1:6")

            resumed_llm = _SequenceLLM(["def test_twoSum():\n    Solution().twoSum([3, 3], 6)"])
            run(args, llm_factory=lambda temperature, timeout, max_tokens: resumed_llm)

            result = json.loads(output_path.read_text())
            self.assertEqual(set(result["tests"]), {"6", "7"})
            self.assertEqual(resumed_llm.calls, 1)

    def test_default_factory_forwards_request_timeout_and_disables_nested_retries(self):
        sentinel = object()
        with patch("magma.llm_client.make_llm", return_value=sentinel) as make_llm:
            result = _default_llm_factory(0.2, 17.0, 4096)

        self.assertIs(result, sentinel)
        make_llm.assert_called_once_with(temperature=0.2, timeout=17.0, max_retries=0, max_tokens=4096)

    def test_runner_does_not_resume_from_unversioned_ast_prompt_output(self):
        with tempfile.TemporaryDirectory() as td:
            input_path = Path(td) / "input.jsonl"
            output_path = Path(td) / "output.jsonl"
            input_path.write_text(json.dumps(RECORD) + "\n")
            old_row = result_record(RECORD, "line", {6: "def test_twoSum():\n    raise AssertionError"})
            old_row.pop("prompt_version")
            output_path.write_text(json.dumps(old_row) + "\n")
            args = argparse.Namespace(
                input=str(input_path),
                paths=None,
                out=str(output_path),
                cache=None,
                mode="line",
                limit=1,
                max_targets=1,
                temperature=0.0,
                request_timeout=1.0,
                max_output_tokens=4096,
                retries=0,
                retry_sleep=0.0,
                dry_run=False,
                fail_fast=True,
            )
            llm = _SequenceLLM(["def test_twoSum():\n    Solution().twoSum([1, 2], 3)"])

            run(args, llm_factory=lambda temperature, timeout, max_tokens: llm)

            self.assertEqual(llm.calls, 1)
            self.assertEqual(json.loads(output_path.read_text())["prompt_version"], PROMPT_VERSION)


class _SequenceLLM:
    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        result = next(self.outputs)
        if isinstance(result, Exception):
            raise result
        return SimpleNamespace(content=result)


if __name__ == "__main__":
    unittest.main()
