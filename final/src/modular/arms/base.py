"""One class per experiment type; shared mechanics, no name-based dispatch."""
from __future__ import annotations

import ast
import json
from abc import ABC, abstractmethod

from ..context import TaskContext, JsonObject
from ..call_builder import CallBuilder


class InputGenerationMethod(ABC):
    name: str
    uses_model: bool = True
    uses_shared_prompt: bool = True

    def preparation_stages(self):
        """Optional analysis stages; test-generation mechanics stay shared."""
        return ()

    def reporting_stage(self):
        """Optional reporting extension for an arm's extra preparation work."""
        return None

    def extend_summary(self, contexts, summary, reporting):
        """Optional arm-specific accounting after shared evaluation/reporting."""

    def render_summary(self, summary):
        """Optional report text; additional input-method accounting."""
        return ""

    def configuration(self) -> dict:
        if vars(self):
            raise NotImplementedError("Configured arms must expose their configuration for cache invalidation")
        return {}

    def build_messages(self, packet: JsonObject) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": "You generate valid Python function inputs to expose implementation bugs."},
            {"role": "user", "content": packet["common"] + "\n" + self.build_guidance(packet)},
        ]

    @abstractmethod
    def build_guidance(self, packet: JsonObject) -> str:
        """Only this method changes the guidance for a model-generated arm."""

    def run(self, context: TaskContext) -> JsonObject:
        if context.calls is None or context.packet is None:
            raise RuntimeError("A model arm requires prepared context and model calls")
        settings = context.settings
        response = context.calls.complete(
            context.task_number, self.name, self.build_messages(context.packet),
            temperature=settings.input_temperature, max_tokens=settings.input_tokens,
            seed=settings.input_seed + context.task_number,
        )
        rejected_records = []
        try:
            response_text = response.text.strip().removeprefix("```json").removesuffix("```").strip()
            input_records = json.loads(response_text)["inputs"]
            if not isinstance(input_records, list):
                raise ValueError("inputs must be a list")
        except (KeyError, TypeError, ValueError):
            input_records = []
            rejected_records.append({"reason": "invalid_response"})
        accepted_records = []
        for record_index, input_record in enumerate(input_records[:settings.input_budget]):
            try:
                # VALIDATION START: shared named-argument encoder, or validated Python literals.
                if isinstance(input_record, dict) and "arguments" in input_record:
                    builder = CallBuilder.for_source(context.task["prompt"], context.task["entry_point"])
                    accepted = builder.build(input_record["arguments"], guidance_id=input_record.get("guidance_id"))
                else:
                    accepted = self.parse_input(input_record)
                # VALIDATION END: shared named-argument encoder, or validated Python literals.
                accepted_records.append(accepted)
            except (ValueError, SyntaxError, TypeError, RecursionError) as error:
                reason = "invalid_literal"
                if isinstance(input_record, dict) and "arguments" in input_record and type(error) is ValueError:
                    reason = str(error)
                rejected_records.append({"index": record_index, "reason": reason})
        return {"inputs": accepted_records, "rejected": rejected_records, "finish_reason": response.finish_reason}

    @staticmethod
    def parse_input(input_record: JsonObject) -> JsonObject:
        if not isinstance(input_record, dict):
            raise ValueError("Input record must be an object")
        for field_name in ("args", "kwargs"):
            literal = input_record.get(field_name)
            if not isinstance(literal, str) or len(literal) > 16000:
                raise ValueError("Invalid or oversized literal")
        positional_arguments = ast.literal_eval(input_record["args"])
        keyword_arguments = ast.literal_eval(input_record["kwargs"])
        if not isinstance(positional_arguments, (list, tuple)) or not isinstance(keyword_arguments, dict):
            raise ValueError("Invalid args/kwargs")
        for keyword_name in keyword_arguments:
            if not isinstance(keyword_name, str):
                raise ValueError("Keyword names must be strings")
        return {"args": input_record["args"], "kwargs": input_record["kwargs"],
                "guidance_id": input_record.get("guidance_id")}
