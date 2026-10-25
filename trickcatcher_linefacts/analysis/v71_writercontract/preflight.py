"""Public-spec and exact-tokenizer preflight; no model completion."""
import hashlib,json
from pathlib import Path
from trickcatcher_linefacts.pipelines.v71_writercontract.pipeline import validate_cohort
from trickcatcher_linefacts.pipelines.v71_writercontract.semantic_contract import writer_packet
from trickcatcher_linefacts.pipelines.v70_domainwriter.semantic_contract import writer_packet as old_packet
from trickcatcher_linefacts.pipelines.v71_writercontract.domain_constraints import public_domain
from trickcatcher_linefacts.pipelines.v71_writercontract.ngrok_client import NgrokClient,EndpointError

HERE=Path(__file__).resolve().parent
REQUESTS=HERE.parents[1]/'out/pipelines/v57_pathfault/ngrok_pilot6_20261024/preparation/requests.json'

def main():
    requests=json.loads(REQUESTS.read_text());validate_cohort(requests)
    result={'requests_sha256':hashlib.sha256(REQUESTS.read_bytes()).hexdigest(),'rows':[],'completion_calls':0}
    client=NgrokClient()
    try:
        result['metadata']=client.metadata()
        assert result['metadata']['model']=='qwen2.5-coder-32b-instruct'and result['metadata']['max_model_len']==8192
        for req in requests:
            domain=public_domain(req);packet=writer_packet(req);previous=old_packet(req)
            for key in ('source','spec_clauses','sites','public_examples','argument_types','condition_language','edit_forms'):
                assert packet[key]==previous[key]
            assert packet['hypothesis_fields']==previous['output_fields']
            messages=[{'role':'system','content':'Return a JSON object. Separate spec requirements from observed behavior; unknown claims remain unknown.'},
                      {'role':'user','content':json.dumps(packet,separators=(',',':'))}]
            tokens=client.tokenize(messages)
            row={'case_id':req['case_id'],'domain_status':domain['status'],'domain_rules':len(domain['rules']),
                 'domain_binding':domain['binding_sha256'],'domain_and_condition_equal_v70':True,
                 'prompt_tokens':tokens['count'],'output_tokens':1536,'limit':tokens['max_model_len'],
                 'fits':tokens['count']+1536<=tokens['max_model_len'],
                 'messages_sha256':hashlib.sha256(json.dumps(messages,sort_keys=True).encode()).hexdigest()}
            print(json.dumps(row),flush=True);result['rows'].append(row)
        result['passed']=len(result['rows'])==6 and all(x['fits']for x in result['rows'])
    except EndpointError as exc:result.update(passed=False,error=str(exc))
    with(HERE/'preflight.json').open('x')as f:json.dump(result,f,indent=2)
    if not result['passed']:raise SystemExit(1)

if __name__=='__main__':main()
