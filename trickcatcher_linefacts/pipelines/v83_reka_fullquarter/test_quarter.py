"""Verify treatment dispatch, original baseline identity and accounting failures."""
from pathlib import Path
from decimal import Decimal
import json,random,threading
from unittest.mock import patch
import pytest
from . import paths,datasets,combined_generation,scoring,gen_prompts,prompts,v4_prompts
from .stream_wire import payload,MODEL
from .stream_client import OpenRouterClient
from .openrouter_client import AccountingUnknown,BudgetExceeded


def test_fixed_subset_and_package():
    from ..v11_fair import v4_prompts as old_v4,prompts as old_prompts
    parent=json.loads((datasets.HE_ROOT/'tasks_hybrid.json').read_text())['tasks']
    ids=sorted(t['task'] for t in parent if t['split']=='dev')
    selected=datasets.cohort('humaneval')
    assert [t['task'] for t in selected]==sorted(random.Random(20261026).sample(ids,28))
    for t in selected:
        assert prompts.build('concept',t)==old_prompts.build('concept',t)
        assert v4_prompts.seed(t['task'],'concept',0)==old_v4.seed(t['task'],'concept',0)
    assert paths.CONFIG['K']==1 and paths.CONFIG['combined']['arms']==['concept-hybrid','concept-hybrid-ft']


def test_pair_denominator_and_partial_rule():
    rows=[dict(task=3,arm=arm,sample=0,detected=arm=='concept-hybrid-ft',false_positive=0)
          for arm in paths.CONFIG['combined']['arms']]
    assert scoring.paired(rows,1,1)['primary']['wins']==1
    assert scoring.paired(rows,1,1)['primary']['rule_met'] is True
    assert scoring.paired(rows,1,1,partial=True)['primary']['rule_met'] is None
    with pytest.raises(ValueError):scoring.paired(rows[:1],1,1)
    with pytest.raises(ValueError):scoring.paired([dict(r,sample=1) for r in rows],1,1)
    with pytest.raises(ValueError):scoring.paired([rows[0],dict(rows[1],arm='plain')],1,1)


def fake_client(tmp_path):
    c=OpenRouterClient.__new__(OpenRouterClient);c.root=tmp_path;c.model=MODEL;c.max_usd=Decimal('4.2')
    c.lock=threading.Lock();c.halted=False;c.cost_path=tmp_path/'cost.json'
    return c


def success():
    return dict(content='assert f(0) == 0',stream_error=None,model=MODEL,provider='DeepInfra',
                finish_reason='stop',generation_id='test-generation',
                usage={'prompt_tokens':10,'completion_tokens':20,'cost':.0000042})


def test_wire_exact_provider_and_rejection_reserved_retry(tmp_path):
    wire=payload([dict(role='system',content='x'),dict(role='user',content='y')])
    assert wire['provider']['only']==['deepinfra/fp8'] and wire['provider']['allow_fallbacks'] is False
    assert 'seed' not in wire and wire['stream'] and wire['response_format']=={'type':'text'}
    c=fake_client(tmp_path)
    rejected=dict(content='',stream_error='api_error:429',generation_id=None,usage=None)
    raw=json.dumps({'error':{'code':429,'metadata':{'limit_source':'upstream_provider_shared_pool'}}})
    req=dict(slot='chat/a',messages=wire['messages'],seed=1)
    with patch.object(__import__(OpenRouterClient.__module__,fromlist=['dispatch']),'dispatch',side_effect=[(rejected,raw,''),(success(),'','')]),patch('time.sleep'):
        answer=c.complete(req)
    assert answer['attempts']==2
    entries=list(c.ledger()['entries'].values())
    assert entries[0]['state']=='upstream_rejected_unbilled' and entries[0]['cost_usd'] is None
    assert Decimal(entries[0]['reserved_usd'])>0 and entries[1]['cost_usd'] is not None
    assert c.complete(req)==answer


def test_unknown_no_retry_and_budget_before_dispatch(tmp_path):
    import importlib
    module=importlib.import_module(OpenRouterClient.__module__)
    c=fake_client(tmp_path);req=dict(slot='chat/a',messages=[dict(role='system',content='x'),dict(role='user',content='y')],seed=1)
    with patch.object(module,'dispatch',return_value=(dict(stream_error='missing_done',generation_id='a',usage=None),'partial','')) as dispatch:
        with pytest.raises(AccountingUnknown):c.complete(req)
        with pytest.raises(AccountingUnknown):c.complete(dict(req,slot='chat/b'))
        assert dispatch.call_count==1
    c=fake_client(tmp_path/'cap');c.max_usd=Decimal('.000001')
    with patch.object(module,'dispatch') as dispatch:
        with pytest.raises(BudgetExceeded):c.complete(req)
        dispatch.assert_not_called()


def test_only_two_actual_arms_original_first_prompt_seed(tmp_path):
    from .prepare_cpu import load
    rows=load('humaneval');assert rows is not None
    chosen=[r for r in rows if r['baseline']['task']==3]
    assert len(chosen)==1
    task=chosen[0]['baseline'];calls=[]
    class Client:
        model=MODEL
        def chat(self,messages,seed,**kwargs):
            calls.append((messages,seed))
            return dict(text='',key=str(len(calls)),params={},n_in=1,n_out=1,seconds=0,cost_usd=0,transport_attempts=1)
    combined_generation.run(chosen,tmp_path/'generation',Path(paths.CONFIG['V4_PYTHON']),client=Client(),k=1,workers=1)
    generated=[json.loads(s) for s in (tmp_path/'generation/gen.jsonl').read_text().splitlines()]
    assert len(generated)==2 and {r['arm'] for r in generated}==set(paths.CONFIG['combined']['arms'])
    assert {p.name for p in (tmp_path/'generation/artifacts/3/0').iterdir()}==set(paths.CONFIG['combined']['arms'])
    assert calls[0]==(gen_prompts.messages(*prompts.build('concept',task)),v4_prompts.seed(3,'concept',0))
    assert all(r['llm_calls']<=8 for r in generated)


def test_real_worker_generation_and_scoring_three_tasks(tmp_path):
    import ast
    from .prepare_cpu import load
    from .run_v81 import freeze
    selected=load('humaneval')[:3]
    class Client:
        model=MODEL
        def chat(self,messages,seed,**kwargs):
            text='\n'.join(m['content'] for m in messages)
            t=next(p['baseline'] for p in selected if p['baseline']['put'].rstrip() in text
                   or p['baseline']['entry']+'(' in text)
            if 'Hypothesis' in messages[0]['content']:
                raw='def strategy():\n    return st.sampled_from('+repr(datasets.public_inputs(t))+')'
            else:
                assertions=[ast.unparse(n).replace('candidate(',t['entry']+'(')
                            for n in ast.walk(ast.parse(t['base'])) if isinstance(n,ast.Assert)]
                raw='\n'.join(assertions[:1])
            return dict(text=raw,key=str(seed),params={},n_in=1,n_out=1,seconds=0,cost_usd=0,transport_attempts=1)
    run=tmp_path/'humaneval/generation'
    combined_generation.run(selected,run,Path(paths.CONFIG['V4_PYTHON']),client=Client(),k=1,workers=1)
    freeze(tmp_path)
    reports=scoring.humaneval(run,tmp_path,k=1)
    assert set(reports)=={'o0','ref','full'}
    assert all(r['tasks']==3 and r['K']==1 for r in reports.values())
    assert all(len(r['rows'])==6 for r in reports.values())
