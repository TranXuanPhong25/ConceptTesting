"""CPU-only prompt, parser, resume, and real evaluator regression checks."""
from __future__ import annotations

import ast
import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from trickcatcher_linefacts import gen_evaluation, gen_prompts, prompts as old_prompts
from trickcatcher_linefacts.evalmitigate import prompts, run


class Canned:
    model = "qwen2.5-coder-7b-instruct"

    def __init__(self, *, fail_doc_task8=False, fail_after=None):
        self.requests = []
        self.fail_doc_task8 = fail_doc_task8
        self.fail_after = fail_after

    def chat(self, messages, seed, **settings):
        if self.fail_after is not None and len(self.requests) == self.fail_after:
            raise RuntimeError("canned transport failure")
        self.requests.append(dict(messages=copy.deepcopy(messages), seed=seed, **settings))
        is_two = "def truncate_number(" in messages[1]["content"]
        if settings == run.DOC_SETTINGS:
            doc = "Return the fractional part of a positive floating point number." if is_two else \
                  "Return the sum and product of the given list; for an empty list return (0, 1)."
            text = ('Part 2: Corrected Implementation\n```python\ndef ignored():\n    """WRONG PART TWO"""\n    pass\n```\n'
                    'Part 3: Final Requirement Docstring\n<FINAL_DOCSTRING>\n"""' + doc +
                    '"""\n</FINAL_DOCSTRING>')
            if self.fail_doc_task8 and not is_two:
                text = 'Part 2: Corrected Implementation\n"""WRONG PART TWO"""'
        else:
            text = "```python\n" + ("assert truncate_number(1.0) == 0.0\nassert truncate_number(3.5) == 0.0"
                                    if is_two else "assert sum_product([]) == (0, 1)") + "\n```"
        return dict(text=text, key=str(seed), params=dict(model=self.model, seed=seed, **settings),
                    n_in=10, n_out=20, seconds=0.25, cache_hit=False, transport_attempts=1)


class BaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = run.load_bundle()
        cls.small = run.load_bundle(ids=[2, 8])

    def test_onlydoc_and_stage2_hide_body_and_base(self):
        for task in self.bundle["tasks"]:
            tree = ast.parse(task["put"])
            fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == task["entry"])
            fn.body = fn.body[:1] + [ast.parse("raise RuntimeError('UNIQUE_BODY_SENTINEL')").body[0]]
            changed = dict(task, put=ast.unparse(ast.fix_missing_locations(tree)), base="UNIQUE_BASE_SENTINEL")
            self.assertEqual(prompts.test_messages(task), prompts.test_messages(changed))
            self.assertEqual(prompts.test_messages(task, "Replacement requirement"),
                             prompts.test_messages(changed, "Replacement requirement"))
            for doc in (None, "Replacement requirement"):
                user = prompts.test_messages(changed, doc)[1]["content"]
                self.assertNotIn("UNIQUE_BODY_SENTINEL", user)
                self.assertNotIn("UNIQUE_BASE_SENTINEL", user)
                self.assertIn(old_prompts.TAIL.format(entry=task["entry"]), user)
                self.assertIn("maximizing both branch and line coverage", user)
                self.assertIn("# The full function signature is:", user)
                if doc is not None:
                    self.assertIn(doc, user)
            self.assertIn("UNIQUE_BODY_SENTINEL", prompts.advanced_messages(changed)[1]["content"])

    def test_part3_parser_and_fallback(self):
        good = [
            ('**Part 3: Final Requirement Docstring**\n"""Final spec."""', "Final spec."),
            ("Part 3: Final Requirement Docstring\n```python\n'''Final spec.'''\n```", "Final spec."),
            ('Part 2: Corrected Implementation\n"""Wrong."""\nPart 3: Final Requirement Docstring\n"""Right."""', "Right."),
            ("<FINAL_DOCSTRING>Clearly delimited prose.</FINAL_DOCSTRING>", "Clearly delimited prose."),
            ('<FINAL_DOCSTRING>"""First\\nSecond"""</FINAL_DOCSTRING>', "First\nSecond"),
        ]
        for text, expected in good:
            with self.subTest(text=text):
                self.assertEqual(prompts.parse_docstring(text, "Original"), (expected, None))
        bad = ["", 'Part 2: Corrected Implementation\n"""Wrong."""',
               'Part 3: Final Requirement Docstring\n"""Unclosed',
               '<FINAL_DOCSTRING>"""Unclosed</FINAL_DOCSTRING>',
               'Part 3: Final Requirement Docstring\n""""""',
               'Part 3: Final Requirement Docstring\n"""One""" and """Two"""',
               '<FINAL_DOCSTRING>One</FINAL_DOCSTRING><FINAL_DOCSTRING>Two</FINAL_DOCSTRING>']
        for text in bad:
            with self.subTest(text=text):
                doc, failure = prompts.parse_docstring(text, "Original")
                self.assertEqual(doc, "Original")
                self.assertIsNotNone(failure)

    def test_frozen_existing_prompt_bytes(self):
        # Captured before any implementation edit, across all 133 tasks and 8 existing arms.
        frozen_files = {
            "prompts.py": "6e5c0280d3370988ee1b72cea7d370b5b5efe9c2a4d54d3bae4edf66b8e1d36b",
            "gen_prompts.py": "528f01d57e165b02b8f23b0010000a60deba2d7ab86b25b154f1c970342ba3f9",
            "evaluate.py": "bbcb3eea11156722a2d0ea6ba3dcf6c9236237ddda63ede52bf68c2a44f848eb",
            "oracle_b01.py": "a7f5103db6a534ad5e5549d98b311159c9e802fe5329265b39c261b38065a0d2",
        }
        for name, expected in frozen_files.items():
            self.assertEqual(run.sha((run.HARNESS / name).read_bytes()), expected, name)
        snapshot = {}
        for task in self.bundle["tasks"]:
            for arm in old_prompts.ARMS:
                snapshot[f"{task['task']}:{arm}"] = run.sha(json.dumps(
                    gen_prompts.messages(*old_prompts.build(arm, task)), ensure_ascii=False))
            for arm in gen_prompts.DEFAULT_ARMS[3:]:
                snapshot[f"{task['task']}:{arm}"] = run.sha(json.dumps(
                    gen_prompts.generator_messages(arm, task), ensure_ascii=False))
        self.assertEqual(len(snapshot), 1064)
        self.assertEqual(run.sha(json.dumps(snapshot, sort_keys=True)),
                         "734b90b648e08a1701c056b3d88d55e46318886aa4338e56fb52e61b45ed4806")

    def test_seed_scheme_disjoint_and_frozen(self):
        old, added = set(), set()
        for task in range(164):
            for sample in range(3):
                for arm in gen_prompts.ARMS:
                    for stage in range(4):
                        for retry in (0, 1):
                            old.add(gen_prompts.seed(task, arm, sample, stage, retry))
                for index, arm in enumerate(prompts.ARMS):
                    for stage in (0, 1):
                        actual = prompts.seed(task, arm, sample, stage)
                        self.assertEqual(actual, 20261010 + (((250000+task*2+index)*1000+sample)*8+stage*2))
                        added.add(actual)
        self.assertFalse(old & added)
        self.assertEqual(len(added), 164*3*2*2)

    def test_k3_shared_stage1_settings_cost_and_resume(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            root = Path(directory)
            client = Canned()
            run.generate(self.small, root, workers=2, client=client)
            self.assertEqual(len(client.requests), 14)
            docs = [r for r in client.requests if r["max_tokens"] == 4096]
            self.assertEqual(len(docs), 2)
            for request in client.requests:
                settings = {k: request[k] for k in ("temperature", "top_p", "max_tokens")}
                self.assertEqual(settings, run.DOC_SETTINGS if request in docs else run.TEST_SETTINGS)
            rows = [json.loads(line) for line in (root / "gen.jsonl").read_text().splitlines()]
            self.assertEqual(len(rows), 12)
            self.assertEqual(sum(r["llm_calls"] for r in rows), 14)
            self.assertEqual(sum(r["n_in"] for r in rows), 140)
            for row in rows:
                self.assertEqual(row["seed"], prompts.seed(row["task"], row["arm"], row["sample"]))
                self.assertEqual(row["llm_calls"], 2 if row["arm"] == "advdoc" and row["sample"] == 0 else 1)
            manifest = json.loads((root / "manifest.json").read_text())
            self.assertEqual(manifest["prereg_sha256"], run.sha((run.HARNESS / "PREREG.md").read_bytes()))
            self.assertEqual(manifest["prompt_sha256"]["test_generation"], run.sha(prompts.TEST_GENERATION_PROMPT))
            original = (root / "gen.jsonl").read_bytes()
            run.generate(self.small, root, workers=2, client=client)
            self.assertEqual(len(client.requests), 14)
            self.assertEqual((root / "gen.jsonl").read_bytes(), original)
            with self.assertRaises(ValueError):
                run.generate(self.small, root, k=1, client=client)

    def test_interrupted_run_reuses_stage1_and_completed_samples(self):
        small = dict(self.small, tasks=self.small["tasks"][:1])
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            root = Path(directory)
            client = Canned(fail_after=2)
            with self.assertRaises(RuntimeError):
                run.generate(small, root, k=1, workers=1, client=client)
            # Completed artifacts are recoverable even if the JSONL append was interrupted.
            (root / "gen.jsonl").unlink(missing_ok=True)
            client.fail_after = None
            run.generate(small, root, k=1, workers=1, client=client)
            self.assertEqual(len(client.requests), 3)
            self.assertEqual(sum(r["max_tokens"] == 4096 for r in client.requests), 1)

    def test_two_task_k1_smoke_through_existing_evaluator(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            root = Path(directory)
            client = Canned(fail_doc_task8=True)
            run.generate(self.small, root, k=1, workers=1, client=client)
            parsed = json.loads((root / "advanced_doc/8/parsed.json").read_text())
            self.assertTrue(parsed["used_fallback"])
            self.assertEqual(parsed["docstring"], run.preconditions.specification(self.small["tasks"][1])[1])
            run.evaluate(root)  # Real unshare -rn workers, real canonical/PUT scoring.
            scored = [json.loads(line) for line in (root / "eval.jsonl").read_text().splitlines()]
            self.assertEqual(len(scored), 4)
            for row in scored:
                self.assertIn("input_metrics", row)
                self.assertEqual(row["facts_version"], "v3m")
                self.assertEqual(row["llm_calls"], 2 if row["arm"] == "advdoc" else 1)
                if row["task"] == 2:
                    self.assertEqual((row["asserts"][0]["canon"], row["asserts"][0]["put"]), ("ok", "fail"))
                    self.assertEqual(row["asserts"][1]["canon"], "fail")
            with contextlib.redirect_stdout(io.StringIO()) as output:
                gen_evaluation.report(root / "tasks.json", root / "eval.jsonl")
            self.assertIn("onlydoc", output.getvalue())
            self.assertIn("advdoc", output.getvalue())
            # Existing reports remain byte-identical when the appended arms are absent.
            old_rows = [dict(r, arm="plain") for r in scored if r["arm"] == "onlydoc"]
            (root / "old_eval.jsonl").write_text("".join(json.dumps(r)+"\n" for r in old_rows))
            outputs = []
            for arms in (gen_evaluation.ARMS, gen_prompts.ARMS):
                with patch.object(gen_evaluation, "ARMS", arms), contextlib.redirect_stdout(io.StringIO()) as text:
                    gen_evaluation.report(root / "tasks.json", root / "old_eval.jsonl")
                outputs.append(text.getvalue())
            self.assertEqual(*outputs)

    def test_oracle_wrapper_copies_cache_and_uses_existing_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target, cache = root / "run", root / "oracle", root / "old_cache"
            source.mkdir()
            cache.mkdir()
            for name in ("manifest.json", "tasks.json"):
                (source / name).write_text("{}")
            (source / "eval.jsonl").write_text("")
            (cache / ("a"*64+".json")).write_text('{"text":"cached reference"}')
            (cache / "calls.jsonl").write_text("ignored usage log")
            with patch.object(run.oracle_b01, "collect") as collect, \
                    patch.object(run.oracle_b01, "llm") as llm, patch.object(run.oracle_b01, "score") as score:
                run.oracle("all", source, target, workers=4, cache_source=cache)
                collect.assert_called_once_with(source, target)
                llm.assert_called_once_with(source, target, workers=4)
                score.assert_called_once_with(source, target, workers=4, use_llm=True)
            self.assertEqual(json.loads((target / "cache" / ("a"*64+".json")).read_text()),
                             {"text": "cached reference"})
            self.assertFalse((target / "cache/calls.jsonl").exists())
            (source / "eval.jsonl").write_text("changed cohort")
            with self.assertRaises(ValueError):
                run.oracle("collect", source, target, cache_source=cache)

    def test_secret_redaction_and_output_scope(self):
        # Values are generated locally; no live endpoint or credential is inspected.
        secret = "canned-private-endpoint-marker"
        token = "canned-private-token-marker"
        with tempfile.TemporaryDirectory() as directory, patch.dict("os.environ", QWEN_BASE_URL=secret, QWEN_API_KEY=token):
            path = Path(directory) / "response.json"
            run.save(path, dict(text=secret+" "+token, nested=[secret]))
            self.assertNotIn(secret, path.read_text())
            self.assertNotIn(token, path.read_text())
        self.assertEqual(run.under_out(run.OUT), run.OUT)
        with self.assertRaises(ValueError):
            run.under_out(Path("/tmp/invalid-cli-output"))


if __name__ == "__main__":
    unittest.main()
