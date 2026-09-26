import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from testcase_eval.evaluate import Evaluator
from testcase_eval.generate import Pipeline, extract_test_regex, render_hypothesis, select_subset, split_official_prompt
from testcase_eval.llm import CallResult, load_env_file
from testcase_eval.metrics import official_consensus, official_exposed, strict_consensus, validate_outputs
from testcase_eval.report import cluster_bootstrap, paired
from testcase_eval.sandbox import Executor, language_family, replace_java_class_name, run_command
from testcase_eval.store import resolve_test, store_test
from testcase_eval.validator import build_cases, parse_json_block, score


class _ScriptedLLM:
    """Stands in for Gemini: returns queued responses and records prompts."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts = []

    def complete(self, prompt, system=None):
        self.prompts.append(prompt)
        text = self.responses.pop(0) if self.responses else None
        return CallResult(text=text, input_tokens=10, output_tokens=5)


class MetricTests(unittest.TestCase):
    def test_official_checker_line_and_token_rules(self):
        self.assertTrue(validate_outputs("1 2\n3\n", "1 2\n3"))
        self.assertTrue(validate_outputs("YES", "yes"))
        self.assertTrue(validate_outputs("0.3333333333333", "0.33333333333333"))
        self.assertFalse(validate_outputs("0.33", "0.34"))
        self.assertFalse(validate_outputs("1 2", "1 2 3"))
        self.assertFalse(validate_outputs("Alice", "alice"))  # only yes/no/true/false are case-folded
        self.assertTrue(validate_outputs("1\n2", "1 2"))  # token fallback ignores line layout

    def test_official_consensus_single_output_and_first_agreeing_pair(self):
        self.assertEqual(official_consensus(["5"]), "5")
        self.assertEqual(official_consensus(["4", "5", "5"]), "5")
        self.assertEqual(official_consensus(["4", "5"]), "")
        self.assertEqual(official_consensus([]), "")

    def test_official_exposure_counts_failures_and_mismatch_only_with_consensus(self):
        self.assertTrue(official_exposed("3", "success_run", "4"))
        self.assertTrue(official_exposed("3", "time_limit_exceeded", ""))
        self.assertFalse(official_exposed("3", "compilation_error", ""))
        self.assertFalse(official_exposed("", "runtime_error", ""))

    def test_strict_consensus_requires_all_accepted_to_succeed_and_agree(self):
        ok = [{"result": "success_run", "output": "1"}, {"result": "success_run", "output": "1"}]
        self.assertEqual(strict_consensus(ok), ("1", "ok"))
        crashed = ok + [{"result": "runtime_error", "output": ""}]
        self.assertEqual(strict_consensus(crashed)[1], "accepted_submission_failed")
        split = ok + [{"result": "success_run", "output": "2"}]
        self.assertEqual(strict_consensus(split)[1], "accepted_submissions_disagree")
        self.assertEqual(strict_consensus(ok[:1])[1], "too_few_accepted_runs")


class SandboxTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.executor = Executor(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_language_family_covers_official_table(self):
        self.assertEqual(language_family("C++17 (GCC 7-32)"), "cpp")
        self.assertEqual(language_family("Java 8"), "java")
        self.assertEqual(language_family("PyPy 3-64"), "python")
        self.assertIsNone(language_family("Python 2"))

    def test_java_class_is_renamed_like_official_sandbox(self):
        code = "public class Main { public static void main(String[] a) { new Main(); } Main() {} }"
        renamed = replace_java_class_name(code, "Solution")
        self.assertIn("public class Solution", renamed)
        self.assertIn("new Solution()", renamed)

    def test_timeout_and_runtime_error_verdicts(self):
        slow = run_command([sys.executable, "-c", "while True: pass"], "", timeout=0.5)
        self.assertEqual(slow["result"], "time_limit_exceeded")
        crash = run_command([sys.executable, "-c", "raise SystemExit(3)"], "", timeout=5, limit_address_space=False)
        self.assertEqual(crash["result"], "runtime_error")

    @unittest.skipUnless(shutil.which("g++"), "g++ missing")
    def test_cpp_compiles_once_and_runs(self):
        source = "#include <bits/stdc++.h>\nint main(){long long a,b;std::cin>>a>>b;std::cout<<a+b<<'\\n';}"
        first = self.executor.execute("C++17 (GCC 7-32)", source, "2 3")
        self.assertEqual((first["result"], first["output"].strip()), ("success_run", "5"))
        self.assertEqual(len(list(Path(self.tmp.name).iterdir())), 1)
        self.executor.execute("C++17 (GCC 7-32)", source, "4 4")
        self.assertEqual(len(list(Path(self.tmp.name).iterdir())), 1)

    @unittest.skipUnless(shutil.which("javac"), "javac missing")
    def test_java_runs_with_renamed_class(self):
        source = "import java.util.*;\npublic class A { public static void main(String[] x){ Scanner s=new Scanner(System.in); System.out.println(s.nextInt()*2);} }"
        result = self.executor.execute("Java 21", source, "21")
        self.assertEqual((result["result"], result["output"].strip()), ("success_run", "42"))

    def test_compilation_error_is_cached_and_reported(self):
        result = self.executor.execute("Python 3", "def broken(:\n", "")
        self.assertEqual(result["result"], "compilation_error")


class StoreAndExtractionTests(unittest.TestCase):
    def test_large_tests_spill_to_disk_and_resolve(self):
        with tempfile.TemporaryDirectory() as td:
            row = store_test("1\n" * 50000, Path(td))
            self.assertIsNone(row["test"])
            self.assertEqual(resolve_test(row), "1\n" * 50000)
            self.assertEqual(store_test("3\n")["test"], "3\n")

    def test_official_regex_prefers_answer_tag_then_plaintext(self):
        self.assertEqual(extract_test_regex("x <answer>```plaintext\n1 2\n```</answer> ```\n9\n```"), "1 2")
        self.assertEqual(extract_test_regex("reasoning\n```plaintext\n3\n```"), "3")
        self.assertIsNone(extract_test_regex("no fences here"))

    def test_split_official_prompt_drops_instruction_tail(self):
        content = "**Task:**\nproblem\nBuggy Code:\nint main(){}\n\n**Instructions:**\n- small\nThink step by step."
        self.assertTrue(split_official_prompt(content).endswith("int main(){}"))

    def test_env_file_parsing_exports_without_overriding(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "env.sh"
            path.write_text('#!/bin/bash\nexport TCE_TEST_A="x y"\nTCE_TEST_B=2\necho hi\n')
            with patch.dict("os.environ", {"TCE_TEST_B": "keep"}, clear=False):
                import os

                keys = load_env_file(str(path))
                self.assertEqual(keys, ["TCE_TEST_A", "TCE_TEST_B"])
                self.assertEqual(os.environ["TCE_TEST_A"], "x y")
                self.assertEqual(os.environ["TCE_TEST_B"], "keep")


VALIDATOR = "import sys\nt=sys.stdin.read().split()\nif len(t)!=1 or not t[0].isdigit() or not 1<=int(t[0])<=10: sys.exit(1)\n"


class ValidatorTests(unittest.TestCase):
    def test_json_block_and_case_materialisation(self):
        parsed = parse_json_block('text ```json\n{"cases": [{"input": "5", "valid": true}, {"generator": "print(11)", "valid": false}]}\n```')
        cases = build_cases(parsed["cases"], "autocode")
        self.assertEqual([c["text"].strip() for c in cases], ["5", "11"])

    def test_score_counts_correct_classifications_and_sample_failures(self):
        cases = [{"text": "5", "valid": True, "sample": True}, {"text": "11", "valid": False}, {"text": "0", "valid": True}]
        result = score(VALIDATOR, cases)
        self.assertEqual(result["correct"], 2)
        self.assertTrue(result["samples_ok"])
        self.assertEqual(result["wrong"], [2])


class PipelineTests(unittest.TestCase):
    record = {"prompt": [{"content": "**Task:**\nP\nBuggy Code:\nx\n\n**Instructions:**\n- i\nThink step by step."}],
              "extra_info": {"problem_id": "P1", "submission_id": 7, "task_type": "TestCase-Eval-Task2"}}

    def test_concept_condition_feeds_hypothesis_and_repairs_rejected_input(self):
        analyst = '```json\n{"hypotheses": [{"suspicious_code": "f[j]=0", "trigger_condition": "h_i = n", "failure_mode": "WA"}]}\n```'
        gen = _ScriptedLLM([analyst, "```plaintext\n11\n```", "```python\nprint(10)\n```"])
        pipeline = Pipeline(gen, _ScriptedLLM([]), {"P1": {"code": VALIDATOR, "rules": ["R1: 1<=x<=10"]}}, {})
        row = pipeline.run("concept", self.record, None)
        self.assertIn("Trigger condition: h_i = n", gen.prompts[1])
        self.assertIn("rejected", gen.prompts[2])
        self.assertEqual(row["test"].strip(), "10")
        self.assertEqual(row["input_kind"], "generator")
        self.assertEqual(row["gen_validator_verdict"], "accepted")
        self.assertEqual(row["usage"]["calls"], 3)

    def test_nohyp_ablation_has_no_hypothesis_block(self):
        gen = _ScriptedLLM(["```plaintext\n3\n```"])
        pipeline = Pipeline(gen, _ScriptedLLM([]), {"P1": {"code": VALIDATOR, "rules": []}}, {})
        row = pipeline.run("concept_nohyp", self.record, None)
        self.assertNotIn("Fault hypothesis", gen.prompts[0])
        self.assertEqual(row["gen_validator_verdict"], "accepted")

    def test_cot_val_reuses_cot_answer_without_new_call_when_valid(self):
        cot_row = {"submission_id": 7, "test": "4", "trace": [{"stage": "generate", "response": "```plaintext\n4\n```"}]}
        gen = _ScriptedLLM([])
        pipeline = Pipeline(gen, _ScriptedLLM([]), {"P1": {"code": VALIDATOR}}, {7: cot_row})
        row = pipeline.run("cot_val", self.record, None)
        self.assertEqual(gen.prompts, [])
        self.assertEqual(row["test"], "4")
        self.assertEqual(row["usage"]["calls"], 0)

    def test_render_hypothesis_skips_empty_fields(self):
        text = render_hypothesis({"mechanism": "stale counts", "trigger_condition": ""})
        self.assertIn("Mechanism: stale counts", text)
        self.assertNotIn("Trigger condition", text)


class SubsetAndEvaluatorTests(unittest.TestCase):
    def test_subset_is_seeded_stratified_and_one_per_problem(self):
        subs = {i: {"language": ["C++17 (GCC 7-32)", "Java 21", "Python 3"][i % 3]} for i in range(60)}
        task2 = [{"extra_info": {"submission_id": i, "problem_id": f"p{i // 2}"}} for i in range(60)]
        first = select_subset(task2, subs, 3, 1)
        self.assertEqual(first, select_subset(task2, subs, 3, 1))
        self.assertEqual(len(first), 9)
        self.assertEqual(len({i // 2 for i in first}), 9)

    def test_evaluator_scores_official_and_strict_exposure(self):
        subs = [
            {"id": 1, "problem_id": "T", "type": "right_submission", "language": "Python 3", "verdict": "OK", "source": "print(int(input())+1)"},
            {"id": 3, "problem_id": "T", "type": "right_submission", "language": "Python 3", "verdict": "OK", "source": "print(1+int(input()))"},
            {"id": 2, "problem_id": "T", "type": "wrong_submission", "language": "Python 3", "verdict": "WA", "source": "print(int(input()))"},
        ]
        with tempfile.TemporaryDirectory() as td:
            vpath = Path(td) / "v.jsonl"
            vpath.write_text(json.dumps({"problem_id": "T", "code": VALIDATOR}) + "\n")
            with patch("testcase_eval.evaluate.Executor", lambda: Executor(Path(td) / "build")), \
                 patch("testcase_eval.sandbox.PYTHON3", sys.executable):
                ev = Evaluator(Path(td) / "c.sqlite", vpath, subs)
                good = ev.score({"problem_id": "T", "submission_id": 2, "test": "5"})
                bad = ev.score({"problem_id": "T", "submission_id": 2, "test": "50"})
        self.assertTrue(good["exposed_official"] and good["exposed_strict"])
        self.assertTrue(bad["exposed_official"])
        self.assertFalse(bad["exposed_strict"])
        self.assertEqual(bad["invalid_reason"], "validator_rejected")


class ReportTests(unittest.TestCase):
    def test_paired_mcnemar_and_bootstrap(self):
        ref = {i: {"problem_id": f"p{i}", "family": "cpp", "exposed_official": i < 2} for i in range(10)}
        cond = {i: {"problem_id": f"p{i}", "family": "cpp", "exposed_official": i < 6} for i in range(10)}
        rows = paired({"cot": ref, "concept": cond}, list(range(10)), "cot", "exposed_official")
        overall = next(r for r in rows if r["family"] == "all")
        self.assertEqual((overall["cond_only"], overall["ref_only"]), (4, 0))
        self.assertAlmostEqual(overall["diff"], 0.4)
        lo, hi = cluster_bootstrap({"a": [1], "b": [0]})
        self.assertLessEqual(lo, hi)


if __name__ == "__main__":
    unittest.main()
