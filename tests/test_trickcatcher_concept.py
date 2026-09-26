import inspect
import json
import math
import tempfile
import unittest
from pathlib import Path

from trickcatcher_concept import prompts
from trickcatcher_concept.data import parse_examples, seeded_subset, select, task_index
from trickcatcher_concept.llm import LLM, extract_code, extract_json, load_env_file
from trickcatcher_concept.oracle import PutScore, aggregate, score_put
from trickcatcher_concept.oracle import test_cases_for as compute_test_cases
from trickcatcher_concept.provenance import fill
from trickcatcher_concept.sandbox import compile_cpp, normalize_output, python_program, run_program
from trickcatcher_concept.validator import mechanical_negatives, parse_cases, parse_validators
from trickcatcher_concept.report import llm_cost, load_rows, mcnemar, paired_exposure, per_lang_metrics, validity_rates

OK = "OK"


def table(put, **variants):
    out = {"put": {k: [OK, v] if v is not None else ["RUN_ERROR", ""] for k, v in put.items()}}
    for name, values in variants.items():
        out[name] = {k: [OK, v] if v is not None else ["RUN_ERROR", ""] for k, v in values.items()}
    return out


class OracleTests(unittest.TestCase):
    def test_diversity_oracle_prefers_disagreeing_output_over_majority(self):
        # Two variants copy the PUT's answer, one differs: majority voting would
        # report nothing, TrickCatcher reports the disagreeing output.
        outputs = table({"i1": "5"}, v0={"i1": "5"}, v1={"i1": "5"}, v2={"i1": "7"})
        cases = compute_test_cases(outputs, ["v0", "v1", "v2"])
        self.assertEqual([(c.input_id, c.oracle, c.supporters) for c in cases], [("i1", "7", ("v2",))])

    def test_most_frequent_disagreeing_output_and_ties(self):
        outputs = table({"i1": "5", "i2": "1"}, v0={"i1": "7", "i2": "2"}, v1={"i1": "7", "i2": "3"}, v2={"i1": "8", "i2": "1"})
        cases = compute_test_cases(outputs, ["v0", "v1", "v2"])
        self.assertIn(("i1", "7"), [(c.input_id, c.oracle) for c in cases])
        self.assertNotIn(("i1", "8"), [(c.input_id, c.oracle) for c in cases])
        # tie on i2: both 2 and 3 are kept, as in the artifact's analysis code
        self.assertEqual(sorted(c.oracle for c in cases if c.input_id == "i2"), ["2", "3"])

    def test_errors_are_ignored(self):
        outputs = table({"i1": None, "i2": "1"}, v0={"i1": "3", "i2": None})
        self.assertEqual(compute_test_cases(outputs, ["v0"]), [])

    def test_score_put_averages_over_combinations(self):
        outputs = table({"i1": "5"}, v0={"i1": "7"}, v1={"i1": "5"}, v2={"i1": "5"})
        score = score_put(outputs, 2, is_true=lambda c: c.oracle == "7", input_valid=lambda _: True)
        self.assertEqual(score.total, math.comb(3, 2))
        self.assertAlmostEqual(score.tp, 2.0)  # v0 is in 2 of the 3 pairs
        self.assertAlmostEqual(score.tp_rate, 2 / 3)
        self.assertEqual(score.precision, 1.0)
        capped = score_put(outputs, 10, is_true=lambda c: c.oracle == "7", input_valid=lambda _: True)
        self.assertEqual((capped.k, capped.total, capped.tp_rate), (3, 1, 1.0))

    def test_aggregate_matches_notebook_definition(self):
        scores = [PutScore(3, 2, 3, 2.0, 1.0, 0.0, True), PutScore(2, 2, 1, 0.0, 0.0, 0.0, False)]
        agg = aggregate(scores, n_puts=4)
        self.assertAlmostEqual(agg["recall"], (2 / 3) / 4)
        self.assertAlmostEqual(agg["precision"], 2 / 3)
        self.assertAlmostEqual(agg["f1"], 2 * agg["precision"] * agg["recall"] / (agg["precision"] + agg["recall"]))


