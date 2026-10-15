"""Synthetic interface capability probe, separate from benchmark outcomes/budgets."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import random
import sys

REPO=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(REPO))
from trickcatcher_linefacts.pipelines.v17_templates import templates as t,template_semantic as s
from trickcatcher_linefacts.pipelines.v17_templates.llm_client import Client,atomic_json

CASES=[
 dict(id='character_filter',spec='Remove English vowels in either uppercase or lowercase. Preserve all other characters, whitespace, order and repeated occurrences.',arity=1,
      model=dict(template='FILTER',predicate='not_member',values='aeiouAEIOU'),
      examples=[dict(args=['a bE aa!'],expected=' b !'),dict(args=['BC BC'],expected='BC BC')]),
 dict(id='bidirectional_order',spec='Return True exactly when the input sequence is nondecreasing OR nonincreasing. Equal adjacent values are allowed.',arity=1,
      model=dict(template='ORDER_CHECK',direction='either'),
      examples=[dict(args=[[1,1,2]],expected=True),dict(args=[[3,2,2]],expected=True),dict(args=[[1,3,2]],expected=False)]),
 dict(id='indexed_sum',spec='Sum the even integer VALUES at zero-based POSITIONS 1, 3, 5, and so on in the input list. Return zero if no element qualifies.',arity=1,
      model=dict(template='REDUCE',predicate='even',index='odd',aggregate='sum'),
      examples=[dict(args=[[2,4,6,8]],expected=12),dict(args=[[4,3,2,7]],expected=0),dict(args=[[8,2,1]],expected=2)]),
 dict(id='paired_absolute_difference',spec='Given two equally long integer sequences, return the absolute difference between corresponding elements, preserving their positions.',arity=2,
      model=dict(template='MAP',other_argument=1,transform='abs_sub'),
      examples=[dict(args=[[1,5],[4,1]],expected=[3,4]),dict(args=[[],[]],expected=[])]),
 dict(id='filtered_multiplicity',spec='Keep strings with even length, sort them by length and then lexical order for equal lengths. Preserve repeated occurrences of kept strings.',arity=1,
      model=dict(template='FILTER',predicate='length_even',order='length_lex',distinct=False),
      examples=[dict(args=[['zz','aa','zz','b','aaaa']],expected=['aa','zz','zz','aaaa'])]),
 dict(id='empty_safe_minimum',spec='Return the smallest strictly positive integer in the input sequence. Return None when no strictly positive integer exists.',arity=1,
      model=dict(template='REDUCE',predicate='positive',aggregate='min'),
      examples=[dict(args=[[0,-2]],expected=None),dict(args=[[0,4,2]],expected=2),dict(args=[[]],expected=None)]),
]


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--online',action='store_true');ap.add_argument('--prepare-only',action='store_true');a=ap.parse_args()
    root=REPO/'trickcatcher_linefacts/out/template_capability_probe';root.mkdir(parents=True,exist_ok=True)
    prepared=[]
    for i,case in enumerate(CASES):
        truth=t.normalize(case['model'],case['arity'])
        assert all(t.expected(truth,tuple(e['args']))==e['expected'] for e in case['examples'])
        options=[truth]
        for f in t.alternatives(truth):
            values=[t.observe(f['model'],tuple(e['args'])) for e in case['examples']]
            if any(v['status']=='unknown' for v in values):continue
            if not any(v['status']!='ok' or v['value']!=e['expected'] for v,e in zip(values,case['examples'])):continue
            options.append(f['model'])
            if len(options)>=4:break
        random.Random(20261016+i).shuffle(options)
        choices={f'C{j}':m for j,m in enumerate(options)}
        correct=next(k for k,m in choices.items() if m==truth)
        prepared.append(dict(case,normalized_truth=truth,choices=choices,correct_choice=correct))
    from trickcatcher_linefacts.pipelines.v17_templates.v4_runtime import immutable
    immutable(root/'declared_cases.json',prepared)
    if a.prepare_only:
        print('Prepared six synthetic cases; verified expected values and randomized choice positions; no model calls.');return
    gate=REPO/'trickcatcher_linefacts/pipelines/v17_templates/out/humaneval/behavior_smoke/concept_gate.json'
    if not gate.exists() or json.loads(gate.read_text())['passed']:raise SystemExit('Probe runs only after v17 gate failure')
    c=Client(root/'cache',offline=not a.online,workers=2)
    def one(job):
        i,case=job;d=root/case['id'];ir=dict(docstring=case['spec'],parameters=['xs'] if case['arity']==1 else ['left','right'])
        messages=s.messages('spec',{},dict(ir=ir))
        messages[-1]['content']+='\nFor this synthetic probe, return exactly ONE proposal.'
        immutable(d/'synthesis_prompt.json',messages)
        synth=c.chat(messages,20261016+i*2,temperature=0,top_p=1,max_tokens=512);atomic_json(d/'synthesis_response.json',synth)
        compiles=False;semantic_match=False;strict=False;error=None
        try:
            rows=s.parse(synth['text'],'proposals')
            if len(rows)!=1:raise ValueError('one_proposal_expected')
            model=t.normalize(rows[0],case['arity']);compiles=True
            semantic_match=all(ob['status']=='ok' and type(ob['value']) is type(e['expected']) and ob['value']==e['expected'] for e in case['examples'] for ob in [t.observe(model,tuple(e['args']))])
            accepted,rejections=s.proposals(synth['text'],ir);strict=bool(accepted) and not rejections
        except (ValueError,TypeError,KeyError) as exc:error=type(exc).__name__
        messages=[dict(role='system',content='Choose exactly one provided candidate. Return JSON {"choice":"actual candidate ID"} only.'),
                  dict(role='user',content='REQUIREMENT:\n'+case['spec']+'\nTEMPLATE SEMANTICS:\n'+json.dumps(t.CATALOG)+
                       '\nCANDIDATE MODELS:\n'+json.dumps(case['choices']))]
        immutable(d/'choice_prompt.json',messages)
        choice=c.chat(messages,20261017+i*2,temperature=0,top_p=1,max_tokens=512);atomic_json(d/'choice_response.json',choice)
        try:
            raw=choice['text'].strip()
            import re
            raw=re.sub(r'^```(?:json)?\s*\n|\n```\s*$','',raw)
            selected=json.loads(raw)['choice'];choice_valid=type(selected) is str and selected in case['choices']
        except (ValueError,TypeError,KeyError):selected=None;choice_valid=False
        result=dict(id=case['id'],synthesis_compiles=compiles,synthesis_semantics_on_declared_examples=semantic_match,
                    synthesis_evidence_schema_valid=strict,synthesis_error=error,choice_valid=choice_valid,
                    selected=selected,correct_choice=case['correct_choice'],choice_correct=choice_valid and selected==case['correct_choice'])
        atomic_json(d/'result.json',result);print(json.dumps(result),flush=True);return result
    with ThreadPoolExecutor(2) as pool:rows=list(pool.map(one,enumerate(prepared)))
    ledger=[json.loads(x) for x in (root/'cache/calls.jsonl').read_text().splitlines()]
    calls=[r for r in ledger if not r.get('cache_hit') and not r.get('error')]
    result=dict(scope='six synthetic interface cases; not a detection benchmark or semantic proof',
                chance_expected_correct=sum(1/len(c['choices']) for c in prepared),always_C0_correct=sum(c['correct_choice']=='C0' for c in prepared),rows=rows,
                summary={k:sum(r[k] for r in rows) for k in ('synthesis_compiles','synthesis_semantics_on_declared_examples','synthesis_evidence_schema_valid','choice_valid','choice_correct')},
                costs=dict(successful_new_requests=len(calls),input_tokens=sum(r.get('n_in',0) for r in calls),output_tokens=sum(r.get('n_out',0) for r in calls),
                           failed_attempts=sum(bool(r.get('error')) for r in ledger),cache_hits=sum(bool(r.get('cache_hit')) for r in ledger)))
    atomic_json(root/'report.json',result);print(json.dumps(result['summary']),flush=True)
if __name__=='__main__':main()
