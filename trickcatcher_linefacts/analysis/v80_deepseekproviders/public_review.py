"""Bounded public spec/input verification after both provider freezes, no API."""
from pathlib import Path
import json,ast,hashlib
from trickcatcher_linefacts.pipelines.v80_deepseekproviders.construction import replay
from trickcatcher_linefacts.pipelines.v80_deepseekproviders.domain_constraints import public_domain,check_domain
from trickcatcher_linefacts.pipelines.v80_deepseekproviders.replay_worker import encode

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
BASE=REPO/'trickcatcher_linefacts/out/pipelines/v80_deepseekproviders'


def main():
    assert not (HERE/'public_review_results.json').exists()
    frozen={}
    for slug in ('reka','deepinfra_fp8'):
        root=BASE/slug;frozen[slug]=json.loads((root/'frozen.json').read_text())
        assert all(hashlib.sha256((root/rel).read_bytes()).hexdigest()==h for rel,h in frozen[slug].items())
    req=next(r for r in json.loads((BASE/'reka/plan.json').read_text())['requests'] if r['case_id']=='85')
    full=json.loads((BASE/'reka/85/full_known/response.json').read_text())['value']['hypotheses'][0]
    assert full['edit']=={'kind':'expression','expression':'max_gap // 2'}
    nodes=[n for n in ast.walk(ast.parse(req['source'])) if isinstance(n,ast.Call) and ast.unparse(n)=='math.ceil(max_gap / 2)']
    assert len(nodes)==1
    n=nodes[0];edit={'span':[n.lineno,n.col_offset,n.end_lineno,n.end_col_offset],
                   'node_kind':'Call','before':ast.unparse(n),'after':full['edit']['expression']}
    jobs=[
      {'route':'reka','arm':'raw_known','arguments':'([1,2,1,2,3,4,3],)','expected':'2','edit':None,
       'reasoning':'For value1 at indices0,2 on a7-cycle, every index is within2 edges of one of these indices. At1second indices4,5 remain outside. Values2/3 also have largest gaps5, singleton4 gap7: none can fill in1. Minimum2.'},
      {'route':'reka','arm':'full_known','arguments':'([1,2,3,4,5],)','expected':'2','edit':edit,
       'reasoning':'All values unique on a5-cycle. One target initially covers1 position; at1step can cover at most3, at2steps all5. Minimum2. This is the model-described all-distinct odd-length5 family.'},
      {'route':'deepinfra_fp8','arm':'raw_known','arguments':'([1,2,3],)','expected':'1','edit':None,
       'reasoning':'Three unequal values on a3-cycle; both other positions neighbour initial1, so all can choose1 in one simultaneous step. Not initially equal, minimum1.'},
      {'route':'deepinfra_fp8','arm':'raw_known','arguments':'([1,2,3,1,4],)','expected':'1','edit':None,
       'reasoning':'Value1 starts at0,3 on a5-cycle. Their closed one-step neighbourhoods cover0,1,2,3,4. Not already equal, minimum1.'},
    ]
    (HERE/'public_review_plan.json').write_text(json.dumps({'jobs':jobs,'native_program_cap':5,'private_references':0,'expectations':'public_spec_reasoning'},indent=2)+'\n')
    rows=[]
    for job in jobs:
        domain=check_domain(public_domain(req),ast.literal_eval(job['arguments']));assert domain['passed']
        result=replay(req['source'],req['entry'],ast.literal_eval(job['arguments']),job['edit'],seed=20261024)
        assert result.get('status')=='ok' and result['put']['status']=='ok',result
        expected=encode(ast.literal_eval(job['expected']))
        row={**job,'domain':domain,'observed':result,'put_disagrees_with_spec':result['put']['output']!=expected}
        if job['edit'] is not None:
            row['model_edit_matches_spec']=result['alternative']['status']=='ok' and result['alternative']['output']==expected
        rows.append(row)
    assert all(row['put_disagrees_with_spec'] for row in rows)
    assert all(row.get('model_edit_matches_spec',True) for row in rows)
    for slug,files in frozen.items():
        assert all(hashlib.sha256((BASE/slug/rel).read_bytes()).hexdigest()==h for rel,h in files.items())
    report={'rows':rows,'native_replay_operations':4,'native_program_executions':5,'new_model_calls':0,
            'private_reference_calls':0,'all_provider_outputs_unchanged':True}
    (HERE/'public_review_results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
