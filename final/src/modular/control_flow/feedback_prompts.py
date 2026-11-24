"""Original CF concept guidance, extended with optional spec scenarios and native feedback."""
import json
from .feedback import scoped_feedback
from final.src.runtime.artifacts import digest

INSTRUCTION = '''Discover testing CONCEPTS that help construct inputs for the supplied uncovered C1/C2 targets.
Return ONLY one JSON object with keys concepts and inputs; no expected outputs or assertions.
concepts (up to 6): [{id,target_id,name,input_relation,instruction,evidence_lines,predicate,strategies}].
Use EXACT string target_id from coverage_targets[].id, never a program_id or source line number.
When coverage_targets is empty, return concepts: []; do not invent targets. Use optional obligations
and direct inputs for semantic scenarios in already covered code.
A concept is a meaningful input scenario, not just a line number:
explain the parameter relationship or operation behavior, the construction recipe, and the earlier
guards needed to reach it. Use source assignments and guards; a structural path is only an
approximation, never proof. Keep semantic claims as hypotheses; never infer an oracle from PUT output.
Return inputs FIRST. Construct control/contrast representatives that preserve earlier guards and
change the relevant data relation; account for how that contribution can survive to the return.
Target reach alone is not activation. Use first_unobserved_arc/observed_exits to repair a missed guard;
arc membership does not establish event order. Keep valid prior input relations unless feedback
contradicts them, and explain revisions in the existing input_relation/instruction fields.
Examples of concept families: cardinality after dedup, first/later occurrence, equality after aggregation,
later loop update, alternative after an early return. Derive the actual binding from this source.
evidence_lines is a nonempty integer list of ORIGINAL source lines supporting the concept.
predicate is an optional safe boolean expression over INPUT PARAMETERS, or "" if not representable.
Every predicate clause must depend on an actual parameter: sum([1,2]) == 3 is a constant example,
not a predicate about xs. If a relation such as sum of positive xs cannot be expressed with the
allowed helpers, use predicate="" and retain the concept/instruction for native target checking.
Allowed expressions: comparisons, and/or/not, +/-, indexing, len/sum/min/max/abs, distinct_count(sequence).
No local branch variables, attributes, imports, comprehensions, arbitrary calls or executable code.
strategies is {} or an object keyed by EVERY signature parameter; descriptors reuse Hypothesis:
{kind:int,min:integer,max:integer}, {kind:bool}, {kind:sampled,values:[JSON values]},
{kind:str,min_size:integer,max_size:integer,alphabet:string},
{kind:list,elements:descriptor,min_size:integer,max_size:integer}.
Dependent bounds may refer to an earlier parameter, e.g. max:"len(xs)". Keep search sizes <=30.
Finite values/search limits are exploration budgets, never new spec/domain constraints.
Use sampled values for correlated constructions that independent descriptors cannot express.
inputs: [{arguments:{EXACT parameter name: JSON value},concept_id:string_or_null}], up to input_budget.
Do not repeat base inputs. Inputs must satisfy the trusted contract. Keep direct input attempts even
when an abstraction is uncertain. In a feedback round revise concepts/strategies based on target hit,
domain failures or runtime status. Unknown or a timeout does not mean unreachable. All unmet targets,
including currently unsupported scenarios, remain eligible; never claim coverage from your own labels.'''

INSTRUCTION += '''
Only the current allowed_target_ids and their supplied sources are actionable; previous proposals
may refer to deferred targets. Never guess the source or binding of a target omitted from this request.
If source reasoning suggests a target cannot be reached, you may set optional feasibility to
"suspected_infeasible" and explain the reason in input_relation/instruction. This is an unverified
hypothesis, not a proof. Use strategies:{} and focus new attempts on other supplied targets instead
of repeating the same failed construction. No field may declare infeasibility confirmed.
Each target_diagnostics entry keeps an observed input and missed-guard evidence, or an explicit
unknown reason when no observation exists. Arc sets do not prove event order or joint feasibility.'''

