"""Modern input schema shared by plain input generation."""
import json

import ast
import io
import tokenize


INPUT_SIZE_GUIDANCE = (
    "Keep floats finite, integers bounded, strings/lists modest\n"
    "(normally <=30 elements), and execution under 3 seconds. "
)


def compact_source(source):
    """Remove prompt-only noise while preserving ORIGINAL source line labels."""
    tree=ast.parse(source)
    lines=source.splitlines()
    spans=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Expr) and isinstance(node.value,ast.Constant) and isinstance(node.value.value,str):
            spans.append((node.lineno,node.col_offset,node.end_lineno,node.end_col_offset))
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type==tokenize.COMMENT:
            spans.append((*token.start,*token.end))
    for start,col,end,endcol in sorted(spans,reverse=True):
        for row in range(start,end+1):
            begin=col if row==start else 0
            finish=endcol if row==end else len(lines[row-1])
            lines[row-1]=lines[row-1][:begin]+' '*(finish-begin)+lines[row-1][finish:]
    return '\n'.join(f'{i+1}: {line.rstrip()}' for i,line in enumerate(lines) if line.strip())


def structured_input_prompt(task, programs, contract, budget, *, prior_stage_inputs=(), extra_base_tests=''):
    augmented_base = ''
    if extra_base_tests:
        augmented_base += '\n' + extra_base_tests.rstrip() + '\n'
    if prior_stage_inputs:
        augmented_base = ('\nADDITIONAL BASE INPUTS FROM EARLIER STAGES (no expected outputs):\n'
            'Treat these calls as part of the base suite. Use their source stage and supplied '
            'technique labels to understand what was exercised. Derive which feasible decision-table '
            'rules are still missing from the actual calls and generate distinct inputs for those rules. '
            'Technique labels are hypotheses. Do not repeat these calls.\n'
            + json.dumps(prior_stage_inputs, ensure_ascii=False, separators=(',', ':')) + '\n')
    return f'''Generate up to {budget} small, distinct new calls to expose specification violations
in these base-passing implementations. INPUTS ONLY: no assertions or expected outputs.
The reference supplies outputs later. Use the specification/domain, not majority correctness.
Do not repeat base inputs. {INPUT_SIZE_GUIDANCE}Fewer valid calls are better than padding.
Return JSON: {{"inputs":[{{"arguments":{{"parameter_name":"a value of the correct type"}},"guidance_id":null}}]}}.
arguments maps the EXACT function parameter names to JSON values. A list parameter needs a
nested JSON array as its value; a string parameter needs a string value. Do not write Python
args/kwargs strings, parentheses, expressions, multiplication or arithmetic inside values.
The call builder handles argument ordering, singleton tuple commas and literal serialization.
Only for actual tuple/set values, use {{"__python_type__":"tuple","items":[1,2]}}
or {{"__python_type__":"set","items":[1,2]}}. Unused default parameters may be omitted.

SPECIFICATION:
{task['prompt']}
INPUT DOMAIN CONTRACT:
{contract}
ORIGINAL BASE TESTS:
{task['test']}{augmented_base}
BASE-PASSING IMPLEMENTATIONS (original line labels):
{json.dumps([{'id':program['id'],'code':compact_source(program['code'])} for program in programs],separators=(',',':'))}
'''
