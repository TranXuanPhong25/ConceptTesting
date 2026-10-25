"""Bounded public semantic checks after paid outputs froze. No API/private refs."""
import ast,json,hashlib
from pathlib import Path
from trickcatcher_linefacts.pipelines.v73_ossdiagnosis.pipeline import load_checkpoint,checkpoint
from trickcatcher_linefacts.pipelines.v73_ossdiagnosis.construction import replay
from trickcatcher_linefacts.pipelines.v73_ossdiagnosis.domain_constraints import public_domain,check_domain
from trickcatcher_linefacts.pipelines.v73_ossdiagnosis.replay_worker import encode

HERE=Path(__file__).resolve().parent

def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    current=read(HERE/'CURRENT_RUN.json');out=Path(current['out']);plan=load_checkpoint(out/'plan.json');freeze=load_checkpoint(out/'frozen.json')
    if(HERE/'public_review_results.json').exists():raise ValueError('do_not_repeat_public_probes')
    for rel,h in freeze.items():assert sha(out/rel)==h
    req85=next(r for r in plan['requests']if r['case_id']=='85');req124=next(r for r in plan['requests']if r['case_id']=='124')
    raw85=load_checkpoint(out/'85/raw_known/response.json')['value']['analysis']
    raw124=load_checkpoint(out/'124/raw_known/response.json')['value']['analysis']
    assert '[1,2,3,4,5]'in raw85 and '`jAfter[mi + 1] <= t`'in raw124
    nodes=[n for n in ast.walk(ast.parse(req124['source']))if isinstance(n,ast.Compare)and ast.unparse(n)=='jAfter[mi + 1] <= t + 1']
    assert len(nodes)==1;n=nodes[0]
    edit={'span':[n.lineno,n.col_offset,n.end_lineno,n.end_col_offset],'node_kind':'Compare',
          'before':ast.unparse(n),'after':'jAfter[mi + 1] <= t'}
    base=req124['public_examples'][0]
    jobs=[{'case_id':'85','origin':'model_candidate','arguments':'([1,2,3,4,5],)','expected':'2','edit':None,
           'public_reasoning':'All5values unique. Any chosen target initially occupies1position and covers at most3positions after1second, so1cannot suffice; after2seconds its wave covers the5-cycle. Minimum2. PUTceil(5/2)=3.'},
          {'case_id':'124','origin':'model_suggested_edit_on_supplied_public_example',
           'arguments':base['arguments'],'expected':base['expected'],'edit':edit,
           'public_reasoning':'This expected value is in the supplied public example. Tightening <=t+1 to <=t contradicts claimed direction: <=t is stricter. A suffix matching word2[t+1:] is sufficient. The replacement should not reject this base example.'}]
    assert sum(1 if j['edit']is None else 2 for j in jobs)==3
    checkpoint(HERE/'public_review_plan.json',{'jobs':jobs,'prior_paid_output_freeze_sha256':sha(out/'frozen.json'),
        'native_program_execution_cap':3,'public_probe_cap_per_response':2,'new_paid_calls':0,'private_labels_read':0})
    rows=[]
    for job in jobs:
        req=req85 if job['case_id']=='85'else req124;args=ast.literal_eval(job['arguments'])
        domain=check_domain(public_domain(req),args);assert domain['passed']
        observed=replay(req['source'],req['entry'],args,job['edit'],seed=20261024)
        expected=encode(ast.literal_eval(job['expected']));program=observed.get('put',{});alternative=observed.get('alternative',{})
        row={**job,'domain_check':domain,'observed':observed,
             'put_normal':program.get('status')=='ok','put_matches_expected':program.get('output')==expected}
        if job['edit']is not None:
            row['alternative_normal']=alternative.get('status')=='ok';row['alternative_matches_expected']=alternative.get('output')==expected
        rows.append(row)
    assert all(sha(out/rel)==h for rel,h in freeze.items())
    result={'rows':rows,'native_replay_operations':2,'native_program_executions':3,'new_paid_calls':0,
            'private_reference_calls':0,'expectations':'reviewer_public_reasoning_and_supplied_public_example',
            'paid_outputs_unchanged':True}
    checkpoint(HERE/'public_review_results.json',result)
    print(json.dumps({**{k:v for k,v in result.items()if k!='rows'},'rows':[{k:v for k,v in r.items()if k not in('observed','domain_check')}for r in rows]},indent=2))

if __name__=='__main__':main()
