"""VF3 measured arms: V2 fault guidance + strict VF3 schema + 20+10 observed feedback."""
from __future__ import annotations

from dataclasses import replace
import json

from pydantic import ValidationError

from ..call_builder import CallBuilder
from ..calls import structured_format
from ..catalogue import Catalogue, bound_arguments, measure_catalogue
from ..input_buckets.predicates import declared_types
from ..response_json import load_response_json
from ..tool_sampling.membership import evaluate
from ..tool_sampling.schema import validate_expression
from ..tool_sampling.trusted_domain import compile_domain
from ..vf3_measured_schema import canonical_response, membership_errors, response_type
from .fault_oriented import DecisionTableV2Arm, EpBvaV2Arm

COMMON_VF3_MEASURED_INSTRUCTION = """Use the supplied JSON Schema; catalogue and inputs contain no expected outputs.
catalogue.status must be "applicable" with nonempty catalogue sections whenever the technique applies.
NEVER choose status="not_applicable" or "unresolved" to write a summary of your test plan in reason.
Use "not_applicable" or "unresolved" ONLY if no catalogue can be built for the specification at all, and explain why in reason.
Aim to use the full input budget (up to 20 distinct novel inputs in round 0, not duplicating base examples): first cover every equivalence class, boundary target, or feasible rule, then use remaining slots for fault-revealing edge cases, contrasts, and multi-condition interactions.
There is at most one metadata/coverage feedback round with up to 10 new inputs; keep already-hit target IDs/definitions (unless a predicate threw a runtime error), repair unknown or missed metadata, and retain previous inputs within the total budget."""

EP_BVA_VF3_MEASURED_INSTRUCTION = """Every function with input parameters supports EP+BVA, so set status="applicable" with nonempty classes and boundaries.
Give each class a unique ID (E1, E2, ...) and each boundary a unique ID (B1, B2, ...) with no ID reused across sections.
Class predicate is required and must be one executable Python boolean expression over the EXACT function parameter names (never prose such as "exists", never undefined intermediate variables, never __import__, and never walrus :=).
Use any(...)/all(...) generator expressions (or nested comprehensions) for quantified checks, guard empty sequences/indices (e.g. `len(s) > 0 and s[0] == 'a'`), and ensure the expression always returns bool.
For BVA boundaries: use transform="length" or "count" for list/string lengths (never transform="identity" with numeric endpoints on a list or str). ONLY use transform="count" when counting a specific literal element/substring and ALWAYS set non-null count_value (a str for str parameters; NEVER leave count_value=null with transform="count"). Use parsed_int/parsed_float ONLY for strings representing a single number.
Boundary context fixes ONLY OTHER parameters (never include the tested parameter in context; use {} when none are fixed).
Numeric lower/upper endpoints must come from the specification, not schema caps: for unbounded list/string lengths, set lower=0 (or 1 if nonempty) and upper=null (NEVER invent upper=30). Never set numeric_kind="integer"/"float" with BOTH lower=null AND upper=null; for unbounded integers, use numeric_kind="discrete" with critical values (e.g. [-1, 0, 1]) or bound a spec class edge (e.g. lower=0, upper=null).
For numeric_kind="float", supply a realistic positive step (e.g. 0.1, 0.01, or 1e-6).
nominal is REQUIRED complete named arguments satisfying boundary.context; include the nominal input and single-fault boundary inputs (varying ONLY the tested parameter from nominal) in inputs."""

