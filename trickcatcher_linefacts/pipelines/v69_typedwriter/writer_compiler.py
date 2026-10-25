"""Compile a small writer surface without inferring repairs from natural language."""
import ast
import copy
import hashlib
import json

from .binding_graph import build
from .predicate_compiler import compile_condition, normalize_aliases, check_types, strip_profile
from .joint_constructor import profile

SCHEMA = 'v69_claim_trigger_edit'


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def public_profiles(request):
    return profile([ast.literal_eval(row['arguments']) for row in request['public_examples']])


def compile_edit(request, site_id, edit):
    if edit is None:
        return None
    if not isinstance(edit, dict):
        raise ValueError('edit_object_required')
    sites = {node['id']: node for node in build(request['source'])['nodes']}
    site = sites.get(site_id)
    if site is None:
        raise ValueError('unknown_site_id')
    tree = ast.parse(request['source'])
    target = next((n for n in ast.walk(tree) if isinstance(n, ast.expr) and
                   [n.lineno, n.col_offset, n.end_lineno, n.end_col_offset] == site['span']), None)
    if target is None:
        raise ValueError('edit_expression_site_required')
    kind = edit.get('kind')
    if kind == 'operator' and set(edit) == {'kind', 'operator'}:
        operators = {
            ast.Compare: {'==': ast.Eq, '!=': ast.NotEq, '<': ast.Lt, '<=': ast.LtE, '>': ast.Gt, '>=': ast.GtE},
            ast.BinOp: {'+': ast.Add, '-': ast.Sub, '*': ast.Mult, '//': ast.FloorDiv, '%': ast.Mod},
            ast.BoolOp: {'and': ast.And, 'or': ast.Or},
        }
        if type(target) not in operators or edit['operator'] not in operators[type(target)]:
            raise ValueError('edit_operator_site_mismatch')
        changed = copy.deepcopy(target)
        operator = operators[type(target)][edit['operator']]()
        if isinstance(changed, ast.Compare):
            if len(changed.ops) != 1:
                raise ValueError('edit_ambiguous_chained_comparison')
            changed.ops = [operator]
        else:
            changed.op = operator
        return ast.unparse(ast.fix_missing_locations(changed))
    if kind == 'literal' and set(edit) == {'kind', 'value'} and type(edit['value']) in (int, bool, str):
        return ast.unparse(ast.Constant(edit['value']))
    if kind == 'expression' and set(edit) == {'kind', 'expression'}:
        text = edit['expression']
        if not isinstance(text, str) or not 1 <= len(text) <= 1600:
            raise ValueError('edit_expression_size')
        # Preserve submitted text; admission applies the existing purity/no-op gate.
        ast.parse(text, mode='eval')
        return text
    raise ValueError('edit_fields_or_kind')


def compile_proposals(request, proposals, *, mode='writer'):
    """Explicit legacy mode is only for frozen CPU replay; no schema auto-detection."""
    if mode not in ('writer', 'legacy'):
        raise ValueError('compiler_mode')
    if not isinstance(proposals, list):
        return [], [{'index': None, 'status': 'rejected', 'reason': 'proposal_list'}]
    compiled, receipts = [], []
    for index, original in enumerate(proposals[:3]):
        receipt = {'index': index, 'mode': mode, 'raw_sha256': fingerprint(original), 'rewrites': []}
        try:
            if not isinstance(original, dict):
                raise ValueError('proposal_object')
            item = copy.deepcopy(original)
            if mode == 'writer':
                required = {'site_id', 'spec_clause_id', 'family', 'required_relation', 'observed_relation',
                            'priority', 'trigger', 'edit', 'alternative_rationale'}
                if not required <= set(item) or set(item)-required-{'event_condition'}:
                    raise ValueError('writer_fields')
                profiles = public_profiles(request)
                item['trigger'], changes = compile_condition(item['trigger'], len(profiles))
                receipt['rewrites'].extend(changes)
                item['event_predicate'], changes = compile_condition(item.pop('event_condition', 'True'), len(profiles), event=True)
                receipt['rewrites'].extend(changes)
                item['alternative'] = compile_edit(request, item['site_id'], item.pop('edit'))
            else:
                item['trigger'] = normalize_aliases(item['trigger'], receipt['rewrites'])
                if 'event_predicate' in item:
                    item['event_predicate'] = normalize_aliases(item['event_predicate'], receipt['rewrites'], path='$.event')
            receipt.update(status='compiled', compiled_index=len(compiled), compiled_sha256=fingerprint(item))
            compiled.append(item)
        except (ValueError, KeyError, TypeError, SyntaxError) as exc:
            receipt.update(status='rejected', reason=type(exc).__name__+':'+str(exc)[:160])
        receipts.append(receipt)
    if len(proposals) > 3:
        receipts.append({'index': None, 'status': 'rejected', 'reason': 'proposal_cap', 'omitted': len(proposals)-3})
    return compiled, receipts


