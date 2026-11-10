"""Vietnamese reports for catalogue comparisons; reuse existing seeded comparison."""
from dataclasses import asdict
from itertools import combinations
import json
from pathlib import Path

from .stages.reporting import ReportingStage


class CatalogueReportingStage(ReportingStage):
    def source_dependencies(self):
        # Existing read-only classifiers import helpers from the audit package.
        return tuple((Path(__file__).parents[1] / 'audits').glob('*.py'))

    def build_summary(self, contexts, cohort):
        summary = super().build_summary(contexts, cohort)
        summary['settings'] = asdict(contexts[0].settings)
        summary['tester_calls_by_arm'] = usage_by_arm(contexts[0].artifacts.directory,
                                                     list(summary['arms']))
        summary['catalogues'] = {context.task['task_id']: context.extensions.get('catalogue_measurements', {})
                                for context in contexts}
        summary['generation_statuses'] = {}
        for context in contexts:
            for name, batch in context.inputs.get('arms', {}).items():
                counts = summary['generation_statuses'].setdefault(name, {})
                self.increment(counts, batch.get('status', 'generated'))
        names = list(summary['arms'])
        task_results = [context.result for context in contexts]
        summary['comparisons'] = []
        for left_arm, right_arm in combinations(names, 2):
            summary['comparisons'].append(self.compare(task_results, left_arm, right_arm))
        # Saved evaluation observations only: no native/model execution.
        from final.src.audits.detection_kinds import classify_arm, kind_counts
        summary['detection_kinds'] = {}
        for arm_name in names:
            detections = classify_arm(contexts[0].artifacts.directory, arm_name)
            summary['detection_kinds'][arm_name] = kind_counts(detections)
        return summary

    def render(self, summary):
        settings = summary['settings']
        lines = ['# Kết quả testing arms', '',
            f"Đã evaluation {summary['scored_tasks']}/{summary['expected_tasks']} task records; "
            f"{summary['evaluated_base_pass']} eligible base-pass PUTs. "
            'Detection dưới đây áp dụng cho frozen cohort và reference hiện có; catalogue coverage không chứng minh detection. '
            'Semantic audit và phần không kiểm được vẫn là `pending`.', '',
            f"Budget: {settings['input_budget']} inputs/task/arm, một generation call/task/arm; "
            f"completion cap {settings['input_tokens']} tokens/call, context cap {settings['context_tokens']} tokens; "
            f"timeout {settings['timeout_seconds']} giây/input. Robust không đủ eligibility được skip trước model call.", '',
            '| Arm | Novel valid inputs | Confirmed detected PUTs / eligible PUTs | Task có detection / eligible task | Wrong-value PUTs | Exception PUTs | Resource PUTs |',
            '|---|---:|---:|---:|---:|---:|---:|']
        eligible_tasks = summary['expected_tasks'] - len(summary['skips'])
        for name, values in summary['arms'].items():
            kinds = summary['detection_kinds'][name]
            lines.append(f"| {name} | {values['valid_inputs']} | {values['detected']}/{summary['evaluated_base_pass']} | "
                f"{values['tasks_detected']}/{eligible_tasks} | {kinds['wrong_value']} | {kinds['crash']} | {kinds['resource']} |")
        lines += ['', 'Mỗi PUT lấy kind mạnh nhất trong các confirming inputs: wrong-value → exception → timeout/resource. '
                  'Một input phủ nhiều obligation vẫn chỉ là một input. Raw detection dùng toàn bộ novel valid inputs.', '',
                  'Matched-valid-input-budget: lấy subset ngẫu nhiên có seed riêng từng task/pair; '
                  'không lấy prefix. Giữ cả task có matched budget bằng 0.']
        for comparison in summary['comparisons']:
            lines.append(f"- {comparison['left']} vs {comparison['right']}: macro detected PUT fraction "
                         f"{comparison['left_macro_fraction']} vs {comparison['right_macro_fraction']} trên "
                         f"{comparison['task_count']} task; {comparison['zero_valid_budget_tasks']} task có 0 matched inputs; "
                         f"paired permutation p={comparison['paired_permutation_pvalue']:.5g}.")
        lines += ['', 'Catalogue accounting theo task nằm trong `catalogue_measurements.json` và summary. '
                  'Declared coverage dùng covers của inputs đã qua domain/reference, là self-report; '
                  'mechanical BVA chỉ kiểm phần selector/context/nominal đọc được. DT denominator là feasible rules gốc; '
                  'merged ID không tự phủ mọi combination. Thiếu metadata để kiểm thì pending. '
                  'Coverage hiện chỉ đếm novel inputs; base-call coverage chưa đối chiếu là pending. '
                  'Cartesian/design cap vượt input budget ghi budget_limited; feasibility vẫn pending.', '',
                  'Config thực tế:', '```json', json.dumps(settings, ensure_ascii=False, indent=2), '```', '',
                  'Model calls/tokens thực tế theo arm (tester_calls; writer_calls là chi phí cohort đã có):',
                  '```json', json.dumps({'tester_calls': summary['tester_calls'], 'tester_calls_by_arm':summary['tester_calls_by_arm'], 'writer_calls': summary['writer_calls'],
                    'keepalive_calls': summary['keepalive_calls']}, ensure_ascii=False, indent=2), '```', '',
                  'Fail/skip và catalogue status:', '```json',
                  json.dumps({'task_skips': summary['skips'], 'generation_statuses': summary['generation_statuses'],
                              'diagnostics': summary['diagnostics'], 'catalogues': summary['catalogues']}, ensure_ascii=False, indent=2), '```', '']
        return '\n'.join(lines)


def usage_by_arm(directory, names):
    result = {}
    for name in names:
        attempts, received, missing_usage = 0, 0, 0
        totals = {key:0 for key in ('prompt_tokens','completion_tokens','total_tokens')}
        for call in directory.glob('tasks/*/calls/*'):
            if call.name != name and not call.name.startswith(name + '_unknown_attempt_'):
                continue
            attempts += (call/'attempt.json').exists()
            if (call/'response.json').exists():
                received += 1
                usage = json.loads((call/'response.json').read_text()).get('usage', {})
                missing_usage += not all(type(usage.get(key)) in (int,float) for key in totals)
                for key in totals:
                    if type(usage.get(key)) in (int,float):
                        totals[key] += usage[key]
        result[name] = {'invocations':attempts, 'received':received, 'unknown':attempts-received,
                        'known_usage':totals, 'responses_with_incomplete_usage':missing_usage}
    return result
