import argparse
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from testeval_py.feedback_loop import evaluate_target, run


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
    "target_lines": [7],
    "blocks": [],
}


class FeedbackLoopTests(unittest.TestCase):
    def test_target_evaluator_distinguishes_not_covered_and_covered(self):
        miss = "def test_twoSum():\n    solution = Solution()\n    solution.twoSum([1, 2], 4)"
        hit = "def test_twoSum():\n    solution = Solution()\n    solution.twoSum([1, 2], 3)"

        self.assertEqual(evaluate_target(RECORD, miss, 7)["status"], "not_covered")
        self.assertEqual(evaluate_target(RECORD, hit, 7)["status"], "covered")

    def test_feedback_loop_retries_only_until_target_is_covered(self):
        with tempfile.TemporaryDirectory() as td:
            input_path = Path(td) / "input.jsonl"
            output_path = Path(td) / "output.jsonl"
            input_path.write_text(json.dumps(RECORD) + "\n")
            args = argparse.Namespace(
                input=str(input_path), paths=None, out=str(output_path), cache=None,
                mode="line", prompt_mode="baseline", limit=0, max_targets=1,
                rounds=2, test_timeout=5, temperature=0.0, request_timeout=1.0,
                max_output_tokens=4096, dry_run=False,
            )
            llm = _SequenceLLM([
                "def test_twoSum():\n    solution = Solution()\n    solution.twoSum([1, 2], 4)",
                "def test_twoSum():\n    solution = Solution()\n    solution.twoSum([1, 2], 3)",
            ])

            run(args, llm_factory=lambda temperature, timeout, max_tokens: llm)

            row = json.loads(output_path.read_text())
            self.assertIn("[1, 2], 3", row["tests"]["7"])
            self.assertEqual(llm.calls, 2)


class _SequenceLLM:
    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        return SimpleNamespace(content=next(self.outputs))


if __name__ == "__main__":
    unittest.main()
