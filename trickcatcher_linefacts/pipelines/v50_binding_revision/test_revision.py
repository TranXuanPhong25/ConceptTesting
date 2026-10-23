"""Synthetic CPU regression suite. Never reads the diagnostic pools or contacts an API."""
import ast
import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx

from . import revision_protocol as p, capability as c, revision as app
from .d1_client import Client, InputOverCap, TransportStop, MODEL
from .flow_common import immutable, write_json
from .isolated import run_once


def binding(name='B1', relation='count_ge', args=None, concept='eligible_contribution'):
    return {'id': name, 'concept': concept, 'relation': relation,
            'arguments': ['values', 'cutoff'] if args is None else args,
            'spec_quote': 'Include equality.', 'spec_status': 'justified'}


def reply(value):
    return {'text': json.dumps(value), 'finish_reason': 'stop', 'origin': 'synthetic_CPU_control'}


def row():
    return {'spec': 'Include equality.', 'parameters': ['values', 'cutoff'],
            'code': 'def sample(values, cutoff):\n return sum(v > cutoff for v in values)\n',
            'rows': [{'id': 'O1', 'input': '([3], 3)', 'execution_status': 'ok',
                      'output': '0', 'output_capture': 'literal', 'exception_type': None}]}


def initial(items):
    raw = reply({'bindings': items})
    return {'raw': raw, 'admission': p.admit(raw)}


def final(items):
    return reply({'bindings': items, 'implementation_judgment': 'observed_mismatch',
                  'reason': 'The equality element is excluded.', 'evidence': ['O1', 'original_spec']})


def domain(two=True):
    result = [{'name': 'values', 'kind': 'int_list', 'min_value': -3, 'max_value': 3, 'max_size': 4}]
    if two:
        result.append({'name': 'cutoff', 'kind': 'int', 'min_value': -3, 'max_value': 3, 'max_size': 0})
    return result


