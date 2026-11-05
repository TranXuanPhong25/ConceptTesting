"""Shared per-input execution cache, isolated from generators and model prompts."""
from __future__ import annotations

import ast
import fcntl
import hashlib
import importlib.metadata
import inspect
import json
import math
import platform
import sqlite3
import sys
from pathlib import Path

from final.pipeline import digest
from .boundary_value_analysis.types import entry_function, input_signature


CACHE_POLICY = "isolated-input-execution-v1"
CACHEABLE_STATUSES = {"oracle": {"ok", "invalid_domain", "error"},
                      "evaluate": {"pass", "fail", "error"}}


def typed_value(value):
    """Preserve types, float bits and dict insertion order in input identities."""
    kind = type(value)
    if kind is dict:
        return ["dict", [[typed_value(key), typed_value(item)] for key, item in value.items()]]
    if kind in (tuple, list):
        return [kind.__name__, [typed_value(item) for item in value]]
    if kind is float:
        if not math.isfinite(value):
            raise ValueError("Nonfinite input is not reusable")
        return ["float", value.hex()]
    if kind in (str, bytes, bool, int, type(None), complex):
        return [kind.__name__, repr(value)]
    # Set iteration may depend on insertion history: use original syntax instead.
    raise ValueError("Input type requires syntax-preserving identity")


def input_identity(job, record):
    arguments = ast.literal_eval(record["args"])
    keywords = ast.literal_eval(record["kwargs"])
    try:
        signature = input_signature(entry_function(job["context"], job["entry"]))
        bound = signature.bind(*arguments, **keywords)
        bound.apply_defaults()
        values = [[name, typed_value(value)] for name, value in bound.arguments.items()]
        identity = {"bound": values}
    except (ValueError, TypeError, SyntaxError, RecursionError):
        identity = {"args_ast": ast.dump(ast.parse(record["args"], mode="eval")),
                    "kwargs_ast": ast.dump(ast.parse(record["kwargs"], mode="eval"))}
    if job["mode"] == "evaluate":
        # Expected outputs/tolerances affect verdicts even when PUT/input is unchanged.
        identity["expected"] = record["expected"]
    return identity


def runtime_identity():
    harness = Path(__file__).resolve().parents[1] / "experiments/concept_reference_v1"
    files = [Path(__file__), harness / "execution.py", harness / "worker.py", harness / "contracts.py"]
    return {
        "python": sys.version, "executable": str(Path(sys.executable).resolve()),
        "platform": platform.platform(),
        "signature_parser_sha256": hashlib.sha256(
            (inspect.getsource(entry_function) + inspect.getsource(input_signature)).encode()).hexdigest(),
        "packages": {name: importlib.metadata.version(name) for name in ("numpy", "scipy", "evalplus")},
        "sources": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in files},
    }


