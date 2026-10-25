"""Read-only integrity/accounting audit of prepared evidence; no native/model calls."""
import hashlib
import json
from pathlib import Path
from trickcatcher_linefacts.pipelines.v70_domainwriter.pipeline import contexts,load_checkpoint,digest
from trickcatcher_linefacts.pipelines.v70_domainwriter.evidence_gate import select_evidence,assess_context,realized
from trickcatcher_linefacts.pipelines.v70_domainwriter.writer_compiler import compile_and_admit
from trickcatcher_linefacts.pipelines.v70_domainwriter.domain_constraints import public_domain,check_domain
import ast

HERE=Path(__file__).resolve().parent

def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    current=read(HERE/'CURRENT_RUN.json');root=Path(current['run_root']);gen=root/'generation'
    terminal=read(root/'terminal.json');summary=read(gen/'prepare_summary.json')
    assert sha(gen/'prepare_summary.json')==terminal['summary_sha256']
    assert sha(gen/'prepare_frozen.json')==terminal['freeze_sha256']
    freeze=read(gen/'prepare_frozen.json')
    for rel,h in freeze.items():assert sha(gen/rel)==h
    requests=read(root/'preparation/requests.json');packets=read(gen/'prepared_contexts.json')
    rows=[];dispatches=0;known_in=0;known_out=0
    gate=load_checkpoint(gen/'admission_gate.json')if(gen/'admission_gate.json').exists()else None
    preflight={r['case_id']:r for r in read(HERE/'preflight.json')['rows']}
    for req in requests:
        folder=gen/req['case_id'];writer=folder/'shared_writer'
        response_path=writer/'response.json'
        if not response_path.exists():
            rows.append({'case_id':req['case_id'],'status':'no_complete_response'});continue
        response=read(response_path);request=read(writer/'request.json')
        assert response['request_sha256']==digest(request)
        token=read(writer/'tokenization.json')
        assert token['count']==preflight[req['case_id']]['prompt_tokens']
        physical=list(writer.glob('attempt_[0-9][0-9].json'));assert len(physical)<=2
        dispatches+=len(physical)
        for attempt in physical:
            assert read(attempt)['request_sha256']==response['request_sha256']
            receipt=attempt.with_name(attempt.stem+'_result.json')
            if receipt.exists()and read(receipt).get('status')=='received':
                r=read(receipt)['response'];known_in+=r.get('input_tokens')or 0;known_out+=r.get('output_tokens')or 0
        proposals=(response.get('value')or{}).get('hypotheses',[])
        accepted,rejected,compilation=compile_and_admit(req,proposals,mode='writer')
        assert load_checkpoint(folder/'writer_compilation.json')==compilation
        path=folder/'construction.json'
        if not path.exists():
            rows.append({'case_id':req['case_id'],'status':'no_construction_checkpoint'});continue
        construction=load_checkpoint(path)
        assert construction['input_domain']==public_domain(req)
        assert [r['hypothesis']for r in construction['records']]==accepted
        executed=sum(r.get('public_consistency',{}).get('native_executions',0)+sum(x['native_executions']for x in r['runs'])for r in construction['records'])
        assert executed==construction['native_executions']<=256
        assert construction['candidates_tested']==sum(len(r['runs'])for r in construction['records'])<=64
        for record in construction['records']:
            for run in record['runs']:
                assert check_domain(construction['input_domain'],ast.literal_eval(run['arguments']))['passed']
                assert run['domain_check']['passed']
            check=record.get('public_consistency',{})
            if check.get('status')=='passed':
                assert len(check['rows'])==len(req['public_examples'])*8
                assert all(row['normal']and row['matches']for row in check['rows'])
            else:assert not record['runs']
        ctx=contexts(req,construction);assert ctx==packets[req['case_id']]
        assert ctx['concept']['evidence']==ctx['equal_evidence_raw']['evidence']
        assert ctx['inputs_only']['inputs']==select_evidence(req,construction)['inputs']
        assessed=assess_context(req,ctx['concept'])
        if gate:
            gate_row=next(r for r in gate['rows']if r['case_id']==req['case_id'])
            assert all(gate_row[key]==value for key,value in assessed.items())
            assert gate_row['admitted']==len(accepted)and gate_row['rejected']==rejected
        rows.append({'case_id':req['case_id'],'status':'verified','gate_passed':assessed['passed'],
                     'native_executions':executed,'admitted':len(accepted)})
    assert dispatches==summary['actual_dispatches']<=12
    assert known_in==summary['known_input_tokens']and known_out==summary['known_output_tokens']
    assert not [p for p in gen.rglob('response.json')if p.parent.name!='shared_writer']
    if gate:assert gate['passed']==all(r['passed']for r in gate['rows'])
    result={'integrity':'PASS','review_kind':'owner_readonly_artifact_audit','freeze_entries':len(freeze),'cases':rows,
            'actual_dispatches':dispatches,'known_input_tokens':known_in,'known_output_tokens':known_out,
            'model_or_native_calls':0,'private_label_reads':0,'independent_agent_review':False}
    audit_path=HERE/'fresh_terminal_audit.json'
    if audit_path.exists():assert read(audit_path)==result
    else:
        with audit_path.open('x')as f:json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
