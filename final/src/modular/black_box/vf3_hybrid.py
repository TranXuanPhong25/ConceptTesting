"""Flat shared base class for EP/BVA and DT arms (VF3 Hybrid: strict Round 1 + free Round 2)."""
from __future__ import annotations

import ast
from abc import abstractmethod
import json
import re

from pydantic import ValidationError
from final.src.runtime.contracts import bound_call_key

from ..call_builder import CallBuilder
from ..calls import structured_format
from ..cohort import base_call_keys
from .catalogue import bound_arguments, observe_catalogue, validate_catalogue
from .catalogue_response import read_catalogue_response
from ..input_prompts import render_input_prompt
from ..response_json import load_response_json
from ..tool_sampling.membership import evaluate
from ..tool_sampling.trusted_domain import compile_domain
from .vf3_hybrid_schema import build_response_type, membership_errors
from ..arm_names import VF3_INPUTS_PER_ROUND
from ..common import InputGenerationMethod

FAULT_HYPOTHESIS_OUTPUT_NOTE = (
    'Optional class/rule field "fault_hypothesis" is a short plausible implementation mistake '
    "supported by the specification; use it where it motivates a distinct class or rule. "
    'Use the existing "covers" labels to connect inputs. This is a hypothesis, not a confirmed bug.'
)

COMMON_R1_INSTRUCTION = """Use the supplied lean JSON Schema; catalogue and inputs contain no expected outputs.
Set catalogue.status="applicable" whenever the technique applies (never use "not_applicable"/"unresolved" for test summaries).
Prioritize fault-revealing edge cases and contrasting inputs that exercise your catalogue. Generate distinct novel calls up to the requested input budget, avoiding base examples and including useful bug-hunting tests beyond the catalogue."""

ROUND2_REASONING_INSTRUCTION = (
    "ROUND 2 — FREE REASONING & BLIND-SPOT AUDIT (NO STRICT JSON SCHEMA).\n"
    "Return ONE valid plain JSON object (no markdown fences, no expected outputs, JSON literals only in arguments — no arithmetic like a + b): "
    '{"catalogue": {"gap_classes_or_rules": [...]}, "inputs": [{"arguments": {...}, "covers": [...]}]}.\n'
    "1. Cover any missed_targets or unknown_targets listed below.\n"
    "2. Critically audit existing_classes / existing_conditions against the specification and visible PUTs: "
    "what valid specification behaviors, domain subsets, or boundary interactions fall OUTSIDE those predicates "
    "or were modeled too narrowly (e.g., character/whitespace/encoding variants, numeric scale or precision limits, "
    "empty/singleton/duplicate/tie/order/sign edge cases, or multi-parameter interactions)?\n"
    "3. Use the free-form 'catalogue' object solely for concise gap reasoning and fault hypotheses "
    "(do NOT repeat Round 1's catalogue; strict predicate syntax is not required).\n"
    f"4. Generate up to {VF3_INPUTS_PER_ROUND} new distinct concrete inputs. Exclude base examples and retained_inputs."
)


def _record_key(builder, record):
    return bound_call_key(bound_arguments(builder, record))


def _encode_json_value(value, depth=0):
    if depth > 12:
        raise ValueError("nesting_too_deep")
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("inf_or_nan_float")
        return value
    if isinstance(value, list):
        return [_encode_json_value(item, depth + 1) for item in value]
    if isinstance(value, tuple):
        return {"__python_type__": "tuple", "items": [_encode_json_value(item, depth + 1) for item in value]}
    if isinstance(value, set):
        return {"__python_type__": "set", "items": [_encode_json_value(item, depth + 1) for item in sorted(value, key=repr)]}
    if isinstance(value, dict):
        if not all(isinstance(k, str) for k in value):
            raise ValueError("non_string_dict_key")
        return {k: _encode_json_value(v, depth + 1) for k, v in value.items()}
    raise ValueError(f"unsupported_literal_type:{type(value).__name__}")


