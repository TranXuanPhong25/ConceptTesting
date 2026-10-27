"""Post-freeze engineering evaluation; target receives only source code."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from .engine import search
from ..retrieval_v2.evaluate import binding_score,check_gold_freeze,score

HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'retrieval_v2/evaluation'
OUT=HERE/'evaluation_v5'
FILES=['engine.py','baseline_engine.py','facts.py','applicability.py','corpus.py','requirements.txt','scoped_tests.py','evaluate.py']

def fingerprint():
    return {name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in FILES}

def freeze():
    check_gold_freeze()
    if OUT.exists() and (OUT/'FREEZE.json').exists():raise ValueError('A freeze already exists; preserve this evaluation')
    OUT.mkdir(exist_ok=True)
    manifest={'implementation':fingerprint(),'inputs':{name:hashlib.sha256((BASE/name).read_bytes()).hexdigest() for name in ['inputs.json','gold.json','mechanism_sites.json','development.json','audit.json']},'status':'pre_outcome_freeze','labels':'unchanged, single-author, development-informed; no fresh heldout'}
    (OUT/'FREEZE.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest

def evaluate():
    manifest=json.loads((OUT/'FREEZE.json').read_text())
    if manifest['implementation']!=fingerprint():raise ValueError('Implementation changed since freeze')
    for name,sha in manifest['inputs'].items():
        if hashlib.sha256((BASE/name).read_bytes()).hexdigest()!=sha:raise ValueError('Frozen input changed')
    if (OUT/'RESULTS.json').exists():raise ValueError('Scores already exist; preserve outcomes, do not silently retune')
    inputs=json.loads((BASE/'inputs.json').read_text())
    # Generate source-only retrieval packets first; labels join only afterwards.
    packets={task['task_id']:search(code=task['code'],top_k=3,include_facts=False) for task in inputs}
    gold=json.loads((BASE/'gold.json').read_text())['tasks']
    sites=json.loads((BASE/'mechanism_sites.json').read_text())['tasks']
    old={row['task_id']:row for split in ['development','audit'] for row in json.loads((BASE/f'{split}.json').read_text())['tasks']}
    records=[]
    for task in inputs:
        tid=task['task_id'];packet=packets[tid];hits=packet['results']
        ids=[h['concept']['id'] for h in hits];accepted=gold[tid]['concept_ids']
        rows=[{'concept_id':h['concept']['id'],'line':h['evidence'][0]['line'] if h['evidence'] else None,'frozen_family_match':h['concept']['id'] in accepted,'instantiated':h.get('instantiated'),'evidence':h['evidence']} for h in hits]
        records.append({'task_id':tid,'split':task['split'],'warning':packet['warning'],'labeled':bool(accepted),'baseline':old[tid]['systems']['structural_v2'],
                        'v5':{**score(ids,accepted),**binding_score(hits,sites.get(tid,{})),'returned':len(hits),'label_matching_cards':sum(r['frozen_family_match'] for r in rows),'selected':rows,'excluded_bindings':packet.get('excluded_bindings',[])}})
    def summary(rows):
        n=len(rows);returned=sum(r['v5']['returned'] for r in rows)
        return {'tasks':n,'v2_family_hit_at_3':sum(r['baseline']['hit_at_3'] for r in rows),'v5_family_hit_at_3':sum(r['v5']['hit_at_3'] for r in rows),'v2_first_site_hit_at_3':sum(r['baseline']['first_site_hit_at_3'] for r in rows),'v5_first_site_hit_at_3':sum(r['v5']['first_site_hit_at_3'] for r in rows),'v5_any3_site_hit_at_3':sum(r['v5']['any_site_hit_at_3'] for r in rows),'returned_cards':returned,'frozen_label_match_rate':sum(r['v5']['label_matching_cards'] for r in rows)/returned if returned else None,'scoped_backend_fallbacks':sum(bool(r['warning']) for r in rows),'site_win_tasks':[r['task_id'] for r in rows if r['v5']['first_site_hit_at_3'] and not r['baseline']['first_site_hit_at_3']],'site_loss_tasks':[r['task_id'] for r in rows if r['baseline']['first_site_hit_at_3'] and not r['v5']['first_site_hit_at_3']]}
    result={'summary':summary(records),'splits':{s:summary([r for r in records if r['split']==s]) for s in ['development','audit']},'limits':['Frozen labels incomplete; label match rate is not actual bug precision.','All source was previously inspected; not an independent holdout.','No new same-model grading, native utility, or paid inference.','Guard exclusions depend on recorded builtin/type/public-domain assumptions.'],'records':records,'freeze':manifest}
    (OUT/'RESULTS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['freeze','evaluate']);args=p.parse_args()
    result=freeze() if args.command=='freeze' else evaluate()
    print(json.dumps(result if args.command=='freeze' else result['summary'],indent=2))
