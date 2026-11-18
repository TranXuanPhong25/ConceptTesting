"""Admit verified tool treatments before any reference or PUT workload."""
from ..call_builder import CallBuilder
from .trusted_domain import compile_domain


def hypothesis_status(batch, index=0):
    receipts = [item for item in batch.get('tool_receipts', []) if item['tool'] == 'hypothesis']
    receipt = receipts[index] if len(receipts) > index else None
    clean = any(row.get('domain') == 'true' and not row.get('solver_rejected')
                and not any(error['stage'].startswith('P') or error['stage']=='V1' for error in row['errors'])
                and any(source['tool'] == 'hypothesis' and receipt is not None
                        and source.get('seed') == receipt['seed'] for source in row['sources'])
                for row in batch.get('candidate_ledger', []))
    exercised = receipt and receipt['status'] in {'complete', 'budget_exhausted'} and receipt['draws'] > 0 and clean
    return {'status': 'exercised' if exercised else 'not_exercised',
            'draws': receipt['draws'] if receipt else 0,
            'reason': None if exercised else 'No clean domain-valid Hypothesis candidate from this sampler'}


def treatment_status(name, batch):
    if batch.get('preparation_error'):
        return {'status': 'invalid_preparation', 'reason': batch['preparation_error']}
    authority = batch.get('domain_authority', {})
    if authority.get('status') == 'unsupported' or (authority.get('status') == 'supported'
            and batch['preparation']['domain'] != authority['expression']):
        return {'status': 'invalid_preparation', 'reason': 'Trusted admission domain mismatch/unsupported'}
    if name == 'tool_direct':
        return {'status': 'direct_control'}
    receipts = batch.get('tool_receipts', [])
    rows = batch.get('candidate_ledger', [])
    initial = hypothesis_status(batch)
    if initial['status'] != 'exercised':
        return {**initial, 'component': 'shared_hypothesis'}
    if name == 'tool_hypothesis':
        return initial
    if name == 'tool_hypothesis_extra':
        return {**hypothesis_status(batch, 1), 'component': 'extra_hypothesis'}
    if name == 'tool_hypothesis_z3':
        if any(kind not in {'int', 'bool'} for kind in batch['preparation']['types'].values()):
            return {'status': 'not_applicable', 'reason': 'Z3 exact subset requires integer/bool parameters'}
        receipt = next((item for item in receipts if item['tool'] == 'z3'), None)
        if receipt and not receipt['results']:
            return {'status': 'not_needed', 'reason': 'No uncovered eligible targets'}
        verified = [item for item in (receipt or {}).get('results', []) if item['status'] == 'sat']
        if verified:
            ids = {item['candidate_id'] for item in verified}
            native = any(row['candidate_id'] in ids and row.get('domain') == 'true'
                         and not row.get('solver_rejected') for row in rows)
            if native:
                return {'status': 'exercised', 'native_witnesses': len(verified)}
        statuses = {item['status'] for item in (receipt or {}).get('results', [])}
        if statuses and statuses <= {'unsupported'}:
            return {'status': 'not_applicable', 'reason': 'No remaining target can be translated by the exact Z3 subset'}
        if statuses and statuses <= {'unsat', 'unsupported'}:
            return {'status': 'no_witness', 'reason': 'Supported queries UNSAT; no native witness'}
        return {'status': 'not_exercised', 'reason': 'No verified native solver witness'}
    if name == 'tool_planner':
        if not batch['preparation']['factors']:
            return {'status': 'not_applicable', 'reason': 'No finite factors declared'}
        receipt = next((item for item in receipts if item['tool'] == 'allpairspy'), None)
        realized = [item for item in (receipt or {}).get('results', []) if item['status'] == 'realized']
        return {'status': 'exercised' if realized else 'not_exercised', 'realized_rows': len(realized)}
    raise ValueError('Unknown tool treatment: ' + name)


def validate_generation(contexts):
    tasks, failures, authorities = {}, [], {}
    for context in contexts:
        if context.inputs.get('skip'):
            continue
        builder = CallBuilder.for_source(context.task['prompt'], context.task['entry_point'])
        expected = compile_domain(context.metadata.get('contract', ''), builder.signature.parameters)
        authorities[context.task['task_id']] = expected
        treatments = {}
        for name, batch in context.inputs['arms'].items():
            authority_matches = batch.get('domain_authority') == expected
            if expected['status'] == 'supported':
                authority_matches = authority_matches and batch['preparation'].get('admission_types') == expected['admission_types']
            treatments[name] = (treatment_status(name, batch) if authority_matches else
                                {'status': 'invalid_preparation', 'reason': 'Missing/mismatched trusted admission receipt or types'})
        tasks[context.task['task_id']] = treatments
        for name, status in treatments.items():
            if status['status'] in {'invalid_preparation', 'not_exercised', 'no_witness'}:
                failures.append({'task_id': context.task['task_id'], 'arm': name, **status})
    report = {'ready': not failures, 'tasks': tasks, 'failures': failures, 'domain_authorities': authorities,
              'policy': 'no oracle/PUT on invalid or unexercised applicable tools; not_applicable/not_needed are not efficacy evidence'}
    contexts[0].artifacts.write('tool_generation_gate.json', report)
    for context in contexts:
        context.extensions['tool_generation_gate'] = tasks.get(context.task['task_id'], {})
    if failures:
        raise ValueError('tool_generation_gate: invalid/unexercised treatments; inspect tool_generation_gate.json')
