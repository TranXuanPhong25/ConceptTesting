import json

from final.src.benchmarks.language_runtime import execute_program


def test_sandbox_cannot_read_host_files(tmp_path):
    secret = tmp_path / 'secret'
    secret.write_text('private fixture')
    source = f'def f(): return open({str(secret)!r}).read()'
    task = {'language':'python', 'declaration':'def f(): pass', 'entry_point':'f'}
    result = execute_program(task, source, [{}], timeout=2)
    assert result['tests'][0].get('value') != 'private fixture'
    assert secret.read_text() == 'private fixture'


def test_python_dictionary_order_does_not_change_result():
    task = {'language':'python','entry_point':'f','declaration':'def f(): pass'}
    left = execute_program(task, 'def f(): return {"a":1,"b":2}', [{}])
    right = execute_program(task, 'def f(): return {"b":2,"a":1}', [{}])
    assert left['tests'][0]['value'] == right['tests'][0]['value']


def test_python_invocations_cannot_mutate_the_next_input():
    task = {'language':'python','entry_point':'f','declaration':'def f(): pass'}
    source = 'from pathlib import Path\ndef f():\n    p=Path("/work/marker")\n    seen=p.exists()\n    try:\n        p.write_text("x")\n    except OSError:\n        pass\n    return seen\n'
    result = execute_program(task, source, [{},{}])
    assert result['tests'] == [{'status':'ok','value':False}, {'status':'ok','value':False}]


def test_result_symlink_is_not_followed_by_parent(tmp_path):
    canary=tmp_path/'secret'
    canary.write_text(json.dumps('host-only fixture'))
    source=f'import os\ndef f():\n    os.symlink({str(canary)!r},"/results/ct-result.json")\n    raise SystemExit(0)\n'
    task={'language':'python','declaration':'def f(): pass','entry_point':'f'}
    result=execute_program(task,source,[{}])
    assert result['tests'][0]['status']=='output_error'
    assert 'host-only fixture' not in json.dumps(result)
