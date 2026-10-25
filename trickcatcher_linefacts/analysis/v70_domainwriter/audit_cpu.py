"""Read-only provenance, accounting and evidence audit; no native/model execution."""
import hashlib
import json
from pathlib import Path

from trickcatcher_linefacts.pipelines.v70_domainwriter.pipeline import load_checkpoint,source_identity,contexts,readiness_identity
from trickcatcher_linefacts.pipelines.v70_domainwriter.replay_saved import input_identity
from trickcatcher_linefacts.pipelines.v70_domainwriter.writer_compiler import compile_and_admit
from trickcatcher_linefacts.pipelines.v70_domainwriter.domain_constraints import public_domain,check_domain
import ast
from trickcatcher_linefacts.pipelines.v70_domainwriter.evidence_gate import realized,assess_context,select_evidence

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]

def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    current=read(HERE/'CPU_RUN.json');out=Path(current['out']);requests_path=Path(current['requests'])
    before=load_checkpoint(out/'frozen_before_replay.json')
    assert source_identity()==before['source_files']
    assert input_identity(requests_path)==before['inputs']
    assert readiness_identity(requests_path)==before['runtime_and_artifacts']
    folder=REPO/'trickcatcher_linefacts/pipelines/v70_domainwriter'
    assert sha(folder/'PREREG_V70.md')==before['protocol_sha256']and sha(folder/'REVIEW_V70.md')==before['review_sha256']
    freeze=load_checkpoint(out/'frozen.json')
    for rel,digest in freeze.items():assert sha(out/rel)==digest
    summary=load_checkpoint(out/'summary.json');requests=read(requests_path);rows=[];total_native=0
    for req,row in zip(requests,summary['rows'],strict=True):
        assert row['case_id']==req['case_id']
        saved=read(REPO/'trickcatcher_linefacts/analysis/v67_prepare6/frozen_writers'/f"{req['case_id']}.json")
        hypotheses,rejected,compilation=compile_and_admit(req,(saved.get('value')or{}).get('hypotheses',[]),mode='legacy')
        child=out/req['case_id'];assert load_checkpoint(child/'compilation.json')==compilation
        assert row['admitted']==len(hypotheses)and row['rejected']==rejected
        report=load_checkpoint(child/'construction.json')
        assert report['input_domain']==public_domain(req)
        assert [r['hypothesis']for r in report['records']]==hypotheses
        count=0;realizations=0;sensitive=0
        for record in report['records']:
            public=record['public_consistency'];count+=public['native_executions']
            assert public['native_executions']==len(public['rows'])
            if public['status']=='passed':
                assert len(public['rows'])==len(req['public_examples'])*8
                assert all(x['normal']and x['matches']for x in public['rows'])
            else:assert not record['runs']
            for run in record['runs']:
                assert check_domain(report['input_domain'],ast.literal_eval(run['arguments']))['passed']
                assert run['domain_check']['passed']
                count+=run['native_executions'];realizations+=realized(run)
                sensitive+=realized(run)and run.get('output_sensitivity')is True
        assert count==report['native_executions']==row['native_executions']<=256
        assert report['candidates_tested']==row['candidates']==sum(len(r['runs'])for r in report['records'])<=64
        ctx=contexts(req,report);assert load_checkpoint(child/'prepared_contexts.json')==ctx
        assert ctx['concept']['evidence']==ctx['equal_evidence_raw']['evidence']
        assert ctx['inputs_only']['inputs']==select_evidence(req,report)['inputs']
        assert row['gate']==assess_context(req,ctx['concept'])
        total_native+=count
        rows.append(dict(case_id=req['case_id'],admitted=len(hypotheses),candidates=row['candidates'],native_executions=count,
                         realized=realizations,sensitive=sensitive,selected_sensitive=len(row['gate']['delivered_sensitive']),
                         gate_passed=row['gate']['passed']))
    assert len(rows)==6 and total_native==summary['native_executions']
    assert summary['gate_passed']==all(r['gate_passed']for r in rows)
    parent=read(folder/'PARENT_V69.json')
    assert all(sha(folder.parent/parent['ports']/rel)==digest for rel,digest in parent['sha256'].items())
    result={'integrity':'PASS','review_kind':'owner_readonly_audit','frozen_entries':len(freeze),'rows':rows,
            'native_executions':total_native,'new_model_calls':0,'audit_native_calls':0,'private_labels_read':0,
            'independent_agent_review':False,'origin_and_sources_unchanged':True}
    target=HERE/'cpu_terminal_audit.json'
    if target.exists():assert read(target)==result
    else:
        with target.open('x')as f:json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
