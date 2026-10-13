"""Offline generation integration tests: fake responses, no endpoint or secrets."""
import contextlib
import json
import socket
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from . import paths, run_v4, scorer, fair_generation, v8_strict_est, v4_evaluation, oracle_b01
from .offline_client import OfflineClient, CacheMiss


class FakeClient:
    model = paths.CONFIG['model']

    def __init__(self, n_assertions=1):
        self.requests = []
        self.n_assertions = n_assertions

    def chat(self, messages, seed, **kwargs):
        self.requests.append((messages, seed))
        if 'Hypothesis' in messages[0]['content']:
            text = 'def strategy():\n    return st.just((100,))'
        elif 'sample_one' in messages[0]['content']:
            text = 'def sample_one():\n    return (100,)'
        elif 'For EXACTLY' in messages[-1]['content']:
            # Deliberately over-generate and reverse order: strict must constrain it.
            text = 'assert f(999) == 999\nassert f(101) == 101\nassert f(100) == 100'
        else:
            text = '\n'.join(f'assert f({i}) == {i}' for i in range(self.n_assertions))
        return dict(text=text,n_in=1,n_out=1,seconds=0,key=str(seed))


def task():
    valid = 'def valid(x):\n    return True\n'
    strategy = 'def strategy():\n    return st.just((100,))\n'
    facts = [dict(kind='SPEC',text=f'hint {i}',witness_call=None) for i in range(3)]
    return dict(task=0,entry='f',put='def f(x):\n    """Return x."""\n    return x\n',base='def check(candidate):\n    pass\n',
                split='dev',doc_fail=False,facts_version='v4',mined_valid_src=valid,
                valid_sha256=run_v4.preconditions.sha(valid),strategy_src=strategy,
                strategy_sha256=run_v4.preconditions.sha(strategy),concept_meta=facts,placebo_meta=facts,
                concept_facts=[f['text'] for f in facts],placebo_facts=[f['text'] for f in facts],tool_inputs=[])


