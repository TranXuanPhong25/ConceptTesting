"""Same common prompt across arms; only the registered guidance packet differs."""
from __future__ import annotations

import ast
import json
import io
import tokenize

ARMS=('plain','classical','contrastive','placebo','toolinput')


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


def common_prompt(task,programs,contract,budget):
    return f'''Generate exactly {budget} small, distinct new input calls to find specification violations
in these base-passing Python implementations. All inputs will be executed against
ALL retained implementations of this task. The reference program supplies expected
outputs later: generate INPUTS ONLY, never assertions or expected outputs.
Use the specification and domain contract, not presumed majority correctness.
Do not copy inputs exercised by the existing base tests. Keep floats finite, integers
bounded, strings/lists modest (normally <=30 elements), and execution under 3 seconds.
Return only compact JSON: {{"inputs":[{{"args":"(1, [2, 3])","kwargs":"{{}}","concept_id":null}}]}}.
args/kwargs must be strings containing Python literals: positional list/tuple and
keyword dict. No code, imports or expressions inside these literal strings. If a
guidance card is used, set concept_id to its id; otherwise null. Input validity and
diversity matter more than filling the budget with repeated or invalid calls.

SPECIFICATION:
{task['prompt']}
INPUT DOMAIN CONTRACT (same for every arm):
{contract}
ORIGINAL BASE TESTS:
{task['test']}
BASE-PASSING IMPLEMENTATIONS (each listing uses ORIGINAL source line numbers):
{json.dumps([dict(id=p['id'],code=compact_source(p['code'])) for p in programs],separators=(',',':'))}
'''


def messages(common,arm,analysis,witnesses):
    if arm=='plain':
        guidance='No additional analysis packet. Choose useful new tests from the information above.'
    elif arm=='toolinput':
        guidance='Optional new input examples from a deterministic library sampler (not known bugs):\n'+json.dumps(
            [dict(args=w['args'],kwargs=w['kwargs']) for w in witnesses],separators=(',',':'))
    else:
        cards=analysis[arm]
        guidance='Testing guidance (apply only when consistent with the specification):\n'+json.dumps(
            [dict(id=c['id'],kind=c['kind'],text=c['text']) for c in cards],separators=(',',':'))
    return [dict(role='system',content='You generate valid Python function inputs to expose implementation bugs.'),
            dict(role='user',content=common+'\n'+guidance)]
