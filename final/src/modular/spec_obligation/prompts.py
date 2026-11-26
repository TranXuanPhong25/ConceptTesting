"""Small fixed soft examples, with no retrieval or benchmark-specific bindings."""
import json
from ..control_flow.analysis import unobserved_step
from final.src.runtime.artifacts import digest

SOFT_EXAMPLES = (
    {'pattern': 'dedup loses multiplicity', 'spec_role': 'every occurrence contributes',
     'cfg_dfg_hint': 'input -> set -> aggregate -> return',
     'scenario': 'repeat a nonzero value whose contributions survive to the return',
     'correct_use': 'spec explicitly requests distinct values; dedup is then valid'},
    {'pattern': 'early return misses a later contributor', 'spec_role': 'consider all matching elements',
     'cfg_dfg_hint': 'loop body -> return, bypassing later iterations',
     'scenario': 'a later matching element changes the required result',
     'correct_use': 'spec requests only the first match'},
    {'pattern': 'overwrite loses accumulated information', 'spec_role': 'combine contributions',
     'cfg_dfg_hint': 'multiple writes -> final read; earlier write may not reach use',
     'scenario': 'earlier and later contributions differ and both matter',
     'correct_use': 'spec requests the last matching value'},
)

INSTRUCTION = '''Use the specification, original numbered source, CFG arcs and static may-def-use to propose
testing scenarios. Soft examples illustrate reasoning only; do not copy their applicability or inputs.
Distinguish a branch/statement not executed by base from a semantic scenario base has not exercised.
Covered code may still need a semantic test. Missing traces are UNKNOWN, not unexecuted code.
Structural paths and DFG edges are approximations, not feasibility or bug proofs.
Every semantic obligation binds an EXACT program_id and executable original line. Quote a requirement
verbatim from the specification; explain the operation's possible mismatch, activation relation,
construction instruction and a correct-use counterexample. A hypothesis is not a confirmed bug.
Return data only; no expected outputs, assertions, executable Python, st.* calls or imports.
Optional predicate is a boolean input expression using exact parameter names, len/sum/min/max/abs,
distinct_count, comparisons, Boolean operators and bounded indexing. Use "" when unsupported.
Predicates describe input scenarios, never claim transformed local state from inputs alone.
An unsupported predicate still permits direct construction from the scenario/instruction; its
semantic membership remains unknown. Do not drop useful direct attempts because metadata is uncertain.
Optional strategies maps ALL signature parameters in signature order to JSON descriptors:
{kind:"int",min:0,max:5}, {kind:"bool"}, {kind:"float",min:0,max:1},
{kind:"str",alphabet:"ab",min_size:0,max_size:5},
{kind:"list",elements:{kind:"int",min:0,max:3},min_size:0,max_size:5},
{kind:"sampled",values:[JSON values]}. Bounds may reference earlier parameters or len(earlier)+/-integer.
Use sampled collections or dependent bounds for correlated values; independent strategies may miss relations.
Never weaken the trusted contract to reach a target. Keep valid direct input attempts even if metadata is uncertain.
DO NOT generate any base input, including equivalent positional/keyword/default spellings.
The final base_inputs_do_not_repeat list is a compact reminder; it can be incomplete when context is limited.
The controller rejects duplicates against the full recorded base inventory.'''


