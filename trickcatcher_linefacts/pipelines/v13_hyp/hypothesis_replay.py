"""Pin the local constant pool that seeded the v4c draw worker.

Hypothesis 6.169.0 mines literals from imported local Python source. Packaging
adds orchestration literals, which otherwise changes draws despite equal seeds.
The pinned pool is extracted from source ASTs, with no original module imports.
"""
import json
from .paths import HERE, CONFIG


def freeze_local_constants():
    if not CONFIG.get('freeze_hypothesis_constants', True): return
    from hypothesis.internal.constants_ast import Constants
    from hypothesis.internal.conjecture import providers
    values = json.loads((HERE / 'hypothesis_constants.json').read_text())['values']
    from sortedcontainers import SortedSet
    from hypothesis.internal.floats import float_to_int
    constants = Constants(integers=SortedSet(), floats=SortedSet(key=float_to_int),
                          strings=SortedSet(), bytes=SortedSet())
    for kind, items in values.items():
        for value in items:
            constants.add(bytes.fromhex(value) if kind == 'bytes' else value)
    providers.CONSTANTS_CACHE.cache.clear()
    providers._get_local_constants = lambda: constants
