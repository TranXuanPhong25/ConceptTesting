"""Offline request equivalence, discovery and sandbox feedback tests."""
import ast
import json
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from . import gen_prompts, prompts, run_v4, v4_callfb as fb, v4_prompts, v4_runtime
from . import dry_run
from .offline_client import OfflineClient, request

HERE = Path(__file__).resolve().parent


def tiny_task():
    return dict(task=2, entry='entry', put='def entry(x, y=2):\n    """Return x plus y for nonnegative x."""\n    return x+y\n',
                base='def check(candidate):\n    assert candidate(0) == 2', concept_meta=[], placebo_meta=[],
                mined_valid_src='def valid(x, y=2):\n    return x >= 0\n', facts_version='v4')


class ProtocolTests(unittest.TestCase):
    def test_round1_requests_and_historical_cache_keys(self):
        from ..v7 import gen_prompts as gp7, prompts as p7, v4_prompts as vp7
        from ..v7.offline_client import request as req7
        cache = OfflineClient(HERE.parents[1]/'out/gen2_qwen7b_v7hyb_v4_r2/cache')
        tasks = json.loads(dry_run.BUNDLE.read_text())['tasks']
        hits, checks = 0, 0
        for task in tasks:
            for sample in range(3):
                for arm, kind in [('plain','plain'), ('concept','concept'), ('placebo-hybrid','placebo')]:
                    old = gp7.messages(*p7.build(kind,task))
                    new = gen_prompts.messages(*prompts.build(kind,task))
                    self.assertEqual(old, new)
                    old_seed = vp7.seed(task['task'],arm,sample,0)
                    new_seed = v4_prompts.seed(task['task'],arm,sample,0)
                    self.assertEqual(old_seed, new_seed)
                    key, _ = request(new,new_seed)
                    self.assertEqual(req7(old,old_seed),request(new,new_seed))
                    if (cache.cache_dir/(key+'.json')).is_file():
                        self.assertEqual(cache.chat(new,new_seed)['key'],key)
                        hits += 1
                    checks += 1
        self.assertGreater(hits,0)
        print(f'round-1 equivalence: {checks} keys, {hits} historical cache hits')

    def test_literal_calls_and_parse_errors(self):
        task = tiny_task()
        self.assertEqual(fb.literal_call('entry(y=2, x=1)',task)['call'],'entry(1, 2)')
        self.assertEqual(fb.literal_call('entry(1)',task)['input_repr'],'(1, 2)')
        for source in ['other(1)', 'entry(1+2)', 'entry(*[1])', 'entry()', 'entry(x=1,x=2)', 'entry(1,2,3)']:
            with self.assertRaises((ValueError,SyntaxError)):
                fb.literal_call(source,task)
        generated = fb.extract_calls('entry(1)\nentry(2)\nentry(1+2)\nentry(3)\nentry(4)\nentry(5)',task)
        self.assertEqual(len(generated['entries']),5)
        self.assertEqual(len(generated['candidates']),4)
        self.assertTrue(generated['errors'])

    def test_strict_filter_and_missing_expected(self):
        task = tiny_task()
        selected = [fb.literal_call('entry(1)',task),fb.literal_call('entry(2)',task)]
        missing = []
        text = ('assert entry(999) == 0\nassert entry(x=1) == 3\n'
                'assert entry(1) == 10\nassert entry(2) == __import__("os")\n'
                'assert entry(2) == 4; entry(999)\nassert entry(2) != 4')
        self.assertEqual(fb.strict_assertions(text,task,selected,missing=missing),
                         ['assert entry(1, 2) == 3','assert entry(2, 2) == None'])
        self.assertEqual(missing,['entry(2, 2)'])
        self.assertIn('do not add other assertions',fb.oracle_messages(task,selected)[1]['content'])

    def test_feedback_three_levels_and_plain_no_hint(self):
        task = tiny_task(); generated = fb.extract_calls('entry(-1)',task)
        row = dict(generated['candidates'][0], valid=False, contract_error='x >= 0', shown_hits=[False],
                   feedback=dict(hint=dict(reached_site=True,local_behavior_differs=False,output_differs=False),
                                 output_new_vs_round1=True))
        flagged = dict(records=[row],summary={})
        payload, rendered = fb.feedback(generated,flagged,{'kind':'MUTANT'},'inputs satisfying x=0 reach it')
        self.assertTrue(payload['calls'][0]['reached_site'])
        self.assertIn('x >= 0',rendered)
        self.assertIn('inputs satisfying x=0 reach it',rendered)
        plain, rendered = fb.feedback(generated,flagged,None)
        self.assertTrue(plain['calls'][0]['output_new_vs_round1'])
        self.assertNotIn('reached_site',rendered)

    def test_trigger_condition_has_no_witness_and_omits_v7(self):
        task = dict(tiny_task(),facts_version='v3m2')
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            path = Path(tmp)/'conditions.json'
            path.write_text(json.dumps([dict(task=2,text='hint',lib=dict(status='derived',descs=['x = 0']),
                                            witness_call='entry(0)')]))
            self.assertEqual(fb.trigger_condition(task,{'text':'hint'},path),'inputs satisfying x = 0 reach it')
            self.assertIsNone(fb.trigger_condition(dict(task,facts_version='v4'),{'text':'hint'},path))

    def test_seed_disjoint_and_unique(self):
        old = {v4_prompts.seed(t,a,s,stage,r,retry) for t in range(165) for a in v4_prompts.ARMS
               for s in range(3) for stage in range(4) for r in range(6) for retry in range(2)}
        new = [fb.seed(t,a,s,stage,r,retry) for t in range(165) for a in v4_prompts.ARMS if a.endswith('-hybrid')
               for s in range(3) for stage in (1,2,3) for r in range(6) for retry in range(3)]
        self.assertEqual(len(new),len(set(new)))
        self.assertFalse(old & set(new))

    def test_loop_accumulates_hits_and_matches_plain_proposals(self):
        task = tiny_task(); fact = dict(kind='OUTCOME',text='hint')
        queries = []
        def query(messages, stage, request=0, retry=0, *unused):
            queries.append(messages)
            return '\n'.join(f'entry({retry})' for _ in range(5))
        def classify(task,directory,python,*,candidates,shown,**kwargs):
            records = [dict(c,valid=True,shown_hits=[ast.literal_eval(c['input_repr'])[0]>0],
                            feedback=dict(output_new_vs_round1=True)) for c in candidates]
            return dict(records=records,summary={})
        result = fb.discover(task,'concept-hybrid',0,[],[0],[fact],query,classify,HERE,None)
        self.assertEqual(result['schedule'],[3])
        self.assertEqual(len(result['selected']),2)
        self.assertEqual(len(queries[2]),6)  # prompt + two assistant/feedback turns
        plain = fb.discover(task,'plain-hybrid',0,[],[],[],query,classify,HERE,None,
                            matched_schedule=result['schedule'])
        self.assertEqual(plain['count'],result['count'])
        self.assertEqual(len(plain['selected']),2)
        self.assertNotIn('HINT:',queries[3][1]['content'])

    def test_success_stops_early_and_empty_stops_at_three(self):
        task = tiny_task(); fact = dict(kind='OUTCOME',text='hint')
        def query(*args): return '\n'.join(f'entry({i})' for i in range(5))
        def classify(*args, candidates, **kwargs):
            return dict(records=[dict(c,valid=True,shown_hits=[True]) for c in candidates],summary={})
        success = fb.discover(task,'concept-hybrid',0,[],[0],[fact],query,classify,HERE,None)
        self.assertEqual(success['count'],1)
        self.assertEqual(len(success['selected']),2)
        def empty(*args,**kwargs): return dict(records=[],summary=dict(classification_error='timeout',first_contract_message='timeout'))
        failure = fb.discover(task,'concept-hybrid',0,[],[0],[fact],query,empty,HERE,None)
        self.assertEqual(failure['count'],3)
        self.assertEqual(failure['selected'],[])

    def test_plain_valid_keep_survives_unavailable_feedback(self):
        task = tiny_task()
        def query(*args): return 'entry(1)\nentry(2)\nentry(3)\nentry(4)\nentry(5)'
        def classify(*args,candidates,**kwargs):
            return dict(records=[dict(c,valid=True,shown_hits=[],trace_error='Timeout') for c in candidates],summary={})
        result = fb.discover(task,'plain-hybrid',0,[],[],[],query,classify,HERE,None,matched_schedule=[1])
        self.assertEqual(len(result['selected']),2)


