"""Engineering verification only; no inference, no production outputs."""
import ast
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import socket
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from . import paths,datasets,combined_generation,combined_facts,provenance,scoring,v4_runtime
from .context_preflight import check_request
from .llm_client import atomic_json

PYTHON=Path(paths.CONFIG['V4_PYTHON'])


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(*a,**kw):raise AssertionError('network forbidden in CPU verification')
    monkeypatch.setattr(socket.socket,'connect',blocked)
    monkeypatch.setattr(socket,'create_connection',blocked)
    yield
    paths.select_model('gpt-oss-120b')


def test_parent_and_unchanged_port():
    p=paths.HERE.parent/'v31_faulttemplate/ft_concepts.py'
    assert (paths.HERE/'ft_concepts.py').read_bytes()==p.read_bytes()
    m=json.loads((paths.HERE/'PARENT.json').read_text())
    for name in ('fair_generation.py','run_v4.py','v4_prompts.py','prompts.py','gen_prompts.py','spec_facts.py','oracle_b01.py','scorer.py','v4_facts.py'):
        assert provenance.sha(paths.HERE/name)==m['files'][name]
    assert (paths.HERE/'tracer.py').read_bytes()==(paths.HERE.parent/'v7_vp/tracer.py').read_bytes()


def test_all_113_disabled_bundles_prompts_seeds():
    from ..v11_fair import prompts as old_prompts,gen_prompts as old_gen,v4_prompts as old_v4
    from . import prompts,gen_prompts,v4_prompts
    rows=datasets.cohort('humaneval');assert len(rows)==113
    count=0
    for t in rows:
        out=combined_facts.merge(t,[],[],[],enabled=False)
        assert out==t
        for arm in ('plain','concept','placebo'):
            assert prompts.build(arm,out)==old_prompts.build(arm,t);count+=1
        for fact in t['concept_meta']:
            assert v4_prompts.hybrid_messages(out,fact,[])==old_v4.hybrid_messages(t,fact,[]);count+=1
        assert gen_prompts.strict_oracle_messages(out,[])==old_gen.strict_oracle_messages(t,[])
        for arm in old_v4.ARMS:
            for sample in range(3):assert v4_prompts.seed(t['task'],arm,sample)==old_v4.seed(t['task'],arm,sample)
    assert count>=339


def test_fixed_merge_ranking_and_separation():
    t=dict(task=2,entry='f',tool_inputs=['f(1)'],concept_meta=[],concept_facts=[])
    normal=[dict(kind='STMT',line=i,block=i,text=f'L{i} never executed',reached=True,witness_call='f(1)') for i in (1,3,5)]
    faults=[dict(kind='FAULT',line=i,fault_type='VALUE',survivors=2,distinguished=d,text=f'L{i} wrong value',reached=True,witness_call='f(98765)') for i,d in ((2,1),(4,3))]
    r=combined_facts.merge(t,normal,faults,[(98765,)])
    assert [f['kind'] for f in r['concept_meta']]==['STMT','FAULT','STMT']
    assert r['concept_meta'][1]['line']==4
    assert '98765' not in '\n'.join(r['concept_facts']) and 'f(98765)' in r['tool_inputs']
    assert len(combined_facts.merge(t,normal,faults,[])['concept_meta'])<=3


def test_cohort_has_public_only_vibepass():
    rows=datasets.cohort('vibepass_half');assert len(rows)==33
    for t in rows:
        assert 'exec(' not in t['base'] and 'canonical_solution' not in t and 'reference' not in t
        assert t['mined_valid_src']=='def valid(*args):\n    return True\n'


def test_cost_and_caps():
    from .cost import estimate
    e=estimate();assert e['estimate_usd']=='6.40475136'
    assert Decimal(e['hard_cap_usd'])==Decimal(str(paths.CONFIG['openrouter']['hard_max_usd']))
    assert sum(r['logical_calls'] for r in e['rows'])==14892
    assert paths.CONFIG['K']==3 and all(paths.CONFIG[x] for x in paths.FAIR_FLAGS)


def test_context_retries_and_overflow():
    from .transport import user_feedback
    assert check_request(user_feedback([dict(role='system',content='Python'),dict(role='user',content='test'),dict(role='assistant',content='bad'),dict(role='user',content='correct')]))>0
    with patch('trickcatcher_linefacts.pipelines.v77_combined.context_preflight.token_count',return_value=131072):
        with pytest.raises(ValueError):check_request([])


