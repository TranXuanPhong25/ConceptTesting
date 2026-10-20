"""Offline transport/budget safety tests with fake replies, no real env/API access."""
import json
import pytest
from .router_transport import Router,StopRun
from . import router_transport

class Reply:
    status_code=200
    def __init__(self,cost=.00001,usage=True):self.cost=cost;self.usage=usage
    def json(self):
        d=dict(choices=[dict(message={'content':'{}'},finish_reason='stop')],model=router_transport.C['model'])
        if self.usage:d['usage']=dict(prompt_tokens=10,completion_tokens=2,cost=self.cost)
        return d
class HTTP:
    def __init__(self,reply=None):self.reply=reply or Reply();self.calls=0
    def post(self,*a,**k):self.calls+=1;return self.reply

@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv('OPENROUTER_API_KEY','test-not-a-real-key');monkeypatch.setenv('OPENROUTER_MODEL',router_transport.C['model']);monkeypatch.setenv('OPENROUTER_MAX_USD','1');monkeypatch.setenv('OPENROUTER_BASE_URL','https://openrouter.ai/api/v1')

def test_cache_exact_request_no_paid_repeat(tmp_path):
    h=HTTP();r=Router(tmp_path,h);a=r.complete('S1',[],1);assert r.complete('S1',[],1)==a and h.calls==1
    assert json.loads((tmp_path/'ledger.json').read_text()).popitem()[1]['cost_usd']==.00001

def test_missing_usage_is_unknown_and_stops(tmp_path):
    h=HTTP(Reply(usage=False));r=Router(tmp_path,h)
    with pytest.raises(StopRun):r.complete('S1',[],1)
    with pytest.raises(StopRun):Router(tmp_path,h).complete('S1',[],1)
    assert h.calls==1 and r.total()>0

def test_budget_reserves_before_dispatch(tmp_path,monkeypatch):
    monkeypatch.setenv('OPENROUTER_MAX_USD','.000001');h=HTTP();r=Router(tmp_path,h)
    with pytest.raises(StopRun,match='budget_limit'):r.complete('S1',[],1)
    assert h.calls==0

def test_oversized_cost_stops_but_preserves_actual(tmp_path):
    h=HTTP(Reply(cost=.1));r=Router(tmp_path,h)
    with pytest.raises(StopRun,match='protocol'):r.complete('S1',[],1)
    assert r.total()==.1
    with pytest.raises(StopRun):r.complete('S2',[],2)
    assert h.calls==1

@pytest.mark.parametrize('cap',['nan','inf','-1','0'])
def test_bad_cap(tmp_path,monkeypatch,cap):
    monkeypatch.setenv('OPENROUTER_MAX_USD',cap)
    with pytest.raises(StopRun):Router(tmp_path,HTTP())
