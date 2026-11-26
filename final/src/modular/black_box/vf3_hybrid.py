"""Flat shared base class for EP/BVA and DT arms (VF3 Hybrid: strict Round 1 + free Round 2)."""
from __future__ import annotations

import ast
from dataclasses import replace
import json
import re

from pydantic import ValidationError

from ..call_builder import CallBuilder
from ..calls import structured_format
from .catalogue import bound_arguments, measure_catalogue, validate_catalogue
from .catalogue_response import read_catalogue_response
from ..input_prompts import render_input_prompt
from ..response_json import load_response_json
from ..tool_sampling.membership import evaluate
from ..tool_sampling.trusted_domain import compile_domain
from .vf3_hybrid_schema import canonical_catalogue, membership_errors, response_type
from ..arm_names import VF3_INPUTS_PER_ROUND, VF3_RETAINED_INPUT_BUDGET
from ..common import InputGenerationMethod
from ..catalogue_reporting import CatalogueReporter

EP_BVA_GUIDANCE = (
    "Use Equivalence Partitioning (EP) with normal Boundary Value Analysis (BVA). "
    "Start from specification behaviors and input dependencies.\n"
    "Partition by meaningful rules, result categories and jointly valid combinations, "
    "rather than numeric ranges alone. Use plausible specification-supported fault "
    "hypotheses to refine classes; split or merge when a different fault could be hidden.\n"
    "Choose typical representatives that satisfy their class, keeping unrelated values ordinary; "
    "then add useful class-edge min/min+, max-/max tests, varying one quantity at a time.\n"
    "Check membership and remove redundancy unless tests distinguish different plausible faults. "
    "Other useful tests are welcome. List classes and boundaries in the catalogue."
)

DECISION_TABLE_GUIDANCE = (
    "Use Decision Table Testing for behaviors determined by interacting conditions.\n"
    "Derive conditions and ordered actions from the specification; a condition may be "
    "an input predicate or relation, even when the function has only one parameter. "
    "Form combinations; distinguish feasible, infeasible and unresolved cases.\n"
    "Use plausible fault hypotheses to notice missing conditions, combinations or priorities.\n"
    "Vary interacting conditions across multiple feasible inputs per rule to expose subtle "
    "implementation bugs; use existing base calls as context and add NEW distinct contrasts.\n"
    "Check gaps, overlaps and representative membership; keep tests for distinct faults. "
    "Other useful tests are welcome. List the rules in the catalogue."
)

FAULT_HYPOTHESIS_OUTPUT_NOTE = (
    'Optional class/rule field "fault_hypothesis" is a short plausible implementation mistake '
    "supported by the specification; use it where it motivates a distinct class or rule. "
    'Use the existing "covers" labels to connect inputs. This is a hypothesis, not a confirmed bug.'
)

SOFT_EXAMPLES = {
    "ep_bva": (
        "One possible example is package-version filtering (packaging SpecifierSet.filter). With a final-only specifier such as >=2.0, "
        "prereleases=None keeps matching prereleases only when no matching final survives; prereleases=True or False changes that policy. "
        "A final outside the specifier must not suppress an otherwise matching prerelease. Useful ideas might compare candidate lists "
        "[2.1a1], [1.9,2.1a1] and [2.1a1,2.1], in either order, then consider explicit policy overrides. These classes depend on policy "
        "and the filtered candidate set, not separate numeric intervals alone. A plausible fault is checking for any final before applying "
        "the specifier. A prerelease/final transition can suggest extra boundary tests. This illustrates possible reasoning, not required "
        "class names or a complete suite; use other ideas when better."
    ),
    "decision_table": (
        "For example, HTTP response preconditions (Werkzeug Response.apply_conditions) combine method, validators and time. "
        "If-Match uses strong ETag comparison and, when present, takes precedence over If-Unmodified-Since. If-None-Match uses weak comparison; "
        "a match gives 304 for GET/HEAD but 412 for other methods. Its presence suppresses If-Modified-Since even when it does not match. "
        "Possible discriminating pairs use a matching strong If-Match with an otherwise failing date, a weakly matching If-None-Match under GET "
        "versus PUT, or a nonmatching If-None-Match with a date that alone would give 304. These can expose wrong precedence or merging rules "
        "across method-dependent actions. This is one source of test ideas, not a required table shape; only group conditions supported by the "
        "actual specification.\n\nTest a workshop receipt toggle when both settings have identical ordered actions under the spec. Hold the rest of the booking fixed."
    ),
}

COMMON_R1_INSTRUCTION = """Use the supplied lean JSON Schema; catalogue and inputs contain no expected outputs.
Set catalogue.status="applicable" whenever the technique applies (never use "not_applicable"/"unresolved" for test summaries).
Prioritize fault-revealing edge cases and contrasting inputs that exercise your catalogue. Generate distinct novel calls up to the requested input budget, avoiding base examples and including useful bug-hunting tests beyond the catalogue."""

