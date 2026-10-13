"""Development utility: freeze Hypothesis's original draw-worker source constants.

This reads source ASTs, never imports the originals or instantiates their clients.
Run with the dedicated interpreter. The snapshot prevents package/path refactoring
from changing Hypothesis's automatically mined 'local' string/integer examples.
"""
import json
from pathlib import Path
from .paths import HERE, REPO

MODULES = ('v4_worker', 'preconditions', 'gen_inputs', 'precond_prompts', 'llm_client',
           'v4_runtime', 'tracer', 'v4_strategies', 'v4_prompts', 'gen_prompts', 'prompts')


def main():
    from hypothesis.internal.constants_ast import Constants, _constants_from_source
    constants = Constants()
    for name in MODULES:
        constants |= _constants_from_source((REPO / 'trickcatcher_linefacts' / (name+'.py')).read_bytes(), limit=True)
    values = {kind: list(constants.set_for_type(kind)) for kind in ('integer', 'float', 'string', 'bytes')}
    values['bytes'] = [v.hex() for v in values['bytes']]
    (HERE / 'hypothesis_constants.json').write_text(json.dumps(dict(modules=MODULES, values=values), indent=2)+'\n')
    print('Frozen local constants:', {k:len(v) for k,v in values.items()})


if __name__ == '__main__': main()
