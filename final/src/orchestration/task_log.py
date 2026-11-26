"""Per-task error log built from saved run records, for Prefect table artifacts.

Read-only: it only reads the JSON files a run already wrote. One row per task:
generation problems (rejected records, truncated responses, parser repairs),
inputs the reference rejected (by reason and reference status), and the PUT
failure observations (fail / error with exception name / timeout).
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path


def read_if(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return {}


EVALUATION_LAYOUTS = ('evaluation/tasks', 'tasks')
GENERATION_LAYOUTS = ('generation/tasks', 'format_view/tasks', 'repaired_view/tasks', 'tasks', 'evaluation/tasks')


def task_directories(directory, required_file, layouts):
    """Return {task_number: path} from the first layout that holds required_file."""
    directory = Path(directory)
    for layout in layouts:
        found = {path.parent.name: path.parent for path in (directory / layout).glob('*/' + required_file)}
        if found:
            return found
    return {}


def counter_text(counter):
    return ', '.join(f'{name}×{count}' for name, count in counter.most_common()) or '—'


def generation_text(inputs_record, calls_directory):
    if inputs_record.get('skip'):
        return 'skip: ' + str(inputs_record['skip'])
    parts = []
    for arm, record in inputs_record.get('arms', {}).items():
        details = [f"{len(record.get('inputs', []))} input"]
        reasons = Counter(row.get('reason', 'unknown') for row in record.get('rejected', []))
        repaired = record.get('packaging_repair_count', 0) + record.get('format_repair_slots', 0)
        if repaired:
            # Repaired views keep the original rejection list for source info.
            details.append(f'repaired slots {repaired}')
            if reasons:
                details.append('rejected before repair ' + counter_text(reasons))
        elif reasons:
            details.append('rejected ' + counter_text(reasons))
        if record.get('status'):
            details.append('status ' + record['status'])
        if record.get('response_repairs'):
            details.append('repair ' + '+'.join(record['response_repairs']))
        for call_name in (arm, arm + '_initial', arm + '_feedback'):
            response = read_if(calls_directory / call_name / 'response.json') if calls_directory else {}
            if response.get('finish_reason') == 'length':
                suffix = '' if call_name == arm else f' ({call_name})'
                details.append(f'truncated{suffix} (finish_reason=length)')
        parts.append(arm + ': ' + ', '.join(details))
    return '; '.join(parts)


def reference_text(oracle):
    reasons = Counter()
    for row in oracle.get('rejected', []):
        statuses = sorted({outcome.get('status') for outcome in row.get('outcomes', []) if outcome.get('status')})
        reasons[row.get('reason', 'unknown') + (f"({'/'.join(statuses)})" if statuses else '')] += 1
    return counter_text(reasons)


def put_failure_text(task_directory, result):
    statuses = Counter()
    for put_id, outcome in result.get('outcomes', {}).items():
        failing = outcome.get('failing', [])
        if not failing:
            continue
        first = read_if(task_directory / 'evaluation' / f'{put_id}_0.json').get('tests', [])
        for index in failing:
            if index < len(first):
                item = first[index]
                label = item.get('status', 'unknown')
                if item.get('exception'):
                    label += ':' + item['exception']
                statuses[label] += 1
    return counter_text(statuses)


def task_error_rows(directory):
    """One row per task with any generation, reference or PUT problem."""
    directory = Path(directory)
    results = task_directories(directory, 'result.json', EVALUATION_LAYOUTS)
    generations = task_directories(directory, 'inputs.json', GENERATION_LAYOUTS)
    responses = task_directories(directory, 'calls', GENERATION_LAYOUTS)
    rows = []
    for number in sorted(set(results) | set(generations), key=int):
        result = read_if(results[number] / 'result.json') if number in results else {}
        inputs_record = read_if(generations[number] / 'inputs.json') if number in generations else {}
        calls_directory = responses[number] / 'calls' if number in responses else None
        oracle = read_if(results[number] / 'oracle_valid.json') if number in results else {}
        detected = {arm: metrics.get('detected', 0) for arm, metrics in result.get('arms', {}).items()}
        unstable = sum(len(outcome.get('unstable', [])) for outcome in result.get('outcomes', {}).values())
        row = {
            'task': 'HumanEval/' + number,
            'generation': generation_text(inputs_record, calls_directory) if inputs_record else '—',
            'reference_rejected': reference_text(oracle),
            'put_confirmed_failures': put_failure_text(results[number], result) if result else '—',
            'unstable_observations': unstable,
            'detected_puts': ', '.join(f'{arm} {count}' for arm, count in detected.items()) or '—',
        }
        has_problem = (row['reference_rejected'] != '—' or row['put_confirmed_failures'] not in ('—',)
                       or unstable or 'rejected' in row['generation'] or 'truncated' in row['generation']
                       or 'skip' in row['generation'] or 'repair' in row['generation'])
        if has_problem:
            rows.append(row)
    return rows
