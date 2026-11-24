"""Pinned evaluation-only reference programs, independent of input generation."""
from __future__ import annotations

import json
from pathlib import Path


DEFAULT_REFERENCES = Path(__file__).resolve().parents[2] / "data/humanevalplus_v0.1.10_references.json"


class TaskReferencePrograms:
    """Explicit task-provided references for controlled diagnostics and fixtures."""
    record_provenance = False

    def configuration(self):
        return {"source": "task_canonical_solution", "policy": "original-task-reference"}

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
        self.package = json.loads(content)
        # Expected export: humanevalplus-reference-programs-1, EvalPlus v0.1.10, with hidden_tests_retained=false

    def configuration(self):
        return {"source": "EvalPlus/HumanEval+", "version": self.package["version"],
                "path": str(self.path),
                "scope": "evaluation-only-no-hidden-inputs"}

    def for_task(self, task, metadata = None):
        record = self.package["tasks"][task["task_id"]]
        return {"context": record["prompt"], "source": record["prompt"] + record["canonical_solution"],
                "entry": record["entry_point"], "contract": record["contract"],
                "provenance": {**self.configuration(), "spec_compatibility": record["spec_compatibility"]}}
