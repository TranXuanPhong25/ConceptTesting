"""Adapt independent input-producing methods to one generator interface."""
from __future__ import annotations

from .base import InputGenerator
from ..input_preparation import load_or_prepare_packet


class MethodInputGenerator(InputGenerator):
    def __init__(
        self,
        methods,
        *,
        prepare_packet: bool = True,
    ):
        self.methods = tuple(methods)
        names = []
        for method in self.methods:
            if not method.name or not method.name.replace("_", "").isalnum() or method.name in names:
                raise ValueError("Input method names must be unique nonempty identifiers")
            names.append(method.name)
        if not names:
            raise ValueError("At least one input-producing method is required")
        self.prepare_packet = prepare_packet

    def configuration(self):
        return {
            "methods": [
                {
                    "name": method.name,
                    "class": type(method).__module__ + "." + type(method).__qualname__,
                    "configuration": method.configuration(),
                }
                for method in self.methods
            ]
        }

    def prepare_context(self, context):
        if self.prepare_packet:
            load_or_prepare_packet(context, self.methods)

    def generate(self, context):
        packet = context.packet or {}
        skip = packet.get("skip")
        if skip:
            return {"task_id": context.task["task_id"], "skip": skip}
        limit = context.settings.context_tokens - context.settings.input_tokens - 128
        token_counts = packet.get('prompt_tokens', {})
        batches = {}
        for method in self.methods:
            if token_counts.get(method.name, 0) > limit:
                batches[method.name] = {"inputs": [], "rejected": [], "status": "prompt_too_large"}
            else:
                batches[method.name] = method.run(context)
        return {
            "task_id": context.task["task_id"],
            "arms": batches,
        }

    def runtime_dependencies(self):
        return tuple(
            dict.fromkeys(
                package
                for method in self.methods
                for package in getattr(method, "runtime_dependencies", lambda: ())()
            )
        )

    def extend_summary(self, contexts, summary, reporter):
        for method in self.methods:
            extension = getattr(method, "extend_summary", None)
            if extension is not None:
                extension(contexts, summary, reporter)
