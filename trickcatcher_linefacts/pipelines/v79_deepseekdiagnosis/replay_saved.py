"""Frozen six-case CPU engineering replay. No endpoint client is instantiated."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

from .pipeline import checkpoint, load_checkpoint, contexts, source_identity, validate_cohort, readiness_identity
from .writer_compiler import compile_and_admit
from .joint_constructor import construct_case
from .evidence_gate import assess_context, realized

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
ORIGIN=REPO/'trickcatcher_linefacts/analysis/v67_prepare6'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text())


def input_identity(requests_path):
    archive=read(ORIGIN/'writer_archive_inventory.json')
    writers={}
    for cid in ('61','66','124','58','131','85'):
        path=ORIGIN/'frozen_writers'/f'{cid}.json'
        digest=sha(path)
        if digest!=archive[cid]['original_sha256'] or digest!=archive[cid]['archived_sha256']:
            raise ValueError('saved_writer_integrity')
        writers[cid]=digest
    if sha(requests_path)!=read(ORIGIN/'prepare_summary.json')['requests_sha256']:
        raise ValueError('saved_request_integrity')
    return {'writers':writers,'requests_sha256':sha(requests_path)}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--requests',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise ValueError('fresh_replay_output_required')
    requests=read(a.requests);validate_cohort(requests)
    original=input_identity(a.requests)
    identity={'source_files':source_identity(),'config_sha256':sha(HERE/'config.json'),
              'runtime_and_artifacts':readiness_identity(a.requests),
              'protocol_sha256':sha(HERE/'PREREG_V70.md'),'review_sha256':sha(HERE/'REVIEW_V70.md'),
              'inputs':original,'python':sys.version,'mode':'legacy_CPU_replay',
              'bounds':{'max_case_seconds':120,'max_candidates':64,'max_native_executions':256}}
    a.out.mkdir(parents=True,exist_ok=False)
    checkpoint(a.out/'frozen_before_replay.json',identity)
    rows=[]
    for req in requests:
        folder=a.out/req['case_id'];folder.mkdir()
        saved=read(ORIGIN/'frozen_writers'/f"{req['case_id']}.json")
        proposals=(saved.get('value')or{}).get('hypotheses',[])
        hypotheses,rejected,compilation=compile_and_admit(req,proposals,mode='legacy')
        checkpoint(folder/'compilation.json',compilation)
        started=time.monotonic()
        construction=construct_case(req,hypotheses,{'max_case_seconds':120,'repeat_seeds':[20261024,20261025],'repeats_per_program_seed':2})
        checkpoint(folder/'construction.json',construction)
        context=contexts(req,construction);checkpoint(folder/'prepared_contexts.json',context)
        gate=assess_context(req,context['concept'])
        records=[]
        for r in construction['records']:
            records.append({'hypothesis_id':r['hypothesis']['id'],'public_status':r['public_consistency']['status'],
                            'issues':r['construction'].get('issues',[]),'runs':len(r['runs']),
                            'realized':sum(realized(x)for x in r['runs']),
                            'sensitive':sum(realized(x)and x.get('output_sensitivity')is True for x in r['runs']),
                            'domain_pruned_shapes':r['construction'].get('domain_pruned_shapes',0),
                            'domain_mismatches':r['construction'].get('domain_mismatches',0)})
        row={'case_id':req['case_id'],'proposals':len(proposals),'admitted':len(hypotheses),'rejected':rejected,
             'normalizations':[r for r in compilation['receipts']if r.get('rewrites')],
             'records':records,'candidates':construction['candidates_tested'],'native_executions':construction['native_executions'],
             'gate':gate,'elapsed_seconds':time.monotonic()-started}
        checkpoint(folder/'result.json',row);rows.append(row)
        print(json.dumps({'case_id':req['case_id'],'admitted':row['admitted'],'candidates':row['candidates'],'gate':gate['passed']}),flush=True)
    assert source_identity()==identity['source_files'] and sha(HERE/'config.json')==identity['config_sha256']
    assert readiness_identity(a.requests)==identity['runtime_and_artifacts']
    assert sha(HERE/'PREREG_V70.md')==identity['protocol_sha256'] and sha(HERE/'REVIEW_V70.md')==identity['review_sha256']
    assert input_identity(a.requests)==original
    summary={'rows':rows,'gate_passed':all(r['gate']['passed']for r in rows),'case_count':6,
             'actual_new_model_calls':0,'private_label_reads':0,'old_response_count_reused':6,
             'native_executions':sum(r['native_executions']for r in rows),'source_and_origin_unchanged':True,
             'new_writer_schema_exercised':'authored_fixtures_only','interpretation':'engineering_replay_not_replication_or_efficacy'}
    checkpoint(a.out/'summary.json',summary)
    checkpoint(a.out/'frozen.json',{str(f.relative_to(a.out)):sha(f)for f in sorted(a.out.rglob('*.json'))})
    print(json.dumps({k:v for k,v in summary.items()if k!='rows'}),flush=True)

if __name__=='__main__':main()