class SandboxTests(unittest.TestCase):
    def test_spec_input_class_feedback_and_invalid_keep(self):
        task = dict(tiny_task(),put='def entry(x):\n    return x\n',
                    mined_valid_src='def valid(x):\n    return isinstance(x, int) and x <= 1500\n')
        fact = dict(kind='SPEC',text='large input',input_class=dict(cls='LARGE',param=0))
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            result = run_v4.classify(task,Path(tmp),v4_runtime.interpreter(),
                candidates=[dict(input_repr='(1000,)'),dict(input_repr='(2000,)')],shown=[fact],feedback=True)
        valid, invalid = result['records']
        self.assertTrue(valid['valid'])
        self.assertTrue(valid['shown_hits'][0])
        self.assertFalse(invalid['valid'])
        self.assertFalse(invalid['shown_hits'][0])
        self.assertTrue(invalid['feedback']['hint']['local_behavior_differs'])
        self.assertIsNone(invalid['feedback']['hint']['reached_site'])

    def test_statement_mutation_local_state_and_unreachable_site(self):
        source = 'def entry(x):\n    if x:\n        y = 1\n    return 0\n'
        task = dict(tiny_task(),put=source,mined_valid_src='def valid(x):\n    return True\n')
        fact = dict(kind='MUTANT',line=3,k=0,text='statement deletion',
                    mutant_src=source.replace('y = 1','pass'))
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            result = run_v4.classify(task,Path(tmp),v4_runtime.interpreter(),
                candidates=[dict(input_repr='(True,)'),dict(input_repr='(False,)')],shown=[fact],feedback=True)
        reached, missed = result['records']
        self.assertTrue(reached['feedback']['hint']['reached_site'])
        self.assertTrue(reached['feedback']['hint']['local_behavior_differs'])
        self.assertFalse(reached['feedback']['hint']['output_differs'])
        self.assertFalse(missed['feedback']['hint']['reached_site'])
        self.assertIsNone(missed['feedback']['hint']['local_behavior_differs'])

    def test_validator_exception_reports_violated_condition(self):
        task = dict(tiny_task(),put='def entry(x):\n    return x\n',
                    mined_valid_src='def valid(x):\n    return x >= 0\n')
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            result = run_v4.classify(task,Path(tmp),v4_runtime.interpreter(),
                candidates=[dict(input_repr="('bad',)")],feedback=True)
        self.assertFalse(result['records'][0]['valid'])
        self.assertIn('x >= 0 raised TypeError',result['records'][0]['contract_error'])

    def test_reach_infect_propagate_and_validator(self):
        task = dict(tiny_task(),put='def entry(x):\n    y = x + 1\n    return 0\n',
                    mined_valid_src='def P1_m(x):\n    return x >= 0\ndef P1(x):\n    return P1_m(x)\ndef valid(x):\n    return P1(x) is True\n')
        fact = dict(kind='MUTANT',line=2,k=0,text='mutation',mutant_src=task['put'].replace('x + 1','x + 2'))
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            result = run_v4.classify(task,Path(tmp),v4_runtime.interpreter(),
                candidates=[dict(input_repr='(0,)'),dict(input_repr='(-1,)')],shown=[fact],feedback=True)
        self.assertNotIn('classification_error',result['summary'])
        first, invalid = result['records']
        self.assertEqual(first['feedback']['hint']['reached_site'],True)
        self.assertEqual(first['feedback']['hint']['local_behavior_differs'],True)
        self.assertEqual(first['feedback']['hint']['output_differs'],False)
        self.assertFalse(first['shown_hits'][0])
        self.assertFalse(invalid['valid'])
        self.assertIn('x >= 0',invalid['contract_error'])

    def test_output_novelty_and_boundary_compared_values(self):
        task = dict(tiny_task(),put='def entry(x):\n    if x < 2:\n        return x\n    return 2\n')
        from . import tracer
        _,sites = tracer.instrument(task['put'])
        sid = next(k for k,s in enumerate(sites) if s.get('line')==2 and s.get('kind')=='cond')
        fact = dict(kind='OUTCOME',line=2,cell=[sid,'T'],text='branch')
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            result = run_v4.classify(task,Path(tmp),v4_runtime.interpreter(),
                candidates=[dict(input_repr='(1,)')],shown=[fact],feedback=True,
                reference_outputs=[dict(status='ok',value='1')])
        row = result['records'][0]
        self.assertFalse(row['feedback']['output_new_vs_round1'])
        self.assertTrue(row['feedback']['hint']['local_behavior_differs'])
        self.assertIn(['left','1'],row['feedback']['hint']['compared_values'])

    def test_three_dev_tasks_all_seven_arms(self):
        summary = dry_run.execute()
        self.assertEqual(summary['rows'],21)
        self.assertEqual(summary['tasks'],[2,3,4])
        self.assertTrue(any(r['round2_proposal_requests']>1 for r in summary['hybrid']))

    def test_skip_empty_oracle_and_separate_oracle_budgets(self):
        summary = dry_run.execute(client=dry_run.ScriptedClient(empty_target=True))
        for task in (2,3,4):
            concept = next(r for r in summary['hybrid'] if r['task']==task and r['arm']=='concept-hybrid')
            plain = next(r for r in summary['hybrid'] if r['task']==task and r['arm']=='plain-hybrid')
            self.assertEqual(concept['kept'],0)
            self.assertEqual(concept['round2_oracle_requests'],0)
            self.assertEqual(plain['round2_proposal_requests'],concept['round2_proposal_requests'])
            self.assertEqual(plain['round2_oracle_requests'],1)


if __name__ == '__main__':
    with patch.object(socket,'create_connection',side_effect=AssertionError('network forbidden')):
        unittest.main(verbosity=2)
