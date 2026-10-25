"""Frozen metadata planning costs; model caps split across fixed datasets."""
from decimal import Decimal
import json
from .paths import CONFIG, HERE


def estimate(model=None):
    model=model or CONFIG['model_choice'];c=CONFIG['models'][model]
    rates=c['price_per_million'];p=Decimal(str(rates['prompt']))/1000000;q=Decimal(str(rates['completion']))/1000000
    calls={'plain':1,'plain-hybrid':8,'toolinput':1,'placebo-hybrid':8,'concept-hybrid':8,'concept-hybrid-ft':8}
    rows=[]
    for dataset,tasks in CONFIG['combined']['tasks'].items():
        for arm,n in calls.items():
            requests=n*tasks*CONFIG['K']
            cost=requests*(4096*p+c['planning_output_tokens']*q)
            worst=requests*(4096*p+c['max_tokens']*q)
            rows.append(dict(dataset=dataset,arm=arm,calls_per_sample=n,tasks=tasks,K=CONFIG['K'],logical_calls=requests,
                             estimate_usd=str(cost),full_output_cost_usd=str(worst)))
    total=sum((Decimal(r['estimate_usd']) for r in rows),Decimal(0));cap=min(total*Decimal('1.5'),Decimal(10))
    he=(cap*Decimal(113)/146).quantize(Decimal('.00000001'));vp=cap-he
    return dict(model=model,route='relace/fp4' if model=='deepseek-v4-flash' else 'price-priority eligible routes (Near AI planning)',
                prompt_per_million=str(rates['prompt']),completion_per_million=str(rates['completion']),rows=rows,
                estimate_usd=str(total),hard_cap_usd=str(cap),dataset_caps_usd={'humaneval':str(he),'vibepass_half':str(vp)},
                full_output_cost_usd=str(sum(Decimal(r['full_output_cost_usd']) for r in rows)),
                assumptions=f"4096 prompt + {c['planning_output_tokens']} output including reasoning/call; maximum logical calls; shared round1 double counted; scoring shares dataset cap")

if __name__=='__main__':
    print(json.dumps({m:estimate(m) for m in CONFIG['models']},indent=2))