class InputExecutionCache:
    """Every missed (program, input, repeat) runs in a fresh sandbox."""

    def __init__(self, directory: Path, *, read_only=False):
        self.directory = Path(directory).resolve()
        self.read_only = read_only

    def configuration(self):
        return {"directory": str(self.directory), "policy": CACHE_POLICY,
                "repeats": "separate-cache-entries", "timeout_results": "not_reused"}

    def execute(self, job, *, repeat_index, executor):
        if self.read_only:
            raise FileNotFoundError("Read-only replay requires run execution artifacts; shared cache cannot execute")
        if job.get("mode") not in CACHEABLE_STATUSES or type(repeat_index) is not int or repeat_index not in (0, 1):
            raise ValueError("Input execution cache supports oracle/evaluate repeats 0 and 1")
        self.directory.mkdir(parents=True, exist_ok=True)
        locks = self.directory / "locks"
        locks.mkdir(exist_ok=True)
        database = sqlite3.connect(self.directory / "results.sqlite3", timeout=30)
        try:
            database.execute("CREATE TABLE IF NOT EXISTS results "
                             "(key TEXT PRIMARY KEY, payload TEXT NOT NULL, checksum TEXT NOT NULL)")
            database.commit()
            scope = {key: value for key, value in job.items() if key != "tests"}
            scope.update(policy=CACHE_POLICY, repeat_index=repeat_index, runtime=runtime_identity(),
                         executor={"module": executor.__module__, "name": executor.__qualname__,
                                   "source": hashlib.sha256(inspect.getsource(executor).encode()).hexdigest()})
            scope_key = digest(scope)
            counters = {"input_records": len(job["tests"]), "hits": 0, "misses": 0,
                        "executed_inputs": 0, "not_cached": 0, "corrupt_entries": 0}
            outcomes = []
            for record in job["tests"]:
                identity = input_identity(job, record)
                key = digest({"scope": scope_key, "input": identity})
                with (locks / (key + ".lock")).open("a+") as lock:
                    fcntl.flock(lock, fcntl.LOCK_EX)
                    outcome = self.read_result(database, key, job["mode"], counters)
                    if outcome is None:
                        counters["misses"] += 1
                        # One input per sandbox prevents a preceding input's side effects
                        # from changing a result later reused in another suite/order.
                        single_record = {name: record[name] for name in ("args", "kwargs", "expected") if name in record}
                        result = executor({**job, "tests": [single_record]})
                        outcome = self.validate_outcome(result)
                        counters["executed_inputs"] += 1
                        if outcome["status"] in CACHEABLE_STATUSES[job["mode"]]:
                            payload = json.dumps(outcome, sort_keys=True)
                            database.execute("INSERT OR REPLACE INTO results VALUES (?, ?, ?)",
                                             (key, payload, digest(outcome)))
                            database.commit()
                        else:
                            counters["not_cached"] += 1
                    else:
                        counters["hits"] += 1
                    outcomes.append(outcome)
            return {"tests": outcomes}, {"policy": CACHE_POLICY, "mode": job["mode"],
                                         "repeat_index": repeat_index, **counters}
        finally:
            database.close()

    @staticmethod
    def validate_outcome(result):
        # VALIDATION START: sandbox must return exactly one complete result.
        if not isinstance(result, dict) or not isinstance(result.get("tests"), list) or len(result["tests"]) != 1:
            raise ValueError("Sandbox result does not match the single input")
        outcome = result["tests"][0]
        if not isinstance(outcome, dict) or outcome.get("status") not in (
            "ok", "invalid_domain", "pass", "fail", "error", "timeout"
        ):
            raise ValueError("Sandbox returned an invalid input outcome")
        if outcome["status"] == "ok" and not all(isinstance(outcome.get(name), str) for name in ("input_key", "expected")):
            raise ValueError("Oracle outcome is missing its input key or expected output")
        # VALIDATION END: sandbox must return exactly one complete result.
        return outcome

    @classmethod
    def read_result(cls, database, key, mode, counters):
        row = database.execute("SELECT payload, checksum FROM results WHERE key = ?", (key,)).fetchone()
        if row is None:
            return None
        try:
            outcome = json.loads(row[0])
            cls.validate_outcome({"tests": [outcome]})
            if digest(outcome) != row[1] or outcome["status"] not in CACHEABLE_STATUSES[mode]:
                raise ValueError("Cache checksum or result status mismatch")
            return outcome
        except (ValueError, TypeError):
            counters["corrupt_entries"] += 1
            return None


def cached_execution(context, path, job, repeat_index, executor, cache):
    """Keep existing run checkpoints as the authoritative replay layer."""
    if cache is None:
        return context.artifacts.load_or_compute(path, lambda: executor(job) if job["tests"] else {"tests": []})
    receipt_path = path.removesuffix(".json") + "_cache.json"
    if context.artifacts.exists(path):
        outcome = context.artifacts.read(path)
        if context.artifacts.exists(receipt_path):
            receipt = context.artifacts.read(receipt_path)
        else:
            receipt = {"policy": CACHE_POLICY, "mode": job["mode"], "repeat_index": repeat_index,
                       "state": "receipt_missing"}
    else:
        if context.artifacts.read_only:
            raise FileNotFoundError(f"Read-only replay requires {path}")
        if job["tests"]:
            outcome, receipt = cache.execute(job, repeat_index=repeat_index, executor=executor)
        else:
            outcome = {"tests": []}
            receipt = {"policy": CACHE_POLICY, "mode": job["mode"], "repeat_index": repeat_index,
                       "input_records": 0, "hits": 0, "misses": 0, "executed_inputs": 0,
                       "not_cached": 0, "corrupt_entries": 0}
        context.artifacts.write(path, outcome)
        context.artifacts.write(receipt_path, receipt)
    receipts = context.extensions.setdefault("input_execution_cache", {})
    receipts[path] = receipt
    return outcome
