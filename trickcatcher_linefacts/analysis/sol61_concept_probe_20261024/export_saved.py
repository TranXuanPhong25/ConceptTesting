"""Export only this probe's completed native-agent final messages and usage records."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,re
ROOT=Path(__file__).resolve().parent
PARENT='01a145cf-19c9-7b93-8375-dc3409a10d2d'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,value):
 text=json.dumps(value,ensure_ascii=False,indent=2)+'\n';p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():assert p.read_text()==text,'export drift'
 else:p.write_text(text)
def main():
 frozen=json.loads((ROOT/'prelaunch.json').read_text())
 for path,value in frozen['files'].items():assert sha(ROOT/path)==value,path
 seen={}
 for path in (Path.home()/'.codex/sessions/2026/10/24').glob('*.jsonl'):
  with path.open() as stream: first=json.loads(stream.readline())
  meta=first.get('payload',{}); spawn=meta.get('source',{})
  if not isinstance(spawn,dict):continue
  spawn=spawn.get('subagent',{}).get('thread_spawn',{})
  name=spawn.get('agent_path','')
  if spawn.get('parent_thread_id')!=PARENT or not re.fullmatch(r'/root/sol61_t[1-6]_[gc]',name):continue
  rows=[json.loads(x) for x in path.read_text().splitlines()]
  finals=[x for x in rows if x['type']=='response_item' and x['payload'].get('type')=='message' and x['payload'].get('role')=='assistant' and x['payload'].get('phase')=='final_answer']
  completed=any(x['type']=='event_msg' and x['payload'].get('type')=='task_complete' for x in rows)
  assert completed and len(finals)==1, name
  context=[x['payload'] for x in rows if x['type']=='turn_context']
  assert len(context)==1 and context[0]['model']=='gpt-6.1-sol',name
  usages={x['payload']['response_id']:x['payload'] for x in rows if x['type']=='token_usage_record'}
  toolcalls=[x['payload'] for x in rows if x['type']=='response_item' and x['payload'].get('type') in ('custom_tool_call','function_call')]
  final=finals[0]['payload'];text=''.join(x['text'] for x in final['content'] if x['type']=='output_text')
  usage={k:sum(v['usage'].get(k,0) for v in usages.values()) for k in ['input_tokens','cached_input_tokens','output_tokens','reasoning_output_tokens','total_tokens']}
  record={'origin':'native_gpt-6.1-sol_subagent','agent_path':name,'thread_id':meta['id'],'model':context[0]['model'],'effort':context[0].get('effort'),'final_response':final,'final_text':text,'source_session_sha256':sha(path),'final_timestamp':finals[0]['timestamp'],'tool_calls':toolcalls,'usage_records':list(usages.values()),'usage':usage,'inference_responses_with_usage':len(usages),'completed':completed}
  filename=name.rsplit('/',1)[-1]+'.json';write(ROOT/'raw'/filename,record)
  seen[name]={'file':'raw/'+filename,'sha256':sha(ROOT/'raw'/filename),'usage':usage,'inference_responses_with_usage':len(usages),'tool_call_count':len(toolcalls),'model':record['model'],'effort':record['effort']}
 assert len(seen)==12,len(seen)
 write(ROOT/'generation_frozen.json',{'prelaunch_sha256':sha(ROOT/'prelaunch.json'),'agents':seen,'scope':'12 native agent episodes; each delivery+final may use multiple inference responses; no endpoint/PUT calls'})
 print(json.dumps({'agents':len(seen),'inference_responses':sum(x['inference_responses_with_usage'] for x in seen.values()),'tool_calls':sum(x['tool_call_count'] for x in seen.values()),'usage':{k:sum(x['usage'][k] for x in seen.values()) for k in next(iter(seen.values()))['usage']},'models':sorted({x['model'] for x in seen.values()}),'efforts':sorted({x['effort'] for x in seen.values()})}))
if __name__=='__main__':main()
