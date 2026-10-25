import json
import pytest
from .pipeline import generate_case,contexts,final_audit,check_freeze


REQUEST={'case_id':'fixture','source':'def f(x):\n    """Add one."""\n    return x+1\n','entry':'f','spec':'Add one.',
         'public_examples':[{'arguments':'(1,)','expected':'2'}]}


class Client:
    """Authored transport fixture only; no simulated research outcomes."""
    model='fixture';calls=0
    def tokenize(self,messages):return {'count':100,'max_model_len':8192}
    def complete(self,messages,max_tokens,seed):
        self.calls+=1
        payload=json.loads(messages[-1]['content'])
        result={'hypotheses':[]} if 'sites'in payload else {'tests':[{'arguments':'(2,)','expected':'3'}],'reason':'fixture'}
        return {'content':json.dumps(result),'finish_reason':'stop','input_tokens':1,'output_tokens':1,'model':'fixture'}


def test_pipeline_runs_all_stages_and_resumes_without_more_calls(tmp_path):
    client=UsefulClient();result=generate_case(client,USEFUL_REQUEST,tmp_path)
    assert set(result['arms'])=={'plain','explicit_pattern','concept','equal_evidence_raw','inputs_only'}
    assert client.calls==18
    assert generate_case(client,USEFUL_REQUEST,tmp_path)==result and client.calls==18
    assert all(v['final_realization']['rows'][0]['status']=='parsed' for v in result['arms'].values())


def test_final_audit_does_not_inherit_witness_certificate():
    result=final_audit(REQUEST,[{'arguments':'notliteral','expected':'3'}],[])
    assert result['rows'][0]['status']=='malformed'


def test_changed_source_refuses_cached_case(tmp_path):
    client=UsefulClient();generate_case(client,USEFUL_REQUEST,tmp_path)
    with pytest.raises(ValueError,match='protocol_drift'):
        generate_case(client,dict(USEFUL_REQUEST,source=USEFUL_REQUEST['source']+'\n'),tmp_path)


def test_baseline_context_contains_exactly_one_source_copy():
    c=contexts(REQUEST,{'records':[]})
    assert 'source'not in c['explicit_pattern']and REQUEST['source']in c['explicit_pattern']['instruction']
    assert all(c[a]['known_bug_premise']==c['plain']['known_bug_premise']for a in c)


from .test_contractfix import REQ as USEFUL_REQUEST, proposal


class UsefulClient(Client):
    def complete(self,messages,max_tokens,seed):
        payload=json.loads(messages[-1]['content'])
        if 'sites' in payload:
            self.calls+=1
            return {'content':json.dumps({'hypotheses':[proposal()]}),'finish_reason':'stop','input_tokens':1,'output_tokens':1,'model':'fixture'}
        return super().complete(messages,max_tokens,seed)
