"""Read the author's MIT-licensed prompt as data, preserve vendor sources."""
import ast
import hashlib
from pathlib import Path

REPO=Path(__file__).resolve().parents[3]
ARTIFACT=REPO/'research/utgen-debug/vendor/UTGenDebug/utils.py'


def prompt_artifact():
    source=ARTIFACT.read_text()
    for node in ast.parse(source).body:
        if isinstance(node,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='joint_adv_prompt'for t in node.targets):
            text=ast.literal_eval(node.value)
            return text,hashlib.sha256(source.encode()).hexdigest()
    raise ValueError('author_prompt_not_found')


def adapt(request):
    text,sha=prompt_artifact()
    fn=next(n for n in ast.parse(request['source']).body if isinstance(n,ast.FunctionDef)and n.name==request['entry'])
    signature=request['entry']+'('+ast.unparse(fn.args)+')'
    original=text.format(signature=signature,description=request.get('spec',ast.get_docstring(fn)or ''),
                         code=request['source'],entry_point=request['entry'])
    marker='Respond in the format below:'
    if marker not in original:raise ValueError('author_prompt_format_marker_changed')
    prefix=original.split(marker,1)[0]
    adapted=prefix+'\nRespond as one JSON object {"hypothesis":"...", "error_pattern":"...", "tests":[{"arguments":"positional tuple literal", "expected":"literal"}], "reason":"..."}. Up to six tests. Preserve the hypothesis/pattern/valid-input/spec-output reasoning requirements above.'
    return {'prompt':adapted,'author_source_sha256':sha,
            'adaptation':'preserve original instructions through output-format marker; replace Markdown format with common JSON test schema and up-to-six cap',
            'known_bug_premise':'retained for frozen known-bug dev cohort only','trained_UTGen':False}
