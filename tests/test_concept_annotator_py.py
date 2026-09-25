import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from concept_annotator_py import (
    annotate_record,
    render_prompt_block,
)


PY_SOLUTION = """from typing import List

class Solution:
  def twoSum(self, nums: List[int], target: int) -> List[int]:
    seen = {}
    for i, x in enumerate(nums):
      need = target - x
      if need in seen:
        return [seen[need], i]
      seen[x] = i
    return []
"""


MEDIAN_SOLUTION = """class Solution:
  def findMedianSortedArrays(self, nums1, nums2):
    n1 = len(nums1)
    n2 = len(nums2)
    if n1 > n2:
      return self.findMedianSortedArrays(nums2, nums1)
    return 0
"""


TESTEVAL_RECORD = {
    "task_num": 1,
    "task_title": "Two Sum",
    "difficulty": 0,
    "func_name": "twoSum",
    "description": "Return indices of two numbers that add up to target.",
    "python_solution": PY_SOLUTION,
    "target_lines": [9, 10],
    "blocks": [
        {
            "type": "if",
            "start": 8,
            "end": 9,
            "trigger_condition": "(need in seen)",
            "trigger_condition_with_lineno": "Line 8: (need in seen)",
        },
        {"type": "else", "start": 8, "end": 10},
    ],
}


PATH_RECORD = {
    "task_num": 1,
    "task_title": "Two Sum",
    "sampled_paths": [
        [
            "LOOP #1: Entered for loop at line 6-10\n",
            "BRANCH #1: Covered if branch at line 8-9\n",
        ]
    ],
    "sampled_condition_paths": [["Line 6: (for i, x in enumerate(nums))", "Line 8: (need in seen)"]],
}


