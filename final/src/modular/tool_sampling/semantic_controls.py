"""Challenge candidate targets with independently labeled input scenarios."""
import ast
from .ledger import predicate_status


def check_controls(model, builder, controls):
    rows, failures = [], []
    declared = controls.get('targets', []) if isinstance(controls, dict) else []
    by_id = {item.get('target_id'): item for item in declared if isinstance(item, dict)}
    if len(by_id) != len(declared):
        failures.append({'code':'duplicate_or_invalid_control_target'})
    targets = {item['id']:item for item in model['targets']}
    for target_id in set(by_id)-set(targets):
        failures.append({'target_id':target_id,'code':'unknown_control_target'})
    for target_id,target in targets.items():
        signed = by_id.get(target_id)
        if signed is None:
            failures.append({'target_id':target_id,'code':'missing_independent_controls'})
            continue
        examples = signed.get('examples', [])
        expected_labels = set()
        for example in examples:
            item = {'target_id':target_id, 'arguments':example.get('arguments'), 'expected':example.get('expected'),
                    'reason':example.get('reason'), 'passed':False}
            try:
                if type(item['expected']) is not bool or not isinstance(item['reason'],str) or not item['reason'].strip():
                    raise ValueError('unknown_or_unexplained_control_label')
                call = builder.build(item['arguments'])
                bound = builder.signature.bind(*ast.literal_eval(call['args']),**ast.literal_eval(call['kwargs']))
                bound.apply_defaults();args=dict(bound.arguments)
                domain,detail=predicate_status(model['domain'],args)
                if domain!='true':
                    raise ValueError('control_outside_trusted_domain')
                context,_=predicate_status(target.get('context','True'),args)
                predicate,_=predicate_status(target['predicate'],args)
                if context not in {'true','false'} or predicate not in {'true','false'}:
                    raise ValueError('control_membership_unknown_or_error')
                actual=context==predicate=='true'
                item.update(actual=actual,passed=actual is item['expected'])
                expected_labels.add(item['expected'])
                if not item['passed']:
                    item['code']='semantic_membership_mismatch';failures.append(item)
            except (TypeError,ValueError,SyntaxError) as exc:
                item['code']=str(exc);failures.append(item)
            rows.append(item)
        if True not in expected_labels and target.get('status') != 'infeasible':
            failures.append({'target_id':target_id,'code':'missing_positive_control'})
        if False not in expected_labels and signed.get('negative_status')!='not_applicable':
            failures.append({'target_id':target_id,'code':'missing_negative_control'})
        if signed.get('negative_status')=='not_applicable' and not signed.get('reason'):
            failures.append({'target_id':target_id,'code':'unexplained_no_negative_control'})
    return {'passed':not failures,'targets':len(targets),'checked_examples':len(rows),'checks':rows,'failures':failures,
            'evidence_scope':'Finite independent labeled controls, not proof of NL equivalence; no PUT/reference output used'}
