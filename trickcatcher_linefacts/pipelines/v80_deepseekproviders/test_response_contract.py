import json
import pytest
from .writer_compiler import compile_response
from .test_contractfix import REQ,writer_proposal
from .test_pipeline import Client
from .pipeline import prepare_case,admission_gate


@pytest.mark.parametrize('value',[{},writer_proposal(),{'hypotheses':None},{'hypotheses':{}},{'hypotheses':[],'site_id':'unexpected'},[]])
def test_malformed_envelopes_never_become_silent_abstention(value):
    accepted,rejected,compiled=compile_response(REQ,{'error':None,'value':value})
    assert not accepted and rejected
    assert compiled['response_contract']['status']=='invalid'
    assert compiled['response_contract']['explicit_abstention'] is False


def test_explicit_empty_and_valid_claim_are_distinguished():
    accepted,rejected,compiled=compile_response(REQ,{'error':None,'value':{'hypotheses':[]}})
    assert not accepted and not rejected and compiled['response_contract']['explicit_abstention']
    accepted,rejected,compiled=compile_response(REQ,{'error':None,'value':{'hypotheses':[writer_proposal()]}})
    assert len(accepted)==1 and not rejected and not compiled['response_contract']['explicit_abstention']


def test_incomplete_response_is_not_abstention_even_if_parsed_value_looks_empty():
    accepted,rejected,compiled=compile_response(REQ,{'error':'incomplete_completion','value':{'hypotheses':[]}})
    assert not accepted and rejected[0]['reason']=='writer_response_error:incomplete_completion'
    assert not compiled['response_contract']['explicit_abstention']


def test_single_object_integration_preserves_error_across_resume(tmp_path):
    class Single(Client):
        def complete(self,messages,max_tokens,seed):
            self.calls+=1
            return {'content':json.dumps(writer_proposal()),'finish_reason':'stop','input_tokens':1,'output_tokens':1}
    client=Single();first=prepare_case(client,REQ,tmp_path)
    assert not first[0] and first[1][0]['reason']=='writer_outer_hypotheses_object_required'
    assert prepare_case(client,REQ,tmp_path)==first and client.calls==1
    receipt=json.loads((tmp_path/'writer_compilation.json').read_text())
    assert receipt['response_contract']['status']=='invalid'
