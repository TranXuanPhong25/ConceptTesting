"""Read saved preparation responses without repairing them or running any workload."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from pydantic import ValidationError

from ..call_builder import CallBuilder
from final.src.benchmarks.datasets import load_tasks
from ..response_json import load_response_json
from .schema import preparation_type, parse_preparation, validate_expression


def inspect_response(raw, builder):
    problems = []
    try:
        preparation_type(builder).model_validate(raw)
    except ValidationError as exc:
        problems.extend({'stage': 'schema', 'location': list(item['loc']), 'code': item['type'],
                         'detail': item['msg']} for item in exc.errors(include_input=False, include_url=False))
    if not isinstance(raw, dict):
        return {'valid': False, 'issues': problems, 'requires_new_preparation': True}
    types = raw.get('types') if isinstance(raw.get('types'), dict) else dict.fromkeys(builder.signature.parameters)
    expressions = [('domain', raw.get('domain'))]
    targets = raw.get('targets')
    if isinstance(targets, list):
        for index, target in enumerate(targets):
            if isinstance(target, dict):
                expressions.extend((f'targets.{index}.{field}', target.get(field, 'True' if field == 'context' else None))
                                   for field in ('context', 'predicate'))
    factors = raw.get('factors')
    if isinstance(factors, dict):
        for name, levels in factors.items():
            if isinstance(levels, dict):
                expressions.extend((f'factors.{name}.{level}', predicate) for level, predicate in levels.items())
    for location, text in expressions:
        try:
            validate_expression(text, types)
        except ValueError as exc:
            problems.append({'stage': 'expression', 'location': location.split('.'),
                             'code': 'unsupported_or_non_boolean_expression', 'detail': str(exc)})
    unsupported=[]
    parsed=False
    try:
        prepared=parse_preparation(raw, builder)
        unsupported=[target['id'] for target in prepared['targets'] if target.get('support')=='unsupported']
        parsed=True
    except ValueError as exc:
        if not problems:
            problems.append({'stage': 'native_contract', 'location': [], 'code': 'invalid_preparation', 'detail': str(exc)})
    if parsed:
        for issue in problems:
            if issue['stage']=='expression' and issue.get('location',[None])[0]=='targets':
                issue['severity']='unsupported_target'
    fatal=any(issue.get('severity')!='unsupported_target' for issue in problems)
    return {'valid': parsed and not fatal, 'issues': problems, 'requires_new_preparation': not parsed or fatal,
            'fully_supported':parsed and not problems, 'unsupported_target_ids':unsupported,
            'strategy_container': type(raw.get('strategies')).__name__,
            'positional_strategy_count_matches_signature': isinstance(raw.get('strategies'), list)
                and len(raw['strategies']) == len(builder.signature.parameters),
            'automatic_repairs': [], 'semantics_repaired': False}


def audit_saved_responses(source):
    tasks = {task['task_id']: task for task in load_tasks()}
    paths = sorted(Path(source).glob('tasks/*/calls/tool_preparation/response.json'))
    rows, before = [], {}
    for path in paths:
        content = path.read_bytes()
        before[str(path)] = hashlib.sha256(content).hexdigest()
        task_id = 'HumanEval/' + path.parents[2].name
        task = tasks[task_id]
        response = json.loads(content)
        try:
            raw, _ = load_response_json(response['text'])
            result = inspect_response(raw, CallBuilder.for_source(task['prompt'], task['entry_point']))
        except (ValueError, KeyError, TypeError) as exc:
            result = {'valid': False, 'requires_new_preparation': True,
                      'issues': [{'stage': 'response', 'code': 'invalid_response', 'detail': str(exc)}]}
        if response.get('finish_reason') != 'stop':
            result['valid'] = False
            result['requires_new_preparation'] = True
            result['fully_supported'] = False
            result['issues'].append({'stage': 'response', 'code': 'truncated_response',
                                     'detail': str(response.get('finish_reason'))})
        rows.append({'task_id': task_id, 'response_sha256': before[str(path)], **result})
    unchanged = all(hashlib.sha256(Path(path).read_bytes()).hexdigest() == checksum for path, checksum in before.items())
    if not unchanged:
        raise RuntimeError('Source response changed during audit')
    codes = Counter(item['code'] for row in rows for item in row['issues'])
    return {'source_directory': str(Path(source).resolve()), 'tasks': len(rows),
            'valid_preparations': sum(row['valid'] for row in rows),
            'fully_supported_preparations':sum(row.get('fully_supported',False) for row in rows), 'rows': rows,
            'issue_counts_multilabel': dict(codes), 'source_response_hashes': before,
            'source_unchanged': unchanged, 'new_model_calls': 0, 'native_executions': 0,
            'note': 'Không tự map list thành parameter map, không đổi prose thành predicates; positional shape alone does not prove semantics.'}


def render(report):
    lines = ['# Audit saved tool preparations', '',
             f"{report['valid_preparations']}/{report['tasks']} preparations dùng được theo interface; "
             f"{report.get('fully_supported_preparations','pending')} preparations được hỗ trợ đầy đủ. "
             'Đây là kiểm tra interface, không đo efficacy tools. Không sửa raw response hay suy ra missing constraints.', '',
             '| Task | Schema errors | Expression errors | Cần preparation mới |', '|---|---:|---:|---|']
    for row in report['rows']:
        counts = Counter(item['stage'] for item in row['issues'])
        lines.append(f"| {row['task_id']} | {counts['schema']} | {counts['expression']} | {row['requires_new_preparation']} |")
    lines += ['', 'Issue counts là multi-label; một response có nhiều lỗi. Không chuẩn hóa prose, '
              'không bỏ domain/target unsupported để làm validation pass. Danh sách và source SHA256 trong JSON cạnh report.', '',
              'Source response hashes trước/sau khớp; 0 new model calls, 0 native executions.']
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(args.source.resolve()):
        parser.error('Audit output must stay outside the frozen source run')
    report = audit_saved_responses(args.source)
    args.output.mkdir(parents=True, exist_ok=True)
    for name, content in [('audit.json', json.dumps(report, ensure_ascii=False, indent=2)+'\n'), ('REPORT.md', render(report))]:
        path = args.output/name
        if path.exists() and path.read_text() != content:
            raise ValueError('Audit output differs; choose a new directory')
        path.write_text(content)
    print(json.dumps({key: report[key] for key in ('tasks', 'valid_preparations', 'source_unchanged', 'new_model_calls', 'native_executions')}))


if __name__ == '__main__':
    main()
