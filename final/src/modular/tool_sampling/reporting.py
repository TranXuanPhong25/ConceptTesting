"""Funnel, verified coverage and Vietnamese reports with explicit denominators."""
from collections import Counter
from dataclasses import asdict
import json
import ast
from itertools import combinations

from ..reporting import Reporter
from .selection import hits


def funnel(batch):
    rows = batch['candidate_ledger']
    parse_rows = [row for row in rows if any(error['stage'].startswith('P') for error in row['errors'])]
    primary = Counter(row['primary_error']['code'] for row in parse_rows)
    multilabel = Counter(code for row in parse_rows for code in {error['code'] for error in row['errors']})
    def reached(stage):
        return sum(not any(error['stage'].startswith('P') and int(error['stage'][1]) <= stage
                           for error in row['errors']) for row in rows)
    from .audit import unique_pool
    unique = unique_pool(batch)
    counts = [('total', len(rows)), ('parsed', reached(3)), ('bound', reached(5)),
              ('domain_valid', sum(row.get('domain') == 'true' for row in rows)),
              ('unique', len(unique)), ('selected', sum(row['selected'] for row in unique))]
    previous = len(rows)
    stages = []
    for name, count in counts:
        stages.append({'stage': name, 'count': count, 'denominator': previous,
                       'fraction': count / previous if previous else None})
        previous = count
    return {'stages': stages, 'total_candidates': len(rows), 'response_record_value_parsed': reached(3),
            'bound': reached(5), 'domain_valid': sum(row.get('domain') == 'true' for row in rows),
            'unique': len(unique), 'selected': sum(row['selected'] for row in unique),
            'parse_errors': {'count': len(parse_rows), 'denominator': len(rows),
                'primary_exclusive': dict(primary), 'multi_label': dict(multilabel),
                'at_least_two_errors': sum(len(row['errors']) >= 2 for row in parse_rows),
                'other': sum(any(error['code'] == 'other' for error in row['errors']) for row in rows)},
            'domain_rejects': sum(any(error['code'] == 'domain_rejects' for error in row['errors']) for row in rows),
            'membership_unknown': sum(any(error['code'] == 'membership_unknown' for error in row['errors']) for row in rows),
            'membership_error': sum(any(error['code'] == 'membership_error' for error in row['errors']) for row in rows),
            'by_tool': {tool: {'candidate_emissions': sum(row['sources'][0]['tool'] == tool for row in rows),
                             'unique_shared_or_exclusive': sum(any(source['tool'] == tool for source in row['sources']) for row in unique),
                             'unique_exclusive': sum({source['tool'] for source in row['sources']} == {tool} for row in unique)}
                        for tool in sorted({source['tool'] for row in rows for source in row['sources']})}}


def coverage(batch):
    from .audit import unique_pool
    pool = unique_pool(batch)
    selected = [row for row in pool if row['selected']]
    pool_hits = set().union(*(hits(row) for row in pool))
    suite_hits = set().union(*(hits(row) for row in selected))
    targets = batch['preparation']['targets']
    checked = {target['id'] for target in targets if target.get('support') != 'unsupported'
               and any(row['membership'][target['id']]['context'] in {'true', 'false'}
                       and row['membership'][target['id']]['target'] in {'true', 'false'} for row in pool)}
    unknown = {target['id'] for target in targets if target['id'] not in checked}
    contributions = {}
    for tool in {source['tool'] for row in pool for source in row['sources']}:
        exclusive = [row for row in pool if {source['tool'] for source in row['sources']} == {tool}]
        others = [row for row in pool if row not in exclusive]
        contributions[tool] = sorted(set().union(*(hits(row) for row in exclusive)) -
                                      set().union(*(hits(row) for row in others)))
    factors = batch['preparation'].get('factors', {})
    from .ledger import predicate_status
    actual_levels, planner_rows = {}, {}
    tuples, selected_tuples = set(), set()
    for row in pool:
        arguments = {name: ast.literal_eval(value) for name, value in row.get('bound_values', {}).items()}
        actual = {name: [level for level, predicate in levels.items()
                         if predicate_status(predicate, arguments)[0] == 'true'] for name, levels in factors.items()}
        actual_levels[row['candidate_id']] = actual
        unambiguous = {name: levels[0] for name, levels in actual.items() if len(levels) == 1}
        for left, right in combinations(sorted(unambiguous), 2):
            item = (left, unambiguous[left], right, unambiguous[right])
            tuples.add(item)
            if row['selected']:
                selected_tuples.add(item)
        for source in row['sources']:
            if 'planner_row_id' not in source:
                continue
            item = planner_rows.setdefault(source['planner_row_id'], {
                'requested': source['planner_levels'], 'actual_witnesses': 0, 'selected_witnesses': 0})
            matches = all(actual.get(name) == [level] for name, level in source['planner_levels'].items())
            item['actual_witnesses'] += matches
            item['selected_witnesses'] += matches and row['selected']
    total_pairs = sum(len(factors[left]) * len(factors[right]) for left, right in combinations(factors, 2))
    return {'pool_covered': len(pool_hits), 'suite_covered': len(suite_hits),
            'checked_targets': len(checked), 'total_targets': len(targets), 'unknown_targets': sorted(unknown),
            'unsupported_targets': [target['id'] for target in targets if target.get('support') == 'unsupported'],
            'uncovered_targets': sorted({target['id'] for target in targets} - suite_hits),
            'exclusive_targets_by_tool': contributions, 'origin_by_target': {target['id']: target['origin'] for target in targets},
            'actual_factor_levels': actual_levels, 'planner_rows': planner_rows,
            'combinations': {'covered_pairwise': len(tuples), 'suite_pairwise': len(selected_tuples),
                             'cartesian_pairwise': total_pairs, 'feasible_pairwise': None,
                             'feasibility': 'pending; infeasible combinations not credited',
                             'realized_tuples': [list(item) for item in sorted(tuples)]}}


