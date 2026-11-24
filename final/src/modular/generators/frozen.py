"""Rescore saved inputs without invoking a generator, tokenizer or model."""
from __future__ import annotations

from pathlib import Path

from ..artifacts import ArtifactStore
from .base import InputGenerator


class FrozenInputsGenerator(InputGenerator):
    def __init__(self, source_directory, *, methods=()):
        self.source = ArtifactStore(Path(source_directory), read_only=True)
        self.manifest = self.source.read("modular_manifest.json")
        self.methods = tuple(methods)

    def configuration(self):
        return {"source_run": str(self.source.directory), "mode": "saved-inputs-no-model"}

    def generate(self, context):
        return self.source.read(context.task_directory + "/inputs.json")

    def extend_summary(self, contexts, summary, reporting):
        for method in self.methods:
            method.extend_summary(contexts, summary, reporting)
        summary["reused_generation"] = {
            "source_run": str(self.source.directory), "new_model_calls": 0,
            "source_model": self.manifest.get("model"),
        }
