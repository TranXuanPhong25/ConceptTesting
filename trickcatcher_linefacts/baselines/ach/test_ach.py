"""Offline tests (no LLM, no network; the sandbox needs `unshare -rn`):
    python -B -m unittest trickcatcher_linefacts.baselines.ach.test_ach -v"""
import json
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from . import mutants, prompts, run
from .fake_client import FakeClient

PUT = 'def f(x: int) -> int:\n    """Return twice x."""\n    return x * 2\n'
BASE = 'def check(candidate):\n    assert candidate(2) == 4\n    assert candidate(0) == 0\n'
MUTANT_RESPONSE = textwrap.dedent('''\
    Here is the faulty version:
    ```python
    def f(x: int) -> int:
        """Return twice x."""
        # MUTANT <START>
        if x >= 10:
            return x * 3
        # MUTANT <END>
        return x * 2
    ```''')
TEST_RESPONSE = textwrap.dedent('''\
    ```python
    def check(candidate):
        assert candidate(2) == 4
        assert candidate(0) == 0
        assert candidate(20) == 40
        assert candidate(5) == 11
        assert candidate(30) == 91
        y = 12
        assert candidate(y) == 24
    ```''')


def scripted(answers):
    def script(messages, seed):
        user = messages[-1]['content']
        if user.startswith('CONTEXT:'):
            return answers['fault']
        if user.startswith("I'm going to show you"):
            return answers['equivalence']
        return answers['test']
    return script


class RuleBasedSteps(unittest.TestCase):
    def test_assemble_keeps_markers_and_helpers(self):
        response = 'import math\ndef helper(v):\n    return v\n\ndef f(x: int) -> int:\n    # MUTANT <START>\n    return helper(x) * 3\n    # MUTANT <END>\n'
        put = 'GLOBAL = 1\n\n' + PUT + '\nTAIL = 2\n'
        mutant = mutants.assemble(put, response, 'f')
        self.assertIn('# MUTANT <START>', mutant)
        self.assertLess(mutant.index('def helper'), mutant.index('def f'))
        self.assertTrue(mutant.startswith('import math'))
        self.assertIn('TAIL = 2', mutant); self.assertIn('GLOBAL = 1', mutant)
        with self.assertRaises(ValueError):
            mutants.assemble(PUT, 'x = 1\n', 'f')
        with self.assertRaises(SyntaxError):
            mutants.assemble(PUT, 'def f(:\n', 'f')

    def test_comment_only_mutant_is_syntactically_identical(self):
        commented = PUT.replace('    return x * 2', '    # MUTANT <START>\n    # Introduce a bug by not doubling\n    return x * 2  # bug\n    # MUTANT <END>')
        self.assertEqual(mutants.normal_form(mutants.strip_comments(commented)), mutants.normal_form(PUT))
        self.assertNotIn('#', mutants.strip_comments(commented))

    def test_judge(self):
        self.assertEqual(mutants.judge('Yes'), 'equivalent')
        self.assertEqual(mutants.judge('`no`, because x=10 differs'), 'non-equivalent')
        self.assertEqual(mutants.judge('**No**.'), 'non-equivalent')
        self.assertEqual(mutants.judge('It depends.'), 'unsure')
        self.assertEqual(mutants.judge('Nothing changes'), 'unsure')

    def test_prompts_follow_table1(self):
        task = dict(task=1, entry='f', put=PUT, base=BASE)
        fault = prompts.make_fault(task)[1]['content']
        self.assertTrue(fault.startswith('CONTEXT: Faults that make the function `f` violate its specification'))
        self.assertIn('Delimit the mutated part using the comment-pair `# MUTANT <START>` and `# MUTANT <END>`', fault)
        test = prompts.make_test(task, 'MUTANT CODE')[1]['content']
        self.assertIn('will fail on the mutant version of the function, but would pass on the correct version.', test)
        self.assertIn("respond with `yes`", prompts.equivalence('a', 'b')[1]['content'])

    def test_keep_modes(self):
        killed_pass = dict(put_outcomes=['pass'] * 5, put_calls_ok=True, mutant_outcome='fail', outputs_differ=True)
        killed_fail = dict(put_outcomes=['fail'] * 5, put_calls_ok=True, mutant_outcome='fail', outputs_differ=True)
        crash = dict(put_outcomes=['error:TypeError'], put_calls_ok=False, mutant_outcome='fail', outputs_differ=True)
        flaky = dict(put_outcomes=['pass', 'fail'], put_calls_ok=True, mutant_outcome='fail', outputs_differ=True)
        self.assertTrue(run.keep(killed_pass, 'paper') and run.keep(killed_pass, 'run'))
        self.assertTrue(run.keep(killed_fail, 'run')); self.assertFalse(run.keep(killed_fail, 'paper'))
        self.assertFalse(run.keep(crash, 'run') or run.keep(crash, 'paper'))
        self.assertFalse(run.keep(flaky, 'run') or run.keep(flaky, 'paper'))


