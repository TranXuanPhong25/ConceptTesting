"""Compact catalogue validation and conservative measurements; never executes predicates.

Pydantic validates structure. Numeric intervals, named selectors, itertools products
and math.nextafter cover the mechanical subset. Prose remains pending semantic audit.
No result here filters an input or supplies an expected output.
"""
from __future__ import annotations

import ast
import json
from collections import defaultdict
from itertools import combinations, product
import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from .call_builder import CallBuilder, decode_value, supported_value

Number = int | float
ConditionValue = str | bool | int | float
MAX_CONDITION_COMBINATIONS = 10000


class Schema(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", allow_inf_nan=False)


class Selector(Schema):
    parameter: str | None = None
    transform: Literal["identity", "length", "count", "parsed_int", "parsed_float"] = "identity"
    count_value: object = None


class EquivalenceClass(Selector):
    id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    partition: str | None = None
    kind: Literal["input", "output", "invalid"] = "input"
    lower: Number | None = None
    upper: Number | None = None
    lower_inclusive: bool = True
    upper_inclusive: bool = True
    members: list | None = None
    fault_hypothesis: str | None = Field(default=None, min_length=1, exclude_if=lambda value: value is None)


class Boundary(Selector):
    id: str = Field(min_length=1)
    dimension: str = Field(min_length=1)
    values: list[Number | str | bool] = Field(min_length=1)
    lower: Number | None = None
    upper: Number | None = None
    numeric_kind: Literal["integer", "float", "discrete"] | None = None
    step: Number | None = Field(default=None, gt=0)
    context: dict[str, object] = Field(default_factory=dict)
    nominal: dict[str, object] | None = None

    @field_validator("context", "nominal")
    @classmethod
    def validate_context_and_nominal_arguments(cls, values):
        """Use the same safe literal contract for context, nominal and real inputs."""
        if values is not None:
            for value in values.values():
                if not supported_value(decode_value(value)):
                    raise ValueError("unsupported catalogue argument value")
        return values


class Rule(Schema):
    id: str = Field(min_length=1)
    conditions: dict[str, ConditionValue]
    actions: list[str] = Field(min_length=1)
    merged_from: list[str] = Field(default_factory=list)
    fault_hypothesis: str | None = Field(default=None, min_length=1, exclude_if=lambda value: value is None)


class OriginalRule(Schema):
    id: str = Field(min_length=1)
    conditions: dict[str, ConditionValue]
    actions: list[str] = Field(default_factory=list)
    status: Literal["feasible", "infeasible", "unresolved"] = "feasible"
    reason: str | None = None


class Catalogue(Schema):
    classes: list[EquivalenceClass] = Field(default_factory=list)
    boundaries: list[Boundary] = Field(default_factory=list)
    rules: list[Rule] = Field(default_factory=list)
    original_rules: list[OriginalRule] = Field(default_factory=list)
    # Optional machine-readable domains, never arbitrary Python expressions.
    conditions: dict[str, list[ConditionValue]] = Field(default_factory=dict)
    mutually_exclusive: list[list[str]] = Field(default_factory=list)
    status: Literal["applicable", "not_applicable", "unresolved"] = "applicable"
    reason: str | None = None


def validate_catalogue(raw, sections):
    """Validate shape and declared consistency; spec semantics remain unproven."""
    if not isinstance(raw, dict) or any(section not in raw for section in sections):
        return None, ["missing_catalogue_or_section"]
    try:
        catalogue = Catalogue.model_validate(raw)
    except ValidationError as error:
        return None, ["schema:" + ".".join(map(str, item["loc"])) + ":" + item["type"]
                      for item in error.errors(include_input=False)]
    except (ValueError, TypeError, RecursionError, OverflowError):
        return None, ["invalid_catalogue_data"]
    errors = validate_catalogue_structure(catalogue, sections)
    errors.extend(partition_issues(catalogue.classes))
    errors.extend(decision_table_check(catalogue)["errors"])
    errors.extend(validate_boundary_ranges(catalogue.boundaries))
    return catalogue, errors


def validate_catalogue_structure(catalogue, required_sections):
    """Check shared IDs, status explanations and required nonempty sections."""
    errors = []
    identifiers = []
    for section in (catalogue.classes, catalogue.boundaries, catalogue.rules):
        identifiers.extend(item.id for item in section)
    if len(identifiers) != len(set(identifiers)):
        errors.append("duplicate_id")
    if catalogue.status != "applicable" and not catalogue.reason:
        errors.append("missing_status_reason")
    if catalogue.status == "applicable":
        if any(not getattr(catalogue, section) for section in required_sections):
            errors.append("empty_required_section")
    return errors


def validate_boundary_ranges(boundaries):
    """A supplied lower endpoint cannot exceed its upper endpoint."""
    errors = []
    for boundary in boundaries:
        if boundary.lower is not None and boundary.upper is not None:
            if boundary.lower > boundary.upper:
                errors.append(f"reversed_boundary:{boundary.id}")
    return errors


def partition_issues(classes):
    errors = []
    for item in classes:
        # An empty member set or an empty interval cannot represent a class.
        if item.members == [] or (item.lower is not None and item.upper is not None and
                (item.lower > item.upper or (item.lower == item.upper and
                 not (item.lower_inclusive and item.upper_inclusive)))):
            errors.append(f"empty_class:{item.id}")
    # Only compare explicit partitions/selectors. Independent axes may overlap.
    groups = defaultdict(list)
    for item in classes:
        if item.partition and item.parameter:
            groups[(item.partition, item.parameter, item.transform)].append(item)
    for group in groups.values():
        for left, right in combinations(group, 2):
            if left.members is not None and right.members is not None:
                overlap = any(value in right.members for value in left.members)
            elif all(value is not None for value in (left.lower, left.upper, right.lower, right.upper)):
                low, high = max(left.lower, right.lower), min(left.upper, right.upper)
                overlap = low < high or (low == high and interval_contains(left, low) and interval_contains(right, low))
            else:
                continue
            if overlap:
                errors.append(f"overlap:{left.id}:{right.id}")
    return errors


def interval_contains(item, value):
    if item.lower is None and item.upper is None:
        return None
    if type(value) not in (int, float):
        return False
    return ((item.lower is None or value > item.lower or (value == item.lower and item.lower_inclusive)) and
            (item.upper is None or value < item.upper or (value == item.upper and item.upper_inclusive)))


def selected_value(selector, arguments):
    if selector.parameter is None or selector.parameter not in arguments:
        return None, False
    value = arguments[selector.parameter]
    try:
        if selector.transform == "length":
            value = len(value)
        elif selector.transform == "count":
            value = value.count(decode_value(selector.count_value))
        elif selector.transform == "parsed_int":
            value = int(value)
        elif selector.transform == "parsed_float":
            value = float(value)
        if type(value) is float and not math.isfinite(value):
            return None, False
        return value, True
    except (ValueError, TypeError, AttributeError, OverflowError):
        return None, False


def boundary_targets(boundary, *, robust=False):
    """Only finite specified endpoints; unbounded Python int gets no invented limits."""
    numeric_kind = boundary.numeric_kind
    if numeric_kind is None:
        if boundary.lower is None and boundary.upper is None and all(type(value) in (str, bool) for value in boundary.values):
            numeric_kind = "discrete"
        else:
            numeric_kind = "float" if any(type(value) is float for value in (boundary.lower, boundary.upper)) else "integer"
    if numeric_kind == "discrete":
        return list(dict.fromkeys(boundary.values))
    targets = []
    for endpoint, inward in ((boundary.lower, 1), (boundary.upper, -1)):
        if endpoint is None:
            continue
        def neighbor(direction):
            if numeric_kind == "float" and boundary.step is None:
                return math.nextafter(float(endpoint), math.inf if direction > 0 else -math.inf)
            step = boundary.step if boundary.step is not None else 1
            return endpoint + direction * step
        candidates = [endpoint, neighbor(inward)]
        if robust:
            candidates.append(neighbor(-inward))
        for value in candidates:
            inside = ((boundary.lower is None or value >= boundary.lower) and
                      (boundary.upper is None or value <= boundary.upper))
            if (type(value) is int or math.isfinite(value)) and (robust or inside) and value not in targets:
                targets.append(value)
    return targets


def bound_arguments(builder, record):
    bound = builder.signature.bind(*ast.literal_eval(record["args"]), **ast.literal_eval(record["kwargs"]))
    bound.apply_defaults()
    return bound.arguments


def matches_context(arguments, context):
    return all(name in arguments and arguments[name] == decode_value(value) for name, value in context.items())


def mechanical_boundaries(catalogue, arguments, *, robust=False, worst_case=False):
    rows = []
    for boundary in catalogue.boundaries:
        targets = boundary_targets(boundary, robust=robust)
        expected = targets or boundary.values
        matched, violations = [], []
        nominal = None if boundary.nominal is None else {key: decode_value(value) for key, value in boundary.nominal.items()}
        # A nominal must cover every argument and satisfy the boundary's context
        # before single-fault coverage can be checked.
        single_checkable = nominal is not None and boundary.parameter is not None and all(
            set(item) == set(nominal) for item in arguments)
        single_checkable = single_checkable and selected_value(boundary, nominal)[1]
        single_checkable = single_checkable and matches_context(nominal, boundary.context)
        other_dimensions = []
        # Preserve other declared dimensions even when they share one parameter
        # (for example, length(lst) and count(lst, 0)).
        for other in catalogue.boundaries:
            same_selector = (other.parameter, other.transform, other.count_value) == (boundary.parameter, boundary.transform, boundary.count_value)
            if not same_selector and nominal is not None and matches_context(nominal, other.context):
                nominal_value, checkable = selected_value(other, nominal)
                if not checkable:
                    single_checkable = False
                other_dimensions.append((other, nominal_value))
        for index, item in enumerate(arguments):
            value, checkable = selected_value(boundary, item)
            if not checkable or not matches_context(item, boundary.context) or value not in expected:
                continue
            single_fault = single_checkable and all(item[name] == nominal[name] for name in item if name != boundary.parameter)
            single_fault = single_fault and all(selected_value(other, item) == (nominal_value, True)
                                                 for other, nominal_value in other_dimensions)
            if single_checkable and not single_fault:
                violations.append(index)
            if worst_case or single_fault:
                matched.append(value)
        observed = list(dict.fromkeys(matched))
        rows.append({"id": boundary.id, "targets": expected, "matched_values": observed,
            "missing_values": [value for value in expected if value not in observed] if single_checkable or worst_case else None,
            "numeric_targets_status": "checked" if targets else "pending",
            "declared_values_match_targets": set(boundary.values) == set(targets) if targets else None,
            "single_fault": "not_required" if worst_case else "checked" if single_checkable else "pending",
            "non_single_fault_input_indices": violations if not worst_case else [],
            "nominal_input_present": any(item == nominal for item in arguments) if single_checkable else None,
            "semantic_grounding": "pending"})
    return rows


def normal_design_size(catalogue, *, robust=False):
    """Count declared single-fault coordinate obligations, deduplicating nominals.

    This is a design over supplied dimensions, not proof that all spec dimensions
    were supplied. No input arguments are synthesized or executed here.
    """
    groups = defaultdict(set)
    for boundary in catalogue.boundaries:
        if not boundary.nominal or boundary.parameter is None:
            return None
        nominal = {key: decode_value(value) for key, value in boundary.nominal.items()}
        nominal_value, checkable = selected_value(boundary, nominal)
        targets = boundary_targets(boundary, robust=robust)
        if not checkable or not targets or not matches_context(nominal, boundary.context):
            return None
        group = json.dumps(boundary.nominal, sort_keys=True, ensure_ascii=False)
        for value in targets:
            if value != nominal_value:
                groups[group].add((boundary.parameter, boundary.transform,
                                   json.dumps(boundary.count_value, sort_keys=True), value))
        groups[group]  # retain a degenerate all-nominal design
    return sum(1 + len(values) for values in groups.values()) if groups else None


def truth(value):
    return value is True or value == "T"


def conditions_match(pattern, actual):
    return all(value == "-" or (name in actual and actual[name] == value) for name, value in pattern.items())


def conditions_violate_exclusivity(conditions, mutually_exclusive_groups):
    """At most one true condition is allowed in each declared exclusive group."""
    for group in mutually_exclusive_groups:
        true_count = sum(truth(conditions.get(name)) for name in group)
        if true_count > 1:
            return True
    return False


def validate_original_rule_definitions(catalogue, originals_by_id):
    """Validate original IDs, feasibility declarations and finite-domain values."""
    errors = []
    if len(originals_by_id) != len(catalogue.original_rules):
        errors.append("duplicate_original_rule_id")
    for rule in catalogue.original_rules:
        exclusive_conditions_conflict = conditions_violate_exclusivity(
            rule.conditions, catalogue.mutually_exclusive)
        if exclusive_conditions_conflict and rule.status != "infeasible":
            errors.append(f"infeasible_combination:{rule.id}")
        if rule.status == "infeasible" and not rule.reason:
            errors.append(f"infeasible_without_reason:{rule.id}")
        if rule.status == "feasible" and (not rule.actions or "-" in rule.conditions.values()):
            errors.append(f"incomplete_original_rule:{rule.id}")
        if catalogue.conditions:
            condition_names_differ = set(rule.conditions) != set(catalogue.conditions)
            values_outside_domains = any(
                value not in catalogue.conditions.get(name, [])
                for name, value in rule.conditions.items())
            if condition_names_differ or values_outside_domains:
                errors.append(f"invalid_condition_values:{rule.id}")
    return errors


def validate_merged_rule_definitions(catalogue, originals_by_id, feasible_originals):
    """Merged rules must preserve source conditions and ordered actions."""
    errors, pending = [], []
    for merged_rule in catalogue.rules:
        original_with_same_id = originals_by_id.get(merged_rule.id)
        if original_with_same_id is not None:
            identical_conditions = merged_rule.conditions == original_with_same_id.conditions
            identical_actions = merged_rule.actions == original_with_same_id.actions
            unambiguous_sources = merged_rule.merged_from in ([], [merged_rule.id])
            if not (identical_conditions and identical_actions and unambiguous_sources):
                errors.append(f"ambiguous_merged_original_id:{merged_rule.id}")
        if len(merged_rule.merged_from) != len(set(merged_rule.merged_from)):
            errors.append(f"duplicate_merge_source:{merged_rule.id}")
        for source_id in merged_rule.merged_from:
            original_rule = originals_by_id.get(source_id)
            if original_rule is None:
                pending.append(f"missing_merge_source:{source_id}")
                continue
            preserves_original = (
                original_rule.status == "feasible"
                and original_rule.actions == merged_rule.actions
                and conditions_match(merged_rule.conditions, original_rule.conditions))
            if not preserves_original:
                errors.append(f"invalid_merge:{merged_rule.id}:{source_id}")
        if originals_by_id:
            matched_source_ids = []
            for original_rule in feasible_originals:
                if conditions_match(merged_rule.conditions, original_rule.conditions):
                    matched_source_ids.append(original_rule.id)
            if merged_rule.merged_from and set(matched_source_ids) != set(merged_rule.merged_from):
                errors.append(f"merge_mapping_mismatch:{merged_rule.id}")
    return errors, pending


def rule_patterns_overlap(left_rule, right_rule):
    """Check syntactic intersection only; this does not establish feasibility."""
    condition_names = set(left_rule.conditions) | set(right_rule.conditions)
    for name in condition_names:
        left_value = left_rule.conditions.get(name, "-")
        right_value = right_rule.conditions.get(name, "-")
        if left_value != "-" and right_value != "-" and left_value != right_value:
            return False
    return True


def condition_combination_count(condition_domains):
    if not condition_domains:
        return None
    return math.prod(len(values) for values in condition_domains.values())


def overlap_is_explicitly_infeasible(left_rule, right_rule, catalogue, originals_by_id):
    """Require every finite intersection to have an explicit infeasible record."""
    combination_count = condition_combination_count(catalogue.conditions)
    if combination_count is None or combination_count > MAX_CONDITION_COMBINATIONS:
        return False
    condition_names = list(catalogue.conditions)
    statuses_by_combination = {}
    for original_rule in originals_by_id.values():
        coordinates = tuple(original_rule.conditions.get(name) for name in condition_names)
        statuses_by_combination[coordinates] = original_rule.status
    intersections = []
    condition_domains = [catalogue.conditions[name] for name in condition_names]
    for values in product(*condition_domains):
        conditions = dict(zip(condition_names, values))
        if conditions_match(left_rule.conditions, conditions) and conditions_match(right_rule.conditions, conditions):
            intersections.append(values)
    return bool(intersections) and all(
        statuses_by_combination.get(values) == "infeasible" for values in intersections)


def find_potential_rule_overlaps(catalogue, originals_by_id):
    """Keep unexplained syntactic intersections pending for semantic audit."""
    pending = []
    for left_rule, right_rule in combinations(catalogue.rules, 2):
        if not rule_patterns_overlap(left_rule, right_rule):
            continue
        joint_conditions = dict(left_rule.conditions)
        for name, value in right_rule.conditions.items():
            if value != "-":
                joint_conditions[name] = value
        if conditions_violate_exclusivity(joint_conditions, catalogue.mutually_exclusive):
            continue
        # Feasible witnesses are checked separately. Prose alone cannot establish
        # that the intersection belongs to, or lies outside, the joint domain.
        if not overlap_is_explicitly_infeasible(left_rule, right_rule, catalogue, originals_by_id):
            pending.append(f"potential_overlap:{left_rule.id}:{right_rule.id}")
    return pending


def validate_feasible_rule_coverage(rules, feasible_originals):
    """Each feasible original needs exactly one rule with the same action order."""
    errors = []
    for original_rule in feasible_originals:
        matching_rules = []
        for rule in rules:
            if conditions_match(rule.conditions, original_rule.conditions):
                matching_rules.append(rule)
        if not matching_rules:
            errors.append(f"missing_rule:{original_rule.id}")
        elif len(matching_rules) > 1:
            errors.append(f"overlapping_rules:{original_rule.id}")
        if any(rule.actions != original_rule.actions for rule in matching_rules):
            errors.append(f"conflicting_actions:{original_rule.id}")
    return errors


def find_unresolved_condition_combinations(catalogue, originals_by_id):
    """Count missing finite combinations without treating them as infeasible."""
    combination_count = condition_combination_count(catalogue.conditions)
    if combination_count is None:
        return []
    if combination_count > MAX_CONDITION_COMBINATIONS:
        return ["combination_check_budget_limited"]
    condition_names = list(catalogue.conditions)
    represented = set()
    for original_rule in originals_by_id.values():
        represented.add(tuple(original_rule.conditions.get(name) for name in condition_names))
    missing_count = 0
    condition_domains = [catalogue.conditions[name] for name in condition_names]
    for values in product(*condition_domains):
        if values not in represented:
            missing_count += 1
    return [f"unresolved_combinations:{missing_count}"] if missing_count else []


def decision_table_check(catalogue):
    """Validate DT declarations in a fixed order; retain stable diagnostic codes."""
    originals_by_id = {rule.id: rule for rule in catalogue.original_rules}
    feasible_originals = [rule for rule in originals_by_id.values() if rule.status == "feasible"]
    errors = validate_original_rule_definitions(catalogue, originals_by_id)
    merge_errors, pending = validate_merged_rule_definitions(catalogue, originals_by_id, feasible_originals)
    errors.extend(merge_errors)
    pending.extend(find_potential_rule_overlaps(catalogue, originals_by_id))
    if originals_by_id:
        errors.extend(validate_feasible_rule_coverage(catalogue.rules, feasible_originals))
    else:
        pending.append("original_combinations_not_supplied")
    pending.extend(find_unresolved_condition_combinations(catalogue, originals_by_id))
    return {"errors": errors, "pending": pending,
            "feasible_rule_ids": [rule.id for rule in feasible_originals],
            "infeasible_rule_ids": [rule.id for rule in originals_by_id.values() if rule.status == "infeasible"],
            "unresolved_rule_ids": [rule.id for rule in originals_by_id.values() if rule.status == "unresolved"]}


def collect_declared_coverage(records, obligation_ids, feasible_original_ids):
    """Keep labels from surviving inputs separate from mechanically checked facts."""
    declared_ids, unknown_ids, unlabelled_inputs = set(), set(), 0
    known_ids = obligation_ids | feasible_original_ids
    for record in records:
        covers = record.get("covers")
        if covers is None:
            unlabelled_inputs += 1
            continue
        declared_ids.update(set(covers) & known_ids)
        unknown_ids.update(set(covers) - known_ids)
    return declared_ids, unknown_ids, unlabelled_inputs


def measure_equivalence_classes(classes, arguments):
    """Infer class membership only from explicit members or numeric intervals."""
    measurements = []
    for equivalence_class in classes:
        matched_input_indices = []
        explicit_membership = (
            equivalence_class.members is not None
            or equivalence_class.lower is not None
            or equivalence_class.upper is not None)
        checkable = equivalence_class.parameter is not None and explicit_membership
        for index, input_arguments in enumerate(arguments):
            value, extracted = selected_value(equivalence_class, input_arguments)
            if not checkable or not extracted:
                continue
            if equivalence_class.members is not None:
                belongs_to_class = value in equivalence_class.members
            else:
                belongs_to_class = interval_contains(equivalence_class, value)
            if belongs_to_class:
                matched_input_indices.append(index)
        measurements.append({"id": equivalence_class.id,
            "mechanical_status": "checked" if checkable else "pending",
            "input_indices": matched_input_indices})
    return measurements


def measure_original_rule_coverage(catalogue, declared_ids, feasible_original_ids):
    """A merged label never credits every original combination it represents."""
    if not catalogue.rules:
        return {"status": "not_applicable", "covered": None, "total": None}
    if catalogue.original_rules:
        return {"status": "declared", "covered": len(declared_ids & feasible_original_ids),
                "total": len(feasible_original_ids)}
    # Without merge metadata, each fully specified rule can itself be original.
    has_merged_rules = any(rule.merged_from or "-" in rule.conditions.values() for rule in catalogue.rules)
    if has_merged_rules:
        return {"status": "pending", "covered": None, "total": None}
    rule_ids = {rule.id for rule in catalogue.rules}
    return {"status": "declared", "covered": len(declared_ids & rule_ids), "total": len(catalogue.rules)}


def measure_strong_ep_coverage(catalogue, records, class_measurements):
    """One input can credit one cross-partition combination at most."""
    partitions = defaultdict(list)
    for equivalence_class in catalogue.classes:
        if equivalence_class.partition and equivalence_class.kind == "input":
            partitions[equivalence_class.partition].append(equivalence_class.id)
    if not partitions:
        return None
    total_combinations = math.prod(len(group) for group in partitions.values())
    covered_combinations, conflicting_inputs = set(), []
    for index, record in enumerate(records):
        covered_classes = set(record.get("covers") or [])
        choices = [covered_classes.intersection(group) for group in partitions.values()]
        if any(len(choice) > 1 for choice in choices):
            conflicting_inputs.append(index)
            continue
        if not all(len(choice) == 1 for choice in choices):
            continue
        selected_classes = tuple(next(iter(choice)) for choice in choices)
        membership_conflict = any(
            row["mechanical_status"] == "checked" and index not in row["input_indices"]
            for row in class_measurements if row["id"] in selected_classes)
        if membership_conflict:
            conflicting_inputs.append(index)
        else:
            covered_combinations.add(selected_classes)
    return {"covered": len(covered_combinations), "total_cartesian": total_combinations,
            "feasibility": "pending", "conflicting_input_indices": conflicting_inputs,
            "coverage_basis": "self_reported"}


def measure_worst_case_coverage(catalogue, arguments):
    """Count observed boundary-coordinate tuples without materializing the product."""
    if not catalogue.boundaries:
        return None
    choices = []
    nominal_values_available = []
    for boundary in catalogue.boundaries:
        targets = boundary_targets(boundary)
        nominal_value, extracted = selected_value(boundary, boundary.nominal) if boundary.nominal else (None, False)
        if boundary.nominal and extracted:
            targets.append(nominal_value)
        choices.append(list(dict.fromkeys(targets)))
        nominal_values_available.append(bool(boundary.nominal and extracted))
    if not all(choices) or not all(nominal_values_available):
        return None
    observed_combinations = set()
    for input_arguments in arguments:
        coordinates = [selected_value(boundary, input_arguments) for boundary in catalogue.boundaries]
        coordinates_within_choices = all(
            extracted and value in options
            for (value, extracted), options in zip(coordinates, choices))
        contexts_match = all(matches_context(input_arguments, boundary.context) for boundary in catalogue.boundaries)
        if coordinates_within_choices and contexts_match:
            observed_combinations.add(tuple(value for value, extracted in coordinates))
    return {"covered": len(observed_combinations), "total_cartesian": math.prod(map(len, choices)),
            "feasibility": "pending"}


def count_uncovered_boundary_values(boundary_measurements):
    """A total is pending until every supplied boundary has a checked missing list."""
    if not boundary_measurements:
        return None
    uncovered_count = 0
    for boundary in boundary_measurements:
        missing_values = boundary["missing_values"]
        if missing_values is None:
            return None
        uncovered_count += len(missing_values)
    return uncovered_count


def measure_catalogue(batch, task, valid_indices, *, arm_name, input_budget):
    """Measure only arm-local inputs accepted by the twice-run reference."""
    raw = batch.get("catalogue")
    if raw is None or batch.get("catalogue_status") in ("off", "catalogue_invalid"):
        return {"status": batch.get("catalogue_status", batch.get("status", "pending")),
                "errors": batch.get("catalogue_errors", []), "semantic_audit": "pending"}
    catalogue = Catalogue.model_validate(raw)
    builder = CallBuilder.for_source(task["prompt"], task["entry_point"])
    valid_index_set = set(valid_indices)
    records = [record for index, record in enumerate(batch["inputs"]) if index in valid_index_set]
    arguments = [bound_arguments(builder, record) for record in records]
    obligation_ids = set()
    for section in (catalogue.classes, catalogue.boundaries, catalogue.rules):
        obligation_ids.update(item.id for item in section)
    feasible_original_ids = {rule.id for rule in catalogue.original_rules if rule.status == "feasible"}
    declared_ids, unknown_ids, unlabelled_inputs = collect_declared_coverage(
        records, obligation_ids, feasible_original_ids)
    class_measurements = measure_equivalence_classes(catalogue.classes, arguments)
    boundary_measurements = mechanical_boundaries(catalogue, arguments,
        robust=arm_name == "bva_robust", worst_case=arm_name == "bva_worst_case")
    decision_table_measurement = decision_table_check(catalogue)
    table_coverage = measure_original_rule_coverage(catalogue, declared_ids, feasible_original_ids)
    uncovered_boundary_values = count_uncovered_boundary_values(boundary_measurements)
    strong_coverage = measure_strong_ep_coverage(catalogue, records, class_measurements) if arm_name == "ep_strong" else None
    worst_case_coverage = measure_worst_case_coverage(catalogue, arguments) if arm_name == "bva_worst_case" else None
    cartesian_total = (strong_coverage or worst_case_coverage or {}).get("total_cartesian")
    normal_size = None
    if boundary_measurements and arm_name != "bva_worst_case":
        normal_size = normal_design_size(catalogue, robust=arm_name == "bva_robust")
    # Coverage gaps alone do not prove the budget caused them.
    required_size = cartesian_total if cartesian_total is not None else normal_size
    budget_limited = required_size > input_budget if required_size is not None else None
    return {"status": catalogue.status, "valid_input_records": len(records), "declared": {
                "covered_ids": sorted(declared_ids & obligation_ids), "total_obligations": len(obligation_ids),
                "status": "pending" if unlabelled_inputs else "self_reported", "unlabelled_inputs": unlabelled_inputs,
                "unknown_cover_ids": sorted(unknown_ids)},
            "classes": class_measurements, "boundaries": boundary_measurements,
            "decision_table": decision_table_measurement,
            "original_rule_coverage": table_coverage, "strong_ep": strong_coverage, "worst_case": worst_case_coverage,
            "normal_design": {"required_inputs": normal_size, "status": "declared_coordinates_only" if normal_size is not None else "pending"},
            "base_call_coverage": "pending", "coverage_scope": "novel_reference_valid_inputs_only",
            "budget_limited": budget_limited,
            "uncovered_boundary_values": uncovered_boundary_values if boundary_measurements else None,
            "partition_disjointness_and_exhaustiveness": "pending", "semantic_audit": "pending"}
