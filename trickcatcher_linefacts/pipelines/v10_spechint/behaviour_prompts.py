"""Frozen specification-only RBCTest-style behavioural mining prompts."""
import json

SYSTEM = 'Read only the supplied Python signature and docstring. Do not infer requirements from an implementation.'
OBSERVATION = '''List atomic behavioural requirements relating the output to the input, such as sorting, case insensitivity, tie breaking, or retaining duplicates. Include only requirements explicitly stated in the specification. For each give a short statement and a nonempty verbatim quote from the supplied specification. Do not list input preconditions. Reply only with a JSON list: [{"id":"B1","statement":"...","quote":"exact words"}]. Use unique ids B1, B2, and so on.'''
CONFIRMATION = '''For each candidate decide whether its quoted words explicitly support the stated output behaviour. Reject guesses and input preconditions. Preserve the candidate id and its verbatim quote exactly. Reply only with a JSON list: [{"id":"B1","keep":true,"quote":"exact words"}]. Include every candidate id once.'''
CODE = '''For each kept requirement write def D(<specification parameters>) -> bool, true exactly for inputs where this requirement matters: an implementation ignoring it could return a different answer. D is NOT an input-validity predicate. Optionally write def R(<specification parameters>, *, out) -> bool checking the requirement on the output. R must hold on every valid input/output pair, including inputs outside D. Use only pure builtins; no imports, decorators, global state, I/O, try/except, or parameter mutation. Guard types and operations. Reply only with a JSON list: [{"id":"B1","D":"def D(xs):\\n    return ...\\n","R":"def R(xs, *, out):\\n    return ...\\n"}]. Omit R or set it to null when unavailable. Do not add requirements.'''


def messages(stage, spec, requirements=None):
    body = {'observation': OBSERVATION, 'confirmation': CONFIRMATION, 'code': CODE}[stage]
    body += '\n\nSPECIFICATION:\n' + spec
    if requirements is not None:
        body += '\n\nREQUIREMENTS:\n' + json.dumps(requirements, ensure_ascii=False)
    return [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': body}]