class Sandbox(unittest.TestCase):
    def test_mutant_and_test_checks(self):
        mutant = mutants.assemble(PUT, MUTANT_RESPONSE.split('```python\n')[1].split('```')[0], 'f')
        with tempfile.TemporaryDirectory() as d:
            built, err = run.sandbox(dict(mode='mutant', entry='f', put=PUT, mutant=mutant, base=BASE, timeout=5),
                                     Path(d) / 'b', sys.executable, 60)
            self.assertIsNone(err)
            self.assertEqual(built['mutant'], dict(builds=True, passes=True, error=None))
            asserts = ['assert f(20) == 40', 'assert f(5) == 11', 'assert f(3) == 6', 'assert f(None) == 0',
                       'assert f(10 ** 1) == 20']
            checked, err = run.sandbox(dict(mode='tests', entry='f', put=PUT, mutant=mutant, assertions=asserts,
                                            repeats=3, timeout=5), Path(d) / 't', sys.executable, 60)
            self.assertIsNone(err)
            by = {c['source']: c for c in checked}
            self.assertEqual(by['assert f(20) == 40']['put_outcomes'], ['pass'] * 3)
            self.assertEqual(by['assert f(20) == 40']['mutant_outcome'], 'fail')
            self.assertTrue(by['assert f(20) == 40']['outputs_differ'])
            self.assertFalse(by['assert f(5) == 11']['outputs_differ'])
            self.assertFalse(by['assert f(3) == 6']['outputs_differ'])
            self.assertEqual(by['assert f(None) == 0']['put_outcomes'][0], 'error:TypeError')
            self.assertTrue(by['assert f(10 ** 1) == 20']['outputs_differ'])

    def test_sandbox_has_no_network_and_no_credentials(self):
        probe = ('import os, socket\nassert "QWEN_BASE_URL" not in os.environ and "QWEN_API_KEY" not in os.environ\n'
                 'try:\n    socket.create_connection(("1.1.1.1", 53), timeout=2)\n    NET = True\n'
                 'except OSError:\n    NET = False\nassert not NET\n' + PUT)
        with tempfile.TemporaryDirectory() as d:
            built, err = run.sandbox(dict(mode='mutant', entry='f', put=probe, mutant=probe, base=BASE, timeout=5),
                                     Path(d), sys.executable, 60)
            self.assertIsNone(err)
            self.assertTrue(built['put']['builds'], built)


class EndToEnd(unittest.TestCase):
    def run_ach(self, d, answers, *extra):
        task = dict(task=5, split='dev', entry='f', put=PUT, base=BASE, facts_version='v4')
        bundle = Path(d) / 'bundle.json'
        bundle.write_text(json.dumps(dict(facts_version='v4', tasks=[task])))
        import trickcatcher_linefacts.baselines.ach.fake_client as fc
        original = fc.default_script
        fc.default_script = scripted(answers)
        try:
            return run.main(['--tasks', str(bundle), '--out', str(Path(d) / 'o'), '--k', '1', '--fake', *extra])
        finally:
            fc.default_script = original

    def test_full_cycle_run_filter(self):
        with tempfile.TemporaryDirectory() as d:
            [r] = self.run_ach(d, dict(fault=MUTANT_RESPONSE, equivalence='no, x >= 10 differs', test=TEST_RESPONSE))
            self.assertEqual(r['arm'], 'ach')
            self.assertEqual(r['mutant_statuses'], ['killed', 'duplicate'])
            self.assertEqual(r['llm_calls'], 4)          # cycle (3) + second fault; then fewer than 3 calls remain
            self.assertEqual(r['assertions'], ['assert f(20) == 40', 'assert f(30) == 91', 'assert f(12) == 24'])
            self.assertEqual(r['mutant_attempts'][0]['base_copies'], 2)

    def test_paper_filter_requires_pass_on_put(self):
        with tempfile.TemporaryDirectory() as d:
            [r] = self.run_ach(d, dict(fault=MUTANT_RESPONSE, equivalence='No.', test=TEST_RESPONSE), '--filter', 'paper')
            self.assertEqual(r['assertions'], ['assert f(20) == 40', 'assert f(12) == 24'])

    def test_equivalent_and_identical_mutants_get_no_tests(self):
        with tempfile.TemporaryDirectory() as d:
            [r] = self.run_ach(d, dict(fault=MUTANT_RESPONSE, equivalence='yes', test=TEST_RESPONSE), '--mutants', '2')
            self.assertEqual(r['mutant_statuses'], ['equivalent', 'duplicate'])
            self.assertEqual(r['assertions'], [])
        identical = '```python\n' + PUT.replace('    return', '    # MUTANT <START>\n    return') + '    # MUTANT <END>\n```'
        with tempfile.TemporaryDirectory() as d:
            [r] = self.run_ach(d, dict(fault=identical, equivalence='no', test=TEST_RESPONSE), '--mutants', '1')
            self.assertEqual(r['mutant_statuses'], ['syntactically-identical'])
            self.assertEqual(r['llm_calls'], 1)

    def test_default_fake_script(self):
        with tempfile.TemporaryDirectory() as d:
            task = dict(task=9, split='dev', entry='f', put='def f(a, b):\n    if a < b:\n        return b - a\n    return a - b\n',
                        base='def check(candidate):\n    assert candidate(1, 3) == 2\n    assert candidate(5, 5) == 0\n')
            bundle = Path(d) / 'bundle.json'
            bundle.write_text(json.dumps(dict(tasks=[task])))
            rows = run.main(['--tasks', str(bundle), '--out', str(Path(d) / 'o'), '--k', '2', '--fake'])
            self.assertEqual(len(rows), 2)
            self.assertTrue(all(r['llm_calls'] <= 6 for r in rows))


if __name__ == '__main__':
    unittest.main()
