"""Authored process/trace controls, never a model or paper reproduction."""
import json
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import client as c


class Failure(RuntimeError):pass


def fake(monkeypatch,items=('agent_message',),usage=True,stderr_text=''):
    calls=[]
    class Process:
        pid=99999999
        def __init__(self,cmd,**kwargs):
            calls.append(cmd);text='{"answer":5}';Path(cmd[cmd.index('-o')+1]).write_text(text)
            events=[{'type':'thread.started'},{'type':'turn.started'}]
            events += [{'type':'item.completed','item':{'type':kind,'text':text}} for kind in items]
            events += [{'type':'turn.completed','usage':{'input_tokens':100,'output_tokens':20} if usage else {}}]
            kwargs['stdout'].write(('\n'.join(json.dumps(x) for x in events)+'\n').encode());kwargs['stdout'].flush()
            kwargs['stderr'].write(stderr_text.encode());kwargs['stderr'].flush()
        def wait(self,timeout):return 0
    monkeypatch.setattr(c.subprocess,'Popen',Process);return calls


def req(slot='f00__meta'):
    return {'slot':slot,'stage':'meta','messages':[{'role':'system','content':'system original'}, {'role':'user','content':'user original'}]}


def test_single_attempt_exact_prompt_and_usage(tmp_path,monkeypatch):
    calls=fake(monkeypatch);client=c.Client(tmp_path,Failure,2);result=client.complete(req())
    assert result['input_tokens']==100 and result['output_tokens']==20 and result['tool_executions']==0
    assert client.complete(req())==result and len(calls)==1
    assert calls[0][-1]=='[SYSTEM]\nsystem original\n\n[USER]\nuser original'
    assert '--ignore-user-config' in calls[0] and 'web_search="disabled"' in calls[0]
    (tmp_path/'calls/f00__meta/response.json').unlink()
    with pytest.raises(Failure,match='consumed'):client.complete(req())
    assert len(calls)==1


@pytest.mark.parametrize('kind',['command_execution','mcp_tool_call','unknown_future_tool','plan'])
def test_any_tool_or_unknown_item_aborts(tmp_path,monkeypatch,kind):
    calls=fake(monkeypatch,items=(kind,));client=c.Client(tmp_path,Failure,2)
    with pytest.raises(c.ProtocolViolation):client.complete(req())
    assert len(calls)==1 and c.costs(tmp_path)['forbidden_item_count']==1


def test_missing_usage_not_zero(tmp_path,monkeypatch):
    fake(monkeypatch,usage=False)
    with pytest.raises(c.ProtocolViolation):c.Client(tmp_path,Failure,2).complete(req())
    assert c.costs(tmp_path)['unknown_usage_attempts']==1


def test_budget_does_not_spawn_second_slot(tmp_path,monkeypatch):
    calls=fake(monkeypatch);client=c.Client(tmp_path,Failure,1);client.complete(req())
    with pytest.raises(c.ProtocolViolation,match='cap'):client.complete(req('f01__meta'))
    assert len(calls)==1


@pytest.mark.parametrize('raw',['42','{"type":"item.completed","item":"bad"}',
                              '{"type":"item.completed","item":{"type":"agent_message","text":42}}'])
def test_malformed_events_are_safely_rejected(raw):
    assert c.inspect_events(raw)['invalid_lines'] > 0


@pytest.mark.parametrize('event',[{'type':'unexpected_tool','name':'shell'}, {'type':'turn.failed'},
                                 {'type':'error'}, {'type':'thread.started','model':'other-model'}])
def test_unknown_top_level_and_model_mismatch_are_rejected(event):
    assert c.inspect_events(json.dumps(event))['forbidden_items']


def test_only_exact_pre_turn_configuration_warnings_are_allowed():
    warning={'type':'item.completed','item':{'type':'error','message':next(iter(c.CONFIG_WARNINGS))}}
    before=c.inspect_events(json.dumps(warning)+'\n'+json.dumps({'type':'turn.started'}))
    assert not before['forbidden_items'] and len(before['configuration_warnings'])==1
    after=c.inspect_events(json.dumps({'type':'turn.started'})+'\n'+json.dumps(warning))
    assert after['forbidden_items']==['error']
    warning['item']['message']+=' changed'
    assert c.inspect_events(json.dumps(warning))['forbidden_items']==['error']


def test_router_attempt_without_json_tool_item_is_rejected(tmp_path,monkeypatch):
    fake(monkeypatch,stderr_text='ERROR codex_core::tools::router: error=code-mode host is disabled')
    with pytest.raises(c.ProtocolViolation):c.Client(tmp_path,Failure,1).complete(req())
    assert c.costs(tmp_path)['denied_router_attempts']==1
    assert not (tmp_path/'calls/f00__meta/response.json').exists()
