"""Schema adversaries and real sandbox checks; no model effectiveness is simulated."""
import ast
import copy
import json
import tempfile
import sys
import unittest
from unittest.mock import patch
from pathlib import Path
from . import experiment, experiment_schema as schema, preconditions


def task(mr=False):
    if mr:
        source='def f(xs):\n    """Return the sum of all items."""\n    return sum(xs[:1])\n'
        base='def check(candidate):\n    assert candidate([1]) == 1\n'
        valid='def valid(xs):\n    return isinstance(xs, list) and all(isinstance(x, int) for x in xs)\n'
        strategy='def strategy():\n    return st.tuples(st.lists(st.integers(0, 4), min_size=2, max_size=4))\n'
    else:
        source=('def f(x):\n    """Return x plus one."""\n    value = x + 1\n'
                '    if x > 50:\n        return value + 1\n    return value\n')
        base='def check(candidate):\n    assert candidate(1) == 2\n'
        valid='def valid(x):\n    return isinstance(x, int) and -1000 <= x <= 1000\n'
        strategy='def strategy():\n    return st.tuples(st.integers(-1000, 1000))\n'
    return dict(task=0,entry='f',put=source,base=base,split='dev',mined_valid_src=valid,strategy_src=strategy,
                concept_meta=[] if mr else [dict(kind='STMT',line=5,lines=[5],witness_call='f(100)',text='line 5 not covered')],
                placebo_meta=[],tool_inputs=[],facts_version='v4',
                valid_sha256=preconditions.sha(valid),strategy_sha256=preconditions.sha(strategy))


def prepared(t):
    # Minimal tool-evidence fixture: two observed def-use edges and one enclosing guard.
    sites=[dict(line=i,covered=True,data=[],control=[]) for i in (1,3,4,5,6)]
    sites[2]['data']=[dict(definition=1,name='x',kind='p-use')]
    sites[3]['data']=[dict(definition=3,name='value',kind='c-use')]
    sites[3]['control']=[dict(line=4,condition='x > 50',outcome='T')]
    candidates=dict(sites=sites,base_ok=True,base_trace_statuses={},survivor_mutants=[])
    return dict(graph=schema.graph(t,candidates),candidates=candidates)


def graph_raw(p,trigger='x > 50'):
    g=p['graph'];edge=next(e['id'] for e in g['edges'].values() if e['source']=='L3' and e['target']=='L5')
    concept=next(c['id'] for c in g['concepts'].values() if c['site']=='L5')
    return dict(clause_id='R1',family='STRICT_BOUNDARY',concept_ids=[concept],path=[edge],
                T=trigger,O='def obligation(args, result):\n    return result == args[0] + 1',
                alternative='extra one added after the value computation')


def mr_raw(tau='def transform(args):\n    return (list(reversed(args[0])),)'):
    return dict(clause_id='R1',family='PERMUTATION',parameter=0,D='len(xs) > 1',tau=tau,
                rho='def relation(args, followup_args, result, followup_result):\n    return result == followup_result')


class SchemaTests(unittest.TestCase):
    def test_disconnected_or_unknown_path_rejected(self):
        t=task();p=prepared(t);r=graph_raw(p)
        r['path']=['E999']
        cards,failures=schema.parse(json.dumps([r]),t,p['graph'],'obgraph')
        self.assertFalse(cards);self.assertEqual(len(failures),1)
        r=graph_raw(p);r['path']=[next(e['id'] for e in p['graph']['edges'].values() if e['target']=='L4')]+r['path']
        self.assertFalse(schema.parse(json.dumps([r]),t,p['graph'],'obgraph')[0])

    def test_concept_anchor_and_return_endpoint_required(self):
        t=task();p=prepared(t);r=graph_raw(p)
        r['concept_ids']=[next(c['id'] for c in p['graph']['concepts'].values() if c['site']=='L1')]
        self.assertFalse(schema.parse(json.dumps([r]),t,p['graph'],'obgraph')[0])
        r=graph_raw(p);r['path']=[next(e['id'] for e in p['graph']['edges'].values() if e['target']=='L4')]
        r['concept_ids']=[next(c['id'] for c in p['graph']['concepts'].values() if c['site']=='L4')]
        self.assertFalse(schema.parse(json.dumps([r]),t,p['graph'],'obgraph')[0])

    def test_generated_mutation_import_and_put_call_rejected(self):
        for code in ('def transform(args):\n    args[0][0] = 5\n    return args',
                     'def transform(args):\n    import os\n    return args',
                     'def transform(args):\n    return f(args)'):
            with self.assertRaises(ValueError):schema.pure(code,'transform',('args',))

    def test_duplicate_proposals_do_not_take_multiple_slots(self):
        t=task();p=prepared(t);r=graph_raw(p)
        cards,failures=schema.parse(json.dumps([r,r]),t,p['graph'],'obgraph')
        self.assertEqual(len(cards),1);self.assertIn('duplicate_card',failures[0]['error'])

    def test_no_witness_leak_and_same_evidence_cards(self):
        t=task();p=prepared(t);card=schema.parse(json.dumps([graph_raw(p)]),t,p['graph'],'obgraph')[0][0]
        card['witness']=dict(input_repr='(987654321,)')
        for arm in ('graph-strategy','card-strategy','graph-noconcept'):
            self.assertNotIn('987654321',schema.visible(card,arm))
        graph=json.loads(schema.visible(card,'graph-strategy'));flat=json.loads(schema.visible(card,'card-strategy'))
        self.assertEqual(sorted(graph.pop('connected_path'),key=lambda e:e['id']),flat.pop('unordered_evidence'))
        self.assertEqual(graph,flat)