EP_BVA_R1_INSTRUCTION = """Set status="applicable" with one shared catalogue.nominal, unique class IDs E1, E2.. and boundary IDs B1, B2.. (never reuse IDs across sections), and spec-derived boundaries.
Every class predicate MUST be pure executable Python boolean syntax ONLY over exact parameter names (NO English prose, NO undefined loop vars like i — use any/all generators and guard empty sequences/indices).
For boundaries: use transform="length" (upper=null when unbounded, never invent upper=30), numeric_kind="discrete" with explicit values for unbounded discrete points (never both lower=null and upper=null), and positive step for floats.
Include nominal and single-fault boundary inputs alongside broader fault-revealing edge cases."""

DT_R1_INSTRUCTION = """Model 2 to 4 independent specification conditions C1..Cn (1 only for truly single-predicate specs) as pure executable Python boolean syntax ONLY over exact parameter names (NO English prose, NO undefined vars — use any/all generators and guard empty sequences/indices).
Mark each truth-table row R.. (e.g. R01: C1=false, C2=true) feasible (at least one, optional short fault_hypothesis), infeasible, or unresolved.
Do not stop at one input per rule: generate diverse fault-revealing contrasts and tricky edge cases across feasible rules up to the requested input budget."""

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


def _frozen_value(value):
    if isinstance(value, dict):
        return ("dict", tuple(sorted(((_frozen_value(k), _frozen_value(v)) for k, v in value.items()), key=repr)))
    if isinstance(value, (list, tuple)):
        return (type(value).__name__, tuple(_frozen_value(item) for item in value))
    if isinstance(value, (set, frozenset)):
        return (type(value).__name__, tuple(sorted((_frozen_value(item) for item in value), key=repr)))
    return (type(value).__name__, repr(value))


def _record_key(builder, record):
    return repr(_frozen_value(dict(bound_arguments(builder, record))))


def _encode_json_value(value, depth=0):
    if depth > 12:
        raise ValueError("nesting_too_deep")
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("non_finite_float")
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


