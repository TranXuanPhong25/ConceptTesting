"""Pinned evaluation-only reference programs, independent of input generation."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


DEFAULT_REFERENCES = Path(__file__).resolve().parents[2] / "data/humanevalplus_v0.1.10_references.json"


class TaskReferencePrograms:
    """Explicit task-provided references for controlled diagnostics and fixtures."""
    record_provenance = False

    def configuration(self):
        return {"source": "task_canonical_solution", "policy": "original-task-reference"}

    def source_dependencies(self):
        return ()

    def for_task(self, task, metadata):
        return {"context": task["prompt"], "source": task["prompt"] + task["canonical_solution"],
                "entry": task["entry_point"], "contract": metadata["contract"],
                "provenance": self.configuration()}


class HumanEvalPlusReferencePrograms:
    """Only curated references/contracts: no plus inputs, test cases or model calls."""
    record_provenance = True

    def __init__(self, path=DEFAULT_REFERENCES):
        self.path = Path(path).resolve()
        content = self.path.read_bytes()
        self.sha256 = hashlib.sha256(content).hexdigest()
        self.package = json.loads(content)
        if self.package.get("schema") != "humanevalplus-reference-programs-1":
            raise ValueError("Unknown reference-program schema")
        if self.package.get("version") != "v0.1.10" or self.package.get("hidden_tests_retained") is not False:
            raise ValueError("Expected pinned reference-only HumanEval+ v0.1.10")
        expected = {f"HumanEval/{number}" for number in range(164)}
        if set(self.package["tasks"]) != expected:
            raise ValueError("Expected all164reference programs")
        allowed = {"entry_point", "original_prompt_sha256", "prompt", "canonical_solution",
                   "contract", "atol", "spec_compatibility"}
        for record in self.package["tasks"].values():
            if set(record) != allowed:
                raise ValueError("Reference export has unexpected fields")

    def configuration(self):
        return {"source": "EvalPlus/HumanEval+", "version": self.package["version"],
                "path": str(self.path), "sha256": self.sha256,
                "upstream_dataset_sha256": self.package["upstream_dataset_sha256"],
                "scope": "evaluation-only-no-hidden-inputs"}

    def source_dependencies(self):
        return (self.path,)

    def for_task(self, task, metadata):
        # VALIDATION START: reference source, spec binding and domain version match.
        if hashlib.sha256(self.path.read_bytes()).hexdigest() != self.sha256:
            raise ValueError("Reference programs changed during execution")
        record = self.package["tasks"][task["task_id"]]
        if (hashlib.sha256(task["prompt"].encode()).hexdigest() != record["original_prompt_sha256"]
                or task["entry_point"] != record["entry_point"]):
            raise ValueError("Reference program belongs to another task specification")
        if metadata["contract"] != record["contract"] or metadata["atol"] != record["atol"]:
            raise ValueError("Reference and contract/tolerance must use the same pinned dataset version")
        # VALIDATION END: reference source, spec binding and domain version match.
        return {"context": record["prompt"], "source": record["prompt"] + record["canonical_solution"],
                "entry": record["entry_point"], "contract": record["contract"],
                "provenance": {**self.configuration(), "spec_compatibility": record["spec_compatibility"],
                               "reference_sha256": hashlib.sha256(
                                   (record["prompt"] + record["canonical_solution"]).encode()).hexdigest()}}