class AdmissionTests(unittest.TestCase):
    def test_invalid_sibling_does_not_drop_good_binding(self):
        good = binding(); bad = dict(binding('B2'), concept='nonsense')
        for is_final, response in [(False, reply({'bindings': [good, bad]})), (True, final([good, bad]))]:
            before = copy.deepcopy(response)
            admitted = p.admit(response, is_final, ['O1', 'original_spec'])
            self.assertEqual(admitted['accepted'], [good])
            self.assertEqual(len(admitted['items']), 2)
            self.assertFalse(admitted['items'][1]['admitted'])
            self.assertEqual(response, before)

    def test_unknown_legal_and_explicitly_not_executable(self):
        unknown = dict(binding(relation='unknown', args=[], concept='unknown'), spec_status='unknown', spec_quote='')
        record = initial([unknown])
        self.assertEqual(record['admission']['accepted'], [unknown])
        self.assertIsNone(p.checks([unknown], row())['B1']['concept_relation_vocabulary_compatible'])
        self.assertEqual(p.compare_feedback([unknown], row())['rows'][0][2], 'unknown')

    def test_duplicate_id_only_drops_colliding_items(self):
        result = p.admit(reply({'bindings': [binding(), binding(), binding('B3')]}))
        self.assertEqual([b['id'] for b in result['accepted']], ['B3'])
        self.assertEqual(len(result['items']), 3)

    def test_malformed_envelope_and_duplicate_json_keep_finals_possible(self):
        for text in ('bad JSON', '[1,2]', '{"bindings":[],"bindings":[]}'):
            raw = {'text': text, 'finish_reason': 'stop'}
            record = {'raw': raw, 'admission': p.admit(raw)}
            packet = p.final_packet(row(), record, p.compare_feedback([], row()), 'raw')
            self.assertEqual(packet['initial_response'], text)
            self.assertTrue(packet['initial_admission']['initial_unavailable'])
            self.assertEqual(packet['observations'], row()['rows'])

    def test_root_error_preserves_readable_items(self):
        response = reply({'bindings': [binding()], 'extra': 3})
        result = p.admit(response)
        self.assertFalse(result['envelope_valid'])
        self.assertEqual(len(result['accepted']), 1)

    def test_overflow_preserved_not_silently_discarded(self):
        items = [binding(f'B{i}') for i in range(4)]
        result = p.admit(reply({'bindings': items}))
        self.assertEqual(len(result['items']), 4)
        self.assertEqual(len(result['accepted']), 3)
        self.assertIn('item_budget_exceeded', [x['rule'] for x in result['items'][3]['errors']])

    def test_final_can_add_change_and_drop(self):
        old = [binding(relation='count_gt'), binding('B2')]
        new = [binding(args=['cutoff', 'values']), binding('NEW')]
        result = p.admit(final(new), True, ['O1', 'original_spec'])
        self.assertEqual(result['accepted'], new)
        moves = p.transitions(old, new)
        self.assertEqual(moves['added'], ['NEW'])
        self.assertEqual(moves['removed'], ['B2'])
        self.assertEqual(moves['changed'], ['B1'])
        # A syntactic change need not be a semantic improvement.
        self.assertIn('no semantic', moves['scope'])

    def test_bad_evidence_does_not_erase_valid_binding(self):
        response = final([binding()]); value = json.loads(response['text']); value['evidence'].append('invented')
        result = p.admit(reply(value), True, ['O1', 'original_spec'])
        self.assertFalse(result['evidence_valid'])
        self.assertEqual(result['accepted'], [binding()])

    def test_evidence_has_no_arbitrary_eight_id_limit(self):
        value = json.loads(final([binding()])['text']); value['evidence'] = [f'O{i}' for i in range(12)]
        result = p.admit(reply(value), True, value['evidence'])
        self.assertTrue(result['evidence_valid'])
        self.assertTrue(result['envelope_valid'])

    def test_truncation_not_repaired(self):
        response = reply({'bindings': [binding()]}); response['finish_reason'] = 'length'
        result = p.admit(response)
        self.assertFalse(result['parseable'])
        self.assertEqual(result['accepted'], [])

    def test_only_computed_feedback_differs_between_arms(self):
        record = initial([binding(relation='count_gt')]); data = row()
        before = copy.deepcopy((record, data))
        feedback = p.compare_feedback(record['admission']['accepted'], data)
        raw = p.final_packet(data, record, feedback, 'raw')
        tool = p.final_packet(data, record, feedback, 'tool')
        self.assertIsNone(raw.pop('tool_feedback'))
        self.assertEqual(tool.pop('tool_feedback'), feedback)
        self.assertEqual(raw, tool)
        self.assertEqual((record, data), before)
        self.assertNotIn('fixture', raw)
        # Wrong normative relation can agree with the implementation.
        self.assertTrue(feedback['rows'][0][5])
        self.assertIn('unverified', feedback['scope'])

    def test_output_argument_not_silently_mapped(self):
        b = binding(args=['output', 'cutoff'])
        result = initial([b])
        self.assertEqual(result['admission']['accepted'], [b])
        self.assertFalse(p.checks([b], row())['B1']['argument_names_known'])
        self.assertEqual(p.compare_feedback([b], row())['rows'][0][2], 'unknown')

    def test_all_unknown_conventions_remain_consistent(self):
        for concept, relation in [('unknown', 'unknown'), ('unknown', 'count_ge'), ('eligible_contribution', 'unknown')]:
            b = dict(binding(concept=concept, relation=relation), spec_status='unknown')
            self.assertEqual(initial([b])['admission']['accepted'], [b])
            flag = p.checks([b], row())['B1']['concept_relation_vocabulary_compatible']
            self.assertIsNot(flag, False)


