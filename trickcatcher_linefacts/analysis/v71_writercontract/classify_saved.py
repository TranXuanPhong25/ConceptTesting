"""Read-only contract classification of frozen v70 answers; no native/model calls."""
import hashlib,json
from pathlib import Path
from trickcatcher_linefacts.pipelines.v71_writercontract.writer_compiler import compile_response
from trickcatcher_linefacts.pipelines.v71_writercontract.pipeline import source_identity

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
ORIGIN=REPO/'trickcatcher_linefacts/analysis/v70_domainwriter'

def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    current=read(ORIGIN/'CURRENT_RUN.json');root=Path(current['run_root']);requests=read(root/'preparation/requests.json')
    freeze=read(root/'generation/prepare_frozen.json')
    for rel,h in freeze.items():assert sha(root/'generation'/rel)==h
    sources=source_identity();rows=[]
    for req in requests:
        response_path=root/'generation'/req['case_id']/'shared_writer/response.json';response=read(response_path)
        hypotheses,rejected,compilation=compile_response(req,response)
        rows.append({'case_id':req['case_id'],'original_sha256':sha(response_path),'admitted':len(hypotheses),
                     'rejected':rejected,'compilation':compilation})
    assert source_identity()==sources
    result={'rows':rows,'sources':sources,'original_frozen_entries':len(freeze),'new_model_calls':0,'native_calls':0,
            'invalid_contracts':sum(r['compilation']['response_contract']['status']=='invalid'for r in rows),
            'explicit_abstentions':sum(r['compilation']['response_contract']['explicit_abstention']for r in rows),
            'raw_responses_repaired':False}
    with(HERE/'saved_contract_classification.json').open('x')as f:json.dump(result,f,indent=2)
    print(json.dumps({k:v for k,v in result.items()if k not in('rows','sources')}))

if __name__=='__main__':main()
