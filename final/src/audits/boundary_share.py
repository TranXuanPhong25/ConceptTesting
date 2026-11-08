"""Share of boundary inputs among bug-revealing inputs, per arm (saved artifacts only).

No model call and no PUT execution. An input counts as a boundary input when:

- natural_edge: some value is an empty container/string, a one-element container,
  a one-character string, or the number 0, 1 or -1; or
- reference_threshold: running the reference solution on it, some numeric
  comparison (<, <=, >, >=, ==, !=) is evaluated with both sides equal, or with
  both sides integers that differ by exactly 1 (at or adjacent to the threshold).

The reference is instrumented with an AST rewrite of single comparisons and run
in a subprocess with a timeout. This is a heuristic approximation of "boundary";
it does not say that the boundary caused the failure.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
REFERENCES = ROOT / 'final/data/humanevalplus_v0.1.10_references.json'
ORDER_OPERATORS = {ast.Lt: '<', ast.LtE: '<=', ast.Gt: '>', ast.GtE: '>=', ast.Eq: '==', ast.NotEq: '!='}

TRACER = r'''
import ast, json, sys
NEAR = []
def __boundary_compare(left, operator, right):
    numeric = lambda value: isinstance(value, (int, float)) and not isinstance(value, bool)
    if numeric(left) and numeric(right):
        if left == right or (isinstance(left, int) and isinstance(right, int) and abs(left - right) == 1):
            NEAR.append(1)
    return {'<': left < right, '<=': left <= right, '>': left > right, '>=': left >= right,
            '==': left == right, '!=': left != right}[operator]
payload = json.loads(sys.stdin.read())
namespace = {'__boundary_compare': __boundary_compare}
exec(compile(payload['source'], 'reference', 'exec'), namespace)
function = namespace[payload['entry']]
results = []
for test in payload['tests']:
    NEAR.clear()
    try:
        function(*ast.literal_eval(test['args']), **ast.literal_eval(test['kwargs']))
    except BaseException:
        pass
    results.append(bool(NEAR))
print(json.dumps(results))
'''


class InstrumentComparisons(ast.NodeTransformer):
    def visit_Compare(self, node):
        self.generic_visit(node)
        if len(node.ops) == 1 and type(node.ops[0]) in ORDER_OPERATORS:
            return ast.copy_location(ast.Call(func=ast.Name('__boundary_compare', ast.Load()), args=[
                node.left, ast.Constant(ORDER_OPERATORS[type(node.ops[0])]), node.comparators[0]], keywords=[]), node)
        return node


def instrumented_reference(reference):
    tree = ast.parse(reference['prompt'] + reference['canonical_solution'])
    return ast.unparse(ast.fix_missing_locations(InstrumentComparisons().visit(tree)))


def reference_threshold_hits(reference, tests, timeout=120):
    payload = {'source': instrumented_reference(reference), 'entry': reference['entry_point'], 'tests': tests}
    try:
        completed = subprocess.run([sys.executable, '-I', '-c', TRACER], input=json.dumps(payload),
                                   capture_output=True, text=True, timeout=timeout)
        return json.loads(completed.stdout)
    except (subprocess.TimeoutExpired, ValueError):
        return [None] * len(tests)


def walk(value):
    yield value
    if isinstance(value, (list, tuple, set)):
        for item in value:
            yield from walk(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from walk(key)
            yield from walk(item)


def natural_edge(test):
    arguments = list(ast.literal_eval(test['args'])) + list(ast.literal_eval(test['kwargs']).values())
    for argument in arguments:
        for value in walk(argument):
            if isinstance(value, bool):
                continue
            if isinstance(value, (str, list, tuple, dict, set)) and len(value) <= 1:
                return True
            if isinstance(value, (int, float)) and value in (0, 1, -1):
                return True
    return False


def analyse(evaluation, arms):
    references = json.loads(REFERENCES.read_text())['tasks']
    rows = []
    for result_path in sorted(Path(evaluation).glob('tasks/*/result.json'), key=lambda path: int(path.parent.name)):
        result = json.loads(result_path.read_text())
        if result.get('skip') or not all(arm in result.get('arms', {}) for arm in arms):
            continue
        tests = json.loads((result_path.parent / 'oracle_valid.json').read_text())['tests']
        threshold = reference_threshold_hits(references[result['task_id']], tests)
        revealed = {}
        for put_id, outcome in result['outcomes'].items():
            for index in outcome['failing']:
                revealed.setdefault(index, set()).add(put_id)
        for index, test in enumerate(tests):
            owners = [arm for arm in arms if index in result['arm_indices'][arm]]
            rows.append({'task_id': result['task_id'], 'index': index, 'args': test['args'], 'kwargs': test['kwargs'],
                         'arms': owners, 'revealed_puts': sorted(revealed.get(index, ())),
                         'natural_edge': natural_edge(test), 'reference_threshold': threshold[index]})
    return rows


def share(rows):
    total = len(rows)
    natural = sum(row['natural_edge'] for row in rows)
    threshold = sum(bool(row['reference_threshold']) for row in rows)
    either = sum(row['natural_edge'] or bool(row['reference_threshold']) for row in rows)
    unknown = sum(row['reference_threshold'] is None for row in rows)
    def percent(count):
        return round(100 * count / total, 1) if total else None
    return {'inputs': total, 'natural_edge': natural, 'reference_threshold': threshold, 'boundary_either': either,
            'natural_edge_pct': percent(natural), 'reference_threshold_pct': percent(threshold),
            'boundary_either_pct': percent(either), 'threshold_unknown': unknown}


def summarise(rows, arms):
    left, right = arms
    groups = {
        'failing_shared': [row for row in rows if row['revealed_puts'] and set(row['arms']) == {left, right}],
        f'failing_{left}_only': [row for row in rows if row['revealed_puts'] and row['arms'] == [left]],
        f'failing_{right}_only': [row for row in rows if row['revealed_puts'] and row['arms'] == [right]],
        f'failing_{left}_all': [row for row in rows if row['revealed_puts'] and left in row['arms']],
        f'failing_{right}_all': [row for row in rows if row['revealed_puts'] and right in row['arms']],
        f'all_valid_{left}': [row for row in rows if left in row['arms']],
        f'all_valid_{right}': [row for row in rows if right in row['arms']],
    }
    summary = {name: share(group) for name, group in groups.items()}
    for arm in arms:
        detected, by_boundary = set(), set()
        for row in rows:
            if arm in row['arms']:
                for put_id in row['revealed_puts']:
                    detected.add((row['task_id'], put_id))
                    if row['natural_edge'] or row['reference_threshold']:
                        by_boundary.add((row['task_id'], put_id))
        summary[f'puts_{arm}'] = {'detected': len(detected), 'revealed_by_some_boundary_input': len(by_boundary),
                                  'only_non_boundary_inputs': len(detected - by_boundary)}
    summary['failing_tasks'] = dict(Counter(row['task_id'] for row in rows if row['revealed_puts']))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--evaluation', type=Path, required=True)
    parser.add_argument('--arms', nargs=2, default=['direct', 'soft_bva'])
    parser.add_argument('--output', type=Path, required=True)
    options = parser.parse_args()
    rows = analyse(options.evaluation, options.arms)
    report = {'definition': __doc__, 'evaluation': str(options.evaluation), 'arms': options.arms,
              'summary': summarise(rows, options.arms), 'rows': [row for row in rows if row['revealed_puts']],
              'new_model_calls': 0}
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({key: value for key, value in report['summary'].items() if key != 'failing_tasks'}, indent=2))


if __name__ == '__main__':
    main()
