"""Offline execute the frozen Reka strategy in existing v81 sandboxes."""
from pathlib import Path
import ast,hashlib,json
from datetime import datetime,timezone
from trickcatcher_linefacts.pipelines.v81_deepinfra_quarter.prepare_cpu import load
from trickcatcher_linefacts.pipelines.v81_deepinfra_quarter.v4_strategies import checked,draws
from trickcatcher_linefacts.pipelines.v81_deepinfra_quarter.run_v4 import classify
from trickcatcher_linefacts.pipelines.v81_deepinfra_quarter.v4_runtime import interpreter

HERE=Path(__file__).resolve().parent


def main():
    trial=json.loads((HERE/'provider_trial_results_final3.json').read_text())
    row=next(x for x in trial['results'] if x['provider']=='reka')
    raw=row['response']['content']
    code=checked(raw)
    request=json.loads((HERE/'provider_trial_prompt_final3.json').read_text())
    body=request['messages'][1]['content']
    fact_text=body.split('\n\nFACT:\n')[-1].strip()
    if not fact_text:raise ValueError('missing_frozen_fact')
    prepared=load('humaneval')
    pair=next(x for x in prepared if x['baseline']['task']==19)
    task=pair['baseline']
    fact=next((x for x in task['concept_meta'] if x['text'].strip()==fact_text),None)
    if fact is None:raise ValueError('frozen_fact_not_in_original_baseline')
    out=HERE/'reka_strategy_execution'
    out.mkdir(exist_ok=False)
    (out/'strategy.py').write_text(code)
    python=interpreter()
    generated=draws(code,task,out/'draw',python,20261027,n=100,cap=500)
    classified=classify(task,out/'classify',python,candidates=generated['candidates'],
                        shown=[fact],requested_draws=100)
    summary=classified['summary']
    report={'status':'completed_offline_strategy_diagnostic','provider':'Reka',
            'prompt_sha256':request['messages_sha256'] if 'messages_sha256' in request else hashlib.sha256(json.dumps(request['messages'],sort_keys=True).encode()).hexdigest(),
            'task':19,'arm':'concept-hybrid','fact_kind':fact['kind'],'fact_text':fact_text,
            'hypothesis_seed':20261027,'draw_requested':100,'hypothesis_attempt_cap':500,
            'draws':generated,'classification_summary':summary,
            'input_examples':[r['input_repr'] for r in classified['records'][:12]],
            'native_private_reference_calls':0,'new_paid_model_calls':0,
            'does_not_update_v81_score':True,'finished_utc':datetime.now(timezone.utc).isoformat()}
    (out/'REPORT.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'generated_candidates':len(generated['candidates']),
                      'valid':summary.get('valid'),'shown_hit_count':summary.get('shown_hit_counts'),
                      'removed':summary.get('removed'),'errors':generated.get('errors',[]),
                      'report':str(out/'REPORT.json')}))


if __name__=='__main__':main()
