"""Four bounded public-input replays after all model outputs froze.

Expected values are reviewer-derived tiny spec arguments, never model/scorer refs.
"""
import ast,json,hashlib
from pathlib import Path
from trickcatcher_linefacts.pipelines.v72_diagnosisprobe.pipeline import load_checkpoint,checkpoint
from trickcatcher_linefacts.pipelines.v72_diagnosisprobe.construction import replay
from trickcatcher_linefacts.pipelines.v72_diagnosisprobe.domain_constraints import public_domain,check_domain
from trickcatcher_linefacts.pipelines.v72_diagnosisprobe.replay_worker import encode

HERE=Path(__file__).resolve().parent

def read(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    current=read(HERE/'CURRENT_RUN.json');out=Path(current['out']);plan=load_checkpoint(out/'plan.json')
    frozen=load_checkpoint(out/'frozen.json')
    for rel,h in frozen.items():assert sha(out/rel)==h
    if(HERE/'public_probe_results.json').exists():raise ValueError('do_not_repeat_native_review')
    anchors=read(HERE/'PUBLIC_REVIEW_ANCHORS.json')
    jobs=[
      {'case_id':'85','arm':'raw_known','origin':'model_candidate','arguments':'([1, 3, 1, 3, 1],)',
       'model_claimed_expected':'1','spec_expected':'1','candidate_quote':'[1, 3, 1, 3, 1]',
       'reasoning':'At indices0,2,4 there are already ones. Each remaining index1,3copies an adjacent1 in one simultaneous step. Not already equal, so optimum1.'},
      {'case_id':'85','arm':'raw_known','origin':'review_anchor',**{k:v for k,v in anchors['cases'][0].items()if k!='case_id'}},
      {'case_id':'124','arm':'raw_known','origin':'model_candidate','arguments':"('abcde', 'ace')",
       'model_claimed_expected':'[0, 2, 4]','spec_expected':'[0, 1, 4]','candidate_quote':"('abcde', 'ace')",
       'reasoning':'Indices[0,1,4]formabe, changeb→c to obtainace. Firstindex0is minimal; secondindex1is minimal; with that one mismatch, last character must be e at4. Thus[0,1,4]is lexicographically minimal. The model sequence[0,2,4]is valid but larger, and its two-change explanation violates the at-most-one rule.'},
      {'case_id':'124','arm':'raw_known','origin':'review_anchor',**{k:v for k,v in anchors['cases'][1].items()if k!='case_id'}},
    ]
    assert len(jobs)==4 and all(sum(j['case_id']==case for j in jobs)<=2 for case in ('85','124'))
    checkpoint(HERE/'public_probe_plan.json',{'jobs':jobs,'before_native_calls':True,'prior_output_freeze_sha256':sha(out/'frozen.json'),'private_labels_read':0})
    rows=[]
    for job in jobs:
        req=next(r for r in plan['requests']if r['case_id']==job['case_id']);args=ast.literal_eval(job['arguments'])
        domain=check_domain(public_domain(req),args);assert domain['passed']
        if job['origin']=='model_candidate':
            answer=read(out/job['case_id']/job['arm']/'response.json')['value']['analysis']
            assert job['candidate_quote']in answer
        observed=replay(req['source'],req['entry'],args,None,seed=20261024)
        program=observed.get('put',{});normal=observed.get('status')=='ok'and program.get('status')=='ok'
        expected=encode(ast.literal_eval(job['spec_expected']))
        row={**job,'domain_check':domain,'observed':observed,'normal':normal,
             'output_disagrees_with_public_reasoning':normal and program.get('output')!=expected}
        if 'model_claimed_expected'in job:
            row['model_expected_matches_public_reasoning']=encode(ast.literal_eval(job['model_claimed_expected']))==expected
            row['put_matches_model_expected']=normal and program.get('output')==encode(ast.literal_eval(job['model_claimed_expected']))
        rows.append(row)
    result={'rows':rows,'native_replay_calls':len(rows),'new_model_calls':0,'private_reference_calls':0,
            'expected_source':'explicit_reviewer_public_spec_reasoning_not_reference_program',
            'model_candidates_executed':2,'reviewer_anchors_executed':2,'original_outputs_unchanged':True}
    assert all(sha(out/rel)==h for rel,h in frozen.items())
    checkpoint(HERE/'public_probe_results.json',result)
    print(json.dumps({**{k:v for k,v in result.items()if k!='rows'},'rows':[{k:v for k,v in row.items()if k not in('observed','domain_check')}for row in rows]},indent=2))

if __name__=='__main__':main()