def _extract_input_items(text):
    """Parse each {...} item inside the last "inputs":[...] array one by one."""
    if not isinstance(text, str) or len(text) > 200_000:
        return []
    matches = list(re.finditer(r'["\']inputs["\']\s*:\s*\[', text))
    if not matches:
        return []
    pos, length, items = matches[-1].end(), len(text), []
    decoder = json.JSONDecoder()
    while pos < length and len(items) < 128:
        while pos < length and text[pos] in " \t\r\n,":
            pos += 1
        if pos >= length or text[pos] == "]":
            break
        if text[pos] != "{":
            next_obj, next_end = text.find("{", pos), text.find("]", pos)
            if next_obj == -1 or (next_end != -1 and next_end < next_obj):
                break
            pos = next_obj
        try:
            parsed, pos = decoder.raw_decode(text, pos)
        except ValueError:
            depth, end = 0, None
            for i in range(pos, length):
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            if end is None:
                break
            try:
                parsed = ast.literal_eval(text[pos:end])
            except (ValueError, SyntaxError, TypeError, RecursionError):
                parsed = None
            pos = end
        if isinstance(parsed, dict) and ("arguments" in parsed or ("args" in parsed and "kwargs" in parsed)):
            try:
                encoded = _encode_json_value(parsed)
                json.dumps(encoded, allow_nan=False)
                items.append(encoded)
            except (TypeError, ValueError, OverflowError, RecursionError):
                pass
    return items


def _unhit_and_error_feedback(round0_feedback):
    missed, unknown = [], []
    for row in round0_feedback.get("targets", []):
        status = row.get("status")
        if status == "hit":
            continue
        item = {"kind": row["kind"], "id": row["id"], "status": status}
        if row["kind"] == "boundaries":
            item["missing_values"] = [t["value"] for t in row.get("targets", []) if t.get("status") != "hit"]
            if row.get("single_fault") == "pending":
                item["single_fault"] = "pending"
        if row.get("errors"):
            item["errors"] = row["errors"][:2]
        (missed if status == "miss" else unknown).append(item)
    payload = {
        "phase": "pre_freeze_no_oracle",
        "catalogue_status": round0_feedback.get("catalogue_status"),
        "membership_ready": round0_feedback.get("membership_ready", False),
        "missed_targets": missed,
        "unknown_targets": unknown,
        "metadata_errors": round0_feedback.get("metadata_errors", []),
        "invalid_input_count": sum(1 for r in round0_feedback.get("admission", []) if r.get("status") == "invalid"),
    }
    if round0_feedback.get("errored_condition_details"):
        payload["errored_conditions"] = round0_feedback["errored_condition_details"]
    return payload


