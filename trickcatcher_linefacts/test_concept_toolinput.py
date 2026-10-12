"""Offline regression checks; all responses are canned, workers stay isolated."""
import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from trickcatcher_linefacts import evaluate, gen_evaluation, gen_inputs, gen_prompts, prompts, run_gen

HERE = Path(__file__).resolve().parent


class Canned:
    model = 'canned'

    def __init__(self):
        self.requests = []

    def chat(self, messages, seed):
        self.requests.append((copy.deepcopy(messages), seed))
        is_two = 'def truncate_number(' in messages[1]['content']
        if messages[0]['content'] != prompts.SYSTEM:
            text = 'def sample_one():\n    return ' + ('[1.0]' if is_two else '[[]]')
        else:
            lines = (['assert truncate_number(1.0) == 0.0', 'assert truncate_number(3.5) == 0.0']
                     if is_two else ['assert sum_product([]) == (0, 1)'])
            text = '```python\n' + '\n'.join((lines * 11)[:11]) + '\n```'
        return dict(text=text, key=str(seed), params=dict(seed=seed), n_in=10, n_out=20,
                    seconds=0.0, cache_hit=False, transport_attempts=1)


class CombinedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        bundle = json.loads((HERE/'out/tasks_v3m2_all.json').read_text())
        cls.tasks = [t for t in bundle['tasks'] if t['task'] in (2, 8)]
        cls.task = next(t for t in cls.tasks if t['task'] == 2)

    def test_frozen_seeds(self):
        self.assertEqual(gen_prompts.ARMS[:-1], gen_prompts.DEFAULT_ARMS)
        old, added = set(), set()
        for n in range(164):
            for sample in range(3):
                for stage in range(4):
                    for retry in range(2):
                        for i, arm in enumerate(gen_prompts.DEFAULT_ARMS):
                            expected = 20261010 + (((n*6+i)*1000+sample)*8+stage*2+retry)
                            self.assertEqual(gen_prompts.seed(n, arm, sample, stage, retry), expected)
                            old.add(expected)
                        added.add(gen_prompts.seed(n, 'concept-toolinput', sample, stage, retry))
        self.assertFalse(old & added)
        self.assertEqual(len(added), 164*3*4*2)
        with self.assertRaises(ValueError):
            gen_prompts.generator_messages('concept-toolinput', self.task)

    def test_witness_mapping(self):
        task = copy.deepcopy(self.task)
        selected = [dict(input_repr='[1.0]', call='truncate_number(1.0)')]
        text = gen_prompts.concept_toolinput_messages(task, selected)[1]['content']
        self.assertEqual(text.count('An input that reaches this:'), 2)
        self.assertNotIn('`truncate_number(123.0)`', text)
        for fact in task['concept_facts']:
            self.assertIn('- '+fact+'\n', text)
        self.assertIn(prompts.FACTS_HEAD, text)
        self.assertIn(prompts.FACTS_TAIL+prompts.TOOLINPUT_TAIL, text)
        del task['concept_meta'][0]['witness_call']
        self.assertEqual(gen_prompts.concept_toolinput_messages(task, selected)[1]['content'].count(
            'An input that reaches this:'), 1)
        empty = dict(task, concept_facts=[], concept_meta=[])
        self.assertEqual(gen_prompts.concept_toolinput_messages(empty, []),
                         gen_prompts.messages(*prompts.build('plain', empty)))

    def test_filtered_frozen_order(self):
        task = dict(self.task, tool_inputs=['truncate_number(-1.0)', 'truncate_number(123.0)',
                                          'truncate_number(1.0)', 'truncate_number(1.0)',
                                          'truncate_number(2.0)', 'truncate_number(3.0)',
                                          'truncate_number('+repr('x'*1001)+')'])
        with tempfile.TemporaryDirectory() as directory:
            result = gen_inputs.classify(task, dict(mined_src=task['mined_valid_src']),
                                         gen_inputs.witness_candidates(task), [], directory)
        self.assertNotIn('classification_error', result['summary'])
        self.assertEqual(result['summary']['removed'], 2)
        self.assertEqual(result['summary']['oversize'], 1)
        selected = gen_inputs.select('toolinput', result, 123)
        self.assertEqual([r['call'] for r in selected],
                         ['truncate_number(123.0)', 'truncate_number(1.0)', 'truncate_number(2.0)'])

    def test_run_evaluate_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            client = Canned()
            contracts = {t['task']: dict(mined_src=t['mined_valid_src']) for t in self.tasks}
            with contextlib.redirect_stdout(io.StringIO()):
                run_gen.run(self.tasks, contracts, root/'combined', None, k=3, workers=1, client=client,
                            facts_version='v3m', arms=('concept-toolinput',))
            self.assertEqual(len(client.requests), 6)
            combined = root/'combined'
            rows = [json.loads(line) for line in (combined/'gen.jsonl').read_text().splitlines()]
            self.assertTrue(all(r['llm_calls'] == 1 and not r['generator_attempts'] for r in rows))
            self.assertEqual(json.loads((combined/'manifest.json').read_text())['arms'], ['concept-toolinput'])
            for row, (messages, seed) in zip(rows, client.requests):
                task = next(t for t in self.tasks if t['task'] == row['task'])
                self.assertEqual(seed, gen_prompts.seed(row['task'], row['arm'], row['sample']))
                if not task['concept_facts']:
                    self.assertEqual(messages, gen_prompts.messages(*prompts.build('plain', task)))
            with contextlib.redirect_stdout(io.StringIO()):
                run_gen.run(self.tasks, contracts, combined, None, k=3, workers=1, client=client,
                            facts_version='v3m', arms=('concept-toolinput',))
            self.assertEqual(len(client.requests), 6)
            evaluate.evaluate(combined/'tasks.json', combined/'gen.jsonl', combined/'eval.jsonl')
            scored = [json.loads(line) for line in (combined/'eval.jsonl').read_text().splitlines()]
            self.assertTrue(all(len(r['asserts']) == 10 for r in scored))
            two = next(r for r in scored if r['task'] == 2)
            self.assertEqual((two['asserts'][0]['canon'], two['asserts'][0]['put']), ('ok', 'fail'))
            self.assertEqual(two['asserts'][1]['canon'], 'fail')
            with contextlib.redirect_stdout(io.StringIO()) as output:
                evaluate.report(combined/'tasks.json', combined/'eval.jsonl')
            self.assertIn('concept-toolinput', output.getvalue())
            self.assertNotIn(' vs ', output.getvalue())
            with contextlib.redirect_stdout(io.StringIO()):
                run_gen.run(self.tasks, contracts, root/'default', HERE.parent/'.venv/bin/python',
                            k=3, workers=1, client=Canned(), facts_version='v3m')
            default = root/'default'
            self.assertEqual(json.loads((default/'manifest.json').read_text())['arms'], list(gen_prompts.DEFAULT_ARMS))
            evaluate.evaluate(default/'tasks.json', default/'gen.jsonl', default/'eval.jsonl')
            with contextlib.redirect_stdout(io.StringIO()) as output:
                evaluate.report(combined/'tasks.json', combined/'eval.jsonl', [default/'eval.jsonl'])
            text = output.getvalue()
            for arm in ('toolinput', 'concept', 'plain'):
                self.assertIn('concept-toolinput vs '+arm+':', text)
            self.assertLess(text.index('concept-toolinput vs toolinput:'), text.index('concept-toolinput vs concept:'))
            with self.assertRaises(ValueError):
                gen_evaluation.report(combined/'tasks.json', combined/'eval.jsonl', [combined/'eval.jsonl'])
            (combined/'eval.jsonl').write_text('\n'.join(json.dumps(r) for r in scored[:-1])+'\n')
            with self.assertRaises(ValueError):
                gen_evaluation.report(combined/'tasks.json', combined/'eval.jsonl')

    def test_frozen_bundle_cli(self):
        argv = ['run_gen.py', '--from-bundle', '--tasks', str(HERE/'out/tasks_v3m2_all.json'),
                '--arms', 'concept-toolinput', '--out-dir', '/tmp/unused-ct', '--k', '3']
        with patch('sys.argv', argv), patch.object(run_gen, 'run') as run, \
                patch.object(run_gen, 'run_mined', side_effect=AssertionError('must not rebuild facts')):
            run_gen.main()
        args, kwargs = run.call_args
        self.assertEqual(len(args[0]), 133)
        self.assertTrue(all('mined_src' in c and 'contract_src' not in c for c in args[1].values()))
        self.assertEqual(kwargs['arms'], ['concept-toolinput'])
        self.assertEqual(kwargs['k'], 3)


if __name__ == '__main__':
    unittest.main()
