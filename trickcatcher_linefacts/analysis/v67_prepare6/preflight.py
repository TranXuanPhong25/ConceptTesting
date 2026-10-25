"""Read-only endpoint/tokenizer preflight; no completion dispatch."""
import hashlib
import json
from pathlib import Path
from trickcatcher_linefacts.pipelines.v67_evidencegate_compact.pipeline import validate_cohort
from trickcatcher_linefacts.pipelines.v67_evidencegate_compact.semantic_contract import writer_packet
from trickcatcher_linefacts.pipelines.v65_evidencegate.semantic_contract import writer_packet as old_packet
from trickcatcher_linefacts.pipelines.v67_evidencegate_compact.ngrok_client import NgrokClient,EndpointError

HERE=Path(__file__).resolve().parent
REQUESTS=Path('trickcatcher_linefacts/out/pipelines/v57_pathfault/ngrok_pilot6_20261024/preparation/requests.json')

def main():
    requests=json.loads(REQUESTS.read_text());validate_cohort(requests)
    result={'request_sha256':hashlib.sha256(REQUESTS.read_bytes()).hexdigest(),'rows':[], 'completion_calls':0}
    client=NgrokClient()
    try:
        result['metadata']=client.metadata()
        assert result['metadata']['model']=='qwen2.5-coder-32b-instruct' and result['metadata']['max_model_len']==8192
        for request in requests:
            packet=writer_packet(request)
            assert packet==old_packet(request)
            messages=[{'role':'system','content':'Return a JSON object. Separate spec requirements from observed behavior; unknown claims remain unknown.'},
                      {'role':'user','content':json.dumps(packet,separators=(',',':'))}]
            t=client.tokenize(messages)
            row=dict(case_id=request['case_id'],prompt_tokens=t['count'],output_tokens=1536,
                     limit=t['max_model_len'],fits=t['count']+1536<=t['max_model_len'],
                     complete_packet_equal=True,messages_sha256=hashlib.sha256(json.dumps(messages,sort_keys=True).encode()).hexdigest())
            result['rows'].append(row)
            print(json.dumps(row),flush=True)
        result['passed']=all(r['fits'] for r in result['rows']) and len(result['rows'])==6
    except EndpointError as exc:
        result['passed']=False;result['error']=str(exc)
    path=HERE/'preflight_compact.json'
    with path.open('x') as f:json.dump(result,f,indent=2)
    if not result['passed']:raise SystemExit(1)

if __name__=='__main__':main()