INSTRUCTION += '\nUse the input_representation contract: finite JSON values with supported tuple/set tags; no complex numbers or executable expressions. A PUT branch does not establish valid public input types.'



def messages(context, evidence, targets, *, semantic, feedback=None, obligations=(), previous_response=None, round_index=None,
             obligations_only=False):
    from ..spec_obligation.prompts import INSTRUCTION as SPEC_INSTRUCTION, SOFT_EXAMPLES
    if round_index is None:
        round_index = 1 if feedback is not None else 0
    call = evidence.arm + f'_round_{round_index}'
    path = context.task_directory + '/calls/' + call
    directive = path + '.frozen_request_replay.json'
    if context.artifacts.exists(directive):
        approval = context.artifacts.read(directive)
        record = context.artifacts.read(path + '/request.json')
        if not approval.get('authorization') or digest(record) != approval.get('request_id'):
            raise ValueError('frozen_cf_request_identity_mismatch')
        expected = {'temperature': context.settings.input_temperature, 'max_tokens': context.settings.input_tokens,
                    'seed': context.settings.input_seed + context.task_number + round_index}
        if any(record.get(k) != v for k, v in expected.items()):
            raise ValueError('frozen_cf_request_settings_mismatch')
        request = record['messages'];payload = json.loads(request[-1]['content'])
        if (payload.get('round') != round_index or payload.get('specification') != evidence.specification
                or payload.get('trusted_contract') != context.metadata.get('contract', '')
                or payload.get('parameter_names') != list(evidence.builder.signature.parameters)
                or payload.get('input_budget') != min(20, context.settings.input_budget)):
            raise ValueError('frozen_cf_request_task_mismatch')
        for row in payload['programs']:
            program = evidence.by_id.get(row['program_id'])
            if (program is None or row['source_sha256'] != evidence.analyses[row['program_id']]['source_sha256']
                    or row['numbered_source'] != '\n'.join(f'{i}: {line}' for i, line in enumerate(program['code'].splitlines(), 1))):
                raise ValueError('frozen_cf_request_source_mismatch')
        return request
    instruction = SPEC_INSTRUCTION if obligations_only else INSTRUCTION
    if obligations_only:
        instruction+='''
Return exactly ONE JSON object with keys inputs and obligations, inputs FIRST:
{"inputs":[{"arguments":{"EXACT parameter name":"JSON value"},"obligation_id":"O1 or null"}],
 "obligations":[{"program_id":"COPY_SUPPLIED_ID","line":1,"requirement":"quote from specification",
 "pattern":"operation risk","scenario":"activation relation","instruction":"control/contrast construction",
 "counterexample":"when this operation is correct","predicate":"safe input expression or empty string","strategies":{}}],"reason":"required when obligations is empty"}.
obligations is REQUIRED in BOTH rounds, at most 3. Propose at least one justified source-bound
requirement scenario when applicable. If none can be justified, return obligations:[] and a nonempty
reason; this is an unexercised treatment, not successful obligation-guided generation.
Do not return concepts or target_id: this arm has no structural coverage targets. Use exact
program_id and original executable line from programs/analysis. Preserve valid earlier obligations
unless measured feedback contradicts them. A base hit is one witness, not adequacy.
Always retain useful direct inputs when metadata is invalid; round 1 repairs errors using the
measured seed/sampling feedback. No expected/actual outputs or assertions.'''
    elif semantic:
        instruction=instruction.replace('keys concepts and inputs;', 'keys inputs, concepts and obligations;')
        instruction=instruction.replace('Use optional obligations','Use grounded obligations')
        instruction += '\n\n' + SPEC_INSTRUCTION + '''
The obligations key is required; propose justified semantic scenarios (at most 3):
[{program_id,line,requirement,pattern,scenario,instruction,counterexample,predicate,strategies}].
Always return concepts AND direct seed inputs in BOTH rounds; add obligations alongside them.
If no obligation is justified, use obligations:[] and a nonempty reason; do not omit the key.
inputs may carry concept_id and/or obligation_id. Empty or invalid metadata never forbids inputs.
Return input records FIRST so complete seed inputs survive a truncated metadata tail.
Construct inputs for remaining C1/C2 outcomes independently of semantic pattern examples. A concept
must address the actual branch condition; do not replace a type/guard scenario with a generic pattern.
Base hit only means one scenario witness exists, not that all representatives or boundaries were tested.
Round 1 revises concepts/scenarios/strategies/inputs using native feedback: remaining target IDs,
input relation + site reach, parse errors, domain rejections, runtime status and unobserved candidates.
Do not call a target infeasible because it timed out or a strategy failed. Keep the trusted contract.
No expected outputs/PUT return values are available during generation. Do not invent them as evidence.
Keep metadata concise so seed inputs, concepts and obligations fit the response budget.'''
    remaining = set(feedback.get('remaining_target_ids', [t['id'] for t in targets])) if feedback is not None else {t['id'] for t in targets}
    unpresented = set(feedback.get('unpresented_target_ids', [])) if feedback is not None else remaining
    prior_programs = set(feedback.get('supplied_program_ids', [])) if feedback is not None else set()
    priority = {p['id']: 3 if p['id'] in prior_programs else 2 for p in evidence.programs}
    for target in targets:
        rank = 0 if target['id'] in unpresented else 1 if target['id'] in remaining else 3
        priority[target['program_id']] = min(priority[target['program_id']], rank)
    programs = [{'program_id': p['id'], 'source_sha256': evidence.analyses[p['id']]['source_sha256'],
        'numbered_source': '\n'.join(f'{i}: {line}' for i, line in enumerate(p['code'].splitlines(), 1))}
        for p in sorted(evidence.programs, key=lambda p: priority[p['id']])]
    payload = {'phase': 'feedback' if feedback is not None else 'propose',
        'round': round_index, 'specification': context.task['prompt'],
        'trusted_contract': context.metadata.get('contract', ''),
        'parameter_names': list(evidence.builder.signature.parameters),
        'input_representation':{'signature':str(evidence.builder.signature),
            'public_input_types':getattr(evidence.builder,'input_types',{}),
            'wire':'finite JSON values; tuple/set via __python_type__/items; complex unsupported',
            'search_limits_are_not_specification_bounds':True},
        'input_budget': min(20, context.settings.input_budget), 'programs': programs,
        'analysis': [{k: v for k, v in analysis.items() if k != 'targets'} for analysis in evidence.analyses.values()],
        'coverage_targets': targets, 'obligations': list(obligations), 'feedback': feedback}
    if semantic:
        payload['soft_examples'] = SOFT_EXAMPLES
    base = evidence.base_reminder()
    # As in CF/v1, remove whole packets, never renumber source or truncate its body.
    while True:
        payload['allowed_target_ids'] = [t['id'] for t in payload['coverage_targets']]
        payload['feedback'] = scoped_feedback(payload['feedback'], payload['coverage_targets'],
                                              {p['program_id'] for p in payload['programs']}, payload['obligations'])
        payload['base_inputs_do_not_repeat'] = base
        request = [{'role': 'system', 'content': instruction},
                   {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}]
        if previous_response is not None:
            request[1:1]=[{'role':'user','content':'Revise this previous input-generation proposal using the current task and feedback supplied next.'},
                          {'role':'assistant','content':previous_response}]
        if context.calls.token_count(request) + context.settings.input_tokens + 128 <= context.settings.context_tokens:
            return request
        if len(base) > 6:
            base = base[:len(base) // 2]
        elif feedback is not None and payload['feedback'].get('candidates'):
            payload['feedback'] = {**payload['feedback'], 'candidates': payload['feedback']['candidates'][:-1]}
            payload['feedback']['candidate_details_truncated'] = True
        elif len(payload['programs']) > 1:
            removed = payload['programs'].pop()['program_id']
            payload['analysis'] = [r for r in payload['analysis'] if r['program_id'] != removed]
            payload['coverage_targets'] = [r for r in payload['coverage_targets'] if r['program_id'] != removed]
            payload['obligations'] = [r for r in payload['obligations'] if r['program_id'] != removed]
        else:
            return None