def compile_and_admit(request, proposals, *, mode='writer'):
    from .semantic_contract import admit
    compiled, receipts = compile_proposals(request, proposals, mode=mode)
    accepted = []
    for index, item in enumerate(compiled):
        receipt = next(row for row in receipts if row.get('compiled_index') == index)
        good, errors = admit(request, [item])
        if errors:
            receipt.update(status='admission_rejected', reason=errors[0]['reason'])
        else:
            accepted.extend(good)
            receipt.update(status='admitted', hypothesis_id=good[0]['id'])
    accepted.sort(key=lambda h: (-h['priority'], h['site']['span'], h['id']))
    rejected = [{'index': row['index'], 'reason': row['reason']} for row in receipts if row['status'] != 'admitted']
    return accepted, rejected, {'schema': SCHEMA, 'mode': mode, 'receipts': receipts, 'semantic_truth': 'unverified'}


def writer_packet(request, base):
    packet = copy.deepcopy(base)
    packet.pop('predicate_grammar', None)
    packet.pop('predicate_examples', None)
    packet['writer_schema'] = SCHEMA
    try:
        profiles = public_profiles(request)
        packet['argument_types'] = [{'name': f'arg{i}', 'observed_type': strip_profile(t)} for i, t in enumerate(profiles)]
    except ValueError as exc:
        packet['argument_types'] = {'unsupported_public_profile': str(exc)}
    packet['instruction'] = (
        'Return a JSON object with a hypotheses array of up to three justified spec-versus-code fault hypotheses. A code-style concern or a statement '
        'that existing behavior is correct is not a mismatch: abstain with an empty hypotheses array. '
        'Copy site_id/spec_clause_id from the supplied tables. Explain the required relation, the observed '
        'violation and why the edit follows that exact clause. Use an INTEGER priority 0..3. '
        'trigger is a short Boolean Python expression over positional arg0,arg1,... with the displayed types; '
        'use len(arg0) for string length, never compare a string to an integer. String < and <= mean Python '
        'lexicographic order, not length. The tool compiles this expression; do not write JSON predicate IR. '
        'Use an operator edit for a simple operator change; the tool preserves source operands. For a more '
        'complex edit use one pure replacement expression for the exact site, never assignment or a function. '
        'JSON null means no proposed edit; the string None is not abstention. Preserve all public examples. '
        'event_condition may be True, or a Boolean condition with local("name") at the selected site. '
        'Observed outputs and plausible prose do not establish that an edit is correct.'
    )
    packet['output_fields'] = dict(site_id='supplied site ID', spec_clause_id='supplied clause ID', family='short fault family',
        required_relation='what the spec requires', observed_relation='how this site violates it', priority='INTEGER 0..3',
        trigger='Boolean expression STRING, e.g. len(arg0) >= 3', event_condition='optional expression STRING, default True',
        edit='null or one object from edit_forms', alternative_rationale='20..1600 characters linking spec and predicted local change')
    packet['condition_language'] = {'comparisons': ['==', '!=', '<', '<=', '>', '>='],
        'boolean': ['and', 'or', 'not'], 'integer_arithmetic': ['+', '-', '% positive literal'],
        'functions': ['len(value)', 'has_duplicate(value)', 'all_distinct(value)'],
        'examples': ['len(arg0) >= 3', 'len(arg0) > 0 and arg0 != arg1', 'arg0 % 2 == 1'],
        'restrictions': 'No arbitrary calls, attributes, subscripts, comprehensions or prose. Boolean root required.'}
    packet['edit_forms'] = [{'kind': 'operator', 'operator': '<='}, {'kind': 'literal', 'value': 0},
                            {'kind': 'expression', 'expression': 'x + 1'}]
    return packet
