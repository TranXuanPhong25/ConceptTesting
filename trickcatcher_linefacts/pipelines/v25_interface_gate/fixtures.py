"""Seen authored diagnostic only; normative banks never enter Qwen contexts."""
import copy
import itertools

from hypothesis import given, settings, seed, strategies as st, Phase

from . import pilot_fixtures
from .binding import from_literal
from .common import D, base_inputs, digest, task_for, typed_value

IDS = ('f02', 'f04', 'f06', 'f14', 'f13')


def cases():
    available = {c['fixture_id']: c for c in pilot_fixtures.cases()}
    return [copy.deepcopy(available[x]) for x in IDS]


def expected(case, arguments):
    """Authored independent evaluator; never model expected-output or predicate replacement."""
    uid = case['fixture_id']
    if uid == 'f13':
        return None
    if uid in ('f01', 'f02', 'f14', 'f15'):
        value = sorted(arguments['xs'])
    elif uid in ('f03', 'f04'):
        value = sum(x >= arguments['limit'] for x in arguments['xs'])
    elif uid in ('f05', 'f06'):
        value = set(arguments['required']) <= set(arguments['container'])
    else:
        raise ValueError('unknown_authored_fixture')
    return {'status': 'ok', 'value': value}


def same_observation(a, b):
    return a is not None and b is not None and typed_value(a) == typed_value(b)


def semantic_bank(case):
    if case['fixture_id'] == 'f13':
        return []
    lists = [list(x) for n in range(3) for x in itertools.product((-1, 0, 1), repeat=n)]
    task = task_for(case)
    names = task['parameter_ids']
    options = [(-1, 0, 1) if name == 'limit' else lists for name in names]
    result = []
    for combination in itertools.product(*options):
        args = {name: copy.deepcopy(value) for name, value in zip(names, combination)}
        required = expected(case, args)
        actual = required['value']
        candidates = [required, {'status': 'exception', 'exception_type': 'ValueError'}]
        for value in (None, False, True, 0, 1, -1, 0.0, 1.0, -1.0, [], 'wrong'):
            candidates.append({'status': 'ok', 'value': value})
        if type(actual) is list:
            for value in (list(reversed(actual)), list(dict.fromkeys(actual)), actual + [2], actual[:-1]):
                candidates.append({'status': 'ok', 'value': value})
            for index, item in enumerate(actual):
                for replacement in (float(item), bool(item)):
                    wrong_type = list(actual); wrong_type[index] = replacement
                    candidates.append({'status': 'ok', 'value': wrong_type})
        elif type(actual) is int:
            candidates += [{'status': 'ok', 'value': actual + 1}, {'status': 'ok', 'value': actual - 1}]
        seen = set()
        for candidate in candidates:
            key = digest(candidate)
            if key in seen:
                continue
            seen.add(key)
            result.append({'arguments': args, 'observation': candidate,
                           'expected': same_observation(candidate, required)})
    if len(result) > D['max_predicate_rows']:
        raise ValueError('semantic_bank_cap')
    return result


def discovery_pool(case):
    """Only public argument types shape this Hypothesis strategy, not fault/spec/gold."""
    task = task_for(case)
    bases = [from_literal(task, x) for x in base_inputs(case)]
    first = bases[0]
    strategies = {}
    for name, value in first.items():
        if type(value) is list and all(type(x) is int for x in value):
            strategies[name] = st.lists(st.integers(-2, 3), max_size=4)
        elif type(value) is int:
            strategies[name] = st.integers(-2, 3)
        else:
            raise ValueError('unsupported_public_argument_type')
    selected, seen = [], set()
    @seed(D['seed'] + int(case['fixture_id'][1:]))
    @settings(max_examples=D['pool_examples'], database=None, deadline=None, phases=(Phase.generate,))
    @given(st.fixed_dictionaries(strategies))
    def collect(arguments):
        key = digest(arguments)
        if key not in seen and len(selected) < D['pool_size']:
            seen.add(key)
            selected.append(arguments)
    collect()
    if len(selected) != D['pool_size']:
        raise ValueError('insufficient_unique_frozen_pool')
    merged = list(selected)
    for args in bases:
        if digest(args) not in {digest(x) for x in merged}:
            merged.append(args)
    return {'pool': selected, 'public_base_inputs': bases, 'all_inputs': merged,
            'scope': '24 fixed type-only Hypothesis draws plus public bases; no fault/witness/gold selection'}
