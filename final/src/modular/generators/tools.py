"""Opt-in C/A/B tool pipeline, sharing one preparation and one initial pool."""
import copy
import json
import time

from .base import InputGenerator
from ..stages.input_preparation import InputPreparationStage
from ..tool_sampling.config import TOOL_ARMS, validate_budgets
from ..call_builder import CallBuilder
from ..input_buckets.predicates import declared_types
from ..response_json import load_response_json
from ..tool_sampling.schema import preparation_schema, parse_preparation
from ..tool_sampling.trusted_domain import compile_domain
from ..tool_sampling.ledger import CandidateLedger, error
from ..tool_sampling.constructors import sample_hypothesis, fill_z3, plan_combinations
from ..tool_sampling.selection import select_suite, hits
from final.src.runtime.artifacts import digest

PREPARATION = '''Return one compact JSON object with exactly these keys:
types: object keyed by every signature parameter, never a list. Use int/bool/float/str/list/list[int]/list[float]/list[str]; any only for an unannotated polymorphic parameter. These types describe sampling/solver support, never replace trusted input admission. Never use type-union strings.
domain: copy TRUSTED_ADMISSION_DOMAIN verbatim when supplied. This is benchmark input admission, not PUT behavior on invalid inputs. Never remove its constraints, infer that a contract assert makes invalid inputs testable, or turn a domain condition into an optional target. Without a trusted domain, keep semantic status unresolved.
domain_source_quote: exact spec or trusted-contract evidence. Do not invent bounds.
strategies: object keyed by every parameter (for f(a,b), {"a":descriptor,"b":descriptor}), never a positional list. Descriptors: {kind:int|float,min:optional number or prior-parameter +/- expression,max:optional bound}, {kind:bool}, {kind:sampled,values:[...]}, {kind:str,min_size:0,max_size:explicit spec bound or len(prior_parameter),alphabet:optional string}, {kind:list,elements:descriptor,min_size:0,max_size:explicit spec bound}. Numeric min/max may use len(prior_parameter), e.g. k:{kind:int,min:0,max:"len(arr)"}. Generate arr/a before their dependent k/b. Use {kind:unsupported,reason:"..."} when no supported constructor is justified; never invent bounds or add a constraint field. Use int min0 and base min2/max9 when these are trusted admission bounds. actions/merged_from are arrays of strings, never objects/null.
targets: [{id,kind:class|boundary|rule,predicate,context,origin:spec|contract|impl,source_quote,status:feasible|infeasible|unresolved,reason,actions,merged_from,fault_rationale,boundary_side}]. Preserve original DT rule IDs and ordered actions, no merge that loses rules. Unknown is not don't-care. Implementation-derived targets are hypotheses, never oracle definitions. Include EP classes, BVA sides (integers step1; floats spec step or nextafter, not +/-1), and feasible DT rules. Mark ambiguity unresolved. Do not assume full coverage.
factors: {factor_name:{level_name:boolean expression}}, finite spec-derived levels; use {} when unavailable.
inputs: [{arguments:{parameter:value}}], direct concrete seed inputs, maximum requested suite budget.
domain/context/predicate and factor levels must be executable boolean expressions, never prose or placeholders like all?. Use context="True" when nothing is held fixed; put explanations in reason. Expressions permit comparisons, and/or/not, +/-, indexing and bounded helper calls len/sum/min/max/abs/is_int/is_bool/is_str/is_list/all_ints/is_instance. Use all_type(xs,"int") for exact integer elements and all_instance(xs,"int,float") for Python isinstance element semantics; these differ for bool. Use distinct_count(sequence) for number of different elements/symbols; distinguish length from diversity and describe the predicate literally. A mixed/homogeneous class must state which argument and property it constrains; do not call a length-only target mixed. Use chars_in(a,"01") for binary strings, all_in_range(arr,-1000,1000) for element ranges, is_numeric(a) to check int/float/numeric-string admission, and numeric_value(a) for float(str(a).replace(',', '.')) semantics. is_numeric accepts valid floats as well as dot/comma numeric strings and rejects arbitrary text. is_finite_numeric_string(s) checks a finite dot-decimal string (does not accept comma or a non-string). Example: numeric_value(a)==numeric_value(b), not str(a).replace(...). Use is_str(a) and is_str(b) and len(a)==len(b) and chars_in(a,"01") and chars_in(b,"01"), never all?. For equal lengths, b may use min_size/max_size="len(a)". Helper types: overlapping_occurrences(text,fragment)->bool (whether any occurrences overlap), any_type/any_in/all_in/any_not_in/any_multiple->bool, slice_values(values,start,step)->sequence, distinct_count(sequence)->int. For substring membership use needle in text/not in text. Boolean helpers are not numeric counts. Bounds may reference only parameters earlier in signature order. No type()/isinstance(), arbitrary attributes, loops or comprehensions. Do not invent size20 for an unbounded string; use sampled seeds with a stated limitation or unsupported if the constructor cannot express the domain. Z3 only supports integer/bool linear comparisons and logic; keep all constraints. Do not invent behavioral classes just to exercise a tool.
Only test invalid business input when its handling is specified: testable domain must include that specified invalid class. Discount eligibility is a target, not a validity filter.
Do not include expected outputs or execute a PUT/reference. Read spec and trusted contract only.'''




