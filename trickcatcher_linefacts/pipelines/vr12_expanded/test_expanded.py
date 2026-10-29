import unittest
from copy import deepcopy
from . import diagnostic as d
from .test_diagnostic import record


class ExpansionTests(unittest.TestCase):
    def test_same_public_task_and_seed_routing_control(self):
        r=record();before=deepcopy(r)
        strict=d.make_task(r,'strict');retain=d.make_task(r,'retain')
        self.assertEqual(strict['concept_facts'],retain['concept_facts'])
        self.assertEqual(strict['vr8_round1_response'],retain['vr8_round1_response'])
        self.assertFalse(strict['vr9_retain']);self.assertTrue(retain['vr9_retain'])
        self.assertNotIn('vr9_saved_pools',strict)
        self.assertEqual(r,before)

    def test_rejects_injected_historical_task_pool(self):
        r=record();r['task']['vr9_saved_pools']=[{}]
        with self.assertRaisesRegex(ValueError,'new_tasks'):
            d.make_task(r,'retain')

    def test_cap_matches_explicit_four_arm_k1_census(self):
        self.assertEqual(d.TASKS,11)
        self.assertEqual(d.MAX_CALLS,132)
        self.assertEqual(set(d.MODES),{'strict','retain','applicable','generic'})


if __name__=='__main__':unittest.main()
