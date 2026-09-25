import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from testeval_py.paper_runner import run


RECORD = {
    "task_num": 1,
    "task_title": "Small branch",
    "difficulty": 1,
    "func_name": "f",
    "description": "Return one for positive values.",
    "python_solution": "class Solution:\n  def f(self, x):\n    if x > 0:\n      return 1\n    return 0\n",
    "target_lines": [4],
    "blocks": [],
}


class FakeLLM:
    def __init__(self):
        self.calls = []

    def invoke(self, messages):
        self.calls.append(messages)
        content = "x > 0" if len(self.calls) == 1 else "def test_f():\n    solution=Solution()\n    solution.f(1)"
        return SimpleNamespace(content=content, response_metadata={"finish_reason": "STOP"})


class TestEvalPaperRunnerTests(unittest.TestCase):
    def test_two_step_uses_official_prompts_and_caches_both_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            (root / "prompt").mkdir()
            (root / "data" / "leetcode-py-all.jsonl").write_text(json.dumps(RECORD) + "\n")
            (root / "prompt" / "system_exec.txt").write_text("SYSTEM")
            (root / "prompt" / "line_oneshot_gencond.txt").write_text("COND {targetline}\n{program}")
            (root / "prompt" / "line_oneshot_gentest.txt").write_text("TEST {func_name}: {conditions}\n{program}")
            data_utils = SimpleNamespace(
                read_jsonl=lambda path: [json.loads(line) for line in path.read_text().splitlines()],
                add_lineno_comment=lambda code: code,
                write_jsonl=lambda rows, path: path.write_text("".join(json.dumps(row) + "\n" for row in rows)),
            )
            formatter = SimpleNamespace(
                remove_extra=lambda test, name: test,
                reformat_case_byrules=lambda test, name: test,
            )
            args = Namespace(
                upstream=str(root),
                out=str(root / "predictions.jsonl"),
                cache=str(root / "cache.jsonl"),
                arm="concept",
                protocol="two-step",
                concept_facts=None,
                limit=1,
                max_targets=0,
                max_output_tokens=None,
                request_timeout=1,
                retries=0,
                retry_sleep=0,
                retry_max_wait=0,
                dry_run=False,
            )
            llm = FakeLLM()
            with patch("testeval_py.paper_runner._upstream_modules", return_value=(data_utils, formatter)):
                run(args, llm=llm)
                cached_llm = FakeLLM()
                run(args, llm=cached_llm)
                reused_args = Namespace(**vars(args))
                reused_args.out = str(root / "reused.jsonl")
                reused_args.cache = str(root / "reused.cache.jsonl")
                reused_args.reuse_cache = [args.cache]
                reused_llm = FakeLLM()
                run(reused_args, llm=reused_llm)

            self.assertEqual(len(llm.calls), 2)
            self.assertEqual(len(cached_llm.calls), 0)
            self.assertEqual(len(reused_llm.calls), 0)
            self.assertEqual(llm.calls[0][0].content, "SYSTEM")
            self.assertTrue(llm.calls[0][1].content.startswith("COND 4\n"))
            self.assertIn("Static facts from program analysis", llm.calls[0][1].content)
            self.assertIn("Use these facts to derive the necessary conditions", llm.calls[0][1].content)
            self.assertTrue(llm.calls[1][1].content.startswith("TEST f: x > 0\n"))
            self.assertNotIn("Static facts from program analysis", llm.calls[1][1].content)
            row = json.loads(Path(args.out).read_text().splitlines()[0])
            self.assertEqual(row["conditions"]["4"], "x > 0")
            self.assertIn("solution.f(1)", row["tests"]["4"])
            self.assertEqual(len(Path(args.cache).read_text().splitlines()), 2)
            self.assertEqual(len(Path(reused_args.cache).read_text().splitlines()), 2)

    def test_witness_is_added_to_condition_and_test_steps(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            (root / "prompt").mkdir()
            (root / "data" / "leetcode-py-all.jsonl").write_text(json.dumps(RECORD) + "\n")
            (root / "prompt" / "system_exec.txt").write_text("SYSTEM")
            (root / "prompt" / "line_oneshot_gencond.txt").write_text("COND {targetline} {program}")
            (root / "prompt" / "line_oneshot_gentest.txt").write_text("TEST {func_name}: {conditions} {program}")
            data_utils = SimpleNamespace(
                read_jsonl=lambda path: [json.loads(line) for line in path.read_text().splitlines()],
                add_lineno_comment=lambda code: code,
                write_jsonl=lambda rows, path: path.write_text("".join(json.dumps(row) + "\n" for row in rows)),
            )
            formatter = SimpleNamespace(
                remove_extra=lambda test, name: test,
                reformat_case_byrules=lambda test, name: test,
            )
            args = Namespace(
                upstream=str(root), out=str(root / "predictions.jsonl"), cache=str(root / "cache.jsonl"),
                arm="concept-witness", protocol="two-step", concept_facts=None, limit=1, max_targets=0,
                task_num=None, target_line=None, max_output_tokens=None, request_timeout=1, retries=0,
                retry_sleep=0, retry_max_wait=0, dry_run=False, witness_seconds=1.0,
                witness_max_candidates=10, witness_fallback=True, reuse_cache=[],
            )
            llm = FakeLLM()
            witness = {
                "supported": True, "tried": 1, "timed_out": False,
                "witnesses": {4: {
                    "call": "solution.f([1])", "target_line": 4,
                    "recent_lines": [2, 3, 4], "locals_at_target": {"x": 1},
                }},
            }
            with patch("testeval_py.paper_runner._upstream_modules", return_value=(data_utils, formatter)):
                with patch("testeval_py.verified_witness.find_verified_witnesses", return_value=witness):
                    run(args, llm=llm)

            self.assertIn("Static facts from program analysis", llm.calls[0][1].content)
            self.assertIn("Verified execution witness", llm.calls[0][1].content)
            self.assertIn("Use these facts to derive", llm.calls[0][1].content)
            self.assertIn("Generated conditions above", llm.calls[1][1].content)
            self.assertIn("Verified execution witness", llm.calls[1][1].content)
            self.assertIn("satisfies both", llm.calls[1][1].content)

    def test_verified_witness_replaces_test_that_misses_target(self):
        record = {
            **RECORD,
            "python_solution": (
                "class Solution:\n  def f(self, xs: list[int]):\n"
                "    if len(xs) > 1:\n      return 1\n    return 0\n"
            ),
        }
        witness = {
            "supported": True, "tried": 1, "timed_out": False,
            "witnesses": {4: {
                "call": "solution.f([0, 0])", "target_line": 4,
                "recent_lines": [2, 3, 4], "locals_at_target": {},
            }},
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            (root / "prompt").mkdir()
            (root / "data" / "leetcode-py-all.jsonl").write_text(json.dumps(record) + "\n")
            (root / "prompt" / "system_exec.txt").write_text("SYSTEM")
            (root / "prompt" / "line_oneshot_gencond.txt").write_text("COND {targetline} {program}")
            (root / "prompt" / "line_oneshot_gentest.txt").write_text("TEST {func_name} {conditions} {program}")
            data_utils = SimpleNamespace(
                read_jsonl=lambda path: [json.loads(line) for line in path.read_text().splitlines()],
                add_lineno_comment=lambda code: code,
                write_jsonl=lambda rows, path: path.write_text("".join(json.dumps(row) + "\n" for row in rows)),
            )
            formatter = SimpleNamespace(
                remove_extra=lambda test, name: test,
                reformat_case_byrules=lambda test, name: test,
            )
            args = Namespace(
                upstream=str(root), out=str(root / "predictions.jsonl"), cache=None,
                arm="concept-witness", protocol="two-step", concept_facts=None,
                limit=1, max_targets=0, max_output_tokens=None, request_timeout=1,
                retries=0, retry_sleep=0, retry_max_wait=0, dry_run=False,
                witness_seconds=1.0, witness_max_candidates=10, witness_fallback=True,
            )
            with patch("testeval_py.paper_runner._upstream_modules", return_value=(data_utils, formatter)):
                with patch("testeval_py.verified_witness.find_verified_witnesses", return_value=witness):
                    result = run(args, llm=FakeLLM())

            row = json.loads(Path(args.out).read_text().splitlines()[0])
            self.assertEqual(result["fallbacks"], 1)
            self.assertEqual(row["witness_fallback_targets"], [4])
            self.assertIn("solution.f([0, 0])", row["tests"]["4"])


if __name__ == "__main__":
    unittest.main()
