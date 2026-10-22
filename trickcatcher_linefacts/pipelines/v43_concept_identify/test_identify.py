"""Artificial control regressions only: no diagnostic/model/native execution."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx

from . import identify as app, identify_tools as tools
from .d1_client import Client, TransportStop
from .flow_common import write_json


def observation(arguments, output=None, exception=None, name='O1'):
    return {'id':name,'input':repr(arguments),'execution_status':'exception' if exception else 'ok',
            'output':repr(output) if not exception else None,'exception_type':exception,'output_capture':'literal'}


def binding(relation, arguments=None, concept='eligible_contribution', quote='requirement'):
    return {'id':'B1','concept':concept,'relation':relation,
            'arguments':['xs'] if arguments is None else arguments,'spec_quote':quote}


class RelationTests(unittest.TestCase):
    def test_occurrence_and_order_are_independent(self):
        row=observation(([2,1,2],),[1,2])
        self.assertFalse(tools.compare(binding('preserve_occurrences'),row,['xs'])['holds_on_observation'])
        self.assertTrue(tools.compare(binding('ascending'),row,['xs'])['holds_on_observation'])

    def test_membership_direction_and_extras(self):
        row=observation(([1,2],[1]),False)
        args=['container','required'];params=['container','required']
        self.assertFalse(tools.compare(binding('required_subset_container',args),row,params)['holds_on_observation'])
        self.assertTrue(tools.compare(binding('equal_sets',args),row,params)['holds_on_observation'])
        reverse=tools.compare(binding('required_subset_container',args[::-1]),row,params)
        self.assertTrue(reverse['holds_on_observation'])  # Direction changes the candidate, not spec truth.

    def test_eligibility_and_multiplicity_are_separate(self):
        one=observation(([1,2],),2)
        repeat=observation(([2,2],),2)
        self.assertFalse(tools.compare(binding('sum_positive'),one,['xs'])['holds_on_observation'])
        self.assertTrue(tools.compare(binding('sum_gt_one'),one,['xs'])['holds_on_observation'])
        self.assertFalse(tools.compare(binding('sum_gt_one'),repeat,['xs'])['holds_on_observation'])
        self.assertTrue(tools.compare(binding('sum_distinct_gt_one'),repeat,['xs'])['holds_on_observation'])

    def test_exception_is_not_return_none(self):
        exception=observation(([-1,0],),exception='ValueError')
        normal=observation(([-1,0],),None)
        self.assertFalse(tools.compare(binding('min_positive_none'),exception,['xs'])['holds_on_observation'])
        self.assertTrue(tools.compare(binding('min_positive_raise'),exception,['xs'])['holds_on_observation'])
        self.assertFalse(tools.compare(binding('min_positive_raise'),normal,['xs'])['holds_on_observation'])
        self.assertTrue(tools.compare(binding('min_positive_none'),normal,['xs'])['holds_on_observation'])

    def test_bool_is_not_integer_count(self):
        row=observation(([2],2),True)
        self.assertFalse(tools.compare(binding('count_ge',['xs','limit']),row,['xs','limit'])['holds_on_observation'])

    def test_unknown_bad_roles_and_extra_args(self):
        row=observation(([2],),2)
        for b in (binding('unknown',[]),binding('sum_positive',['absent']),binding('sum_positive',['xs','xs'])):
            self.assertEqual(tools.compare(b,row,['xs'])['status'],'unknown')

    def test_unusable_observation_is_not_candidate_refutation(self):
        for status,capture in [('timeout','literal'),('ok','opaque')]:
            row=observation(([1],),[1]);row.update(execution_status=status,output_capture=capture)
            self.assertEqual(tools.compare(binding('preserve_occurrences'),row,['xs'])['status'],'unknown')

    def test_mechanical_quality_is_not_semantic_entailment(self):
        b=binding('sum_gt_one',concept='membership_inclusion',quote='missing quote')
        flags=tools.binding_checks(b,['xs'],'requirement')
        self.assertFalse(flags['quote_is_nonempty_exact_spec_substring'])
        self.assertFalse(flags['concept_relation_vocabulary_compatible'])
        self.assertIn('unverified',flags['spec_entailment'])
        # Still inspect the candidate instead of dropping it as a normative gate.
        self.assertTrue(tools.compare(b,observation(([2],),2),['xs'])['holds_on_observation'])


class EvidenceTests(unittest.TestCase):
    def test_changed_value_is_not_changed_satisfaction(self):
        rows=[observation(([1],),[1],name='O1'),observation(([2],),[2],name='O2')]
        b=binding('preserve_occurrences')
        matrix={r['id']:{'B1':tools.compare(b,r,['xs'])} for r in rows}
        result=tools.contrast(rows,matrix)
        self.assertEqual(result['pairs'][0]['changed_candidates'],[])
        self.assertEqual(result['pairs'][0]['only_changed_argument'],0)

    def test_no_pair_is_only_finite_pool_absence(self):
        row=observation(([1],),1)
        result=tools.contrast([row],{'O1':{'B1':{'status':'unknown'}}})
        self.assertEqual(result['found'],0)
        self.assertIn('not infeasibility',result['no_pair_means'])

    def test_unused_local_vs_return_use(self):
        unused=tools.return_dependencies('def f(xs):\n temporary=set(xs)\n return sorted(xs)\n')
        used=tools.return_dependencies('def f(xs):\n temporary=set(xs)\n return sorted(temporary)\n')
        self.assertEqual(unused['unreferenced_top_level_targets'],['temporary'])
        self.assertEqual(used['unreferenced_top_level_targets'],[])
        self.assertIn('NOT sound',unused['scope'])
        branch=tools.return_dependencies('def f(xs):\n if xs:\n  return 1\n return 0\n')
        self.assertTrue(branch['control_or_nested_scope_present'])

    def test_tool_error_does_not_remove_valid_sibling(self):
        result=tools.tools([binding('sum_positive')],[observation(([2],),2)],['xs'],'not valid python!',
                           ['return_dependencies','compare_bindings'])
        self.assertEqual(result['return_dependencies']['status'],'error')
        table=result['candidate_relations_on_observations']
        self.assertEqual(dict(zip(table['columns'],table['rows'][0])),
                         {'observation':'O1','binding':'B1','status':'computed','candidate_value':'2',
                          'candidate_exception':None,'holds_on_observation':True,'reason':None})

    def test_compact_matrix_preserves_unknown_reason(self):
        row=observation(([2],),2)
        b=binding('unknown',[])
        original=tools.compare(b,row,['xs'])
        table=tools.tools([b],[row],['xs'],'def f(xs): return 2',['compare_bindings'])['candidate_relations_on_observations']
        restored=dict(zip(table['columns'],table['rows'][0]))
        self.assertEqual({key:restored[key] for key in original},original)

    def test_paired_packet_facts_are_identical_and_unmodified(self):
        row={'spec':'requirement','code':'def f(xs):\n return xs\n','parameters':['xs'],
             'rows':[observation(([1],),[1])]}
        proposal={'bindings':[binding('preserve_occurrences',concept='occurrence_conservation')],'tools':['compare_bindings']}
        before=copy.deepcopy((row,proposal))
        feedback=tools.tools(proposal['bindings'],row['rows'],row['parameters'],row['code'],proposal['tools'])
        raw=app.final_packet(row,proposal,feedback,'raw');tool=app.final_packet(row,proposal,feedback,'tool')
        self.assertIsNone(raw.pop('tool_feedback'));self.assertEqual(tool.pop('tool_feedback'),feedback)
        self.assertEqual(raw,tool);self.assertEqual((row,proposal),before)
        self.assertNotIn('expected',raw);self.assertNotIn('fixture',raw)


class ControllerTests(unittest.TestCase):
    def test_selected_and_evidence_ids_are_checked(self):
        value={'selected':['B1'],'evidence':['O1']}
        app.validate_selection(value,['B1'],['O1'])
        with self.assertRaisesRegex(ValueError,'undefined_selected_binding'):
            app.validate_selection(value,['B2'],['O1'])
        with self.assertRaisesRegex(ValueError,'undefined_evidence_id'):
            app.validate_selection(value,['B1'],['O2'])

    def test_duplicate_json_and_incomplete_outputs_rejected(self):
        for response in ({'text':'{"bindings":[],"bindings":[],"tools":[]}','finish_reason':'stop'},
                         {'text':'{"bindings":[],"tools":[]}','finish_reason':'length'}):
            with self.assertRaises((ValueError,AssertionError)):
                app.decode(response,True)
        decoded=app.decode({'text':'```json\n{"bindings":[],"tools":[]}\n```','finish_reason':'stop'},True)
        self.assertEqual(decoded,{'bindings':[],'tools':[]})

    def test_parent_inventory_identity_is_frozen(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'prepared').mkdir()
            write_json(root/'freeze.json',{'sources':app.sources(),'dependencies':app.deps(),
                                          'parent_inventories':{'old':'original'},'prepared':{}})
            with patch.object(app,'ROOT',root),patch.object(app,'parent_inventories',return_value={'old':'edited'}),patch.object(app,'old_verify') as old_verify:
                with self.assertRaisesRegex(AssertionError,'frozen_parent_inventory_drift'):
                    app.verify()
                old_verify.assert_not_called()

    def test_prepare_requires_independent_approval_before_reading_pool(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(app,'ROOT',Path(temp)),patch.object(app,'old_verify') as old_verify:
            with self.assertRaises(FileNotFoundError):
                app.prepare()
            old_verify.assert_not_called()

    def test_unknown_transport_attempt_is_never_retried(self):
        counts={'completion':0}
        def handler(request):
            if request.url.path.endswith('/models'):
                return httpx.Response(200,json={'data':[{'id':'qwen2.5-coder-32b-instruct','max_model_len':8192}]})
            counts['completion']+=1
            raise httpx.ReadTimeout('artificial transport control')
        with tempfile.TemporaryDirectory() as temp:
            client=Client(Path(temp),base='http://artificial.invalid/v1',transport=httpx.MockTransport(handler))
            client.token_count=lambda _: 10
            messages=[{'role':'user','content':'artificial'}]
            with self.assertRaises(TransportStop):client.complete('slot',messages)
            with self.assertRaisesRegex(TransportStop,'already_consumed'):client.complete('slot',messages)
            self.assertEqual(counts['completion'],1)
            attempt=json.loads((Path(temp)/'calls/slot/attempt.json').read_text())
            self.assertFalse(attempt['usage_known']);client.close()


if __name__=='__main__':
    unittest.main()