class ToolReporter(Reporter):
    def build_summary(self, contexts, cohort):
        summary = super().build_summary(contexts, cohort)
        summary['settings'] = asdict(contexts[0].settings)
        summary['tool_sampling'] = {context.task['task_id']: context.extensions.get('tool_sampling', {}) for context in contexts}
        summary['tool_treatments'] = {context.task['task_id']: context.extensions.get('tool_generation_gate', {})
                                      for context in contexts}
        summary['domain_authorities'] = {context.task['task_id']: {
            name: batch.get('domain_authority', {'status':'not_provided'})
            for name, batch in context.inputs.get('arms', {}).items()} for context in contexts}
        summary['preparation_cost'] = 'Shared: tool_preparation, one call/task; see tester_calls. Supplied preparations use zero new calls.'
        from final.src.audits.detection_kinds import classify_arm, kind_counts
        summary['detection_kinds'] = {name: kind_counts(classify_arm(contexts[0].artifacts.directory, name))
                                      for name in summary['arms']}
        return summary

    def render(self, summary):
        lines = ['# Kết quả tool sampling EP/BVA/DT', '',
                 f"Evaluation {summary['scored_tasks']}/{summary['expected_tasks']} task records; "
                 f"{summary['evaluated_base_pass']} eligible PUTs. Coverage không chứng minh detection; "
                 'semantic audit pending. Pool bị cap chỉ cho lower bound, không kết luận generation gap. '
                 'Status exercised ghi nhận sampler hoặc planner đã được dùng để sinh input.', '',
                 '| Arm | Novel valid inputs | Detected PUTs / eligible PUTs | Wrong-value PUTs | Exception PUTs | Resource PUTs |', '|---|---:|---:|---:|---:|---:|']
        for name, values in summary['arms'].items():
            kinds = summary['detection_kinds'][name]
            lines.append(f"| {name} | {values['valid_inputs']} | {values['detected']}/{summary['evaluated_base_pass']} | {kinds['wrong_value']} | {kinds['crash']} | {kinds['resource']} |")
        lines += ['', 'Chỉ reference sau global freeze cung cấp expected output. Không dùng diagnostic để sửa suite. '
                  'Primary parse errors loại trừ lẫn nhau; multi-label có thể đếm một candidate nhiều lần. '
                  'by_tool: shared inputs không được tính là exclusive của từng tool. '
                  'Random control dùng cùng clean pool; số PUT và số inputs là hai đơn vị riêng.', '',
                  'Config/budget thực tế và chi phí shared preparation:', '```json',
                  json.dumps({'settings': summary['settings'], 'tester_calls': summary['tester_calls'],
                              'writer_calls': summary['writer_calls'], 'preparation_cost': summary['preparation_cost'],
                              'skips': summary['skips']}, ensure_ascii=False, indent=2), '```', '',
                  'Funnel theo thứ tự total → parsed → bound → domain_valid → unique → selected; '
                  'mỗi bước dùng bước trước làm mẫu số. Coverage dùng checked_targets và total_targets; '
                  'Detection dùng eligible_puts. Thời gian tool tính bằng giây.', '',
                  'Diagnostic theo task/arm (ledger trước freeze nằm trong inputs.json; kết quả pool tách riêng):',
                  '```json', json.dumps({'treatment_status': summary['tool_treatments'],
                                        'domain_authorities': summary['domain_authorities'],
                                        'diagnostics': summary['tool_sampling']}, ensure_ascii=False, indent=2), '```', '']
        return '\n'.join(lines)
