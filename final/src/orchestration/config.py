"""Serializable, unit-explicit benchmark configurations and offline budget previews."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
from pathlib import Path
from final.src.modular.arm_names import CATALOGUE_ARM_NAMES, ANALYSIS_CALL_CAPS

ROOT = Path(__file__).resolve().parents[3]
COHORTS = {
    'humaneval164': 'final/out/cohorts/qwen35_27b_humaneval164/cohort.json',
    'known_bug10': 'final/out/development_groups/boundary/known_bug_10/cohort.json',
    'boundary_smoke': 'final/out/development_groups/boundary/smoke/cohort.json',
    'equivalence_smoke': 'final/out/development_groups/equivalence/smoke/cohort.json',
}
DEFAULTS = {'cohort': 'humaneval164', 'mode': 'batch', 'arms': ['direct', 'soft_bva'],
    'task_numbers': [], 'inputs_per_task': 20, 'completion_tokens': 4096, 'context_tokens': 8192,
    'temperature': .7, 'input_seed': 314159, 'reference_seed': 271828, 'timeout_seconds': 8.0,
    'per_put_base_examples': 12, 'scorer': 'confirm_first_failures', 'model_name': 'qwen3.5-27b-awq',
    'catalogue': True}


def normalize(values):
    """Resolve defaults, validate each config concern, then normalize task order."""
    validate_config_field_names(values)
    config = {**DEFAULTS, **values}
    config['arms'] = list(config['arms'])
    config['task_numbers'] = list(config['task_numbers'])

    validate_cohort_and_generation_mode(config)
    validate_arm_selection(config)
    # The catalogue switch is a strict boolean; strings such as "false" are invalid.
    if type(config['catalogue']) is not bool:
        raise ValueError('catalogue must be a boolean')
    validate_task_number_selection(config['task_numbers'])
    validate_generation_budgets(config)
    validate_scorer_and_served_model(config)

    config['task_numbers'].sort()
    return config


def validate_config_field_names(values):
    """Reject unknown fields, including credentials that must stay outside config."""
    unknown_fields = set(values) - set(DEFAULTS)
    if unknown_fields:
        raise ValueError('Unknown config fields: ' + ', '.join(sorted(unknown_fields)))


def validate_cohort_and_generation_mode(config):
    """Only named frozen cohorts and the batch/per-PUT generation modes exist."""
    if config['cohort'] not in COHORTS or config['mode'] not in ('batch', 'per_put'):
        raise ValueError('Unknown cohort or mode')


def validate_arm_selection(config):
    """Require distinct arms supported by the selected generation mode."""
    if config['mode'] == 'batch':
        allowed_arms = ('plain', 'direct', 'soft_bva', *CATALOGUE_ARM_NAMES, *ANALYSIS_CALL_CAPS)
    else:
        allowed_arms = ('boundary',)

    selected_arms = config['arms']
    has_duplicate_arms = len(set(selected_arms)) != len(selected_arms)
    has_unknown_arms = bool(set(selected_arms) - set(allowed_arms))
    if not selected_arms or has_duplicate_arms or has_unknown_arms:
        raise ValueError('Unknown or duplicate batch arm; per_put accepts boundary only')


def validate_task_number_selection(task_numbers):
    """HumanEval task IDs must be distinct integers in the frozen 0..163 range."""
    has_duplicate_tasks = len(set(task_numbers)) != len(task_numbers)
    has_invalid_task = any(type(number) is not int or not 0 <= number < 164 for number in task_numbers)
    if has_duplicate_tasks or has_invalid_task:
        raise ValueError('Task numbers must be unique integers from0to163')


def validate_generation_budgets(config):
    """Check numeric limits and leave room for a prompt after completion reserve."""
    integer_limits = {
        'inputs_per_task': (1, 200),
        'completion_tokens': (128, 32768),
        'context_tokens': (512, 131072),
        'input_seed': (0, 2147483483),
        'reference_seed': (0, 2147483483),
        'per_put_base_examples': (1, 300),
    }
    for field_name, (lower, upper) in integer_limits.items():
        value = config[field_name]
        # Exact int checks prevent booleans from silently becoming budgets/seeds.
        if type(value) is not int or not lower <= value <= upper:
            raise ValueError(f'{field_name} must be an integer in[{lower},{upper}]')

    finite_number_limits = [('temperature', 0, 2), ('timeout_seconds', .1, 60)]
    for field_name, lower, upper in finite_number_limits:
        value = config[field_name]
        if type(value) not in (int, float) or not math.isfinite(value) or not lower <= value <= upper:
            raise ValueError(f'{field_name} outside allowed range')

    # Completion tokens plus the safety reserve must not consume the whole context.
    if config['completion_tokens'] + 128 >= config['context_tokens']:
        raise ValueError('Completion reserve must leave prompt context')


def validate_scorer_and_served_model(config):
    """Require a supported repeat policy and a nonempty bounded model identifier."""
    if config['scorer'] not in ('confirm_first_failures', 'full_two_repeats'):
        raise ValueError('Unknown scorer')
    model_name = config['model_name']
    if not isinstance(model_name, str) or not model_name.strip() or len(model_name) > 120:
        raise ValueError('Invalid served model name')


def load_cohort(config):
    path = ROOT / COHORTS[config['cohort']]
    cohort = json.loads(path.read_text())
    expected = hashlib.sha256(json.dumps(cohort['tasks'], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    # Validate the frozen cohort contents before deriving any run budget.
    if cohort['cohort_sha256'] != expected:
        raise ValueError('Cohort checksum differs')
    return path, cohort


def preview(values):
    config = normalize(values)
    path, cohort = load_cohort(config)
    available = {int(row['task_id'].split('/')[-1]): row for row in cohort['tasks']}
    selected = config['task_numbers'] or sorted(available)
    # Validate task membership in this cohort, beyond the global HumanEval ID range.
    if set(selected)-set(available):
        raise ValueError('Selected tasks are absent from cohort')
    target_count = cohort.get('development_selection', {}).get('target_programs', 10)
    eligible, skipped, quotas = [], [], Counter()
    logical = {arm: 0 for arm in config['arms']}
    for number in selected:
        row = available[number]
        passing = sum(program['base']['status']=='pass' for program in row['programs'])
        reason = 'generation_shortfall' if row['generated']!=target_count else 'no_base_pass' if not passing else None
        if reason:
            skipped.append({'task_id':row['task_id'],'reason':reason})
            continue
        eligible.append({'task_id':row['task_id'],'base_pass_put_count':passing})
        for arm in logical:
            logical[arm] += ANALYSIS_CALL_CAPS.get(arm, 1) if config['mode']=='batch' else min(passing, config['inputs_per_task'])
        if config['mode']=='per_put':
            allocated=min(passing,config['inputs_per_task']); quotient,remainder=divmod(config['inputs_per_task'],allocated)
            quotas[quotient]+=allocated-remainder
            if remainder:quotas[quotient+1]+=remainder
    # A preview requires at least one task with the expected PUT count and a base pass.
    if not eligible:
        raise ValueError('No eligible tasks for selected config')
    return {'config':config,'cohort_path':str(path),'cohort_sha256':cohort['cohort_sha256'],
        'target_program_count':target_count,'selected_task_numbers':selected,
        'requested_task_count':len(selected),'eligible_task_count':len(eligible),
        'evaluated_base_pass_put_count':sum(row['base_pass_put_count'] for row in eligible),
        'logical_calls_by_arm':logical,'logical_call_cap':sum(logical.values()),
        'max_input_slots_per_arm':len(eligible)*config['inputs_per_task'],
        'input_budget_unit':'per task per arm','per_put_generation_quota_histogram':dict(sorted(quotas.items())),
        'eligible_tasks':eligible,'skips':skipped,
        'base_context':'original base tests' if config['mode']=='batch' else f"at most{config['per_put_base_examples']}base calls per PUT",
        'parser':'shared named-arguments parser' if config['mode']=='batch' else 'strict per-PUT soft-BVA parser',
        'completion_token_cap_per_call':config['completion_tokens'],
        'completion_token_cap_total':sum(logical.values())*config['completion_tokens'],
        'catalogue_note':'Coverage đo sau freeze/domain/reference; prose chưa audit là pending. Robust cần spec eligibility; call cap là upper bound.',
        'context_note':'Actual visibility is jointly tokenized before each task; completion count may be lower on context overflow.'}
