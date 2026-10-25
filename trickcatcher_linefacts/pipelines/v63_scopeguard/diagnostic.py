"""One frozen reference-free native diagnostic; no model or private evaluator."""
import argparse
import ast
import hashlib
import json
from pathlib import Path

from .recipe_compiler import compile_public
from .native_construct import certify_case

HERE=Path(__file__).resolve().parent


def write_new(path,value):
    with path.open('x') as stream:json.dump(value,stream,indent=2,sort_keys=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--requests',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    requests=json.loads(a.requests.read_text())
    config=json.loads((HERE/'config.json').read_text())['pathfault_complete']
    if [r['case_id'] for r in requests]!=config['case_ids']:raise ValueError('frozen_case_ids')
    budget={'max_candidates':config['max_candidates_per_case'],'max_executions':config['max_native_executions_per_case'],
            'seeds':config['repeat_seeds'],'repeats':config['repeats_per_program_seed']}
    compiled=[dict(case_id=r['case_id'],**compile_public(r,budget)) for r in requests]
    identity={'requests_sha256':hashlib.sha256(a.requests.read_bytes()).hexdigest(),'config':config,
              'sources':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(HERE.glob('*.py'))},
              'compiled':compiled,'scope':'reference_free_engineering_only'}
    a.out.mkdir(parents=True,exist_ok=False)
    write_new(a.out/'frozen_plan.json',identity)
    summaries=[]
    for r,c in zip(requests,compiled):
        if c['recipes']:
            report=certify_case(r['source'],r['entry'],c['recipes'],ast.literal_eval(r['public_examples'][0]['arguments']))
            status='executed'
        else:report={'recipes':[],'native_executions':0,'candidates_tested':0};status='no_applicable_recipe'
        report.update(case_id=r['case_id'],status=status,limitations=c['unsupported'])
        write_new(a.out/f"case_{r['case_id']}.json",report)
        runs=[x for recipe in report['recipes'] for x in recipe['runs']]
        summary={'case_id':r['case_id'],'status':status,'recipes':len(c['recipes']),
                 'native_executions':report['native_executions'],'candidates_tested':report['candidates_tested'],
                 'site_input_realized':sum(x['obligation_realized'] for x in runs),
                 'behavioral_witnesses':sum(x['output_sensitivity']is True for x in runs)}
        summaries.append(summary);print(json.dumps(summary),flush=True)
    write_new(a.out/'summary.json',{'rows':summaries,'scope':'no_spec_truth_or_bug_labels'})


if __name__=='__main__':main()
