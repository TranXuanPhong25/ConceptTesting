"""Authored fixtures verify measured DU events without any model or benchmark run."""
import pytest

from final.src.runtime.execution import execute


def trace(source, args='(True,)', base=None, contract=''):
    import ast
    fn = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'f')
    spec = 'def f(' + ast.unparse(fn.args) + '):\n    pass\n'
    job = dict(mode='data_flow', source=source, entry='f', context=spec,
               contract=contract, timeout=1, tests=[dict(args=args, kwargs='{}')])
    if base is not None:
        job['base'] = base
    return execute(job)['baseline'] if base is not None else execute(job)['tests'][0]


def edges(source, observation):
    from final.src.runtime.data_flow import analyze
    analysis = analyze(source, 'f')
    return {(p['variable'], p['definition'], p['use'], p.get('outcome')) for p in analysis['pairs']
            if p['id'] in observation['data_flow']['pairs']}


def test_redefinition_kills_old_definition_and_same_line_order():
    source = 'def f(flag):\n    x = 1; x = x + 1; x = 3\n    return x\n'
    seen = trace(source)
    from final.src.runtime.data_flow import analyze
    definitions = analyze(source, 'f')['definitions']
    xdefs = [d for d in definitions if d['variable'] == 'x']
    pairs = [p for p in analyze(source, 'f')['pairs'] if p['id'] in seen['data_flow']['pairs']]
    assert any(p['definition_id'] == xdefs[0]['id'] and p['use'] == 2 for p in pairs)
    assert {p['definition_id'] for p in pairs if p['use'] == 3} == {xdefs[2]['id']}
    assert seen['status'] == 'executed'
    assert 'actual' not in str(seen) and 'expected' not in str(seen)


def test_parameter_and_two_reaching_definitions():
    source = 'def f(flag):\n    if flag:\n        x = 1\n    else:\n        x = 2\n    return x\n'
    yes, no = trace(source), trace(source, '(False,)')
    assert ('flag', 1, 2, 'T') in edges(source, yes)
    assert ('flag', 1, 2, 'F') in edges(source, no)
    assert ('x', 3, 6, None) in edges(source, yes)
    assert ('x', 5, 6, None) not in edges(source, yes)
    assert ('x', 5, 6, None) in edges(source, no)


def test_loop_update_uses_previous_iteration_definition():
    source = 'def f(n):\n    x = 0\n    for i in range(n):\n        x += i\n    return x\n'
    seen = edges(source, trace(source, '(3,)'))
    assert ('x', 2, 4, None) in seen
    assert ('x', 4, 4, None) in seen
    assert ('i', 3, 4, None) in seen
    assert ('x', 4, 5, None) in seen


def test_short_circuit_records_only_evaluated_atoms():
    source = 'def f(x, y):\n    if x and y:\n        return 1\n    return 0\n'
    seen = trace(source, '(False, True)')
    assert ('y', 1, 2, 'T') not in edges(source, seen)
    assert ('y', 1, 2, 'F') not in edges(source, seen)
    assert ('x', 1, 2, 'F') in edges(source, seen)
    assert len(seen['data_flow']['condition_outcomes']) == 2


def test_recursion_and_separate_calls_do_not_mix_frames():
    source = 'def f(n):\n    x = n\n    if n > 0:\n        f(n - 1)\n        x = 9\n    return x\n'
    seen = trace(source, base='def check(candidate):\n    assert candidate(1) == 9\n    assert candidate(0) == 0\n')
    assert seen['status'] == 'executed' and seen['test_count'] == 2
    assert ('x', 2, 6, None) in edges(source, seen)
    assert ('x', 5, 6, None) in edges(source, seen)
    assert seen['baseline_scope'] == 'full_base_suite'
    assert 'actual' not in str(seen)


def test_exception_before_assignment_never_defines_target():
    source = 'def f(x):\n    y = 1\n    try:\n        y = 1 / x\n    except ZeroDivisionError:\n        pass\n    return y\n'
    seen = edges(source, trace(source, '(0,)'))
    assert ('y', 2, 7, None) in seen
    assert ('y', 4, 7, None) not in seen


def test_unsupported_scope_falls_back_to_original_coverage():
    source = 'def f(xs):\n    return [x + 1 for x in xs]\n'
    seen = trace(source, '([1, 2],)')
    assert seen['status'] == 'executed' and 2 in seen['coverage']['lines']
    assert seen['data_flow']['status'] == 'unsupported'
    assert seen['data_flow']['unsupported'] and not seen['data_flow']['pairs']


def test_domain_rejection_has_no_measurement():
    source = 'def f(x):\n    return x\n'
    seen = trace(source, '(0,)', contract='    assert x > 0\n')
    assert seen['domain'] == 'invalid' and 'coverage' not in seen


def test_static_pairs_are_candidates_with_unknown_feasibility():
    from final.src.runtime.data_flow import analyze
    result = analyze('def f(x):\n    y = x\n    return y\n', 'f')
    assert result['pairs'] and result['pair_feasibility'] == 'unknown'
    assert all('column' in row and 'scope' in row for row in result['definitions'] + result['uses'])


@pytest.mark.parametrize('expression', ['x and y', 'x or y', 'not (x and y)', 'x < y < z'])
def test_custom_truthiness_is_evaluated_once_and_output_matches_original(expression):
    source = 'def f(x, y, z=None):\n    if ' + expression + ':\n        return 1\n    return 0\n'
    # Source is a fixture, compiled only by the sandbox's existing base-suite runner.
    base = '''class Probe:
    def __init__(self, value): self.value, self.calls = value, 0
    def __bool__(self): self.calls += 1; return self.value
    def __lt__(self, other): return self

def check(candidate):
    x, y, z = Probe(False), Probe(True), Probe(True)
    value = candidate(x, y, z)
    counts = (x.calls, y.calls, z.calls)
    x, y, z = Probe(False), Probe(True), Probe(True)
    expected = 1 if EXPRESSION else 0
    assert value == expected
    assert counts == (x.calls, y.calls, z.calls)
'''.replace('EXPRESSION', expression)
    assert trace(source, base=base)['status'] == 'executed'


@pytest.mark.parametrize('source,args', [
    ('def f(x):\n    """A fixture."""\n    if x:\n        return 1\n    return 0\n', '(True,)'),
    ('def f(n):\n    x = 0\n    for i in range(n):\n        x += i\n    return x\n', '(3,)'),
    ('def f(n):\n    while n > 0:\n        n -= 1\n    return n\n', '(2,)'),
])
def test_instrumentation_retains_original_coverage(source, args):
    measured = trace(source, args)
    original = execute(dict(mode='control_flow', source=source, entry='f',
        context=source[:source.index(':') + 1] + '\n    pass\n', contract='', timeout=1,
        tests=[dict(args=args, kwargs='{}')]))['tests'][0]
    assert measured['coverage'] == original['coverage']


def test_nested_not_and_chained_comparison_state_atom_scope_limit():
    from final.src.runtime.data_flow import analyze
    result = analyze('def f(x,y,z):\n    if not (x and y) or x < y < z:\n        return 1\n', 'f')
    assert result['status'] == 'unsupported'
    assert 'chained_comparison_truthiness' in result['unsupported']
