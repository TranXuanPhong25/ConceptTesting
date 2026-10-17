"""JSON Schema interfaces and prompts; semantics authored by Qwen, not AST/name matching."""
import json

from jsonschema import Draft202012Validator

from .common import syntax_evidence, strict_json
from .predicates import validate_code

TEXT = {'type': 'string', 'maxLength': 4096}
NONEMPTY = dict(TEXT, minLength=1)


def obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


SCHEMAS = {
    'contract': obj({'decision': {'enum': ['proposed', 'unknown']}, 'spec_quote': TEXT,
                     'domain': NONEMPTY, 'relation': TEXT, 'uncertainty': TEXT, 'predicate_source': TEXT}),
    'behavior': obj({'summary': NONEMPTY, 'source_lines': {'type': 'array', 'maxItems': 12,
                                                         'items': {'type': 'integer'}}, 'limitations': TEXT}),
    'hypothesis': obj({'obligation_id': {'const': 'O1'},
                       'verdict': {'enum': ['mismatch', 'consistent', 'unknown']},
                       'target_line': {'type': ['integer', 'null']}, 'claim': TEXT,
                       'trigger_source': TEXT, 'predicted_effect': TEXT, 'alternative': TEXT,
                       'reason': NONEMPTY}),
    'inputs': obj({'inputs': {'type': 'array', 'maxItems': 3,
                              'items': obj({'arguments': {'type': 'object'}, 'purpose': {'enum': ['trigger', 'contrast']}})},
                   'reason': NONEMPTY})
}
VALIDATORS = {k: Draft202012Validator(v) for k, v in SCHEMAS.items()}


def parse(stage, text, task):
    stage = {'hyp_revision': 'hypothesis', 'revision': 'inputs'}.get(stage, stage)
    value = strict_json(text)
    errors = list(VALIDATORS[stage].iter_errors(value))
    if errors:
        raise ValueError('schema:' + errors[0].validator)
    statements = {n['span'][0] for n in task['nodes']
                  if n['is_statement'] and n['execution_scope'] == 'function_body'}
    if stage == 'contract':
        if value['decision'] == 'proposed':
            if not value['spec_quote'] or value['spec_quote'] not in task['spec'] or not value['relation'].strip():
                raise ValueError('contract_quote_or_relation')
            validate_code(value['predicate_source'], 'obligation')
        elif value['predicate_source'] or not value['uncertainty'].strip():
            raise ValueError('unknown_contract_requires_uncertainty_and_no_predicate')
    if stage == 'behavior' and any(x not in statements for x in value['source_lines']):
        raise ValueError('behavior_source_reference')
    if stage == 'hypothesis':
        if value['target_line'] is not None and value['target_line'] not in statements:
            raise ValueError('hypothesis_source_reference')
        if value['verdict'] == 'mismatch':
            if value['target_line'] is None or not value['claim'].strip():
                raise ValueError('mismatch_requires_target_claim')
            validate_code(value['trigger_source'], 'trigger')
        elif value['trigger_source']:
            raise ValueError('non_mismatch_has_no_trigger')
    return value


def messages(stage, task, **data):
    """Every stage is a fresh API context; upstream raw outputs stored separately."""
    system = ('Return exactly one JSON object matching the supplied schema, no Markdown. '
              'Unknown intent must remain unknown. Cite real source statements. Tools have '
              'bounded observational scope. Preserve original domain; unsupported is unknown.')
    if stage == 'contract':
        context = {'signature': task['signature'], 'spec': task['spec']}
        instruction = (
            'Extract one precise full returned-value relation (an executable obligation) from '
            'the spec, with its source quote, original domain and uncertainty. If intended '
            'output semantics are undefined, decision=unknown, predicate_source="", and explain '
            'uncertainty. Otherwise decision=proposed. Write Python code defining exactly '
            'def obligation(arguments, observation): returning a bool. arguments maps parameter '
            'names to JSON values before execution. observation is {"status":"ok","value":value} '
            'or {"status":"exception","exception_type":name}. Required normal results must reject '
            'exception observations. Enforce output TYPE, ordering, multiplicities, quantifiers '
            'and boundary where specified: bool differs from int, True is not integer1. '
            'Use only pure builtins Counter,all,any,bool,int,isinstance,len,list,max,min,set,sorted, '
            'sum,tuple,type. Counter is preloaded. No imports, attributes, mutation, helper '
            'functions, recursion or statement loops. Local assignments, if/return and bounded '
            'generator/list comprehensions are allowed. Code must decide permitted output from '
            'the spec, never imitate a PUT. Do not narrow the input domain.')
        schema = SCHEMAS['contract']
    elif stage == 'behavior':
        context = {'code': task['source_masked'], 'syntax': syntax_evidence(task)}
        instruction = ('Describe actual returned behavior and guards. Distinguish unused/dead '
                       'operations from returned effects. Masked docstring is not missing code. '
                       'Do not invent missing empty guards or speculative outside-domain defects.')
        schema = SCHEMAS['behavior']
    else:
        context = {'signature': task['signature'], 'spec': task['spec'], 'code': task['source_masked'],
                   'base_tests': task['base'], **data}
        if stage in ('hypothesis', 'hyp_revision'):
            instruction = (
                'Compare obligation O1 with actual returned behavior; propose one mismatch, '
                'consistent or unknown hypothesis. For mismatch choose ONE real target_line '
                'and define def trigger(arguments): returning bool with a feasible sufficient '
                'distinguishing input condition, not just line reach. Use the same restricted '
                'pure Python language as obligation. State predicted effect and an alternative. '
                'For consistent/unknown use trigger_source="" and target_line=null. Original '
                'domain applies. You cannot change obligation O1 or its semantics. Native '
                'evidence does not itself prove specification correctness.')
            if stage == 'hyp_revision':
                instruction += (' Review initial hypothesis and all provided counterevidence; '
                                'keep, revise, withdraw to consistent or mark unknown. Only '
                                'hypothesis/trigger may change; O1 remains frozen. An observed '
                                'trigger pass without a violation is counterevidence to that '
                                'candidate, not proof of global consistency.')
            schema = SCHEMAS['hypothesis']
        else:
            instruction = (
                'Propose up to3 NEW concrete inputs using {"arguments":{"parameter_name":JSON_value},'
                '"purpose":"trigger" or "contrast"}. Do not produce Python tuples, code, '
                'expected outputs or predicted outputs. Respect original domain. Challenge '
                'hypotheses and seek new distinguishing cases outside the shared pool inputs '
                'shown. If intent is undefined, abstain with inputs=[]. Verification states '
                'describe observed evidence only, not universal correctness.')
            if 'hypothesis_support_state' in data:
                instruction += (
                    ' Use only the calibrated executable obligation. When an observed-supported '
                    'hypothesis is supplied, trigger candidates must satisfy its trigger(arguments) '
                    'and seek an observation making obligation(arguments, observation) False while '
                    'reaching target_line. Contrast candidates may challenge that condition. '
                    'Unsupported hypotheses are not established faults; do not invent a replacement '
                    'contract. If no calibrated obligation is available, abstain with inputs=[].')
            if stage == 'revision':
                instruction += ' Review fixed replay feedback, preserve contrary evidence and propose additional inputs.'
            schema = SCHEMAS['inputs']
    return [{'role': 'system', 'content': system},
            {'role': 'user', 'content': json.dumps({'instruction': instruction, 'context': context,
                                                   'schema': schema}, sort_keys=True, ensure_ascii=False)}]
