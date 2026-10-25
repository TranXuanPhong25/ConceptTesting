"""Read-only diagnostic provenance audit; no model, native or private-label calls."""
import hashlib,json
from pathlib import Path
from trickcatcher_linefacts.pipelines.v72_diagnosisprobe.diagnosis_probe import identity,messages,summarize
from trickcatcher_linefacts.pipelines.v72_diagnosisprobe.pipeline import load_checkpoint
from trickcatcher_linefacts.pipelines.v72_diagnosisprobe.ngrok_run import digest

HERE=Path(__file__).resolve().parent

def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    current=read(HERE/'CURRENT_RUN.json');out=Path(current['out']);requests=Path(current['requests'])
    plan=load_checkpoint(out/'plan.json');summary=load_checkpoint(out/'summary.json');freeze=load_checkpoint(out/'frozen.json')
    assert plan==read(HERE/'PLAN_FROZEN.json')and sha(out/'plan.json')==read(HERE/'PLAN_FROZEN.sha256.json')['sha256']
    assert identity(requests)==plan['identity']
    for rel,digest_ in freeze.items():assert sha(out/rel)==digest_
    jobs=plan['jobs'];known_in=0;known_out=0;dispatches=0;responses=0
    assert len(jobs)==4 and [(j['case_id'],j['arm'])for j in jobs]==[('85','raw_known'),('85','full_known'),('124','full_known'),('124','raw_known')]
    hashes=[]
    for job,row in zip(jobs,summary['rows'],strict=True):
        req=next(r for r in plan['requests']if r['case_id']==job['case_id'])
        assert messages(req,job['arm'])==job['messages']
        folder=out/job['case_id']/job['arm'];request=read(folder/'request.json');response=read(folder/'response.json')
        expected={'messages':job['messages'],'stage':job['arm'],'seed':job['seed'],'max_tokens':job['max_tokens'],
                  'model':plan['metadata']['model'],'provider':'ngrok'}
        assert request==expected and response['request_sha256']==digest(request)
        hashes.append(response['request_sha256'])
        assert row==load_checkpoint(folder/'assessment.json')
        assert row['assessment']==summarize(req,job['arm'],response)
        token=read(folder/'tokenization.json');assert token==job['tokenization']
        attempts=list(folder.glob('attempt_[0-9][0-9].json'));assert len(attempts)<=2
        dispatches+=len(attempts)
        for attempt in attempts:
            assert read(attempt)['request_sha256']==response['request_sha256']
            receipt=attempt.with_name(attempt.stem+'_result.json')
            if receipt.exists()and read(receipt).get('status')=='received':
                actual=read(receipt)['response'];responses+=1
                known_in+=actual.get('input_tokens')or 0;known_out+=actual.get('output_tokens')or 0
                assert actual.get('input_tokens')==job['tokenization']['count']
    assert len(set(hashes))==4 and dispatches==summary['actual_dispatches']<=8 and responses==summary['received_responses']
    assert known_in==summary['known_input_tokens']and known_out==summary['known_output_tokens']
    result={'integrity':'PASS','owner_readonly_audit':True,'frozen_entries':len(freeze),'requests':len(jobs),
            'actual_dispatches':dispatches,'received_responses':responses,'known_input_tokens':known_in,'known_output_tokens':known_out,
            'historical_reused':2,'audit_model_or_native_calls':0,'private_labels_read':0,'independent_agent_review':False}
    target=HERE/'terminal_audit.json'
    if target.exists():assert read(target)==result
    else:
        with target.open('x')as f:json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
