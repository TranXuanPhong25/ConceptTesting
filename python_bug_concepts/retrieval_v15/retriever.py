"""One fixed BM25 query followed by the same slot binder in all arms."""
import json
from pathlib import Path
from .instances import extract
from .lexical import Lexical,tokens

HERE=Path(__file__).resolve().parent
ARMS=('raw','concepts','relations','direct')
COMPOSITES={'search_position_indexing','transform_then_filter','distinct_cardinality'}
CAP=3
QUERY_CHARS=2048


def query_text(source,packet,arm):
    if arm not in ARMS:raise ValueError('unknown query arm')
    if arm=='raw':text=source
    else:
        parts=[]
        by_id={x['id']:x for x in packet['instances']}
        for instance in packet['instances']:
            if arm=='concepts' and instance['kind'] in COMPOSITES:continue
            parts += [instance['kind'].replace('_',' '),*instance['properties']]
            parts += [f"{role} {slot['type']}" for role,slot in instance['slots'].items()]
            if arm in ('relations','direct'):
                for relation in instance['relations']:
                    parent=by_id.get(relation['subject'])
                    parts.append(' '.join([parent['kind'] if parent else 'unknown producer',relation['predicate'],instance['kind']]).replace('_',' '))
        parts += [f"public requirement cue {c['property']} {c['value']} unverified" for c in packet['requirement']['cues']]
        text='\n'.join(parts)
    return text[:QUERY_CHARS],max(0,len(text)-QUERY_CHARS)


def bind(template,instance):
    if template['kind']!=instance['kind']:return None
    if any(role not in instance['slots'] or instance['slots'][role]['type']!=typ for role,typ in template['slots'].items()):return None
    if not set(template['relations'])<={r['predicate'] for r in instance['relations']}:return None
    return dict(template_id=template['id'],instance_id=instance['id'],slots=instance['slots'],
                relations=instance['relations'],assumptions=instance['assumptions'],
                domain_evidence=instance['domain_evidence'],source_chain=instance.get('source_chain',[]),
                partitions=[dict(p,bindings={k:v['evidence']['expression'] for k,v in instance['slots'].items()},
                                 status='planned_not_executed',realized=None) for p in template['partitions']],
                status='source_bound_conditional',bug_verdict='not_inferred')


def search(source,entry=None,arm='relations'):
    packet=extract(source,entry)
    templates=json.loads((HERE/'templates.json').read_text())
    documents={t['id']:' '.join([t['title'],t['description'],*t['slots'],*t['relations']]) for t in templates}
    text,omitted=query_text(source,packet,arm)
    if arm=='direct':
        kinds={i['kind'] for i in packet['instances']}
        matched=[t for t in templates if t['kind'] in kinds]
        matched.sort(key=lambda t:(-len(t['relations']),t['kind']=='cardinality',t['id']))
        ranking=[(t['id'],None) for t in matched[:CAP]]
    else:
        index=Lexical(documents)
        try:ranking=index.ranking(text)[:CAP]
        finally:index.close()
    by_id={t['id']:t for t in templates};candidates=[];bindings=[]
    for tid,score in ranking:
        bound=[b for i in packet['instances'] if (b:=bind(by_id[tid],i)) is not None]
        candidates.append(dict(template_id=tid,bm25_score=score,bound_instances=len(bound)))
        bindings+=bound
    return dict(version='vr15_concept_compositions',arm=arm,backend='direct kind routing' if arm=='direct' else 'SQLite FTS5 BM25',
                candidate_cap=CAP,query=text,omitted_query_characters=omitted,
                query_used_for_ranking=arm!='direct',
                omitted_query_terms=max(0,len(set(tokens(text)))-128) if arm!='direct' else 0,
                **packet,candidates=candidates,bindings=bindings)