def saved_messages(context, evidence, phase, input_budget):
    call = evidence.arm + '_' + phase
    relative = context.task_directory + '/calls/'
    directive = relative + call + '.frozen_request_replay.json'
    if not context.artifacts.exists(directive):
        return None
    approval = context.artifacts.read(directive)
    record = context.artifacts.read(relative + call + '/request.json')
    if not approval.get('authorization') or digest(record) != approval.get('request_id'):
        raise ValueError('frozen_request_identity_mismatch')
    expected = {'temperature': context.settings.input_temperature, 'max_tokens': context.settings.input_tokens,
                'seed': context.settings.input_seed + context.task_number + (phase == 'construct')}
    if any(record.get(k) != value for k, value in expected.items()):
        raise ValueError('frozen_request_settings_mismatch')
    request = record['messages']
    payload = json.loads(request[-1]['content'])
    if (payload.get('phase') != phase or payload.get('specification') != evidence.specification
            or payload.get('trusted_contract') != context.metadata.get('contract', '')
            or payload.get('parameter_names') != list(evidence.builder.signature.parameters)
            or payload.get('input_budget') != input_budget):
        raise ValueError('frozen_request_task_mismatch')
    for row in payload['programs']:
        program = evidence.by_id.get(row['program_id'])
        if (program is None or row['source_sha256'] != evidence.analyses[row['program_id']]['source_sha256']
                or row['numbered_source'] != '\n'.join(f'{i}: {line}' for i, line in enumerate(program['code'].splitlines(), 1))):
            raise ValueError('frozen_request_source_mismatch')
    return request


CONSTRUCT_CONTRACT = ('Return JSON {"inputs":[{"arguments":{"EXACT parameter name":"JSON value"},'
                      '"obligation_id":"O1 or null"}]}. Inputs only, up to input_budget. '
                      'Exercise selected structural targets AND missing semantic obligations when both are supplied.')

TARGET_PROPOSE = (
    'Return one JSON object with "inputs" FIRST, then "obligations". Start with concrete inputs '
    '[{"arguments":{"EXACT parameter name":"JSON value"},"target_id":"exact coverage_targets id"}]. '
    'Give one novel, contract-valid seed for each feasible target within input_budget. For an arc, '
    'work backwards from its destination through every preceding guard in path. Use base_trace_gap '
    'to see which edge the base suite lacks and which exits it exercised. Arc sets do not establish '
    'execution order. When code transforms an input before testing it, find an admitted representation '
    'that separates the transformation from the next guard. Then give up to 3 concise obligations with program_id, '
    'line, requirement, pattern, scenario, instruction, counterexample, predicate and strategies. '
    'Use the spec and the supplied source to justify each scenario.')

CONSTRUCT_OBLIGATION_FIELDS = (
    'id', 'program_id', 'line', 'requirement', 'pattern',
    'scenario', 'instruction', 'counterexample', 'predicate',
)

IMPLEMENTATION_RISK_NOTE = (
    'When inspecting numbered_source, prioritize functional correctness mismatches over stress or resource inputs: '
    'look for subtle semantic bugs, numerical or floating-point precision, rounding, and comparison-tolerance boundaries, '
    'and hidden assumptions in string, character, encoding, regex, or contract-admitted value handling. '
    'Keep inputs reasonably sized; do not spend slots on oversized inputs solely to trigger timeouts or recursion limits.'
)

TARGET_CONSTRUCT = (
    'Return only {"inputs":[{"arguments":{"EXACT parameter name":"JSON value"},'
    '"target_id":"supplied ID or null","obligation_id":"supplied ID or null"}]}. '
    'First construct a novel input for each feasible missed or untried target. Keep earlier guards '
    'satisfied while changing the condition at the missing edge. Check the requested destination '
    'against the numbered source. Treat an unknown trace as inconclusive. Then spend remaining slots '
    'on distinct controls and contrasts for the spec and obligations, including requirements the draft '
    'overlooked. Even when every target in seed_feedback is already hit or unknown, still use the full '
    'input_budget across all supplied programs; do not stop early. ' + IMPLEMENTATION_RISK_NOTE + ' '
    'Vary one requirement while satisfying the others so a difference can reach the return. '
    'A case a validator should reject may still be inside the trusted input contract. '
    'Bind only to IDs in this request, using JSON null for an unbound label. Keep inputs distinct, within input_budget '
    'and within the trusted contract.')


