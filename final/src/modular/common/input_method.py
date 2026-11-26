"""One class per experiment type; shared mechanics, no name-based dispatch."""
from __future__ import annotations

import ast
from abc import ABC, abstractmethod

from ..context import TaskContext, JsonObject
from ..call_builder import CallBuilder
from ..input_prompts import render_input_prompt
from ..response_json import load_response_json


class InputGenerationMethod(ABC):
    name: str
    uses_model: bool = True
    uses_shared_prompt: bool = True

    def extend_summary(self, contexts, summary, reporting):
        """Optional arm-specific accounting after shared evaluation/reporting."""

    def configuration(self) -> dict:
        return {}

    def build_messages(self, packet: JsonObject) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": "You generate valid Python function inputs to expose implementation bugs."},
            {"role": "user", "content": self.build_prompt(packet) + "\n" + self.build_guidance(packet)},
        ]

    def build_prompt(self, packet: JsonObject) -> str:
        return render_input_prompt(packet)

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
        return self.decode_response(response, context)

    def decorate_input(self, accepted, input_record, record_index):
        return accepted

    def decode_response(self, response, context):
        response_repairs = []
        try:
            decoded_response, response_repairs = load_response_json(response.text)
            input_records = decoded_response["inputs"]
            # Validate the response envelope before iterating individual calls.
            if not isinstance(input_records, list):
                raise ValueError("inputs must be a list")
        except (KeyError, TypeError, ValueError):
            result = {"inputs": [], "rejected": [{"reason": "invalid_response"}],
                      "finish_reason": response.finish_reason}
        else:
            result = self._decode_input_records(
                input_records[:context.settings.input_budget],
                context,
                finish_reason=response.finish_reason,
            )
        if response_repairs:
            result["response_repairs"] = response_repairs
        return result

    def _decode_input_records(self, input_records, context, *, finish_reason):
        rejected_records = []
        accepted_records = []
        builder = CallBuilder.for_source(context.task['prompt'], context.task['entry_point'])
        for record_index, input_record in enumerate(input_records):
            try:
                # VALIDATION START: shared named-argument encoder, or validated Python literals.
                if isinstance(input_record, dict) and "arguments" in input_record:
                    accepted = builder.build(input_record["arguments"], guidance_id=input_record.get("guidance_id"))
                else:
                    accepted = self.parse_input(input_record)
                # VALIDATION END: shared named-argument encoder, or validated Python literals.
                accepted_records.append(self.decorate_input(accepted, input_record, record_index))
            except (ValueError, SyntaxError, TypeError, RecursionError) as error:
                reason = "invalid_literal"
                if isinstance(input_record, dict) and "arguments" in input_record and type(error) is ValueError:
                    reason = str(error)
                rejected_records.append({"index": record_index, "reason": reason})
        return {"inputs": accepted_records, "rejected": rejected_records, "finish_reason": finish_reason}

    @staticmethod
    def validate_input_literal_fields(input_record: JsonObject) -> None:
        """Only bounded args/kwargs strings may reach the Python literal parser."""
        if not isinstance(input_record, dict):
            raise ValueError("Input record must be an object")
        for field_name in ("args", "kwargs"):
            literal = input_record.get(field_name)
            if not isinstance(literal, str) or len(literal) > 16000:
                raise ValueError("Invalid or oversized literal")

    @staticmethod
    def validate_parsed_call_arguments(positional_arguments, keyword_arguments) -> None:
        """A call needs a positional sequence and keyword mapping with string keys."""
        if not isinstance(positional_arguments, (list, tuple)) or not isinstance(keyword_arguments, dict):
            raise ValueError("Invalid args/kwargs")
        for keyword_name in keyword_arguments:
            if not isinstance(keyword_name, str):
                raise ValueError("Keyword names must be strings")

    @staticmethod
    def parse_input(input_record: JsonObject) -> JsonObject:
        InputGenerationMethod.validate_input_literal_fields(input_record)
        positional_arguments = ast.literal_eval(input_record["args"])
        keyword_arguments = ast.literal_eval(input_record["kwargs"])
        InputGenerationMethod.validate_parsed_call_arguments(positional_arguments, keyword_arguments)
        return {"args": input_record["args"], "kwargs": input_record["kwargs"],
                "guidance_id": input_record.get("guidance_id")}