class ConceptAnnotatorPyTests(unittest.TestCase):
    def test_target_line_annotation_uses_python_ast_and_control_context(self):
        annotated = annotate_record(TESTEVAL_RECORD, PATH_RECORD)

        ann = annotated["concept_annotation_py"]
        self.assertEqual(ann["schema"], "concept_annotator_py.v4")
        self.assertIn("hash_map", ann["program_concepts"])
        self.assertIn("loop", ann["program_concepts"])
        self.assertIn("membership_test", ann["program_concepts"])

        line_target = ann["line_targets"][0]
        self.assertEqual(line_target["line"], 9)
        self.assertEqual(line_target["ast_node"], "Return")
        self.assertEqual(line_target["code"], "return [seen[need], i]")
        self.assertIn("return_value", line_target["concepts"])
        self.assertIn("subscript", line_target["concepts"])
        self.assertEqual(line_target["reads"], ["seen", "need", "i"])
        self.assertEqual(line_target["writes"], [])
        self.assertEqual(line_target["control_context"][0]["line"], 8)
        self.assertEqual(line_target["control_context"][0]["condition"], "need in seen")

    def test_branch_and_path_annotations_match_testeval_metadata(self):
        ann = annotate_record(TESTEVAL_RECORD, PATH_RECORD)["concept_annotation_py"]

        branch = ann["branch_targets"][0]
        self.assertEqual(branch["start"], 8)
        self.assertEqual(branch["end"], 9)
        self.assertEqual(branch["type"], "if")
        self.assertEqual(branch["condition"], "need in seen")
        self.assertIn("membership_test", branch["concepts"])
        self.assertIn("hash_map_lookup", branch["concepts"])

        path = ann["path_targets"][0]
        self.assertEqual(path["index"], 0)
        self.assertEqual(path["conditions"][0]["line"], 6)
        self.assertEqual(path["conditions"][1]["line"], 8)
        self.assertEqual(path["conditions"][1]["truth"], True)
        self.assertIn("line 8 -> need in seen", path["summary"])

    def test_branch_condition_falls_back_to_python_ast_when_testeval_omits_it(self):
        record = dict(TESTEVAL_RECORD)
        record["blocks"] = [{"type": "if", "start": 8, "end": 9}]

        branch = annotate_record(record)["concept_annotation_py"]["branch_targets"][0]

        self.assertEqual(branch["condition"], "need in seen")
        self.assertIn("membership_test", branch["concepts"])
        self.assertIn("hash_map_lookup", branch["concepts"])

    def test_prompt_block_is_testeval_python_specific(self):
        ann = annotate_record(TESTEVAL_RECORD, PATH_RECORD)["concept_annotation_py"]
        block = render_prompt_block(ann, max_lines=2, max_branches=1, max_paths=1)

        self.assertIn("Reachability facts for the target", block)
        self.assertIn("target L9", block)
        self.assertIn("branch_true: target - x in seen", block)
        self.assertIn("state_before_use: seen already contains target - x", block)
        self.assertIn("loop_two_plus_iteration: seen starts empty", block)
        self.assertNotIn("index_in_bounds: need selects an existing element of seen", block)
        self.assertIn("target - x in seen", block)
        self.assertNotIn("hash_map", block)
        self.assertNotIn("return_value", block)

    def test_symbolic_synthesis_expands_aliases_to_input_constraints(self):
        record = {
            "task_num": 4,
            "task_title": "Median of Two Sorted Arrays",
            "func_name": "findMedianSortedArrays",
            "python_solution": MEDIAN_SOLUTION,
            "target_lines": [6],
            "blocks": [],
        }

        target = annotate_record(record)["concept_annotation_py"]["line_targets"][0]
        symbolic = target["symbolic"]

        self.assertIn("recursive", symbolic["intent"].lower())
        self.assertEqual(symbolic["path_constraints"][0]["source_expression"], "n1 > n2")
        self.assertEqual(symbolic["path_constraints"][0]["input_expression"], "len(nums1) > len(nums2)")
        self.assertEqual(symbolic["input_relations"], ["len(nums1) > len(nums2)"])
        self.assertEqual(symbolic["avoid_relations"], ["len(nums1) <= len(nums2)"])
        self.assertIn("nums1 <- nums2", symbolic["state_transition"])
        self.assertIn("len(nums1) = len(nums2) + 1", symbolic["boundary_strategy"][0])

    def test_symbolic_synthesis_tracks_else_branch_polarity(self):
        record = {
            "task_num": 2,
            "task_title": "Absolute Value",
            "func_name": "absolute",
            "python_solution": """class Solution:
  def absolute(self, x):
    if x > 0:
      return x
    else:
      return -x
""",
            "target_lines": [6],
            "blocks": [],
        }

        symbolic = annotate_record(record)["concept_annotation_py"]["line_targets"][0]["symbolic"]

        self.assertFalse(symbolic["path_constraints"][0]["required_truth"])
        self.assertEqual(symbolic["input_relations"], ["x <= 0"])
        self.assertEqual(symbolic["avoid_relations"], ["x > 0"])

    def test_symbolic_synthesis_does_not_inline_conditional_reassignment(self):
        record = {
            "task_num": 3,
            "task_title": "Conditional Alias",
            "func_name": "first",
            "python_solution": """class Solution:
  def first(self, values, force):
    size = len(values)
    if force:
      size = 1
    if size > 0:
      return values[0]
""",
            "target_lines": [7],
            "blocks": [],
        }

        constraint = annotate_record(record)["concept_annotation_py"]["line_targets"][0]["symbolic"]["path_constraints"][-1]

        self.assertEqual(constraint["source_expression"], "size > 0")
        self.assertEqual(constraint["expanded_expression"], "size > 0")

    def test_target_requires_bypassing_prior_continue_and_updated_loop_state(self):
        record = {
            "task_num": 15,
            "func_name": "threeSum",
            "python_solution": """class Solution:
  def threeSum(self, nums):
    nums.sort()
    for i in range(len(nums) - 2):
      if i > 0 and nums[i] == nums[i - 1]:
        continue
      l = i + 1
      r = len(nums) - 1
      while l < r:
        summ = nums[i] + nums[l] + nums[r]
        if summ == 0:
          l += 1
          r -= 1
          while nums[l] == nums[l - 1] and l < r:
            l += 1
        else:
          l += 1
""",
            "target_lines": [15],
            "blocks": [],
        }
        facts = annotate_record(record)["concept_annotation_py"]["line_targets"][0]["symbolic"]["reachability_facts"]
        self.assertIn({"kind": "avoid_early_exit", "detail": "at L5: not (i > 0 and nums[i] == nums[i - 1])"}, facts)
        self.assertIn(
            {"kind": "state_after_update", "detail": "after `l += 1`, require `nums[l] == nums[l - 1] and l < r`"},
            facts,
        )

    def test_sequence_index_fact_is_not_applied_to_dictionary_assignment(self):
        record = {
            "task_num": 1,
            "func_name": "f",
            "python_solution": """class Solution:
  def f(self, values: list[int]):
    seen = {}
    seen[values[0]] = 1
    return seen[values[0]]
""",
            "target_lines": [4],
            "blocks": [],
        }
        facts = annotate_record(record)["concept_annotation_py"]["line_targets"][0]["symbolic"]["reachability_facts"]
        self.assertTrue(any(f["kind"] == "index_in_bounds" and "values" in f["detail"] for f in facts))
        self.assertFalse(any(f["kind"] == "index_in_bounds" and "seen" in f["detail"] for f in facts))

    def test_cli_merges_testeval_records_with_path_records(self):
        with tempfile.TemporaryDirectory() as td:
            data_path = Path(td) / "leetcode-py.jsonl"
            paths_path = Path(td) / "tgt_paths.jsonl"
            out_path = Path(td) / "annotated.jsonl"
            data_path.write_text(json.dumps(TESTEVAL_RECORD) + "\n")
            paths_path.write_text(json.dumps(PATH_RECORD) + "\n")

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "concept_annotator_py.run",
                    "--in",
                    str(data_path),
                    "--paths",
                    str(paths_path),
                    "--out",
                    str(out_path),
                ],
                check=True,
            )

            rows = [json.loads(line) for line in out_path.read_text().splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["concept_annotation_py"]["line_targets"][0]["line"], 9)
            self.assertEqual(rows[0]["concept_annotation_py"]["path_targets"][0]["index"], 0)


if __name__ == "__main__":
    unittest.main()