def target_propose_contract(obligation_limit=3):
    distinct_note = ' (prefer distinct program_ids)' if obligation_limit > 3 else ''
    risk_note = (' ' + IMPLEMENTATION_RISK_NOTE) if obligation_limit > 3 else ''
    return (
        'Return one JSON object with "inputs" FIRST, then "obligations". Start with concrete inputs '
        '[{"arguments":{"EXACT parameter name":"JSON value"},"target_id":"exact coverage_targets id"}]. '
        'Give one novel, contract-valid seed for each feasible target within input_budget. For an arc, '
        'work backwards from its destination through every preceding guard in path. Use base_trace_gap '
        'to see which edge the base suite lacks and which exits it exercised. Arc sets do not establish '
        'execution order. When code transforms an input before testing it, find an admitted representation '
        f'that separates the transformation from the next guard. Then give up to {obligation_limit} concise '
        f'obligations{distinct_note} with program_id, line, requirement, pattern, scenario, instruction, '
        f'counterexample, predicate and strategies. Use the spec and the supplied source to justify each scenario.{risk_note}'
    )


def compact_construct_obligations(obligations):
    return [{field: row[field] for field in CONSTRUCT_OBLIGATION_FIELDS if field in row} for row in obligations]


def compact_analysis(payload):
    owners = {row['program_id'] for key in ('coverage_targets', 'obligations') for row in payload.get(key, [])}
    for row in reversed(payload['analysis']):
        if row['program_id'] not in owners:
            payload['analysis'].remove(row)
            return True
    if any(row.keys() - {'program_id', 'source_sha256'} for row in payload['analysis']):
        payload['analysis'] = [{'program_id': row['program_id'], 'source_sha256': row['source_sha256']}
                               for row in payload['analysis']]
        return True
    return False


def trim_feedback_inputs(payload):
    rows = payload.get('seed_feedback', [])
    for row in reversed(rows):
        if 'input' in row:
            del row['input']
            return True
    return False