class SearchTests(unittest.TestCase):
    def test_known_boundary_discriminator_reproducible(self):
        a, b = binding(), binding('B2', relation='count_gt')
        first = c.find_discriminator(a, b, domain())
        second = c.find_discriminator(a, b, domain())
        self.assertEqual(first, second)
        self.assertEqual(first['status'], 'found')
        args = ast.literal_eval(first['input'])
        self.assertIn(args[1], args[0])
        self.assertNotEqual(first['left_prediction'], first['right_prediction'])
        self.assertLessEqual(first['checks'], 512)

    def test_equivalent_relations_are_bounded_unknown(self):
        result = c.find_discriminator(binding(), binding('B2'), domain(), max_examples=12)
        self.assertEqual(result['status'], 'not_found_within_budget')
        self.assertIn('not infeasibility', result['scope'])

    def test_no_silent_missing_alternative_fill(self):
        result = c.find_discriminator(binding(relation='unknown'), binding(), domain())
        self.assertEqual(result['status'], 'not_available')
        self.assertEqual(result['checks'], 0)

    def test_hard_predicate_budget(self):
        result = c.find_discriminator(binding(), binding('B2'), domain(), max_checks=1)
        self.assertLessEqual(result['checks'], 1)
        self.assertNotEqual(result['status'], 'found')

    def test_domain_types_are_exact(self):
        self.assertTrue(c.in_domain(([1], 0), domain()))
        self.assertFalse(c.in_domain(([True], 0), domain()))
        self.assertFalse(c.in_domain(([1], False), domain()))
        self.assertFalse(c.in_domain(([7], 0), domain()))

    def test_exception_and_none_predictions_differ(self):
        a = binding(relation='min_positive_none', args=['values'])
        b = binding('B2', relation='min_positive_raise', args=['values'])
        found = c.find_discriminator(a, b, domain(False))
        self.assertEqual(found['status'], 'found')
        self.assertNotEqual(found['left_prediction'], found['right_prediction'])


class ExecutionTests(unittest.TestCase):
    def test_mutation_alias_snapshot_and_cache(self):
        source = 'def sample(values):\n values.append(2)\n alias=values\n return alias\n'
        with tempfile.TemporaryDirectory() as temp:
            result = c.execute_probe(source, 'sample', '([1],)', domain(False), temp,
                                     names=['values', 'alias'], lines=[4])
            self.assertTrue(result['native_checked'])
            self.assertEqual(result['ordinary']['output_repr'], '[1, 2]')
            self.assertEqual(result['ordinary']['output_aliases'], [0])
            self.assertNotEqual(result['ordinary']['input_before'], result['ordinary']['input_after'])
            snapshot = result['traced']['snapshots'][0]
            self.assertEqual(snapshot['values']['alias']['repr'], '[1, 2]')
            with patch('subprocess.Popen', side_effect=AssertionError('must use cache')):
                cached = c.execute_probe(source, 'sample', '([1],)', domain(False), temp,
                                         names=['values', 'alias'], lines=[4])
            self.assertEqual(result, cached)
            self.assertEqual(len(list(Path(temp).glob('*/attempt.json'))), 2)

    def test_early_return_exception_and_trace_truncation(self):
        source = 'def sample(values):\n if not values:\n  raise ValueError()\n return values[0]\n'
        with tempfile.TemporaryDirectory() as temp:
            exceptional = c.execute_probe(source, 'sample', '([],)', domain(False), temp)
            self.assertTrue(exceptional['native_checked'])
            self.assertEqual(exceptional['ordinary']['exception_type'], 'ValueError')
            early = c.execute_probe(source, 'sample', '([2],)', domain(False), temp, max_events=1)
            self.assertTrue(early['native_checked'])
            self.assertEqual(early['ordinary']['output_repr'], '2')
            self.assertFalse(early['traced']['trace_complete'])
            self.assertTrue(early['traced']['trace_truncated'])

    def test_invalid_domain_never_launches(self):
        with tempfile.TemporaryDirectory() as temp, patch('subprocess.Popen') as launch:
            with self.assertRaisesRegex(ValueError, 'outside_declared_domain'):
                c.execute_probe('def sample(values): return values', 'sample', '([99],)', domain(False), temp)
            launch.assert_not_called()

    def test_timeout_is_unknown_and_consumed(self):
        source = 'def sample(values):\n while True:\n  pass\n'
        with tempfile.TemporaryDirectory() as temp:
            result = c.execute_probe(source, 'sample', '([],)', domain(False), temp)
            self.assertFalse(result['native_checked'])
            self.assertEqual(result['ordinary']['status'], 'unresolved')
            with patch('subprocess.Popen', side_effect=AssertionError('no unknown retry')):
                again = c.execute_probe(source, 'sample', '([],)', domain(False), temp)
            self.assertEqual(again, result)

    def test_interrupted_worker_not_relaunched(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp); script = Path('/artificial.py'); job = {'rows': []}
            from .flow_common import digest
            from .paths import CONFIG
            immutable(folder/'attempt.json', {'identity': digest({'job': job, 'script': str(script),
                      'interpreter': CONFIG['V4_PYTHON']}), 'state': 'reserved', 'launched': None})
            with patch('subprocess.Popen', side_effect=AssertionError('no unknown retry')):
                result = run_once(script, job, folder)
            self.assertEqual(result['reason'], 'interrupted_worker_attempt_not_retried')


