from pathlib import Path
import ast
import json
import pytest
from final.src.modular.pynguin.runner import sandbox
from final.src.modular.pynguin.extraction import extract
from final.src.modular.tests.test_pynguin_adapter import context, PYTHON
from final.src.modular.pynguin import PynguinSettings, PynguinInputGenerator


def test_precall_capture_types_mutation_and_independent_sequence(tmp_path):
    source='def f(x, *, flag=True):\n    if isinstance(x,list): x.append(9)\n    return x\n'
    exported={'test_target.py':'''import target as module_0
def test_0():
    module_0.f((1,), flag=True)
def test_1():
    module_0.f([1], flag=1)
def test_2():
    module_0.f(1)
    module_0.f(2)
'''}
    result=extract(PYTHON,tmp_path,source,'f',exported,64,10)
    assert result['status']=='complete', result
    assert [ast.literal_eval(r['args']) for r in result['calls']]==[((1,),),([1],),(1,),(2,)]
    assert [ast.literal_eval(r['kwargs']) for r in result['calls']]==[{'flag':True},{'flag':1},{},{}]
    assert not result['rejected']


def test_sandbox_hides_canary_and_env(tmp_path, monkeypatch):
    canary=tmp_path.parent/'host_canary'
    canary.write_text('private')
    monkeypatch.setenv('OPENAI_API_KEY','canary-secret')
    (tmp_path/'check.py').write_text(f'''import os
from pathlib import Path
assert not Path({str(canary)!r}).exists()
assert 'OPENAI_API_KEY' not in os.environ
''')
    assert sandbox(PYTHON,tmp_path,'check.py',5)['status']=='complete'


def test_parent_timeout_kills_namespace(tmp_path):
    (tmp_path/'hang.py').write_text('import subprocess, time\nsubprocess.Popen(["/bin/sleep","45"])\ntime.sleep(45)\n')
    result=sandbox(PYTHON,tmp_path,'hang.py',1)
    assert result['status']=='timeout'
    assert result['elapsed_seconds'] < 4


def test_upstream_toy_and_replay(tmp_path):
    settings=PynguinSettings(python=PYTHON,search_seconds=2,wall_seconds=15,maximum_test_executions=80,owner_limit=1)
    ctx=context(tmp_path,'def f(x: int):\n    if x > 0:\n        return 1\n    return -1\n')
    generator=PynguinInputGenerator(settings)
    batch=generator.run_task(ctx)
    assert batch['status']=='complete',batch
    assert batch['inputs'] and batch['pynguin']['owners'][0]['exports']
    assert batch['pynguin']['owners'][0]['actual_config']['version']=='0.48.0'
    assert generator.run_task(ctx)==batch


def test_compile_crash_is_not_empty(tmp_path):
    result=extract(PYTHON,tmp_path,'def f(:\n','f',{'test_target.py':'import target\n'},4,5)
    assert result['status']=='failed'

def test_mutable_global_and_object_rejected(tmp_path):
    source='state=[]\ndef f(x):\n    state.append(x)\n    return len(state)\n'
    result=extract(PYTHON,tmp_path,source,'f',{'test_target.py':'import target\ndef test_0():\n    target.f(1)\n'},4,5)
    assert result['status']=='unsupported_input'

def test_alias_rejected(tmp_path):
    source='def f(x,y):\n    x.append(1)\n    return y\n'
    exported={'test_target.py':'import target\ndef test_0():\n    x=[]\n    target.f(x,x)\n'}
    result=extract(PYTHON,tmp_path,source,'f',exported,4,5)
    assert not result['calls'] and result['rejected'][0]['reason']=='aliased_mutable_input'

def test_empty_exports_and_corrupt_stats(tmp_path):
    from final.src.modular.pynguin.adapter import read_statistics
    assert read_statistics('not a csv')=={'status':'pending','reason':'invalid_statistics'}
    result=extract(PYTHON,tmp_path,'def f(x):\n    return x\n','f',{},4,5)
    assert result['status']=='empty'

def test_recursion_counts_only_external_entry(tmp_path):
    source='def f(x: int):\n    if x <= 0: return 0\n    return f(x-1)+1\n'
    exported={'test_target.py':'import target\ndef test_0():\n    target.f(3)\n'}
    result=extract(PYTHON,tmp_path,source,'f',exported,4,5)
    assert result['status']=='complete' and len(result['calls'])==1
    assert result['calls'][0]['args']=='(3,)'


def test_extraction_binds_singleton_tuple_and_bool_identity(tmp_path):
    from final.src.modular.call_builder import CallBuilder, input_identity
    source='def f(x, *, flag=True):\n    return x\n'
    exported={'test_target.py':'import target\ndef test_0():\n    target.f((1,),flag=True)\ndef test_1():\n    target.f((1,),flag=1)\n'}
    result=extract(PYTHON,tmp_path,source,'f',exported,4,5)
    builder=CallBuilder.for_source(source,'f')
    records=[]
    for call in result['calls']:
        bound=builder.signature.bind(*ast.literal_eval(call['args']),**ast.literal_eval(call['kwargs']))
        records.append(builder.build_values(bound.arguments))
    assert ast.literal_eval(records[0]['args'])==((1,),)
    assert input_identity(builder.signature,records[0])!=input_identity(builder.signature,records[1])

