"""Dependency-free explicit budgets, shared by CLI and Prefect."""
import copy
import math

TOOL_ARMS = ('tool_direct', 'tool_hypothesis', 'tool_hypothesis_extra', 'tool_planner')
INTEGER_BUDGETS = ('draws', 'extra_draws', 'planner_rows', 'planner_draws', 'audit_cap')
TIME_BUDGETS = ('sample_seconds', 'extra_seconds', 'planner_seconds')

def validate_budgets(config):
    required = set(INTEGER_BUDGETS + TIME_BUDGETS) | {'arms', 'random_seeds'}
    if not isinstance(config, dict) or set(config) != required:
        raise ValueError('Tool config requires exactly: ' + ','.join(sorted(required)))
    for key in INTEGER_BUDGETS:
        if type(config[key]) is not int or not 1 <= config[key] <= 100000:
            raise ValueError(key + ': explicit positive integer required (<=100000)')
    for key in TIME_BUDGETS:
        if type(config[key]) not in (int, float) or not math.isfinite(config[key]) or not 0 < config[key] <= 3600:
            raise ValueError(key + ': finite seconds required in (0,3600]')
    arms = config['arms']
    if (not isinstance(arms, list) or not arms or any(name not in TOOL_ARMS for name in arms)
            or len(arms) != len(set(arms))):
        raise ValueError('Unknown/duplicate tool arms')
    seeds = config['random_seeds']
    if (not isinstance(seeds, list) or not seeds or len(seeds) > 1000
            or any(type(seed) is not int or not 0 <= seed < 2**32 for seed in seeds)
            or len(seeds) != len(set(seeds))):
        raise ValueError('Nonempty distinct random_seeds required')
    return copy.deepcopy(config)
