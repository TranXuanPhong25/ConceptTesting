"""Read-only streaming/cost/provenance audit, no new paid/native calls."""
from decimal import Decimal
import hashlib,json
from pathlib import Path
from trickcatcher_linefacts.pipelines.v73_ossdiagnosis.pipeline import load_checkpoint
from trickcatcher_linefacts.pipelines.v73_ossdiagnosis.oss_probe import identity
from trickcatcher_linefacts.pipelines.v73_ossdiagnosis.openrouter_stream import parse_sse,known_cost,reservation
from trickcatcher_linefacts.pipelines.v73_ossdiagnosis.ngrok_run import digest

HERE=Path(__file__).resolve().parent

def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    current=read(HERE/'CURRENT_RUN.json');out=Path(current['out']);plan=load_checkpoint(out/'plan.json')
    assert identity()==plan['identity']
    assert sha(HERE/'endpoints_before_run.json')==plan['endpoints_sha256']
    assert plan==read(HERE/'PLAN_FROZEN.json')and sha(out/'plan.json')==read(HERE/'PLAN_FROZEN.sha256.json')['sha256']
    freeze=load_checkpoint(out/'frozen.json');summary=load_checkpoint(out/'summary.json')
    for rel,h in freeze.items():assert sha(out/rel)==h
    qroot=Path(plan['historical_qwen_root']);assert sha(qroot/'frozen.json')==plan['historical_freeze_sha256']
    qplan=load_checkpoint(qroot/'plan.json')
    assert sum(Decimal(j['worstcase_usd'])for j in plan['jobs'])<=Decimal(plan['run_cap_usd'])<=Decimal('0.02')
    costs=Decimal(0);providers=[];tokens_in=0;tokens_out=0;reasoning=0;paid_attempts=0;rows=[]
    for job,qjob in zip(plan['jobs'],qplan['jobs'],strict=True):
        assert job['request']['messages']==qjob['messages']
        folder=out/job['case_id']/job['arm'];attempt=folder/'attempt.json'
        if not attempt.exists():rows.append({'case_id':job['case_id'],'arm':job['arm'],'status':'not_dispatched'});continue
        paid_attempts+=1
        assert load_checkpoint(folder/'request.json')==job['request']
        assert load_checkpoint(attempt)['request_sha256']==digest(job['request'])==job['request_sha256']
        assert reservation(job['request'])==Decimal(job['worstcase_usd'])
        if not(folder/'stream_result.json').exists():rows.append({'case_id':job['case_id'],'arm':job['arm'],'status':'unknown_transport'});continue
        actual=load_checkpoint(folder/'stream_result.json');parsed=parse_sse((folder/'response.sse').read_text())
        for key,value in parsed.items():
            if key=='stream_error'and actual.get('curl_exit_code'):continue
            assert actual[key]==value
        if(folder/'cost_receipt.json').exists():
            cost=known_cost(actual);costs+=cost;receipt=load_checkpoint(folder/'cost_receipt.json')
            assert Decimal(receipt['actual_cost_usd'])==cost and Decimal(receipt['cumulative_cost_usd'])==costs
            providers.append(actual['provider']);usage=actual['usage']
            tokens_in+=usage['prompt_tokens'];tokens_out+=usage['completion_tokens']
            reasoning+=(usage.get('completion_tokens_details')or{}).get('reasoning_tokens')or 0
        rows.append({'case_id':job['case_id'],'arm':job['arm'],'provider':actual['provider'],
                     'finish_reason':actual['finish_reason'],'stream_error':actual['stream_error']})
    assert paid_attempts==summary['paid_dispatches']<=4 and costs==Decimal(summary['actual_known_cost_usd'])<=Decimal(plan['run_cap_usd'])
    result={'integrity':'PASS','owner_readonly_audit':True,'frozen_entries':len(freeze),'rows':rows,
            'paid_dispatches':paid_attempts,'actual_known_cost_usd':str(costs),'actual_providers':providers,
            'input_tokens':tokens_in,'output_tokens_including_reasoning':tokens_out,'reasoning_tokens':reasoning,
            'unknown_cost_attempts':summary['unknown_cost_attempts'],'new_paid_or_native_calls':0,'private_labels_read':0,
            'independent_agent_review':False}
    target=HERE/'terminal_audit.json'
    if target.exists():assert read(target)==result
    else:
        with target.open('x')as f:json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
