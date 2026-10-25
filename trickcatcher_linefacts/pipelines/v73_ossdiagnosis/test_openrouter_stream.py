import json
from decimal import Decimal
import pytest
from .openrouter_stream import parse_sse,known_cost,payload,reservation,curl_command,MODEL


def frame(value):return 'data: '+json.dumps(value)+'\n\n'
def usage():return {'prompt_tokens':10,'completion_tokens':20,'cost':0.000003,'completion_tokens_details':{'reasoning_tokens':12}}


def test_comments_fragments_usage_and_repeated_terminal_frames():
    text=': OPENROUTER PROCESSING\n\n'+frame({'id':'gen-test','model':MODEL,'provider':'Near AI','choices':[{'index':0,'delta':{'content':'{"analysis":'},'finish_reason':None}]})
    text+=frame({'choices':[{'index':0,'delta':{'content':'"text"}'},'finish_reason':'stop'}]})
    text+=frame({'choices':[{'index':0,'delta':{'content':''},'finish_reason':'stop'}],'usage':usage()})+'data: [DONE]\n\n'
    r=parse_sse(text)
    assert r['stream_error']is None and r['content']=='{"analysis":"text"}'
    assert r['provider']=='Near AI'and r['done']and known_cost(r)==Decimal('0.000003')


def test_empty_choice_usage_frame_and_multiline_data():
    text='data: {"choices":[{"delta":{"content":"ok"},\ndata: "finish_reason":"stop"}]}\n\n'
    text+=frame({'choices':[],'usage':usage()})+'data: [DONE]\n\n'
    r=parse_sse(text);assert r['stream_error']is None and r['content']=='ok'and r['usage']==usage()


def test_error_before_stream_and_midstream_are_not_success():
    assert parse_sse('{"error":{"code":403,"message":"not logged"}}')['stream_error']=='api_error:403'
    text=frame({'choices':[],'error':{'code':'server_error','message':'disconnected'}})+'data: [DONE]\n\n'
    assert parse_sse(text)['stream_error']=='api_error:server_error'


@pytest.mark.parametrize('text,error',[
    (frame({'choices':[{'delta':{'content':'partial'},'finish_reason':'stop'}]}),'missing_done'),
    ('data: nonsense\n\ndata: [DONE]\n\n','invalid_sse_frame'),
    ('data: [DONE]\n\n'+frame({'choices':[]}),'data_after_done'),
])
def test_incomplete_or_invalid_streams_are_explicit(text,error):
    assert parse_sse(text)['stream_error']==error


@pytest.mark.parametrize('record',[{}, {'usage':{}},{'usage':{'prompt_tokens':10,'completion_tokens':20}},
    {'usage':{'prompt_tokens':10,'completion_tokens':20,'cost':True}},
    {'usage':{'prompt_tokens':10,'completion_tokens':20,'cost':-1}}])
def test_unknown_or_invalid_cost_stops_budget_accounting(record):
    with pytest.raises(ValueError):known_cost(record)


def test_paid_payload_routing_reasoning_and_conservative_reservation():
    body=payload([{'role':'user','content':'hello'}])
    assert body['model']==MODEL and body['stream']and body['provider']['sort']=='price'
    assert body['provider']['require_parameters']and body['reasoning']=={'effort':'low','exclude':True}
    assert body['max_tokens']==8192 and reservation(body)>Decimal('0.002')
    assert 4*reservation(body)<Decimal('0.02')


def test_curl_command_contains_no_authorization_or_environment_interpolation():
    command=curl_command('/tmp/public-request.json')
    assert '-N'in command and '--config'in command and '-'in command
    assert not any('Authorization'in arg or 'OPENROUTER_API_KEY'in arg or 'Bearer'in arg for arg in command)
