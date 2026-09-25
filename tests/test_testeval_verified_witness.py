import unittest

from testeval_py.verified_witness import _candidate_arguments, find_verified_witnesses


THREE_SUM = """class Solution:
  def threeSum(self, nums: list[int]):
    if len(nums) < 3:
      return []
    nums.sort()
    ans = []
    for i in range(len(nums) - 2):
      if i > 0 and nums[i] == nums[i - 1]:
        continue
      l = i + 1
      r = len(nums) - 1
      while l < r:
        summ = nums[i] + nums[l] + nums[r]
        if summ == 0:
          ans.append((nums[i], nums[l], nums[r]))
          l += 1
          r -= 1
          while nums[r] == nums[r + 1] and l < r:
            r -= 1
        elif summ < 0:
          l += 1
        else:
          r -= 1
    return ans
"""


class VerifiedWitnessTests(unittest.TestCase):
    def test_finds_fresh_execution_witness_for_duplicate_skip(self):
        lines = THREE_SUM.splitlines()
        target = next(
            i for i, line in enumerate(lines, 1)
            if line.strip() == "r -= 1" and lines[i - 2].strip().startswith("while nums[r]")
        )
        record = {
            "python_solution": THREE_SUM,
            "func_name": "threeSum",
            "description": "Given an integer array nums, return all zero-sum triplets.",
            "target_lines": [target],
        }

        result = find_verified_witnesses(record, seconds=2, max_candidates=800)

        self.assertTrue(result["supported"])
        self.assertIn(target, result["witnesses"])
        witness = result["witnesses"][target]
        self.assertEqual(witness["target_line"], target)
        self.assertEqual(witness["recent_lines"][-1], target)
        self.assertIn("solution.threeSum(", witness["call"])
        self.assertIn("r", witness["locals_at_target"])

    def test_skips_unsupported_dictionary_argument(self):
        record = {
            "python_solution": "class Solution:\n  def f(self, a: dict[str, int]):\n    return a['x']\n",
            "func_name": "f",
            "target_lines": [3],
        }
        result = find_verified_witnesses(record, seconds=1)
        self.assertFalse(result["supported"])
        self.assertEqual(result["witnesses"], {})

    def test_candidate_search_respects_obvious_description_constraints(self):
        median = list(_candidate_arguments(("int_list", "int_list"), "median of two sorted arrays"))
        self.assertTrue(median)
        self.assertTrue(all(a or b for a, b in median))
        self.assertTrue(all(a == sorted(a) and b == sorted(b) for a, b in median))
        triplets = list(_candidate_arguments(("int_list",), "Return all zero-sum triplets"))
        self.assertTrue(all(len(args[0]) >= 3 for args in triplets))


if __name__ == "__main__":
    unittest.main()
