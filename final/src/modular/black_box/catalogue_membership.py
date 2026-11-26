"""Observed input membership, separate from declarations and spec correctness."""
import time

from .catalogue import effective_boundary_context, selected_value, interval_contains, matches_context
from ..common.membership import membership_row, membership_summary
from ..tool_sampling.membership import evaluate, expression

MAX_PREDICATE_CHECKS = 2048
MAX_MEMBERSHIP_SECONDS = 5


def boolean_condition(value):
    if type(value) is bool:
        return value
    if type(value) is str and value in ('T','True','true','F','False','false'):
        return value in ('T','True','true')
    return None


def predicate_supported(text, names):
    try:
        expression(text, names)
    except (ValueError, SyntaxError, TypeError, RecursionError):
        return False
    return True


def measure_membership(catalogue, arguments, records, source_indices, boundary_measurements, parameter_names):
    started = time.monotonic()
    checks = 0
    cache = {}

    def predicate_result(text, index):
        nonlocal checks
        if not text:
            return None, 'missing_predicate'
        key = (text, index)
        if key not in cache:
            if checks >= MAX_PREDICATE_CHECKS or time.monotonic() - started >= MAX_MEMBERSHIP_SECONDS:
                return None, 'membership_budget_exhausted'
            checks += 1
            try:
                cache[key] = evaluate(text, dict(arguments[index])), None
            except (ValueError, TypeError, SyntaxError, ArithmeticError, LookupError,
                    AttributeError, RecursionError, OSError) as error:
                cache[key] = None, type(error).__name__ + ':' + str(error)[:200]
        return cache[key]

    classes = []
    for item in catalogue.classes:
        outcomes = []
        if item.predicate is not None:
            checkable = predicate_supported(item.predicate, parameter_names)
        else:
            checkable = item.kind == 'input' and item.parameter in parameter_names and (
                item.members is not None or item.lower is not None or item.upper is not None)
        for index, values in enumerate(arguments):
            if item.predicate is not None:
                outcomes.append(predicate_result(item.predicate, index))
            elif checkable:
                value, extracted = selected_value(item, values)
                belongs = value in item.members if item.members is not None else interval_contains(item, value)
                outcomes.append((belongs, None) if extracted else (None, 'selector_unavailable'))
            else:
                outcomes.append((None, 'missing_membership_definition'))
        classes.append(membership_row(item.id, outcomes, source_indices, checkable=checkable))

    boundaries = []
    for item, mechanical in zip(catalogue.boundaries, boundary_measurements):
        targets = []
        boundary_context = effective_boundary_context(item)
        checkable = item.parameter in parameter_names and mechanical['numeric_targets_status'] == 'checked'
        for target in mechanical['targets']:
            outcomes = []
            for values in arguments:
                value, extracted = selected_value(item, values)
                if not checkable or not extracted or not set(boundary_context) <= set(values):
                    outcomes.append((None, 'boundary_selector_or_targets_unavailable'))
                else:
                    outcomes.append((matches_context(values, boundary_context) and value == target, None))
            row = membership_row(item.id, outcomes, source_indices, checkable=checkable)
            targets.append({**row, 'value':target})
        # Each target value is an obligation. A single hit cannot cover the whole boundary.
        statuses = [row['status'] for row in targets]
        status = 'hit' if statuses and all(value == 'hit' for value in statuses) else (
            'miss' if 'miss' in statuses else 'unknown')
        per_input = []
        for index in range(len(arguments)):
            values = [row['input_statuses'][index] for row in targets]
            per_input.append('hit' if 'hit' in values else 'unknown' if not values or 'unknown' in values else 'miss')
        witnesses = sorted({index for row in targets for index in row['input_indices']})
        boundaries.append({'id':item.id, 'status':status, 'targets':targets,
            'criterion':'boundary_values_in_context', 'single_fault':mechanical['single_fault'],
            'input_indices':witnesses,'source_input_indices':[source_indices[index] for index in witnesses],
            'input_statuses':per_input})

    def measure_rule(rule):
        outcomes = []
        required = {name:value for name, value in rule.conditions.items() if value != '-'}
        checkable = bool(required) and all(boolean_condition(value) is not None and
            predicate_supported(catalogue.condition_predicates.get(name), parameter_names)
            for name, value in required.items())
        for index in range(len(arguments)):
            results = []
            for name, expected in required.items():
                wanted = boolean_condition(expected)
                if wanted is None:
                    results.append((None, 'unsupported_condition_value:' + name))
                    continue
                actual, error = predicate_result(catalogue.condition_predicates.get(name), index)
                results.append((None if actual is None else actual == wanted, error))
            # A false condition proves a miss even if another condition is unknown.
            if any(value is False for value, _ in results):
                outcomes.append((False, None))
            elif any(value is None for value, _ in results):
                outcomes.append((None, next(error for value, error in results if value is None)))
            elif results or rule.conditions:
                outcomes.append((True, None))  # An all-wildcard merged rule matches any valid input.
            else:
                outcomes.append((None, 'missing_rule_conditions'))
        return membership_row(rule.id, outcomes, source_indices, checkable=checkable)

    rules = [measure_rule(rule) for rule in catalogue.rules]
    original_definitions = catalogue.original_rules
    original_basis = 'declared_feasible_originals'
    if not original_definitions:
        original_basis = 'unmerged_rules'
        if any(rule.merged_from or '-' in rule.conditions.values() for rule in catalogue.rules):
            original_basis = 'unknown'
        else:
            original_definitions = catalogue.rules
    originals = [measure_rule(rule) for rule in original_definitions if getattr(rule,'status','feasible') == 'feasible']
    conditions = [membership_row(name,[predicate_result(text,index) for index in range(len(arguments))],
                                source_indices,checkable=predicate_supported(text,parameter_names))
                  for name,text in catalogue.condition_predicates.items()]

    by_id = {row['id']:row for row in classes + boundaries + rules + originals}
    label_checks = []
    for index, record in enumerate(records):
        declared = set(record.get('covers') or [])
        actual = {identifier for identifier, row in by_id.items() if row['input_statuses'][index] == 'hit'}
        false = sorted(identifier for identifier in declared if identifier in by_id and
                       by_id[identifier]['input_statuses'][index] == 'miss')
        unknown = sorted(identifier for identifier in declared if identifier not in by_id or
                         by_id[identifier]['input_statuses'][index] == 'unknown')
        label_checks.append({'input_index':index,'source_input_index':source_indices[index],
            'false_cover_ids':false,'unknown_cover_ids':unknown,'undeclared_hit_ids':sorted(actual - declared)})
    original_summary = membership_summary(originals) if original_basis != 'unknown' else {
        'total':None,'hit':None,'miss':None,'unknown':None}
    return {'protocol':'catalogue-membership-v1','coverage_scope':'novel_reference_valid_inputs_only',
            'input_source_indices':source_indices,'classes':classes,'boundaries':boundaries,'conditions':conditions,
        'rules':rules,'original_rules':originals,'original_rule_basis':original_basis,
        'summary':{'classes':membership_summary(classes),'boundaries':membership_summary(boundaries),
                   'original_rules':original_summary},
        'label_checks':label_checks,'semantic_grounding':'pending',
        'budget':{'predicate_checks':checks,'max_predicate_checks':MAX_PREDICATE_CHECKS,
                  'max_membership_seconds':MAX_MEMBERSHIP_SECONDS}}
