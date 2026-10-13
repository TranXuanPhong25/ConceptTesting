"""The three ACH prompts (paper Table 1), adapted from a Kotlin class + test class to a Python PUT + check().

Wording follows Table 1; only the language/unit nouns are changed (Kotlin class -> Python code/function,
method -> function, test class -> test function, `//` -> `#` markers). The concern is the function's
specification; there is no `{diff}` example of a previous fault in this setting, so 'similar to {diff}' is
dropped. A one-sentence output-format line is appended to the test prompt so that the extended test
function can be read as `assert candidate(...) == ...` lines (TrickCatcher row format).
"""
from __future__ import annotations

from .tc import SYSTEM

CONCERN = ('Faults that make the function `{entry}` violate its specification, i.e. the behaviour that the '
           'docstring of `{entry}` requires.')

MAKE_FAULT = ('CONTEXT: {concern} INSTRUCTION: Here is a Python function and a test function with some unit '
              'tests for the function under test\n```python\n{put}\n```.\n```python\n{base}\n```.\nWrite a new '
              'version of the code under test in which each function is replaced by a new version of that '
              'function that contains a typical bug that makes `{entry}` violate its specification. Delimit the '
              'mutated part using the comment-pair `# MUTANT <START>` and `# MUTANT <END>`')

EQUIVALENCE = ("I'm going to show you two slightly different versions of a Python function. Here is the first "
               'version of the Python function:\n```python\n{v1}\n```.\nHere is the second version of the Python '
               'function:\n```python\n{v2}\n```.\nINSTRUCTION: If the first version of the function will always do '
               'exactly the same thing as the second version of the function, just respond with `yes`. However, '
               'if the two versions of the function are not equivalent, respond with `no`, and give an explanation '
               'of how execution of the first version can produce a different behaviour to execution of the second '
               'version.')

MAKE_TEST = ('What follows is two versions of a Python function under test. An original correct function and a '
             'mutated version of that function that contains one mutant per function, each of which represents a '
             'bug. Each bug is delimited by the comment-pair `# MUTANT <START>` and `# MUTANT <END>`. The original '
             'function and its mutant are followed by a test function that contains unit tests for the original '
             'correct function under test. This is the original version of the function under test:\n```python\n'
             '{original}\n```.\nThis is the mutated version of the function under test:\n```python\n{mutated}\n```.\n'
             'Here is the existing test function:\n```python\n{base}\n```.\nWrite an extended version of the test '
             'function that contains extra test cases that will fail on the mutant version of the function, but '
             'would pass on the correct version.')

FORMAT = ('\nEach test case must be one assertion of the form `assert candidate(<arguments>) == <expected>`. '
          'Reply with a single ```python code block.')


def _msgs(user):
    return [dict(role='system', content=SYSTEM), dict(role='user', content=user)]


def make_fault(task):
    concern = CONCERN.format(entry=task['entry'])
    return _msgs(MAKE_FAULT.format(concern=concern, put=task['put'].strip(), base=task['base'].strip(), entry=task['entry']))


def equivalence(original, mutant):
    return _msgs(EQUIVALENCE.format(v1=original.strip(), v2=mutant.strip()))


def make_test(task, mutated):
    return _msgs(MAKE_TEST.format(original=task['put'].strip(), mutated=mutated.strip(), base=task['base'].strip()) + FORMAT)
