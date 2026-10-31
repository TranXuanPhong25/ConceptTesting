"""Frozen source-only prototype evaluation; no target/reference execution."""
import argparse
import hashlib
import json
import platform
import sqlite3
from pathlib import Path
from .retriever import ARMS,search,HERE

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')


def relation_labels(relations,instances):
    by_id={x['id']:x for x in instances}
    return [dict(subject_kind=by_id.get(x['subject'],{}).get('kind'),
                 subject_expression=by_id.get(x['subject'],{}).get('evidence',{}).get('expression'),
                 predicate=x['predicate'],object_kind=by_id.get(x['object'],{}).get('kind'),
                 object_expression=by_id.get(x['object'],{}).get('evidence',{}).get('expression'),
                 evidence=[e['expression'] for e in x['evidence']]) for x in relations]


def verify():
    manifest=json.loads((HERE/'FREEZE.json').read_text())
    for name,h in manifest['files'].items():
        if sha(HERE/name)!=h:raise ValueError('frozen_file_changed: '+name)
    approval=json.loads((HERE/'REVIEW_APPROVAL.json').read_text())
    if approval['freeze_sha256']!=sha(HERE/'FREEZE.json') or approval['status']!='approved':
        raise ValueError('review_not_approved_for_frozen_source')


def run():
    verify();out=HERE/'evaluation'
    out.mkdir(exist_ok=False)
    fixtures=json.loads((HERE/'fixtures.json').read_text())
    census=json.loads((HERE/'census_inputs.json').read_text())
    predictions={group:{arm:[] for arm in ARMS} for group in ('fixtures','census')}
    for group,inputs in [('fixtures',fixtures),('census',census)]:
        for arm in ARMS:
            for x in inputs:
                try:result=search(x['source'],x['entry'],arm)
                except (ValueError,SyntaxError,RecursionError) as exc:
                    result=dict(error=type(exc).__name__,message=str(exc)[:200],instances=[],bindings=[],candidates=[])
                predictions[group][arm].append(dict(id=x['id'],result=result))
    save(out/'PREDICTIONS.json',predictions)
    save(out/'PREDICTION_SEAL.json',dict(sha256=sha(out/'PREDICTIONS.json')))
    labels={x['id']:x['expected'] for x in fixtures}
    results={}
    for arm,rows in predictions['fixtures'].items():
        expected=candidate_hits=bound_hits=false_bindings=slot_errors=extracted=extraction_errors=0
        expected_relations=exact_relations=relation_errors=0
        details=[]
        for row in rows:
            gold={r['kind']:r for r in labels[row['id']]};r=row['result'];expected+=len(gold)
            candidates={x['template_id'].removeprefix('concept.') for x in r['candidates']}
            expected_relations+=sum(len(x['relations']) for x in gold.values())
            candidate_hits+=len(candidates&set(gold))
            correct=set()
            for instance in r['instances']:
                extracted+=1
                actual={k:v['evidence']['expression'] for k,v in instance['slots'].items()}
                extraction_errors+=instance['kind'] not in gold or actual!=gold[instance['kind']]['slots']
            for binding in r['bindings']:
                kind=binding['template_id'].removeprefix('concept.')
                actual={k:v['evidence']['expression'] for k,v in binding['slots'].items()}
                relations=relation_labels(binding['relations'],r['instances'])
                expected_edges=gold.get(kind,{}).get('relations',[])
                edge_match=relations==expected_edges
                relation_errors+=not edge_match
                if edge_match:exact_relations+=len(relations)
                if kind not in gold:false_bindings+=1
                elif actual!=gold[kind]['slots']:slot_errors+=1
                elif edge_match:correct.add(kind)
            bound_hits+=len(correct)
            details.append(dict(id=row['id'],expected=sorted(gold),candidates=sorted(candidates),exact_bound=sorted(correct),error=r.get('error')))
        results[arm]=dict(expected_instances=expected,candidate_hits=candidate_hits,exact_bound_hits=bound_hits,
            false_bindings=false_bindings,slot_errors=slot_errors,extracted=extracted,extraction_errors=extraction_errors,
            expected_relations=expected_relations,exact_bound_relations=exact_relations,
            missing_or_incorrect_relations=expected_relations-exact_relations,relation_errors=relation_errors,details=details)
    coverage={}
    for arm,rows in predictions['census'].items():
        coverage[arm]=dict(tasks=len(rows),errors=[x['id'] for x in rows if 'error' in x['result']],
            with_instances=sum(bool(x['result']['instances']) for x in rows),
            with_bindings=sum(bool(x['result']['bindings']) for x in rows),
            instances=sum(len(x['result']['instances']) for x in rows),bindings=sum(len(x['result']['bindings']) for x in rows),
            truncated_queries=sum(x['result'].get('omitted_query_characters',0)>0 for x in rows),
            unknown_records=sum(len(x['result'].get('unknown',[])) for x in rows))
    verify()
    save(out/'RESULTS.json',dict(engineering_fixtures=results,unlabeled_census=coverage,
        runtime=dict(python=platform.python_version(),sqlite=sqlite3.sqlite_version),model_calls=0,
        target_executions=0,canonical_used=False,generalization_claim=False))
    save(out/'COMPLETE.json',dict(fixtures=len(fixtures),census=len(census),prediction_sha256=sha(out/'PREDICTIONS.json'),results_sha256=sha(out/'RESULTS.json')))
    print(json.dumps(dict(fixtures={k:{a:b for a,b in v.items() if a!='details'} for k,v in results.items()},census=coverage),indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['check','run']);args=parser.parse_args()
    if args.command=='check':verify();print('VR14 source/review integrity pass')
    else:run()