class ParsingTests(unittest.TestCase):
    def test_examples_from_description(self):
        text = "Stuff\nEXAMPLES:\n\nINPUT:\n6 2 1001\n\nOUTPUT:\n1369\n\nINPUT:\n2\n1 2\n\nOUTPUT:\n3\n"
        self.assertEqual(parse_examples(text), [("6 2 1001\n", "1369\n"), ("2\n1 2\n", "3\n")])

    def test_sandbox_runs_without_preexec_fn_and_applies_limits(self):
        # Regression test for the fork()+gRPC hazard: run_program must not use a
        # subprocess preexec_fn (see sandbox.py docstring). It also must still
        # apply resource limits -- proven here by a program that reads stdin,
        # allocates more than its RLIMIT_AS budget, and would otherwise succeed.
        with tempfile.TemporaryDirectory() as tmp:
            program, error = compile_cpp(
                "#include <cstdio>\n#include <cstdlib>\nint main(){int n;scanf(\"%d\",&n);"
                "printf(\"got %d\\n\", n);return 0;}\n", Path(tmp))
            self.assertIsNotNone(program, error)
            result = run_program(program, "42\n", timeout=5, memory_mb=256)
            self.assertEqual((result.status, result.output), ("OK", "got 42"))

            oom_source = ("#include <cstdlib>\nint main(){volatile char *p ="
                          "(char*)malloc(2000ULL*1024*1024);if(!p) return 1;p[0]=1;return 0;}\n")
            oom_program, oom_error = compile_cpp(oom_source, Path(tmp))
            self.assertTrue(oom_program is not None, oom_error)
            oom_result = run_program(oom_program, "", timeout=5, memory_mb=256)
            self.assertNotEqual(oom_result.status, "OK")  # RLIMIT_AS=256MB must reject a 2GB allocation

    def test_sandbox_module_never_uses_preexec_fn(self):
        import trickcatcher_concept.sandbox as sandbox_module
        self.assertNotIn("preexec_fn=", inspect.getsource(sandbox_module))

    def test_python_program_runs_under_wrapper_too(self):
        with tempfile.TemporaryDirectory() as tmp:
            program = python_program("import sys\nprint(sys.stdin.read().strip()[::-1])\n", Path(tmp))
            result = run_program(program, "hello\n", timeout=10)
            self.assertEqual((result.status, result.output), ("OK", "olleh"))

    def test_normalize_output(self):
        self.assertEqual(normalize_output("1  2\n3\n"), "1 2 3")
        self.assertEqual(normalize_output("0.5000000000\n"), normalize_output("0.5"))
        self.assertNotEqual(normalize_output("Yes"), normalize_output("YES"))

    def test_extract_code_prefers_language_block(self):
        raw = "text\n```python\nprint(1)\n```\n```cpp\nint main(){}\n```"
        self.assertEqual(extract_code(raw, "cpp"), "int main(){}\n")
        self.assertEqual(extract_code("```\nx=1\n```", "python"), "x=1\n")
        self.assertEqual(extract_code("int main(){}", "cpp"), "int main(){}\n")

    def test_extract_json(self):
        self.assertEqual(extract_json('```json\n{"a": 1}\n```'), {"a": 1})
        self.assertEqual(extract_json('noise {"a": [1]} tail'), {"a": [1]})

    def test_validator_and_case_parsing(self):
        raw = ("### VALIDATOR 1\n```python\nimport sys\ndata=sys.stdin.read()\nsys.exit(0)\n```\n### VALIDATOR 2\n"
               "```python\nimport sys\ndata=sys.stdin.read()\n```\n### VALIDATOR 3\nnot code\n")
        self.assertEqual(len(parse_validators(raw)), 2)
        cases = parse_cases("INVALID 1 (violates C1):\n0\nINVALID 2 (violates C2):\n3\n1 2\nVALID 1:\n1\n5\n")
        self.assertEqual(cases, [("0\n", False), ("3\n1 2\n", False), ("1\n5\n", True)])

    def test_mechanical_negatives_catch_truncated_body(self):
        negatives = mechanical_negatives(["3\n1 2 3\n"])
        self.assertIn("3\n1 2\n", negatives)
        self.assertIn("3\n", negatives)
        self.assertIn("", negatives)
        self.assertNotIn("3\n1 2 3\n", negatives)

    def test_env_file_parsing_does_not_override(self):
        import os
        with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as handle:
            handle.write('#!/bin/bash\nexport TCC_TEST_KEY="value one"\necho hi\n')
        os.environ.pop("TCC_TEST_KEY", None)
        self.assertEqual(load_env_file(handle.name), ["TCC_TEST_KEY"])
        self.assertEqual(os.environ["TCC_TEST_KEY"], "value one")


