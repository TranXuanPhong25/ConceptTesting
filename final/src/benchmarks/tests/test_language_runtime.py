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


def test_public_solution_compiles_separately_from_java_harness():
    source = 'import java.util.*;\npublic class Solution { public int f(int x) { return x + 1; } }'
    task = {'language': 'java', 'declaration': 'class Solution { public int f(int x) {',
        'example_test': 'public class Main { public static void main(String[] args) { List<Integer> xs = Arrays.asList(1); assert new Solution().f(xs.get(0)) == 2; } }'}
    assert execute_program(task, source, [], base=True)['tests'] == [{'status': 'ok'}]
    assert execute_program(task, source, [{'x': 2}])['tests'] == [{'status': 'ok', 'value': 3}]


@pytest.mark.parametrize('number,calls,expected', [
    (95, [{'dict': {'p': 'pineapple', 'b': 'banana'}}], [True]),
    (137, [{'a': 1, 'b': 2.5}, {'a': 1, 'b': '2,3'}], [2.5, '2,3']),
    (151, [{'lst': [1, 3, 2, 0]}], [10]),
])
def test_humaneval_x_dynamic_values_compile_and_run(number, calls, expected):
    from final.src.benchmarks.datasets import load_humaneval_x
    from final.src.benchmarks.pipeline import adapter_task

    task = adapter_task(load_humaneval_x('java')[number])
    result = execute_program(task, task['reference_source'], calls, timeout=8)
    assert result['status'] == 'ok', result
    assert result['tests'] == [{'status': 'ok', 'value': value} for value in expected], result


def test_result_symlink_is_not_followed_by_parent(tmp_path):
    canary=tmp_path/'secret'
    canary.write_text(json.dumps('host-only fixture'))
    source=f'import os\ndef f():\n    os.symlink({str(canary)!r},"/results/ct-result.json")\n    raise SystemExit(0)\n'
    task={'language':'python','declaration':'def f(): pass','entry_point':'f'}
    result=execute_program(task,source,[{}])
    assert result['tests'][0]['status']=='output_error'
    assert 'host-only fixture' not in json.dumps(result)
