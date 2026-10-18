"""Mechanical scoring of unmodified one-shot subagent replies; no semantic matcher."""
from pathlib import Path
import json,hashlib,sys
REPO=Path(__file__).resolve().parents[3];sys.path.insert(0,str(REPO))
from trickcatcher_linefacts.pipelines.v22_qwenchain_audit import schemas,prompt_aliases
HERE=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    manifest=json.loads((HERE/'manifest.json').read_text());rows=[]
    for entry in manifest['probes']:
        directory=HERE/entry['packet'];assert sha(directory/'packet.json')==entry['packet_sha256']
        parent=REPO/entry['parent_case'];root=parent.parent.parent
        protocol=json.loads((root/'protocol.json').read_text())
        version=entry['parent_case'].split('/pipelines/')[1].split('/')[0];source=REPO/'trickcatcher_linefacts/pipelines'/version
        assert all(sha(source/name)==digest for name,digest in protocol['sources'].items())
        snapshot=json.loads((root/'generation_frozen.json').read_text())
        assert all(sha(root/name)==digest for name,digest in snapshot.items())
        saved=json.loads((parent/'requests'/(entry['request_key']+'.json')).read_text())['request']
        assert json.loads((directory/'packet.json').read_text())['messages']==saved['payload']['messages']
        state=json.loads((parent/'state.json').read_text());task=json.loads((parent/'context.json').read_text())['task']
        artifact={s:r['artifact'] for s,r in state['stages'].items() if r['state']=='valid' and (s in ('S1','S2') if entry['stage']=='S3' else False)}
        _,back=prompt_aliases.maps(task,artifact)
        raw=(directory/'response.txt').read_text();row=dict(entry,response_sha256=sha(directory/'response.txt'),state='failed',raw=raw)
        try:
            obj,_=schemas.extract(raw);expanded=prompt_aliases.expand(entry['stage'],obj,back)
            schemas.validate(entry['stage'],expanded,task,state['registry'])
            row.update(state='valid',parsed=obj)
        except (ValueError,TypeError,KeyError) as exc:row['error']=str(exc)
        rows.append(row)
    result=dict(model=manifest['model'],rows=rows,valid=sum(r['state']=='valid' for r in rows),qwen_valid=sum(r['qwen_state']=='valid' for r in rows),attempts=6,token_cost='unavailable through subagent harness; unmatched to Qwen budgets',D_IO=None,scope='six targeted seen-case probes; agent harness differs; not end-to-end or causal model isolation')
    (HERE/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
    for row in rows:print(row['packet'],row['stage'],row['fixture'],row['state'],row.get('error'),row.get('parsed',{}).get('status'),[(x.get('verdict'),x.get('divergence_condition')) for x in row.get('parsed',{}).get('comparisons',[])])

if __name__=='__main__':main()
