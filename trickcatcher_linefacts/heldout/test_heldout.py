"""Offline integration checks. All execution uses namespaces; no LLM or network."""
import ast
import builtins
import contextlib
import gzip
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
import warnings
from unittest.mock import patch

from . import dataset, run
from .bindings import Paths, bound

# Same existing v4 venv used by the dev pipeline; override with --python's
# equivalent V4_PYTHON when running these tests on another installation.
LOCAL_V4 = Path("/tmp/claude-1000/-home-phong-dev-ConceptTester/2dddac78-7845-4887-9c28-b6313bcf7c52/scratchpad/codex_v4/venv/bin/python")


@contextlib.contextmanager
def no_humaneval_reads():
    """Fail on original datasets, PUTs or cohort lists, including bound defaults."""
    original_open = builtins.open
    path_open = Path.open
    def guard(path):
        if isinstance(path, (str, os.PathLike)):
            p = str(Path(path).absolute())
            forbidden = ("PBT_EdgeCases/run/data/humaneval", ".cache/evalplus/HumanEvalPlus",
                         "vendor/TrickCatcher/Datasets/EvalPlus/PUTs")
            if any(x in p for x in forbidden) or p in {
                str(dataset.ROOT / "tasks.txt"), str(dataset.ROOT / "out/pilot_tasks.json")}:
                raise AssertionError("stray HumanEval read: " + p)
    def opened(file, *args, **kwargs):
        guard(file); return original_open(file, *args, **kwargs)
    def path_opened(self, *args, **kwargs):
        guard(self); return path_open(self, *args, **kwargs)
    with patch("builtins.open", opened), patch.object(Path, "open", path_opened):
        yield


class HeldoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # The unchanged dev drivers use short-lived open() comprehensions.
        warnings.filterwarnings("ignore", category=ResourceWarning)
        cls.scratch = tempfile.TemporaryDirectory(prefix="heldout_test_", dir="/tmp")
        cls.paths = Paths(Path(cls.scratch.name))
        cls.python = Path(os.environ.get("V4_PYTHON", LOCAL_V4))
        if not cls.python.exists():
            raise RuntimeError("set V4_PYTHON to the dedicated v4 venv to run offline integration tests")
        from trickcatcher_linefacts.llm_client import Client
        cls.no_client = patch.object(Client, "__init__", side_effect=AssertionError("LLM forbidden in offline tests"))
        cls.no_client.start()
        with contextlib.redirect_stdout(io.StringIO()):
            cls.manifest = dataset.build(out=cls.paths.root / "he", ids=[99, 264], workers=2, python=cls.python)
        shutil.copyfile(dataset.DATA / "labels_manual.json", cls.paths.root / "labels_manual.json")
        cls.rows = {int(r["task_id"].split("/")[1]): r for r in map(json.loads, cls.paths.he.read_text().splitlines())}
        for n, row in cls.rows.items():
            put = (cls.paths.puts / f"HumanEval_{n}/put0.py").read_text()
            fn = dataset.entry_node(put, row["entry_point"])
            params = ast.unparse(fn.args)
            valid = f"def valid({params}):\n    return True\n"
            strategy = "def strategy():\n    return st.tuples(" + ", ".join("st.integers(-10, 2000)" for _ in fn.args.args) + ")\n"
            pd, sd = cls.paths.precond / str(n), cls.paths.strategy / str(n)
            pd.mkdir(parents=True); sd.mkdir(parents=True)
            (pd / "valid.py").write_text(valid)
            (pd / "summary.json").write_text(json.dumps(dict(evidence_filter=False, preconditions_version="B5", valid_sha256=dataset.digest(valid))))
            (sd / "strategy.py").write_text(strategy)
            (sd / "summary.json").write_text(json.dumps(dict(valid_sha256=dataset.digest(valid), strategy_sha256=dataset.digest(strategy), fallback=False)))
        # Real facts.py fuzz/tracing/ranking, with synthetic mining fixtures only.
        with no_humaneval_reads(), bound(cls.paths), contextlib.redirect_stdout(io.StringIO()):
            run.facts(cls.paths, cls.python, workers=2)
            # Exercise the v7 fallback on one task; this is a test fixture only.
            fp = cls.paths.facts / "99.json"
            fr = json.loads(fp.read_text()); fr["top3"] = []; fp.write_text(json.dumps(fr))
            run.specfacts(cls.paths, cls.python, workers=2)
            cls.bundle = run.bundle(cls.paths)

    @classmethod
    def tearDownClass(cls):
        cls.no_client.stop()
        cls.scratch.cleanup()

    def test_dataset_and_provenance(self):
        self.assertEqual(self.manifest["tasks_built"], 2)
        self.assertEqual(self.manifest["failing_checks"], [])
        plus = {int(r["task_id"].split("/")[1]): r for r in map(json.loads, self.paths.plus.read_text().splitlines())}
        with gzip.open(dataset.DATA / "raw/MbppPlus.jsonl.gz", "rt") as stream:
            raw = {int(r["task_id"].split("/")[1]): r for r in map(json.loads, stream)}
        for record in self.manifest["puts"]:
            n = record["task"]
            self.assertEqual(record["split"], "heldout")
            self.assertTrue(record["verification"]["put_check"])
            self.assertTrue(record["verification"]["canonical_check"])
            self.assertIsNotNone(record["verification"]["plus_failure"])
            source = (dataset.DATA / record["source_path"]).read_text()
            put = (self.paths.puts / f"HumanEval_{n}/put0.py").read_text()
            self.assertEqual(dataset.digest(source), record["source_sha256"])
            self.assertEqual(dataset.digest(put), record["put_sha256"])
            self.assertEqual(ast.get_docstring(dataset.entry_node(put, self.rows[n]["entry_point"]), clean=False), dataset.spec_text(raw[n]["prompt"]))
            ast.parse(self.rows[n]["prompt"] + self.rows[n]["canonical_solution"])
            ast.parse(plus[n]["prompt"] + plus[n]["contract"])
            self.assertEqual(plus[n]["base_input"], raw[n]["base_input"])
            self.assertEqual(plus[n]["plus_input"], raw[n]["plus_input"])

    def test_contract_rejection_and_recursive_float_tolerance(self):
        src = "def f(n):\n    return [float(n)]\n"
        put = "def f(n):\n    return [n + (5e-5 if n == 1 else 1)]\n"
        job = dict(entry="f", canon=src, put=put, contract="def f(n):\n    assert n > 0\n",
                   base=[[0], [1]], plus=[[0], [2]], atol=1e-4)
        result = dataset.verify(job, self.paths.root / "float_fixture", self.python)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["base_rejected"], 1)
        self.assertEqual(result["plus_rejected"], 1)
        self.assertEqual(result["n_base"], 1)
        self.assertEqual(len(__import__("trickcatcher_linefacts.spec_facts", fromlist=["base_args"]).base_args(result["test"])), 1)
        job["atol"] = 0
        result = dataset.verify(job, self.paths.root / "float_fixture_strict", self.python)
        self.assertFalse(result["put_check"])

    def test_rebinding_and_restoration(self):
        from trickcatcher_linefacts import generate, evaluate, oracle_b01, offline, gen_inputs, spec_facts, run_v4, run_v6
        old = generate.HE, evaluate.HEP, gen_inputs.load_contracts, run_v4.task_sources
        with no_humaneval_reads(), bound(self.paths):
            for module in (evaluate, oracle_b01, offline): self.assertEqual(module.HEP, self.paths.plus)
            self.assertEqual(offline.HE, self.paths.he)
            self.assertEqual(offline.PUTS, self.paths.puts)
            self.assertEqual(spec_facts.OUT, self.paths.specfacts)
            self.assertEqual(run_v6.PRECOND, self.paths.precond)
            self.assertEqual(generate.TASKS, self.paths.selection)
            self.assertEqual(set(gen_inputs.load_contracts()), {264, 99})
            tasks, he, pilot = run_v4.task_sources([99, 264])
            self.assertEqual(pilot, [])
            self.assertTrue(all(t["split"] == "heldout" for t in tasks))
            self.assertEqual(oracle_b01.variants("tc", 99), [])
            generate.bundle(264, he[264])  # definition-time default must rebind too
            with self.assertRaises(ValueError): run_v4.safe_path(dataset.ROOT / "out/tasks_v4_all.json")
            with self.assertRaises(ValueError): run_v4.safe_path(self.paths.root / "he")
            with self.assertRaises(ValueError): run_v4.task_sources([264, 264])
        self.assertEqual((generate.HE, evaluate.HEP, gen_inputs.load_contracts, run_v4.task_sources), old)

    def test_bundle_format_and_spec_fallback(self):
        dev = json.loads((dataset.ROOT / "out/tasks_v7hyb_v4.json").read_text())
        self.assertEqual(set(self.bundle), set(dev))
        normal = next(t for t in dev["tasks"] if not t.get("spec_facts"))
        spec = next(t for t in dev["tasks"] if t.get("spec_facts"))
        for t in self.bundle["tasks"]:
            self.assertEqual(set(t), set(spec if t.get("spec_facts") else normal))
            self.assertEqual(t["facts_version"], "v4")
            self.assertEqual(t["split"], "heldout")
            self.assertEqual(dataset.digest(t["strategy_src"]), t["strategy_sha256"])
            self.assertEqual(dataset.digest(t["mined_valid_src"]), t["valid_sha256"])
            self.assertLessEqual(len(t["concept_facts"]), 3)
            for key in ("concept_meta", "placebo_meta"):
                for fact in t[key]:
                    if fact["kind"] == "MUTANT": self.assertIn("mutant_src", fact)
        self.assertTrue(next(t for t in self.bundle["tasks"] if t["task"] == 99)["spec_facts"])
        self.assertFalse((self.paths.specfacts / "264.json").exists())

    def test_evaluation_and_oracle_without_llm(self):
        from trickcatcher_linefacts import evaluate, v4_prompts
        from .reporting import evaluation_report
        self.paths.generation.mkdir(exist_ok=True)
        (self.paths.generation / "tasks.json").write_text(json.dumps(self.bundle))
        inputs = {264: "assert dog_age(1) == 10.5", 99: "assert decimal_to_binary(-1) == '-1'"}
        rows = [dict(task=n, arm=arm, sample=s, split="heldout", text=src, assertions=[src], run_id="offline-fixture",
                     llm_calls=0, n_in=0, n_out=0, seconds=0) for n, src in inputs.items() for arm in v4_prompts.ARMS for s in range(3)]
        (self.paths.generation / "gen.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
        with no_humaneval_reads(), bound(self.paths), contextlib.redirect_stdout(io.StringIO()):
            evaluate.evaluate(self.paths.generation / "tasks.json", self.paths.generation / "gen.jsonl",
                              self.paths.generation / "eval.jsonl", self.python)
            run.check_run(self.paths)
            metrics = evaluation_report(self.paths)
            self.assertIn("heldout/all", metrics)
            self.assertIn("real-bug/all", metrics)
            run.oracle(self.paths, "collect")
            # Synthetic responses exercise scoring; no generation endpoint exists.
            self.paths.oracle.mkdir(exist_ok=True)
            refs = [dict(task=str(n), sample=s, text="```python\n" + self.rows[n]["prompt"] + self.rows[n]["canonical_solution"] + "\n```")
                    for n in inputs for s in range(10)]
            (self.paths.oracle / "ref_responses.json").write_text(json.dumps(refs))
            (self.paths.oracle / "post_responses.json").write_text(json.dumps([dict(task=str(n), sample=0, text="assert True") for n in inputs]))
            run.oracle(self.paths, "score", self.python, no_llm=True)
        metrics = json.loads((self.paths.oracle / "metrics.json").read_text())
        self.assertEqual(metrics["heldout"]["tasks"], [99, 264])
        self.assertEqual(metrics["heldout"]["arms"]["concept-hybrid"]["ref"]["any_of_k"], 2)
        self.assertEqual(metrics["heldout"]["arms"]["concept-hybrid"]["full"]["any_of_k"], 2)
        self.assertEqual(metrics["diagnostics"]["ref_variants"], 20)
        self.assertEqual(metrics["diagnostics"]["n_post_kept"], 2)
        self.assertEqual(metrics["diagnostics"]["n_pairs"], 6)
        self.assertNotIn("dpp", metrics["heldout"]["arms"]["plain"])


if __name__ == "__main__":
    unittest.main()