def fake_transport(tmp_path,responses):
    from .openrouter_client import OpenRouterClient
    import threading
    c=OpenRouterClient.__new__(OpenRouterClient)
    c.root=tmp_path;c.model=paths.CONFIG['openrouter']['model'];c.max_usd=Decimal('0.04');c.lock=threading.Lock();c.halted=False
    c.cost_path=tmp_path/'cost.json'
    c.sdk=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kw:responses.pop(0))))
    return c


def response(cost='0.001',text='assert f(1) == 1',finish='stop'):
    usage=SimpleNamespace(model_dump=lambda:dict(cost=cost,prompt_tokens=10,completion_tokens=10))
    return SimpleNamespace(id='mock-id',model=paths.CONFIG['openrouter']['model'],model_extra={},usage=usage,
                           choices=[SimpleNamespace(message=SimpleNamespace(content=text),finish_reason=finish)])


def test_ledger_retry_and_cached_response(tmp_path):
    c=fake_transport(tmp_path,[response(finish='length'),response()])
    req=dict(slot='a',messages=[dict(role='system',content='Python'),dict(role='user',content='test')],seed=1)
    r=c.complete(req);assert r['attempts']==1 and len(c.ledger()['entries'])==1
    assert c.complete(req)==r
    assert c.spent()==.001


def test_unknown_and_cap_block_before_dispatch(tmp_path):
    from .openrouter_client import AccountingUnknown,BudgetExceeded
    c=fake_transport(tmp_path,[response(cost=None)])
    req=dict(slot='a',messages=[dict(role='system',content='Python'),dict(role='user',content='test')],seed=1)
    with pytest.raises(AccountingUnknown):c.complete(req)
    with pytest.raises(AccountingUnknown):c.complete(dict(req,slot='b'))
    assert c.ledger()['entries']['a/attempt-1']['reserved_usd'] is not None
    c=fake_transport(tmp_path/'cap',[]);c.max_usd=Decimal('.00001')
    with pytest.raises(BudgetExceeded):c.complete(req)


def test_403_resume_preserves_global_ledger(tmp_path):
    from .openrouter_client import WorkspacePaused
    from .run_v77 import archive_denials
    import openai,httpx
    root=tmp_path/'transport';root.mkdir()
    c=fake_transport(root,[])
    def denied(**kw):raise openai.PermissionDeniedError('denied',response=httpx.Response(403,request=httpx.Request('POST','https://openrouter.ai/api/v1/chat/completions')),body={})
    c.sdk.chat.completions.create=denied
    req=dict(slot='chat/a',messages=[dict(role='system',content='Python'),dict(role='user',content='test')],seed=1)
    with pytest.raises(WorkspacePaused):c.complete(req)
    before=c.ledger();archive_denials(tmp_path);assert c.ledger()==before
    assert json.loads((root/'calls/chat/a/attempts.json').read_text())==[]
    c.halted=False;c.sdk.chat.completions.create=lambda **kw:response()
    assert c.complete(req)['finish_reason']=='stop'
    assert len(c.ledger()['entries'])==2


class MockClient:
    model=paths.CONFIG['openrouter']['model']
    def __init__(self,prepared):
        self.requests=[];self.task_order=[];self.prepared=prepared;self.model=paths.CONFIG['openrouter']['model']
    def chat(self,messages,seed,**kw):
        text='\n'.join(m['content'] for m in messages)
        t=next(p['baseline'] for p in self.prepared if p['baseline']['put'].rstrip() in text or p['baseline']['entry']+'(' in text)
        both=next(p for p in self.prepared if p['baseline']['task']==t['task'])
        if 'Hypothesis' in messages[0]['content']:
            candidates=[]
            for variant in both['baseline'],both['combined']:
                for f in variant['concept_meta']:
                    if f.get('witness_call'):
                        fn=ast.parse(f['witness_call'],mode='eval').body
                        try:candidates.append(tuple(ast.literal_eval(a) for a in fn.args))
                        except (ValueError,SyntaxError):pass
            candidates+=datasets.public_inputs(t)
            raw='def strategy():\n    return st.sampled_from('+repr(candidates[:12])+')'
        else:
            public=[]
            for node in ast.walk(ast.parse(t['base'])):
                if isinstance(node,ast.Assert):
                    expr=node.test
                    if isinstance(expr,ast.Call) and isinstance(expr.func,ast.Name) and expr.func.id=='_heldout_same':
                        s='assert '+ast.unparse(expr.args[0])+' == '+ast.unparse(expr.args[1])
                    else:s=ast.unparse(node)
                    public.append(s.replace('candidate(',t['entry']+'('))
            # Deliberate mock errors are engineering inputs, never efficacy data.
            raw='\n'.join(public[:1]) or 'assert '+t['entry']+'(0) == None'
        assert [m['role'] for m in messages]==['system','user']
        self.task_order.append(t['task'])
        self.requests.append((messages,seed));check_request(messages)
        return dict(text=raw,key=str(seed),params={},n_in=1,n_out=1,seconds=0,cache_hit=False,transport_attempts=1)


