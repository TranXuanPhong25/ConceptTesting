"""Read-only diagnosis of existing v2; no new retrieval method or PUT execution."""
import hashlib,json
from pathlib import Path
from ...retrieval_v2.engine import structural_evidence,search
HERE=Path(__file__).resolve().parent
OLD=HERE.parents[1]/'retrieval_v2/evaluation'

def main():
    inputs=json.loads((OLD/'inputs.json').read_text())
    gold=json.loads((OLD/'gold.json').read_text())['tasks']
    sites=json.loads((OLD/'mechanism_sites.json').read_text())['tasks']
    metrics={str(k):{'family_hits':0,'family_first_selected_site_hits':0} for k in [1,3,5,10,100]}
    records=[]
    for task in inputs:
        tid=task['task_id'];evidence,_,_,warning=structural_evidence(task['code'])
        ranked=search(code=task['code'],top_k=100)['results']
        expected=set(gold[tid]['concept_ids'])
        def lines(cid):return {s['line'] for s in sites.get(tid,{}).get(cid,[])}
        family=bool(expected.intersection(evidence))
        any_site=any(any(e['line'] in lines(cid) for e in evidence.get(cid,[])) for cid in expected)
        for k,row in metrics.items():
            selected=ranked[:int(k)]
            row['family_hits']+=any(r['concept']['id'] in expected for r in selected)
            row['family_first_selected_site_hits']+=any(r['concept']['id'] in expected and r['evidence'] and r['evidence'][0]['line'] in lines(r['concept']['id']) for r in selected)
        records.append({'task_id':tid,'labeled':bool(expected),'ast_parsed':warning is None,'any_eligible_gold_family':family,'any_raw_evidence_matches_gold_site':any_site,'eligible_count':len(evidence),'raw_evidence_sites':sum(map(len,evidence.values()))})
    result={'kind':'existing_engine_diagnostic_only','new_model_calls':0,'put_executions':0,'input_hashes':{n:hashlib.sha256((OLD/n).read_bytes()).hexdigest() for n in ['inputs.json','gold.json','mechanism_sites.json']},'tasks':len(inputs),'labeled_tasks':sum(r['labeled'] for r in records),'ast_parsed':sum(r['ast_parsed'] for r in records),'top_k':metrics,'any_eligible_gold_family':sum(r['any_eligible_gold_family'] for r in records),'any_raw_evidence_matches_gold_site':sum(r['any_raw_evidence_matches_gold_site'] for r in records),'limits':['Incomplete single-author labels; 22 unlabeled tasks cannot be classified from these counts.','Any-site metrics are retrospective oracle ceilings, not achievable retrieval performance.','The all-card first-site metric still fixes each concept to its highest-priority site.'],'records':records}
    (HERE/'DIAGNOSTIC.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='records'},indent=2))
if __name__=='__main__':main()
