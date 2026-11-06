"""Resumable type → templates → LLM selection → LLM inputs workflow, per PUT."""
from __future__ import annotations

import hashlib
import fcntl
import math
import re
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path

from final.src.modular.artifacts import ArtifactStore
from final.src.modular.calls import CachedModelCalls
from final.src.modular.context import ModelCalls
from final.src.runtime.artifacts import digest
from .types import InputTypeExtraction
from .templates import BoundaryTemplates
from .stages import BoundarySelection, BoundaryInputGeneration
from .binding import BoundaryGuidance
from .construction import TargetCompiler


@dataclass(frozen=True)
class BoundarySettings:
    boundary_budget: int = 4
    input_budget: int = 20
    base_example_limit: int = 12
    selection_tokens: int = 4096
    input_tokens: int = 2048
    selection_temperature: float = 0.0
    input_temperature: float = 0.7
    context_tokens: int = 8192
    seed: int = 314159
    construction_mode: str = "compiled"

    def __post_init__(self):
        # VALIDATION START: configured budgets, seed and temperatures.
        for name in ("boundary_budget", "input_budget", "base_example_limit", "selection_tokens", "input_tokens", "context_tokens"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(f"{name} must be a positive integer")
        if max(self.selection_tokens, self.input_tokens) + 128 >= self.context_tokens:
            raise ValueError("Completion budget leaves no prompt context")
        if type(self.seed) is not int or self.seed < 0:
            raise ValueError("seed must be a nonnegative integer")
        for name in ("selection_temperature", "input_temperature"):
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 2:
                raise ValueError(f"{name} must be between zero and two")
        if self.construction_mode not in ("compiled", "literal"):
            raise ValueError("Unknown boundary construction mode")
        # VALIDATION END: configured budgets, seed and temperatures.


@dataclass
class BoundaryContext:
    task_number: int
    program_id: str
    entry_point: str
    specification: str
    contract: str
    program_source: str
    base_inputs: list[dict]
    settings: BoundarySettings
    artifacts: ArtifactStore | None
    calls: ModelCalls | None
    input_types: dict = field(default_factory=dict)
    templates: dict = field(default_factory=dict)
    selection: dict = field(default_factory=dict)
    guidance: dict = field(default_factory=dict)
    construction: dict = field(default_factory=dict)

    @property
    def directory(self):
        return f"tasks/{self.task_number}/boundary/{self.program_id}"

    def query(self, phase, messages, max_tokens, temperature):
        if self.calls is None:
            raise RuntimeError("Boundary LLM stage requires model calls; extraction alone needs none")
        token_count = self.calls.token_count(messages)
        request = {"messages": messages, "temperature": temperature, "max_tokens": max_tokens,
                   "seed": self.settings.seed + self.task_number, "prompt_tokens": token_count}
        self.artifacts.write(f"{self.directory}/{phase}_prompt.json", request)
        # VALIDATION START: request fits the model context budget.
        if token_count + max_tokens + 128 > self.settings.context_tokens:
            return None
        # VALIDATION END: request fits the model context budget.
        # Transport/cache errors propagate; they must not be converted to no_boundary.
        return self.calls.complete(self.task_number, f"bva_{self.program_id}_{phase}", messages,
                                   temperature=temperature, max_tokens=max_tokens,
                                   seed=self.settings.seed + self.task_number)


class BoundaryValueAnalysis:
    """Works with existing ModelCalls/ArtifactStore; never runs a PUT or an oracle."""

    def __init__(self, settings: BoundarySettings | None = None):
        self.settings = settings or BoundarySettings()

    def extract(self, *, specification: str, entry_point: str, program_source: str,
                base_inputs: list[dict], contract: str = "") -> dict:
        """Offline candidate inspection, without an artifact directory or LLM."""
        context = BoundaryContext(0, "inspection", entry_point, specification, contract,
                                  program_source, base_inputs, self.settings, None, None)
        context.input_types = InputTypeExtraction().run(context)
        context.templates = BoundaryTemplates().run(context)
        context.guidance = BoundaryGuidance().run(context)
        return {"input_types": context.input_types, "templates": context.templates, "guidance": context.guidance}

    def run(self, *, task_number: int, program_id: str | int, specification: str,
            entry_point: str, program_source: str, base_inputs: list[dict],
            artifacts: ArtifactStore, calls: ModelCalls | None = None, contract: str = "") -> dict:
        # VALIDATION START: public API arguments.
        if type(task_number) is not int or task_number < 0:
            raise ValueError("task_number must be a nonnegative integer")
        program_id = str(program_id)
        if not re.fullmatch(r"[A-Za-z0-9_]{1,64}", program_id):
            raise ValueError("program_id must be a simple identifier")
        if not all(isinstance(value, str) for value in (specification, entry_point, program_source, contract)):
            raise ValueError("Specification, source, entry and contract must be strings")
        if not isinstance(base_inputs, list) or any(not isinstance(record, dict) for record in base_inputs):
            raise ValueError("base_inputs must be a list of objects")
        # VALIDATION END: public API arguments.
        # Accept saved base calls, but never forward outcomes/traces or unrelated fields.
        base_inputs = [{name: record[name] for name in ("args", "kwargs", "bound") if name in record}
                       for record in base_inputs]
        # VALIDATION START: read-only mode cannot use a live model backend.
        if artifacts.read_only and calls is not None and not isinstance(calls, CachedModelCalls):
            raise ValueError("Read-only BVA accepts only cached calls or no calls")
        # VALIDATION END: read-only mode cannot use a live model backend.
        context = BoundaryContext(task_number, program_id, entry_point, specification, contract,
                                  program_source, base_inputs, self.settings, artifacts, calls)
        with self.run_lock(context):
            return self.run_stages(context)

    def run_for_program(self, task: dict, program: dict, *, artifacts: ArtifactStore,
                        calls: ModelCalls | None = None, contract: str = "") -> dict:
        """Adapter for saved final/ task + cohort records; no reference/plus access."""
        return self.run(task_number=int(task["task_id"].split("/")[-1]), program_id=program["id"],
                        specification=task["prompt"], entry_point=task["entry_point"],
                        program_source=program["code"], base_inputs=program.get("base", {}).get("calls", []),
                        artifacts=artifacts, calls=calls, contract=contract)

    def run_stages(self, context):
        artifacts = context.artifacts
        calls = context.calls
        identity_path = f"{context.directory}/identity.json"
        previous = artifacts.read(identity_path) if artifacts.exists(identity_path) else None
        model_id = calls.model_id if calls is not None else None
        if artifacts.read_only and previous is not None:
            model_id = previous["model"]
        identity = {
            "schema": "boundary-value-analysis-5", "task_number": context.task_number, "program_id": context.program_id,
            "input_sha256": digest({"specification": context.specification, "contract": context.contract,
                                    "entry_point": context.entry_point, "program_source": context.program_source,
                                    "base_inputs": context.base_inputs}),
            "settings": asdict(self.settings), "model": model_id, "sources": self.source_hashes(),
        }
        # VALIDATION START: immutable source, inputs, settings and model identity.
        artifacts.write(identity_path, identity)
        # VALIDATION END: immutable source, inputs, settings and model identity.
        context.input_types = artifacts.load_or_compute(
            f"{context.directory}/input_types.json", lambda: InputTypeExtraction().run(context))
        context.templates = artifacts.load_or_compute(
            f"{context.directory}/templates.json", lambda: BoundaryTemplates().run(context))
        if context.input_types["status"] != "extracted":
            return self.finish(context, context.input_types["status"])
        if not context.templates["candidates"]:
            return self.finish(context, "no_templates")
        context.guidance = artifacts.load_or_compute(
            f"{context.directory}/public_guards.json", lambda: BoundaryGuidance().run(context))
        context.selection = artifacts.load_or_compute(
            f"{context.directory}/selection.json", lambda: BoundarySelection().run(context))
        if context.selection["status"] != "selected":
            return self.finish(context, context.selection["status"])
        if self.settings.construction_mode == "compiled":
            context.construction = artifacts.load_or_compute(
                f"{context.directory}/compiled_targets.json", lambda: TargetCompiler().run(context))
            if context.construction["closed_scalar"]:
                inputs = context.construction["closed_inputs"]
                blocked = context.construction["blocked"]
                status = "generated" if inputs else "construction_unknown"
                if blocked and all(item["reason"] == "duplicate_input" for item in blocked):
                    status = "already_covered_inputs" if not inputs else "generated"
                generation = artifacts.load_or_compute(f"{context.directory}/generation.json", lambda: {
                    "status": status, "inputs": inputs, "rejected": blocked,
                    "reason": "Scalar targets constructed by code; no context LLM required.", "model_call_used": False})
                return self.finish(context, generation["status"], generation)
            if not context.construction["obligations"]:
                generation = artifacts.load_or_compute(f"{context.directory}/generation.json", lambda: {
                    "status": "construction_unknown", "inputs": [], "rejected": context.construction["blocked"],
                    "reason": "No representable target within the supported construction policy.", "model_call_used": False})
                return self.finish(context, generation["status"], generation)
        generation = artifacts.load_or_compute(
            f"{context.directory}/generation.json", lambda: BoundaryInputGeneration().run(context))
        return self.finish(context, generation["status"], generation)

    @staticmethod
    def finish(context, status, generation=None):
        reason = (generation or context.selection).get("reason", "")
        if not reason:
            reason = {"no_templates": "No supported boundary family from the available input type evidence.",
                      "unsupported_signature": "Expected one synchronous function with fixed arguments and literal defaults.",
                      "prompt_too_large": "The request does not fit the configured context budget."}.get(status, "")
        result = {
            "status": status, "skip": None if status == "generated" else status,
            "task_number": context.task_number, "program_id": context.program_id,
            "inputs": generation["inputs"] if generation else [],
            "rejected": generation["rejected"] if generation else context.selection.get("rejected", []),
            "boundaries": context.selection.get("boundaries", []),
            "reason": reason,
            "domain_validation": "pending_external_contract_or_reference_validation",
            "logical_calls": {"selection": context.artifacts.exists(f"{context.directory}/select_prompt.json")
                              and context.selection.get("status") != "prompt_too_large",
                              "generation": generation is not None and generation.get("model_call_used", True)
                              and generation["status"] != "prompt_too_large"},
        }
        context.artifacts.write(f"{context.directory}/result.json", result)
        return result

    @staticmethod
    def source_hashes():
        hashes = {}
        for path in sorted(Path(__file__).parent.glob("*.py")):
            hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        builder_path = Path(__file__).parent.parent / "call_builder.py"
        hashes["../call_builder.py"] = hashlib.sha256(builder_path.read_bytes()).hexdigest()
        return hashes

    @staticmethod
    @contextmanager
    def run_lock(context):
        lock_path = context.artifacts.path(f"{context.directory}/.run.lock")
        if context.artifacts.read_only:
            lock_file = lock_path.open("r")
            mode = fcntl.LOCK_SH
        else:
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            lock_file = lock_path.open("a+")
            mode = fcntl.LOCK_EX
        with lock_file:
            fcntl.flock(lock_file, mode | fcntl.LOCK_NB)
            yield