def test_public_prompt_context_precedes_exact_put(tmp_path):
    source='def f(x: List[int]):\n    return total(x)\n'
    prompt='from typing import List\ndef total(x):\n    return sum(x)\ndef f(x: List[int]):\n    pass\n'
    exported={'test_target.py':'import target\ndef test_0():\n    target.f([1,2])\n'}
    result=extract(PYTHON,tmp_path,source,'f',exported,4,5,context_source=prompt)
    assert result['status']=='complete' and result['calls'][0]['args']=='([1, 2],)'


def test_helper_attribute_state_is_not_fresh_input(tmp_path):
    source="def set_mode(x: int):\n    f.mode=x\ndef f(x: int):\n    return getattr(f,'mode',0)+x\n"
    exported={'test_target.py':'import target\ndef test_0():\n    target.set_mode(10)\n    target.f(1)\n'}
    result=extract(PYTHON,tmp_path,source,'f',exported,4,5)
    assert result['status']=='unsupported_input' and not result['calls']


def test_helper_interaction_before_entry_rejected(tmp_path):
    source='def helper(x: int):\n    return x\ndef f(x: int):\n    return x\n'
    exported={'test_target.py':'import target\ndef test_0():\n    x=target.helper(10)\n    target.f(x)\n'}
    result=extract(PYTHON,tmp_path,source,'f',exported,4,5)
    assert not result['calls']
    assert result['rejected'][0]['reason']=='target_helper_interaction'


@pytest.mark.parametrize('relative',['export/test_target.py','actual_config.json','statistics/statistics.csv','stdout.log','stderr.log'])
def test_child_artifact_symlink_rejected_before_parent_read(tmp_path,monkeypatch,relative):
    from final.src.modular.pynguin import adapter
    canary=tmp_path/'host_canary';canary.write_text('host-private-content')
    ctx=context(tmp_path/'artifacts')
    generator=PynguinInputGenerator(PynguinSettings(python=PYTHON))
    def malicious_child(python,workspace,script,wall):
        path=workspace/relative;path.parent.mkdir(parents=True,exist_ok=True)
        path.symlink_to(canary)
        for log in ('stdout.log','stderr.log'):
            if not (workspace/log).exists(): (workspace/log).write_text('')
        return {'status':'complete','elapsed_seconds':0,'command':[]}
    monkeypatch.setattr(adapter.runner,'sandbox',malicious_child)
    result=generator.run_task(ctx)
    assert result['status']=='failed'
    assert result['pynguin']['owners'][0]['reason']=='unsafe_child_artifact'
    assert 'host-private-content' not in json.dumps(result)


def test_extraction_result_symlink_rejected(tmp_path,monkeypatch):
    from final.src.modular.pynguin import runner
    canary=tmp_path.parent/'host_canary_extract';canary.write_text('{"calls":[],"status":"complete"}')
    def malicious_child(python,workspace,script,wall):
        (workspace/'extraction.json').symlink_to(canary)
        return {'status':'complete'}
    monkeypatch.setattr(runner,'sandbox',malicious_child)
    result=extract(PYTHON,tmp_path,'def f(x):\n    return x\n','f',{},4,5)
    assert result['status']=='failed'

@pytest.mark.parametrize('directory',['export','statistics'])
def test_child_directory_symlink_is_not_enumerated(tmp_path,monkeypatch,directory):
    from final.src.modular.pynguin import adapter
    outside=tmp_path/'host_directory';outside.mkdir()
    (outside/'test_leak.py').write_text('host-private-content')
    (outside/'statistics.csv').write_text('host-private-content')
    ctx=context(tmp_path/'artifacts')
    generator=PynguinInputGenerator(PynguinSettings(python=PYTHON))
    def malicious_child(python,workspace,script,wall):
        (workspace/directory).symlink_to(outside,target_is_directory=True)
        for name in ('stdout.log','stderr.log'): (workspace/name).write_text('')
        return {'status':'complete','elapsed_seconds':0,'command':[]}
    monkeypatch.setattr(adapter.runner,'sandbox',malicious_child)
    batch=generator.run_task(ctx)
    assert batch['status']=='failed'
    assert batch['pynguin']['owners'][0]['reason']=='unsafe_child_artifact'
    assert 'host-private-content' not in json.dumps(batch)


def test_independent_calls_are_extracted_with_distinct_mutable_locals(tmp_path):
    source='def f(x):\n    if isinstance(x,list): x.append(1)\n    return x\n'
    exported={'test_target.py':'''import target
def test_0():
    target.f(1)
    x = [2]
    target.f(x)
'''}
    result=extract(PYTHON,tmp_path,source,'f',exported,64,10)
    assert result['status']=='complete', result
    assert [ast.literal_eval(row['args']) for row in result['calls']]==[(1,),([2],)]


def test_dependent_calls_and_mutated_local_reuse_stay_rejected(tmp_path):
    source='def f(x):\n    if isinstance(x,list): x.append(1)\n    return x\n'
    exported={'test_target.py':'''import target
def test_0():
    x = target.f([1])
    target.f(x)
def test_1():
    x = []
    target.f(x)
    target.f(x)
'''}
    result=extract(PYTHON,tmp_path,source,'f',exported,64,10)
    assert not result['calls']
    assert all(row['reason']=='stateful_test_sequence' for row in result['rejected'])


def test_public_immutable_constant_does_not_imply_state(tmp_path):
    result=extract(PYTHON,tmp_path,'def f(x):\n    return x\n','f',
        {'test_target.py':'import target\ndef test_0():\n    target.f(1)\n'},4,5,
        context_source='FIX = "Add more test cases."\n')
    assert result['status']=='complete' and len(result['calls'])==1
