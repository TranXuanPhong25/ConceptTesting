"""CPU-only B5 fuzz witnesses and additive v7 top-three hint selection."""
import ast
import copy
import functools
import json
import random
from . import behaviour, facts, preconditions
from .tracer import alarm, dcopy


@functools.lru_cache(maxsize=2048)
def domain(code):
    # Only called from workers; never execute mined code in the orchestrator.
    return preconditions.load_predicate(code, 'D')


def input_hit(fact, inputs, valid):
    """A BEHAV hit depends on B5 validity and D, never on PUT execution or R."""
    if inputs is None or valid is None:
        return False
    args, kwargs = inputs
    try:
        with alarm(1):
            accepted = valid(*dcopy(args), **dcopy(kwargs)) is True if callable(valid) else valid is True
        if not accepted:
            return False
        with alarm(1):
            return domain(fact['D_src'])(*dcopy(args), **dcopy(kwargs)) is True
    except BaseException:
        return False


def emit(requirements, base, fuzz, valid, entry):
    """Witness is the first matching input in facts.py's unchanged fuzz ordering."""
    result = []
    for r in requirements:
        D = domain(r['D_src'])
        covered, bad = False, False
        for args, kwargs in base:
            try:
                with alarm(1): value = D(*dcopy(args), **dcopy(kwargs))
                if type(value) is not bool: bad = True; break
                covered |= value
            except BaseException:
                bad = True; break
        if bad or covered:
            continue
        for index, inputs in enumerate(fuzz):
            if input_hit(r, inputs, valid):
                result.append(dict(r, kind='BEHAV', reached=True, witness=index,
                    witness_repr=repr(inputs), witness_call=facts.call_src(entry, inputs),
                    block='BEHAV:' + r['id'], tier=0,
                    text=f'Specification requirement (behaviour): {r["statement"]} ("{r["quote"]}"). '
                         'No existing test uses an input where this matters.'))
                break
    return result


def build(task, requirements):
    if preconditions.sha(task['mined_valid_src']) != task['valid_sha256']:
        raise ValueError('B5 validator hash mismatch')
    base = [inputs for inputs, _ in behaviour.base_pairs(task)]
    valid = preconditions.load_predicate(task['mined_valid_src'], 'valid')

    def check(_task, inputs):
        try:
            with alarm(1):
                return valid(*dcopy(inputs[0]), **dcopy(inputs[1])) is True
        except BaseException:
            return False

    # Replay facts.main's pool exactly, including PUT constants, seed, caps, and B5 gate.
    facts.CONSTS[:] = sorted({n.value for n in ast.walk(ast.parse(task['put'])) if isinstance(n, ast.Constant)
        and isinstance(n.value, (int, float)) and not isinstance(n.value, bool)
        and abs(n.value) < 10 ** 6} - {0, 1, -1})[:12]
    stats = {}
    fuzz = facts.fuzz_inputs(base, random.Random(facts.SEED + task['task']), check, task['task'], stats)
    stats['validator'] = 'mined'
    return dict(task=task['task'], valid_sha256=task['valid_sha256'], n_base=len(base),
                n_fuzz=len(fuzz), fuzz_validity=stats,
                fuzz_sha256=preconditions.sha(repr(fuzz)),
                requirements_sha256=preconditions.sha(json.dumps(requirements, sort_keys=True)),
                facts=emit(requirements, base, fuzz, valid, task['entry']))


def select(v7_top, behaviour_facts, task_id):
    if not behaviour_facts:
        return copy.deepcopy(v7_top)
    pool = copy.deepcopy(v7_top + behaviour_facts)
    for i, f in enumerate(pool):
        # v7's SPEC fallback did not pass through code-block ranking.
        if f['kind'] == 'SPEC':
            f.setdefault('block', 'SPEC:' + str(i))
            f.setdefault('reached', True)
    return facts.pick(pool, task_id, extra_slots=('SPEC', 'BEHAV'))


def augment(task, emitted):
    old = copy.deepcopy(task['concept_meta'])
    top = select(old, emitted, task['task'])
    task.update(v7_concept_meta=old, behav_pool=emitted, concept_meta=top,
                concept_facts=[f['text'] for f in top])
    if top != old:
        task['tool_inputs'] = list(dict.fromkeys(f['witness_call'] for f in top if f.get('witness_call')))
