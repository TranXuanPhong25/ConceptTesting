"""Scoped path/default rebinding. No original source files are changed."""
from __future__ import annotations

from contextlib import contextmanager, ExitStack
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch
import inspect
import json

from .dataset import DATA


@dataclass(frozen=True)
class Paths:
    root: Path = DATA

    @property
    def he(self): return self.root / "he/humaneval_mbpp.jsonl"
    @property
    def plus(self): return self.root / "he/humaneval_mbpp_plus.jsonl"
    @property
    def puts(self): return self.root / "he/PUTs"
    @property
    def selection(self): return self.root / "he/tasks.json"
    @property
    def precond(self): return self.root / "precond_qwen7b_v4"
    @property
    def strategy(self): return self.root / "strategy_qwen7b_v4c"
    @property
    def facts(self): return self.root / "facts_v6"
    @property
    def specfacts(self): return self.root / "spec_facts_v7"
    @property
    def all(self): return self.root / "tasks_v7_all.json"
    @property
    def hybrid(self): return self.root / "tasks_v7hyb_v4.json"
    @property
    def generation(self): return self.root / "gen2_qwen7b_v7hyb_v4"
    @property
    def oracle(self): return self.root / "oracle_v7hyb"

    def ids(self):
        manifest = json.loads((self.root / "he/manifest.json").read_text())
        if manifest["failing_checks"]:
            raise ValueError(f"dataset verification failed: {manifest['failing_checks']}")
        ids = [int(x) for x in (self.root / "he/tasks.txt").read_text().split()]
        if len(ids) != manifest["tasks_built"] or len(set(ids)) != len(ids):
            raise ValueError("dataset ids/manifest mismatch")
        return ids

    def safe(self, path):
        path = Path(path).resolve()
        he = self.root.resolve() / "he"
        if self.root.resolve() not in path.parents or path == he or he in path.parents:
            raise ValueError("pipeline outputs must be inside the heldout root, outside he/")
        return path


def task_sources(paths, ids):
    allowed = set(paths.ids())
    if not ids or len(set(ids)) != len(ids) or not set(ids) <= allowed:
        raise ValueError("expected distinct selected held-out tasks")
    he = {int(r["task_id"].split("/")[1]): r for r in map(json.loads, paths.he.read_text().splitlines())}
    tasks = [dict(task=n, entry=he[n]["entry_point"], base=he[n]["test"],
                  put=(paths.puts / f"HumanEval_{n}/put0.py").read_text(), split="heldout") for n in ids]
    return tasks, he, []


@contextmanager
def bound(paths=Paths()):
    """Restore all module globals, including definition-time defaults, on exit.

    Source-code roots intentionally stay original: tool/prompt hashes and worker
    dispatch must continue to identify and execute the unmodified dev code.
    Every data-dependent child receives explicit filenames or payloads.
    """
    from trickcatcher_linefacts import (generate, evaluate, oracle_b01, offline,
                                       gen_inputs, run_v4, run_v6, spec_facts)
    with ExitStack() as stack:
        def bind(module, name, value):
            stack.enter_context(patch.object(module, name, value))
        def defaults(function, **values):
            # Path constants also occur as definition-time defaults; merely
            # rebinding the module constant does not change those references.
            signature = inspect.signature(function)
            entries = [p for p in signature.parameters.values() if p.default is not inspect.Parameter.empty
                       and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
            replacement = tuple(values.get(p.name, p.default) for p in entries)
            stack.enter_context(patch.object(function, "__defaults__", replacement))
        defaults(generate.bundle, facts_dir=paths.facts)
        defaults(evaluate.evaluate, tasks_path=paths.generation / "tasks.json", gen_path=paths.generation / "gen.jsonl",
                 eval_path=paths.generation / "eval.jsonl")
        defaults(evaluate.report, tasks_path=paths.generation / "tasks.json", eval_path=paths.generation / "eval.jsonl")
        for name in ("load_run", "collect", "llm", "execute", "judges", "score"):
            defaults(getattr(oracle_b01, name), run=paths.generation, out=paths.oracle)
        for name, value in dict(HE=paths.he, PUTS=paths.puts, TASKS=paths.selection,
                                TASKS_V3=paths.all, FACTS=paths.facts).items():
            bind(generate, name, value)
        for module in (evaluate, oracle_b01, offline):
            bind(module, "HEP", paths.plus)
        bind(evaluate, "OUT", paths.generation)
        for name, value in dict(HE=paths.he, PUTS=paths.puts, OUT=paths.root / "offline_v7", DESIGN=set()).items():
            bind(offline, name, value)
        bind(offline, "excluded", lambda: set())
        bind(oracle_b01, "RUN", paths.generation)
        bind(oracle_b01, "OUT", paths.oracle)
        bind(oracle_b01, "variants", lambda *args: [])
        bind(oracle_b01, "ORACLES", ["ref", "full"])
        bind(spec_facts, "OUT", paths.specfacts)
        for name, value in dict(PRECOND=paths.precond, FACTS=paths.facts, SOURCE=paths.selection).items():
            bind(run_v6, name, value)
        bind(gen_inputs, "CONTRACTS", paths.plus)
        original_contracts = gen_inputs.load_contracts
        bind(gen_inputs, "load_contracts", lambda path=None: original_contracts(path or paths.plus))
        bind(run_v4, "task_sources", lambda ids: task_sources(paths, ids))
        bind(run_v4, "safe_path", paths.safe)
        yield
