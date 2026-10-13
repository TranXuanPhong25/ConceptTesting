"""Offline adapter regression tests; all solution execution is sandboxed."""
import ast
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from . import vibepass as vp
from .bindings import Paths, task_sources


def fixture():
    return dict(question_id="fixture", question_content='Return a value.\nPreserve "quotes" and \\slashes.',
                starter_code="class Solution:\n    def solve(self, xs: List[int], scale: int = 1) -> float:\n",
                buggy_solution="def helper(xs):\n    return sum(xs)\n\nclass Solution:\n"
                               "    def solve(self, xs, scale=1):\n        xs.append(0)\n"
                               "        return helper(xs) * scale + (1 if len(xs) > 2 else 0)\n",
                silver_solution="class Solution:\n    def solve(self, xs, scale=1):\n"
                                "        xs.append(0)\n        return sum(xs) * scale\n",
                test_checker="def is_valid_test(xs, scale=1):\n"
                             "    return isinstance(xs, list) and bool(xs) and scale > 0\n")


class AdapterTests(unittest.TestCase):
    def test_signature_docstring_and_preserved_source(self):
        row = fixture()
        he, plus, put = vp.normalize(row, 17, "solve", [[[2], 1]], [[[2, 3], 1]])
        tree = ast.parse(put)
        entry = tree.body[-1]
        self.assertEqual(entry.name, "solve")
        self.assertEqual(ast.get_docstring(entry, clean=False), row["question_content"])
        self.assertEqual(ast.unparse(entry.args), "xs: List[int], scale: int=1")
        self.assertEqual(ast.unparse(entry.returns), "float")
        self.assertIn(row["buggy_solution"], put)
        self.assertIn(row["silver_solution"], he["canonical_solution"])
        self.assertIn(row["test_checker"], plus["contract"])
        self.assertIn("assert is_valid_test", plus["contract"])
        self.assertEqual(he["task_id"], "HumanEval/17")
        ast.parse(he["prompt"] + he["canonical_solution"])
        ast.parse(he["prompt"] + plus["contract"])
        self.assertEqual(vp.arguments('[1,2]\n3\n'), [[1, 2], 3])

    def job(self):
        he, plus, put = vp.normalize(fixture(), 17, "solve", [[[2], 1]], [[[2, 3], 1]])
        return dict(entry="solve", put=put, canon=he["prompt"] + he["canonical_solution"],
                    contract=he["prompt"] + plus["contract"], base=plus["base_input"],
                    plus=plus["plus_input"], generated=[[[], 1], [[3], 1]], atol=0)

    def verify(self, job):
        with tempfile.TemporaryDirectory() as directory:
            return vp.verify(job, Path(directory), sys.executable, timeout=30)

    def test_real_sandbox_checks_contract_and_private_difference(self):
        result = self.verify(self.job())
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["generated_valid_indices"], [1])
        self.assertEqual(result["plus_failure"]["source"], "private")
        self.assertEqual(result["put_check_status"], "ok")

    def test_rejected_public_is_reported_not_dropped(self):
        job = self.job(); job["base"] = [[[], 1]]
        result = self.verify(job)
        self.assertFalse(result["ok"])
        self.assertEqual(result["base_rejected"], [0])
        self.assertEqual(result["n_base"], 1)

    def test_identical_put_fails_selection(self):
        job = self.job(); job["put"] = job["canon"]
        result = self.verify(job)
        self.assertFalse(result["ok"])
        self.assertIsNone(result["plus_failure"])

    def test_tolerant_comparison_and_generated_only_witness(self):
        job = dict(entry="f", canon="def f(n):\n    return [float(n)]\n",
                   put="def f(n):\n    return [n + (5e-7 if n == 1 else 1)]\n",
                   contract="def f(n):\n    assert n > 0\n", base=[[1]], plus=[[0]], generated=[[2]], atol=0)
        result = self.verify(job)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["plus_rejected"], 1)
        self.assertEqual(result["plus_failure"]["source"], "generated")

    def test_wrapper_copies_input_and_constructs_fresh_solution(self):
        job = self.job()
        job["put"] = job["put"].replace("        xs.append(0)",
            "        assert not getattr(self, '_called', False)\n"
            "        self._called = True\n        xs.append(0)")
        # Exercise the wrapper repeatedly in the sandbox, checking the caller's
        # input and Solution instance isolation, beyond tracer-side copying.
        job["put"] += "\n_original = solve\ndef solve(xs, scale=1):\n" \
                       "    before = list(xs)\n    a = _original(xs, scale)\n" \
                       "    b = _original(xs, scale)\n    assert xs == before and a == b\n    return a\n"
        result = self.verify(job)
        self.assertTrue(result["ok"], result)

    def test_sandbox_command_and_scrubbed_environment(self):
        with patch.object(vp.subprocess, "run") as run:
            vp.sandbox(["worker.py"], "/usr/bin/python3", timeout=11)
        args, kwargs = run.call_args
        self.assertEqual(args[0], ["unshare", "-rn", "/usr/bin/python3", "-I", "-B", "worker.py"])
        self.assertEqual(set(kwargs["env"]), {"PATH", "LANG"})
        self.assertEqual(kwargs["timeout"], 11)

    def test_sandbox_timeout_is_persisted_as_failure(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
                vp, "sandbox", side_effect=vp.subprocess.TimeoutExpired("sandbox", 1)):
            result = vp.verify(self.job(), Path(directory), sys.executable, timeout=1)
            self.assertFalse(result["ok"])
            self.assertEqual(json.loads((Path(directory) / "result.json").read_text()), result)

    def test_build_keeps_failed_id_in_manifest_and_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / "input"; out = Path(directory) / "he"
            (data / "data/vibepass").mkdir(parents=True)
            (data / "scratch/tests").mkdir(parents=True)
            good = dict(fixture(), difficulty="medium", platform="leetcode")
            bad = dict(good, starter_code="invalid Python")
            (data / "data/vibepass/test.jsonl").write_text("".join(json.dumps(r) + "\n" for r in (good, bad)))
            items = [dict(row=n, question_id="fixture", uid=f"fixture#{n}", platform="leetcode",
                          usable_strict=True, func_name="solve", fuzz_checker_valid=0) for n in (0, 1)]
            (data / "usable.json").write_text(json.dumps(dict(source={}, instances=items)))
            tests = dict(question_id="fixture", func_name="solve",
                         public=[dict(input="[2]\n1")], private=[dict(input="[2,3]\n1")])
            (data / "scratch/tests/fixture.json").write_text(json.dumps(tests))
            with patch.object(vp, "generated_candidates", return_value={0: [], 1: []}):
                manifest = vp.build(data, out, sys.executable, workers=1)
            self.assertEqual(manifest["tasks_selected"], 2)
            self.assertEqual(manifest["tasks_built"], 1)
            self.assertEqual(manifest["tasks_verified"], 1)
            self.assertEqual(manifest["failing_checks"], [1])
            self.assertEqual((out / "tasks.txt").read_text(), "0\n1\n")
            self.assertEqual([p["task"] for p in manifest["puts"]], [0, 1])
            self.assertIn("error", manifest["puts"][1]["verification"])


