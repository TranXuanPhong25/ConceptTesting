"""Final-only grading using copied v11 workers and the saved ten-reference pool."""
from collections import defaultdict
import json
from . import diagnostic as d,oracle_b01 as ob,v4_runtime
from .llm_client import atomic_json


def score(records):
    root=d.ROOT
    for name,digest in json.loads((root/'GENERATION_FREEZE.json').read_text())['files'].items():
        assert d.sha(root/name)==digest,name
    references={int(x['task_id'].split('/')[1]):x for x in json.loads((d.HERE/'assets/grading_references.json').read_text())}
    programs=json.loads((d.HERE/'assets/refs.json').read_text())
    rows=[];executions={};tasks={};mechanism={m:{} for m in d.MODES}
    atomic_json(root/'STATUS.json',dict(stage='grading',completed=0,total=len(records)))
    for record in records:
        n=record['task']['task'];h=references[n];task_rows=[]
        for mode in d.MODES:
            task=d.make_task(record,mode);tasks[n]=task
            path=root/'generation'/mode/str(n)
            generated=[json.loads(l) for l in (path/'gen.jsonl').read_text().splitlines()]
            job=dict(task=task,rows=generated,canon=h['prompt']+h['canonical_solution'],contract_src=h['prompt']+h['contract']+'\n    pass\n',atol=h.get('atol',0))
            evaluated=v4_runtime.isolated('evaluate',job,root/'grading'/str(n)/mode,timeout=1800)
            task_rows += [dict(r,arm=mode if r['arm']=='concept-hybrid' else mode+'_round1') for r in evaluated]
            artifact=path/'artifacts'/str(n)/'0/concept-hybrid'
            first=json.loads((artifact/'round1_inputs/classify_result.json').read_text())['records']
            final=json.loads((artifact/'final_inputs/classify_result.json').read_text())['records']
            before={r['input_repr'] for r in first}
            fresh=[r for r in final if r['input_repr'] not in before and r['valid']]
            mechanism[mode][str(n)]=dict(novel_valid_inputs=len(fresh),
                novel_semantic_inputs=sum(r.get('semantic_measurements',[{}])[0].get('state') is True for r in fresh),
                final_semantic_inputs=sum(r['valid'] and r.get('semantic_measurements',[{}])[0].get('state') is True for r in final),
                final_unknown=sum(r['valid'] and r.get('semantic_measurements',[{}])[0].get('state') is None for r in final))
        calls=set();expected=defaultdict(set)
        for row in task_rows:
            for assertion in row['asserts']:
                call=ob.call_of(assertion['src'],record['task']['entry']);expr=ob.expected_of(assertion['src'])
                if call is not None:
                    calls.add(call)
                    if expr is not None:expected[call].add(expr)
        t=record['task']
        job=dict(entry=t['entry'],put=t['put'],canon=h['prompt']+h['canonical_solution'],base=t['base'],
                 contract=h['prompt']+h['contract']+'\n    pass\n',spec=ob.preconditions.specification(t)[0],
                 dpp=[],tc=[],ref=[ob.code_block(x['response']['text']) for x in programs[str(n)]],post=[],mutants=[],
                 calls=sorted(calls),b1={},o0={c:sorted(v) for c,v in expected.items()},atol=h.get('atol',0),shared_scorer=True)
        executed=v4_runtime.isolated('oracle',job,root/'grading'/str(n)/'oracle',timeout=3000)
        executions[str(n)]=executed;rows+=task_rows
        atomic_json(root/'scored'/f'{n}.json',dict(rows=task_rows,execution=executed))
        atomic_json(root/'STATUS.json',dict(stage='grading',completed=len(executions),total=len(records)))
    results={}
    for oracle in ('ref','o0'):
        arms={}
        for mode in d.MODES:
            bugs=set();alarms=set();abstained=0
            for row in (r for r in rows if r['arm']==mode):
                seen=set();n=row['task']
                for assertion in row['asserts']:
                    call=ob.call_of(assertion['src'],tasks[n]['entry'])
                    if call is None or oracle=='ref' and call in seen:continue
                    seen.add(call);rec=executions[str(n)]['calls'].get(call,{})
                    emit,correct,passes=ob.decide(oracle,rec,None,ob.expected_of(assertion['src']),assertion)
                    abstained+=not emit
                    if emit and not passes:(bugs if rec.get('valid',False) and correct else alarms).add(n)
            arms[mode]=dict(tasks=len(records),confirmed_tasks=sorted(bugs),false_alarm_tasks=sorted(alarms),abstained_calls=abstained)
        contrasts={}
        for control in ('old','generic'):
            wins=sorted(set(arms['semantic']['confirmed_tasks'])-set(arms[control]['confirmed_tasks']))
            losses=sorted(set(arms[control]['confirmed_tasks'])-set(arms['semantic']['confirmed_tasks']))
            contrasts[control]=dict(wins=wins,losses=losses,sign_test_p=ob.sign_p(len(wins),len(losses)))
        results[oracle]=dict(arms=arms,contrasts=contrasts)
    responses=[json.loads(p.read_text()) for p in (root/'transport/calls').glob('*/response.json')]
    attempts=d.ledger();assert len(responses)==len(attempts)
    keys=('prompt_tokens','completion_tokens','total_tokens')
    usage={k:sum((r.get('usage') or {}).get(k) or 0 for r in responses) for k in keys}
    unknown=sum(any(type((r.get('usage') or {}).get(k)) is not int for k in keys) for r in responses)
    inherited_responses=[r['round1'] for r in records]+[r['response'] for group in programs.values() for r in group]
    inherited_usage={k:sum((r.get('usage') or {}).get(k) or 0 for r in inherited_responses) for k in keys}
    inherited_unknown=sum(any(type((r.get('usage') or {}).get(k)) is not int for k in keys) for r in inherited_responses)
    inherited=json.loads((d.HERE/'assets/INHERITED.json').read_text())
    d.verify()
    atomic_json(root/'RESULTS.json',dict(results=results,mechanism=mechanism,
                metrics=ob.fairness_metrics(tasks,rows,executions,{}),new_completion_attempts=len(attempts),
                new_usage=usage,new_unknown_usage=unknown,inherited=inherited,
                inherited_round1_ref_usage=inherited_usage,inherited_unknown_usage=inherited_unknown,
                logical_new_calls=sum(r['llm_calls']-1 for r in rows if r['arm'] in d.MODES)))
    atomic_json(root/'STATUS.json',dict(stage='complete',completed=len(records),total=len(records),new_completion_attempts=len(attempts),new_usage=usage))
    atomic_json(root/'COMPLETE.json',json.loads((root/'STATUS.json').read_text()))
