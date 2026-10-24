"""Post-freeze mechanical accounting only. Semantic judgments are independently reviewed."""
from pathlib import Path
from collections import Counter
import ast,json,hashlib
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parents[2]
POOL=REPO/'trickcatcher_linefacts/out/pipelines/v43_concept_identify/humaneval/binding8/prepared'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canonical(s):return repr(ast.literal_eval(s))
def main():
 frozen=json.loads((ROOT/'generation_frozen.json').read_text()); mapping=json.loads((ROOT/'manifest.json').read_text())['mapping']
 full={};totalrows=0
 for path in POOL.glob('*.json'):
  rows=json.loads(path.read_text())['rows'];totalrows+=len(rows)
  full[path.stem]={canonical(r['input']) for r in rows}
 entire=set().union(*full.values())
 result={'saved_rows':totalrows,'entire_pool_unique_input_literals':len(entire),'tasks':{},'arms':{}}
 for arm,short in [('generic','g'),('concept','c')]:
  totals=Counter();details=[]
  for n in range(1,7):
   name=f'/root/sol61_t{n}_{short}';entry=frozen['agents'][name];path=ROOT/entry['file'];assert sha(path)==entry['sha256']
   record=json.loads(path.read_text());answer=json.loads(record['final_text']);task=f'T{n}';ep=mapping[task]
   rows=[]
   for proposal in answer.get('inputs',answer.get('proposed_inputs',[])):
    literal=canonical(proposal['input']);rows.append({'input':proposal['input'],'novel_per_case':literal not in full[ep],'novel_entire_pool':literal not in entire})
   taskmetrics={'episode':ep,'judgment':answer['judgment']['decision'],'initial_H_decision':answer['initial_hypothesis_decision']['decision'],'input_count':len(rows),'inputs':rows,'usage':record['usage'],'inference_responses':record['inference_responses_with_usage'],'tool_calls':len(record['tool_calls']),'model':record['model'],'effort':record['effort'],'answer_words':len(record['final_text'].split()),'unknown_evidence_ids':sorted(set(answer['evidence_ids'])-set(json.loads((ROOT/'packets'/f'{task}_{arm}.json').read_text())['task_packet']['evidence_ids']))}
   result['tasks'].setdefault(task,{})[arm]=taskmetrics
   totals.update(record['usage']);totals.update(input_count=len(rows),novel_per_case=sum(x['novel_per_case'] for x in rows),novel_entire_pool=sum(x['novel_entire_pool'] for x in rows),inference_responses=record['inference_responses_with_usage'],tool_calls=len(record['tool_calls']))
   details.extend(rows)
  result['arms'][arm]=dict(totals,unique_proposed_inputs=len({canonical(x['input']) for x in details}),tasks_with_novel_per_case=sum(any(x['novel_per_case'] for x in result['tasks'][f'T{n}'][arm]['inputs']) for n in range(1,7)),tasks_with_novel_entire_pool=sum(any(x['novel_entire_pool'] for x in result['tasks'][f'T{n}'][arm]['inputs']) for n in range(1,7)))
 result['scope']='Novel literal is not bug discovery; predicates/effectiveness require independent semantic review; no native calls.'
 (ROOT/'mechanical_results.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'arms':result['arms'],'pool_rows':totalrows,'entire_unique':len(entire)}))
 for task,arms in result['tasks'].items():print(task,json.dumps({a:{k:v[k] for k in ['episode','judgment','initial_H_decision','inputs','unknown_evidence_ids']} for a,v in arms.items()}))
if __name__=='__main__':main()
