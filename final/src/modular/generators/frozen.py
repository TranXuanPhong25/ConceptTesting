"""Rescore frozen inputs without invoking a generator, tokenizer or model."""
from __future__ import annotations

import hashlib
from pathlib import Path

from final.src.runtime.artifacts import digest
from ..artifacts import ArtifactStore
from .base import InputGenerator


class FrozenInputsGenerator(InputGenerator):
    def __init__(self, source_directory, *, methods=()):
        self.source = ArtifactStore(Path(source_directory), read_only=True)
        self.manifest = self.source.read("modular_manifest.json")
        self.freeze = self.source.read("generation_frozen.json")
        self.methods = tuple(methods)
        if self.freeze["cohort_sha256"] != self.manifest["cohort_sha256"]:
            raise ValueError("Frozen inputs and source manifest belong to different cohorts")
        if self.freeze["inputs_sha256"] != digest(self.freeze["inputs"]):
            raise ValueError("Frozen input ledger checksum mismatch")
        if set(self.freeze["inputs"]) != set(self.manifest["tasks"]):
            raise ValueError("Frozen input task set mismatch")
        if [method.name for method in self.methods] != [method["name"] for method in self.manifest["arms"]]:
            raise ValueError("Rescore methods must match the original input batches")
        self.identity = {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                         for path in self.source_dependencies()}

    def configuration(self):
        return {"source_run": str(self.source.directory), "mode": "frozen-inputs-no-model",
                "generation_sha256": self.freeze["inputs_sha256"], "source_files": self.identity}

    def source_dependencies(self):
        paths = [self.source.path("modular_manifest.json"), self.source.path("generation_frozen.json")]
        for task_id in self.manifest["tasks"]:
            paths.append(self.source.path(f"tasks/{task_id.split('/')[-1]}/inputs.json"))
        return tuple(paths)

    def generate(self, context):
        task_id = context.task["task_id"]
        inputs = self.source.read(context.task_directory + "/inputs.json")
        # VALIDATION START: rescore consumes the exact previously frozen input batch.
        if task_id not in self.freeze["inputs"] or digest(inputs) != self.freeze["inputs"][task_id]:
            raise ValueError("Saved inputs changed after the original generation freeze")
        if context.settings.input_budget != self.manifest["settings"]["input_budget"]:
            raise ValueError("Rescore input budget differs from source generation")
        # VALIDATION END: rescore consumes the exact previously frozen input batch.
        return inputs

    def dependency_objects(self):
        return self.methods

    def extend_summary(self, contexts, summary, reporting):
        for method in self.methods:
            method.extend_summary(contexts, summary, reporting)
        summary["reused_generation"] = {
            "source_run": str(self.source.directory), "new_model_calls": 0,
            "source_model": self.manifest["model"],
            "source_generation_sha256": self.freeze["inputs_sha256"],
        }

    def render_summary(self, summary):
        text = "\nInputs reused unchanged from a previously frozen run; no new model calls.\n"
        for method in self.methods:
            text += method.render_summary(summary)
        return text
