"""Serializable, unit-explicit benchmark configurations and offline budget previews."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
COHORTS = {
    'humaneval164': 'final/out/cohorts/qwen35_27b_humaneval164/cohort.json',
    'known_bug10': 'final/out/development_groups/boundary/known_bug_10/cohort.json',
}
DEFAULTS = {'cohort': 'humaneval164', 'mode': 'batch', 'arms': ['direct', 'soft_bva'],
    'task_numbers': [], 'inputs_per_task': 20, 'completion_tokens': 2048, 'context_tokens': 8192,
    'temperature': .7, 'input_seed': 314159, 'reference_seed': 271828, 'timeout_seconds': 3.0,
    'per_put_base_examples': 12, 'scorer': 'confirm_first_failures', 'model_name': 'qwen3.5-27b-awq'}


def normalize(values):
    if set(values) - set(DEFAULTS):
        raise ValueError('Unknown config fields: '+', '.join(sorted(set(values)-set(DEFAULTS))))
    config = {**DEFAULTS, **values}
    config['arms'] = list(config['arms'])
    config['task_numbers'] = list(config['task_numbers'])
    if config['cohort'] not in COHORTS or config['mode'] not in ('batch', 'per_put'):
        raise ValueError('Unknown cohort or mode')
    allowed = ('direct', 'soft_bva') if config['mode'] == 'batch' else ('boundary',)
    if not config['arms'] or len(set(config['arms'])) != len(config['arms']) or set(config['arms']) - set(allowed):
        raise ValueError('Batch arms: direct/soft_bva; per_put arm: boundary')
    if len(set(config['task_numbers'])) != len(config['task_numbers']) or any(type(n) is not int or not 0<=n<164 for n in config['task_numbers']):
        raise ValueError('Task numbers must be unique integers from0to163')
    limits = {'inputs_per_task': (1, 200), 'completion_tokens': (128, 32768),
              'context_tokens': (512, 131072), 'input_seed': (0, 2147483483),
              'reference_seed': (0, 2147483483), 'per_put_base_examples': (1, 300)}
    for key, (lower, upper) in limits.items():
        if type(config[key]) is not int or not lower <= config[key] <= upper:
            raise ValueError(f'{key} must be an integer in[{lower},{upper}]')
    for key, lower, upper in [('temperature', 0, 2), ('timeout_seconds', .1, 60)]:
        if type(config[key]) not in (int, float) or not math.isfinite(config[key]) or not lower<=config[key]<=upper:
            raise ValueError(f'{key} outside allowed range')
    if config['completion_tokens']+128>=config['context_tokens']:
        raise ValueError('Completion reserve must leave prompt context')
    if config['scorer'] not in ('confirm_first_failures', 'full_two_repeats'):
        raise ValueError('Unknown scorer')
    if not isinstance(config['model_name'], str) or not config['model_name'].strip() or len(config['model_name'])>120:
        raise ValueError('Invalid served model name')
    config['task_numbers'].sort()
    return config


def load_cohort(config):
    path = ROOT / COHORTS[config['cohort']]
    cohort = json.loads(path.read_text())
    expected = hashlib.sha256(json.dumps(cohort['tasks'], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    if cohort['cohort_sha256'] != expected:
        raise ValueError('Cohort checksum differs')
    return path, cohort


def preview(values):
    config = normalize(values)
    path, cohort = load_cohort(config)
    available = {int(row['task_id'].split('/')[-1]): row for row in cohort['tasks']}
    selected = config['task_numbers'] or sorted(available)
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
            logical[arm] += 1 if config['mode']=='batch' else min(passing, config['inputs_per_task'])
        if config['mode']=='per_put':
            allocated=min(passing,config['inputs_per_task']); quotient,remainder=divmod(config['inputs_per_task'],allocated)
            quotas[quotient]+=allocated-remainder
            if remainder:quotas[quotient+1]+=remainder
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
        'context_note':'Actual visibility is jointly tokenized before each task; completion count may be lower on context overflow.'}
