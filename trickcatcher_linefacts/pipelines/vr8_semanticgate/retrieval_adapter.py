"""Bind unchanged v2 cards to v11 execution targets using public source sites only."""
from copy import deepcopy
import json
from python_bug_concepts.retrieval_v2.engine import search
from python_bug_concepts.retrieval_v3.prompts import compact
from . import facts


def adapt(task, pool, db):
    packet = search(code=task['put'], top_k=3, db=db)
    if packet['warning']:
        raise ValueError('retrieval source parse failed')
    ranked = facts.pick([f for f in pool if f['kind'] != 'SPEC'], task['task'], k=len(pool))
    selected, audit, used = [], [], set()
    for hit in packet['results']:
        card = hit['concept']
        evidence = hit['evidence'][0] if hit['evidence'] else None
        if evidence is None:
            audit.append(dict(concept_id=card['id'], status='no_executable_site'))
            continue
        line, end = evidence['line'], evidence.get('end_line', evidence['line'])
        bound = next((f for f in ranked if line <= f.get('line', -1) <= end
                      and json.dumps(f, sort_keys=True) not in used), None)
        if bound is not None:
            used.add(json.dumps(bound, sort_keys=True))
            target, gate = deepcopy(bound), 'existing_v11_gap'
        else:
            # shortcut: line reachability is weaker than the card trigger; report it separately, never call it semantic verification.
            target = dict(kind='STMT', line=line, lines=[line], witness_call=None,
                          text=f'Execute source line {line}; this does not establish the hypothesized bug trigger.')
            gate = 'line_reachability_only'
        target.update(card_id=card['id'], card=compact(card), retrieval_evidence=evidence,
                      retrieval_gate=gate, tool_target_text=target['text'])
        target['text'] = json.dumps(compact(card), ensure_ascii=False) + '\n  Tool target: ' + target['tool_target_text']
        selected.append(target)
        audit.append(dict(concept_id=card['id'], line=line, status=gate, target_kind=target['kind']))
    result = deepcopy(task)
    result.update(retrieval_method='v2_compact_site_bound', concept_meta=selected,
                  concept_facts=[f['text'] for f in selected],
                  tool_inputs=list(dict.fromkeys(f['witness_call'] for f in selected if f.get('witness_call'))))
    return result, audit