class ToolInputGenerator(InputGenerator):
    def __init__(self, config, *, preparations=None, semantic_controls=None):
        self.config = validate_budgets(config)
        self.preparations = copy.deepcopy(preparations)
        self.semantic_controls = copy.deepcopy(semantic_controls)
        if preparations is not None and not isinstance(preparations, dict):
            raise ValueError('preparations must map task IDs to preparation objects')

    def configuration(self):
        return {'budgets': self.config, 'preparations': None if self.preparations is None else
                {task_id: repr(value) for task_id, value in self.preparations.items()},
                'protocol': 'tools-ep-bva-dt-v5-python-membership-signed' if self.semantic_controls is not None else 'tools-ep-bva-dt-v5-python-membership',
                'semantic_controls': self.semantic_controls, 'preparation_prompt': PREPARATION}

    def runtime_dependencies(self):
        return ('hypothesis', 'z3-solver', 'allpairspy', 'pydantic')

    def preparation_stages(self):
        # Reuse cohort eligibility without a shared PUT-visible model prompt.
        return (InputPreparationStage(()),)

    def generate(self, context):
        if context.packet and context.packet.get('skip'):
            return {'task_id': context.task['task_id'], 'skip': context.packet['skip']}
        return context.artifacts.load_or_compute(context.task_directory + '/tool_generation.json',
                                                 lambda: self.construct(context))

    def prepare(self, context):
        builder = CallBuilder.for_source(context.task['prompt'], context.task['entry_point'])
        authority = compile_domain(context.metadata.get('contract', ''), builder.signature.parameters)
        if authority['status'] == 'unsupported':
            return None, error('P1', 'invalid_response', 'unsupported_trusted_domain:' + ';'.join(authority['unsupported']))
        if self.preparations is not None:
            if context.task['task_id'] not in self.preparations:
                raise ValueError('Missing supplied preparation for ' + context.task['task_id'])
            return copy.deepcopy(self.preparations[context.task['task_id']]), None
        if context.calls is None:
            raise RuntimeError('Tool preparation requires model calls or supplied preparations')
        messages = [{'role': 'system', 'content': PREPARATION},
                    {'role': 'user', 'content': context.task['prompt'] + '\nTrusted contract:\n' +
                     context.metadata['contract'] + '\nSuite budget: ' + str(min(20, context.settings.input_budget))}]
        builder = CallBuilder.for_source(context.task['prompt'], context.task['entry_point'])
        schema = preparation_schema(builder, trusted_domain=authority['expression'])
        # Native response_format constrains structure; the local validator still
        # checks semantics of expressions and rejects unsupported requirements.
        messages[1]['content'] += '\nParameter order: ' + ', '.join(builder.signature.parameters)
        if authority['expression'] is not None:
            messages[1]['content'] += '\nTRUSTED_ADMISSION_DOMAIN (copy exactly): ' + authority['expression']
        if context.calls.token_count(messages) + context.settings.input_tokens + 128 > context.settings.context_tokens:
            return None, error('P1', 'invalid_response', 'preparation_prompt_too_large')
        complete = getattr(context.calls, 'complete_structured', None)
        if complete is None:
            raise RuntimeError('Tool preparation requires structured-completion support; no unconstrained fallback')
        response = complete(context.task_number, 'tool_preparation', messages, schema=schema,
            temperature=context.settings.input_temperature, max_tokens=context.settings.input_tokens,
            seed=context.settings.input_seed + context.task_number)
        if response.finish_reason != 'stop':
            return {'raw_response': response.text}, error('P1', 'truncated_response', response.finish_reason)
        try:
            value, _ = load_response_json(response.text)
            return value, None
        except (ValueError, TypeError) as exc:
            return {'raw_response': response.text}, error('P1', 'invalid_response', str(exc))

    def construct(self, context):
        start = time.monotonic()
        if self.config['audit_cap'] < min(20, context.settings.input_budget):
            raise ValueError('audit_cap must include the complete frozen suite')
        builder = CallBuilder.for_source(context.task['prompt'], context.task['entry_point'])
        authority = compile_domain(context.metadata.get('contract', ''), builder.signature.parameters)
        raw, preparation_error = self.prepare(context)
        try:
            if preparation_error:
                raise ValueError(preparation_error['detail'])
            model = parse_preparation(raw, builder, trusted_domain=authority['expression'])
            # Inferred types choose sampling/solver support; they cannot narrow
            # the independently compiled trusted input-admission checks.
            model['admission_types'] = (authority['admission_types'] if authority['status'] == 'supported' else model['types'])
            annotated = declared_types(context.task['prompt'], context.task['entry_point'])
            if any(model['types'][name] != kind for name, kind in annotated.items()):
                raise ValueError('preparation_type_conflicts_with_signature')
        except (ValueError, SyntaxError) as exc:
            preparation_error = preparation_error or error('P1', 'invalid_response', str(exc))
            # Retain decodable direct inputs; domain admission is deferred to the
            # post-freeze reference, exactly as for the existing direct baseline.
            model = {'types': {}, 'domain': 'True', 'targets': [], 'strategies': {}, 'factors': {},
                     'inputs': raw.get('inputs', []) if isinstance(raw, dict) and isinstance(raw.get('inputs'), list) else [],
                     'domain_support': 'deferred_reference', 'semantic_audit': 'pending'}
        base = CandidateLedger(context.task['task_id'], 'shared', builder, model)
        if preparation_error:
            base.add(raw, {'tool': 'preparation'}, errors=[preparation_error])
        for index, record in enumerate(model['inputs']):
            base.add(record, {'tool': 'direct', 'draw_index': index})
        base_inputs = []
        for program in (context.cohort_task or {}).get('programs', []):
            base_inputs.extend(program.get('base', {}).get('calls', []))
        for index, record in enumerate(base_inputs):
            # Existing cohort calls can carry output metadata; never put it in ledger.
            base.add({key: record[key] for key in ('args', 'kwargs') if key in record},
                     {'tool': 'base', 'draw_index': index})
        initial = copy.deepcopy(base)
        common_receipt = None
        if not preparation_error and any(name != 'tool_direct' for name in self.config['arms']):
            common_receipt = sample_hypothesis(initial, draws=self.config['draws'],
                seed=context.settings.input_seed + context.task_number, seconds=self.config['sample_seconds'])
        initial_hash = digest(initial.rows)
        batches = {}
        for name in self.config['arms']:
            ledger = copy.deepcopy(base if name == 'tool_direct' else initial)
            ledger.arm = name
            for row in ledger.rows:
                row['arm'] = name
            receipts = [common_receipt] if common_receipt and name != 'tool_direct' else []
            if not preparation_error:
                if name == 'tool_hypothesis_z3':
                    receipts.append(fill_z3(ledger, queries=self.config['solver_queries'],
                        timeout_ms=self.config['solver_timeout_ms'], seconds=self.config['solver_seconds']))
                elif name == 'tool_hypothesis_extra':
                    receipts.append(sample_hypothesis(ledger, draws=self.config['extra_draws'],
                        seed=context.settings.input_seed + context.task_number + 1000003, seconds=self.config['extra_seconds']))
                elif name == 'tool_planner':
                    receipts.append(plan_combinations(ledger, rows=self.config['planner_rows'],
                        draws_per_row=self.config['planner_draws'], seed=context.settings.input_seed + context.task_number,
                        seconds=self.config['planner_seconds'], solver_queries=self.config['planner_solver_queries'],
                        timeout_ms=self.config['solver_timeout_ms']))
            suite = select_suite(ledger, min(20, context.settings.input_budget))
            covered = set().union(*(hits(row) for row in ledger.selected_rows()))
            snapshot = {**model, 'inputs': [repr(record) for record in model['inputs']]}
            batches[name] = {'inputs': suite, 'candidate_ledger': ledger.rows, 'preparation': snapshot,
                'domain_authority': authority,
                'preparation_error': preparation_error, 'preparation_sha256': digest(repr(raw)),
                'initial_pool_sha256': initial_hash, 'tool_receipts': receipts,
                'uncovered_targets': [target['id'] for target in model['targets'] if target['id'] not in covered],
                'status': 'preparation_invalid_direct_fallback' if preparation_error else 'generated',
                'selected_unique_dt_rules_lost_to_cap': [target['id'] for target in model['targets']
                    if target.get('kind') == 'rule' and target.get('status') == 'feasible'
                    and target['id'] not in covered and sum(target['id'] in hits(row) for row in ledger.pool()) == 1]}
        return {'task_id': context.task['task_id'], 'arms': batches, 'generation_seconds': time.monotonic() - start}

    def validate_generation(self, contexts):
        if self.semantic_controls is not None:
            from ..tool_sampling.semantic_controls import check_controls
            reports = {}
            for context in contexts:
                if context.inputs.get('skip'):
                    continue
                builder = CallBuilder.for_source(context.task['prompt'], context.task['entry_point'])
                model = next(iter(context.inputs['arms'].values()))['preparation']
                reports[context.task['task_id']] = check_controls(model, builder,
                    self.semantic_controls.get(context.task['task_id'], {}))
            ready = all(report['passed'] for report in reports.values())
            contexts[0].artifacts.write('semantic_controls_gate.json', {'ready':ready,'tasks':reports})
            if not ready:
                raise ValueError('semantic_controls_gate: independent signed examples contradict or do not cover targets')
        from ..tool_sampling.gate import validate_generation
        validate_generation(contexts)

    def post_evaluation_stages(self, execution_cache, reference_programs):
        from ..tool_sampling.audit import ToolAuditStage
        return (ToolAuditStage(self.config, execution_cache, reference_programs),)

    def reporting_stage(self):
        from ..tool_sampling.reporting import ToolReportingStage
        return ToolReportingStage()
