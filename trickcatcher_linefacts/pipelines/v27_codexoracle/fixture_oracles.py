"""Evaluator-only spec oracles for authored diagnostic fixtures. Never prompt material."""
from .chain_inputs import parse_arguments, typed_value


def expected(case, literal):
    args = parse_arguments(literal, {'required': 1 if case['fixture_id'] not in
                                     ('f03', 'f04', 'f05', 'f06', 'f11', 'f12') else 2,
                                     'positional': 1 if case['fixture_id'] not in
                                     ('f03', 'f04', 'f05', 'f06', 'f11', 'f12') else 2,
                                     'varargs': False, 'required_keyword_only': False})
    uid = case['fixture_id']
    if uid == 'f13':
        return None  # undefined "suitable": no invented expected result
    if uid in ('f01', 'f02', 'f14', 'f15'):
        value = sorted(args[0])
    elif uid in ('f03', 'f04'):
        value = sum(x >= args[1] for x in args[0])
    elif uid in ('f05', 'f06'):
        value = set(args[1]) <= set(args[0])
    elif uid in ('f07', 'f08'):
        value = min((x for x in args[0] if x > 0), default=None)
    elif uid in ('f09', 'f10'):
        value = all(x % 2 == 0 for x in args[0])
    elif uid in ('f11', 'f12'):
        value = sum(args[0]) <= args[1]
    elif uid == 'f16':
        value = sum(x for x in args[0] if x > 0)
    else:
        raise ValueError('unknown_fixture')
    return ('ok', typed_value(value))
