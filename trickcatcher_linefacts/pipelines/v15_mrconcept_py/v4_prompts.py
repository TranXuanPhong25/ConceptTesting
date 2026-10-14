"""Registered v4 prompts; the existing o0 oracle and paper templates are unchanged."""

# Direct-script workers run with -I: establish this copy's package explicitly.
import sys as _package_sys
from pathlib import Path as _PackagePath
if not __package__:
    _package_here = _PackagePath(__file__).resolve().parent
    _package_sys.path.insert(0, str(_package_here.parents[2]))
    __package__ = "trickcatcher_linefacts.pipelines." + _package_here.name
from .paths import REPO as _REPO, DATA_OUT, CONFIG, dataset_paths
import json
from . import gen_prompts, preconditions

LEGACY_ARMS = ('plain', 'concept', 'toolinput', 'gen-plain', 'concept-hybrid', 'placebo-hybrid', 'plain-hybrid')
NEW_ARMS = ('review-hybrid', 'flat-hybrid', 'rel-hybrid', 'rel-nospec-hybrid')
ARMS = LEGACY_ARMS + NEW_ARMS + ('witness-only', 'hyp-hybrid', 'hyp-witness-only')
SYSTEM = 'Write a Python Hypothesis input strategy from the supplied specification.'
DOMAIN = '''Write def strategy(): returning a hypothesis.strategies strategy whose draws are positional argument tuples for the supplied function. Describe the input domain in the specification. The surviving mined conditions below are domain information; the harness applies the validator mechanically. Use only hypothesis.strategies (available as st), pure builtins and pure string methods. No other imports, I/O, global state, decorators, mutation, or execution of the function. You may use local variables, lambdas, st.map/filter/flatmap and st.builds. Every draw must have the correct arity and be literal-roundtrippable. Reply with Python code only.'''
TARGET = '''Write def strategy(): returning a Hypothesis strategy of positional argument tuples that exercise the fact below. Use the supplied domain strategy as a starting point. Use only hypothesis.strategies (available as st), pure builtins and pure string methods; no other imports, I/O, global state, decorators, mutation, or execution of the function. Reply with Python code only.'''
CONTROL = '''Write def strategy(): returning a Hypothesis strategy for inputs that the existing tests do not exercise. Use the supplied domain strategy as a starting point. Return positional argument tuples. Use only hypothesis.strategies (available as st), pure builtins and pure string methods; no other imports, I/O, global state, decorators, mutation, or execution of the function. Reply with Python code only.'''
RETRY = 'The strategy failed verification: {error}\nWrite a corrected def strategy(). Reply with Python code only.'


def domain_messages(task, conditions):
    spec = preconditions.specification(task)[0]
    return gen_prompts.messages(SYSTEM, DOMAIN + '\n\nSPECIFICATION:\n' + spec +
                               '\n\nSURVIVING CONDITIONS:\n' + json.dumps(conditions, ensure_ascii=False))


def hybrid_messages(task, fact=None, assertions=()):
    body = TARGET if fact is not None else CONTROL
    body += '\n\nSPECIFICATION:\n' + preconditions.specification(task)[0]
    body += '\n\nPUT:\n' + task['put'] + '\n\nEXISTING TESTS:\n' + task['base']
    body += '\n\nROUND-1 ASSERTIONS:\n' + '\n'.join(assertions)
    body += '\n\nDOMAIN STRATEGY:\n' + task['strategy_src']
    if fact is not None:
        body += '\n\nFACT:\n' + fact['text']
    return gen_prompts.messages(SYSTEM, body)


def seed(task, arm, sample, stage=0, request=0, retry=0):
    if arm in ('hyp-hybrid','hyp-witness-only'):
        return CONFIG['seeds']['arms'] + ((400000 + int(task)*2 + ('hyp-hybrid','hyp-witness-only').index(arm))*1000+sample)*128 + stage*32+request*2+retry
    if arm == 'flat-hybrid': arm = 'concept-hybrid'
    if arm not in LEGACY_ARMS:
        return CONFIG['seeds']['arms'] + ((200000 + int(task)*len(NEW_ARMS) + NEW_ARMS.index(arm))*1000+sample)*128 + stage*32+request*2+retry
    # Round one is shared by referring to the plain/concept seed, never the hybrid index.
    return CONFIG["seeds"]["arms"] + (((int(task)*len(LEGACY_ARMS)+LEGACY_ARMS.index(arm))*1000+sample)*128 + stage*32+request*2+retry)
