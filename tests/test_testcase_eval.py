import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from testcase_eval.concepts import static_fault_concepts
from testcase_eval.oracle import evaluate_fault_exposure_record, outputs_equal
from testcase_eval.runner import extract_test_input, run
from testcase_eval.stats import mcnemar


class _FakeResponse:
    def __init__(self, content):
        self.content = content


class _FakeLLM:
    def invoke(self, messages):
        return _FakeResponse("```plaintext\n1\n```")


class TestCaseEvalIntegrationTests(unittest.TestCase):
    def test_extracts_plaintext_fence_from_model_response(self):
        response = "Reasoning first.\n```plaintext\n2\n1\n7\n1\n9\n```"

        self.assertEqual(extract_test_input(response), "2\n1\n7\n1\n9")

    def test_static_concepts_identify_frequency_state_and_reset_boundary(self):
        source = """int f[51];
for (j=0; j<n; j++) { cin >> a; f[a]++; }
for (j=0; j<n; j++) f[j]=0;
"""

        concepts = static_fault_concepts(source, "C++17 (GCC 7-32)")

        self.assertIn("frequency_counting", concepts["tags"])
        self.assertIn("global_mutable_state", concepts["tags"])
        self.assertTrue(any("reset" in item.lower() for item in concepts["risk_hypotheses"]))

    def test_output_comparison_accepts_numeric_formatting(self):
        self.assertTrue(outputs_equal("1.000000\nYES", "1\nyes"))
        self.assertFalse(outputs_equal("1 2", "1 3"))

    def test_fault_exposure_requires_correct_consensus_and_wrong_divergence(self):
        prediction = {
            "problem_id": "toyA",
            "submission_id": 2,
            "test": "2\n",
        }
        submissions = [
            {"id": 1, "problem_id": "toyA", "type": "right_submission", "language": "Python 3", "source": "x=int(input()); print(x+1)"},
            {"id": 3, "problem_id": "toyA", "type": "right_submission", "language": "Python 3", "source": "x=int(input()); print(1+x)"},
            {"id": 2, "problem_id": "toyA", "type": "wrong_submission", "language": "Python 3", "source": "x=int(input()); print(x)"},
        ]

        result = evaluate_fault_exposure_record(prediction, submissions, timeout=2)

        self.assertTrue(result["valid_input"])
        self.assertEqual(result["expected_output"], "3\n")
        self.assertEqual(result["wrong_output"], "2\n")
        self.assertTrue(result["exposed"])

    def test_one_per_problem_keeps_only_first_submission(self):
        with tempfile.TemporaryDirectory() as td:
            tasks_path = Path(td) / "task2.jsonl"
            subs_path = Path(td) / "subs.jsonl"
            out_path = Path(td) / "out.jsonl"

            rows = [
                {"prompt": [{"content": "solve it"}], "extra_info": {"submission_id": 1, "problem_id": "A", "task_type": "t"}},
                {"prompt": [{"content": "solve it"}], "extra_info": {"submission_id": 2, "problem_id": "A", "task_type": "t"}},
                {"prompt": [{"content": "solve it"}], "extra_info": {"submission_id": 3, "problem_id": "B", "task_type": "t"}},
            ]
            tasks_path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")

            subs = [
                {"id": 1, "problem_id": "A", "type": "wrong_submission", "language": "Python 3", "source": "print(1)"},
                {"id": 2, "problem_id": "A", "type": "wrong_submission", "language": "Python 3", "source": "print(1)"},
                {"id": 3, "problem_id": "B", "type": "wrong_submission", "language": "Python 3", "source": "print(1)"},
            ]
            subs_path.write_text("\n".join(json.dumps(r) for r in subs) + "\n")

            args = argparse.Namespace(
                input=str(tasks_path),
                submissions=str(subs_path),
                out=str(out_path),
                condition="baseline",
                python_only=True,
                one_per_problem=True,
                limit=0,
                rpm=6000,
                temperature=0.0,
                request_timeout=60.0,
                max_output_tokens=2048,
            )

            with patch("testcase_eval.runner.make_llm", return_value=_FakeLLM()):
                generated = run(args)

            self.assertEqual(generated, 2)
            written = [json.loads(line) for line in out_path.read_text().splitlines() if line.strip()]
            self.assertEqual({row["submission_id"] for row in written}, {1, 3})

    def test_mcnemar_counts_discordant_pairs(self):
        concept = {1: 1, 2: 0, 3: 1, 4: 0}
        baseline = {1: 0, 2: 0, 3: 0, 4: 1}

        b, c, p = mcnemar(concept, baseline)

        self.assertEqual(b, 2)
        self.assertEqual(c, 1)
        self.assertTrue(0.0 <= p <= 1.0)


if __name__ == "__main__":
    unittest.main()
