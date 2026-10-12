"""Canned CPU checks, frozen v4 sources, and a real two-task sandbox smoke."""
from __future__ import annotations

import ast
import contextlib
import copy
import io
import json
import os
import random
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from trickcatcher_linefacts import gen_prompts, run_v4, v4_prompts
from trickcatcher_linefacts.evalmitigate import prompts, run_advhyb as run

FROZEN_V4 = {
    "run_v4.py": "89b794dd44bcfc1f646eb3621453c21b7ccf0a49cb0cba787418e066ab86c29b",
    "v4_evaluation.py": "02368654082344651432ec4844efd2b4cede4f90fe75836f0c385f7c4251f7ba",
    "v4_facts.py": "517e03301f51c3ab763c534c63e7bfa49fcd8f5dbafbd39dca15f7954e7720fc",
    "v4_offline.py": "a449667414f11e610956037a4373cdc1fe5376561cb40413acfa770deef0e666",
    "v4_prompts.py": "6a0c161b0a35cfac411f3539ac8560bcedd5ebac18ad730215c80ad7643fd76f",
    "v4_runtime.py": "017fba439b132250ee5e9066460a0f36b5adee37d6086262b5f5b668adc6a9aa",
    "v4_strategies.py": "12826f661273a518ec4814a37a89eb9057cc7168efbcef31dd925dee227d7526",
    "v4_tools.py": "94820f9d0c691c2a0df4e9fdb3117f12cafcefbb9f6993cbf8b94c0d341fc7aa",
    "v4_worker.py": "afcf03d8b84153463a01f871236c8b3055e4808b75a06ad95d50e1e164504b7d",
}


def v4_python():
    if os.environ.get("V4_PYTHON"):
        return Path(os.environ["V4_PYTHON"])
    # Discover the existing pinned scratch venv without creating/installing tools.
    found = sorted(Path("/tmp").glob("claude-*/**/codex_v4/venv/bin/python"))
    if found:
        return found[0]
    return run.v4_runtime.interpreter()


class Canned:
    model = "qwen2.5-coder-7b-instruct"

    def __init__(self, *, retry_first=False, fail_controls=False, fail_after=None):
        self.requests = []
        self.retry_first = retry_first
        self.fail_controls = fail_controls
        self.fail_after = fail_after

    def chat(self, messages, seed, **settings):
        if self.fail_after == len(self.requests):
            raise RuntimeError("canned interruption")
        self.requests.append(dict(messages=copy.deepcopy(messages), seed=seed, **settings))
        if settings == run.STRATEGY_SETTINGS:
            text = "def strategy():\n    return st.just((1.0,))\n"
            if self.retry_first and len(self.requests) == 1:
                text = "def wrong():\n    return 1\n"
            if self.fail_controls and v4_prompts.CONTROL in messages[1]["content"]:
                text = "def wrong():\n    return 1\n"
        else:
            user = messages[-1]["content"]
            cs = user.split("SELECTED INPUTS:\n")[1].strip().splitlines()
            text = "```python\n" + "\n".join(f"assert {c} == 0.0" for c in cs) + "\n```"
        return dict(text=text, key=str(seed), params=dict(model=self.model, seed=seed, **settings),
                    n_in=10, n_out=20, seconds=0.25, cache_hit=False, transport_attempts=1)