DT_VF3_MEASURED_INSTRUCTION = """DT schema records one original Boolean table: prefer 2 to 4 independent specification conditions named C1..Cn (C1..C4) whenever multiple branches, edge properties, or input interactions exist (use 1 condition only for truly single-predicate specs).
condition_predicates maps each condition ID to one executable Python boolean expression over the EXACT function parameter names (use any/all generators or nested comprehensions; guard empty sequences/indices so predicates never raise IndexError/ZeroDivisionError; no prose, no __import__, no walrus :=, and no undefined variables).
catalogue.rules keys encode exact condition bits: R01 means C1=false, C2=true; include every Boolean combination of C1..Cn as required by the schema.
Fill each row's status (feasible/infeasible/unresolved), actions (nonempty for feasible), reason (required for infeasible/unresolved), and optional fault_hypothesis; code derives the original_rules and feasible rules views.
At least one row in an applicable table must have status="feasible"; if no combination is feasible, set catalogue.status="not_applicable" with a reason.
Do NOT stop at one input per rule: generate multiple distinct fault-revealing contrasts per feasible rule to use up to the full input budget."""

FEEDBACK_PREDICATE_RULES = (
    "Use executable Python boolean expressions over exact function parameter names only. "
    "No prose such as exists/such that, no __import__, no walrus :=, and no undefined intermediate variables. "
    "Express quantified checks using any/all with generator expressions and guard empty lists/strings/indices against IndexError/ZeroDivisionError. "
    "Ensure predicates evaluate strictly to bool (not str/list via short-circuit). "
    "For BVA boundaries, never put the tested parameter in context, use transform='length' for lengths or transform='count' ONLY with a non-null count_value, "
    "never invent upper=30 for unbounded lengths, never leave both lower and upper null for integer/float, supply a positive step for float, "
    "and provide complete nominal arguments matching context. "
    "For DT, keep the SAME number of conditions C1..Cn when any rule already hit, keep >=1 row feasible, and put expressions only in condition_predicates."
)

LOCKED_KEYS_BY_SECTION = {
    "classes": ("predicate",),
    "boundaries": (
        "parameter", "transform", "count_value", "numeric_kind",
        "lower", "upper", "step", "context",
    ),
    "rules": ("conditions",),
    "original_rules": ("conditions", "status"),
}


def _frozen_base_value(value):
    """Match sandbox worker.input_key serialization used in frozen cohort base_input_keys."""
    if isinstance(value, dict):
        items = tuple(sorted(((_frozen_base_value(k), _frozen_base_value(v)) for k, v in value.items()), key=repr))
        return ("dict", items)
    if isinstance(value, (list, tuple)):
        return (type(value).__name__, tuple(_frozen_base_value(item) for item in value))
    if isinstance(value, (set, frozenset)):
        return (type(value).__name__, tuple(sorted((_frozen_base_value(item) for item in value), key=repr)))
    return (type(value).__name__, repr(value))


def _frozen_record_key(builder, record):
    return repr(_frozen_base_value(dict(bound_arguments(builder, record))))


def _valid_predicate(text, expression_types):
    if not isinstance(text, str) or not text:
        return False
    try:
        validate_expression(text, expression_types)
    except (ValueError, TypeError, SyntaxError, RecursionError):
        return False
    return True


def _compact_catalogue_for_feedback(catalogue, *, is_decision_table):
    compact = {
        key: value
        for key, value in (catalogue or {}).items()
        if value is not None and value != [] and value != {}
    }
    for section in ("classes", "boundaries", "rules", "original_rules"):
        if section in compact:
            compact[section] = [
                {
                    key: value
                    for key, value in row.items()
                    if value is not None and value != [] and value != {}
                }
                for row in compact[section]
            ]
    if not is_decision_table:
        return {key: value for key, value in compact.items() if key != "original_rules"}
    return {
        **{key: value for key, value in compact.items() if key not in ("rules", "original_rules")},
        "rules": {
            row["id"]: {
                key: row[key]
                for key in ("status", "actions", "reason", "fault_hypothesis")
                if key in row
            }
            for row in compact.get("original_rules", [])
        },
    }


