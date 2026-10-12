"""Input precondition prompts, adapted from RBCTest's observation/confirmation idea."""
import json

SYSTEM = "Read only the supplied Python signature and docstring. Do not infer requirements from an implementation."
OBSERVATION = """List every condition the specification places on the inputs: types, ranges, lengths, allowed characters or elements, and relations between parameters. Use one atomic condition per item. Include only what the docstring states or its examples necessarily imply. Add nothing for unrestricted inputs. Reply only with a JSON list: [{"id":"P1","condition":"..."}]. Use unique ids P1, P2, and so on."""
CONFIRMATION = """For each candidate, decide whether the specification states it or necessarily implies it from the meaning of its words (for example, a length, count or size cannot be negative; an index must lie within its sequence). Reject guesses and merely plausible restrictions. For each kept condition, quote the exact words of the signature or docstring it is based on; the quote does not have to state the condition itself. Reply only with a JSON list: [{"id":"P1","keep":true,"evidence":"exact words from the specification"}]. Include every candidate id once."""
CODE = """Write one Python predicate per kept condition, named by its id, with the supplied function's parameters and a bool return value. Reply only with Python function definitions. Use only builtins; no imports, decorators, global state, I/O, or parameter mutation. Each predicate must return True exactly when its condition holds. Guard types and operations so it never raises. Do not use try/except: raising checks are recorded as rejections. Do not add conditions."""


def messages(stage, spec, candidates=None):
    instruction = {"observation": OBSERVATION, "confirmation": CONFIRMATION, "code": CODE}[stage]
    body = instruction + "\n\nSPECIFICATION:\n" + spec
    if candidates is not None:
        body += "\n\nCONDITIONS:\n" + json.dumps(candidates, ensure_ascii=False)
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": body}]
