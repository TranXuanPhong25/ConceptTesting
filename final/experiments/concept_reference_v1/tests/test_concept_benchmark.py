"""Engineering fixtures; no paper simulation, GPU call or benchmark outcomes."""
import json
from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from final.core_model import CoreModel, ModelResponse
from final.pipeline import Pipeline, Settings, digest, save
from final.experiments.concept_reference_v1.analysis import analyze_task
from final.experiments.concept_reference_v1.benchmark import generate_inputs, score_task, report
from final.experiments.concept_reference_v1.cohort import build_task, load_cohort, build_cohort
from final.experiments.concept_reference_v1.execution import execute
from final.experiments.concept_reference_v1.model import QwenModel
from final.experiments.concept_reference_v1.prompts import compact_source
from final.run import DATA_SHA256


TASK=dict(task_id='HumanEval/0',prompt='def f(x):\n    """Return absolute value."""\n',
          canonical_solution='    return abs(x)\n',entry_point='f',
          test='def check(candidate): assert candidate(2)==2')
META=dict(contract='\n    assert type(x)==int\n',atol=0)


class FixtureModel(CoreModel):
    context=8192

    def __init__(self):
        self.writer_calls=0
        self.tester_calls=0

    @property
    def model_id(self):
        return 'fixture'

    def tokens(self,messages):
        return max(1,len(json.dumps(messages))//4)

    def generate(self,messages,**kwargs):
        text=messages[-1]['content']
        if '"programs"' in text:
            start=self.writer_calls*5
            self.writer_calls+=1
            rows=[dict(code=f'def f(x):\n    return x if x > -{i} else -x',approach=f'fixture{i}')
                  for i in range(start,start+5)]
            return ModelResponse(json.dumps(dict(programs=rows)))
        self.tester_calls+=1
        assert 'return abs(x)' not in text
        if 'No additional analysis packet' in text:
            args='(3,)'
        elif 'base inputs exercise classes' in text and 'never exercise' not in text:
            args='(4,)'
        else:
            args='(-1,)'
        return ModelResponse(json.dumps(dict(inputs=[dict(args=args,kwargs='{}',concept_id=None)])))


def test_library_evidence_includes_all_four_classical_kinds():
    code='def f(x):\n    y=0\n    if x>0:\n        y=x\n    return y'
    base=execute(dict(mode='base',source=code,context=TASK['prompt'],entry='f',base=TASK['test'],trace=True,timeout=3))
    packet=analyze_task(dict(task_id=TASK['task_id'],programs=[dict(id=0,code=code,base=base)]))
    assert {c['kind'] for c in packet['classical']}=={'BOUNDARY','EQUIVALENCE','CFG','DEF_USE'}
    assert packet['analyses'][0]['graph_error'] is None
    assert any(p['define']==2 and p['use']==5 for p in packet['analyses'][0]['def_use'])
    assert 'pair coverage is unknown' in next(c for c in packet['classical'] if c['kind']=='DEF_USE')['text']


def test_def_use_excludes_write_to_write_but_includes_augmented_reads():
    code='def f(x):\n    y=1\n    y=2\n    y+=x\n    return y'
    base=execute(dict(mode='base',source=code,context=TASK['prompt'],entry='f',
                      base='def check(candidate): assert candidate(2)==4',trace=True,timeout=3))
    analysis=analyze_task(dict(task_id=TASK['task_id'],programs=[dict(id=0,code=code,base=base)]))
    pairs=analysis['analyses'][0]['def_use']
    assert not any(p['use']==3 and p['name']=='y' for p in pairs)
    assert any(p['define']==3 and p['use']==4 and p['name']=='y' for p in pairs)


def test_prompt_listing_preserves_original_source_line_numbers():
    code='def f(x):\n    """Long doc.\n    Another line.\n    """\n    # comment\n    if x>0:\n        return x\n    return -x'
    listing=compact_source(code)
    assert '6:     if x>0:' in listing
    assert '8:     return -x' in listing
    assert 'Long doc' not in listing
    assert '# comment' not in listing


def test_cross_put_contrast_is_static_not_a_bug_claim():
    programs=[]
    for i,op in enumerate(('>','>=')):
        code=f'def f(x):\n    return x if x {op} 0 else -x'
        base=execute(dict(mode='base',source=code,context=TASK['prompt'],entry='f',base=TASK['test'],trace=True,timeout=3))
        programs.append(dict(id=i,code=code,base=base))
    analysis=analyze_task(dict(task_id=TASK['task_id'],programs=programs))
    assert analysis['contrastive_available']
    assert analysis['contrastive'][0]['kind']=='CONTRASTIVE'
    assert 'not evidence' in analysis['contrastive'][0]['text']


def test_domain_contract_filters_inputs_before_reference():
    result=execute(dict(mode='oracle',context=TASK['prompt'],source=TASK['prompt']+TASK['canonical_solution'],
                        contract=META['contract'],entry='f',tests=[dict(args='(1.5,)',kwargs='{}'),
                         dict(args='(-1,)',kwargs='{}')],timeout=3))
    assert result['tests'][0]['status']=='invalid_domain'
    assert result['tests'][1]['expected']=='1'


def test_reference_float_and_polynomial_comparisons():
    result=execute(dict(mode='evaluate',context=TASK['prompt'],source='def f(x):return 1.00000001',entry='f',
                        tests=[dict(args='(1,)',kwargs='{}',expected='1.0')],atol=0,timeout=3))
    assert result['tests'][0]['status']=='pass'
    for root in (-1,1):
        result=execute(dict(mode='evaluate',context='def find_zero(xs):\n    """root"""\n',
            source=f'def find_zero(xs):return {root}',entry='find_zero',atol=1e-4,timeout=3,
            tests=[dict(args='([-1,0,1],)',kwargs='{}',expected='1.0')]))
        assert result['tests'][0]['status']=='pass'
        result=execute(dict(mode='evaluate',context='def find_zero(xs):\n    """root"""\n',
            source=f'def find_zero(xs):return {root}',entry='find_zero',atol=1e-4,timeout=3,
            tests=[dict(args='()',kwargs="{'xs':[-1,0,1]}",expected='1.0')]))
        assert result['tests'][0]['status']=='pass'


def test_transport_allows_tiny_probe_without_256_token_minimum(monkeypatch):
    monkeypatch.setenv('FINAL_BASE_URL','http://unused.invalid/v1')
    monkeypatch.setenv('FINAL_MODEL','fixture')
    model=QwenModel()
    monkeypatch.setattr(model,'tokens',lambda messages:27)
    monkeypatch.setattr(model,'post',lambda path,body:{'choices':[dict(message=dict(content='ok'),finish_reason='stop')]})
    response=model.generate([],temperature=0,max_tokens=32,seed=1)
    assert response.text=='ok'
    assert response.usage['requested_output_budget']==32


def test_fixed_cohort_then_concept_generation_reference_scoring_and_reuse(tmp_path,monkeypatch):
    model=FixtureModel()
    client=Pipeline(model,tmp_path/'cohort',Settings())
    cohort_task=build_task(TASK,client,tmp_path/'cohort/tasks/0')
    assert cohort_task['generated']==cohort_task['base_pass']==10
    assert model.writer_calls==2
    cohort=dict(tasks=[cohort_task],cohort_sha256=digest([cohort_task]),dataset_sha256=DATA_SHA256)
    save(tmp_path/'cohort/cohort.json',cohort)

    class ForbiddenWriter:
        @property
        def model_id(self):
            raise AssertionError('Frozen cohort must not touch a model')

    assert build_cohort(ForbiddenWriter(),[TASK],tmp_path/'cohort')==cohort
    out=tmp_path/'experiment'
    generate_inputs(TASK,cohort_task,META,model,out)
    assert model.tester_calls==5
    generate_inputs(TASK,cohort_task,META,model,out)
    assert model.tester_calls==5
    result=score_task(TASK,cohort_task,META,out)
    assert result['arms']['plain']['detected']==0
    assert result['arms']['classical']['detected']==8
    assert score_task(TASK,cohort_task,META,out)==result
    summary=report(out,cohort,1)
    assert summary['arms']['classical']['detected']==8
    assert summary['comparisons'][0]['rows'][0]['inputs_each']==1
    assert summary['comparisons'][0]['left_macro_fraction']==.8
    assert model.writer_calls==2
    # Prove offline score never constructs a model or requires endpoint env.
    from final.experiments.concept_reference_v1 import run as controller
    monkeypatch.setattr(controller,'QwenModel',lambda:FixtureModel())
    monkeypatch.setattr(controller,'load_tasks',lambda:[TASK])
    args=['--out',str(out),'--cohort',str(tmp_path/'cohort'),'--task-ids','0']
    assert controller.main(args+['--phase','cohort'])==0
    data=json.loads((out/'tasks/0/inputs.json').read_text())
    inputs={TASK['task_id']:digest(data)}
    save(out/'generation_frozen.json',dict(cohort_sha256=cohort['cohort_sha256'],inputs=inputs,inputs_sha256=digest(inputs)))
    monkeypatch.delenv('FINAL_BASE_URL',raising=False)
    monkeypatch.delenv('FINAL_MODEL',raising=False)

    def forbidden_model():
        raise AssertionError('Offline scoring must never initialize a model')

    monkeypatch.setattr(controller,'QwenModel',forbidden_model)
    assert controller.main(args+['--phase','score'])==0


def test_frozen_cohort_detects_artifact_tampering(tmp_path):
    path=tmp_path/'cohort.json'
    data=dict(tasks=[],cohort_sha256=digest([]),dataset_sha256=DATA_SHA256)
    save(path,data)
    assert load_cohort(path)==data
    data['tasks']=[{'tampered':True}]
    save(path,data)
    with pytest.raises(ValueError,match='checksum'):
        load_cohort(path)


def test_keepalive_resume_preserves_previous_call_accounting(tmp_path,monkeypatch):
    from final.experiments.concept_reference_v1 import keepalive
    save(tmp_path/'keepalive/0000.json',dict(state='received',usage=dict(total_tokens=5)))
    fake=SimpleNamespace(url='http://unused.invalid/v1',model_id='fixture',post=lambda *a,**k:{'usage':{'total_tokens':2}})
    monkeypatch.setattr(keepalive,'QwenModel',lambda **kwargs:fake)
    monkeypatch.setattr(keepalive.urllib.request,'urlopen',lambda *a,**k:nullcontext(SimpleNamespace(status=200)))
    observer=keepalive.KeepAlive(tmp_path)
    waits=iter([False,True])
    monkeypatch.setattr(observer.stop,'wait',lambda timeout:next(waits))
    observer.run()
    assert json.loads((tmp_path/'keepalive/0000.json').read_text())['usage']['total_tokens']==5
    assert json.loads((tmp_path/'keepalive/0001.json').read_text())['usage']['total_tokens']==2
