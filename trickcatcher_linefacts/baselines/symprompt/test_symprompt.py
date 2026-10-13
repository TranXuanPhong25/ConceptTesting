"""Offline tests (no LLM, no network):
    python -B -m unittest trickcatcher_linefacts.baselines.symprompt.test_symprompt -v"""
import ast
import json
import tempfile
import textwrap
import unittest
from pathlib import Path

from . import pathcollect, prompts, run, tc
from .fake_client import FakeClient


def paths_of(src, name='f'):
    tree = ast.parse(textwrap.dedent(src))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    return [p.as_dict() for p in pathcollect.collect(fn)]


class PathCollection(unittest.TestCase):
    def test_figure5_three_sequential_branches_give_n_plus_one_paths(self):
        found = paths_of('''
            def f(a, b, c):
                if a:
                    x = 1
                else:
                    x = 2
                if b:
                    y = 1
                else:
                    y = 2
                if c:
                    z = 1
                else:
                    z = 2
                return x + y + z
        ''')
        self.assertEqual([p['constraints'] for p in found],
                         [['a', 'b', 'c'], ['not a', 'b', 'c'], ['a', 'not b', 'c'], ['a', 'b', 'not c']])
        self.assertTrue(all(p['end'] == 'return' and p['returns'] == 'x + y + z' for p in found))

    def test_figure2_return_chain_inverts_untaken_branches(self):
        found = paths_of('''
            def exists_as(path):
                path = normalize_path(path)
                if path.is_dir():
                    return 'directory'
                if path.is_file():
                    return 'file'
                return ''
        ''', 'exists_as')
        self.assertEqual([(p['constraints'], p['returns']) for p in found],
                         [(['path.is_dir()'], "'directory'"),
                          (['not path.is_dir()', 'path.is_file()'], "'file'"),
                          (['not path.is_dir()', 'not path.is_file()'], "''")])

    def test_loops_record_conditions_and_while_true_has_no_exit_constraint(self):
        found = paths_of('''
            def f(xs, n):
                for x in xs:
                    if x < 0:
                        return x
                while True:
                    if n > 3:
                        return n
                    n += 1
        ''')
        texts = [p['constraints'] for p in found]
        self.assertIn(['x in xs', 'x < 0'], texts)
        self.assertTrue(any('not xs' in t for t in texts))
        self.assertFalse(any('True' in c or 'not True' in c for t in texts for c in t))
        self.assertTrue(any(t[-1] == 'n > 3' for t in texts))

    def test_double_negation_is_simplified_and_elif_nests(self):
        found = paths_of('''
            def f(s):
                if not s:
                    return 0
                elif s[0] == 'a':
                    return 1
                else:
                    raise ValueError(s)
        ''')
        self.assertEqual(found[1]['constraints'], ['s', "s[0] == 'a'"])
        self.assertEqual(found[2]['end'], 'raise')
        self.assertIsNone(found[2]['returns'])

    def test_select_prefers_new_branches_then_preorder(self):
        found = pathcollect.collect(ast.parse(textwrap.dedent('''
            def f(a, b):
                if a:
                    return 1
                if a:
                    return 2
                return 3
        ''')).body[0])
        chosen = pathcollect.select(found, 2)
        self.assertEqual(len(chosen), 2)
        self.assertEqual(chosen[0].returns, '1')

    def test_vibepass_wrapper_resolves_to_class_method(self):
        src = textwrap.dedent('''
            from typing import List
            class Solution:
                def helper(self, x):
                    return x
                def solve(self, nums: List[int]) -> int:
                    if not nums:
                        return 0
                    return self.helper(len(nums))
            import copy
            def solve(nums: List[int]) -> int:
                "Spec text."
                return Solution().solve(*copy.deepcopy((nums,)))
        ''')
        fn, cls, wrapper, tree = pathcollect.focal(src, 'solve')
        self.assertEqual((cls.name, fn.name, wrapper.name), ('Solution', 'solve', 'solve'))
        ctx = prompts.context(src, fn, cls, wrapper, tree)
        self.assertIn('class Solution:', ctx)
        self.assertIn('def helper', ctx)            # called focal-class method (dependency context)
        self.assertIn('"Spec text."', ctx)          # the wrapper the tests call
        self.assertEqual(prompts.signature(wrapper), 'solve(nums: List[int]) -> int')


