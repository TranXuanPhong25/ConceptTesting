"""Three S3 slots over verified unchanged accepted real-Qwen parents; no generation."""
import copy
import hashlib
import json
from pathlib import Path
from . import pilot,paths,pilot_fixtures,source_view,schemas
from .online_chain import OnlineChain
from .online_transport import Connection,Tokenizer,OnlineTransport
from .llm_client import atomic_json
from .v4_runtime import immutable
from trickcatcher_linefacts.pipelines.v21_qwenchain_singlejson import pilot as parent
HERE=Path(__file__).resolve().parent;ROOT=paths.DATA_OUT/'s3_replay'
FIXTURES=('f11','f12','f13')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def prepare():
    parent.report()  # Verifies entire old source/generation snapshot; no model calls.
    rows={r['fixture_id']:r for r in pilot_fixtures.cases()};packets=[]
    for ident in FIXTURES:
        old=parent.ROOT/'cases'/ident;state=json.loads((old/'state.json').read_text());context=json.loads((old/'context.json').read_text())
        row=rows[ident];task=source_view.prepare(row['source'],row['entry'],row['base'],valid_code=row['valid_code'])
        if task!=context['task']:raise ValueError('replay_task_drift')
        registry={};stages={}
        for stage in ('S1','S2'):
            rec=state['stages'][stage]
            if rec['state']!='valid' or rec['origin']!='qwen_endpoint':raise ValueError('accepted_Qwen_parent_required')
            obj=copy.deepcopy(rec['parsed_expanded_response']);schemas.validate(stage,obj,task,registry)
            artifact=schemas.register(stage,obj,task['task_hash'],registry)
            if artifact!=rec['artifact']:raise ValueError('replay_artifact_drift')
            stages[stage]=copy.deepcopy(rec)
        packets.append(dict(fixture=ident,task=task,registry=registry,stages=stages,parent_state_sha256=sha(old/'state.json'),parent_context_sha256=sha(old/'context.json')))
    immutable(ROOT/'parents.json',packets)
    immutable(ROOT/'protocol.json',dict(sources={p.name:sha(p) for p in HERE.iterdir() if p.is_file() and p.suffix in ('.py','.json','.jinja','.md')},parents_sha256=sha(ROOT/'parents.json'),scope='S3 only; exact accepted real-Qwen parent replay; no D_IO'))
    return packets

def main():
    atomic_json(ROOT/'status.json',dict(state='running',scheduled_S3_slots=3))
    try:
        packets=prepare();connection=Connection();pilot.verify_models(connection)
        tokenizer=Tokenizer(connection,ROOT/'tokenizer_cache');transport=OnlineTransport(connection,ROOT/'physical_calls.jsonl');rows=[]
        for packet in packets:
            chain=OnlineChain(packet['task'],ROOT/'cases'/packet['fixture'])
            if not chain.data['stages']:
                chain.data['stages']=packet['stages'];chain.data['registry']=packet['registry'];chain.data['replay_provenance']={k:packet[k] for k in ('fixture','parent_state_sha256','parent_context_sha256')};chain.save()
            rec=chain.run_stage('S3',tokenizer,transport)
            rows.append(dict(fixture=packet['fixture'],state=rec['state'],error=rec.get('reason'),artifact=rec.get('artifact'),raw=rec.get('raw')))
        immutable(ROOT/'generation_frozen.json',{str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'cases').rglob('*.json'))})
        calls=[json.loads(x) for x in (ROOT/'physical_calls.jsonl').read_text().splitlines()]
        immutable(ROOT/'report.json',dict(rows=rows,new_completion_attempts=len(calls),received_completions=sum(x['status']=='response_received' for x in calls),input_tokens=sum(x.get('n_in',0) for x in calls),output_tokens=sum(x.get('n_out',0) for x in calls),imported_parent_records=6,new_S1_S2_calls=0,semantic_accuracy=None,D_IO=None))
        atomic_json(ROOT/'status.json',dict(state='complete',scheduled_S3_slots=3))
    except BaseException as exc:
        atomic_json(ROOT/'status.json',dict(state='incomplete_resume_unchanged',error_type=type(exc).__name__));raise

if __name__=='__main__':main()