class StructuredCatalogueArm(InputGenerationMethod):
    """Shared base class for black-box catalogue arms (EP, BVA, EP/BVA, DT).

    Round 1: lean strict JSON Schema and pre-freeze observed feedback.
    Round 2: free JSON blind-spot audit with the same budget for new distinct inputs.
    """

    sections: tuple[str, ...] = ()
    guidance: str = ""
    soft_example: str = ""
    round1_instruction: str = ""

    def configuration(self):
        return {
            "sections": list(self.sections),
            "protocol": "catalogue-vf3-hybrid",
        }

    def extend_summary(self, contexts, summary, reporting):
        accounting = {
            "classes": 0, "rules": 0, "annotated_classes": 0, "annotated_rules": 0,
            "status": "self_reported", "semantic_validation": "pending",
        }
        for context in contexts:
            catalogue = (context.inputs or {}).get("arms", {}).get(self.name, {}).get("catalogue") or {}
            for section in ("classes", "rules"):
                for obligation in catalogue.get(section, []):
                    accounting[section] += 1
                    accounting["annotated_" + section] += bool(obligation.get("fault_hypothesis"))
        summary.setdefault("fault_hypothesis_annotations", {})[self.name] = accounting

    def build_guidance(self, packet):
        text = self.guidance
        if self.soft_example:
            text += (
                "\n" + FAULT_HYPOTHESIS_OUTPUT_NOTE
                + "\n\nSOFT EXAMPLE (another domain; adapt only useful ideas):\n"
                + self.soft_example
            )
        return text + "\n\nVF3 HYBRID ROUND 1 OUTPUT CONTRACT:\n" + COMMON_R1_INSTRUCTION + "\n" + self.round1_instruction

    def build_prompt(self, packet):
        return render_input_prompt(packet, "catalogue")

    def response_type(self, task):
        return build_response_type(task, self.build_catalogue_type)

    @abstractmethod
    def build_catalogue_type(self, arguments_model, annotations, type_map):
        """Build the technique-specific catalogue in the strict response schema."""

    @abstractmethod
    def normalize_catalogue(self, value, *, task):
        """Convert a validated catalogue to the saved measurement format."""

    @abstractmethod
    def summarize_catalogue(self, catalogue):
        """Select the catalogue fields needed in the feedback prompt."""

    def decorate_input(self, accepted, input_record, record_index):
        covers = input_record.get("covers")
        if not isinstance(covers, list) or any(not isinstance(item, str) for item in covers):
            covers = None
        return {**accepted, "covers": covers, "source_index": record_index}

    def _decode_inputs(self, response, context):
        try:
            raw, repairs = read_catalogue_response(response.text)
            records = raw['inputs']
            if not isinstance(records, list):
                raise ValueError('inputs must be a list')
        except (ValueError, TypeError, KeyError, RecursionError):
            return {
                'inputs': [],
                'rejected': [{'reason': 'invalid_response'}],
                'finish_reason': response.finish_reason,
            }, None
        result = self._decode_input_records(
            records[:VF3_INPUTS_PER_ROUND],
            context,
            finish_reason=response.finish_reason,
        )
        if repairs:
            result['response_repairs'] = repairs
        return result, raw.get('catalogue')

    def _novel_inputs(self, context, batch, previous=()):
        builder = CallBuilder.for_source(context.task["prompt"], context.task["entry_point"])
        base_keys = base_call_keys(context.cohort_task, builder.signature)
        seen = {_record_key(builder, row) for row in previous}
        retained, rejected = [], list(batch.get("rejected", []))
        for index, row in enumerate(batch.get("inputs", [])):
            key = _record_key(builder, row)
            if key in base_keys:
                rejected.append({"index": row.get("source_index", index), "reason": "base_duplicate"})
            elif key in seen:
                rejected.append({"index": row.get("source_index", index), "reason": "duplicate"})
            else:
                retained.append(row)
                seen.add(key)
        return {**batch, "inputs": retained, "rejected": rejected}

    def _feedback(self, context, batch):
        builder = CallBuilder.for_source(context.task["prompt"], context.task["entry_point"])
        domain_rule = compile_domain(context.metadata.get("contract", ""), builder.signature.parameters)
        valid_indices, fallback_indices, admission = [], [], []
        for index, record in enumerate(batch["inputs"]):
            status, reason = "unknown", domain_rule["status"]
            if domain_rule["status"] == "supported":
                try:
                    ok = evaluate(domain_rule["expression"], dict(bound_arguments(builder, record)))
                    status, reason = ("valid", None) if ok else ("invalid", "trusted_domain_rejects")
                except (ValueError, TypeError, ArithmeticError, LookupError, SyntaxError) as error:
                    reason = f"{type(error).__name__}:{str(error)[:150]}"
            if status == "valid":
                valid_indices.append(index)
            if status != "invalid":
                fallback_indices.append(index)
            admission.append({"input_index": index, "status": status, "reason": reason})

        measured_indices = valid_indices if domain_rule["status"] == "supported" else fallback_indices
        observed = observe_catalogue(batch, context.task, measured_indices)
        targets = []
        for section in ("classes", "boundaries", "original_rules"):
            for row in observed.get(section, []):
                target = {
                    "kind": section, "id": row["id"], "status": row["status"],
                    "input_indices": row.get("source_input_indices", []),
                    "errors": row.get("errors", [])[:3],
                }
                if section == "boundaries":
                    target["targets"] = [{"value": t["value"], "status": t["status"]} for t in row["targets"]]
                    target["single_fault"] = row["single_fault"]
                targets.append(target)

        return {
            "phase": "pre_freeze_no_oracle",
            "admission": admission,
            "targets": targets,
            "errored_condition_details": {
                row["id"]: row["errors"][:2] for row in observed.get("conditions", []) if row.get("errors")
            },
            "metadata_errors": (
                batch.get("structured_output_errors", [])
                + batch.get("catalogue_errors", [])
                + batch.get("membership_errors", [])
            ),
            "catalogue_status": batch.get("catalogue_status"),
            "membership_ready": batch.get("membership_ready", False),
        }

    def _run_round1(self, context, *, call_name):
        settings = context.settings
        schema_model = self.response_type(context.task)
        response = context.calls.complete(
            context.task_number,
            call_name,
            self.build_messages(context.packet),
            temperature=settings.input_temperature,
            max_tokens=settings.input_tokens,
            seed=settings.input_seed + context.task_number,
            response_format=structured_format(schema_model.model_json_schema()),
        )
        try:
            raw, _ = load_response_json(response.text)
            validated = schema_model.model_validate(raw)
        except (ValidationError, ValueError, TypeError, RecursionError) as error:
            result, _ = self._decode_inputs(response, context)
            result.update(
                structured_output_errors=[str(error)[:2000]],
                catalogue=None, catalogue_status="catalogue_invalid", status="catalogue_invalid",
                catalogue_errors=["structured_output_invalid"], membership_errors=[], membership_ready=False,
            )
            return result

        payload = validated.model_dump(mode="json")
        result = self._decode_input_records(payload["inputs"], context, finish_reason=response.finish_reason)
        normalized = self.normalize_catalogue(payload["catalogue"], task=context.task)
        catalogue, cat_errors = validate_catalogue(normalized, self.sections)
        mem_errors = membership_errors(catalogue, context.task) if catalogue is not None else list(cat_errors)
        cat_status = "catalogue_invalid" if cat_errors else catalogue.status
        result.update(
            catalogue=catalogue.model_dump(mode="json") if catalogue is not None else None,
            catalogue_status=cat_status,
            status=cat_status,
            catalogue_errors=cat_errors,
            structured_output_errors=[],
            membership_errors=mem_errors,
            membership_ready=not mem_errors and cat_status != "catalogue_invalid",
        )
        return result

    def _run_round2(self, context, *, call_name, messages):
        settings = context.settings
        response = context.calls.complete(
            context.task_number,
            call_name,
            messages,
            temperature=settings.input_temperature,
            max_tokens=settings.input_tokens,
            seed=settings.input_seed + context.task_number,
            response_format=None,
        )
        decoded, reasoning = self._decode_inputs(response, context)
        if decoded['rejected'] or decoded.get('response_repairs'):
            recovered = _extract_input_items(response.text)
            if recovered:
                recovered_decoded = self._decode_input_records(
                    recovered[:VF3_INPUTS_PER_ROUND],
                    context,
                    finish_reason=response.finish_reason,
                )
                if len(recovered_decoded['inputs']) > len(decoded['inputs']):
                    recovered_decoded['response_repairs'] = ['per_item_inputs_recovered']
                    decoded = recovered_decoded

        if reasoning is not None:
            try:
                reasoning = json.loads(json.dumps(reasoning, allow_nan=False))
            except (TypeError, ValueError, OverflowError, RecursionError):
                reasoning = {"_non_json_repr": repr(reasoning)[:4000]}
        decoded["round_2_reasoning_catalogue"] = reasoning
        return decoded

    def run(self, context):
        return context.artifacts.load_or_compute(
            f"{context.task_directory}/{self.name}/generation.json",
            lambda: self.generate(context),
        )

    def generate(self, context):
        if context.calls is None or context.packet is None:
            raise RuntimeError("A structured catalogue arm requires prepared context and model calls")
        first = self._novel_inputs(
            context,
            self._run_round1(context, call_name=f"{self.name}_initial"),
        )

        directory = f"{context.task_directory}/{self.name}"
        round0_feedback = context.artifacts.load_or_compute(
            f"{directory}/round_0_feedback.json",
            lambda: self._feedback(context, first),
        )
        rounds = [{"call_name": f"{self.name}_initial"}]
        inputs = list(first["inputs"])

        messages = self.build_messages(context.packet)
        messages.append({
            "role": "user",
            "content": json.dumps(
                {
                    "instruction": ROUND2_REASONING_INSTRUCTION,
                    **self.summarize_catalogue(first.get("catalogue")),
                    "feedback": _unhit_and_error_feedback(round0_feedback),
                    "retained_inputs": [{k: row[k] for k in ("args", "kwargs")} for row in inputs],
                },
                ensure_ascii=False,
                separators=(",", ":"),
            ),
        })
        if context.calls.token_count(messages) + context.settings.input_tokens + 128 <= context.settings.context_tokens:
            second = self._novel_inputs(
                context,
                self._run_round2(
                    context,
                    call_name=f"{self.name}_feedback",
                    messages=messages,
                ),
                inputs,
            )
            inputs.extend(second["inputs"])
            merged_repairs = list(first.get("response_repairs", [])) + [
                f"r2:{item}" for item in second.get("response_repairs", [])
            ]
            result = {
                **first,
                "inputs": inputs,
                "rejected": first.get("rejected", []) + second.get("rejected", []),
                "round_2_reasoning_catalogue": second.get("round_2_reasoning_catalogue"),
            }
            if merged_repairs:
                result["response_repairs"] = merged_repairs
            context.artifacts.load_or_compute(
                f"{directory}/round_1_feedback.json",
                lambda: self._feedback(context, result),
            )
            rounds.append({"call_name": f"{self.name}_feedback"})
        else:
            result = {**first, "feedback_skip": "prompt_too_large"}

        return {
            **result,
            "inputs": inputs,
            "rounds": rounds,
            "status": result.get("status", "generated"),
        }
