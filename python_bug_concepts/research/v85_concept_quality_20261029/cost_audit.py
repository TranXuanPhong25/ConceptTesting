import argparse,json,collections
from pathlib import Path
parser=argparse.ArgumentParser(description="Attribute saved v85 completion receipts; no inference.")
parser.add_argument('--run-root',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
r=args.run_root

receipts={p.parent.name:json.loads(p.read_text()) for p in (r/'transport/calls').glob('*/response.json')}
def summary(keys):
 return dict(calls=len(keys),**{k:sum(receipts[x]['usage'][k] for x in keys) for k in ('prompt_tokens','completion_tokens','total_tokens')})
groups={};tasks={};stage={};logical={}
for arm in ('v11','retrieval'):
 keys=set();ts=[];round1=set();labels=collections.defaultdict(set)
 for p in sorted((r/'generation'/arm).glob('*/gen.jsonl')):
  rows=[json.loads(l) for l in p.read_text().splitlines()];final=next(x for x in rows if x['arm']=='concept-hybrid');first=next(x for x in rows if x['arm']=='concept')
  assert final['llm_calls']==len(final['calls'])
  own={c['key'] for c in final['calls']};keys.update(own);round1.update(c['key'] for c in first['calls'])
  for c in final['calls']:assert c==receipts[c['key']]
  ts.append(dict(task=final['task'],round2_strategy_requests=final['round2_strategy_requests'],missed_facts=len(final.get('missed_fact_indices',[])),**summary(own)))
  for a in (p.parent/'artifacts').rglob('*.json'):
   if a.name=='result.json':continue
   data=json.loads(a.read_text())
   if isinstance(data,dict) and data.get('status')=='received' and data.get('key') in own:labels[a.stem].add(data['key'])
 groups[arm]=keys;tasks[arm]=ts
 stage[arm]={'round1':summary(round1),'round2':summary(keys-round1),'labels':{k:summary(v) for k,v in labels.items()},'tasks_with_round2':sum(t['calls']>1 for t in ts),'logical_calls':sum(t['calls'] for t in ts)}
oracles={json.loads(p.read_text())['response']['key'] for p in (r/'oracles').glob('*/*.json')};groups['shared_refs']=oracles
overlap=groups['v11']&groups['retrieval']
remaining=set(receipts)-set.union(*groups.values());groups['remaining_preparation']=remaining
prompts=collections.Counter()
for key in remaining:
 body=json.loads((r/'transport/calls'/key/'request.json').read_text())['body']
 prompts[body['messages'][-1]['content'][:60]]+=1
hist=json.loads((r/'HISTORY.json').read_text());historical=[]
for row in hist:
 key=row['attempt']['key'];owner=[name for name,keys in groups.items() if key in keys]
 historical.append(dict(key=key,owner=owner,unknown=bool(row['response'].get('unknown_completion_usage')),duplicate=row.get('duplicate',False),error=row['response'].get('error'),usage=row['response'].get('usage')))
out=dict(groups={k:summary(v) for k,v in groups.items()},cross_arm_shared=summary(overlap),stage=stage,preparation_prompt_prefixes=dict(prompts),history=historical,tasks=tasks)
args.output.write_text(json.dumps(out,indent=2)+'\n')
assert len(tasks['v11'])==len(tasks['retrieval'])==113
assert sum(v['calls'] for v in out['groups'].values())-out['cross_arm_shared']['calls']==len(receipts)==2030
final=json.loads((r/'RESULTS.json').read_text())
for metric in ('prompt_tokens','completion_tokens','total_tokens'):
    unique=sum(v[metric] for v in out['groups'].values())-out['cross_arm_shared'][metric]
    historical_tokens=sum((x['usage'] or {}).get(metric,0) for x in historical)
    assert unique+historical_tokens==final['usage'][metric]
print(json.dumps(out['groups'],indent=2))
