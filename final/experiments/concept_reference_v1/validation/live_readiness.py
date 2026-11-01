"""One real input-generation call on a tiny engineering fixture, not benchmark data."""
import ast
import json
from pathlib import Path

from final.pipeline import Pipeline,Settings,save
from final.experiments.concept_reference_v1.analysis import analyze_task
from final.experiments.concept_reference_v1.benchmark import parsed_input
from final.experiments.concept_reference_v1.execution import execute
from final.experiments.concept_reference_v1.model import QwenModel
from final.experiments.concept_reference_v1.prompts import common_prompt,messages


def main():
    directory=Path('final/out/readiness_qwen27b')
    model=QwenModel()
    task=dict(task_id='Readiness/0',prompt='def f(x):\n    """Return the absolute value of integer x."""\n',
              canonical_solution='    return abs(x)\n',entry_point='f',
              test='def check(candidate): assert candidate(2)==2')
    source='def f(x):\n    if x>0:\n        return x\n    return x'
    base=execute(dict(mode='base',source=source,context=task['prompt'],entry='f',base=task['test'],
                      trace=True,timeout=3))
    program=dict(id=0,code=source,base=base)
    packet=analyze_task(dict(task_id=task['task_id'],programs=[program]))
    contract='\n    assert type(x)==int\n'
    common=common_prompt(task,[program],contract,3)
    response=Pipeline(model,directory,Settings()).query(directory,'classical_readiness',
        messages(common,'classical',packet,[]),temperature=.7,max_tokens=512,seed=880301)
    records=[parsed_input(r) for r in json.loads(response.text)['inputs'][:3]]
    oracle=execute(dict(mode='oracle',source=task['prompt']+task['canonical_solution'],context=task['prompt'],
                        contract=contract,entry='f',tests=records,timeout=3))['tests']
    valid=[]
    seen=set(base['input_keys'])
    for record,gold in zip(records,oracle):
        if gold['status']=='ok' and gold['input_key'] not in seen:
            seen.add(gold['input_key'])
            valid.append(dict(record,expected=gold['expected']))
    runs=[execute(dict(mode='evaluate',source=source,context=task['prompt'],entry='f',tests=valid,atol=0,timeout=3)) for _ in range(2)]
    detected=any(all(r['tests'][i]['status'] in ('fail','error','timeout') for r in runs) for i in range(len(valid)))
    result=dict(purpose='Live API-to-reference-to-PUT engineering readiness, excluded from benchmark',
                model=model.model_id,input_records=records,oracle=oracle,valid_inputs=len(valid),
                put_evaluation=runs,fixture_failure_detected=detected,usage=response.usage,
                runnable=bool(valid) and len(runs)==2)
    save(directory/'result.json',result)
    save(Path(__file__).with_name('live_readiness_result.json'),result)
    print({k:result[k] for k in ('model','valid_inputs','fixture_failure_detected','runnable','usage')})
    return 0 if result['runnable'] else 2


if __name__=='__main__':
    raise SystemExit(main())