@pytest.mark.parametrize('model',['gpt-oss-120b','deepseek-v4-flash'])
@pytest.mark.parametrize('name,ids',[('humaneval',[2,3,4]),('vibepass_half',[36,39,46])])
def test_mock_end_to_end_three_real_tasks(tmp_path,name,ids,model):
    paths.select_model(model)
    selected=[t for t in datasets.cohort(name) if t['task'] in ids];assert len(selected)==3
    from .prepare_cpu import load,ROOT
    manifest=paths.HERE/'assets/cpu_prepared_manifest.json'
    if manifest.exists():
        cached=load(name)
    else:cached=None
    prepared=([p for p in cached if p['baseline']['task'] in ids] if cached else
              [datasets.prepare_one(name,t,tmp_path/'prepare'/str(t['task']),PYTHON) for t in selected])
    client=MockClient(prepared);root=tmp_path/'experiment';run=root/name/'generation'
    combined_generation.run(prepared,run,PYTHON,client=client,k=3,workers=1)
    rows=list(map(json.loads,(run/'gen.jsonl').read_text().splitlines()));assert len(rows)==54
    for row in rows:
        assert row['llm_calls']<=8 and len(row['assertions'])<=20
        group={r['arm']:r for r in rows if (r['task'],r['sample'])==(row['task'],row['sample'])}
        for arm in ('placebo-hybrid','plain-hybrid'):
            assert group[arm]['round2_strategy_requests']==group['concept-hybrid-ft']['round2_strategy_requests']
    from .run_v77 import freeze
    freeze(root);scoring.verify_freeze(root)
    if name=='vibepass_half':report=scoring.vibepass(run,root,k=3);assert report['tasks']==3
    else:
        report=scoring.humaneval(run,root,k=3);assert report['ref']['tasks']==3
    assert client.requests
    assert client.task_order==sorted(client.task_order,key=ids.index)
    paths.select_model('gpt-oss-120b')


def test_partial_prefix_selection_and_no_verdict(tmp_path,monkeypatch):
    from .run_v77 import finalize_partial
    run=tmp_path/'vibepass_half/generation';arms=paths.CONFIG['combined']['arms']
    atomic_json(run/'tasks.json',dict(tasks=[dict(task=36),dict(task=39)]))
    for task in (36,39):
        for sample in range(3):
            for arm in arms:
                if (task,sample,arm)==(39,2,'toolinput'):continue
                atomic_json(run/'artifacts'/str(task)/str(sample)/arm/'result.json',dict(task=task,arm=arm,sample=sample))
    monkeypatch.setattr(scoring,'vibepass',lambda out,root:json.loads((out/'tasks.json').read_text()))
    result=finalize_partial(tmp_path,'vibepass_half')
    assert result['tasks']==[dict(task=36)]
    scoring.verify_freeze(tmp_path)
    status=json.loads((tmp_path/'partial_status.json').read_text())
    assert status['complete_tasks']==[36]
    rows=[dict(task=36,arm=arm,sample=s,detected=arm=='concept-hybrid-ft',false_positive=0) for s in range(3) for arm in arms]
    assert scoring.paired(rows,1,3,partial=True)['primary']['rule_met'] is None


def test_fault_concept_hit_inside_class_method(tmp_path):
    from .run_v4 import classify
    src='class Solution:\n    def compute(self,x):\n        return x+1\ndef f(x):\n    return Solution().compute(x)\n'
    alternative=src.replace('x+1','x-1')
    fact=dict(kind='FAULT',line=3,text='Arithmetic adequacy',alternative_sources=[alternative])
    task=dict(task=999,entry='f',put=src,base='def check(candidate):\n    assert candidate(1)==2\n',
        mined_valid_src='def valid(*args):\n    return True\n',concept_meta=[fact])
    result=classify(task,tmp_path,PYTHON,candidates=[dict(input_repr='(2,)')],shown=[fact])
    assert result['summary']['concept_hit_counts']==[1] and result['summary']['shown_hit_counts']==[1]