class Prompting(unittest.TestCase):
    def test_stub_has_signature_constraints_and_returns(self):
        stub = prompts.stub('f', 3, 'f(a: int) -> int', dict(constraints=['a > 0', 'not a % 2'], end='return', returns='a'))
        self.assertEqual(stub, 'def test_f_3():\n    """\n    Testcase 3 for f(a: int) -> int\n    where a > 0,\n'
                               '    not a % 2\n    returns: a\n    """\n')
        self.assertNotIn('returns', prompts.stub('f', 1, 'f()', dict(constraints=[], end='end', returns=None)))

    def test_context_is_selective(self):
        src = textwrap.dedent('''
            import math
            LIMIT = 3
            def used(x):
                return x
            def unused(x):
                return x
            def f(a):
                return used(a) + LIMIT
        ''')
        fn, cls, wrapper, tree = pathcollect.focal(src, 'f')
        ctx = prompts.context(src, fn, cls, wrapper, tree)
        self.assertIn('import math', ctx); self.assertIn('LIMIT = 3', ctx); self.assertIn('def used', ctx)
        self.assertNotIn('def unused', ctx)
        self.assertTrue(ctx.rstrip().endswith('return used(a) + LIMIT'))

    def test_parse_repair_deletes_trailing_lines(self):
        code, ok = prompts.parse_repair('def test_f():\n    x = 1\n    assert f(x) == 2\n    assert f(x) ==')
        self.assertTrue(ok)
        self.assertTrue(code.endswith('assert f(x) == 2'))


class Flatten(unittest.TestCase):
    PUT = 'from typing import List\ndef f(xs: List[int]) -> int:\n    return len(xs)\n'

    def test_substitution_rename_and_rejections(self):
        code = textwrap.dedent('''
            def test_a():
                xs = [1, 2]
                out = f(xs)
                assert out == 2
                assert candidate([]) == 0
                for i in range(3):
                    assert f([i]) == 1
                ys = [1]
                ys.append(2)
                assert f(ys) == 2
                assert len([1]) == 1
                self.assertEqual(f([3]), 1)
        ''')
        found, rejected = tc.flatten(code, 'f', self.PUT)
        self.assertEqual(found, ['assert f([1, 2]) == 2', 'assert f([]) == 0', 'assert f([3]) == 1'])
        reasons = ' '.join(r['reason'] for r in rejected)
        self.assertIn('i', reasons); self.assertIn('ys', reasons); self.assertIn('does not call f', reasons)

    def test_heldout_comparator_is_normalised_other_helpers_rejected(self):
        base = 'def _same(x, y, atol):\n    return x == y\n\ndef check(candidate):\n    assert _same(candidate([1]), 1, 0.0)\n'
        task = dict(entry='f', put=self.PUT, base=base)
        self.assertEqual(tc.base_assertions(task), {'assert f([1]) == 1'})
        code = 'def test_x():\n    assert _same(2, f([1, 2]), 0.0)\n    assert mine(f([]))\ndef mine(v):\n    return v\n'
        found, rejected = tc.flatten(code, 'f', self.PUT, helpers=tc.base_helpers(task))
        self.assertEqual(found, ['assert f([1, 2]) == 2'])
        self.assertIn('mine', rejected[0]['reason'])

    def test_base_assertions_and_round_robin(self):
        task = dict(entry='f', put=self.PUT, base='def check(candidate):\n    assert candidate([1]) == 1\n')
        self.assertEqual(tc.base_assertions(task), {'assert f([1]) == 1'})
        self.assertEqual(tc.round_robin([['a', 'b', 'c'], ['d'], ['a', 'e']], 4), ['a', 'd', 'b', 'e'])


class EndToEnd(unittest.TestCase):
    def test_fake_run_writes_v7_rows_and_resumes(self):
        task = dict(task=7, split='dev', entry='f', facts_version='v4',
                    put='def f(a: int) -> int:\n    """Return |a|."""\n    if a < 0:\n        return -a\n    return a\n',
                    base='def check(candidate):\n    assert candidate(1) == 1\n    assert candidate(-2) == 2\n')
        with tempfile.TemporaryDirectory() as d:
            bundle = Path(d) / 'bundle.json'
            bundle.write_text(json.dumps(dict(facts_version='v4', tasks=[task])))
            rows = run.main(['--tasks', str(bundle), '--out', str(Path(d) / 'o'), '--k', '2', '--fake', '--llm-budget', '6'])
            self.assertEqual(len(rows), 2)
            for r in rows:
                for key in ('task', 'arm', 'sample', 'split', 'text', 'assertions', 'llm_calls', 'n_in', 'n_out', 'run_id', 'calls'):
                    self.assertIn(key, r)
                self.assertEqual(r['arm'], 'symprompt')
                self.assertEqual(r['llm_calls'], 2)                    # two paths, one prompt each
                self.assertTrue(r['text'].startswith('```python\n'))
                self.assertTrue(all(a.startswith('assert f(') for a in r['assertions']))
            second = Path(d) / 'o' / 'artifacts' / '7' / '0' / '01_path2_prompt.json'
            prompt = json.loads(second.read_text())[1]['content']
            self.assertIn('def test_f_1():', prompt)                   # previous test included in the next prompt
            self.assertIn('Testcase 2 for f(a: int) -> int', prompt)
            again = run.main(['--tasks', str(bundle), '--out', str(Path(d) / 'o'), '--k', '2', '--fake', '--llm-budget', '6'])
            self.assertEqual([r['assertions'] for r in again], [r['assertions'] for r in rows])


if __name__ == '__main__':
    unittest.main()