class SandboxTests(unittest.TestCase):
    def sandbox(self,mode,job):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            return experiment.isolated(mode,job,Path(d))

    def test_tool_extracted_path_hits_and_trigger_is_insufficient(self):
        t=task();p=self.sandbox('prepare',dict(task=t))
        r=graph_raw(p);card=schema.parse(json.dumps([r]),t,p['graph'],'obgraph')[0][0]
        result=self.sandbox('select',dict(task=t,method='obgraph',card=card,
                    candidates=[dict(input_repr='(100,)'),dict(input_repr='(1,)')]))
        self.assertTrue(result['records'][0]['eligible']);self.assertTrue(result['records'][0]['potential_violation'])
        self.assertFalse(result['records'][1].get('eligible',False))
        r=graph_raw(p,trigger='x <= 50')
        card=schema.parse(json.dumps([r]),t,p['graph'],'obgraph')[0][0]
        result=self.sandbox('select',dict(task=t,method='obgraph',card=card,candidates=[dict(input_repr='(1,)')]))
        self.assertTrue(result['records'][0]['trigger_hit']);self.assertFalse(result['records'][0]['path_hit'])
        self.assertFalse(result['records'][0].get('eligible',False))

    def test_base_trigger_hit_does_not_discard_obligation(self):
        t=task();p=prepared(t);r=graph_raw(p,trigger='x >= 0')
        cards=schema.parse(json.dumps([r]),t,p['graph'],'obgraph')[0]
        result=self.sandbox('check',dict(task=t,method='obgraph',cards=cards,prepared=p,seed=20261014))
        self.assertEqual(len(result['cards']),1);self.assertEqual(result['cards'][0]['base_trigger_hits'],1)

    def test_keyword_base_calls_are_used_for_consistency(self):
        t=task();t['base']='def check(candidate):\n    assert candidate(x=1) == 2\n'
        p=prepared(t);r=graph_raw(p,trigger='x >= 0')
        cards=schema.parse(json.dumps([r]),t,p['graph'],'obgraph')[0]
        result=self.sandbox('check',dict(task=t,method='obgraph',cards=cards,prepared=p,seed=20261014))
        self.assertEqual(result['cards'][0]['base_trigger_hits'],1)
        r['O']='def obligation(args, result):\n    return result == args[0] + 2'
        cards=schema.parse(json.dumps([r]),t,p['graph'],'obgraph')[0]
        result=self.sandbox('check',dict(task=t,method='obgraph',cards=cards,prepared=p,seed=20261014))
        self.assertFalse(result['cards']);self.assertIn('contradicted',result['failures'][0]['error'])

    def test_mr_pair_validity_identity_and_permutation_multiset(self):
        t=task(True);g=dict(clauses={'R1':'Return the sum of all items.'})
        card=schema.parse(json.dumps([mr_raw()]),t,g,'mr')[0][0]
        result=self.sandbox('select',dict(task=t,method='mr',card=card,
                    candidates=[dict(input_repr='([1, 2],)'),dict(input_repr='([1, 1],)')]))
        self.assertTrue(result['records'][0]['eligible']);self.assertEqual(result['records'][0]['followup_repr'],'([2, 1],)')
        self.assertTrue(result['records'][0]['potential_violation'])
        self.assertFalse(result['records'][1].get('eligible',False))
        bad=mr_raw('def transform(args):\n    return (args[0] + [1],)')
        card=schema.parse(json.dumps([bad]),t,g,'mr')[0][0]
        result=self.sandbox('select',dict(task=t,method='mr',card=card,candidates=[dict(input_repr='([1, 2],)')]))
        self.assertFalse(result['records'][0].get('eligible',False))

    def test_mr_failure_on_buggy_untested_put_is_kept(self):
        t=task(True);g=dict(clauses={'R1':'Return the sum of all items.'})
        cards=schema.parse(json.dumps([mr_raw()]),t,g,'mr')[0]
        result=self.sandbox('check',dict(task=t,method='mr',cards=cards,prepared={},seed=20261014))
        self.assertEqual(len(result['cards']),1);self.assertGreater(result['cards'][0]['potential_violations'],0)

    def test_property_scoring_separates_confirmed_report_from_false_alarm(self):
        t=task(True);g=dict(clauses={'R1':'Return the sum of all items.'})
        card=schema.parse(json.dumps([mr_raw()]),t,g,'mr')[0][0]
        job=dict(task=t,method='mr',canon='def f(xs):\n    return sum(xs)',contract_src='def f(xs):\n    assert isinstance(xs,list)',
                 samples=[dict(arm='mr-strategy',sample=0,selected=[dict(card=card,input_repr='([1, 2],)',followup_repr='([2, 1],)')])])
        result=self.sandbox('property_score',job)['records'][0]
        self.assertTrue(result['confirmed_report']);self.assertFalse(result['false_alarm'])
        wrong=mr_raw('def transform(args):\n    return (args[0] + [1],)');wrong['family']='MULTIPLICITY'
        wrong['rho']='def relation(args, followup_args, result, followup_result):\n    return followup_result == result + 2'
        card=schema.parse(json.dumps([wrong]),t,g,'mr')[0][0]
        job['samples'][0]['selected']=[dict(card=card,input_repr='([1, 2],)',followup_repr='([1, 2, 1],)')]
        result=self.sandbox('property_score',job)['records'][0]
        self.assertTrue(result['false_alarm']);self.assertFalse(result['confirmed_report'])

    def test_mismatched_followup_is_not_scored_as_relation_evidence(self):
        t=task(True);g=dict(clauses={'R1':'Return the sum of all items.'})
        card=schema.parse(json.dumps([mr_raw()]),t,g,'mr')[0][0]
        job=dict(task=t,method='mr',canon='def f(xs): return sum(xs)',contract_src='def f(xs): pass',
                 samples=[dict(arm='mr-strategy',sample=0,selected=[dict(card=card,input_repr='([1, 2],)',followup_repr='([9],)')])])
        self.assertEqual(self.sandbox('property_score',job)['records'],[])