class LifecycleTests(unittest.TestCase):
    def approval(self):
        return {'freeze_sha256': 'x', 'endpoint_window': {'exclusive': True,
                'competing_owners_checked': ['synthetic'],
                'expires_utc': (datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()}}

    def test_prepare_cannot_read_pools_without_audit(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(app, 'parents') as parents:
            with self.assertRaises(FileNotFoundError):
                app.prepare(Path(temp))
            parents.assert_not_called()

    def test_missing_endpoint_window_prevents_calls(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(app, 'verify'), \
             patch.object(app, 'approval_matches', return_value={'freeze_sha256': 'x'}), \
             patch.object(app, 'sha', return_value='x'), patch.object(app, 'Client') as client:
            with self.assertRaisesRegex(ValueError, 'shared_endpoint_window_required'):
                app.run(Path(temp))
            client.assert_not_called()

    def test_malformed_initial_still_gets_both_finals_all24slots(self):
        responses = []
        class FakeClient:
            def __init__(self, root, **kwargs): pass
            def close(self): pass
            def complete(self, slot, messages):
                responses.append(slot)
                return {'text': 'bad JSON', 'finish_reason': 'stop'} if slot.endswith('initial') else final([binding('NEW')])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_json(root/'launch_approval.json', self.approval())
            for i in range(1, 9): write_json(root/'prepared'/f'E{i}.json', row())
            approval = {'freeze_sha256': 'x', 'endpoint_window': {'exclusive': True,
                        'competing_owners_checked': ['synthetic'],
                        'expires_utc': (datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()}}
            with patch.object(app, 'verify'), patch.object(app, 'quota'), patch.object(app, 'sha', return_value='x'), \
                 patch.object(app, 'approval_matches', return_value=approval), patch.object(app, 'Client', FakeClient):
                result = app.run(root)
            self.assertEqual(result['state'], 'complete')
            self.assertEqual(len(responses), 24)
            self.assertEqual(set(responses), set(app.SLOTS))
            self.assertTrue((root/'generation_frozen.json').exists())
            for i in range(1, 9):
                raw = app.read(root/'requests'/f'E{i}__final_raw.json')
                tool = app.read(root/'requests'/f'E{i}__final_tool.json')
                a,b = json.loads(raw[1]['content']),json.loads(tool[1]['content'])
                a.pop('tool_feedback'); b.pop('tool_feedback'); self.assertEqual(a,b)

    def test_transport_failure_not_retried(self):
        requests = []
        def handler(request):
            requests.append(request.url.path)
            if request.url.path.endswith('/models'):
                return httpx.Response(200, json={'data': [{'id': MODEL, 'max_model_len': 8192}]})
            raise httpx.ReadTimeout('synthetic only')
        with tempfile.TemporaryDirectory() as temp:
            client = Client(Path(temp), base='http://synthetic.invalid/v1', transport=httpx.MockTransport(handler))
            client.token_count = lambda _: 10
            message = [{'role':'user','content':'artificial'}]
            with self.assertRaises(TransportStop): client.complete('slot', message)
            with self.assertRaisesRegex(TransportStop, 'already_consumed'): client.complete('slot', message)
            self.assertEqual(requests.count('/v1/chat/completions'), 1)
            self.assertFalse(app.read(Path(temp)/'calls/slot/attempt.json')['usage_known'])
            client.close()

    def test_no_native_or_gold_import_in_model_controller(self):
        for name in ('revision.py', 'revision_protocol.py'):
            text = (app.HERE/name).read_text()
            self.assertNotIn('import capability', text)
            self.assertNotIn('fixture_oracles', text)
            self.assertNotIn('EVALUATOR_RUBRIC', text)

    def test_terminal_stop_keeps_all_slots_and_frozen_inventory(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(app, 'verify'), patch.object(app, 'quota'), \
             patch.object(app, 'sha', return_value='x'), patch.object(app, 'approval_matches', return_value=self.approval()), \
             patch.object(app, 'Client', side_effect=TransportStop('synthetic_transport_failure')):
            root = Path(temp); write_json(root/'launch_approval.json', self.approval()); result = app.run(root)
            self.assertEqual(result['state'], 'stopped')
            self.assertEqual(result['reason'], 'synthetic_transport_failure')
            snapshot = app.read(root/'checkpoints/0000.json')
            self.assertEqual(len(snapshot['slots']), 24)
            self.assertTrue(all(v['state']=='not_attempted' for v in snapshot['slots'].values()))
            self.assertIn('status.json', snapshot['files'])
            with self.assertRaisesRegex(ValueError, 'terminal_run_no_automatic_retry'):
                app.run(root)

    def test_quota_resume_preserves_and_reuses_received_initial(self):
        calls = []
        class FakeClient:
            def __init__(self, root, **kwargs): self.root = root.parent
            def close(self): pass
            def complete(self, slot, messages):
                artifact = self.root/'artifacts'/f'{slot}.json'
                if artifact.exists(): return app.read(artifact)['raw']
                calls.append(slot)
                return reply({'bindings': [binding()]}) if slot.endswith('initial') else final([binding()])
        with tempfile.TemporaryDirectory() as temp, patch.object(app, 'verify'), \
             patch.object(app, 'sha', return_value='x'), patch.object(app, 'approval_matches', return_value=self.approval()), \
             patch.object(app, 'Client', FakeClient):
            root = Path(temp); write_json(root/'launch_approval.json', self.approval())
            for i in range(1,9): write_json(root/'prepared'/f'E{i}.json', row())
            with patch.object(app, 'quota', side_effect=[None, None, TransportStop('quota_at_or_below15_or_unknown')]):
                stopped = app.run(root)
            self.assertEqual(stopped['state'], 'stopped')
            self.assertEqual(len(calls), 1)
            checkpoint = (root/'checkpoints/0000.json').read_bytes()
            # A new endpoint window is allowed after quota reset; old bytes survive.
            previous_approval = (root/'launch_approval.json').read_text()
            renewed = self.approval()
            renewed['endpoint_window']['expires_utc'] = (datetime.now(timezone.utc)+timedelta(hours=2)).isoformat()
            write_json(root/'launch_approval.json', renewed)
            with patch.object(app, 'quota'):
                resumed = app.run(root)
            self.assertEqual(resumed['state'], 'complete')
            self.assertEqual(len(calls), 24)
            self.assertEqual(len(set(calls)), 24)
            self.assertEqual((root/'checkpoints/0000.json').read_bytes(), checkpoint)
            self.assertTrue((root/'checkpoints/0001.json').exists())
            self.assertEqual(app.read(root/'launches/launch0.json')['approval_json'], previous_approval)

    # Real file hashes below: only verify, approval_matches, quota and Client are synthetic.
    def real_root(self, temp):
        root = Path(temp)
        for i in range(1, 9): write_json(root/'prepared'/f'E{i}.json', row())
        write_json(root/'freeze.json', {'synthetic': True})
        self.renew(root, 1)
        return root

    def renew(self, root, hours, **extra):
        approval = {'freeze_sha256': app.sha(root/'freeze.json'), 'review_sha256': 'r1',
                    'endpoint_window': {'exclusive': True, 'competing_owners_checked': ['synthetic'],
                    'expires_utc': (datetime.now(timezone.utc)+timedelta(hours=hours)).isoformat()}}
        approval.update(extra)
        write_json(root/'launch_approval.json', approval)
        return (root/'launch_approval.json').read_bytes()

    def run_real(self, root, calls, quota=None, over=()):
        class FakeClient:
            def __init__(self, root, **kwargs): self.root = root.parent
            def close(self): pass
            def complete(self, slot, messages):
                if slot in over: raise InputOverCap(7000)
                artifact = self.root/'artifacts'/f'{slot}.json'
                if artifact.exists(): return app.read(artifact)['raw']
                calls.append(slot)
                return reply({'bindings': [binding()]}) if slot.endswith('initial') else final([binding()])
        with patch.object(app, 'verify'), patch.object(app, 'Client', FakeClient), \
             patch.object(app, 'approval_matches', side_effect=lambda r, kind: app.read(r/f'{kind}_approval.json')), \
             patch.object(app, 'quota', side_effect=quota):
            return app.run(root)

    def test_renewal_after_first_quota_check_and_chained_renewals(self):
        calls = []; stop = TransportStop('quota_at_or_below15_or_unknown')
        with tempfile.TemporaryDirectory() as temp:
            root = self.real_root(temp); approvals = [(root/'launch_approval.json').read_bytes()]
            self.assertEqual(self.run_real(root, calls, [stop])['reason'], stop.args[0])
            self.assertEqual(calls, [])
            approvals.append(self.renew(root, 2))
            self.assertEqual(self.run_real(root, calls, [None, None, stop])['state'], 'stopped')
            self.assertEqual(len(calls), 1)
            first_checkpoints = [p.read_bytes() for p in sorted((root/'checkpoints').glob('*.json'))]
            approvals.append(self.renew(root, 3))
            self.assertEqual(self.run_real(root, calls)['state'], 'complete')
            self.assertEqual(sorted(calls), sorted(app.SLOTS))
            for i, raw in enumerate(approvals):
                record = app.read(root/f'launches/launch{i}.json')
                self.assertEqual(record['approval_json'].encode('utf-8'), raw)
            self.assertEqual([p.read_bytes() for p in sorted((root/'checkpoints').glob('*.json'))][:2], first_checkpoints)

    def test_renewal_rejections_change_nothing(self):
        stop = TransportStop('quota_at_or_below15_or_unknown')
        def tamper_launch(root):
            record = app.read(root/'launches/launch0.json'); record['approval_json'] += ' '
            write_json(root/'launches/launch0.json', record); self.renew(root, 2)
        def forge_launch(root):
            self.renew(root, 2); write_json(root/'launches/launch9.json', app.read(root/'launches/launch0.json'))
        def drop_launches(root):
            for p in (root/'launches').glob('*.json'): p.unlink()
            self.renew(root, 2)
        def drift_artifact(root):
            self.renew(root, 2); write_json(root/'artifacts/E3__initial.json', {'raw': None})
        cases = [(tamper_launch, 'prior_launch_approval_not_archived'),
                 (drop_launches, 'prior_launch_approval_not_archived'),
                 (forge_launch, 'quota_checkpoint_drift'),
                 (drift_artifact, 'quota_checkpoint_drift'),
                 (lambda r: self.renew(r, 2, review_sha256='r2'), 'renewal_changes_more_than_window'),
                 (lambda r: self.renew(r, 0.5), 'renewal_window_not_later'),
                 (lambda r: (r/'status.json').unlink(), 'resume_state_incomplete'),
                 (lambda r: write_json(r/'status.json', dict(app.read(r/'status.json'), pid=0)), 'status_checkpoint_mismatch')]
        for change, error in cases:
            with self.subTest(error=error, change=getattr(change, '__name__', '')), tempfile.TemporaryDirectory() as temp:
                calls = []; root = self.real_root(temp)
                self.run_real(root, calls, [None, None, stop])
                change(root)
                status = (root/'status.json').read_bytes() if (root/'status.json').exists() else None
                with self.assertRaisesRegex(ValueError, error):
                    self.run_real(root, calls)
                self.assertEqual(len(calls), 1)
                self.assertEqual(len(list((root/'checkpoints').glob('*.json'))), 1)
                if status is not None: self.assertEqual((root/'status.json').read_bytes(), status)

    def test_renewal_after_non_quota_stop_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            calls = []; root = self.real_root(temp)
            result = self.run_real(root, calls, [None, None, TransportStop('endpoint_window_expired')])
            self.assertEqual(result['reason'], 'endpoint_window_expired')
            self.renew(root, 2)
            with self.assertRaisesRegex(ValueError, 'terminal_run_no_automatic_retry'):
                self.run_real(root, calls)
            self.assertEqual(len(calls), 1)

    def test_input_over_cap_is_per_slot_and_run_continues(self):
        paths = []
        def handler(request):
            paths.append(request.url.path)
            return httpx.Response(200, json={'data': [{'id': MODEL, 'max_model_len': 8192}]})
        with tempfile.TemporaryDirectory() as temp:
            client = Client(Path(temp), base='http://synthetic.invalid/v1', transport=httpx.MockTransport(handler))
            client.token_count = lambda _: 6145
            with self.assertRaises(InputOverCap): client.complete('slot', [{'role': 'user', 'content': 'synthetic'}])
            self.assertEqual(paths, ['/v1/models'])
            self.assertFalse((Path(temp)/'calls/slot/attempt.json').exists())
            client.close()
        over = {'E6__initial', 'E3__final_tool'}
        with tempfile.TemporaryDirectory() as temp:
            calls = []; root = self.real_root(temp)
            self.assertEqual(self.run_real(root, calls, over=over)['state'], 'complete')
            self.assertEqual(sorted(calls), sorted(set(app.SLOTS) - over))
            states = app.read(root/'slots.json')
            self.assertEqual({k for k, v in states.items() if v['state'] == 'input_over_cap'}, over)
            record = app.read(root/'artifacts/E3__final_tool.json')
            self.assertEqual(record['input_over_cap'], {'input_tokens': 7000, 'cap': 6144, 'http_sent': False})
            a, b = (json.loads(app.read(root/'requests'/f'E6__final_{arm}.json')[1]['content']) for arm in ('raw', 'tool'))
            self.assertIsNone(a['initial_response'])
            a.pop('tool_feedback'); b.pop('tool_feedback'); self.assertEqual(a, b)

    def test_freeze_rejects_source_dependency_pool_and_rubric_drift(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); write_json(root/'preparation_approval.json', {})
            frozen = {'sources': {'a':'original'}, 'dependencies': {'p':'original'}, 'parents': {'old':'original'},
                      'prepared': {}, 'slots': app.SLOTS, 'evaluation_sha256': app.sha(app.EVALUATION),
                      'preparation_approval_sha256': app.sha(root/'preparation_approval.json')}
            write_json(root/'freeze.json', frozen)
            with patch.object(app, 'sources', return_value=frozen['sources']) as source, \
                 patch.object(app, 'dependencies', return_value=frozen['dependencies']) as deps, \
                 patch.object(app, 'parents', return_value=frozen['parents']), patch.object(app, 'approval_matches'):
                app.verify(root)
                source.return_value={'a':'drift'}
                with self.assertRaisesRegex(ValueError, 'source_dependency_drift'): app.verify(root)
                source.return_value=frozen['sources']; deps.return_value={'p':'drift'}
                with self.assertRaisesRegex(ValueError, 'source_dependency_drift'): app.verify(root)
                deps.return_value=frozen['dependencies']
                write_json(root/'prepared/new.json', {})
                with self.assertRaisesRegex(ValueError, 'parent_or_pool_drift'): app.verify(root)
                (root/'prepared/new.json').unlink()
                frozen['evaluation_sha256']='drift'; write_json(root/'freeze.json', frozen)
                with self.assertRaisesRegex(ValueError, 'evaluation_drift'): app.verify(root)

    def test_http_guard_stops_before_completion_reservation(self):
        paths=[]; guards=[]
        def handler(request):
            paths.append(request.url.path)
            if request.url.path.endswith('/models'):
                return httpx.Response(200,json={'data':[{'id':MODEL,'max_model_len':8192}]})
            if request.url.path.endswith('/tokenize'):
                return httpx.Response(200,json={'count':10,'max_model_len':8192})
            raise AssertionError('completion must not be sent')
        def guard():
            guards.append(1)
            if len(guards)==3: raise TransportStop('endpoint_window_expired')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); client=Client(root,base='http://synthetic.invalid/v1',
                transport=httpx.MockTransport(handler),before_request=guard)
            with self.assertRaisesRegex(TransportStop,'endpoint_window_expired'):
                client.complete('slot',[{'role':'user','content':'synthetic'}])
            self.assertEqual(paths,['/v1/models','/tokenize'])
            self.assertFalse((root/'calls/slot/attempt.json').exists())
            self.assertEqual(len(list((root/'metadata_calls').glob('*/attempt.json'))),2)
            self.assertTrue(all(app.read(f)['state']=='received' for f in (root/'metadata_calls').glob('*/attempt.json')))
            client.close()

    def test_models_cache_and_explicit_resume_preflight(self):
        paths=[]
        def handler(request):
            paths.append(request.url.path)
            return httpx.Response(200,json={'data':[{'id':MODEL,'max_model_len':8192}]})
        with tempfile.TemporaryDirectory() as temp:
            for launch in ('launch0','launch0','launch1'):
                client=Client(Path(temp),base='http://synthetic.invalid/v1',transport=httpx.MockTransport(handler),preflight_id=launch)
                client.close()
            self.assertEqual(paths,['/v1/models','/v1/models'])

    def test_unknown_models_attempt_not_retried(self):
        paths=[]
        def handler(request):
            paths.append(request.url.path)
            raise httpx.ReadTimeout('synthetic only')
        with tempfile.TemporaryDirectory() as temp:
            for _ in range(2):
                with self.assertRaises(TransportStop):
                    Client(Path(temp),base='http://synthetic.invalid/v1',transport=httpx.MockTransport(handler))
            self.assertEqual(paths,['/v1/models'])

    def test_quota_checks_are_durable_and_threshold_inclusive(self):
        from types import SimpleNamespace
        snapshots=[{'remaining_percent':16,'should_stop':False},{'remaining_percent':15,'should_stop':True}]
        with tempfile.TemporaryDirectory() as temp, patch.object(app.subprocess,'run',
            side_effect=[SimpleNamespace(stdout=json.dumps(s)) for s in snapshots]):
            root=Path(temp); app.quota(root)
            with self.assertRaises(TransportStop): app.quota(root)
            self.assertEqual([app.read(p) for p in sorted((root/'quota_checks').glob('*.json'))],snapshots)


if __name__ == '__main__':
    unittest.main()