class PromptTests(unittest.TestCase):
    TEMPLATE = "INSTR\n**PROBLEM DESCRIPTION**:\n{pro_des}\n\n**CODE**:\n{code}\n"

    def test_baseline_variant_prompt_is_verbatim_template(self):
        prompt = prompts.variant_prompt(self.TEMPLATE, "DESC", "int main(){return {1};}")
        self.assertEqual(prompt, fill(self.TEMPLATE, pro_des="DESC", code="int main(){return {1};}"))

    def test_concept_prompts_keep_paper_prompt_as_prefix(self):
        base = fill(self.TEMPLATE, pro_des="DESC", code="CODE").rstrip("\n")
        hyp = {"id": "H1", "code": "a+b", "mechanism": "overflow", "violated_rule": "C2", "trigger": "a=b=1e9"}
        self.assertTrue(prompts.variant_prompt(self.TEMPLATE, "DESC", "CODE", hyp).startswith(base))
        gen_t = "GEN {pid}\n{pro_des}\n"
        card = {"constraints": [{"id": "C1", "rule": "1<=N<=10"}], "hypotheses": [hyp]}
        gen = prompts.generator_prompt(gen_t, "p1", "DESC", card)
        self.assertTrue(gen.startswith("GEN p1\nDESC"))
        self.assertIn("C1: 1<=N<=10", gen)
        self.assertIn("a=b=1e9", gen)
        self.assertEqual(prompts.generator_prompt(gen_t, "p1", "DESC"), "GEN p1\nDESC\n")

    def test_card_prompt_does_not_mangle_braces_in_code(self):
        code = "vector<vector<int>> a = {{1,2}};"
        self.assertIn(code, prompts.card_prompt("cpp", "DESC", code))


class DataTests(unittest.TestCase):
    def test_task_index_and_subset(self):
        all_tasks = task_index(include_excluded=True)
        self.assertEqual(sum(t["lang"] == "cpp" for t in all_tasks), 250)
        self.assertEqual(sum(t["lang"] == "python" for t in all_tasks), 115)
        tasks = task_index()
        self.assertLess(len(tasks), len(all_tasks))  # exclusions.json removes harness-incompatible PUTs
        subset = seeded_subset()
        self.assertEqual(len(subset), 75)
        self.assertEqual(subset, seeded_subset())
        self.assertTrue(set((t["lang"], t["pid"]) for t in subset) <= set((t["lang"], t["pid"]) for t in tasks))
        held = select("heldout")
        self.assertEqual(len(held) + len(subset), len(tasks))


class LLMCacheTests(unittest.TestCase):
    def test_cached_call_is_not_repeated_and_records_tokens(self):
        calls = []

        class Fake:
            def invoke(self, messages):
                calls.append(messages)

                class R:
                    content = "hello"
                    usage_metadata = {"input_tokens": 3, "output_tokens": 1}
                return R()

        with tempfile.TemporaryDirectory() as tmp:
            llm = LLM(Path(tmp), factory=lambda t, m: Fake(), model="fake")
            first = llm.call("a/b", "prompt", temperature=0, max_tokens=5)
            second = llm.call("a/b", "prompt", temperature=0, max_tokens=5)
            self.assertEqual(len(calls), 1)
            self.assertEqual(first["input_tokens"], 3)
            self.assertTrue(second["cached"])
            saved = json.loads((Path(tmp) / "a" / "b.json").read_text())
            self.assertEqual(saved["model"], "fake")


