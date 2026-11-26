"""Shared input prompt blocks for Plain and catalogue generation."""
import json

import ast
import io
import tokenize

from .arm_names import VF3_INPUTS_PER_ROUND

INPUT_SIZE_GUIDANCE = (
    "Keep floats finite, integers bounded, strings/lists modest\n"
    "(normally <=30 elements), and execution under 3 seconds. "
)
INPUTS_ONLY = "INPUTS ONLY: no assertions or expected outputs."
INPUTS_WITH_CATALOGUE = "Return inputs with a compact catalogue; no assertions or expected outputs."
PLAIN_OUTPUT = 'Return JSON: {"inputs":[{"arguments":{"parameter_name":"a value of the correct type"},"guidance_id":null}]}.'
CATALOGUE_OUTPUT = (
    "Return one JSON object matching the supplied JSON Schema: catalogue and inputs. "
    "covers labels are optional; no expected outputs."
)
ARGUMENT_GUIDANCE = """arguments maps the EXACT function parameter names to JSON values. A list parameter needs a
nested JSON array as its value; a string parameter needs a string value. Do not write Python
args/kwargs strings, parentheses, expressions, multiplication or arithmetic inside values.
The call builder handles argument ordering, singleton tuple commas and literal serialization.
Only for actual tuple/set values, use {"__python_type__":"tuple","items":[1,2]}
or {"__python_type__":"set","items":[1,2]}. Unused default parameters may be omitted."""


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


def input_prompt_blocks(task, programs, contract, budget, *, prior_stage_inputs=(), extra_base_tests=''):
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
    def intro(budget, output_scope, size_guidance=""):
        size = "small, " if size_guidance else ""
        return f"""Generate up to {budget} {size}distinct new calls to expose specification violations
in these base-passing implementations. {output_scope}
The reference supplies outputs later. Use the specification/domain, not majority correctness.
Do not repeat base inputs. {size_guidance}Fewer valid calls are better than padding.
"""

    task_context = f'''SPECIFICATION:
{task['prompt']}
INPUT DOMAIN CONTRACT:
{contract}
ORIGINAL BASE TESTS:
{task['test']}{augmented_base}
BASE-PASSING IMPLEMENTATIONS (original line labels):
{json.dumps([{'id':program['id'],'code':compact_source(program['code'])} for program in programs],separators=(',',':'))}
'''
    return {
        "intro": intro(budget, INPUTS_ONLY, INPUT_SIZE_GUIDANCE),
        "plain_intro": intro(budget, INPUTS_ONLY),
        "catalogue_intro": intro(VF3_INPUTS_PER_ROUND, INPUTS_WITH_CATALOGUE, INPUT_SIZE_GUIDANCE),
        "output": PLAIN_OUTPUT,
        "arguments": ARGUMENT_GUIDANCE + "\n\n",
        "task_context": task_context,
    }


def render_input_prompt(packet, variant="shared"):
    if "prompt_blocks" in packet:
        blocks = packet["prompt_blocks"]
        intro = blocks.get(f"{variant}_intro", blocks["intro"])
        output = CATALOGUE_OUTPUT if variant == "catalogue" else blocks["output"]
        return f'{intro}{output}\n{blocks["arguments"]}{blocks["task_context"]}'

    # Preserve the exact request text when resuming a saved flat packet.
    common = packet["common"]
    if variant == "plain":
        instructions, separator, context = common.partition("\n\nSPECIFICATION:\n")
        instructions = instructions.replace(" small, distinct new calls", " distinct new calls", 1)
        return instructions.replace(INPUT_SIZE_GUIDANCE, "", 1) + separator + context
    if variant == "catalogue":
        return common.replace(PLAIN_OUTPUT, CATALOGUE_OUTPUT, 1).replace(INPUTS_ONLY, INPUTS_WITH_CATALOGUE)
    return common


def structured_input_prompt(task, programs, contract, budget, *, prior_stage_inputs=(), extra_base_tests=''):
    """Render the flat prompt used by the historical MBPP Pynguin runner."""
    return render_input_prompt({"prompt_blocks": input_prompt_blocks(
        task, programs, contract, budget,
        prior_stage_inputs=prior_stage_inputs, extra_base_tests=extra_base_tests,
    )})
