"""Authored CPU positive controls ONLY. Online preparation never imports this module."""


def authored_contract(case):
    uid = case['fixture_id']
    if uid == 'f13':
        return {'state': 'valid', 'value': {'decision': 'unknown', 'spec_quote': '', 'domain': 'Lists of integers',
                                           'relation': '', 'uncertainty': 'Suitable is undefined', 'predicate_source': ''}}
    if uid in ('f01', 'f02', 'f14', 'f15'):
        expression = 'type(value) is list and all(type(x) is int for x in value) and value == sorted(arguments["xs"])'
    elif uid in ('f03', 'f04'):
        expression = 'type(value) is int and value == sum(1 for x in arguments["xs"] if x >= arguments["limit"])'
    else:
        expression = 'type(value) is bool and value == all(x in arguments["container"] for x in arguments["required"])'
    source = ('def obligation(arguments, observation):\n'
              '    if observation["status"] != "ok":\n'
              '        return False\n'
              '    value = observation["value"]\n'
              '    return ' + expression + '\n')
    return {'state': 'valid', 'value': {'decision': 'proposed', 'spec_quote': 'CPU control only',
                                       'domain': 'Original authored fixture domain', 'relation': 'CPU full relation',
                                       'uncertainty': '', 'predicate_source': source}}
