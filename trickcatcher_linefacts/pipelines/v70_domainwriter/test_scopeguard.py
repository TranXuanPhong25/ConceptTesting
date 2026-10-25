import json
import time
import pytest

from .semantic_contract import writer_packet, admit
from .joint_constructor import verify_input
from .pipeline import final_audit
from .continuation import sha, verify_manifest


def test_module_site_is_unsupported_without_native_execution(monkeypatch):
    from . import joint_constructor
    req={'case_id':'module','source':'limit = abs(-1)\ndef f(x):\n    """Return x."""\n    return x\n',
         'entry':'f','spec':'Return x.','public_examples':[{'arguments':'(2,)','expected':'2'}]}
    packet=writer_packet(req)
    from .binding_graph import build
    assert not any(s['scope']==[] for s in packet['sites'])
    site=next(s for s in build(req['source'])['nodes']if s['scope']==[] and s['kind']=='Call')
    p={'site_id':site['id'],'spec_clause_id':packet['spec_clauses'][0]['id'],
       'family':'INITIALIZATION','required_relation':'return input','observed_relation':'module call',
       'priority':1,'trigger':{'op':'literal','value':True},'event_predicate':{'op':'literal','value':True},'alternative':None}
    accepted,rejected=admit(req,[p])
    assert not accepted and rejected[0]['reason']=='ValueError:unsupported_module_scope'


def test_continuation_verifies_both_original_and_imported_bytes(tmp_path):
    origin=tmp_path/'v62';out=tmp_path/'v63'
    origin.mkdir();out.mkdir()
    for folder in (origin,out):(folder/'response.json').write_text('{"original":true}')
    manifest={'origin':str(origin),'original_inventory':{'response.json':sha(origin/'response.json')},
              'imported_inventory':{'response.json':sha(out/'response.json')}}
    (out/'continuation.json').write_text(json.dumps(manifest))
    assert verify_manifest(out)==manifest
    (out/'response.json').write_text('{}')
    with pytest.raises(ValueError,match='continuation_import_integrity'):verify_manifest(out)
    (origin/'response.json').write_text('{}')
    with pytest.raises(ValueError,match='continuation_original_integrity'):verify_manifest(out)
