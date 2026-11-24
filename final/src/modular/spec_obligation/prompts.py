"""Small fixed soft examples, with no retrieval or benchmark-specific bindings."""
import json
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

INSTRUCTION = '''Use the specification, original numbered source and CFG arcs to propose
testing scenarios. Soft examples illustrate reasoning only; do not copy their applicability or inputs.
Distinguish a branch/statement not executed by base from a semantic scenario base has not exercised.
Covered code may still need a semantic test. Missing traces are UNKNOWN, not unexecuted code.
Structural paths are approximations, not feasibility or bug proofs.
Every semantic obligation binds an EXACT program_id and executable original line. Quote a requirement
verbatim from the specification; explain the operation's possible mismatch, activation relation,
construction instruction and a correct-use counterexample. A hypothesis is not a confirmed bug.
Construct a control and a contrasting representative when the contract permits: keep earlier
guards, vary the activation relation, and ensure the changed contribution can survive to return.
Use the existing scenario/instruction fields for this recipe; do not add metadata fields.
A predicate hit and site reach do not prove activation or propagation. A base hit is one witness,
not evidence that all representatives, boundaries or representations have been exercised.
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


def messages(context, evidence, *, hybrid, phase, obligations=(), targets=(), input_budget=20):
    replay = saved_messages(context, evidence, phase, input_budget)
    if replay is not None:
        return replay
    programs = []
    analyses = []
    for program in evidence.programs:
        identifier = program['id']
        analysis = evidence.analyses[identifier]
        programs.append({'program_id': identifier, 'source_sha256': analysis['source_sha256'],
            'numbered_source': '\n'.join(f'{i}: {line}' for i, line in enumerate(program['code'].splitlines(), 1))})
        analyses.append({key: value for key, value in analysis.items() if key != 'targets'})
    contract = ('Return JSON {"obligations":[{program_id,line,requirement,pattern,scenario,instruction,'
                'counterexample,predicate,strategies}],"inputs":[]}. At most3obligations. '
                'All fields except predicate/strategies are required.' if phase == 'propose' else
                'Return JSON {"inputs":[{"arguments":{"EXACT parameter name":"JSON value"},'
                '"obligation_id":"O1 or null"}]}. Inputs only, up to input_budget. '
                'Exercise selected structural targets AND missing semantic obligations when both are supplied.')
    payload = {'phase': phase, 'mode': 'coverage_and_spec' if hybrid else 'spec_obligation',
        'response_contract': contract, 'specification': context.task['prompt'],
        'trusted_contract': context.metadata.get('contract', ''),
        'parameter_names': list(evidence.builder.signature.parameters), 'input_budget': input_budget,
        'programs': programs, 'analysis': analyses, 'coverage_targets': list(targets),
        'obligations': list(obligations), 'soft_examples': SOFT_EXAMPLES}
    base = evidence.base_reminder()
    # Preserve source numbering and binding when trimming; discard whole low-priority PUT packets.
    while True:
        payload['base_inputs_do_not_repeat'] = base
        request = [{'role': 'system', 'content': INSTRUCTION},
                   {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}]
        if context.calls.token_count(request) + context.settings.input_tokens + 128 <= context.settings.context_tokens:
            return request
        if len(base) > 6:
            base = base[:len(base) // 2]
        elif len(payload['programs']) > 1:
            removed = payload['programs'].pop()['program_id']
            payload['analysis'] = [row for row in payload['analysis'] if row['program_id'] != removed]
            payload['coverage_targets'] = [row for row in payload['coverage_targets'] if row['program_id'] != removed]
            payload['obligations'] = [row for row in payload['obligations'] if row['program_id'] != removed]
        else:
            return None