def _check_feedback_consistency(first_catalogue, second_catalogue, round0_feedback, expression_types):
    """Preserve already-hit target definitions keyed by (section, id) while allowing repair of unknown/missed/errored metadata."""
    if not first_catalogue:
        return []
    old = first_catalogue
    new = second_catalogue or {}
    parameter_names = set(expression_types)
    hit_targets = {
        (row["kind"], row["id"])
        for row in round0_feedback.get("targets", [])
        if row.get("status") == "hit"
    }
    errored_targets = {
        (row["kind"], row["id"])
        for row in round0_feedback.get("targets", [])
        if row.get("errors")
    }
    errored_conditions = set(round0_feedback.get("errored_conditions", []))
    if not hit_targets:
        return []

    id_counts = {}
    for section in ("classes", "boundaries", "rules"):
        for row in old.get(section, []):
            identifier = row.get("id") if isinstance(row, dict) else None
            if identifier is not None:
                id_counts[identifier] = id_counts.get(identifier, 0) + 1
    colliding_ids = {identifier for identifier, count in id_counts.items() if count > 1}

    errors = []
    for section in ("classes", "boundaries", "rules", "original_rules"):
        old_rows = old.get(section, [])
        new_rows = {row["id"]: row for row in new.get(section, []) if isinstance(row, dict) and "id" in row}
        base_locked_keys = LOCKED_KEYS_BY_SECTION[section]
        for old_row in old_rows:
            identifier = old_row.get("id")
            if (section, identifier) not in hit_targets:
                continue
            # Exempt colliding IDs so Round 1 can repair duplicate_id without deadlocking.
            if identifier in colliding_ids:
                continue
            if identifier not in new_rows:
                errors.append(f"dropped_hit_target:{section}:{identifier}")
                continue
            new_row = new_rows[identifier]
            locked_keys = (
                base_locked_keys + ("values",)
                if section == "boundaries" and old_row.get("numeric_kind") == "discrete"
                else base_locked_keys
            )
            for key in locked_keys:
                old_value = old_row.get(key)
                if key == "predicate" and (
                    not _valid_predicate(old_value, expression_types)
                    or (section, identifier) in errored_targets
                ):
                    continue
                if key == "parameter" and old_value not in parameter_names:
                    continue
                if key == "step" and old_row.get("numeric_kind") == "float" and old_value is None:
                    continue
                if key == "status" and section == "original_rules":
                    if any(cond in errored_conditions for cond in old_row.get("conditions", {})):
                        continue
                new_value = new_row.get(key)
                if key == "values" and isinstance(old_value, list) and isinstance(new_value, list):
                    old_set = {(type(item).__name__, item) for item in old_value}
                    new_set = {(type(item).__name__, item) for item in new_value}
                    if new_set != old_set:
                        errors.append(f"changed_hit_target_definition:{section}:{identifier}")
                        break
                    continue
                if new_value != old_value:
                    errors.append(f"changed_hit_target_definition:{section}:{identifier}")
                    break

    # Lock valid, non-erroring condition predicates referenced by hit original rules.
    hit_rule_conditions = set()
    for old_rule in old.get("original_rules", []):
        if ("original_rules", old_rule.get("id")) in hit_targets:
            hit_rule_conditions.update(old_rule.get("conditions", {}).keys())
    for name in sorted(hit_rule_conditions):
        if name in errored_conditions:
            continue
        old_predicate = old.get("condition_predicates", {}).get(name)
        if _valid_predicate(old_predicate, expression_types):
            if new.get("condition_predicates", {}).get(name) != old_predicate:
                errors.append(f"changed_hit_condition_definition:{name}")
    return errors


def _should_accept_feedback_catalogue(first, second, consistency):
    """Accept repaired Round 1 catalogue only if it does not regress structural or membership quality."""
    if consistency:
        return False
    first_status = first.get("catalogue_status")
    second_status = second.get("catalogue_status")
    if second_status == "catalogue_invalid":
        return False
    if first_status == "catalogue_invalid":
        # Allow repairing an invalid catalogue into applicable, not_applicable, or unresolved.
        return second_status in ("applicable", "not_applicable", "unresolved")
    if first_status == "unresolved":
        return second_status == "applicable"
    if first_status == "not_applicable":
        return second_status in ("applicable", "not_applicable")
    if second_status != "applicable":
        return False
    if first.get("membership_ready") and not second.get("membership_ready"):
        return False
    if len(second.get("membership_errors", [])) > len(first.get("membership_errors", [])):
        return False
    return True


