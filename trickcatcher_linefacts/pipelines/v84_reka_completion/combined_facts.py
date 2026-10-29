"""Prospective v7/v31 merge; concrete witness metadata never becomes concept text."""
from copy import deepcopy
from . import facts, ft_concepts


def fault_facts(groups, candidates, outputs, mutant_outputs, entry):
    result = []
    for g in groups:
        if not g['distinguished']:
            continue
        indices = sorted({i for xs in g['killed'].values() for i in xs})
        if not indices:
            continue
        i = indices[0]
        args = candidates[i]['args']
        alternatives = list(dict.fromkeys(f"`{m['before']}` -> `{m['after']}`" for m in g['survivors']))
        text = (f"Fault-type adequacy at L{g['line']}: {ft_concepts.TYPE_TEXT[g['type']]}. "
                f"Behaviour: `{g['code']}`. The public tests do not distinguish "
                f"{len(g['survivors'])} surviving alternatives ({'; '.join(alternatives[:3])}). "
                "Exercise this behaviour and determine the required result from the specification.")
        result.append(dict(kind='FAULT',line=g['line'],fault_type=g['type'],text=text,
                           survivors=len(g['survivors']),distinguished=g['distinguished'],
                           alternatives=alternatives,alternative_sources=[m['mutant_src'] for m in g['survivors']],
                           reached=True,witness_call=entry+'('+', '.join(map(repr,args))+')',
                           block=g['line'],witness=i))
    return result


def merge(task, full_facts, fault_pool, template_inputs, *, enabled=True):
    if not enabled:
        return deepcopy(task)
    v7 = [f for f in full_facts if f['kind'] not in ('MUTANT','MUTANT-X')]
    standard = [f for f in v7 if f['kind'] != 'SPEC']
    ordered = facts.pick(standard, task['task'], k=len(standard))
    ordered += [f for f in v7 if f['kind']=='SPEC' and f.get('reached',True)]
    ranked = sorted(fault_pool,key=lambda f:(-f['distinguished'],-f['survivors'],ft_concepts.PRIORITY[f['fault_type']],f['line']))
    queues = [ordered[:],ranked[:]]
    selected, lines = [], set()
    while len(selected)<3 and any(queues):
        for queue in queues:
            while queue and queue[0].get('line') is not None and queue[0]['line'] in lines:
                queue.pop(0)
            if queue and len(selected)<3:
                f=queue.pop(0); selected.append(f)
                if f.get('line') is not None: lines.add(f['line'])
    result=deepcopy(task)
    calls=list(task['tool_inputs'])
    for f in full_facts:
        if f.get('witness_call'): calls.append(f['witness_call'])
    for args in template_inputs:
        calls.append(task['entry']+'('+', '.join(map(repr,args))+')')
    result.update(concept_meta=selected,concept_facts=[f['text'] for f in selected],
                  tool_inputs=list(dict.fromkeys(calls)))
    return result
