"""Small offline fixtures: python -B -m unittest trickcatcher_linefacts.pipelines.v11_fair_vp.test_final_analysis -v."""
import copy
import json
from pathlib import Path
import random
import sys
import tempfile
import unittest

from . import final_analysis as fp


def record(valid=True, di=True, emit=True, cok=True, pok=False):
    return dict(valid=valid, d_i=di, ref=dict(emit=emit, canon_ok=cok, put_ok=pok, post_ok=True))


class FinalProtocolTests(unittest.TestCase):
    def test_failing_denominator_and_flags_are_distinct(self):
        tasks = {0: dict(entry='f')}
        calls = {'f(0)': record(),                     # true report
                 'f(1)': record(valid=False, di=False), # invalid failing report
                 'f(2)': record(cok=False, di=False),   # wrong expected, failing
                 'f(3)': record(cok=False, pok=True),   # wrong expected, PUT passes
                 'f(4)': record(emit=False)}            # abstention, D_I retained
        rows = [dict(task=0, sample=0, asserts=[dict(src=f'assert f({i}) == 7') for i in range(5)]
                     + [dict(src='assert f(0) == 8')], llm_calls=2, n_in=10, n_out=20)]
        samples = fp.score_samples(tasks, rows, {'0': dict(calls=calls)}, {}, 'ref')
        m = fp.summarize(samples, 1)
        self.assertEqual((m['D_I'], m['D_IO']), (3, 1))
        self.assertEqual((m['failing'], m['correct_failing'], m['false_alarms']), (3, 1, 2))
        self.assertAlmostEqual(m['precision'], 1/3)
        self.assertAlmostEqual(m['false_alarm_rate'], 2/3)
        self.assertEqual(m['percent_samples_flagging_correct'], 100)
        self.assertEqual(m['emitted_false_alarms_per_sample'], 3)
        self.assertEqual(m['assertions_per_sample'], 4)  # dedup + abstention
        self.assertEqual(m['generated_assertions_per_sample'], 6)
        self.assertEqual(m['tokens_per_sample'], 30)

    def test_undefined_rates_and_missing_costs(self):
        row = dict(task=0, sample=0, asserts=[])
        m = fp.summarize(fp.score_samples({0: dict(entry='f')}, [row], {}, {}, 'ref'), 1)
        self.assertIsNone(m['precision'])
        self.assertIsNone(m['false_alarm_rate'])
        self.assertIsNone(m['llm_calls_per_sample'])
        self.assertEqual(m['bug_per_run'], 0)

    def test_missing_execution_is_not_silently_zero(self):
        with self.assertRaisesRegex(ValueError, 'Missing oracle'):
            fp.score_samples({0: dict(entry='f')}, [dict(task=0, sample=0, asserts=[dict(src='assert f(0)==0')])], {}, {}, 'ref')

    def test_question_clustering_and_complete_pairing(self):
        a = {(0, 0): dict(detecting=True), (1, 0): dict(detecting=True),
             (2, 0): dict(detecting=False)}
        b = {(0, 0): dict(detecting=False), (1, 0): dict(detecting=False),
             (2, 0): dict(detecting=True)}
        task = fp.compare(a, b, {i: str(i) for i in range(3)}, 1, 'ref', ('a', 'b'))
        question = fp.compare(a, b, {0: 'qA', 1: 'qA', 2: 'qB'}, 1, 'ref', ('a', 'b'))
        self.assertEqual((task['wins'], task['losses']), (2, 1))
        self.assertEqual((question['wins'], question['losses'], question['ties']), (1, 1, 0))
        self.assertEqual(question['per_cluster']['qA'], [2, 0])
        # Only task 0 has both K=2 samples; task 1 is excluded entirely.
        aa = {(0, 0): dict(detecting=True), (0, 1): dict(detecting=False), (1, 0): dict(detecting=True)}
        bb = copy.deepcopy(aa)
        bb[0, 0]['detecting'] = False
        c = fp.compare(aa, bb, {0: 'qA', 1: 'qA'}, 2, 'ref', ('a', 'b'))
        self.assertEqual((c['tasks'], c['excluded_tasks'], c['a_bug_per_run']), (1, 1, 0.5))

    def test_sign_test(self):
        self.assertEqual(fp.sign_test(0, 0), 1)
        self.assertEqual(fp.sign_test(5, 0), 0.0625)
        self.assertEqual(fp.sign_test(0, 5), fp.sign_test(5, 0))
        self.assertEqual(fp.sign_test(3, 3), 1)

    def test_random_subsets_deterministic_and_not_prefix(self):
        scores = [dict(detecting=False)]*3 + [dict(detecting=True)]
        value = fp.cut(scores, 1, random.Random(fp.SEED))
        self.assertEqual(value, fp.cut(scores, 1, random.Random(fp.SEED)))
        self.assertGreater(value, 0)
        self.assertLess(value, 1)
        self.assertEqual(fp.cut(scores, 0, random.Random(0)), 0)
        self.assertEqual(fp.cut(scores, 4, random.Random(0)), 1)
        a = {(0, 0): dict(scores=scores)}
        b = {(0, 0): dict(scores=[dict(detecting=False)])}
        first = fp.compare(a, b, {0: 'q'}, 1, 'ref', ('a', 'b'), matched=True)
        self.assertEqual(first, fp.compare(a, b, {0: 'q'}, 1, 'ref', ('a', 'b'), matched=True))
        self.assertEqual(first['matched_calls_per_sample'], 1)

    @staticmethod
    def fixture(root):
        run, oracle = root/'run', root/'oracle'
        run.mkdir(); (oracle/'exec').mkdir(parents=True)
        task = dict(task=0, split='heldout', entry='f', put='def f(x):\n    return x + 1\n',
                    base='def check(candidate):\n    assert candidate(0) == 0\n',
                    tool_inputs=['f(2)', 'f( 2 )'])
        (run/'tasks.json').write_text(json.dumps(dict(tasks=[task])))
        rows = [dict(task=0, split='heldout', sample=s, arm=a,
                     asserts=[dict(src='assert f(0) == 99')], llm_calls=1, n_in=11, n_out=12)
                for a in fp.ARMS for s in range(2)]
        (run/'eval.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
        job = dict(entry='f', put=task['put'], base=task['base'], spec='def f(x):\n    """Identity."""\n',
                   canon='def f(x):\n    return x\n', contract='def f(x):\n    assert x >= 0\n',
                   ref=['def f(x):\n    return x\n']*3, post=[], mutants=[], calls=['f(0)'],
                   dpp=[], tc=[], b1={}, o0={}, atol=0, shared_scorer=True)
        (oracle/'exec/0.job.json').write_text(json.dumps(job))
        # Deliberately stale record with no hash seed. Must replay, even though
        # it carries the shared_scorer flag.
        (oracle/'exec/0.json').write_text(json.dumps(dict(calls={'f(0)': record(di=False, pok=True)})))
        (oracle/'ref_responses.json').write_text(json.dumps([dict(task='0', sample=s, text=job['ref'][s]) for s in range(3)]))
        (root/'manifest.json').write_text(json.dumps(dict(puts=[dict(task=0, question_id='identity')])))
        data = root/'he'; data.mkdir()
        (data/'humaneval_mbpp_plus.jsonl').write_text(json.dumps(dict(task_id='HumanEval/0', atol=0))+'\n')
        baseline = root/'baseline'; baseline.mkdir()
        (baseline/'eval.jsonl').write_text(''.join(json.dumps(dict(rows[s], arm='adapter'))+'\n' for s in range(2)))
        (baseline/'oracle/exec').mkdir(parents=True)
        (baseline/'oracle/exec/0.job.json').write_text(json.dumps(job))
        return run, oracle, baseline

    def test_end_to_end_ref_only_baseline_and_read_only_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run, oracle, baseline = self.fixture(root)
            before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            result = fp.analyze(run, oracle, [baseline, root/'absent'], 'fixture', root/'report.md',
                                clusters='question', dataset_root=root, workers=1)
            self.assertEqual(list(result['oracles']), ['ref'])
            self.assertEqual(result['cluster_unit'], 'question')
            m = result['oracles']['ref']['arms']
            self.assertEqual((m['witness-only']['bug_per_run'], m['concept-hybrid']['bug_per_run']), (1, 1))
            self.assertEqual(m['witness-only']['llm_calls_per_sample'], 0)
            self.assertEqual(m['witness-only']['distinct_calls_per_sample'], 1)
            self.assertEqual(m['baseline']['precision'], 1)
            self.assertEqual(len(result['oracles']['ref']['primary']), 4)
            self.assertEqual(result['skipped_baselines'][0]['baseline'], 'absent')
            for name, content in before.items():
                self.assertEqual((root/name).read_bytes(), content)
            self.assertEqual({str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}-set(before),
                             {'report.md', 'report.json'})
            first = (root/'report.json').read_bytes()
            fp.analyze(run, oracle, [baseline, root/'absent'], 'fixture', root/'report.md',
                       clusters='question', dataset_root=root, workers=1)
            self.assertEqual(first, (root/'report.json').read_bytes())
            both = copy.deepcopy(result)
            both['oracles']['full'] = copy.deepcopy(both['oracles']['ref'])
            self.assertEqual(fp.markdown(both),
                             fp.markdown(json.loads(json.dumps(both, sort_keys=True))))

    def test_worker_uses_tolerant_scorer_for_all_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run, oracle, _ = self.fixture(root)
            job = fp.read_json(oracle/'exec/0.job.json')
            job.update(put='def f(x):\n    return [0.0]\n', canon='def f(x):\n    return [0.0005]\n',
                       ref=['def f(x):\n    return [0.0005]\n',
                            'def f(x):\n    return [0.0006]\n',
                            'def f(x):\n    return [0.0007]\n'],
                       base='def check(candidate):\n    assert candidate(0) == [0.0]\n', atol=0.001)
            (oracle/'exec/0.job.json').write_text(json.dumps(job))
            tasks = {0: dict(entry='f', put=job['put'])}
            rows = [dict(task=0, sample=0, asserts=[dict(src='assert f(0) == [0.0]')])]
            ex = fp.execute_records(tasks, rows, oracle, {}, {0: 0.001}, root/'temp', workers=1)
            rec = ex['0']['calls']['f(0)']
            self.assertFalse(rec['d_i'])
            self.assertTrue(rec['ref']['emit'])  # tolerant unanimity + base tests
            self.assertTrue(rec['ref']['canon_ok'])
            self.assertTrue(rec['ref']['put_ok'])

    def test_question_metadata_must_not_fall_back_to_task(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run, oracle, _ = self.fixture(root)
            (root/'manifest.json').unlink()
            with self.assertRaisesRegex(ValueError, 'Missing question_id'):
                fp.analyze(run, oracle, [], 'fixture', root/'report.md',
                           clusters='question', dataset_root=root)
            self.assertFalse((root/'report.md').exists())

    def test_baseline_must_share_reference_program_pool(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run, oracle, baseline = self.fixture(root)
            job_path = baseline/'oracle/exec/0.job.json'
            job = fp.read_json(job_path)
            job['ref'] = ['def f(x):\n    return 99\n']*3
            job_path.write_text(json.dumps(job))
            with self.assertRaisesRegex(ValueError, 'ref program pool differs'):
                fp.analyze(run, oracle, [baseline], 'fixture', root/'report.md', dataset_root=root)
            self.assertFalse((root/'report.md').exists())

    def test_manifest_k_rejects_incomplete_run_and_output_cannot_touch_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run, oracle, _ = self.fixture(root)
            with self.assertRaisesRegex(ValueError, 'outside all input'):
                fp.analyze(run, oracle, [], 'fixture', oracle/'report.md', dataset_root=root)
            (run/'manifest.json').write_text(json.dumps(dict(k=3)))
            with self.assertRaisesRegex(ValueError, 'complete task'):
                fp.analyze(run, oracle, [], 'fixture', root/'report.md', dataset_root=root)
            self.assertFalse((root/'report.md').exists())

    def test_replay_pins_python_hash_seed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, oracle, _ = self.fixture(root)
            job = fp.read_json(oracle/'exec/0.job.json')
            canonical = "def f(x):\n    return ['a','b','c'] if x == 0 else ['apple','banana']\n"
            job.update(put="def f(x):\n    return list(set(['a','b','c']).intersection(['c','b','a'])) if x == 0 else list(set(['apple','banana']).intersection(['banana','apple']))\n",
                       canon=canonical, ref=[canonical]*3,
                       base="def check(candidate):\n    assert candidate(0) == ['a','b','c']\n")
            (oracle/'exec/0.job.json').write_text(json.dumps(job))
            tasks = {0: dict(entry='f', put=job['put'])}
            rows = [dict(task=0, sample=0, asserts=[dict(src="assert f(0)==['a','b','c']"),
                                                  dict(src="assert f(1)==['apple','banana']")])]
            a = fp.execute_records(tasks, rows, oracle, {}, {0: 0}, root/'first', workers=1)
            b = fp.execute_records(tasks, rows, oracle, {}, {0: 0}, root/'second', workers=1)
            self.assertEqual(a, b)
            self.assertFalse(a['0']['calls']['f(0)']['d_i'])
            self.assertTrue(a['0']['calls']['f(1)']['d_i'])

    def test_full_requires_actual_stages_and_respects_cached_judge(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertFalse(fp.full_available(root))
            (root/'post_responses.json').write_text('[]')
            self.assertFalse(fp.full_available(root))
            (root/'judge_responses.json').write_text('[]')
            self.assertTrue(fp.full_available(root))
        rec = record(emit=False)
        rec['judge_cands'] = dict(mutant=dict(emit=True, canon_ok=True, put_ok=False, post_ok=True))
        self.assertFalse(fp.call_score(rec, 'ref')['detecting'])
        self.assertTrue(fp.call_score(rec, 'full', dict(pick='mutant'))['detecting'])
        rec['judge_cands']['mutant']['post_ok'] = False
        self.assertFalse(fp.call_score(rec, 'full', dict(pick='mutant'))['detecting'])


if __name__ == '__main__':
    unittest.main()