@unittest.skipUnless((vp.OUT / "manifest.json").exists(), "build the real offline dataset first")
class BuiltDatasetTests(unittest.TestCase):
    def test_run_cli_accepts_custom_root_and_binds_task_sources(self):
        from . import run
        from trickcatcher_linefacts import run_v4
        seen = []
        def inspect_bundle(paths):
            tasks, he, pilot = run_v4.task_sources(paths.ids())
            seen.append((paths.root, len(tasks), len(he), pilot))
        argv = ["heldout.run", "bundle", "--root", str(vp.OUT.parent)]
        # Exercise real CLI parsing and scoped binding, replacing only the
        # post-mining bundle step; no mining or LLM client is constructed.
        with patch.object(sys, "argv", argv), patch.object(run, "bundle", side_effect=inspect_bundle):
            run.main()
        self.assertEqual(seen, [(vp.OUT.parent, 66, 66, [])])

    def test_manifest_sources_contracts_and_root_compatibility(self):
        manifest = json.loads((vp.OUT / "manifest.json").read_text())
        self.assertEqual((manifest["tasks_built"], manifest["tasks_verified"], manifest["questions"]), (66, 66, 24))
        self.assertEqual(manifest["failing_checks"], [])
        paths = Paths(vp.OUT.parent)
        tasks, he, pilot = task_sources(paths, paths.ids())
        self.assertEqual(len(tasks), 66)
        self.assertEqual(pilot, [])
        plus = {int(r["task_id"].split("/")[1]): r for r in map(json.loads, paths.plus.read_text().splitlines())}
        raw = [json.loads(line) for line in (vp.DATA / "data/vibepass/test.jsonl").read_text().splitlines()]
        for record in manifest["puts"]:
            n = record["task"]; row = raw[n]
            self.assertEqual(record["question_id"], row["question_id"])
            self.assertEqual(record["uid"], f"{row['question_id']}#{n}")
            put = (paths.puts / f"HumanEval_{n}/put0.py").read_text()
            self.assertIn(row["buggy_solution"], put)
            self.assertEqual(record["put_sha256"], vp.digest(put))
            self.assertEqual(record["n_private"] + record["n_generated"], len(plus[n]["plus_input"]))
            self.assertEqual(ast.get_docstring(ast.parse(put).body[-1], clean=False), row["question_content"])
            ast.parse(he[n]["prompt"] + he[n]["canonical_solution"])
            ast.parse(plus[n]["prompt"] + plus[n]["contract"])


if __name__ == "__main__":
    unittest.main()