def make_source(root, bundle, k=1):
    source = root / "advdoc"
    source.mkdir()
    rows = []
    for t in bundle["tasks"]:
        n = t["task"]
        assertions = (["assert truncate_number(3.5) == 0.5"] if n == 2 else
                      ["assert sum_product([]) == (0, 1)"])
        parsed = dict(task=n, run_id="saved-advdoc", docstring="SAVED_FALLBACK_SPEC" if n == 8 else
                      "Return the fractional part of a nonnegative floating point number.",
                      parse_failure="missing_part3" if n == 8 else None, used_fallback=n == 8)
        run.save(source / "advanced_doc" / str(n) / "parsed.json", parsed)
        for s in range(k):
            call = dict(key=f"saved-{n}-{s}", params=dict(seed=123), n_in=3, n_out=4, seconds=0.5)
            rows.append(dict(task=n, split=t["split"], arm="advdoc", sample=s, run_id="saved-advdoc",
                             text="```python\n" + "\n".join(assertions) + "\n```", calls=[call]))
            rows.append(dict(task=n, split=t["split"], arm="onlydoc", sample=s,
                             text="assert DO_NOT_USE_ONLYDOC() == 999"))
    (source / "gen.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    return source


def rows(out, name="gen.jsonl"):
    return [json.loads(s) for s in (out / name).read_text().splitlines()]


def fake_classify(task, directory, python, *, candidates=None, assertions=None, shown=(), requested_draws=None):
    records = []
    for c in candidates or []:
        args = ast.literal_eval(c["input_repr"])
        good = args[0] != -1
        hit = args[0] == 1
        records.append(dict(c, valid=good, call=f"{task['entry']}({args[0]!r})",
                            concept_hits=[hit]*len(task["concept_meta"]), shown_hits=[hit]*len(shown)))
    if assertions is not None:
        hit = any("(1.0)" in a for a in assertions)
        records = [dict(valid=True)] * len(assertions)
        counts = [int(hit)] * len(shown)
    else:
        counts = [sum(r["valid"] and r["shown_hits"][i] for r in records) for i in range(len(shown))]
    return dict(records=records, summary=dict(valid=sum(r["valid"] for r in records),
                                             shown_hit_counts=counts, removed=0))


def fake_draws(*args, **kwargs):
    # Include invalid and non-hitting inputs; targeted selection must exclude both.
    return dict(candidates=[dict(input_repr=repr((n,))) for n in (-1, 2, 1, 1.0)],
                nonliteral=0, wrong_arity=0, errors=[])


class AdvhybTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.small = run.load_bundle(ids=[2, 8])
        cls.one = dict(cls.small, tasks=cls.small["tasks"][:1])

    def test_frozen_run_v4_and_all_v4_sources(self):
        self.assertEqual({p.name for p in run.HARNESS.glob("v4_*.py")}, set(FROZEN_V4) - {"run_v4.py"})
        for name, sha in FROZEN_V4.items():
            self.assertEqual(run.sha((run.HARNESS / name).read_bytes()), sha, name)

    def test_round1_reads_advdoc_rows_and_fallback_doc_without_regeneration(self):
        with tempfile.TemporaryDirectory() as d:
            source = make_source(Path(d), self.small, k=3)
            originals, docs, hashes = run.read_advdoc(self.small, 3, source)
            self.assertEqual(len(originals), 6)
            for (task, sample), row in originals.items():
                self.assertEqual(row["arm"], "advdoc")
                self.assertNotIn("DO_NOT_USE_ONLYDOC", row["text"])
            self.assertEqual(docs[8]["docstring"], "SAVED_FALLBACK_SPEC")
            self.assertTrue(docs[8]["used_fallback"])
            self.assertEqual(hashes["gen_sha256"], run.sha((source / "gen.jsonl").read_bytes()))
            with self.assertRaises(ValueError):
                run.read_advdoc(self.small, 4, source)
            with (source / "gen.jsonl").open("a") as f:
                f.write(json.dumps(originals[2, 0]) + "\n")
            with self.assertRaises(ValueError):
                run.read_advdoc(self.small, 3, source)

    def test_injected_prompt_hides_put_base_facts_and_uses_saved_doc(self):
        task = self.one["tasks"][0]
        tree = ast.parse(task["put"])
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef))
        fn.body = [ast.parse("raise RuntimeError('UNIQUE_PUT_BODY')").body[0]]
        changed = dict(task, put=ast.unparse(ast.fix_missing_locations(tree)), base="UNIQUE_BASE_TESTS",
                       concept_meta=[dict(text="UNIQUE_FACT")])
        selected = [dict(call="truncate_number(1.0)")]
        expected = run.injected_messages(task, "SAVED_SPECIFICATION", selected)
        self.assertEqual(expected, run.injected_messages(changed, "SAVED_SPECIFICATION", selected))
        text = json.dumps(expected)
        for marker in ("UNIQUE_PUT_BODY", "UNIQUE_BASE_TESTS", "UNIQUE_FACT", "integer_part", "PUT:"):
            self.assertNotIn(marker, text)
        self.assertIn("SAVED_SPECIFICATION", text)
        self.assertIn("truncate_number(1.0)", text)
        self.assertIn("one assertion per input", text)
        self.assertIn("specification", text)

    def test_new_seeds_disjoint_unique_and_uint32(self):
        old, new = set(), set()
        for t in range(164):
            for s in range(3):
                for a in v4_prompts.ARMS:
                    for stage in range(4):
                        for req in range(6):
                            for retry in (0, 1):
                                old.add(v4_prompts.seed(t, a, s, stage, req, retry))
                for a in prompts.ARMS:
                    for stage in (0, 1):
                        old.add(prompts.seed(t, a, s, stage))
                for a in gen_prompts.ARMS:
                    for stage in range(4):
                        for retry in (0, 1):
                            old.add(gen_prompts.seed(t, a, s, stage, retry))
                for a in run.ARMS:
                    for stage in range(4):
                        for req in range(6):
                            for retry in (0, 1):
                                new.add(run.seed(t, a, s, stage, req, retry))
        self.assertFalse(old & new)
        self.assertEqual(len(new), 164*3*2*4*6*2)
        self.assertLess(run.seed(999, run.ARMS[1], 999, 3, 63, 1), 2**32)

    def generate_fake(self, source, out, client, bundle=None):
        with patch.object(run.run_v4, "classify", side_effect=fake_classify), \
                patch.object(run.v4_strategies, "draws", side_effect=fake_draws), \
                patch.object(run.v4_runtime, "interpreter", return_value=Path(sys.executable)), \
                patch.object(run_v4.gen_prompts, "oracle_messages", side_effect=AssertionError("PUT oracle forbidden")):
            run.generate(bundle or self.one, out, source=source, client=client, k=1, workers=1)

    def test_retry_budget_control_selection_merge_settings_and_resume(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            root = Path(d)
            source = make_source(root, self.one)
            out = root / "hybrid"
            client = Canned(retry_first=True)
            self.generate_fake(source, out, client)
            targeted, plain = rows(out)
            self.assertEqual(targeted["round2_strategy_requests"], 4)
            self.assertEqual(plain["round2_strategy_requests"], 4)
            self.assertEqual(plain["matched_strategy_requests"], 4)
            self.assertEqual(targeted["missed_fact_indices"], [0, 1, 2])
            self.assertEqual(plain["missed_fact_indices"], [])
            for r in (targeted, plain):
                self.assertEqual(r["round1_assertions"], ["assert truncate_number(3.5) == 0.5"])
                self.assertEqual(r["assertions"][0], r["round1_assertions"][0])
                self.assertEqual(r["calls"][0]["key"], "saved-2-0")
                self.assertEqual(r["llm_calls"], 6)  # saved round1 + four strategies + oracle
                self.assertEqual(r["n_in"], 53)
                self.assertTrue(all(len(a["selected"]) <= 2 for a in r["generator_attempts"]))
                for a in r["generator_attempts"]:
                    if a["error"]:
                        self.assertEqual(a["selected"], [])
                        continue
                    good = [x for x in fake_classify(self.one["tasks"][0], None, None,
                                                    candidates=fake_draws()["candidates"],
                                                    shown=[{}] if r["arm"] == run.ARMS[0] else [])["records"]
                            if x["valid"] and (r["arm"] == run.ARMS[1] or x["shown_hits"][0])]
                    picked = random.Random(run.seed(2, r["arm"], 0, 3, a["request"], a["retry"])).sample(
                        good, min(2, len(good)))
                    self.assertEqual(a["selected"], picked)
            self.assertTrue(all(r["valid"] and all(r["shown_hits"]) for r in targeted["selected_inputs"]))
            self.assertTrue(all(r["valid"] for r in plain["selected_inputs"]))
            for req in client.requests:
                user = req["messages"][1]["content"]
                settings = {key: req[key] for key in run.ORACLE_SETTINGS}
                if "SELECTED INPUTS:" in user:
                    self.assertEqual(settings, run.ORACLE_SETTINGS)
                    self.assertNotIn("integer_part = int(number)", user)
                else:
                    self.assertEqual(settings, run.STRATEGY_SETTINGS)
                    self.assertIn("DOMAIN STRATEGY:", user)
            controls = [r for r in client.requests if v4_prompts.CONTROL in r["messages"][1]["content"]]
            self.assertEqual(len(controls), 4)
            self.assertTrue(all(len(r["messages"]) == 2 for r in controls))
            self.assertEqual(client.requests[1]["messages"][-1]["content"],
                             v4_prompts.RETRY.format(error=targeted["generator_attempts"][0]["error"]))
            original = (out / "gen.jsonl").read_bytes()
            self.generate_fake(source, out, client)
            self.assertEqual(len(client.requests), 10)
            self.assertEqual((out / "gen.jsonl").read_bytes(), original)
            manifest = json.loads((out / "manifest.json").read_text())
            self.assertEqual(manifest["prereg_sha256"], run.sha((run.HARNESS / "PREREG.md").read_bytes()))
            self.assertEqual(manifest["bundle_sha256"], run.digest(self.one))
            self.assertEqual(manifest["prompt_sha256"]["injected"], run.sha(run.INJECTED_PROMPT))
            parsed = source / "advanced_doc/2/parsed.json"
            parsed.write_text(parsed.read_text() + "\n")
            with self.assertRaises(ValueError):
                self.generate_fake(source, out, client)

    def test_plain_errors_do_not_retry_and_empty_selection_still_queries_oracle(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            root = Path(d)
            source = make_source(root, self.one)
            out = root / "hybrid"
            client = Canned(fail_controls=True)
            self.generate_fake(source, out, client)
            targeted, plain = rows(out)
            self.assertEqual(targeted["round2_strategy_requests"], 3)
            self.assertEqual(plain["round2_strategy_requests"], 3)
            self.assertEqual(plain["selected_inputs"], [])
            self.assertEqual(plain["assertions"], plain["round1_assertions"])
            self.assertTrue(all(a["error"] and a["retry"] == 0 for a in plain["generator_attempts"]))
            self.assertEqual(plain["llm_calls"], 5)

    def test_all_round1_facts_hit_skips_round2_for_both_arms(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            root = Path(d)
            source = make_source(root, self.one)
            rr = rows(source)
            rr[0]["text"] = "assert truncate_number(1.0) == 0.0"
            (source / "gen.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rr))
            out = root / "hybrid"
            (out / "cache").mkdir(parents=True)
            (out / "cache/preloaded.json").write_text("{}")
            client = Canned()
            self.generate_fake(source, out, client)
            self.assertEqual(client.requests, [])
            for r in rows(out):
                self.assertEqual(r["round2_strategy_requests"], 0)
                self.assertEqual(r["assertions"], ["assert truncate_number(1.0) == 0.0"])
            self.assertTrue((out / "cache/preloaded.json").exists())

    def test_interruption_resumes_completed_arm_and_keeps_budget(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            root = Path(d)
            source = make_source(root, self.one)
            out = root / "hybrid"
            client = Canned(fail_after=4)
            with self.assertRaises(RuntimeError):
                self.generate_fake(source, out, client)
            self.assertTrue((out / "artifacts/2/0/advdoc-hybrid/result.json").exists())
            self.assertFalse((out / "gen.jsonl").exists())
            client.fail_after = None
            self.generate_fake(source, out, client)
            self.assertEqual(len(client.requests), 8)
            self.assertEqual(rows(out)[1]["round2_strategy_requests"], 3)

    def test_two_task_k1_generate_evaluate_real_v4_sandboxes(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            root = Path(d)
            source = make_source(root, self.small)
            out = root / "hybrid"
            client = Canned()
            with patch.object(run_v4.gen_prompts, "oracle_messages", side_effect=AssertionError("PUT oracle forbidden")):
                run.generate(self.small, out, source=source, python=v4_python(), k=1, workers=2, client=client)
            generated = rows(out)
            target, plain = [r for r in generated if r["task"] == 2]
            self.assertEqual(target["round2_strategy_requests"], 3)
            self.assertEqual(plain["round2_strategy_requests"], 3)
            self.assertEqual(target["round1_input_summary"]["shown_hit_counts"], [0, 0, 0])
            self.assertEqual(target["assertions"], ["assert truncate_number(3.5) == 0.5",
                                                      "assert truncate_number(1.0) == 0.0"])
            for r in generated:
                if r["task"] == 8:
                    self.assertEqual(r["round2_strategy_requests"], 0)
                    self.assertEqual(r["assertions"], r["round1_assertions"])
                    self.assertEqual(r["docstring_parse_failure"], "missing_part3")
            run.evaluate(out)
            scored = rows(out, "eval.jsonl")
            self.assertEqual(len(scored), 4)
            for r in scored:
                self.assertEqual(r["facts_version"], "v4")
                self.assertIn("input_metrics", r)
                if r["task"] == 2:
                    self.assertEqual((r["asserts"][1]["canon"], r["asserts"][1]["put"]), ("ok", "fail"))
            self.assertTrue((out / "report.txt").exists())
            self.assertIn("comparisons", json.loads((out / "report.json").read_text())["dev"])
            # Real oracle collector also accepts the new names and schema.
            oracle = root / "oracle"
            run.oracle("collect", out, oracle, cache_source=root / "absent")
            self.assertIn("truncate_number(1.0)", json.loads((oracle / "calls.json").read_text())["2"])
            first = (out / "gen.jsonl").read_bytes()
            run.generate(self.small, out, source=source, python=v4_python(), k=1, workers=2, client=client)
            self.assertEqual(len(client.requests), 8)
            self.assertEqual((out / "gen.jsonl").read_bytes(), first)

    def test_oracle_cache_copy_and_delegate(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source, out, cache = root / "run", root / "oracle", root / "cache"
            source.mkdir()
            cache.mkdir()
            for name in ("manifest.json", "tasks.json"):
                (source / name).write_text("{}")
            (source / "eval.jsonl").write_text("")
            (cache / ("a"*64 + ".json")).write_text('{"text":"cached ref/post"}')
            (cache / "calls.jsonl").write_text("ignore")
            with patch.object(run, "check_cohort"), patch.object(run.oracle_b01, "collect") as collect, \
                    patch.object(run.oracle_b01, "llm") as llm, patch.object(run.oracle_b01, "score") as score:
                run.oracle("all", source, out, workers=16, cache_source=cache)
                collect.assert_called_once_with(source, out)
                llm.assert_called_once_with(source, out, workers=16)
                score.assert_called_once_with(source, out, workers=12, use_llm=True)
            self.assertEqual(json.loads((out / "cache" / ("a"*64 + ".json")).read_text()),
                             {"text": "cached ref/post"})
            self.assertFalse((out / "cache/calls.jsonl").exists())

    def test_secret_redaction_and_manifest_rejects_incomplete_cohort(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            root = Path(d)
            source = make_source(root, self.one)
            out = root / "hybrid"
            with patch.dict(os.environ, QWEN_BASE_URL="UNIQUE_ENDPOINT_MARKER", QWEN_API_KEY="UNIQUE_TOKEN_MARKER"):
                run.save(root / "redacted.json", dict(text="UNIQUE_ENDPOINT_MARKER UNIQUE_TOKEN_MARKER"))
            self.assertNotIn("UNIQUE_ENDPOINT_MARKER", (root / "redacted.json").read_text())
            self.assertNotIn("UNIQUE_TOKEN_MARKER", (root / "redacted.json").read_text())
            self.generate_fake(source, out, Canned())
            (out / "gen.jsonl").write_text(json.dumps(rows(out)[0]) + "\n")
            with self.assertRaises(ValueError), patch.object(run.evaluator, "evaluate") as evaluate:
                run.evaluate(out)
            evaluate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