class Vf3MeasuredFeedback:
    """Shared VF3 measured mixin combining V2 guidance, strict schema and 20+10 feedback."""

    preserve_prompt_context = True
    feedback_input_budget = 10

    def configuration(self):
        return {
            **super().configuration(),
            "protocol": "catalogue-vf3-measured",
            "calls": "one-initial-plus-one-feedback",
            "max_model_calls": 2,
            "structured_output": "json-schema",
            "oracle_feedback": False,
            "prompt_context": "full-v2-guidance-example-and-visible-PUTs",
            "prefreeze_measurement": "trusted-domain-admitted-or-provisional-input-membership",
            "first_input_budget": "configured-input-budget",
            "feedback_input_budget": self.feedback_input_budget,
            "retained_input_budget": f"configured-input-budget+{self.feedback_input_budget}",
            "base_duplicates": "discard-before-coverage-and-quota",
            "dt_condition_cap": 4 if "rules" in self.sections else None,
        }

    def build_guidance(self, packet):
        base_guidance = super().build_guidance(packet)
        if "rules" in self.sections:
            # Replace V2's merged-"-" advice which conflicts with OriginalTable1..4's unmerged schema.
            base_guidance = base_guidance.replace(
                "Merge only when ordered actions agree and omitted conditions do not change behavior. "
                'If a PUT may depend on a merged "-" condition, vary just that condition across two feasible '
                "calls in the same rule. Use existing calls for either side and add only missing contrasts.\n",
                "Vary interacting conditions across multiple feasible inputs per rule to expose subtle "
                "implementation bugs; use existing base calls as context and add NEW distinct contrasts.\n",
            )
        specific = (
            DT_VF3_MEASURED_INSTRUCTION
            if "rules" in self.sections
            else EP_BVA_VF3_MEASURED_INSTRUCTION
        )
        return (
            base_guidance
            + "\n\nVF3 MEASURED OUTPUT CONTRACT:\n"
            + COMMON_VF3_MEASURED_INSTRUCTION
            + "\n"
            + specific
        )

    def build_messages(self, packet):
        messages = super().build_messages(packet)
        content = messages[1]["content"]
        # Replace the legacy V2 JSON envelope so it cannot contradict the enforced JSON Schema.
        start = content.find('Return JSON: {"catalogue":')
        end = content.find("\narguments maps", start)
        if start >= 0 and end > start:
            replacement = (
                "Return one JSON object matching the supplied JSON Schema: catalogue and inputs. "
                "covers labels are optional; no expected outputs.\n"
            )
            content = content[:start] + replacement + content[end:]
        messages[1]["content"] = content
        return messages

    def round_budgets(self, budget):
        return budget, budget + self.feedback_input_budget

    def run(self, context):
        if not self.settings.catalogue:
            raise ValueError("VF3 measured arms require catalogue=true")
        return context.artifacts.load_or_compute(
            f"{context.task_directory}/{self.name}/generation.json",
            lambda: self.generate(context),
        )

    def run_structured(self, context, *, call_name=None, messages=None, input_budget=None):
        if context.calls is None or context.packet is None:
            raise RuntimeError("A VF3 measured arm requires prepared context and model calls")
        settings = context.settings
        budget = input_budget if input_budget is not None else settings.input_budget
        schema_model = response_type(context.task, self.sections, budget)
        response = context.calls.complete(
            context.task_number,
            call_name or self.name,
            messages or self.build_messages(context.packet),
            temperature=settings.input_temperature,
            max_tokens=settings.input_tokens,
            seed=settings.input_seed + context.task_number,
            response_format=structured_format(schema_model.model_json_schema()),
        )
        try:
            raw, _ = load_response_json(response.text)
            schema_model.model_validate(raw)
        except (ValidationError, ValueError, TypeError, RecursionError) as error:
            # Preserve valid concrete inputs without leaking uncanonicalized dict rules
            # into legacy Catalogue validation (which previously created fake list_type errors).
            result = self._decode_inputs_only_fallback(response, context)
            result["structured_output_errors"] = [str(error)[:2000]]
            result["catalogue"] = None
            result["catalogue_status"] = result["status"] = "catalogue_invalid"
            result["catalogue_errors"] = ["structured_output_invalid"]
            result["membership_errors"] = []
            result["membership_ready"] = False
            return result

        canonical = canonical_response(raw, self.sections, task=context.task)
        result = self.decode_response(replace(response, text=json.dumps(canonical)), context)
        result["structured_output_errors"] = []
        if result.get("catalogue") is not None:
            parsed_catalogue = Catalogue.model_validate(result["catalogue"])
            result["membership_errors"] = membership_errors(parsed_catalogue, context.task)
        else:
            result["membership_errors"] = list(result.get("catalogue_errors", []))
        result["membership_ready"] = (
            not result["membership_errors"] and result["catalogue_status"] != "catalogue_invalid"
        )
        return result

    def _decode_inputs_only_fallback(self, response, context):
        """Extract valid inputs from a structured-schema-failing response without mutating state."""
        temporary_off = type(self)(replace(self.settings, catalogue=False))
        return temporary_off.decode_response(response, context)

    def novel_inputs(self, context, batch, previous=()):
        """Discard base duplicates and within/cross-round duplicates using sandbox frozen keys."""
        builder = CallBuilder.for_source(context.task["prompt"], context.task["entry_point"])
        cohort_task = context.cohort_task or {}
        base_frozen_keys = set(cohort_task.get("base_input_keys", []))
        for program in cohort_task.get("programs", ()):
            for call in program.get("base", {}).get("calls", ()):
                try:
                    base_frozen_keys.add(_frozen_record_key(builder, call))
                except (ValueError, TypeError, SyntaxError):
                    pass

        seen_keys = {_frozen_record_key(builder, row) for row in previous}
        retained = []
        rejected = list(batch.get("rejected", []))
        for index, row in enumerate(batch.get("inputs", [])):
            frozen_key = _frozen_record_key(builder, row)
            if frozen_key in base_frozen_keys:
                reason = "base_duplicate"
            elif frozen_key in seen_keys:
                reason = "duplicate"
            else:
                reason = None
            if reason is not None:
                rejected.append({"index": row.get("source_index", index), "reason": reason})
            else:
                retained.append(row)
                seen_keys.add(frozen_key)
        return {**batch, "inputs": retained, "rejected": rejected}

    def feedback(self, context, batch):
        """Compute pre-freeze trusted-domain admission and observed membership feedback."""
        builder = CallBuilder.for_source(context.task["prompt"], context.task["entry_point"])
        authority = compile_domain(context.metadata.get("contract", ""), builder.signature.parameters)
        admitted_valid = []
        provisional_non_invalid = []
        admission = []
        for index, record in enumerate(batch["inputs"]):
            status = "unknown"
            reason = authority["status"]
            if authority["status"] == "supported":
                try:
                    accepted = evaluate(authority["expression"], dict(bound_arguments(builder, record)))
                    status = "valid" if accepted else "invalid"
                    reason = None if accepted else "trusted_domain_rejects"
                except (ValueError, TypeError, ArithmeticError, LookupError, SyntaxError) as error:
                    reason = f"{type(error).__name__}:{str(error)[:150]}"
            elif authority["status"] == "not_provided":
                reason = "trusted_contract_not_provided"
            if status == "valid":
                admitted_valid.append(index)
            if status != "invalid":
                provisional_non_invalid.append(index)
            admission.append({"input_index": index, "status": status, "reason": reason})

        # When the static domain compiler cannot parse the contract (e.g. .startswith()),
        # measure coverage provisionally on non-invalid inputs instead of dropping them all.
        if authority["status"] == "supported":
            measured_indices = admitted_valid
            admission_basis = "trusted_domain_valid_only"
        else:
            measured_indices = provisional_non_invalid
            admission_basis = "provisional_contract_" + authority["status"]

        measured = measure_catalogue(
            batch,
            context.task,
            measured_indices,
            arm_name=self.name,
            input_budget=self.round_budgets(context.settings.input_budget)[1],
        )
        observed = measured.get("observed", {})
        targets = []
        for section in ("classes", "boundaries", "original_rules"):
            for row in observed.get(section, []):
                target = {
                    "kind": section,
                    "id": row["id"],
                    "status": row["status"],
                    "input_indices": row.get("source_input_indices", []),
                    "errors": row.get("errors", [])[:3],
                }
                if section == "boundaries":
                    target["targets"] = [
                        {"value": item["value"], "status": item["status"]}
                        for item in row["targets"]
                    ]
                    target["single_fault"] = row["single_fault"]
                targets.append(target)

        errored_conditions = [
            row["id"]
            for row in observed.get("conditions", [])
            if row.get("errors")
        ]
        errored_condition_details = {
            row["id"]: row["errors"][:2]
            for row in observed.get("conditions", [])
            if row.get("errors")
        }
        errors = (
            batch.get("structured_output_errors", [])
            + batch.get("catalogue_errors", [])
            + batch.get("membership_errors", [])
        )
        reasons = []
        if batch.get("catalogue_status") == "unresolved":
            reasons.append("unresolved_catalogue")
        if errors or errored_conditions or not batch.get("membership_ready"):
            reasons.append("repair_metadata")
        if any(row["status"] != "hit" for row in targets):
            reasons.append("uncovered_or_unknown_targets")
        if observed.get("original_rule_basis") == "unknown":
            reasons.append("missing_original_denominator")
        if any(row["single_fault"] == "pending" for row in observed.get("boundaries", [])):
            reasons.append("single_fault_pending")
        if any(row["status"] == "invalid" for row in admission):
            reasons.append("input_admission")
        return {
            "phase": "pre_freeze_no_oracle",
            "admission_basis": admission_basis,
            "admission": admission,
            "targets": targets,
            "errored_conditions": errored_conditions,
            "errored_condition_details": errored_condition_details,
            "metadata_errors": errors,
            "repair_reasons": reasons,
            "catalogue_status": batch.get("catalogue_status"),
            "membership_ready": batch.get("membership_ready", False),
            "semantic_grounding": "pending",
        }

    def generate(self, context):
        first_budget, total_budget = self.round_budgets(context.settings.input_budget)
        first_context = replace(context, settings=replace(context.settings, input_budget=first_budget))
        first = self.run_structured(first_context, call_name=f"{self.name}_initial", input_budget=first_budget)
        first = self.novel_inputs(context, first)

        directory = f"{context.task_directory}/{self.name}"
        round0_feedback = context.artifacts.load_or_compute(
            f"{directory}/round_0_feedback.json",
            lambda: self.feedback(context, first),
        )
        rounds = [{"call_name": f"{self.name}_initial", "input_budget": first_budget, "feedback": round0_feedback}]
        inputs = list(first["inputs"])
        remaining = self.feedback_input_budget
        result = first

        # Run feedback for applicable, unresolved, or invalid catalogues (skip only genuine clean not_applicable).
        should_run_feedback = (
            remaining > 0
            and (
                first.get("catalogue_status") in ("applicable", "unresolved", "catalogue_invalid")
                or bool(round0_feedback["repair_reasons"])
            )
        )
        if should_run_feedback:
            feedback_payload = dict(round0_feedback)
            if not feedback_payload["repair_reasons"]:
                feedback_payload["repair_reasons"] = ["supplement_fault_hypotheses"]
            messages = self.build_messages(context.packet)
            messages.append({
                "role": "user",
                "content": json.dumps(
                    {
                        "instruction": (
                            "Return the full repaired catalogue (status='applicable' whenever the technique applies) and "
                            "up to new_input_budget NEW distinct inputs (never repeating base calls or retained_inputs; "
                            "previous retained inputs are preserved automatically). Keep already-hit target IDs and their "
                            "executable definitions unchanged (EXCEPT fix any predicate/condition in errored_conditions or "
                            "target errors that raised a runtime error such as IndexError). Keep the same DT condition count "
                            "C1..Cn if any rule already hit, keep >=1 DT row feasible, keep all IDs unique across sections, "
                            "cover all missed/unknown targets and nominal+single-fault boundary points, and spend remaining "
                            "slots on high-value fault-revealing contrasts. No oracle/PUT outcomes are available."
                        ),
                        "predicate_rules": FEEDBACK_PREDICATE_RULES,
                        "previous_catalogue": _compact_catalogue_for_feedback(
                            first.get("catalogue"),
                            is_decision_table="rules" in self.sections,
                        ),
                        "retained_inputs": [
                            {key: row[key] for key in ("args", "kwargs")}
                            for row in inputs
                        ],
                        "feedback": feedback_payload,
                        "new_input_budget": remaining,
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            })
            if context.calls.token_count(messages) + context.settings.input_tokens + 128 <= context.settings.context_tokens:
                second_context = replace(context, settings=replace(context.settings, input_budget=remaining))
                second = self.run_structured(
                    second_context,
                    call_name=f"{self.name}_feedback",
                    messages=messages,
                    input_budget=remaining,
                )
                second = self.novel_inputs(context, second, inputs)
                builder = CallBuilder.for_source(context.task["prompt"], context.task["entry_point"])
                try:
                    annotations = declared_types(context.task["prompt"], context.task["entry_point"])
                except ValueError:
                    annotations = {}
                expression_types = {
                    name: annotations.get(name, "any")
                    for name in builder.signature.parameters
                }
                consistency = _check_feedback_consistency(
                    first.get("catalogue"),
                    second.get("catalogue"),
                    round0_feedback,
                    expression_types,
                )
                if _should_accept_feedback_catalogue(first, second, consistency):
                    result = second
                else:
                    rejection_reasons = (
                        consistency
                        + second.get("structured_output_errors", [])
                        + second.get("catalogue_errors", [])
                    )
                    if not rejection_reasons:
                        if second.get("catalogue_status") == "applicable":
                            rejection_reasons.append("regressive_membership_errors")
                        else:
                            rejection_reasons.append(
                                f"status_regression:{first.get('catalogue_status')}_to_{second.get('catalogue_status')}"
                            )
                    result = {**first, "feedback_catalogue_errors": rejection_reasons}

                # novel_inputs(context, second, inputs) already filtered base and cross-round duplicates.
                inputs.extend(second["inputs"])
                result = {
                    **result,
                    "inputs": inputs,
                    "rejected": first.get("rejected", []) + second.get("rejected", []),
                }
                round1_feedback = context.artifacts.load_or_compute(
                    f"{directory}/round_1_feedback.json",
                    lambda: self.feedback(context, result),
                )
                rounds.append({
                    "call_name": f"{self.name}_feedback",
                    "input_budget": remaining,
                    "feedback": round1_feedback,
                })
            else:
                result = {**first, "feedback_skip": "prompt_too_large"}

        return {
            **result,
            "inputs": inputs[:total_budget],
            "rounds": rounds,
            "model_calls": len(rounds),
            "oracle_feedback": False,
            "input_budget": total_budget,
            "status": result.get("status", "generated"),
        }


class EpBvaVf3MeasuredArm(Vf3MeasuredFeedback, EpBvaV2Arm):
    name = "ep_bva_vf3_measured"


class DecisionTableVf3MeasuredArm(Vf3MeasuredFeedback, DecisionTableV2Arm):
    name = "decision_table_vf3_measured"


VF3_MEASURED_ARMS = (EpBvaVf3MeasuredArm, DecisionTableVf3MeasuredArm)
