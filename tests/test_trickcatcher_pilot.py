import unittest
import json
import tempfile
from pathlib import Path

from trickcatcher_pilot.evaluate import _execute, _same
from trickcatcher_pilot.run import _concept_text, build_input_messages, parse_inputs
from trickcatcher_pilot.reparse import parse_lenient
from trickcatcher_pilot.stats import summarize
from trickcatcher_pilot.paired import compare
from trickcatcher_pilot.static_concepts import static_concept
from trickcatcher_pilot.cpp_run import parse_inputs as parse_cpp_inputs, build_prompt as build_cpp_prompt
from trickcatcher_pilot.cpp_evaluate import _compile as compile_cpp, _run as run_cpp_binary
from trickcatcher_pilot.cpp_validity import valid_input as valid_cpp_input
from trickcatcher_pilot.prompt_provenance import read_original_templates


class TrickCatcherPilotTests(unittest.TestCase):
    def test_generated_inputs_are_literals_with_correct_arity(self):
        raw = "```python\n[[1, 2], 0.5]\n[[], 0.1]\n[{1, 2}, 0.3]\n__import__('os').system('false')\n[1]\n[[1, 2], 0.5]\n```"
        self.assertEqual(parse_inputs(raw, 2), [[[1, 2], 0.5], [[], 0.1]])

    def test_lenient_wrapper_parser_repairs_both_input_shapes(self):
        self.assertEqual(parse_lenient("[]\n[0]\n[0, 0, 0]", 1, True), [[[]], [[0]], [[0, 0, 0]]])
        self.assertEqual(parse_lenient("[[0, 101]]\n[[1, 1]]", 2, False), [[0, 101], [1, 1]])

    def test_concept_is_added_only_to_concept_arm(self):
        source = "def f(x):\n    return x"
        plan = '{"expected_property":"x stays x","suspected_shortcut":"return x","separating_input_relation":"x = 1"}'
        _, baseline = build_input_messages(source, "official", "{function_and_docstring}", "baseline")
        _, concept = build_input_messages(source, "official", "{function_and_docstring}", "concept", plan)
        self.assertEqual(baseline, source)
        self.assertIn("expected_property: x stays x", concept)
        self.assertNotIn("expected_property", baseline)
        self.assertIn("separating_input_relation: x = 1", _concept_text(plan))

    def test_static_card_uses_only_docstring_and_ast(self):
        source = '''def f(s):
    """Count uppercase vowels in the string."""
    return sum(ch in "AEOU" for ch in s)
'''
        plan, rules = static_concept(source)
        card = json.loads(plan)
        self.assertIn("Count uppercase vowels", card["expected_property"])
        self.assertIn("ch in 'AEOU'", card["suspected_shortcut"])
        self.assertIn("literal_membership", rules)
        _, prompt = build_input_messages(source, "official", "{function_and_docstring}", "static_concept", plan)
        self.assertIn("separating_input_relation", prompt)

    def test_original_prompt_template_gate_rejects_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            template_dir = Path(directory)
            (template_dir / "geninput_direct_sys").write_text("changed prompt")
            (template_dir / "geninput_usr").write_text("{function_and_docstring}")
            with self.assertRaisesRegex(ValueError, "untracked prompt change"):
                read_original_templates(template_dir)

    def test_original_prompt_template_gate_accepts_pinned_artifact(self):
        template_dir = Path("/tmp/TrickCatcher-upstream/Datasets/EvalPlus/PromptTemplates")
        if not template_dir.is_dir():
            self.skipTest("pinned TrickCatcher artifact not installed")
        system, user = read_original_templates(template_dir)
        self.assertIn("professional software testing engineer", system)
        self.assertIn("{function_and_docstring}", user)

    def test_cpp_input_sections_preserve_multiline_stdin(self):
        raw = "INPUT1:\n2\n1 2\nINPUT2: 3 4\nINPUT3:\n```\n5\n```"
        self.assertEqual(parse_cpp_inputs(raw), ["2\n1 2\n", "3 4\n", "5\n"])
        template = "Problem: {pro_des}\nCode: {code}"
        self.assertEqual(build_cpp_prompt(template, "spec", "int main(){}"), "Problem: spec\nCode: int main(){}")

    def test_cpp_differential_runner_detects_output_difference(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "main.cpp"
            binary = Path(directory) / "main"
            source.write_text('#include <iostream>\nint main(){int x; std::cin>>x; std::cout<<(x+1);}\n')
            self.assertEqual(compile_cpp(source, binary), "")
            self.assertEqual(run_cpp_binary(binary, "2\n")["output"], "3")

    def test_cpp_spec_validator_rejects_truncated_sequence(self):
        self.assertFalse(valid_cpp_input("p02616", "200000 1\n-1 -1 -1\n"))
        self.assertTrue(valid_cpp_input("p02616", "3 1\n-1 -1 -1\n"))
        self.assertFalse(valid_cpp_input("p02598", "3 0\n1 2\n"))
        self.assertTrue(valid_cpp_input("p02598", "1 1\n2\n"))

    def test_contract_and_canonical_execution_are_separate(self):
        contract = "def __contract(x):\n    assert x >= 0, 'invalid inputs'\n"
        reference = _execute("def f(x): return x - int(x)", "f", [1.0], contract, 2)
        buggy = _execute("def f(x): return 1 if x == 1 else x - int(x)", "f", [1.0], "", 2)
        invalid = _execute("def f(x): return x", "f", [-1], contract, 2)
        self.assertEqual(reference["status"], "pass")
        self.assertEqual(invalid["status"], "invalid")
        self.assertFalse(_same(reference["value"], buggy["value"], 1e-6))

    def test_stats_pairs_same_task_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = {}
            for arm, exposed in (("baseline", [False, True]), ("generic", [True, True]), ("concept", [True, False])):
                path = Path(directory) / (arm + ".jsonl")
                path.write_text("\n".join(json.dumps({
                    "task_num": task, "task_exposed": found, "exposing": int(found),
                    "valid": 1, "generated": 1,
                }) for task, found in enumerate(exposed, 1)) + "\n")
                paths[arm] = str(path)
            result = summarize(paths["baseline"], paths["generic"], paths["concept"])
            self.assertEqual(result["paired_tasks"], 2)
            self.assertEqual(result["arms"]["generic"]["exposed_tasks"], 2)
            self.assertEqual(result["comparisons"]["baseline_vs_concept"]["a_only"], 1)
            self.assertEqual(result["comparisons"]["baseline_vs_concept"]["b_only"], 1)

    def test_paired_stats_can_exclude_tasks_without_valid_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            a = Path(directory) / "a.jsonl"
            b = Path(directory) / "b.jsonl"
            a.write_text("\n".join(json.dumps({
                "task_num": task, "valid": valid, "exposing": 0,
                "task_exposed": False,
            }) for task, valid in ((1, 0), (2, 1))) + "\n")
            b.write_text("\n".join(json.dumps({
                "task_num": task, "valid": 1, "exposing": 1,
                "task_exposed": True,
            }) for task in (1, 2)) + "\n")
            self.assertEqual(compare([str(a)], [str(b)])["b_only"], [1, 2])
            filtered = compare([str(a)], [str(b)], both_valid_only=True)
            self.assertEqual(filtered["paired_tasks"], 1)
            self.assertEqual(filtered["b_only"], [2])


if __name__ == "__main__":
    unittest.main()
