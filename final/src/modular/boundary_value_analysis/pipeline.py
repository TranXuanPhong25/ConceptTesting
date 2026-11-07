"""Resumable single-completion soft BVA for one PUT; never executes a program."""
from __future__ import annotations

import fcntl
import hashlib
import math
import re
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path

from ..artifacts import ArtifactStore
from ..call_builder import CallBuilder
from ..calls import CachedModelCalls
from ..context import ModelCalls
from final.src.runtime.artifacts import digest
from .inputs import decode_inputs
from .prompts import generation_messages


@dataclass(frozen=True)
class BoundarySettings:
    input_budget: int = 20
    base_example_limit: int = 12
    input_tokens: int = 2048
    input_temperature: float = 0.7
    context_tokens: int = 8192
    seed: int = 314159

    def __post_init__(self):
        for name in ("input_budget", "base_example_limit", "input_tokens", "context_tokens"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(f"{name} must be a positive integer")
        if self.input_tokens + 128 >= self.context_tokens:
            raise ValueError("Completion budget leaves no prompt context")
        if type(self.seed) is not int or self.seed < 0:
            raise ValueError("seed must be a nonnegative integer")
        if (type(self.input_temperature) not in (int, float) or not math.isfinite(self.input_temperature)
                or not 0 <= self.input_temperature <= 2):
            raise ValueError("input_temperature must be between zero and two")


class BoundaryValueAnalysis:
    """Use soft guidance to generate literal inputs without a boundary-selection gate."""

    def __init__(self, settings: BoundarySettings | None = None):
        self.settings = settings or BoundarySettings()

    def run_for_program(self, task, program, *, artifacts, calls=None, contract=""):
        return self.run(task_number=int(task["task_id"].split("/")[-1]), program_id=program["id"],
                        specification=task["prompt"], entry_point=task["entry_point"],
                        program_source=program["code"], base_inputs=program.get("base", {}).get("calls", []),
                        artifacts=artifacts, calls=calls, contract=contract)

    def run(self, *, task_number: int, program_id: str | int, specification: str,
            entry_point: str, program_source: str, base_inputs: list[dict],
            artifacts: ArtifactStore, calls: ModelCalls | None = None, contract: str = ""):
        if type(task_number) is not int or task_number < 0:
            raise ValueError("task_number must be a nonnegative integer")
        program_id = str(program_id)
        if not re.fullmatch(r"[A-Za-z0-9_]{1,64}", program_id):
            raise ValueError("program_id must be a simple identifier")
        if not all(isinstance(value, str) for value in (specification, entry_point, program_source, contract)):
            raise ValueError("Specification, source, entry and contract must be strings")
        if not isinstance(base_inputs, list) or any(not isinstance(record, dict) for record in base_inputs):
            raise ValueError("base_inputs must be a list of objects")
        if artifacts.read_only and calls is not None and not isinstance(calls, CachedModelCalls):
            raise ValueError("Read-only BVA accepts only cached calls or no calls")
        settings = self.settings
        messages = generation_messages(task_id=f"HumanEval/{task_number}", specification=specification,
            contract=contract, program_source=program_source, base_inputs=base_inputs,
            input_budget=settings.input_budget, base_example_limit=settings.base_example_limit)
        directory = f"tasks/{task_number}/boundary/soft_bva/{program_id}"
        with self.run_lock(artifacts, directory):
            identity_path = directory + "/identity.json"
            previous = artifacts.read(identity_path) if artifacts.exists(identity_path) else None
            model_id = calls.model_id if calls is not None else None
            if artifacts.read_only and previous is not None:
                model_id = previous["model"]
            artifacts.write(identity_path, {
                "schema": "soft-bva-v1", "task_number": task_number, "program_id": program_id,
                "input_sha256": digest({"messages": messages, "entry_point": entry_point}),
                "settings": asdict(settings), "model": model_id, "sources": self.source_hashes(),
            })
            result = artifacts.load_or_compute(directory + "/result.json", lambda: self.generate(
                task_number, program_id, specification, entry_point, messages, directory, artifacts, calls))
            return result

    def generate(self, task_number, program_id, specification, entry_point, messages, directory, artifacts, calls):
        try:
            builder = CallBuilder.for_source(specification, entry_point)
        except (ValueError, SyntaxError, TypeError, RecursionError):
            return self.result("unsupported_signature", [], [], program_id, generation_call=False)
        if calls is None:
            raise RuntimeError("Soft BVA generation requires model calls")
        settings = self.settings
        prompt_tokens = calls.token_count(messages)
        artifacts.write(directory + "/inputs_prompt.json", {
            "messages": messages, "prompt_tokens": prompt_tokens, "temperature": settings.input_temperature,
            "max_tokens": settings.input_tokens, "seed": settings.seed + task_number,
        })
        if prompt_tokens + settings.input_tokens + 128 > settings.context_tokens:
            return self.result("prompt_too_large", [], [], program_id, generation_call=False)
        response = calls.complete(task_number, f"bva_{program_id}_soft_inputs", messages,
            temperature=settings.input_temperature, max_tokens=settings.input_tokens, seed=settings.seed + task_number)
        decoded = decode_inputs(response, builder, settings.input_budget)
        return {**self.result(decoded["status"], decoded["inputs"], decoded["rejected"], program_id,
                              generation_call=True), "finish_reason": response.finish_reason}

    @staticmethod
    def result(status, inputs, rejected, program_id, *, generation_call):
        return {"status": status, "skip": None if inputs else status, "program_id": program_id,
                "inputs": inputs, "rejected": rejected, "logical_calls": {"generation": generation_call},
                "domain_validation": "pending_shared_reference_oracle"}

    @staticmethod
    def source_hashes():
        paths = list(Path(__file__).parent.glob("*.py")) + [Path(__file__).parents[1] / "call_builder.py"]
        return {str(path.resolve()): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(paths)}

    @staticmethod
    @contextmanager
    def run_lock(artifacts, directory):
        path = artifacts.path(directory + "/.run.lock")
        if not artifacts.read_only:
            path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("r" if artifacts.read_only else "a+") as lock:
            mode = fcntl.LOCK_SH if artifacts.read_only else fcntl.LOCK_EX
            fcntl.flock(lock, mode | fcntl.LOCK_NB)
            yield
