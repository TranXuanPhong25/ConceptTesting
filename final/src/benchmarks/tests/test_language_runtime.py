import json
import pytest

from final.src.benchmarks.language_runtime import execute_program


@pytest.mark.parametrize('language', ['cpp', 'java', 'python'])
def test_program_cannot_read_host_file(tmp_path, language):
    from final.src.benchmarks.language_runtime import execute_program
    secret = tmp_path / 'host-only.txt'
    secret.write_text('private fixture')
    sources = {
        'python': f'def f():\n    return open({str(secret)!r}).read()\n',
        'cpp': '#include <fstream>\n#include <string>\nstd::string f(){ std::ifstream in(' + json.dumps(str(secret)) + '); std::string s; std::getline(in,s); return s; }',
        'java': 'class Solution { public String f() throws Exception { return java.nio.file.Files.readString(java.nio.file.Path.of(' + json.dumps(str(secret)) + ')); }}',
    }
    task = {'language': language, 'declaration': {'python':'def f(): pass', 'cpp':'std::string f(){', 'java':'public String f() {'}[language], 'entry_point': 'f'}
    result = execute_program(task, sources[language], [{}], timeout=2)
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


def test_cpp_declaration_with_helper_and_partial_target_body():
    declaration = '''string helper(string s) { for(int i=0;i<3;i++) { } return s; }
string target(string s) {
    for (int i=0;i<3;i++) {
'''
    from final.src.benchmarks.language_runtime import serialize_call
    assert serialize_call(declaration, {'s':'x'}, 'cpp').startswith('target(')


@pytest.mark.parametrize('language,number,calls', [
    ('cpp', 22, [{'values': ['a', 3.14, 5]}]),
    ('cpp', 137, [{'a': 1, 'b': 2.5}, {'a': 1, 'b': '2,3'}]),
    ('java', 95, [{'dict': {'p': 'pineapple', 'b': 'banana'}}]),
    ('java', 151, [{'lst': [1, 3, 2, 0]}]),
])
def test_humaneval_x_dynamic_values_compile_and_run(language, number, calls):
    from final.src.benchmarks.datasets import load_humaneval_x
    from final.src.benchmarks.pipeline import adapter_task

    task = adapter_task(load_humaneval_x(language)[number])
    result = execute_program(task, task['reference_source'], calls, timeout=8)
    assert result['status'] == 'ok', result
    assert all(row['status'] == 'ok' for row in result['tests']), result


def test_result_symlink_is_not_followed_by_parent(tmp_path):
    canary=tmp_path/'secret'
    canary.write_text(json.dumps('host-only fixture'))
    source=f'import os\ndef f():\n    os.symlink({str(canary)!r},"/results/ct-result.json")\n    raise SystemExit(0)\n'
    task={'language':'python','declaration':'def f(): pass','entry_point':'f'}
    result=execute_program(task,source,[{}])
    assert result['tests'][0]['status']=='output_error'
    assert 'host-only fixture' not in json.dumps(result)
