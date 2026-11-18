"""Post-freeze pool diagnostic, separate artifacts and no suite mutation."""
from dataclasses import replace
import copy
import random
import statistics

from ..artifacts import ArtifactStore
from ..stages.base import PipelineStage
from ..stages.reference_oracle import ReferenceOracleStage
from ..stages.put_evaluation import PutEvaluationStage
from .selection import hits


def classify_misses(rows, failing_ids, *, suite_detected, complete):
    by_id = {row['candidate_id']: row for row in rows}
    selected = {row['candidate_id'] for row in rows if row['selected']}
    report = {}
    for put, failures in failing_ids.items():
        if put in suite_detected:
            gap = 'detected'
        elif failures & selected:
            gap = 'oracle_eval_gap'
        elif failures:
            gap = 'selector_gap' if any(hits(by_id[key]) for key in failures) else 'catalogue_gap'
        else:
            gap = 'generation_gap' if complete else 'pending_audit_cap'
        report[put] = {'gap': gap, 'parse_interface_gap': 'unknown',
                       'revealing_candidate_ids': sorted(failures),
                       'planner_rows': sorted({source['planner_row_id'] for key in failures
                           for source in by_id[key]['sources'] if 'planner_row_id' in source})}
    return report


def unique_pool(batch):
    groups = {}
    for row in batch['candidate_ledger']:
        if (row['canonical_args'] is not None and row.get('domain') == 'true'
                and not row.get('solver_rejected')
                and not any(item['stage'].startswith('P') or item['stage'] == 'V1' for item in row['errors'])):
            groups.setdefault(row['dedup_group'], row)
    return list(groups.values())


def source_contributions(rows, failing_ids):
    tools = {source['tool'] for row in rows for source in row['sources']} | {'planner'}
    result = {}
    for tool in sorted(tools):
        def exclusively_from(row):
            if tool == 'planner':
                return all('planner_row_id' in source or 'planner_dt_rule_id' in source for source in row['sources'])
            return {source['tool'] for source in row['sources']} == {tool}
        exclusive = {row['candidate_id'] for row in rows if exclusively_from(row)}
        result[tool] = {'exclusive_candidate_inputs': len(exclusive),
                        'exclusive_only_detected_puts': [put for put, ids in failing_ids.items()
                            if ids and ids <= exclusive]}
    return result


class ToolAuditStage(PipelineStage):
    name = 'tool_selection_audit'
    requires = ('put_evaluation',)

    def __init__(self, config, execution_cache, reference_programs):
        self.config, self.execution_cache, self.reference_programs = config, execution_cache, reference_programs

    def configuration(self):
        return {'audit_cap': self.config['audit_cap'], 'random_seeds': self.config['random_seeds'],
                'reference': self.reference_programs.configuration()}

    def run(self, context):
        if context.oracle is None and not context.inputs.get('skip'):
            raise RuntimeError('Pool audit requires reference evaluation')
        if context.inputs.get('skip'):
            return
        results = {}
        for name, batch in context.inputs['arms'].items():
            path = context.task_directory + '/tool_audit/' + name + '.json'
            results[name] = context.artifacts.load_or_compute(path, lambda: self.audit(context, name, batch))
        context.extensions['tool_sampling'] = results

    def audit(self, context, name, batch):
        pool = unique_pool(batch)
        # Include the frozen suite first so a cap never hides selected witnesses.
        ordered = sorted(pool, key=lambda row: (not row['selected'], row['dedup_group']))
        rows = ordered[:self.config['audit_cap']]
        complete = len(rows) == len(pool)
        records = [dict(row['canonical_args'], candidate_id=row['candidate_id']) for row in rows]
        audit_artifacts = ArtifactStore(context.artifacts.path('tool_audit_execution/' + name),
                                       read_only=context.artifacts.read_only)
        audit_context = replace(context, artifacts=audit_artifacts, inputs={'task_id': context.task['task_id'],
            'arms': {'pool_all': {'inputs': records, 'catalogue_status': 'off'}}},
            oracle=None, result=None, extensions={}, completed_stages=set())
        ReferenceOracleStage(self.execution_cache, self.reference_programs).run(audit_context)
        PutEvaluationStage(self.execution_cache).run(audit_context)
        first_reference = audit_artifacts.read(context.task_directory + '/oracle_0.json')['tests']
        indices = {item['input_key']: index for index, item in enumerate(audit_context.oracle['tests'])}
        candidates_by_index = {}
        index_by_candidate = {}
        for row, outcome in zip(rows, first_reference):
            index = indices.get(outcome.get('input_key')) if outcome['status'] == 'ok' else None
            if index is not None:
                candidates_by_index.setdefault(index, set()).add(row['candidate_id'])
                index_by_candidate[row['candidate_id']] = index
        failing_ids = {put: set().union(*(candidates_by_index.get(index, set()) for index in outcome['failing']))
                       for put, outcome in audit_context.result['outcomes'].items()}
        suite_detected = set(context.result['arms'][name]['detected_put_ids'])
        misses = classify_misses(rows, failing_ids, suite_detected=suite_detected, complete=complete)
        cap = min(20, context.settings.input_budget)
        controls = []
        # Same clean candidate pool for random and greedy; reference rejects remain
        # in the draw and simply have no detection, matching pre-oracle selection.
        for seed in self.config['random_seeds']:
            chosen = random.Random(seed).sample(rows, min(cap, len(rows)))
            ids = {row['candidate_id'] for row in chosen}
            controls.append({'seed': seed, 'inputs': len(chosen),
                             'detected': sum(bool(ids & failures) for failures in failing_ids.values())})
        detected = sum(bool(ids) for ids in failing_ids.values())
        from .reporting import funnel, coverage
        from final.src.audits.detection_kinds import classify_arm, kind_counts
        reference_rejections = [dict(item, candidate_id=rows[item['index']]['candidate_id'], stage='V3')
                                for item in audit_context.oracle['rejected']]
        return {'funnel': funnel(batch), 'coverage': coverage(batch),
                'pool_ceiling': {'complete': complete, 'pool_candidates': len(pool), 'audited_candidates': len(rows),
                                 'detected': detected if complete else None, 'observed_detected_lower_bound': detected,
                                 'eligible_puts': context.result['base_pass']},
                'greedy': {'detected': len(suite_detected), 'inputs': len(batch['inputs'])},
                'random_control': {'scope': 'full_pool' if complete else 'capped_pool', 'seeds': controls,
                                   'mean_detected': statistics.mean(row['detected'] for row in controls),
                                   'range_detected': [min(row['detected'] for row in controls), max(row['detected'] for row in controls)]},
                'misses': misses, 'reference_rejections': reference_rejections,
                'source_contributions': source_contributions(rows, failing_ids),
                'detection_kinds': kind_counts(classify_arm(audit_artifacts.directory, 'pool_all')),
                'candidate_to_oracle_index': index_by_candidate,
                'tool_receipts': batch['tool_receipts'], 'preparation_error': batch['preparation_error'],
                'unique_dt_rules_lost_to_cap': batch['selected_unique_dt_rules_lost_to_cap'],
                'cache_receipts': audit_context.extensions.get('input_execution_cache', {}),
                'parse_interface_gap': 'unknown: no automatic raw repair or inferred detection',
                'semantic_audit': 'pending'}
