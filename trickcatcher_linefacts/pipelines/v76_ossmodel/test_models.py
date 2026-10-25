"""Both registered transports are tested with injected SDK; never network."""
import json
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock,patch
import pytest
from .paths import CONFIG,HERE,select_model
from .openrouter_client import OpenRouterClient


@pytest.mark.parametrize('choice',['gpt-oss-120b','deepseek-v4-flash'])
def test_model_payload_ledger_empty_no_resend_and_isolation(tmp_path,monkeypatch,choice):
    c=select_model(choice)
    monkeypatch.setenv('OPENROUTER_API_KEY','fake-offline-only')
    monkeypatch.setenv('OPENROUTER_MODEL',c['model'])
    monkeypatch.delenv('OPENROUTER_BASE_URL',raising=False)
    monkeypatch.delenv('OPENROUTER_MAX_USD',raising=False)
    usage=dict(cost='.001',prompt_tokens=100,completion_tokens=120000,completion_tokens_details={'reasoning_tokens':119999})
    sdk=Mock()
    sdk.chat.completions.create.return_value=SimpleNamespace(id='mock',model=c['model'],model_extra={},provider='Relace' if choice=='deepseek-v4-flash' else 'Near AI',
        usage=SimpleNamespace(model_dump=lambda:usage),choices=[SimpleNamespace(message=SimpleNamespace(content=''),finish_reason='length')])
    try:
        with patch('openai.OpenAI',return_value=sdk):
            client=OpenRouterClient(tmp_path/choice)
            request=dict(slot='test/slot',messages=[dict(role='system',content='Python'),dict(role='user',content='Visible execution feedback')],seed=12)
            result=client.complete(request)
            assert client.complete(request)==result
            assert sdk.chat.completions.create.call_count==1
            payload=sdk.chat.completions.create.call_args.kwargs
            assert [m['role'] for m in payload['messages']]==['system','user']
            assert payload['extra_body']['reasoning']==c['reasoning']
            assert payload['extra_body']['provider']==c['provider']
            if choice=='deepseek-v4-flash':
                assert payload['extra_body']['reasoning']=={'enabled':True}
                assert payload['extra_body']['provider']=={'only':['relace/fp4'],'allow_fallbacks':False}
                assert payload['max_tokens']==131072 and 'seed' not in payload
            entry=next(iter(client.ledger()['entries'].values()))
            assert entry['reasoning_tokens']==119999 and entry['finish_reason']=='length' and entry['empty_answer_count']==1
            assert entry['cost_usd']=='0.001'
            assert client.max_usd==Decimal(str(c['hard_max_usd']))
            client.close()
    finally:select_model('gpt-oss-120b')


def test_deepseek_metadata_pin_and_context():
    snapshot=json.loads((HERE/'assets/deepseek_endpoints_20261025.json').read_text())
    endpoint=next(e for e in snapshot['data']['endpoints'] if e['tag']=='relace/fp4')
    assert endpoint['status']==0 and endpoint['context_length']==1048576
    assert endpoint['max_completion_tokens']>=131072
    try:
        select_model('deepseek-v4-flash')
        from .context_preflight import check_request
        messages=[dict(role='system',content='Python'),dict(role='user',content='test')]
        assert check_request(messages)+131072<endpoint['context_length']
        with patch.dict(CONFIG['openrouter'],context_length=131072):
            with pytest.raises(ValueError):check_request(messages)
    finally:select_model('gpt-oss-120b')


def test_v34_scorer_and_concept_text_unchanged():
    import ast
    from . import ft_run
    parent=HERE.parent/'v34_ftplacebo'
    def selected(path,names):
        return {f.name:ast.dump(f,include_attributes=False) for f in ast.parse(path.read_text()).body
                if isinstance(f,ast.FunctionDef) and f.name in names}
    names=('score','score_record','guidance','placebo_guidance')
    assert selected(HERE/'ft_run.py',names)==selected(parent/'ft_run.py',names)
    assert (HERE/'ft_concepts.py').read_bytes()==(parent/'ft_concepts.py').read_bytes()