def _compact_existing_summary(catalogue, *, is_dt):
    if not isinstance(catalogue, dict):
        return {}
    if is_dt:
        return {
            "existing_conditions": dict(catalogue.get("condition_predicates") or {}),
            "feasible_rule_ids": [
                row["id"] for row in catalogue.get("original_rules", [])
                if isinstance(row, dict) and row.get("status") == "feasible"
            ],
        }
    return {
        "existing_classes": [
            {"id": row["id"], "predicate": row.get("predicate")}
            for row in catalogue.get("classes", []) if isinstance(row, dict) and "id" in row
        ],
        "existing_boundaries": [
            {k: row[k] for k in ("id", "parameter", "transform", "count_value", "numeric_kind", "lower", "upper", "values") if row.get(k) is not None}
            for row in catalogue.get("boundaries", []) if isinstance(row, dict) and "id" in row
        ],
    }


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
    example_key: str = ""
    round1_instruction: str = ""

    def configuration(self):
        return {
            "catalogue": True,
            "sections": list(self.sections),
            "protocol": "catalogue-vf3-hybrid",
            "retained_input_budget": VF3_RETAINED_INPUT_BUDGET,
            "dt_condition_cap": 4 if "rules" in self.sections else None,
        }

    def reporter(self):
        return CatalogueReporter()

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
        if self.example_key:
            text += (
                "\n" + FAULT_HYPOTHESIS_OUTPUT_NOTE
                + "\n\nSOFT EXAMPLE (another domain; adapt only useful ideas):\n"
                + SOFT_EXAMPLES[self.example_key]
            )
        return text + "\n\nVF3 HYBRID ROUND 1 OUTPUT CONTRACT:\n" + COMMON_R1_INSTRUCTION + "\n" + self.round1_instruction

    def build_prompt(self, packet):
        return render_input_prompt(packet, "catalogue")

    def decorate_input(self, accepted, input_record, record_index):
        covers = input_record.get("covers")
        if not isinstance(covers, list) or any(not isinstance(item, str) for item in covers):
            covers = None
        return {**accepted, "covers": covers, "source_index": record_index}

    def _decode_inputs(self, response, context):
        repairs = []
        try:
            raw, repairs = read_catalogue_response(response.text)
            if repairs:
                response = replace(response, text=repr(raw))
        except (ValueError, TypeError, RecursionError):
            pass
        result = super().decode_response(response, context)
        if repairs:
            result["response_repairs"] = repairs + result.get("response_repairs", [])
        return result

    def _novel_inputs(self, context, batch, previous=()):
        builder = CallBuilder.for_source(context.task["prompt"], context.task["entry_point"])
        base_keys = set(context.cohort_task["base_input_keys"])
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
        measured = measure_catalogue(
            batch,
            context.task,
            measured_indices,
            arm_name=self.name,
            input_budget=VF3_RETAINED_INPUT_BUDGET,
        )
        observed = measured.get("observed", {})
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
        schema_model = response_type(context.task, self.sections)
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
            result = self._decode_inputs(response, context)
            result.update(
                structured_output_errors=[str(error)[:2000]],
                catalogue=None, catalogue_status="catalogue_invalid", status="catalogue_invalid",
                catalogue_errors=["structured_output_invalid"], membership_errors=[], membership_ready=False,
            )
            return result

        payload = validated.model_dump(mode="json")
        result = self._decode_input_records(payload["inputs"], context, finish_reason=response.finish_reason)
        canonical = canonical_catalogue(payload["catalogue"], self.sections, task=context.task)
        catalogue, cat_errors = validate_catalogue(canonical, self.sections)
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
        decoded = self._decode_inputs(response, context)
        if decoded.get("rejected") or decoded.get("response_repairs") or len(decoded["inputs"]) < VF3_INPUTS_PER_ROUND:
            recovered = _extract_input_items(response.text)
            if recovered:
                recovered_decoded = self._decode_inputs(
                    replace(response, text=json.dumps({"inputs": recovered}, ensure_ascii=False, allow_nan=False)),
                    context,
                )
                if len(recovered_decoded.get("inputs", [])) > len(decoded.get("inputs", [])):
                    recovered_decoded["response_repairs"] = ["per_item_inputs_recovered"] + list(
                        recovered_decoded.get("response_repairs", [])
                    )
                    decoded = recovered_decoded

        reasoning = None
        for loader in (load_response_json, read_catalogue_response):
            try:
                raw, _ = loader(response.text)
                if isinstance(raw, dict) and "catalogue" in raw:
                    reasoning = raw.get("catalogue")
                    break
            except (ValueError, TypeError, RecursionError):
                continue
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
        context = replace(context, settings=replace(context.settings, input_budget=VF3_INPUTS_PER_ROUND))
        first = self._novel_inputs(
            context,
            self._run_round1(context, call_name=f"{self.name}_initial"),
        )

        directory = f"{context.task_directory}/{self.name}"
        round0_feedback = context.artifacts.load_or_compute(
            f"{directory}/round_0_feedback.json",
            lambda: self._feedback(context, first),
        )
        rounds = [
            {
                "call_name": f"{self.name}_initial",
                "input_budget": VF3_INPUTS_PER_ROUND,
                "feedback": round0_feedback,
            }
        ]
        inputs = list(first["inputs"])

        messages = self.build_messages(context.packet)
        messages.append({
            "role": "user",
            "content": json.dumps(
                {
                    "instruction": ROUND2_REASONING_INSTRUCTION,
                    **_compact_existing_summary(first.get("catalogue"), is_dt="rules" in self.sections),
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
                "round_2_catalogue_role": "reasoning_only",
                "round_2_new_inputs": len(second["inputs"]),
                "round_2_finish_reason": second.get("finish_reason"),
            }
            if merged_repairs:
                result["response_repairs"] = merged_repairs
            round1_feedback = context.artifacts.load_or_compute(
                f"{directory}/round_1_feedback.json",
                lambda: self._feedback(context, result),
            )
            rounds.append({
                "call_name": f"{self.name}_feedback",
                "input_budget": VF3_INPUTS_PER_ROUND,
                "feedback": round1_feedback,
            })
        else:
            result = {**first, "feedback_skip": "prompt_too_large"}

        return {
            **result,
            "inputs": inputs[:VF3_RETAINED_INPUT_BUDGET],
            "rounds": rounds,
            "status": result.get("status", "generated"),
        }


class EpBvaArm(StructuredCatalogueArm):
    name = "ep_bva_vf3_hybrid"
    sections = ("classes", "boundaries")
    guidance = EP_BVA_GUIDANCE
    example_key = "ep_bva"
    round1_instruction = EP_BVA_R1_INSTRUCTION


class DecisionTableArm(StructuredCatalogueArm):
    name = "decision_table_vf3_hybrid"
    sections = ("rules",)
    guidance = DECISION_TABLE_GUIDANCE
    example_key = "decision_table"
    round1_instruction = DT_R1_INSTRUCTION


EpBvaVf3HybridArm = EpBvaArm
DecisionTableVf3HybridArm = DecisionTableArm
VF3_HYBRID_ARMS = (EpBvaArm, DecisionTableArm)