def fit_request(context, payload, *, protect_owners=False, history=(), system=INSTRUCTION):
    budget = context.settings.context_tokens - context.settings.input_tokens - 128
    while True:
        request = [{'role': 'system', 'content': system}, *history,
                   {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}]
        if context.calls.token_count(request) <= budget:
            return request
        base = payload.get('base_inputs_do_not_repeat', [])
        if not history and len(base) > 6:
            payload['base_inputs_do_not_repeat'] = base[:len(base) // 2]
            continue
        if protect_owners and (compact_analysis(payload) or trim_feedback_inputs(payload)):
            continue
        if len(payload['programs']) <= 1:
            return None
        programs = payload['programs']
        removed = programs[-1]
        if protect_owners:
            owners = {r['program_id'] for key in ('coverage_targets', 'obligations') for r in payload.get(key, [])}
            non_owner = next((p for p in reversed(programs) if p['program_id'] not in owners), None)
            if history and non_owner is None:
                return None
            removed = non_owner if non_owner is not None else removed
        programs.remove(removed)
        for key in ('analysis', 'coverage_targets', 'obligations'):
            if key in payload:
                payload[key] = [row for row in payload[key] if row['program_id'] != removed['program_id']]
        if 'seed_feedback' in payload:
            allowed = {t['id'] for t in payload['coverage_targets']}
            payload['seed_feedback'] = [row for row in payload['seed_feedback'] if row['target_id'] in allowed]


def propose_retry_messages(context, proposal_request, error):
    """Build a fresh propose retry without pasting the broken draft into context."""
    payload = json.loads(proposal_request[-1]['content'])
    payload['response_contract'] = payload['response_contract'] + (
        f' Previous propose response failed ({error}). Regenerate ONE complete, valid, concise JSON object only. '
        'Keep prose fields brief, use single quotes inside text instead of unescaped double quotes, '
        'and ensure every bracket and quote is properly closed.'
    )
    return fit_request(context, payload, protect_owners=True, system=proposal_request[0]['content'])


def repair_construct(context, proposal_request, draft, error, seed_feedback=None):
    if error == 'response_size_limit' or not draft.strip():
        return None
    payload = json.loads(proposal_request[-1]['content'])
    payload['phase'] = 'construct'
    contract = CONSTRUCT_CONTRACT
    if seed_feedback is not None and payload['coverage_targets']:
        payload['seed_feedback'] = [row.copy() for row in seed_feedback]
        contract = TARGET_CONSTRUCT
    payload['response_contract'] = contract + (
        f' The previous proposal failed to parse ({error}). Convert useful construction ideas into concrete'
        ' arguments and check them against the given specification, signature and contract. Return inputs only.')
    history = [{'role': 'user', 'content':
        'Revise this previous input-generation proposal using the current task and feedback supplied next.'},
        {'role': 'assistant', 'content': draft}]
    return fit_request(context, payload, protect_owners=True, history=history, system=proposal_request[0]['content'])


def messages(context, evidence, *, hybrid, phase, obligations=(), targets=(), input_budget=20,
             failed_proposal=None, target_seeds=False, seed_feedback=None, obligation_limit=3):
    replay = saved_messages(context, evidence, phase, input_budget)
    if replay is not None:
        return replay
    if failed_proposal is not None:
        repaired = repair_construct(context, *failed_proposal, seed_feedback=seed_feedback)
        if repaired is not None:
            return repaired
    programs = []
    analyses = []
    for program in evidence.programs:
        identifier = program['id']
        analysis = evidence.analyses[identifier]
        programs.append({'program_id': identifier, 'source_sha256': analysis['source_sha256'],
            'numbered_source': '\n'.join(f'{i}: {line}' for i, line in enumerate(program['code'].splitlines(), 1))})
        analyses.append({key: value for key, value in analysis.items() if key != 'targets'})
    if phase == 'propose':
        if obligation_limit == 3:
            limit_text = 'At most3obligations.'
        else:
            limit_text = f'At most {obligation_limit} concise obligations (prefer distinct program_ids).'
        risk_note = (' ' + IMPLEMENTATION_RISK_NOTE) if target_seeds else ''
        contract = ('Return JSON {"obligations":[{program_id,line,requirement,pattern,scenario,instruction,'
                    f'counterexample,predicate,strategies}}],"inputs":[]}}. {limit_text} '
                    f'All fields except predicate/strategies are required.{risk_note}')
    else:
        contract = (
            CONSTRUCT_CONTRACT + ' Use the full input_budget across all supplied programs; do not stop early. '
            + IMPLEMENTATION_RISK_NOTE
        ) if target_seeds else CONSTRUCT_CONTRACT
    guided = target_seeds and bool(targets)
    if guided and phase == 'construct':
        contract = TARGET_CONSTRUCT
    prompt_obligations = (
        compact_construct_obligations(obligations)
        if target_seeds and phase == 'construct'
        else list(obligations)
    )
    payload = {'phase': phase, 'mode': 'coverage_and_spec' if hybrid else 'spec_obligation',
        'response_contract': contract, 'specification': context.task['prompt'],
        'trusted_contract': context.metadata.get('contract', ''),
        'parameter_names': list(evidence.builder.signature.parameters), 'input_budget': input_budget,
        'programs': programs.copy(), 'analysis': analyses.copy(), 'coverage_targets': list(targets),
        'obligations': prompt_obligations, 'soft_examples': SOFT_EXAMPLES}
    if seed_feedback is not None:
        payload['seed_feedback'] = [row.copy() for row in seed_feedback]
    payload['base_inputs_do_not_repeat'] = evidence.base_reminder()
    request = fit_request(context, payload, protect_owners=target_seeds and phase == 'construct')
    if not guided or phase != 'propose':
        return request
    # Keep the original v1 proposal scope before budgeting the seed instructions.
    if not request or not payload['coverage_targets']:
        owners = {t['program_id'] for t in targets}
        payload['programs'] = [p for p in programs if p['program_id'] in owners]
        payload['analysis'] = [a for a in analyses if a['program_id'] in owners]
        payload['coverage_targets'] = list(targets)
    payload['response_contract'] = target_propose_contract(obligation_limit)
    payload['coverage_targets'] = [
        {**t, 'base_trace_gap': unobserved_step(t, evidence.by_id[t['program_id']]['base'].get('coverage'))}
        for t in payload['coverage_targets']]
    return fit_request(context, payload, protect_owners=True) or request