class FairTests(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(socket.socket,'connect',side_effect=AssertionError('network forbidden')))
        self.stack.enter_context(patch.object(socket,'create_connection',side_effect=AssertionError('network forbidden')))

    def generate(self, *, n_assertions=1, good=True, failed_concept=False, covered_placebo=False, flags=None, no_placebo=False, n_hints=3):
        flags = flags or {key:True for key in paths.FAIR_FLAGS}
        self.stack.enter_context(patch.dict(paths.CONFIG,flags))
        def classify(t,directory,python,*,candidates=None,assertions=None,shown=(),requested_draws=None):
            records=[] if assertions is not None else [dict(input_repr='(100,)',call='f(100)',valid=good,shown_hits=[good]*len(shown)),
                                                       dict(input_repr='(101,)',call='f(101)',valid=good,shown_hits=[good]*len(shown))]
            hits=[int(covered_placebo and 'placebo-hybrid' in str(directory))]*len(shown)
            summary=dict(shown_hit_counts=hits,valid=sum(r['valid'] for r in records),removed=0)
            return dict(records=records,summary=summary)
        def draws(code,t,directory,python,seed):
            if failed_concept and 'concept-hybrid' in str(directory):
                raise ValueError('fake verification rejection')
            return dict(candidates=[],nonliteral=0,wrong_arity=0,errors=[])
        client=FakeClient(n_assertions)
        t=task()
        if n_hints != 3:
            hints=[dict(kind='SPEC',text=f'hint {i}',witness_call=None) for i in range(n_hints)]
            t.update(concept_meta=hints,placebo_meta=hints,concept_facts=[f['text'] for f in hints],placebo_facts=[f['text'] for f in hints])
        if no_placebo: t.update(placebo_meta=[],placebo_facts=[])
        with tempfile.TemporaryDirectory(dir=paths.HERE) as directory, \
             patch.object(run_v4,'safe_path',side_effect=Path), \
             patch.object(run_v4.v4_runtime,'interpreter',return_value=Path('/usr/bin/python3')), \
             patch.object(run_v4,'classify',side_effect=classify), \
             patch.object(run_v4.v4_strategies,'draws',side_effect=draws), \
             patch.object(run_v4.gen_inputs,'extract_generator',return_value='def sample_one(): return (100,)'), \
             patch.object(run_v4.gen_inputs,'generate_candidates',return_value=dict(candidates=[],errors=[])), \
             patch.object(run_v4.gen_inputs,'feedback',return_value=None):
            run_v4.run([t],directory,Path('/usr/bin/python3'),client=client,k=1,workers=1)
            rows=[json.loads(line) for line in (Path(directory)/'gen.jsonl').read_text().splitlines()]
        return {r['arm']:r for r in rows},client

    def test_strict_empty_skips_expected_call(self):
        rows,_=self.generate(good=False)
        for arm in ('concept-hybrid','placebo-hybrid','plain-hybrid'):
            row=rows[arm]
            self.assertEqual(row['selected_inputs'],[])
            self.assertEqual(row['llm_calls'],1+row['round2_strategy_requests'])
            self.assertEqual(row['assertions'],row['round1_assertions'])

    def test_strict_matches_cpu_construction_and_prompt(self):
        rows,client=self.generate()
        for arm in ('concept-hybrid','placebo-hybrid','plain-hybrid'):
            row=rows[arm]
            self.assertNotIn('assert f(999) == 999',row['assertions'])
            self.assertEqual(row['assertions'],v8_strict_est.strict(row,'f')[0])
            self.assertEqual(row['assertions'][-2:],[f"assert {r['call']} == {r['input_repr'].strip('(),')}" for r in row['selected_inputs']])
        prompts=[m[-1]['content'] for m,_ in client.requests if 'For EXACTLY' in m[-1]['content']]
        self.assertEqual(len(prompts),3)
        for prompt in prompts:
            self.assertNotIn('you may add',prompt)
            self.assertNotIn('up to 10',prompt)
            self.assertEqual(set(prompt.splitlines()[-2:]),{'f(100)','f(101)'})

    def test_placebo_matches_retry_count_even_if_hints_covered(self):
        rows,_=self.generate(failed_concept=True,covered_placebo=True)
        self.assertEqual(rows['concept-hybrid']['round2_strategy_requests'],6)
        for arm in ('placebo-hybrid','plain-hybrid'):
            self.assertEqual(rows[arm]['round2_strategy_requests'],6)
            self.assertEqual(rows[arm]['matched_strategy_requests'],6)
        self.assertTrue(all(a['fact_index'] is not None for a in rows['placebo-hybrid']['generator_attempts']))

    def test_placebo_empty_hints_still_matches(self):
        rows,_=self.generate(no_placebo=True)
        self.assertEqual(rows['placebo-hybrid']['round2_strategy_requests'],rows['concept-hybrid']['round2_strategy_requests'])

    def test_caps_drop_twenty_first_in_generation_order(self):
        rows,_=self.generate(n_assertions=21)
        for row in rows.values():
            self.assertLessEqual(row['llm_calls'],8)
            self.assertLessEqual(row['n_assertions'],20)
        for arm in ('plain','concept','placebo-hybrid'):
            self.assertEqual(rows[arm]['assertions'],[f'assert f({i}) == {i}' for i in range(20)])
            self.assertGreaterEqual(rows[arm]['dropped_assertions'],1)
        self.assertEqual(rows['plain']['dropped_assertions'],1)
        self.assertEqual(rows['concept-hybrid']['dropped_assertions'],1)
        self.assertEqual(rows['concept-hybrid']['dropped_round2_inputs'],2)
        self.assertEqual(rows['concept-hybrid']['llm_calls'],1+rows['concept-hybrid']['round2_strategy_requests'])

    def test_legacy_completion_limit_and_no_new_fields(self):
        rows,_=self.generate(n_assertions=21,flags={key:False for key in paths.FAIR_FLAGS})
        self.assertEqual(rows['plain']['n_assertions'],10)
        for row in rows.values():
            self.assertNotIn('dropped_assertions',row)
            self.assertNotIn('strict_round2',row)

    def test_missing_expected_and_seen_input(self):
        first=['assert f(100) == 100']
        selected=[dict(call='f(100)'),dict(call='f(101)')]
        result,missing=fair_generation.strict_assertions(first,selected,['assert f(999) == 999'],'f')
        self.assertEqual(result,first+['assert f(101) == None'])
        self.assertEqual(missing,1)

    def test_cache_miss_raises(self):
        with tempfile.TemporaryDirectory(dir=paths.HERE) as directory:
            with self.assertRaises(CacheMiss): OfflineClient(directory).chat([],0)

    def test_caps_limit_large_hint_pool_and_retries(self):
        rows,_=self.generate(n_hints=10,failed_concept=True)
        for row in rows.values(): self.assertLessEqual(row['llm_calls'],8)
        for arm in ('concept-hybrid','placebo-hybrid','plain-hybrid'):
            self.assertEqual(rows[arm]['round2_strategy_requests'],6)

    def test_strict_rejects_additional_put_calls(self):
        final,missing=fair_generation.strict_assertions([], [dict(call='f(100)')],
                                                       ['assert f(100) == f(999)'],'f')
        self.assertEqual(final,['assert f(100) == None'])
        self.assertEqual(missing,1)

    def test_chained_equalities_preserve_short_circuit(self):
        calls=[]
        def f(x): calls.append(x); return float(x)
        ns=dict(f=f,__fair_equal__=lambda a,b:scorer.output_equal(a,b,1e-4))
        exec(scorer.assertion_code('assert f(1) == 1.00001 == f(1)'),ns)
        self.assertEqual(calls,[1,1])
        calls.clear()
        with self.assertRaises(AssertionError):
            exec(scorer.assertion_code('assert f(1) == 3 == f(2)'),ns)
        self.assertEqual(calls,[1])

    def test_tolerance_does_not_change_argument_construction(self):
        inputs=[]
        def f(value): inputs.append(value); return 1.0
        ns=dict(f=f,__fair_equal__=lambda a,b:scorer.output_equal(a,b,1e-4))
        exec(scorer.assertion_code('assert f([x for x in [1.0,1.00001] if x == 1.0]) == 1.00001'),ns)
        self.assertEqual(inputs,[[1.0]])

    def test_shared_scorer_in_actual_evaluation_worker(self):
        t=task(); t.update(concept_meta=[],placebo_meta=[],put='def f(x):\n    return {"x": [2.002]}\n')
        job=dict(task=t,canon='def f(x):\n    return {"x": [2.0]}\n',
                 contract_src='def f(x):\n    pass\n',atol=0.003,
                 rows=[dict(task=0,arm='plain',sample=0,text='',assertions=['assert f(0) == {"x": [2.0]}'])])
        for enabled in (False,True):
            with tempfile.TemporaryDirectory(dir=paths.HERE) as directory, patch.dict(paths.CONFIG,shared_scorer=enabled):
                row=run_v4.v4_runtime.isolated('evaluate',job,directory)[0]
            self.assertEqual(row['asserts'][0]['canon'],'ok')
            self.assertEqual(row['asserts'][0]['put'],'ok' if enabled else 'fail')
            if enabled:
                self.assertFalse(row['input_metrics'][0]['d_i'])
                self.assertFalse(row['asserts'][0]['d_io'])

    def test_shared_scorer_in_actual_oracle_worker(self):
        job=dict(entry='f',put='def f(x):\n    return {"x": [2.002]}',
                 canon='def f(x):\n    return {"x": [2.0]}',base='def check(candidate):\n    pass',
                 contract='def f(x):\n    pass',spec='def f(x):\n    """Return 2."""',
                 dpp=[],tc=[],ref=[f'def f(x):\n    return {{"x": [{v}]}}' for v in (2.0,2.001,2.002)],
                 post=[],mutants=[],calls=['f(0)'],b1={'f(0)':['{"x": [2.0]}']*5},
                 o0={'f(0)':['{"x": [2.0]}']},atol=0.003)
        for enabled in (False,True):
            with tempfile.TemporaryDirectory(dir=paths.HERE) as directory, patch.dict(paths.CONFIG,shared_scorer=enabled):
                jp,op=Path(directory)/'job.json',Path(directory)/'result.json'
                jp.write_text(json.dumps(job))
                process=subprocess.run(['unshare','-rn',paths.CONFIG['V4_PYTHON'],'-I','-B',
                                        str(paths.HERE/'oracle_b01.py'),'worker',str(jp),str(op)],
                                       env=paths.worker_env(),capture_output=True,text=True)
                self.assertEqual(process.returncode,0,process.stderr)
                result=json.loads(op.read_text())['calls']['f(0)']
            self.assertEqual(result['ref']['emit'],enabled)
            self.assertEqual(result['b1']['put_ok'],enabled)
            if enabled: self.assertFalse(result['d_i'])

    def test_recursive_tolerance_and_outcomes(self):
        self.assertTrue(scorer.output_equal({'x':[1.0,(2.0,)]},{'x':[1.000001,(2.000001,)]},1e-5))
        self.assertFalse(scorer.output_equal([1.0],(1.0,),1e-5))
        self.assertFalse(scorer.output_equal(1.0,1.01,1e-5))
        self.assertFalse(scorer.output_equal(float('nan'),float('nan')))
        self.assertTrue(scorer.outcome_equal(('timeout',None),('Timeout',None)))
        self.assertFalse(scorer.outcome_equal(('ValueError',None),('Timeout',None)))
        self.assertFalse(scorer.outcome_equal(('ValueError',None),('ok',None)))

    def test_metrics_denominator_includes_invalid_failures(self):
        rows=[dict(arm='plain',input_metrics=[dict(d_i=True)],asserts=[
            dict(put='fail',canon='ok',contract_valid=True,d_io=True),
            dict(put='fail',canon='ok',contract_valid=False,d_io=False),
            dict(put='ok',canon='fail',contract_valid=True,d_io=False)])]
        m=scorer.arm_metrics(rows)['plain']
        self.assertEqual((m['D_I'],m['D_IO'],m['precision']),(1,1,0.5))
        self.assertEqual((m['false_alarms'],m['false_alarm_rate']),(1,0.5))

    def test_oracle_metrics_use_own_expected_and_contract(self):
        assertions=[dict(src=f'assert f({x}) == 2',canon='ok',put='fail') for x in (0,1)]
        records={f'f({x})':dict(valid=x==0,d_i=x==0,o0_values={'2':dict(canon_ok=True,put_ok=False)},
                              ref=dict(emit=True,canon_ok=True,put_ok=False)) for x in (0,1)}
        with patch.dict(paths.CONFIG,shared_scorer=True):
            m=oracle_b01.fairness_metrics({0:dict(entry='f')},[dict(task=0,arm='plain',sample=0,asserts=assertions)],
                                         {'0':dict(calls=records)},{})['plain']
        self.assertEqual(m['D_I'],1)
        for oracle in ('o0','ref','full'):
            self.assertEqual(m['oracles'][oracle]['D_IO'],1)
            self.assertEqual(m['oracles'][oracle]['precision'],0.5)

    def test_tolerance_metadata_is_shared(self):
        with tempfile.TemporaryDirectory(dir=paths.HERE) as directory:
            p=Path(directory)/'tasks.jsonl'
            p.write_text(json.dumps(dict(task_id='HumanEval/0',atol=0.002))+'\n')
            self.assertEqual(scorer.task_atols(p),{0:0.002})


if __name__=='__main__': unittest.main()