class DriverTests(unittest.TestCase):
    def test_zero_card_gate_never_generates_or_scores_fallback(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            root=Path(d);q=root/'proposals/accounting.json';q.parent.mkdir(parents=True)
            q.write_text(json.dumps(dict(shown=0)))
            with patch.object(experiment,'ROOT',root),patch.object(sys,'argv',['experiment','all']), \
                 patch.object(experiment,'prepare'),patch.object(experiment,'verify_protocol'), \
                 patch.object(experiment,'client'),patch.object(experiment,'propose'), \
                 patch.object(experiment,'generate') as generate,patch.object(experiment,'oracle') as oracle, \
                 patch.object(experiment,'score') as score:
                experiment.main()
                generate.assert_not_called();oracle.assert_not_called();score.assert_not_called()
                self.assertTrue(json.loads((root/'mechanism_gate.json').read_text())['blocked'])
    def test_missing_offline_response_is_not_fabricated_as_empty_answer(self):
        from .offline_client import OfflineClient,CacheMiss
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            root=Path(d);q=root/'proposals/0/summary.json';q.parent.mkdir(parents=True)
            q.write_text(json.dumps(dict(shown=[])))
            with patch.object(experiment,'ROOT',root):
                with self.assertRaises(CacheMiss):experiment.sample(task(),'plain-strategy',0,OfflineClient(root/'cache'))
            self.assertFalse((root/'generation/samples/0/plain-strategy/0/summary.json').exists())

    def test_real_draw_adapter_fixed_calls_resume_and_pair_budget(self):
        # A fixed transport fixture exercises our scheduler, not a simulation of any paper/model.
        class Transport:
            def __init__(self):self.calls=[]
            def chat(self,messages,seed,**kwargs):
                self.calls.append(seed)
                return dict(text='def strategy():\n    return st.tuples(st.lists(st.integers(0, 4), min_size=2, max_size=4))',
                            n_in=50,n_out=25,cache_hit=False)
        t=task(True);g=dict(clauses={'R1':'Return the sum of all items.'})
        card=schema.parse(json.dumps([mr_raw()]),t,g,'mr')[0][0]
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            root=Path(d)
            q=root/'proposals/0/summary.json';q.parent.mkdir(parents=True);q.write_text(json.dumps(dict(shown=[card])))
            cfg=dict(experiment.CFG,max_input_calls=3)
            with patch.object(experiment,'ROOT',root),patch.object(experiment,'METHOD','mr'),patch.object(experiment,'CFG',cfg):
                c=Transport();r=experiment.sample(t,'mr-strategy',0,c)
                self.assertEqual(r['llm_calls'],3);self.assertEqual(len(c.calls),3)
                self.assertLessEqual(r['input_calls'],3)
                calls=set(r['assertions'])
                self.assertTrue(any(pair.get('followup_repr') for pair in r['selected']))
                for pair in r['selected']:
                    if not pair.get('followup_repr'):continue  # empty guidance slots use generic singleton inputs
                    for literal in (pair['input_repr'],pair['followup_repr']):
                        args=ast.literal_eval(literal)
                        self.assertIn('assert f('+', '.join(repr(a) for a in args)+') == None',calls)
                again=experiment.sample(t,'mr-strategy',0,c)
                self.assertEqual(again,r);self.assertEqual(len(c.calls),3)
                blind=experiment.sample(t,'mr-blind',0,c)
                self.assertEqual(r['assertions'],blind['assertions'])
                self.assertEqual(c.calls[:3],c.calls[3:])


if __name__=='__main__':unittest.main()
