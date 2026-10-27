"""Generic duplicate recovery and Qwen/structural interleaving, without gold access."""
from __future__ import annotations
import copy
import hashlib
from pathlib import Path
from ..retrieval_v3.client import Client
from ..retrieval_v3.prompts import BY_ID, baseline, parse_retrieval, retrieval


def parse_recovered(response, code):
    rows, error = parse_retrieval(response, code)
    if error != 'duplicate_concept':
        return rows, error, False
    revised = copy.deepcopy(response)
    unique, seen = [], set()
    for row in revised['parsed']['selected']:
        cid = row.get('id') if isinstance(row, dict) else None
        if cid in seen:
            continue
        seen.add(cid)
        unique.append(row)
    revised['parsed']['selected'] = unique
    rows, error = parse_retrieval(revised, code)
    return rows, error, error is None


def interleave(qwen, structural):
    result, seen = [], set()
    for i in range(3):
        for name, rows in [('qwen',qwen),('v2',structural)]:
            if i < len(rows) and rows[i]['concept_id'] not in seen:
                row = rows[i]
                seen.add(row['concept_id'])
                result.append({**row, 'origin':name,'origin_rank':i+1})
    return result[:3]


def retrieve(code: str, *, out: Path | None = None, response: dict | None = None, client: Client | None = None):
    """Supply cached response for offline use; live mode requires explicit out/env."""
    if response is None:
        if out is None:
            raise ValueError('Live retrieval requires an explicit cache directory')
        client = client or Client(out)
        client.preflight()
        seed = int(hashlib.sha256(code.encode()).hexdigest()[:7],16)
        response = client.complete(retrieval({'code':code}),stage='retrieve',max_tokens=1200,seed=seed)
    qwen, error, recovered = parse_recovered(response,code)
    rows = interleave(qwen,baseline({'code':code}))
    return {'results':[{'rank':i,'concept':BY_ID[row['concept_id']], 'instantiated':{k:row[k] for k in ['line','where','how','what']}, 'origin':row['origin'], 'origin_rank':row['origin_rank'],'status':'unverified_fault_hypothesis'} for i,row in enumerate(rows,1)],'qwen_schema_error':error,'duplicate_recovered':recovered,'model_response_status':response.get('status'),'request_sha256':response.get('request_sha256'),'usage':response.get('usage',{}),'evaluation_status':'post_hoc_development_informed; native utility not measured for this fusion'}

if __name__=='__main__':
    import argparse,json
    p=argparse.ArgumentParser()
    p.add_argument('--code',type=Path,required=True)
    p.add_argument('--cached-response',type=Path)
    p.add_argument('--out',type=Path)
    args=p.parse_args()
    response=json.loads(args.cached_response.read_text()) if args.cached_response else None
    if response is not None and 'response' in response:
        response=response['response']
    print(json.dumps(retrieve(args.code.read_text(),out=args.out,response=response),ensure_ascii=False,indent=2))
