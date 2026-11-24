"""Adapt independent input-producing methods to one generator interface."""
from __future__ import annotations

from collections import Counter

from .base import InputGenerator
from ..catalogue import measure_task_catalogues
from ..input_preparation import load_or_prepare_packet


class MethodInputGenerator(InputGenerator):
    def __init__(
        self,
        methods,
        *,
        prepare_packet: bool = True,
        empty_context_on_overflow: bool = False,
        alternate_order: bool = False,
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
        self.empty_context_on_overflow = empty_context_on_overflow
        self.alternate_order = alternate_order

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
            load_or_prepare_packet(
                context,
                self.methods,
                empty_context_on_overflow=self.empty_context_on_overflow,
            )

    def generate(self, context):
        packet = context.packet or {}
        skip = packet.get("skip")
        if skip and (
            skip != "prompt_too_large"
            or all(getattr(method, "uses_shared_prompt", False) for method in self.methods)
        ):
            return {"task_id": context.task["task_id"], "skip": skip}
        shared_prompt_too_large = skip == "prompt_too_large" or packet.get("empty_context")
        order = tuple(reversed(self.methods)) if self.alternate_order and context.task_number % 2 == 1 else self.methods
        batches = {}
        for method in order:
            if shared_prompt_too_large and getattr(method, "uses_shared_prompt", False):
                batches[method.name] = {"inputs": [], "rejected": [], "status": "prompt_too_large"}
            else:
                batches[method.name] = method.run(context)
        return {
            "task_id": context.task["task_id"],
            "arms": {method.name: batches[method.name] for method in self.methods},
        }

    def post_reference(self, context):
        catalogue_arms = tuple(
            method.name for method in self.methods if getattr(method, "measures_catalogue", False)
        )
        if catalogue_arms:
            measure_task_catalogues(context, catalogue_arms)

    def runtime_dependencies(self):
        return tuple(
            dict.fromkeys(
                package
                for method in self.methods
                for package in getattr(method, "runtime_dependencies", lambda: ())()
            )
        )

    def reporter(self):
        selected = None
        for method in self.methods:
            factory = getattr(method, "reporter", None)
            instance = factory() if factory is not None else None
            if instance is not None:
                if selected is not None and (
                    type(instance) is not type(selected)
                    or getattr(instance, "configuration", dict)() != getattr(selected, "configuration", dict)()
                ):
                    raise ValueError("Conflicting method reporting extensions")
                selected = instance
        return selected

    def extend_summary(self, contexts, summary, reporter):
        for method in self.methods:
            extension = getattr(method, "extend_summary", None)
            if extension is not None:
                extension(contexts, summary, reporter)
            batches = [c.inputs["arms"][method.name] for c in contexts if not c.inputs.get("skip")]
            if getattr(method, "requires_treatment", False) or any("treatment" in b for b in batches):
                states = Counter(b.get("treatment", {}).get("status", "pending") for b in batches)
                summary.setdefault("method_treatments", {})[method.name] = {
                    "tasks": len(batches),
                    "states": dict(states),
                    "ready_for_efficacy": (
                        states["applied"] > 0 and not any(states[s] for s in ("failed", "unknown", "pending"))
                    ),
                }
