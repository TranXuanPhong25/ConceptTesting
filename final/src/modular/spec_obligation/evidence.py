"""Source-bound CFG/DFG, recorded base inventory and bounded native witnesses."""
import ast
import copy
import time

from coverage.parser import PythonParser

from ..boundary_value_analysis.legacy.stages import frozen_value
from ..call_builder import CallBuilder, entry_function
from ..catalogue_membership import membership_row
from ..control_flow.analysis import analyze
from ..tool_sampling.ledger import predicate_status
from final.src.runtime.artifacts import digest
from final.src.runtime.execution import execute


class Evidence:
    def __init__(self, context, arm):
        self.context, self.arm = context, arm
        self.specification = context.task['prompt']
        self.builder = CallBuilder.for_source(self.specification, context.task['entry_point'])
        visible = set(context.packet['visible_put_ids'])
        self.programs = [copy.deepcopy(p) for p in context.cohort_task['programs']
                         if p['id'] in visible and p['base']['status'] == 'pass']
        self.by_id = {p['id']: p for p in self.programs}
        self.base_keys, self.base_records, self.base_complete = set(), {}, {}
        self.analyses, self.errors, self.base_receipts = {}, [], []
        self.observations = {}
        self.base_observations = 0
        self.predicate_checks, self.predicate_seconds = 0, 0
        self.predicate_results = {}
        # Controller dedup uses every recorded base call; prompt visibility remains separate.
        for program in context.cohort_task['programs']:
            for record in program['base'].get('calls', []):
                try:
                    self.base_keys.add(self.key(self.canonical_call(record)))
                except (ValueError, TypeError, KeyError, SyntaxError, RecursionError):
                    pass
        for program in self.programs:
            identifier, base = program['id'], program['base']
            self.base_records[identifier] = []
            self.base_complete[identifier] = isinstance(base.get('calls'), list)
            for index, record in enumerate(base.get('calls', [])):
                try:
                    call = self.canonical_call(record)
                    self.base_keys.add(self.key(call))
                    self.base_records[identifier].append({'index': index, 'call': call})
                except (ValueError, TypeError, SyntaxError, RecursionError) as error:
                    self.base_complete[identifier] = False
                    self.errors.append({'program_id': identifier, 'base_index': index, 'reason': str(error)[:400]})
            import hashlib
            source_hash = hashlib.sha256(program['code'].encode()).hexdigest()
            if base.get('source_sha256') not in (None, source_hash):
                base.pop('coverage', None)
                self.errors.append({'program_id': identifier, 'reason': 'base_source_hash_mismatch'})
            if base.get('coverage') is None and self.base_records[identifier]:
                observations = [self.observe(program, row['call'], base=True) for row in self.base_records[identifier]]
                if (self.base_complete[identifier] and
                        all(row.get('domain') == 'valid' and row.get('status') == 'executed'
                            and 'coverage' in row for row in observations)):
                    base['coverage'] = {'lines': sorted({line for row in observations for line in row['coverage']['lines']}),
                        'arcs': [list(arc) for arc in sorted({tuple(arc) for row in observations for arc in row['coverage']['arcs']})]}
            try:
                analysis = analyze(program, context.task['entry_point'])
                parser = PythonParser(text=program['code'])
                parser.parse_source()
                function = entry_function(program['code'], context.task['entry_point'])
            except (ValueError, SyntaxError, TypeError, RecursionError) as error:
                self.errors.append({'program_id': identifier, 'reason': str(error)[:400],
                                    'stage': 'source_analysis'})
                continue
            analysis['executable_lines'] = sorted(line for line in parser.statements
                                                  if function.lineno < line <= function.end_lineno)
            coverage = base.get('coverage')
            analysis['baseline_scope'] = 'recorded_calls_only; cached aggregate may lack per-input reach'
            analysis['base_inventory_complete'] = self.base_complete[identifier]
            analysis['line_coverage'] = [{'line': line, 'status': 'unknown' if coverage is None else
                'hit' if line in coverage['lines'] else 'miss'} for line in analysis['executable_lines']]
            analysis['branch_coverage'] = [{'arc': arc, 'status': 'unknown' if coverage is None else
                'hit' if arc in coverage['arcs'] else 'miss'} for arc in analysis['cfg_arcs']
                if function.lineno < arc[0] <= function.end_lineno]
            for target in analysis['targets']:
                target['source_sha256'] = analysis['source_sha256']
            self.analyses[identifier] = analysis
        self.programs = [p for p in self.programs if p['id'] in self.analyses]
        self.by_id = {p['id']: p for p in self.programs}

    def canonical_call(self, record):
        if not isinstance(record, dict):
            raise ValueError('call_object_required')
        if 'arguments' in record:
            return self.builder.build(record['arguments'])
        if any(not isinstance(record.get(field, '{}'), str) or len(record.get(field, '{}')) > 16000
               for field in ('args', 'kwargs')):
            raise ValueError('bounded_literal_required')
        args, kwargs = ast.literal_eval(record['args']), ast.literal_eval(record.get('kwargs', '{}'))
        if not isinstance(args, (tuple, list)) or not isinstance(kwargs, dict):
            raise ValueError('invalid_args_kwargs')
        bound = self.builder.signature.bind(*args, **kwargs)
        bound.apply_defaults()
        return self.builder.build_values(dict(bound.arguments))

    def arguments(self, call):
        bound = self.builder.signature.bind(*ast.literal_eval(call['args']), **ast.literal_eval(call['kwargs']))
        bound.apply_defaults()
        return dict(bound.arguments)

    def key(self, call):
        return repr(frozen_value(self.arguments(call)))

    def base_reminder(self):
        seen, result = set(), []
        for rows in self.base_records.values():
            for row in rows:
                key = self.key(row['call'])
                if key not in seen:
                    seen.add(key)
                    result.append({key: row['call'][key] for key in ('args', 'kwargs')})
        return result

    def observe(self, program, call, *, base=False):
        key = digest((program['id'], program['code'], call))
        if key in self.observations:
            return self.observations[key]
        if base and self.base_observations >= 300:
            return {'domain': 'unknown', 'status': 'base_replay_budget_exhausted'}
        path = self.context.task_directory + f'/{self.arm}/traces/{key}.json'
        result = self.context.artifacts.load_or_compute(path, lambda: execute({
            'mode': 'control_flow', 'source': program['code'], 'entry': self.context.task['entry_point'],
            'context': self.specification, 'contract': self.context.metadata.get('contract', ''),
            'tests': [call], 'timeout': min(1, self.context.settings.timeout_seconds),
            'seed': self.context.settings.input_seed})['tests'][0])
        self.observations[key] = result
        if base:
            self.base_observations += 1
            self.base_receipts.append({'program_id': program['id'], 'call': call, **result})
        return result

    def scenario(self, obligation, call, observation=None, *, base=False):
        if obligation['predicate_status'] != 'supported':
            return None, obligation.get('predicate_error', 'unsupported_predicate')
        predicate_key = (obligation['predicate'], self.key(call))
        if predicate_key not in self.predicate_results:
            if self.predicate_checks >= 512 or self.predicate_seconds >= 5:
                return None, 'predicate_budget_exhausted'
            self.predicate_checks += 1
            started = time.monotonic()
            self.predicate_results[predicate_key] = predicate_status(obligation['predicate'], self.arguments(call))
            self.predicate_seconds += time.monotonic() - started
        status, detail = self.predicate_results[predicate_key]
        if status == 'false':
            return False, None
        if status != 'true':
            return None, detail or status
        if observation is None and base:
            observation = self.observe(self.by_id[obligation['program_id']], call, base=True)
        if observation is None or observation.get('domain') != 'valid' or 'coverage' not in observation:
            return None, 'missing_valid_site_trace'
        if obligation['line'] in observation['coverage'].get('lines', []):
            return True, None
        if observation.get('status') != 'executed':
            return None, 'partial_trace_cannot_prove_miss'
        return False, None

    def base_membership(self, obligation):
        identifier = obligation['program_id']
        rows = self.base_records[identifier]
        outcomes = [self.scenario(obligation, row['call'], base=True) for row in rows]
        return membership_row(obligation['id'], outcomes, [row['index'] for row in rows],
                              checkable=self.base_complete[identifier])

    def targets(self):
        selected = []
        rows = list(self.analyses.values())
        for index in range(6):
            for analysis in rows:
                if index < len(analysis['targets']) and len(selected) < 6:
                    selected.append(analysis['targets'][index])
        return selected