def _arm_result(exposed: bool) -> dict:
    tp = 1.0 if exposed else 0.0
    per_k = {str(k): {"total": 1, "tp": tp, "fp": 0.0, "fp_bad_input": 0.0, "tp_rate": tp,
                      "precision": (1.0 if exposed else None), "n_variants": 3} for k in range(2, 11)}
    return {"per_k": per_k, "reported_cases": int(exposed), "true_cases": int(exposed),
            "exposing_inputs": int(exposed), "task_exposed": exposed, "witnesses": [], "invalid_reported_cases": 0}


def _row(task_num: str, lang: str, baseline_exposed: bool, concept_exposed: bool,
        eval_invalid_usable: int = 0) -> dict:
    return {
        "task_num": task_num, "lang": lang, "pid": task_num.split("/")[-1],
        "baseline_strict": _arm_result(baseline_exposed), "concept_strict": _arm_result(concept_exposed),
        "baseline_inputs": {"generated": 10, "usable": 10, "eval_invalid_generated": eval_invalid_usable,
                           "eval_invalid_usable": eval_invalid_usable, "byref_invalid_usable": 0},
        "concept_inputs": {"generated": 10, "usable": 8, "eval_invalid_generated": 0,
                          "eval_invalid_usable": 0, "byref_invalid_usable": 0},
    }


class ReportTests(unittest.TestCase):
    def test_mcnemar_symmetric_and_perfect_agreement(self):
        self.assertEqual(mcnemar(0, 0), 1.0)
        self.assertAlmostEqual(mcnemar(1, 0), mcnemar(0, 1))
        self.assertLess(mcnemar(10, 0), 0.01)

    def test_paired_exposure_counts_discordant_pairs(self):
        rows = [_row("cpp/p1", "cpp", True, True), _row("cpp/p2", "cpp", True, False),
                _row("cpp/p3", "cpp", False, True), _row("cpp/p4", "cpp", False, False)]
        result = paired_exposure(rows, "baseline_strict", "concept_strict")
        self.assertEqual(result["n_paired"], 4)
        self.assertEqual(result["a_exposed"], 2)
        self.assertEqual(result["b_exposed"], 2)
        self.assertEqual(result["both_exposed"], 1)
        self.assertEqual(result["a_only"], ["cpp/p2"])
        self.assertEqual(result["b_only"], ["cpp/p3"])
        self.assertEqual(result["mcnemar_exact_two_sided"], 1.0)

    def test_validity_rates(self):
        rows = [_row("cpp/p1", "cpp", True, True, eval_invalid_usable=2), _row("cpp/p2", "cpp", True, True)]
        rates = validity_rates(rows, "baseline")
        self.assertEqual(rates["generated"], 20)
        self.assertEqual(rates["usable"], 20)
        self.assertAlmostEqual(rates["eval_invalid_rate_of_usable"], 2 / 20)

    def test_per_lang_metrics_all_exposed_gives_recall_one(self):
        rows = [_row(f"cpp/p{i}", "cpp", True, True) for i in range(3)]
        metrics = per_lang_metrics(rows, "strict")
        self.assertIn("cpp", metrics)
        best = metrics["cpp"]["best"]
        self.assertAlmostEqual(best["baseline"]["recall"], 1.0)
        self.assertAlmostEqual(best["concept"]["recall"], 1.0)
        self.assertEqual(metrics["cpp"]["paired_task_exposure"]["n_paired"], 3)

    def test_load_rows_skips_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "r.jsonl"
            path.write_text(json.dumps(_row("cpp/p1", "cpp", True, True)) + "\n" +
                            json.dumps({"task_num": "cpp/p2", "error": "boom"}) + "\n")
            rows = load_rows(path)
            self.assertEqual(len(rows), 1)

    def test_llm_cost_sums_tokens_across_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            cache = run_dir / "llm_cache" / "cpp" / "p1"
            cache.mkdir(parents=True)
            (cache / "a.json").write_text(json.dumps({"model": "m1", "input_tokens": 10, "output_tokens": 5}))
            (cache / "b.json").write_text(json.dumps({"model": "m1", "input_tokens": 3, "output_tokens": 1}))
            cost = llm_cost(run_dir)
            self.assertEqual(cost["calls"], 2)
            self.assertEqual(cost["input_tokens"], 13)
            self.assertEqual(cost["by_model"]["m1"]["output_tokens"], 6)


if __name__ == "__main__":
    unittest.main()
