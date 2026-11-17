"""Public-spec type metadata where HumanEval annotations omit input types.

Types only: value bounds and joint preconditions remain in the trusted contracts.
Do not narrow List[Any], generic lists, or unrestricted dictionary keys/values.
"""
import ast
from functools import lru_cache

# Parameter order follows the public entry declaration; no PUT/reference outcomes.
SPEC_INPUT_TYPES = {
    30: ('list[float]',), 31: ('int',), 32: ('list[float]',),
    40: ('list[int]',), 42: ('list[float]',), 43: ('list[int]',),
    45: ('float', 'float'), 47: ('list[float]',), 51: ('str',),
    52: ('list[float]', 'int'), 62: ('list[float]',),
    64: ('str',), 65: ('int', 'int'), 66: ('str',), 67: ('str', 'int'),
    68: ('list[int]',), 69: ('list[int]',), 70: ('list[int]',),
    71: ('float', 'float', 'float'), 72: ('list[float]', 'float'),
    73: ('list[int]',), 74: ('list[str]', 'list[str]'), 75: ('int',),
    76: ('int', 'int'), 77: ('int',), 78: ('str',), 79: ('int',),
    80: ('str',), 81: ('list[float]',), 82: ('str',), 83: ('int',),
    84: ('int',), 85: ('list[int]',), 86: ('str',),
    87: ('list[list[Any]]', 'int'), 88: ('list[int]',), 89: ('str',),
    90: ('list[int]',), 91: ('str',), 92: ('float', 'float', 'float'),
    93: ('str',), 94: ('list[int]',), 95: ('dict[Any, Any]',),
    96: ('int',), 97: ('int', 'int'), 98: ('str',), 99: ('str',),
    100: ('int',), 101: ('str',), 102: ('float', 'float'),
    103: ('int', 'int'), 104: ('list[int]',), 105: ('list[int]',),
    106: ('int',), 107: ('int',), 108: ('list[int]',), 109: ('list[int]',),
    110: ('list[float]', 'list[float]'), 111: ('str',), 112: ('str', 'str'),
    113: ('list[str]',), 114: ('list[int]',), 115: ('list[list[int]]', 'int'),
    116: ('list[int]',), 117: ('str', 'int'), 118: ('str',), 119: ('list[str]',),
    120: ('list[int]', 'int'), 121: ('list[int]',), 122: ('list[int]', 'int'),
    123: ('int',), 124: ('str',), 125: ('str',), 126: ('list[int]',),
    127: ('tuple[int, int] | list[int]', 'tuple[int, int] | list[int]'),
    128: ('list[int]',), 129: ('list[list[int]]', 'int'), 130: ('int',),
    131: ('int',), 132: ('str',), 133: ('list[float]',), 134: ('str',),
    135: ('list',), 136: ('list',), 137: ('int | float | str', 'int | float | str'),
    138: ('int',), 139: ('int',), 140: ('str',), 141: ('str',), 142: ('list[int]',),
    143: ('str',), 144: ('str', 'str'), 145: ('list[int]',), 146: ('list[float]',),
    147: ('int',), 148: ('str', 'str'), 149: ('list[str]',),
    150: ('int', 'Any', 'Any'), 151: ('list[float]',),
    152: ('list[float]', 'list[float]'), 153: ('str', 'list[str]'),
    154: ('str', 'str'), 155: ('int',), 156: ('int',),
    157: ('float', 'float', 'float'), 158: ('list[str]',),
    159: ('int', 'int', 'int'), 160: ('list[str]', 'list[int]'),
    161: ('str',), 162: ('str',), 163: ('int', 'int'),
}


@lru_cache(maxsize=1)
def specification_types():
    from .datasets import load_tasks
    result = {}
    for task in load_tasks():
        types = SPEC_INPUT_TYPES.get(int(task['task_id'].split('/')[1]))
        if types is None:
            continue
        function = next(node for node in ast.parse(task['prompt']).body
                        if isinstance(node, ast.FunctionDef) and node.name == task['entry_point'])
        parameters = function.args.posonlyargs + function.args.args + function.args.kwonlyargs
        if len(parameters) != len(types):
            raise ValueError('Input type metadata does not match public signature: ' + task['task_id'])
        result[(task['prompt'], task['entry_point'])] = dict(zip((arg.arg for arg in parameters), types))
    return result


def input_types_for_source(source, entry_point):
    # Exact public spec identity prevents applying benchmark metadata to unrelated fixtures/PUTs.
    return specification_types().get((source, entry_point), {}).copy()
