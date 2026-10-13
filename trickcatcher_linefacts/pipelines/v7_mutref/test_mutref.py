"""Unit and CPU replay regression tests; run verify first for integration evidence."""
import copy
import json
import random
import unittest
from pathlib import Path

from . import facts, hint_rank, paths, refs
from .offline_client import CacheMiss, OfflineClient, request
from .run import Layout, task_sources


class MutrefTests(unittest.TestCase):
    def row(self, **changes):
        row = dict(src='code', slot='OUTPUT', covered_site=False, boundary=False,
                   tier=0, cmp_dist=99, hit_frac=0.1, out_change=False,
                   crash=0, n_eval=1, mut_fh=0, mut_wrong=0)
        row.update(changes)
        return row

    def test_frozen_coefficients(self):
        saved = json.loads((paths.REPO / 'trickcatcher_linefacts/out/hint_rank/results.json').read_text())
        self.assertEqual(paths.CONFIG['hint_rank']['coefficients'], saved['rules']['LR[noref+mutref]']['coef'])
        self.assertEqual(paths.CONFIG['hint_rank']['selection'], 'plain')
        self.assertEqual(paths.VERSION, 'v7_mutref')

    def test_all_kinds_can_win(self):
        for kind in hint_rank.KIND_GROUPS:
            rows = [self.row(), self.row(), self.row(slot=kind, crash=1, out_change=True, boundary=True)]
            self.assertEqual(hint_rank.select(17, rows, 1), [2], kind)
        rows = [self.row(src='spec', slot='SPEC-LARGE', crash=1, out_change=True), self.row()]
        self.assertEqual(hint_rank.select(17, rows, 1), [0])

    def test_analysis_seeded_ties_and_small_pools(self):
        rows = [self.row() for _ in range(15)]
        expected = list(range(15))
        random.Random(20261010 + 19).shuffle(expected)
        self.assertEqual(hint_rank.select(19, rows), expected[:3])
        self.assertEqual(hint_rank.select(19, []), [])
        self.assertEqual(hint_rank.select(19, rows[:1]), [0])
        pool = [{'kind': 'OUTPUT'}, {'kind': 'SHAPE'}]
        self.assertEqual(len(facts.pick(pool, 19, rank_rows=rows[:2])), 2)
        with self.assertRaises(ValueError): facts.pick(pool, 19, rank_rows=[])

    def test_labels_and_refdis_cannot_affect_score(self):
        row = self.row()
        extra = dict(row, pf=1.0, good=True, n_maj=10, ref_dis=10, allowed=False, block=123)
        self.assertEqual(hint_rank.score(row), hint_rank.score(extra))
        self.assertNotIn('refdis', paths.CONFIG['hint_rank']['feature_groups'])

    def test_mutref_two_indicators(self):
        self.assertEqual(hint_rank.x_of(self.row(mut_wrong=5))[-2:], [0.0, 1.0])
        self.assertEqual(hint_rank.x_of(self.row(mut_wrong=5, mut_fh=1))[-2:], [1.0, 0.0])
        self.assertEqual(hint_rank.x_of(self.row())[-2:], [0.0, 0.0])

    def test_spec_only_refs_requests_match_cache(self):
        layout = Layout()
        tasks = task_sources(layout)[0]
        altered = copy.deepcopy(tasks[0])
        altered['put'] += '\n# PUT implementation annotation must not enter a spec-only request\n'
        self.assertEqual(list(refs.jobs([tasks[0]])), list(refs.jobs([altered])))
        client = OfflineClient(layout.oracle / 'cache')
        saved = {(r['task'], r['sample']): r for r in json.loads((layout.refs / 'ref_responses.json').read_text())}
        for job in refs.jobs(tasks):
            result = client.chat(job['messages'], job['seed'], temperature=job['temperature'],
                                 top_p=0.95, max_tokens=job['max_tokens'])
            self.assertEqual(result['text'], saved[job['task'], job['sample']]['text'])
        self.assertEqual(len(client.hits), 1330)
        with self.assertRaises(CacheMiss): client.chat([{'role': 'user', 'content': 'missing'}], -1)

    def test_generation_and_oracle_sources_unchanged(self):
        original = paths.HERE.parent / 'v7'
        for name in ('prompts.py', 'gen_prompts.py', 'v4_prompts.py', 'run_v4.py',
                     'v4_worker.py', 'oracle_b01.py', 'gen_inputs.py', 'tracer.py', 'llm_client.py', 'PREREG.md'):
            self.assertEqual((paths.HERE / name).read_bytes(), (original / name).read_bytes(), name)
        self.assertTrue(paths.DATA_OUT.is_relative_to(paths.HERE))
        with self.assertRaises(ValueError): paths.safe_output(original / 'out.json')

    def test_cpu_replay_report(self):
        report = json.loads((paths.DATA_OUT / 'checks/report.json').read_text())
        selection = report['selection']
        self.assertEqual(selection['measured_tasks'], dict(even=58, odd=54))
        self.assertEqual(selection['good_at_3'], dict(even=37, odd=35))
        self.assertEqual(selection['dev_tasks'], 113)
        for key in ('analysis_selection_mismatches', 'unexpected_feature_mismatches', 'ref_survivor_mismatches',
                    'witness_mismatches', 'bundle_derivation_mismatches'):
            self.assertEqual(selection[key], [], key)
        self.assertTrue(report['round1']['all_equal'])
        self.assertGreater(report['round1']['requests'], 0)
        self.assertEqual(report['round1']['requests'], selection['unchanged_hints'] * 7 * 3)


if __name__ == '__main__': unittest.main()
