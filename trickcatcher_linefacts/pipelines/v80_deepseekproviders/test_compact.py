import json
from .pipeline import prepare_case
from .test_pipeline import Client, REQUEST
from .semantic_contract import writer_packet


def test_real_writer_request_preserves_entire_packet_with_compact_encoding(tmp_path):
    client=Client()
    prepare_case(client,REQUEST,tmp_path)
    request=json.loads((tmp_path/'shared_writer'/'request.json').read_text())
    content=request['messages'][-1]['content']
    assert content==json.dumps(writer_packet(REQUEST),separators=(',',':'))
    assert json.loads(content)==writer_packet(REQUEST)
    assert json.loads(content)['writer_schema']=='v71_claim_trigger_edit'
    assert request['max_tokens']==1536 and client.calls==1
